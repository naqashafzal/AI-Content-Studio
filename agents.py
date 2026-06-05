import os
import time
import json
import logging
import wave
import re
import subprocess
import threading
import concurrent.futures
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
            
        # HITL Checkpoint: Script Approval
        import main
        self.log("Waiting for user approval of the script...")
        self.set_status("Waiting for Approval...", "running")
        resume_event = threading.Event()
        self.ui_context.after(0, lambda: main.ScriptEditorWindow(self.ui_context, script, script_file, resume_event))
        resume_event.wait()
        
        # Read the potentially edited script
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
            
        self.set_status("Generating Audio...", "running")
        self.log("Generating Voiceover audio...")
        audio_file = os.path.join(output_dir, "voiceover.wav")
        google_client.generate_tts(script, audio_file, self.config)
        
        self.set_status("Done", "done")
        self.log("Writer Agent finished.")
        return script_file, audio_file

class DirectorAgent(BaseAgent):
    def run(self, topic, script_file, output_dir, style="Cinematic Documentary"):
        self.set_status("Breaking down scenes...", "running")
        self.log(f"Analyzing script for a {style} production...")
        
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
            
        paragraphs = [p for p in script.split('\n\n') if p.strip()]
        google_client = GoogleClient(self.config)
        
        self.set_status("Writing prompts...", "running")
        self.log("Dispatching prompt generation tasks concurrently...")
        scenes = []
        
        def process_paragraph(i, p):
            prompt = google_client.generate_image_prompt_for_segment(style, topic, p)
            return {"id": i+1, "text": p, "prompt": prompt}

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_paragraph, i, p) for i, p in enumerate(paragraphs)]
            for future in concurrent.futures.as_completed(futures):
                scenes.append(future.result())
                
        scenes.sort(key=lambda x: x["id"])
        scene_file = os.path.join(output_dir, "scenes.json")
        with open(scene_file, "w") as f:
            json.dump(scenes, f, indent=4)
            
        # HITL Checkpoint: Storyboard Approval
        import main
        self.log("Waiting for user approval of the visual prompts...")
        self.set_status("Waiting for Approval...", "running")
        resume_event = threading.Event()
        self.ui_context.after(0, lambda: main.AgentStoryboardWindow(self.ui_context, scenes, scene_file, resume_event))
        resume_event.wait()
        
        # Read the potentially edited scenes
        with open(scene_file, "r", encoding="utf-8") as f:
            scenes = json.load(f)
            
        self.set_status("Done", "done")
        self.log(f"Director Agent finished. Created {len(scenes)} scenes.")
        return scenes

class ImageGenAgent(BaseAgent):
    def run(self, scenes, output_dir, aspect_ratio="16:9"):
        self.set_status("Generating Images...", "running")
        wavespeed = WaveSpeedClient(self.config.get("WAVESPEED_AI_KEY"))
        
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        model_id = self.config.get("WAVESPEED_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
        
        self.log("Dispatching image generation tasks concurrently...")
        image_paths_dict = {}
        
        def generate_image(scene):
            self.log(f"Generating image for Scene {scene['id']} ({aspect_ratio})...")
            out_img = os.path.join(images_dir, f"scene_{scene['id']}.png")
            try:
                wavespeed.text_to_image(model_id, scene['prompt'], out_img)
            except Exception as e:
                self.log(f"Warning: Image generation failed for scene {scene['id']}: {e}")
                from PIL import Image
                Image.new('RGB', (1920, 1080), color='black').save(out_img)
            return scene['id'], out_img

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_image, scene) for scene in scenes]
            for future in concurrent.futures.as_completed(futures):
                sid, path = future.result()
                image_paths_dict[sid] = path

        image_paths = [image_paths_dict[s['id']] for s in scenes]
        self.set_status("Done", "done")
        self.log(f"Image Gen Agent finished. Generated {len(image_paths)} initial frames.")
        return image_paths

