from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import threading
import traceback
import os
import json

from server.core.queue import create_job, update_job, get_job, stop_job, add_log, current_job_id, _JOBS, manager, submit_to_queue
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
            update_job(job_id, status="completed", result=final_vid, progress=1.0)
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
            # We don't really expect to receive much from the client, 
            # but we keep the connection open and listen for close.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)

@router.get("/viral-topics")
def get_viral_topics():
    config = load_config()
    trend_agent = TrendAgent(config, JobUI(job_id), "TrendAgent")
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
    return load_config()

@router.post("/settings")
def update_app_settings(new_config: Dict[str, Any]):
    current = load_config()
    current.update(new_config)
    save_config(current)
    return {"message": "Settings saved successfully."}

@router.get("/history")
def get_generation_history():
    import glob
    workspace_dir = "workspace"
    if not os.path.exists(workspace_dir):
        return []
    
    projects = []
    for folder in os.listdir(workspace_dir):
        folder_path = os.path.join(workspace_dir, folder)
        if not os.path.isdir(folder_path): continue
            
        # Determine project type
        project_type = "clipper" if folder.startswith("clipper_") else "podcast"
        
        videos = []
        scripts = []
        
        # Get creation time (approx) based on directory creation
        created_at = os.path.getctime(folder_path)
        
        if project_type == "podcast":
            vid = os.path.join(folder_path, "final_podcast.mp4")
            if not os.path.exists(vid): vid = os.path.join(folder_path, "final_podcast_video.mp4")
            if os.path.exists(vid): videos.append({"title": "Full Podcast", "path": vid.replace("\\", "/")})
            
            script = os.path.join(folder_path, "podcast_script.txt")
            if os.path.exists(script): scripts.append(script.replace("\\", "/"))
        else:
            # Clipper shorts
            clip_files = glob.glob(os.path.join(folder_path, "Final_*.mp4"))
            for cf in clip_files:
                basename = os.path.basename(cf)
                title = basename.replace("Final_", "").replace(".mp4", "").replace("_", " ")
                videos.append({"title": title, "path": cf.replace("\\", "/")})
                
        # Only add projects that have some content
        if videos or scripts:
            projects.append({
                "id": folder,
                "type": project_type,
                "created_at": created_at,
                "videos": videos,
                "scripts": scripts
            })
            
    # Also check outputs directory for explainer videos
    outputs_dir = "outputs"
    if os.path.exists(outputs_dir):
        for folder in os.listdir(outputs_dir):
            if not folder.startswith("explainer_"): continue
            folder_path = os.path.join(outputs_dir, folder)
            if not os.path.isdir(folder_path): continue
            
            project_type = "movie explainer"
            created_at = os.path.getctime(folder_path)
            
            videos = []
            final_vid = os.path.join(folder_path, "final_explainer.mp4")
            if os.path.exists(final_vid):
                videos.append({"title": "Full Explainer Video", "path": final_vid.replace("\\", "/")})
                
            scripts = []
            script_file = os.path.join(folder_path, "script.json")
            if os.path.exists(script_file):
                scripts.append(script_file.replace("\\", "/"))
                
            if videos or scripts:
                projects.append({
                    "id": folder,
                    "type": project_type,
                    "created_at": created_at,
                    "videos": videos,
                    "scripts": scripts
                })
            
    # Sort descending by creation date
    projects.sort(key=lambda x: x["created_at"], reverse=True)
    return projects

@router.delete("/history/{project_id}")
def delete_project(project_id: str):
    import shutil
    if project_id.startswith("explainer_"):
        folder_path = os.path.join("outputs", project_id)
    else:
        folder_path = os.path.join("workspace", project_id)
        
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        return {"message": "Project deleted."}
    raise HTTPException(status_code=404, detail="Project not found")

@router.get("/media")
def serve_media_file(path: str = Query(...)):
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Media file not found.")
