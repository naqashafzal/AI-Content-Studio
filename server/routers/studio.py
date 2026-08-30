from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os
import re
import json
import threading

from config import load_config
from agents import WriterAgent, DirectorAgent, ImageGenAgent, VideoGenAgent, EditorAgent
from api_clients import GoogleClient

router = APIRouter()

class DummyUI:
    def log_to_agent_console(self, msg): print(msg)
    def update_agent_node(self, name, status, state): pass

class ScriptRequest(BaseModel):
    topic: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class StoryboardRequest(BaseModel):
    topic: str
    script: str
    style: str = "Cinematic Documentary"

class RenderRequest(BaseModel):
    topic: str
    script: str
    storyboard: List[Dict[str, Any]]
    aspect_ratio: str = "16:9"

@router.post("/chat")
def handle_chat(req: ChatRequest):
    try:
        config = load_config()
        client = GoogleClient(config)
        
        system_prompt = """You are the Director Agent for an elite AI Content Studio.
Your goal is to brainstorm viral video topics with the user and help them write a script.
Keep your responses conversational, concise, and highly creative.
If the user explicitly approves a topic or asks you to write the full script, write the script!
CRITICAL INSTRUCTION: When you write the full, final script that is ready to be generated, you MUST append this EXACT exact marker at the very bottom of your response:
FINAL_SCRIPT_READY:
[Title of the video]
[The full script text here]
"""
        
        # Build prompt from history
        prompt = system_prompt + "\n\n--- CONVERSATION HISTORY ---\n"
        for msg in req.messages:
            prompt += f"{msg.role.upper()}: {msg.content}\n"
            
        prompt += "DIRECTOR:"
        
        response = client._generate_text(prompt)
        
        script_ready = False
        script_text = ""
        topic_title = "Generated Video"
        
        if "FINAL_SCRIPT_READY:" in response:
            parts = response.split("FINAL_SCRIPT_READY:")
            main_text = parts[0].strip()
            script_block = parts[1].strip().split('\n')
            if len(script_block) > 0:
                topic_title = script_block[0].strip()
                script_text = "\n".join(script_block[1:]).strip()
            script_ready = True
            response = main_text
            
        return {
            "text": response,
            "script_ready": script_ready,
            "script": script_text,
            "topic": topic_title
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/script")
def generate_script(req: ScriptRequest):
    try:
        config = load_config()
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', req.topic)
        output_dir = os.path.join("workspace", safe_topic)
        os.makedirs(output_dir, exist_ok=True)
        
        writer = WriterAgent(config, DummyUI(), "WriterAgent")
        script_file = writer.generate_script(req.topic, output_dir)
        
        with open(script_file, "r", encoding="utf-8") as f:
            script_text = f.read()
            
        return {"script": script_text, "output_dir": output_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/storyboard")
def generate_storyboard(req: StoryboardRequest):
    try:
        config = load_config()
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', req.topic)
        output_dir = os.path.join("workspace", safe_topic)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save edited script
        script_file = os.path.join(output_dir, "script.txt")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(req.script)
            
        director = DirectorAgent(config, DummyUI(), "DirectorAgent")
        scenes = director.generate_storyboard(req.topic, script_file, output_dir, style=req.style)
        
        return {"storyboard": scenes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _run_render_task(req: RenderRequest, output_dir: str):
    try:
        config = load_config()
        # Save script and storyboard
        script_file = os.path.join(output_dir, "script.txt")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(req.script)
            
        sb_file = os.path.join(output_dir, "storyboard.json")
        with open(sb_file, "w", encoding="utf-8") as f:
            json.dump(req.storyboard, f, indent=2)
            
        # Audio
        writer = WriterAgent(config, DummyUI(), "WriterAgent")
        audio_file = writer.generate_audio(script_file, output_dir)
        
        # Image Gen
        image_gen = ImageGenAgent(config, DummyUI(), "ImageGenAgent")
        image_paths = image_gen.run(req.storyboard, output_dir, aspect_ratio=req.aspect_ratio)
        
        # Video Gen
        video_gen = VideoGenAgent(config, DummyUI(), "VideoGenAgent")
        video_paths = video_gen.run(req.storyboard, image_paths, output_dir, aspect_ratio=req.aspect_ratio)
        
        # Editor
        editor = EditorAgent(config, DummyUI(), "EditorAgent")
        final_video = editor.run(video_paths, audio_file, output_dir)
        
    except Exception as e:
        print(f"Render Task Failed: {e}")

@router.post("/render")
def render_video(req: RenderRequest):
    try:
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', req.topic)
        output_dir = os.path.join("workspace", safe_topic)
        os.makedirs(output_dir, exist_ok=True)
        
        # Run rendering in background (or foreground if we want to block, but it takes long)
        threading.Thread(target=_run_render_task, args=(req, output_dir)).start()
        
        return {"message": "Rendering started in background. Please check the History page in a few minutes.", "output_dir": output_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
