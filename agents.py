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

class TrendAgent(BaseAgent):
    def find_viral_topics(self):
        self.set_status("Scanning News...", "running")
        self.log("Fetching top headlines for viral topics...")
        news_client = NewsApiClient(self.config.get("NEWS_API_KEY"))
        headlines = news_client.get_top_headlines(category="technology")
        if not headlines:
            headlines = news_client.get_top_headlines(category="general")
            
        if not headlines:
            self.set_status("Failed", "error")
            return ["AI Taking Over The World", "The Future of Quantum Computing", "Mars Colonization Secrets"]
            
        context = "\n".join([f"- {h}" for h in headlines[:15]])
        prompt = f"Analyze these current news headlines:\n{context}\n\nBased on these, generate exactly 3 highly engaging, viral debate topics suitable for a YouTube podcast. Output them as a numbered list (1., 2., 3.) with no extra text. Keep them punchy and controversial."
        
        google_client = GoogleClient(self.config)
        self.log("Asking AI to synthesize topics...")
        response = google_client._generate_text(prompt)
        
        topics = []
        for line in response.split('\n'):
            line = line.strip()
            if line and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                # Strip the number prefix
                topic = re.sub(r'^\d+\.\s*', '', line).strip()
                # Remove quotes if they exist
                topic = topic.strip('"').strip("'")
                topics.append(topic)
                
        # Fallback if parsing fails
        if len(topics) < 3:
            topics = ["The Hidden Dangers of AI", "Why Tech Giants are Failing", "The Next Big Tech Revolution"]
            
        self.set_status("Topics Ready", "done")
        self.log("Trend analysis complete.")
        return topics[:3]

class WriterAgent(BaseAgent):
    def generate_script(self, topic, output_dir):
        self.set_status("Writing Script...", "running")
        self.log(f"Starting research on: {topic}")
        google_client = GoogleClient(self.config)
        news_client = NewsApiClient(self.config.get("NEWS_API_KEY"))
        research = google_client.deep_research(topic, "English", news_client)
        
        self.log("Initializing Host and Guest AI instances for debate...")
        host_persona = self.config.get("HOST_PERSONA", "A knowledgeable and enthusiastic host.")
        guest_persona = self.config.get("GUEST_PERSONA", "A skeptical but curious guest.")
        host_name = self.config.get("HOST_NAME", "Alex")
        guest_name = self.config.get("GUEST_NAME", "Maya")
        
        script_lines = []
        host_system = f"You are {host_name}, {host_persona}. You are hosting a podcast about {topic}."
        guest_system = f"You are {guest_name}, {guest_persona}. You are a guest on {host_name}'s podcast discussing {topic}."
        
        context_history = f"Topic: {topic}\nResearch: {research[:2000]}\n\n"
        
        self.log("Round 1: Host Introduction")
        prompt = f"{host_system}\nContext: {context_history}\nStart the podcast, introduce the topic and the guest ({guest_name}), and state a strong opening opinion (max 3 sentences). Output ONLY what you say."
        host_line = google_client._generate_text(prompt).strip()
        script_lines.append(f"[{host_name}] {host_line}")
        context_history += f"[{host_name}] {host_line}\n"
        
        for round_num in range(2, 4):
            self.log(f"Round {round_num}: Guest responds")
            prompt = f"{guest_system}\nContext: {context_history}\nRespond to the host. Ask a challenging question or provide a counter-point based on the research (max 3 sentences). Output ONLY what you say, without your name."
            guest_line = google_client._generate_text(prompt).strip()
            script_lines.append(f"[{guest_name}] {guest_line}")
            context_history += f"[{guest_name}] {guest_line}\n"
            
            self.log(f"Round {round_num}: Host responds")
            prompt = f"{host_system}\nContext: {context_history}\nRespond to the guest's point, using the research to back up your claims. Keep the conversation moving forward (max 3 sentences). Output ONLY what you say, without your name."
            host_line = google_client._generate_text(prompt).strip()
            script_lines.append(f"[{host_name}] {host_line}")
            context_history += f"[{host_name}] {host_line}\n"
            
        self.log("Round 4: Conclusion")
        prompt = f"{host_system}\nContext: {context_history}\nWrap up the podcast episode. Thank the guest and the audience, and sign off (max 2 sentences). Output ONLY what you say."
        host_line = google_client._generate_text(prompt).strip()
        script_lines.append(f"[{host_name}] {host_line}")
        
        script = "\n\n".join(script_lines)
        script_file = os.path.join(output_dir, "script.txt")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)
        
        self.set_status("Script Ready", "done")
        return script_file

    def generate_audio(self, script_file, output_dir):
        self.set_status("Generating Audio...", "running")
        self.log("Generating Voiceover audio...")
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
            
        google_client = GoogleClient(self.config)
        audio_file = os.path.join(output_dir, "voiceover.wav")
        google_client.generate_tts(script, audio_file, self.config)
        
        self.set_status("Audio Done", "done")
        self.log("Writer Agent finished.")
        return audio_file

    def run(self, topic, output_dir):
        script_file = self.generate_script(topic, output_dir)
        # Note: In legacy main.py mode, this will no longer pause for Tkinter popups. It will run headlessly.
        audio_file = self.generate_audio(script_file, output_dir)
        return script_file, audio_file

