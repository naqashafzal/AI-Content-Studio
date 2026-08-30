from fastapi import APIRouter
from pydantic import BaseModel
import os
import traceback
import logging

from server.core.queue import create_job, submit_to_queue, update_job, manager
from server.core.explainer_engine import ExplainerEngine

router = APIRouter()

class ExplainerRequest(BaseModel):
    url: str
    target_duration: str = "5 minutes"
    language: str = "English"
    voice: str = "Kore"
    text_engine: str = "Gemini API"
    audio_engine: str = "Gemini API"

def run_explainer_task(job_id: str, req: ExplainerRequest):
    update_job(job_id, status="running", step="Initializing Explainer Engine...")
    
    def on_progress(step_msg, progress_val):
        update_job(job_id, step=step_msg, progress=progress_val)
        manager.broadcast(job_id, {"type": "log", "message": step_msg, "progress": progress_val})
        
    try:
        engine = ExplainerEngine(
            job_id=job_id,
            url=req.url,
            target_duration=req.target_duration,
            language=req.language,
            voice=req.voice,
            text_engine=req.text_engine,
            audio_engine=req.audio_engine,
            on_progress=on_progress
        )
        
        final_video = engine.process()
        
        if final_video and os.path.exists(final_video):
            update_job(job_id, status="completed", result=final_video, progress=1.0)
        else:
            raise Exception("Final video was not generated successfully.")
            
    except Exception as e:
        traceback.print_exc()
        logging.error(f"Movie explainer task failed: {e}")
        update_job(job_id, status="failed", error=str(e))
        manager.broadcast(job_id, {"type": "log", "message": f"Error: {str(e)}", "progress": 1.0})

@router.post("/process")
def start_explainer(req: ExplainerRequest):
    job_id = create_job("explainer")
    submit_to_queue(run_explainer_task, job_id, req)
    return {"job_id": job_id, "message": "Explainer job queued."}
