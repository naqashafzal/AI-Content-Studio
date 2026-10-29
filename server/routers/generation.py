from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import threading
import traceback
import os
import json
import glob

from server.core.queue import (
    create_job, update_job, get_job, stop_job, add_log,
    current_job_id, _JOBS, manager, submit_to_queue, list_jobs
)
from server.core.model_gateway import gateway
from config import load_config, save_config
import pipeline
from agents import TrendAgent, WriterAgent, DirectorAgent, AgentOrchestrator

router = APIRouter()

class JobUI:
    def __init__(self, job_id: str):
        self.job_id = job_id
        
    def log_to_agent_console(self, msg):
        print(f"[{self.job_id}] {msg}")
        add_log(self.job_id, msg)
        
    def update_agent_node(self, name, status, state):
        pass

class GenerationRequest(BaseModel):
    topic: str
    style: str = "Cinematic Documentary"
    voice: Optional[str] = "Kore"
    aspect_ratio: Optional[str] = "16:9"
    bg_mode: Optional[str] = "AI Video"
    bg_music: Optional[bool] = True
    fact_check: Optional[bool] = False
    auto_captions: Optional[bool] = True
    omnichannel: Optional[bool] = False
    start_point: Optional[str] = "Deep Research"
    content_style: Optional[str] = "Podcast"
    image_count: Optional[int] = 8
    video_count: Optional[int] = 1
    generate_thumbnail: Optional[bool] = False
    generate_seo: Optional[bool] = False
    generate_timestamps: Optional[bool] = False
    generate_snippets: Optional[bool] = False
    script_length: Optional[str] = "Medium (~5 minutes)"
    audio_engine: Optional[str] = "Gemini API"
    video_engine: Optional[str] = "WaveSpeed AI"

def run_pipeline_task(job_id: str, req: GenerationRequest):
    current_job_id.set(job_id)
    update_job(job_id, status="running")
    
    config = load_config()
    config["CONTENT_STYLE"] = req.content_style
    config["VISUAL_STYLE"] = req.style
    if req.voice: 
        config["VOICE_NAME"] = req.voice
        config["SPEAKER1"] = req.voice
    if req.audio_engine:
        config["AUDIO_ENGINE"] = req.audio_engine
    if req.video_engine:
        config["VIDEO_ENGINE"] = req.video_engine
    if req.aspect_ratio: config["VIDEO_ASPECT_RATIO"] = req.aspect_ratio
    if req.bg_mode: config["BG_MODE"] = req.bg_mode
    config["ADD_MUSIC"] = req.bg_music
    config["FACT_CHECK_ENABLED"] = req.fact_check
    config["CAPTION_ENABLED"] = req.auto_captions
    config["OMNICHANNEL"] = req.omnichannel
    config["IMAGE_COUNT"] = req.image_count
    config["VIDEO_CLIP_COUNT"] = req.video_count
    config["GENERATE_THUMBNAIL"] = req.generate_thumbnail
    config["GENERATE_SEO"] = req.generate_seo
    config["GENERATE_TIMESTAMPS"] = req.generate_timestamps
    config["GENERATE_SNIPPETS"] = req.generate_snippets
    if req.script_length: config["SCRIPT_LENGTH"] = req.script_length
    
    job = _JOBS[job_id]
    stop_event = job["stop_event"]
    
    def update_progress(step_index, status_label, val):
        update_job(job_id, step=status_label, progress=val)
        
    try:
        p = pipeline.Pipeline(config, stop_event, update_progress)
        final_vid = p.run(req.topic, start_point=req.start_point)
        
        if stop_event.is_set():
            update_job(job_id, status="cancelled")
        elif final_vid and os.path.exists(final_vid):
            update_job(job_id, status="completed", result=final_vid.replace("\\", "/"), progress=1.0)
        else:
            update_job(job_id, status="failed", error="Video file output was not produced. Please check your API keys or FFmpeg setup.", progress=1.0)
            
    except Exception as e:
        traceback.print_exc()
        update_job(job_id, status="failed", error=str(e))

@router.post("/quick")
def start_quick_generation(req: GenerationRequest):
    job_id = create_job(req.topic)
    submit_to_queue(run_pipeline_task, job_id, req)
    return {"job_id": job_id, "message": "Generation queued successfully."}

@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(websocket, job_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)

@router.get("/viral-topics")
def get_viral_topics():
    config = load_config()
    topic_logger_ui = JobUI("topic_discovery")
    trend_agent = TrendAgent(config, topic_logger_ui, "TrendAgent")
    topics = trend_agent.find_viral_topics()
    return {"topics": topics}

@router.get("/status/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/cancel/{job_id}")
def cancel_job(job_id: str):
    stop_job(job_id)
    return {"message": f"Cancellation requested for {job_id}"}

@router.get("/settings")
def get_app_settings():
    return load_config(masked=True)

@router.post("/settings")
def update_app_settings(new_config: Dict[str, Any]):
    current = load_config()
    current.update(new_config)
    save_config(current)
    gateway.refresh_config()
    return {"message": "Settings saved successfully."}