class DirectorAgent(BaseAgent):
    def generate_storyboard(self, topic, script_file, output_dir, style="Cinematic Documentary"):
        self.set_status("Breaking down scenes...", "running")
        self.log(f"Analyzing script for a {style} production...")
        
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
            
        paragraphs = [p for p in script.split('\n\n') if p.strip()]
        google_client = GoogleClient(self.config)
        
        self.set_status("Writing prompts...", "running")
        self.log("Batch generating prompts via LLM...")
        scenes = []
        
        # New approach: Batch generate prompts
        prompts = google_client.generate_image_prompts_batch(style, topic, paragraphs)
        for i, (p, prompt) in enumerate(zip(paragraphs, prompts)):
            scenes.append({"id": i+1, "text": p, "prompt": prompt})
                
        scenes.sort(key=lambda x: x["id"])
        scene_file = os.path.join(output_dir, "scenes.json")
        with open(scene_file, "w") as f:
            json.dump(scenes, f, indent=4)
            
        self.set_status("Storyboard Ready", "done")
        self.log(f"Director Agent created {len(scenes)} scenes.")
        return scene_file

    def run(self, topic, script_file, output_dir, style="Cinematic Documentary"):
        scene_file = self.generate_storyboard(topic, script_file, output_dir, style)
        with open(scene_file, "r", encoding="utf-8") as f:
            scenes = json.load(f)
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
            
            # 1. Try Pixabay (Stock Footage)
            from api_clients import PixabayClient
            pixabay_key = self.config.get("PIXABAY_API_KEY", "")
            if pixabay_key:
                pixabay = PixabayClient(pixabay_key)
                # Use a simplified version of the prompt for search (first 5 words)
                search_query = " ".join(scene['prompt'].split()[:5])
                self.log(f"Attempting to fetch stock footage for: {search_query}")
                success = pixabay.download_video(search_query, out_vid)
                if success:
                    return scene['id'], out_vid
                    
            # 2. Fallback to WaveSpeed AI Video Generation
            try:
                self.log("Pixabay unavailable or no match. Using WaveSpeed AI...")
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
            try:
                captions_file = os.path.join(output_dir, "captions.ass")
                caption_style = self.config.get("CAPTION_STYLE", "Podcast")
                from api_clients import STYLE_PROFILES
                opts = STYLE_PROFILES.get(caption_style, STYLE_PROFILES.get("Podcast", {}))
                pipeline.generate_captions(audio_file, captions_file, self.config.get("PODCAST_LANGUAGE", "English"), style_opts=opts)
                
                captioned_video = os.path.join(output_dir, "final_production_captioned.mp4")
                subs_path = os.path.abspath(captions_file).replace('\\', '/').replace(':', '\\:')
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", final_video,
                    "-vf", f"subtitles='{subs_path}'",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "copy",
                    captioned_video
                ], check=True, capture_output=True, text=True, encoding='utf-8')
                final_video = captioned_video
            except Exception as e:
                self.ui_context.log_to_agent_console(f"Auto-captioning failed: {e}")
        
        self.ui_context.log_to_agent_console("========================================")
        self.ui_context.log_to_agent_console(f"SUCCESS! Final Video saved to: {os.path.abspath(final_video)}")
