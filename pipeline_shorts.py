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

def render_scene_aware_clip(video_path: str, start_time: float, end_time: float, out_path: str):
    """OpusClip-style AI Active Speaker Tracking using Scene-Aware Cropping."""
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        segment_path = tmp.name
        
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start_time), "-to", str(end_time),
        "-i", video_path, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", segment_path
    ], check=True, capture_output=True)
    
    cap = cv2.VideoCapture(segment_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_w = int(height * 9 / 16)
    
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    cuts = []
    current_cut_start = 0.0
    current_crop_x = None
    
    frame_idx = 0
    skip_frames = int(fps / 2) # Sample twice per second
    
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        
        if len(faces) > 0:
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            x, y, w, h = largest_face
            crop_x = max(0, min((x + w // 2) - target_w // 2, width - target_w))
            
            if current_crop_x is None:
                current_crop_x = crop_x
            elif abs(crop_x - current_crop_x) > (width * 0.15):
                cut_time = frame_idx / fps
                cuts.append({"start": current_cut_start, "end": cut_time, "crop_x": current_crop_x})
                current_cut_start = cut_time
                current_crop_x = crop_x
                    
        frame_idx += skip_frames
        
    cap.release()
    
    duration = end_time - start_time
    if current_crop_x is None:
        current_crop_x = (width - target_w) // 2
    cuts.append({"start": current_cut_start, "end": duration, "crop_x": current_crop_x})
    
    if len(cuts) == 1:
        subprocess.run([
            "ffmpeg", "-y", "-i", segment_path,
            "-vf", f"crop={target_w}:{height}:{int(cuts[0]['crop_x'])}:0,scale=720:1280",
            "-c:v", "libx264", "-c:a", "copy", out_path
        ], check=True, capture_output=True)
    else:
        filter_parts = []
        concat_inputs = ""
        for i, cut in enumerate(cuts):
            filter_parts.append(f"[0:v]trim=start={cut['start']}:end={cut['end']},setpts=PTS-STARTPTS,crop={target_w}:{height}:{int(cut['crop_x'])}:0,scale=720:1280[v{i}]")
            concat_inputs += f"[v{i}]"
            
        filter_parts.append(f"{concat_inputs}concat=n={len(cuts)}:v=1:a=0[outv]")
        subprocess.run([
            "ffmpeg", "-y", "-i", segment_path,
            "-filter_complex", ";".join(filter_parts),
            "-map", "[outv]", "-map", "0:a",
            "-c:v", "libx264", "-c:a", "copy", out_path
        ], check=True, capture_output=True)
        
    os.remove(segment_path)

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
        
        prompt = f"""You are an elite, highly intelligent Social Media Marketer and Content Curator.
Your sole objective is to analyze the following YouTube video transcript and extract the {num_clips} most compelling, high-retention segments (strictly between 30 and 60 seconds).

CRITICAL CRITERIA FOR CLIPS:
1. The Hook: Immediate, scroll-stopping statement.
2. The Value: Builds extreme curiosity or drops high-value knowledge.
3. The Cliffhanger: Ends on a cliffhanger wanting more.

Return your response ONLY as a JSON list of objects, with no markdown formatting.
Each object must match this schema:
{{
  "start": float (seconds),
  "end": float (seconds),
  "title": "Clickbaity short title",
  "score": int (1-100 overall virality),
  "hook_score": int (1-100),
  "retention_score": int (1-100),
  "reason": "1 sentence why it's viral",
  "seo_title": "Highly optimized YouTube Shorts Title #shorts",
  "seo_description": "Engaging description...",
  "seo_tags": "shorts, viral, podcast",
  "broll": [
    {{"start_offset": int (seconds from clip start), "end_offset": int, "subject": "visual search term (e.g. hacking, money)"}}
  ]
}}
Do not hallucinate timestamps. The 'broll' array should contain 1 to 3 moments where a visual overlay would increase retention.

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
            
            # Use OpusClip-style AI Active Speaker Tracking
            render_scene_aware_clip(video_path, start, end, out_path)
            
            # --- PHASE 4: DYNAMIC B-ROLL TIMELINE ---
            try:
                pixabay_key = config.get("PIXABAY_API_KEY", "")
                broll_timeline = clip.get("broll", [])
                
                if pixabay_key and broll_timeline:
                    current_vid = out_path
                    for b_idx, b_item in enumerate(broll_timeline):
                        b_subj = str(b_item.get("subject", "")).lower()
                        b_start = b_item.get("start_offset", 2)
                        b_end = b_item.get("end_offset", 5)
                        
                        if not b_subj or b_subj == "none": continue
                        
                        b_roll_path = os.path.join(output_dir, f"broll_{idx}_{b_idx}.mp4")
                        if fetch_b_roll_video(b_subj, pixabay_key, b_roll_path):
                            b_roll_overlay_path = os.path.join(output_dir, f"broll_overlay_{idx}_{b_idx}.mp4")
                            subprocess.run([
                                "ffmpeg", "-y", "-i", current_vid, "-i", b_roll_path,
                                "-filter_complex", 
                                f"[1:v]crop=ih*9/16:ih,scale=720:1280[broll];[0:v][broll]overlay=enable='between(t,{b_start},{b_end})'",
                                "-c:a", "copy",
                                b_roll_overlay_path
                            ], check=True, capture_output=True)
                            current_vid = b_roll_overlay_path
                    out_path = current_vid
            except Exception as e:
                logging.error(f"Dynamic B-Roll injection failed for {clip_name}: {e}")
                
            # --- PHASE 4.5: AUDIO DUCKING (BGM) ---
            try:
                bgm_path = "workspace/bgm.mp3"
                if os.path.exists(bgm_path):
                    bgm_out_path = os.path.join(output_dir, f"bgm_{clip_name}")
                    subprocess.run([
                        "ffmpeg", "-y", "-i", out_path, "-i", bgm_path,
                        "-filter_complex",
                        "[1:a]volume=0.08[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2",
                        "-c:v", "copy",
                        bgm_out_path
                    ], check=True, capture_output=True)
                    out_path = bgm_out_path
            except Exception as e:
                logging.error(f"Audio Ducking failed for {clip_name}: {e}")
            
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
                "path": final_out_path.replace("\\", "/"),
                "seo_title": clip.get("seo_title", title),
                "seo_description": clip.get("seo_description", ""),
                "seo_tags": clip.get("seo_tags", ""),
            })
            
            progress = 0.7 + (0.3 * ((idx + 1) / total_clips))
            update_job_callback(job_id, step=f"Rendered {idx+1}/{total_clips} Clips", progress=progress)
            
        update_job_callback(job_id, step="Finished", progress=1.0, result=json.dumps({"type": "finished", "clips": generated_clips}))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Clipper Error: {e}", exc_info=True)
        update_job_callback(job_id, step="Failed", progress=1.0, error=str(e))
