from fastapi import APIRouter
from pydantic import BaseModel
import traceback

from server.core.queue import create_job, submit_to_queue, update_job, manager
from server.core.director_engine import run_director_pipeline

router = APIRouter()

class DirectorRequest(BaseModel):
    url: str
    remove_silence: bool = True
    add_punch_ins: bool = True
    add_sfx: bool = True

def run_director_task(job_id: str, req: DirectorRequest):
    def update_callback(j_id, step, progress, result=None, error=None):
        status = "processing"
        if error: status = "failed"
        elif progress >= 1.0: status = "completed"
        update_job(j_id, status=status, progress=progress, result=result, error=error)
        manager.broadcast(j_id, {"type": "log", "message": step, "progress": progress})

    try:
        run_director_pipeline(
            req.url, 
            job_id, 
            update_callback,
            remove_silence=req.remove_silence,
            add_punch_ins=req.add_punch_ins,
            add_sfx=req.add_sfx
        )
    except Exception as e:
        traceback.print_exc()
        update_job(job_id, status="failed", error=str(e))
        manager.broadcast(job_id, {"type": "log", "message": f"Error: {str(e)}", "progress": 1.0})

@router.post("/process")
def start_director(req: DirectorRequest):
    job_id = create_job(f"director_{req.url[:20]}")
    submit_to_queue(run_director_task, job_id, req)
    return {"job_id": job_id, "message": "Director job queued successfully."}
