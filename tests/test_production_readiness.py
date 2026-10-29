import os
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.main import app
from config import load_config, save_config

client = TestClient(app, headers={"X-API-Key": "test-suite-token"})

def test_style_routes_both_singular_and_plural():
    """Verifies that both /api/style and /api/styles work without 404."""
    res_singular = client.get("/api/style")
    res_plural = client.get("/api/styles")
    assert res_singular.status_code == 200
    assert res_plural.status_code == 200
    assert isinstance(res_singular.json(), list)
    assert len(res_singular.json()) >= 1

def test_cancel_routes_both_alias_and_generate():
    """Verifies that both /api/cancel/{job_id} and /api/generate/cancel/{job_id} work."""
    from server.core.queue import create_job, get_job
    j1 = create_job("Cancel Alias Test")
    res1 = client.post(f"/api/cancel/{j1}")
    assert res1.status_code == 200
    assert get_job(j1)["status"] == "cancelled"

    j2 = create_job("Cancel Generate Test")
    res2 = client.post(f"/api/generate/cancel/{j2}")
    assert res2.status_code == 200
    assert get_job(j2)["status"] == "cancelled"

def test_dashboard_stats_endpoint():
    """Verifies /api/generate/stats returns live telemetry for the dashboard."""
    res = client.get("/api/generate/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_generated" in data
    assert "render_hours" in data
    assert "recent_projects" in data
    assert "configured_providers" in data

def test_wavespeed_key_synchronization(tmp_path):
    """Verifies WAVESPEED_API_KEY and WAVESPEED_AI_KEY are kept in sync."""
    cfg_file = str(tmp_path / "ws_config.json")
    save_config({"WAVESPEED_API_KEY": "ws_live_secret_987654"}, config_path=cfg_file)
    with open(cfg_file, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["WAVESPEED_API_KEY"] == "ws_live_secret_987654"
    assert saved["WAVESPEED_AI_KEY"] == "ws_live_secret_987654"

def test_publish_and_social_path_traversal_blocked():
    """Verifies /api/publish/youtube and /api/social/export-bundle block paths outside workspace."""
    res1 = client.post("/api/publish/youtube", json={
        "video_path": "config.json",
        "title": "Test",
        "description": "Desc",
        "tags": "tag"
    })
    assert res1.status_code == 403

    res2 = client.post("/api/social/export-bundle", json={
        "video_path": "../secret.mp4",
        "title": "Test"
    })
    assert res2.status_code == 403

def test_explainer_local_file_path_traversal_blocked():
    """Verifies ExplainerEngine blocks copying local files outside workspace."""
    from server.core.explainer_engine import ExplainerEngine
    eng = ExplainerEngine(
        job_id="sec_test",
        url="config.json",
        target_duration="3 minutes",
        on_progress=lambda m, p: None
    )
    if os.path.exists(eng.video_path):
        os.remove(eng.video_path)
    with pytest.raises(PermissionError):
        eng.download_video()

def test_tools_media_workspace_resolution():
    """Verifies media files inside workspace/tools_output can be served via /api/generate/media."""
    os.makedirs("workspace/tools_output", exist_ok=True)
    dummy_file = "workspace/tools_output/test_sample.mp4"
    with open(dummy_file, "w", encoding="utf-8") as f:
        f.write("media ok")
    try:
        res1 = client.get(f"/api/generate/media?path={dummy_file}")
        assert res1.status_code == 200
        # Also verify relative tools_output/test_sample.mp4 resolves safely inside workspace
        res2 = client.get("/api/generate/media?path=tools_output/test_sample.mp4")
        assert res2.status_code == 200
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

def test_storyboard_master_render():
    """Verifies AutonomousStudioOrchestrator.render_approved_storyboard produces an MP4 in workspace."""
    from server.core.queue import create_job, save_stage_checkpoint
    from server.core.orchestrator import AutonomousStudioOrchestrator

    job_id = create_job("Test Storyboard Render", job_type="plan")
    mock_plan = {
        "title": "Quantum Horizons",
        "hook": "Quantum computing is here.",
        "style": "Cinematic Documentary",
        "scenes": [
            {
                "scene_number": 1,
                "duration_estimate_sec": 3.0,
                "speaker": "Host",
                "narration": "Welcome to the future of quantum computing.",
                "visual_description": "Futuristic quantum processor core",
                "camera_framing": "Wide",
                "locked": True
            }
        ]
    }
    save_stage_checkpoint(job_id, "storyboard", mock_plan)

    orch = AutonomousStudioOrchestrator(job_id=job_id)
    with patch("server.core.orchestrator.load_config", return_value={"GEMINI_API_KEY": "", "WAVESPEED_API_KEY": "", "PIXABAY_API_KEY": ""}):
        out_mp4 = orch.render_approved_storyboard()
    assert os.path.exists(out_mp4)
    assert out_mp4.startswith("workspace/")
    assert out_mp4.endswith("master_render.mp4")