@router.get("/history")
def get_generation_history():
    workspace_dir = "workspace"
    projects = []

    if os.path.exists(workspace_dir):
        for folder in os.listdir(workspace_dir):
            folder_path = os.path.join(workspace_dir, folder)
            if not os.path.isdir(folder_path) or folder == "tools_output":
                continue

            if folder.startswith("clipper_"):
                project_type = "clipper"
            elif folder.startswith("director_") or folder.startswith("plan_"):
                project_type = "director"
            else:
                project_type = "podcast"

            videos = []
            scripts = []
            created_at = os.path.getctime(folder_path)

            if project_type == "podcast":
                for candidate in ("final_podcast.mp4", "final_podcast_video.mp4", "master_render.mp4"):
                    vid = os.path.join(folder_path, candidate)
                    if os.path.exists(vid):
                        videos.append({"title": "Full Podcast", "path": vid.replace("\\", "/")})
                        break
                script = os.path.join(folder_path, "podcast_script.txt")
                if os.path.exists(script):
                    scripts.append(script.replace("\\", "/"))
            elif project_type == "director":
                for candidate in ("master_render.mp4", "final_director.mp4", "edited_output.mp4"):
                    vid = os.path.join(folder_path, candidate)
                    if os.path.exists(vid):
                        videos.append({"title": "Director Cut", "path": vid.replace("\\", "/")})
                script = os.path.join(folder_path, "storyboard.json")
                if os.path.exists(script):
                    scripts.append(script.replace("\\", "/"))
            else:
                clip_files = glob.glob(os.path.join(folder_path, "Final_*.mp4"))
                for cf in clip_files:
                    basename = os.path.basename(cf)
                    title = basename.replace("Final_", "").replace(".mp4", "").replace("_", " ")
                    videos.append({"title": title, "path": cf.replace("\\", "/")})

            if videos or scripts:
                projects.append({
                    "id": folder,
                    "type": project_type,
                    "created_at": created_at,
                    "videos": videos,
                    "scripts": scripts
                })

    outputs_dir = "outputs"
    if os.path.exists(outputs_dir):
        for folder in os.listdir(outputs_dir):
            folder_path = os.path.join(outputs_dir, folder)
            if not os.path.isdir(folder_path):
                continue

            created_at = os.path.getctime(folder_path)
            videos = []
            scripts = []

            if folder.startswith("explainer_"):
                project_type = "movie explainer"
                final_vid = os.path.join(folder_path, "final_explainer.mp4")
                if os.path.exists(final_vid):
                    videos.append({"title": "Full Explainer Video", "path": final_vid.replace("\\", "/")})
                script_file = os.path.join(folder_path, "script.json")
                if os.path.exists(script_file):
                    scripts.append(script_file.replace("\\", "/"))
            elif folder.startswith("director_"):
                project_type = "director"
                for mp4 in glob.glob(os.path.join(folder_path, "*.mp4")):
                    videos.append({"title": os.path.basename(mp4), "path": mp4.replace("\\", "/")})
            else:
                continue

            if videos or scripts:
                projects.append({
                    "id": folder,
                    "type": project_type,
                    "created_at": created_at,
                    "videos": videos,
                    "scripts": scripts
                })

    projects.sort(key=lambda x: x["created_at"], reverse=True)
    return projects

@router.get("/stats")
def get_dashboard_stats():
    """Returns real telemetry for the Command Center dashboard."""
    projects = get_generation_history()
    jobs = list_jobs(limit=100)
    cfg = load_config()

    total_videos = sum(len(p.get("videos", [])) for p in projects)
    completed_jobs = [j for j in jobs if j.get("status") == "completed"]
    active_jobs = [j for j in jobs if j.get("status") in ("running", "processing", "queued")]

    # Calculate approximate render hours based on completed jobs & videos
    render_hours = round((total_videos * 3.5 + len(completed_jobs) * 2.0) / 60.0, 1)

    configured_keys = sum(
        1 for k in ("GEMINI_API_KEY", "WAVESPEED_API_KEY", "PIXABAY_API_KEY", "NEWS_API_KEY")
        if cfg.get(k)
    )

    recent_items = []
    for p in projects[:6]:
        vids = p.get("videos", [])
        first_vid = vids[0]["path"] if vids else None
        recent_items.append({
            "id": p["id"],
            "title": p["id"].replace("clipper_", "").replace("explainer_", "").replace("director_", "").replace("_", " ").title(),
            "type": p["type"],
            "created_at": p["created_at"],
            "video_count": len(vids),
            "video_path": first_vid
        })

    return {
        "total_generated": total_videos or len(completed_jobs),
        "total_projects": len(projects),
        "render_hours": render_hours,
        "active_jobs": len(active_jobs),
        "completed_jobs": len(completed_jobs),
        "configured_providers": configured_keys,
        "recent_projects": recent_items,
        "recent_jobs": jobs[:6]
    }

@router.delete("/history/{project_id}")
def delete_project(project_id: str):
    import shutil
    clean_id = os.path.basename(project_id.strip())
    if clean_id != project_id or ".." in project_id or "/" in project_id or "\\" in project_id:
        raise HTTPException(status_code=400, detail="Invalid project ID format.")

    if clean_id.startswith("explainer_"):
        base_dir = os.path.abspath("outputs")
    else:
        base_dir = os.path.abspath("workspace")

    folder_path = os.path.abspath(os.path.join(base_dir, clean_id))
    if not folder_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Access denied.")
        
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        shutil.rmtree(folder_path)
        return {"message": "Project deleted."}
    raise HTTPException(status_code=404, detail="Project not found")

@router.get("/media")
def serve_media_file(path: str = Query(...)):
    from server.core.security import media_path
    return FileResponse(media_path(path), headers={"X-Content-Type-Options": "nosniff"})
