from server.core.security import copy_upload
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import traceback
import re

from server.core.queue import create_job, submit_to_queue, update_job, manager
from pipeline_shorts import analyze_video, render_youtube_clips

router = APIRouter()

class ClipperRequest(BaseModel):
    url: str
    num_clips: int = Field(3, ge=1, le=20)
    min_duration: float = Field(15.0, ge=5, le=120)
    max_duration: float = Field(60.0, ge=10, le=180)
    language: Optional[str] = "auto"

def _make_callback():
    def update_callback(j_id, step, progress, result=None, error=None):
        status = "processing"
        if error: status = "failed"
        elif progress >= 1.0: status = "completed"
        update_job(j_id, status=status, progress=progress, result=result, error=error)
        manager.broadcast(j_id, {"type": "log", "message": step, "progress": progress})
    return update_callback

def _fail(job_id: str, e: Exception):
    traceback.print_exc()
    update_job(job_id, status="failed", error=str(e))
    manager.broadcast(job_id, {"type": "log", "message": f"Error: {str(e)}", "progress": 1.0})

def run_analyze_task(job_id: str, req: ClipperRequest):
    try:
        analyze_video(req.url, False, job_id, _make_callback(), req.num_clips,
                      req.min_duration, req.max_duration, req.language)
    except Exception as e:
        _fail(job_id, e)

@router.post("/analyze")
def start_analyze(req: ClipperRequest):
    if req.max_duration <= req.min_duration:
        raise HTTPException(status_code=400, detail="max_duration must be greater than min_duration.")
    job_id = create_job(f"clipper_{req.url[:20]}")
    submit_to_queue(run_analyze_task, job_id, req)
    return {"job_id": job_id, "message": "Analysis queued successfully."}

from fastapi import UploadFile, File, Form
import shutil
import uuid
import os

def run_analyze_local_task(job_id: str, video_path: str, num_clips: int,
                           min_duration: float = 15.0, max_duration: float = 60.0, language: str = "auto"):
    try:
        analyze_video(video_path, True, job_id, _make_callback(), num_clips, min_duration, max_duration, language)
    except Exception as e:
        _fail(job_id, e)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

@router.post("/analyze_local")
async def start_analyze_local(
    num_clips: int = Form(...),
    file: UploadFile = File(...),
    min_duration: float = Form(15.0),
    max_duration: float = Form(60.0),
    language: str = Form("auto"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    if not (1 <= num_clips <= 20):
        raise HTTPException(status_code=400, detail="num_clips must be between 1 and 20.")
    if max_duration <= min_duration or min_duration < 5:
        raise HTTPException(status_code=400, detail="Invalid duration range.")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
        
    job_id = create_job(f"clipper_local_{uuid.uuid4().hex[:6]}")
    output_dir = os.path.abspath(f"workspace/clipper_{job_id}")
    os.makedirs(output_dir, exist_ok=True)

    # Sanitize filename and avoid path traversal
    safe_basename = re.sub(r'[^a-zA-Z0-9_\-.]', '_', os.path.basename(file.filename))
    safe_filename = f"upload_{uuid.uuid4().hex[:8]}_{safe_basename}"
    video_path = os.path.join(output_dir, safe_filename)
    
    copy_upload(file.file, video_path)
        
    submit_to_queue(run_analyze_local_task, job_id, video_path, num_clips, min_duration, max_duration, language)
    return {"job_id": job_id, "message": "Local analysis queued successfully."}

class RenderRequest(BaseModel):
    job_id: str
    video_path: str
    selected_clips: List[Dict[str, Any]]

def run_render_task(job_id: str, req: RenderRequest):
    try:
        render_youtube_clips(req.job_id, req.video_path, req.selected_clips, _make_callback())
    except Exception as e:
        _fail(job_id, e)

@router.post("/render")
def start_render(req: RenderRequest):
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", req.job_id or ""):
        raise HTTPException(status_code=400, detail="Invalid job_id.")
    # Only allow rendering source videos that live inside the workspace directory
    workspace_root = os.path.realpath(os.path.abspath("workspace"))
    real_video = os.path.realpath(os.path.abspath(req.video_path))
    if os.path.commonpath([workspace_root, real_video]) != workspace_root or not os.path.isfile(real_video):
        raise HTTPException(status_code=400, detail="video_path must be an existing file inside the workspace.")
    if not req.selected_clips:
        raise HTTPException(status_code=400, detail="No clips selected.")
    req.video_path = real_video
    # reuse the same job ID so the frontend can just keep listening
    submit_to_queue(run_render_task, req.job_id, req)
    return {"job_id": req.job_id, "message": "Rendering queued successfully."}
