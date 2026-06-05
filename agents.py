import os
import time
import json
import logging
import wave
import re
import subprocess
from pathlib import Path
from pydub import AudioSegment

from api_clients import GoogleClient, WaveSpeedClient, NewsApiClient

class BaseAgent:
    def __init__(self, config, ui_context, name):
        self.config = config
        self.ui_context = ui_context
        self.name = name
        
    def log(self, msg):
        self.ui_context.log_to_agent_console(f"[{self.name}] {msg}")
        
    def set_status(self, status_text, state="idle"):
        self.ui_context.update_agent_node(self.name, status_text, state)

class WriterAgent(BaseAgent):
    def run(self, topic, output_dir):
        self.set_status("Researching...", "running")
        self.log(f"Starting research on: {topic}")
        google_client = GoogleClient(self.config)
        news_client = NewsApiClient(self.config.get("NEWS_API_KEY"))
        
        research = google_client.deep_research(topic, "English", news_client)
        
        self.set_status("Writing Script...", "running")
        self.log("Writing cinematic script...")
        script = google_client.generate_podcast_script(topic, research, self.config)
        
        script_file = os.path.join(output_dir, "script.txt")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)
            
        self.set_status("Generating Audio...", "running")
        self.log("Generating Voiceover audio...")
        audio_file = os.path.join(output_dir, "voiceover.wav")
        google_client.generate_tts(script, audio_file, self.config)
        
        self.set_status("Done", "done")
        self.log("Writer Agent finished.")
        return script_file, audio_file

class DirectorAgent(BaseAgent):
    def run(self, topic, script_file, output_dir):
        self.set_status("Breaking down scenes...", "running")
        self.log("Analyzing script to create scene breakdown...")
        
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
            
        paragraphs = [p for p in script.split('\n\n') if p.strip()]
        google_client = GoogleClient(self.config)
        
        self.set_status("Writing prompts...", "running")
        scenes = []
        for i, p in enumerate(paragraphs):
            self.log(f"Generating prompt for Scene {i+1}...")
            prompt = google_client.generate_image_prompt_for_segment("Documentary", topic, p)
            scenes.append({
                "id": i+1,
                "text": p,
                "prompt": prompt
            })
            
        scene_file = os.path.join(output_dir, "scenes.json")
        with open(scene_file, "w") as f:
            json.dump(scenes, f, indent=4)
            
        self.set_status("Done", "done")
        self.log(f"Director Agent finished. Created {len(scenes)} scenes.")
        return scenes

class ImageGenAgent(BaseAgent):
    def run(self, scenes, output_dir):
        self.set_status("Generating Images...", "running")
        wavespeed = WaveSpeedClient(self.config.get("WAVESPEED_AI_KEY"))
        
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        model_id = self.config.get("WAVESPEED_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
        
        image_paths = []
        for scene in scenes:
            self.log(f"Generating image for Scene {scene['id']}...")
            self.set_status(f"Scene {scene['id']}/{len(scenes)}", "running")
            out_img = os.path.join(images_dir, f"scene_{scene['id']}.png")
            try:
                wavespeed.text_to_image(model_id, scene['prompt'], out_img)
            except Exception as e:
                self.log(f"Warning: Image generation failed for scene {scene['id']}: {e}")
                from PIL import Image
                Image.new('RGB', (1920, 1080), color='black').save(out_img)
                
            image_paths.append(out_img)
            
        self.set_status("Done", "done")
        self.log(f"Image Gen Agent finished. Generated {len(image_paths)} initial frames.")
        return image_paths

class VideoGenAgent(BaseAgent):
    def run(self, scenes, image_paths, output_dir):
        self.set_status("Generating Videos...", "running")
        wavespeed = WaveSpeedClient(self.config.get("WAVESPEED_AI_KEY"))
        
        video_dir = os.path.join(output_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        
        video_paths = []
        for i, scene in enumerate(scenes):
            self.log(f"Generating video for Scene {scene['id']}...")
            self.set_status(f"Scene {scene['id']}/{len(scenes)}", "running")
            out_vid = os.path.join(video_dir, f"scene_{scene['id']}.mp4")
            
            try:
                # Using WaveSpeed Text-to-Video as the core animation engine
                wavespeed.text_to_video("tencent/hunyuan-video", scene['prompt'], out_vid, "16:9")
            except Exception as e:
                self.log(f"Warning: Video gen failed for scene {scene['id']}: {e}. Creating a fallback static video...")
                img_path = image_paths[i]
                subprocess.run([
                    "ffmpeg", "-y", "-loop", "1", "-i", img_path, 
                    "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p", out_vid
                ], check=True, capture_output=True)
                
            video_paths.append(out_vid)
            
        self.set_status("Done", "done")
        self.log(f"Video Gen Agent finished. Generated {len(video_paths)} video clips.")
        return video_paths

class EditorAgent(BaseAgent):
    def run(self, video_paths, audio_file, output_dir):
        self.set_status("Assembling...", "running")
        self.log("Stitching video clips together...")
        
        concat_file = os.path.join(output_dir, "concat.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for vp in video_paths:
                f.write(f"file '{vp.replace(os.sep, '/')}'\n")
                
        stitched_video = os.path.join(output_dir, "stitched_no_audio.mp4")
        
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c", "copy", stitched_video
        ], check=True, capture_output=True)
        
        self.log("Overlaying voiceover audio...")
        self.set_status("Adding Audio...", "running")
        final_video = os.path.join(output_dir, "final_production.mp4")
        
        subprocess.run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", stitched_video,
            "-i", audio_file, 
            "-c:v", "copy", "-c:a", "aac", "-shortest", final_video
        ], check=True, capture_output=True)
        
        self.set_status("Done", "done")
        self.log("Editor Agent finished.")
        return final_video

class AgentOrchestrator:
    def __init__(self, config, ui_context):
        self.config = config
        self.ui_context = ui_context
        
    def run(self, topic):
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', topic)
        output_dir = os.path.join("agent_workspace", safe_topic)
        os.makedirs(output_dir, exist_ok=True)
        
        writer = WriterAgent(self.config, self.ui_context, "Writer Agent")
        script_file, audio_file = writer.run(topic, output_dir)
        
        director = DirectorAgent(self.config, self.ui_context, "Director Agent")
        scenes = director.run(topic, script_file, output_dir)
        
        image_gen = ImageGenAgent(self.config, self.ui_context, "Image Gen Agent")
        image_paths = image_gen.run(scenes, output_dir)
        
        video_gen = VideoGenAgent(self.config, self.ui_context, "Video Gen Agent")
        video_paths = video_gen.run(scenes, image_paths, output_dir)
        
        editor = EditorAgent(self.config, self.ui_context, "Editor Agent")
        final_video = editor.run(video_paths, audio_file, output_dir)
        
        self.ui_context.log_to_agent_console("========================================")
        self.ui_context.log_to_agent_console(f"SUCCESS! Final Video saved to: {os.path.abspath(final_video)}")
