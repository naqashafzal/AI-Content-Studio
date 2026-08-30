from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os
import traceback
import logging

from server.core.queue import create_job, submit_to_queue, update_job, manager, _JOBS, stop_job
from server.core.videofx_client import VideoFXClient

router = APIRouter()

class VideoFXRequest(BaseModel):
    prompt: str

def run_videofx_task(job_id: str, req: VideoFXRequest):
    def frame_callback(b64_str: str):
        # Broadcast the screenshot to the frontend
        manager.broadcast(job_id, {"type": "browser_frame", "data": b64_str})
        
    try:
        update_job(job_id, status="running", step="Initializing Browser...")
        manager.broadcast(job_id, {"type": "log", "data": "Initializing browser automation..."})
        
        # Ensure outputs folder exists
        os.makedirs("videofx_outputs", exist_ok=True)
        output_path = os.path.join("videofx_outputs", f"{job_id}.mp4")
        
        profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "videofx_profile")
        client = VideoFXClient(profile_path)
        
        manager.broadcast(job_id, {"type": "log", "data": f"Injecting prompt: {req.prompt}"})
        
        job = _JOBS.get(job_id)
        stop_event = job["stop_event"] if job else None
        
        client.generate_video(req.prompt, output_path, on_frame_callback=frame_callback, stop_event=stop_event)
        
        if os.path.exists(output_path):
            update_job(job_id, status="completed", result=output_path, progress=1.0)
            manager.broadcast(job_id, {"type": "log", "data": "Video generated and downloaded successfully!"})
        else:
            raise FileNotFoundError("Video generation finished but file was not found.")
            
    except Exception as e:
        traceback.print_exc()
        logging.error(f"VideoFX task failed: {e}")
        update_job(job_id, status="failed", error=str(e))
        manager.broadcast(job_id, {"type": "log", "data": f"Error: {str(e)}"})

@router.post("/generate")
def start_videofx(req: VideoFXRequest):
    job_id = create_job("videofx")
    submit_to_queue(run_videofx_task, job_id, req)
    return {"job_id": job_id, "message": "VideoFX generation queued."}

@router.delete("/job/{job_id}")
def stop_videofx_job(job_id: str):
    stop_job(job_id)
    return {"message": "Job cancellation requested."}

@router.post("/login")
def start_login():
    profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "videofx_profile")
    client = VideoFXClient(profile_path)
    
    def safe_login():
        try:
            client.login_if_needed()
        except Exception as e:
            logging.error(f"Failed to open login browser: {e}")
            traceback.print_exc()

    # Run login in background so it doesn't block the API
    import threading
    threading.Thread(target=safe_login).start()
    
    return {"message": "Login browser opened. Please check your screen."}

@router.websocket("/ws/{job_id}")
async def videofx_websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(websocket, job_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
