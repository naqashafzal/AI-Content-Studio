import io
import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from server.main import app
from server.core.security import media_path, copy_upload
from server.core.database import SessionLocal, OAuthState, QueueTask
from server.core.queue import create_job, submit_to_queue, recover_pending_tasks, get_job
from server.routers.generation import run_pipeline_task, GenerationRequest
from datetime import datetime, timedelta
import hashlib

client = TestClient(app)
authorized = TestClient(app, headers={"X-API-Key": "test-suite-token"})

def test_default_auth_and_cookie_session():
    assert client.get("/api/config").status_code == 401
    assert client.get("/api/config?token=test-suite-token").status_code == 401
    with TestClient(app) as browser:
        assert browser.post("/api/session", data={"token": "wrong"}, follow_redirects=False).status_code == 401
        response = browser.post("/api/session", data={"token": "test-suite-token"}, follow_redirects=False)
        assert response.status_code == 303
        assert "HttpOnly" in response.headers["set-cookie"]
        assert browser.get("/api/config").status_code == 200
        assert browser.post("/api/config", json={}, headers={"Origin": "https://evil.example"}).status_code == 403
        browser.delete("/api/session")
        assert browser.get("/api/config").status_code == 401

def test_websocket_requires_auth_and_origin():
    job_id = create_job("websocket security")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/generate/ws/{job_id}"):
            pass
    with pytest.raises(WebSocketDisconnect):
        with authorized.websocket_connect(f"/api/generate/ws/{job_id}", headers={"Origin": "https://evil.example"}):
            pass
    with authorized.websocket_connect(f"/api/generate/ws/{job_id}") as ws:
        assert ws.receive_json()["type"] == "full_state"

def test_database_and_symlink_are_not_media(tmp_path):
    assert authorized.get("/api/generate/media?path=workspace/app.db").status_code in (403, 404)
    secret = tmp_path / "secret.mp4"
    secret.write_bytes(b"private")
    from pathlib import Path
    link = Path("workspace/release-test-link.mp4")
    link.symlink_to(secret)
    try:
        assert authorized.get("/api/generate/media", params={"path": str(link)}).status_code in (403, 404)
    finally:
        link.unlink()

def test_upload_limit_removes_partial_file(tmp_path):
    output = tmp_path / "upload.mp4"
    with patch("server.core.security.MAX_UPLOAD_BYTES", 3):
        with pytest.raises(HTTPException) as exc:
            copy_upload(io.BytesIO(b"1234"), output)
    assert exc.value.status_code == 413
    assert not output.exists()

def test_conversion_ignores_client_filename(tmp_path):
    from server.routers.tools import convert_aspect_ratio
    from starlette.datastructures import UploadFile
    with patch("server.routers.tools.subprocess.run") as run:
        result = convert_aspect_ratio(UploadFile(io.BytesIO(b"video"), filename="../../escape.mp4"), "16:9")
    assert ".." not in result["path"]
    assert result["path"].startswith("workspace/tools_output/")
    assert run.call_args.args[0][-1] == result["path"]

def test_oauth_requires_state_and_consumes_it_once():
    assert client.get("/api/social/youtube/callback?code=example").status_code == 400
    state = "test-oauth-state"
    with SessionLocal() as db:
        db.add(OAuthState(state_hash=hashlib.sha256(state.encode()).hexdigest(), expires_at=datetime.utcnow()+timedelta(minutes=1)))
        db.commit()
    with TestClient(app) as browser:
        browser.cookies.set("studio_oauth_state", state)
        with patch("server.routers.social.youtube_flow", side_effect=RuntimeError("provider unavailable")):
            assert browser.get("/api/social/youtube/callback", params={"code": "example", "state": state}).status_code == 502
            assert browser.get("/api/social/youtube/callback", params={"code": "example", "state": state}).status_code == 400

def test_queued_work_is_persisted_and_resubmitted_after_restart():
    job_id = create_job("durability")
    with patch("server.core.queue.worker_pool.submit") as submit:
        submit_to_queue(run_pipeline_task, job_id, GenerationRequest(topic="durability"))
        with SessionLocal() as db:
            task = db.query(QueueTask).filter_by(job_id=job_id).one()
            task_id = task.id
            assert task.status == "queued"
            assert "durability" in task.arguments
        submit.reset_mock()
        recover_pending_tasks()
        assert any(call.args[1] == task_id for call in submit.call_args_list)
        with pytest.raises(HTTPException) as exc:
            submit_to_queue(run_pipeline_task, job_id, GenerationRequest(topic="durability"))
        assert exc.value.status_code == 409
    # Clean up this deliberately queued task before another lifespan starts.
    with SessionLocal() as db:
        db.query(QueueTask).filter_by(id=task_id).update({"status": "cancelled"})
        db.commit()


def test_chunked_request_limit():
    with patch("server.core.security.MAX_UPLOAD_BYTES", 1):
        response = authorized.post("/api/config", content=iter([b"x" * (1024 * 1024 + 2)]))
    assert response.status_code == 413


def test_persisted_task_rehydrates_request_and_claims_only_once():
    from server.core.queue import _run_persisted_task
    job_id = create_job("request serialization")
    with patch("server.core.queue.worker_pool.submit"):
        submit_to_queue(run_pipeline_task, job_id, GenerationRequest(topic="serialized topic"))
    with SessionLocal() as db:
        task_id = db.query(QueueTask).filter_by(job_id=job_id).one().id
    with patch("server.routers.generation.run_pipeline_task") as run:
        _run_persisted_task(task_id)
        _run_persisted_task(task_id)
        run.assert_called_once()
        assert run.call_args.args[1].topic == "serialized topic"


def test_retry_uses_latest_task_and_does_not_duplicate_active_work():
    from server.core.queue import retry_interrupted_task, update_job
    job_id = create_job("retry latest stage")
    with SessionLocal() as db:
        for task_id, status in (("z-earlier", "completed"), ("a-later", "interrupted")):
            db.add(QueueTask(id=task_id, job_id=job_id, function="server.routers.generation:run_pipeline_task", arguments='{}', status=status))
            db.commit()
    update_job(job_id, status="interrupted")
    with patch("server.core.queue.worker_pool.submit") as submit:
        retry_interrupted_task(job_id)
        assert submit.call_args.args[1] == "a-later"
        with pytest.raises(HTTPException):
            retry_interrupted_task(job_id)
    with SessionLocal() as db:
        db.query(QueueTask).filter_by(job_id=job_id).update({"status": "cancelled"})
        db.commit()


def test_second_backend_worker_cannot_start():
    with TestClient(app):
        with pytest.raises(RuntimeError, match="exactly one backend worker"):
            with TestClient(app):
                pass
