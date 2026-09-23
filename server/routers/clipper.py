from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import traceback

from server.core.queue import create_job, submit_to_queue, update_job, manager
from pipeline_shorts import analyze_video, render_youtube_clips

router = APIRouter()

class ClipperRequest(BaseModel):
    url: str
    num_clips: int = 3

def run_analyze_task(job_id: str, req: ClipperRequest):
    def update_callback(j_id, step, progress, result=None, error=None):
        status = "processing"
        if error: status = "failed"
        elif progress >= 1.0: status = "completed"
        update_job(j_id, status=status, progress=progress, result=result, error=error)
        manager.broadcast(j_id, {"type": "log", "message": step, "progress": progress})

    try:
        analyze_video(req.url, False, job_id, update_callback, req.num_clips)
    except Exception as e:
        traceback.print_exc()
        update_job(job_id, status="failed", error=str(e))
        manager.broadcast(job_id, {"type": "log", "message": f"Error: {str(e)}", "progress": 1.0})

@router.post("/analyze")
def start_analyze(req: ClipperRequest):
    job_id = create_job(f"clipper_{req.url[:20]}")
    submit_to_queue(run_analyze_task, job_id, req)
    return {"job_id": job_id, "message": "Analysis queued successfully."}

from fastapi import UploadFile, File, Form
import shutil
import uuid
import os

def run_analyze_local_task(job_id: str, video_path: str, num_clips: int):
    def update_callback(j_id, step, progress, result=None, error=None):
        status = "processing"
        if error: status = "failed"
        elif progress >= 1.0: status = "completed"
        update_job(j_id, status=status, progress=progress, result=result, error=error)
        manager.broadcast(j_id, {"type": "log", "message": step, "progress": progress})

    try:
        analyze_video(video_path, True, job_id, update_callback, num_clips)
    except Exception as e:
        traceback.print_exc()
        update_job(job_id, status="failed", error=str(e))
        manager.broadcast(job_id, {"type": "log", "message": f"Error: {str(e)}", "progress": 1.0})

@router.post("/analyze_local")
async def start_analyze_local(num_clips: int = Form(...), file: UploadFile = File(...)):
    job_id = create_job(f"clipper_local_{uuid.uuid4().hex[:6]}")
    
    output_dir = f"workspace/clipper_{job_id}"
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, file.filename)
    
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    submit_to_queue(run_analyze_local_task, job_id, video_path, num_clips)
    return {"job_id": job_id, "message": "Local analysis queued successfully."}

from typing import List, Dict, Any
class RenderRequest(BaseModel):
    job_id: str
    video_path: str
    selected_clips: List[Dict[str, Any]]

def run_render_task(job_id: str, req: RenderRequest):
    def update_callback(j_id, step, progress, result=None, error=None):
        status = "processing"
        if error: status = "failed"
        elif progress >= 1.0: status = "completed"
        update_job(j_id, status=status, progress=progress, result=result, error=error)
        manager.broadcast(j_id, {"type": "log", "message": step, "progress": progress})

    try:
        render_youtube_clips(req.job_id, req.video_path, req.selected_clips, update_callback)
    except Exception as e:
        traceback.print_exc()
        update_job(job_id, status="failed", error=str(e))
        manager.broadcast(job_id, {"type": "log", "message": f"Error: {str(e)}", "progress": 1.0})

@router.post("/render")
def start_render(req: RenderRequest):
    # reuse the same job ID so the frontend can just keep listening
    submit_to_queue(run_render_task, req.job_id, req)
    return {"job_id": req.job_id, "message": "Rendering queued successfully."}
