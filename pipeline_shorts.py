import os
import re
import json
import logging
import subprocess
import pysubs2
import cv2
import numpy as np
import requests
from server.core.youtube_downloader import download_youtube_video
from pipeline import generate_captions
from api_clients import GoogleClient
from config import load_config

def fetch_b_roll_video(query: str, api_key: str, output_path: str) -> bool:
    if not api_key: return False
    try:
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={query}&video_type=film&per_page=3"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("hits") and len(data["hits"]) > 0:
            video_url = data["hits"][0]["videos"]["medium"]["url"]
            video_data = requests.get(video_url, timeout=20).content
            with open(output_path, "wb") as f:
                f.write(video_data)
            return True
    except Exception as e:
        logging.error(f"Failed to fetch B-Roll: {e}")
    return False

def get_dynamic_crop_filter(video_path: str, start_time: float) -> str:
    """Uses OpenCV to find the speaker's face and returns a dynamic FFmpeg crop string."""
    default_crop = "crop=ih*9/16:ih"
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return default_crop
            
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_time * fps))
        
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        target_w = int(height * 9 / 16)
        
        # Check next 10 frames for a face
        for _ in range(10):
            ret, frame = cap.read()
            if not ret: break
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            if len(faces) > 0:
                largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                x, y, w, h = largest_face
                face_center_x = x + (w // 2)
                crop_x = face_center_x - (target_w // 2)
                crop_x = max(0, min(crop_x, width - target_w))
                cap.release()
                return f"crop={target_w}:{height}:{int(crop_x)}:0"
                
        cap.release()
    except Exception as e:
        logging.error(f"Face tracking error: {e}")
        
    return default_crop

def analyze_youtube_video(url: str, job_id: str, update_job_callback, num_clips: int = 10):
    try:
        config = load_config()
        client = GoogleClient(config)
        output_dir = os.path.join("workspace", f"clipper_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        update_job_callback(job_id, step="Downloading Video", progress=0.1)
        video_path = download_youtube_video(url, output_dir)
        
        update_job_callback(job_id, step="Transcribing Video", progress=0.3)
        # Transcribe without generating an ASS file first, just to get the transcript
        word_timestamps = generate_captions(video_path, None, "English")
        
        if not word_timestamps:
            raise Exception("Transcription failed or returned no words.")
            
        # Build a transcript with timestamps so the LLM knows when things happen
        transcript_chunks = []
        current_chunk_words = []
        chunk_start = 0.0
        
        for w in word_timestamps:
            if not current_chunk_words:
                chunk_start = w['start']
            current_chunk_words.append(w['word'])
            
            # Create a chunk every ~10 seconds
            if w['end'] - chunk_start >= 10.0:
                transcript_chunks.append(f"[{chunk_start:.1f}s - {w['end']:.1f}s]: {' '.join(current_chunk_words)}")
                current_chunk_words = []
                
        if current_chunk_words:
            transcript_chunks.append(f"[{chunk_start:.1f}s - {word_timestamps[-1]['end']:.1f}s]: {' '.join(current_chunk_words)}")
            
        full_transcript = "\n".join(transcript_chunks)
        
        update_job_callback(job_id, step="AI Finding Viral Clips", progress=0.5)
        
        prompt = f"""You are an elite, highly intelligent Social Media Marketer and Content Curator (like OpusClip, but smarter).
Your sole objective is to analyze the following YouTube video transcript and extract the {num_clips} most compelling, high-retention segments (strictly between 30 and 60 seconds).
These clips MUST act as powerful hooks or "trailers" that make viewers instantly curious, forcing them to go watch the full video!

CRITICAL CRITERIA FOR CLIPS:
1. The Hook: The clip must start with an immediate, scroll-stopping statement, shocking fact, or controversial opinion.
2. The Value / Tension: It must build extreme curiosity, tell a crazy story, or drop high-value knowledge.
3. The Cliffhanger: The clip should ideally end on a cliffhanger, unresolved question, or mind-blowing conclusion that leaves the viewer desperately wanting more context from the full video.

Return your response ONLY as a JSON list of objects, with no markdown formatting or extra text.
Each object must have "start" (seconds), "end" (seconds), "title" (clickbaity title), "score" (integer 1-100 indicating virality potential), and "reason" (short 1-sentence explanation of why it will go viral).
Do not hallucinate timestamps. Use the exact timestamps provided in the transcript brackets [start - end].

Transcript snippet (first 15000 chars):
{full_transcript[:15000]}
"""
        response = client._generate_text(prompt).strip()
        # Clean up possible markdown
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
            
        clips_data = json.loads(response.strip())
        
        if not clips_data or len(clips_data) == 0:
            raise Exception("AI could not find any clips.")
            
        update_job_callback(job_id, step="Awaiting Selection", progress=0.6, result=json.dumps({"type": "selection", "clips": clips_data, "video_path": video_path}))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

def render_youtube_clips(job_id: str, video_path: str, selected_clips: list, update_job_callback):
    try:
        config = load_config()
        client = GoogleClient(config)
        output_dir = os.path.join("workspace", f"clipper_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        update_job_callback(job_id, step="Cropping & Captioning", progress=0.7)
        
        generated_clips = []
        total_clips = len(selected_clips)
        
        for idx, clip in enumerate(selected_clips):
            try:
                start = float(clip.get("start", 0))
                end = float(clip.get("end", 30))
                title = str(clip.get("title") or f"Clip {idx+1}")
                
                safe_title = re.sub(r'[^a-zA-Z0-9_]', '', title.replace(" ", "_"))
                clip_name = f"{safe_title}.mp4"
            except (ValueError, TypeError) as e:
                logging.warning(f"Skipping malformed clip data: {clip} - {e}")
                continue
                
            out_path = os.path.join(output_dir, clip_name)
            
            # Detect face and get dynamic crop filter
            crop_filter = get_dynamic_crop_filter(video_path, start)
            
            # Use FFmpeg to slice AND crop dynamically (and force 720x1280 resolution)
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
                "-i", video_path,
                "-vf", f"{crop_filter},scale=720:1280",
                "-c:v", "libx264", "-c:a", "aac",
                out_path
            ], check=True, capture_output=True)
            
            # --- PHASE 4: AUTO B-ROLL INJECTION ---
            try:
                broll_prompt = f"Analyze this clip title: '{title}'. Determine a 1-2 word visual subject for B-Roll. If it's a person talking about abstract concepts, return 'none'. Otherwise, return the exact search term (e.g., 'space', 'bitcoin', 'running'). Return ONLY the search term in lowercase without punctuation."
                broll_subject = client._generate_text(broll_prompt).strip().lower()
                
                has_broll = False
                b_roll_path = os.path.join(output_dir, f"broll_{idx}.mp4")
                pixabay_key = config.get("PIXABAY_API_KEY", "")
                
                if broll_subject and broll_subject != "none" and pixabay_key:
                    has_broll = fetch_b_roll_video(broll_subject, pixabay_key, b_roll_path)
                    
                if has_broll:
                    b_roll_overlay_path = os.path.join(output_dir, f"broll_overlay_{idx}.mp4")
                    # Overlay B-Roll from seconds 2 to 5 over the 720x1280 base video
                    subprocess.run([
                        "ffmpeg", "-y", "-i", out_path, "-i", b_roll_path,
                        "-filter_complex", 
                        "[1:v]crop=ih*9/16:ih,scale=720:1280[broll];[0:v][broll]overlay=enable='between(t,2,5)'",
                        "-c:a", "copy",
                        b_roll_overlay_path
                    ], check=True, capture_output=True)
                    out_path = b_roll_overlay_path
            except Exception as e:
                logging.error(f"B-Roll injection failed for {clip_name}: {e}")
            
            theme = config.get("CAPTION_THEME", "default")
            font = config.get("CAPTION_FONT", "Arial")
            font_size = int(config.get("CAPTION_FONT_SIZE", 22))
            
            if theme == "viral_yellow":
                primarycolor = pysubs2.Color(255, 255, 0, 255)
                backcolor = pysubs2.Color(0, 0, 0, 255)
                outline = 2.0
            elif theme == "neon_cyber":
                primarycolor = pysubs2.Color(0, 255, 255, 255)
                backcolor = pysubs2.Color(255, 0, 255, 100)
                outline = 1.0
            elif theme == "black_white":
                primarycolor = pysubs2.Color(0, 0, 0, 255)
                backcolor = pysubs2.Color(255, 255, 255, 255)
                outline = 2.0
            else:
                primarycolor = pysubs2.Color(255, 255, 255, 255)
                backcolor = pysubs2.Color(0, 0, 0, 150)
                outline = 1.5

            ass_path = os.path.join(output_dir, f"{safe_title}.ass")
            generate_captions(out_path, ass_path, "English", style_opts={
                "fontname": font, 
                "fontsize": font_size, 
                "alignment": 2, 
                "marginv": 60,
                "bold": True,
                "outline": outline,
                "shadow": 1,
                "primarycolor": primarycolor,
                "backcolor": backcolor
            })
            
            final_out_path = os.path.join(output_dir, f"Final_{clip_name}")
            subs_path = os.path.abspath(ass_path).replace('\\', '/').replace(':', '\\:')
            
            subprocess.run([
                "ffmpeg", "-y", "-i", out_path,
                "-vf", f"subtitles='{subs_path}'",
                "-c:v", "libx264", "-c:a", "copy",
                final_out_path
            ], check=True, capture_output=True)
            
            generated_clips.append({
                "title": title,
                "path": final_out_path.replace("\\", "/")
            })
            
            progress = 0.7 + (0.3 * ((idx + 1) / total_clips))
            update_job_callback(job_id, step=f"Rendered {idx+1}/{total_clips} Clips", progress=progress)
            
        update_job_callback(job_id, step="Finished", progress=1.0, result=json.dumps({"type": "finished", "clips": generated_clips}))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Clipper Error: {e}", exc_info=True)
        update_job_callback(job_id, step="Failed", progress=1.0, error=str(e))