class VideoGenAgent(BaseAgent):
    def run(self, scenes, image_paths, output_dir, aspect_ratio="16:9"):
        self.set_status("Generating Videos...", "running")
        wavespeed = WaveSpeedClient(self.config.get("WAVESPEED_AI_KEY"))
        
        video_dir = os.path.join(output_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        
        self.log("Dispatching video generation tasks concurrently...")
        video_paths_dict = {}
        
        def generate_video(scene, img_path):
            self.log(f"Generating video for Scene {scene['id']} ({aspect_ratio})...")
            out_vid = os.path.join(video_dir, f"scene_{scene['id']}.mp4")
            try:
                wavespeed.text_to_video("tencent/hunyuan-video", scene['prompt'], out_vid, aspect_ratio)
            except Exception as e:
                self.log(f"Warning: Video gen failed for scene {scene['id']}: {e}. Creating a fallback static video...")
                subprocess.run([
                    "ffmpeg", "-y", "-loop", "1", "-i", img_path, 
                    "-c:v", "libx264", "-preset", "ultrafast", "-t", "5", "-pix_fmt", "yuv420p", out_vid
                ], check=True, capture_output=True)
            return scene['id'], out_vid

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_video, scenes[i], image_paths[i]) for i in range(len(scenes))]
            for future in concurrent.futures.as_completed(futures):
                sid, path = future.result()
                video_paths_dict[sid] = path

        video_paths = [video_paths_dict[s['id']] for s in scenes]
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
    def __init__(self, config, ui_context, settings=None):
        self.config = config
        self.ui_context = ui_context
        self.settings = settings or {}
        
    def run(self, topic):
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', topic)
        output_dir = os.path.join("agent_workspace", safe_topic)
        os.makedirs(output_dir, exist_ok=True)
        
        writer = WriterAgent(self.config, self.ui_context, "Writer Agent")
        script_file, audio_file = writer.run(topic, output_dir)
        
        director_style = self.settings.get("director_style", "Cinematic Documentary")
        aspect_ratio = self.settings.get("aspect_ratio", "16:9").split(" ")[0] # extract "16:9" from "16:9 (YouTube)"
        
        director = DirectorAgent(self.config, self.ui_context, "Director Agent")
        scenes = director.run(topic, script_file, output_dir, style=director_style)
        
        image_gen = ImageGenAgent(self.config, self.ui_context, "Image Gen Agent")
        image_paths = image_gen.run(scenes, output_dir, aspect_ratio=aspect_ratio)
        
        video_gen = VideoGenAgent(self.config, self.ui_context, "Video Gen Agent")
        video_paths = video_gen.run(scenes, image_paths, output_dir, aspect_ratio=aspect_ratio)
        
        editor = EditorAgent(self.config, self.ui_context, "Editor Agent")
        final_video = editor.run(video_paths, audio_file, output_dir)
        
        if self.settings.get("auto_captions"):
            self.ui_context.log_to_agent_console("Running Auto-Captions Pipeline...")
            import pipeline
            captioned_video = os.path.join(output_dir, "final_production_captioned.mp4")
            # Create a mock update callback for the pipeline
            def dummy_status(p, t, s): pass
            try:
                caption_style = self.config.get("CAPTION_STYLE", "Cinematic")
                from api_clients import STYLE_PROFILES
                opts = STYLE_PROFILES.get(caption_style, STYLE_PROFILES["Cinematic"])
                pipeline.generate_captions(final_video, audio_file, output_dir, dummy_status, style_opts=opts)
                # The pipeline saves the file inside output_dir, let's just point final_video to it
                final_video = os.path.join(output_dir, "final_podcast_video_subtitled.mp4")
            except Exception as e:
                self.ui_context.log_to_agent_console(f"Auto-captioning failed: {e}")
        
        self.ui_context.log_to_agent_console("========================================")
        self.ui_context.log_to_agent_console(f"SUCCESS! Final Video saved to: {os.path.abspath(final_video)}")
