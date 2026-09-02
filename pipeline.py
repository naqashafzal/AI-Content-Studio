"""
pipeline.py

This module defines the main content creation pipeline, fully implementing
all features from the original script in a structured and robust class.

The Pipeline class orchestrates the entire workflow, from research and scriptwriting
to audio/video generation, captioning, and final processing. It utilizes the
API client classes and the configuration module to customize its behavior.
"""

import os
import re
import time
import json
import logging
import subprocess
import wave
import unicodedata

# Third-party libraries
from pydub import AudioSegment
import whisper
import pysubs2

# Import the API client classes
from api_clients import GoogleClient, WaveSpeedClient, NewsApiClient, PixabayClient

# --- Constants for Pipeline Flow ---
PIPELINE_STEPS = [
    "Deep Research",
    "Fact Check Research",
    "Revise Research",
    "Podcast Script",
    "Generate Thumbnail",
    "Analyze Tone",
    "Audio (TTS)",
    "Generate Timed Images",
    "Video Generation",
    "Add Background Music", 
    "Create Final Video",
    "Generate SEO Metadata", # <-- CORRECTED ORDER
    "Generate Timestamps",   # <-- CORRECTED ORDER
    "Generate Snippets"
]

# --- Helper Functions (ported from original script) ---

def format_timestamp(seconds: float) -> str:
    """Converts seconds (float) into MM:SS format."""
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02}:{seconds:02}"

def sanitize_for_tts(text: str) -> str:
    """Removes emojis and normalizes text for TTS processing."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002600-\U000026FF"  # Miscellaneous Symbols
        "\U00002700-\U000027BF"  # Dingbats
        "]+", re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace('*', '')
    text = re.sub(r'[ \t\r\f\v]+', ' ', text).replace('\xa0', ' ').strip()
    return text.replace('“', '"').replace('”', '"').replace('’', "'").replace('—', '-').replace('–', '-')

def mix_audio_with_music(podcast_path, music_path, output_path, music_volume_db=-15):
    """Mixes a podcast audio file with a background music file."""
    logging.info("🎵 Mixing background music...")
    try:
        podcast_audio = AudioSegment.from_file(podcast_path)
        music_audio = AudioSegment.from_file(music_path)
        music_audio = music_audio + music_volume_db
        if len(music_audio) < len(podcast_audio):
            music_audio = music_audio * (len(podcast_audio) // len(music_audio) + 1)
        music_audio = music_audio[:len(podcast_audio)]
        mixed_audio = podcast_audio.overlay(music_audio, position=0)
        mixed_audio.export(output_path, format="mp3")
        logging.info(f"✅ Audio mixed and saved to {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"❌ Error mixing audio: {e}")
        return podcast_path

def generate_captions(audio_file, captions_file, language: str, style_opts: dict = None):
    """Transcribes audio and generates a styled ASS caption file, returning word timestamps."""
    logging.info("Transcribing audio for captions (this may take a moment)...")
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_file, word_timestamps=True, language=language)
        
        all_word_timestamps = []
        for segment in result.get("segments", []):
            all_word_timestamps.extend(segment.get("words", []))

        logging.info(f"Whisper transcribed {len(all_word_timestamps)} words.")

        if captions_file:
            style_opts = style_opts or {}
            subs = pysubs2.SSAFile()
            style = pysubs2.SSAStyle(
                fontname=style_opts.get("fontname", "Arial Black"),
                fontsize=style_opts.get("fontsize", 46),
                primarycolor=style_opts.get("primarycolor", pysubs2.Color(255, 255, 0, 0)),
                outlinecolor=style_opts.get("outlinecolor", pysubs2.Color(0, 0, 0, 0)),
                backcolor=style_opts.get("backcolor", pysubs2.Color(0, 0, 0, 180)),
                bold=style_opts.get("bold", True),
                outline=style_opts.get("outline", 3),
                shadow=style_opts.get("shadow", 1),
                alignment=style_opts.get("alignment", 2),
                marginv=style_opts.get("marginv", 40),
                marginl=style_opts.get("marginl", 20),
                marginr=style_opts.get("marginr", 20),
            )
            subs.styles["Default"] = style
            
            # Hormozi-style Dictionary
            emojis = {
                "MONEY": "💰", "CASH": "💰", "DOLLAR": "💰", "REVENUE": "💰", "MILLION": "💰", "BILLION": "💰",
                "VIRAL": "🔥", "EXPLOSIVE": "🔥", "FIRE": "🔥",
                "SECRET": "🤫", "HIDDEN": "🤫", "TRUTH": "🤫",
                "CRAZY": "🤯", "INSANE": "🤯", "MIND": "🤯",
                "TIME": "⏱️", "FAST": "⏱️", "QUICK": "⏱️",
                "HACK": "🛠️", "WOW": "😲"
            }
            
            primary = style_opts.get("primarycolor", pysubs2.Color(0, 255, 255, 255))
            active_color = f"{{\\c&H{primary.b:02X}{primary.g:02X}{primary.r:02X}&}}"
            inactive_color = "{\\c&HFFFFFF&}"
            
            # Group into lines of ~4 words
            chunks = []
            current_chunk = []
            for word in all_word_timestamps:
                raw = word['word'].strip().upper()
                if not raw: continue
                current_chunk.append(word)
                # break chunk if 4 words reached or there is a pause > 0.5s
                if len(current_chunk) >= 4 or (word['end'] - word['start'] > 0.5):
                    chunks.append(current_chunk)
                    current_chunk = []
            if current_chunk:
                chunks.append(current_chunk)
                
            for chunk in chunks:
                for i, active_word in enumerate(chunk):
                    w_start_ms = int(active_word['start'] * 1000)
                    w_end_ms = int(active_word['end'] * 1000)
                    
                    line_parts = []
                    for j, w in enumerate(chunk):
                        raw_text = w['word'].strip().upper()
                        clean = re.sub(r'[^A-Z]', '', raw_text)
                        
                        part = raw_text
                        if clean in emojis:
                            part = f"{part} {emojis[clean]}"
                            
                        if j == i:
                            # Highlight active word
                            part = f"{active_color}{part}{{\\r}}"
                        else:
                            # Inactive words are white
                            part = f"{inactive_color}{part}{{\\r}}"
                            
                        line_parts.append(part)
                        
                    subs.append(pysubs2.SSAEvent(
                        start=pysubs2.make_time(ms=w_start_ms),
                        end=pysubs2.make_time(ms=w_end_ms),
                        text=" ".join(line_parts),
                        style="Default"
                    ))
                
            subs.save(captions_file)
            logging.info(f"Captions file saved: {captions_file} ({len(subs)} events)")
            
        return all_word_timestamps
    except Exception as e:
        logging.error(f"Whisper transcription failed: {e}", exc_info=True)
        return []

def sanitize_ffmpeg_path(path: str) -> str:
    """
    Sanitizes a file path for use in an ffmpeg filtergraph, especially for the 'ass' filter on Windows.
    """
    path = os.path.normpath(path)
    path = path.replace('\\', '/')
    if ':' in path:
        path = path.replace(':', '\\:', 1)
    return path


class Pipeline:
    """Orchestrates the entire content creation process."""

    def __init__(self, config, stop_event, status_callback, seo_callback=None, on_finish_callback=None, timestamps_callback=None, on_script_generated=None):
        self.config = config
        self.stop_event = stop_event
        self.update_status = status_callback
        self.update_seo = seo_callback
        self.on_finish = on_finish_callback
        self.update_timestamps = timestamps_callback # New callback
        self.on_script_generated = on_script_generated
        self.google_client = GoogleClient(config)
        self.wavespeed_client = WaveSpeedClient(config.get("WAVESPEED_API_KEY"))
        self.news_client = NewsApiClient(config.get("NEWS_API_KEY"))
        self.pixabay_client = PixabayClient(config.get("PIXABAY_API_KEY"))

    def _check_stop(self):
        if self.stop_event.is_set():
            raise InterruptedError("Pipeline execution stopped by user.")

    def _wait(self):
        delay = self.config.get("API_DELAY", 2)
        if delay > 0:
            logging.info(f"Waiting for {delay} seconds...")
            time.sleep(delay)

    def _get_audio_length(self, path):
        try:
            with wave.open(path, "rb") as wf:
                return wf.getnframes() / float(wf.getframerate())
        except Exception:
            try:
                audio = AudioSegment.from_file(path)
                return len(audio) / 1000.0
            except Exception:
                return 0
    
    def _get_step_list(self, start_point: str):
        """Returns a list of steps to execute based on the start point."""
        try:
            start_index = PIPELINE_STEPS.index(start_point)
            return PIPELINE_STEPS[start_index:]
        except ValueError:
            logging.error(f"Invalid start point '{start_point}'. Defaulting to start.")
            return PIPELINE_STEPS

    def run(self, topic: str, start_point: str):
        success = False
        self.word_timestamps_for_images = []
        try:
            logging.info(f"Starting pipeline for topic: '{topic}' from step: '{start_point}'")
            safe_topic = re.sub(r'[\\/:*?"<>|]', '', topic)
            output_dir = safe_topic
            os.makedirs(output_dir, exist_ok=True)
            
            # --- File Paths ---
            summary_file = os.path.join(output_dir, "summary.txt")
            script_file = os.path.join(output_dir, "podcast_script.txt")
            audio_file = os.path.join(output_dir, "podcast.wav")
            mixed_audio_file = os.path.join(output_dir, "podcast_with_music.mp3")
            bg_video_file = os.path.join(output_dir, "background.mp4")
            segment_images_dir = os.path.join(output_dir, "segment_images")
            os.makedirs(segment_images_dir, exist_ok=True)
            final_video_file = os.path.join(output_dir, "final_podcast_video.mp4")
            image_file = os.path.join(output_dir, "generated_image.png") # Final thumbnail path
            captions_file = os.path.join(output_dir, "captions.ass")
            
            # --- Prerequisite File Checks ---
            if start_point != "Deep Research" and not os.path.exists(summary_file):
                raise FileNotFoundError(f"Cannot start from '{start_point}' because a required file is missing: {summary_file}")
            if start_point in PIPELINE_STEPS[3:] and not os.path.exists(script_file): # From Podcast Script onward
                 raise FileNotFoundError(f"Cannot start from '{start_point}' because a required file is missing: {script_file}")
            if start_point in PIPELINE_STEPS[6:] and not os.path.exists(audio_file): # From Audio (TTS) onward
                 raise FileNotFoundError(f"Cannot start from '{start_point}' because a required file is missing: {audio_file}")

            steps_to_run = self._get_step_list(start_point)
            
            research, script, seo_title, audio_len = "", "", "", 0
            generated_images_with_times = []

            # --- Research and Scripting ---
            skipped_research = False
            if "Deep Research" in steps_to_run and os.path.exists(summary_file):
                logging.info(f"Skipping Deep Research, {summary_file} already exists.")
                research = open(summary_file, "r", encoding="utf-8").read()
                self.update_status(0, "☑️", 1.0)
                skipped_research = True
            elif "Deep Research" in steps_to_run: 
                self.update_status(0, "⏳", 0.2); research = self.google_client.deep_research(topic, self.config.get("PODCAST_LANGUAGE"), self.news_client); open(summary_file, "w", encoding="utf-8").write(research); self.update_status(0, "✅", 1.0)
            elif os.path.exists(summary_file): 
                research = open(summary_file, "r", encoding="utf-8").read(); self.update_status(0, "☑️", 1.0)
                skipped_research = True
            self._check_stop()

            if "Fact Check Research" in steps_to_run:
                if self.config.get("FACT_CHECK_ENABLED", False) and not skipped_research:
                    self.update_status(1, "⏳", 0.2); logging.info("Fact-checking the core research...")
                    fact_check = self.google_client.fact_check_script(research, self.config.get("PODCAST_LANGUAGE")); self.update_status(1, "✅", 1.0)
                    self._check_stop()
                    if "Revise Research" in steps_to_run:
                        self.update_status(2, "⏳", 0.2); logging.info("Revising research based on fact-check...")
                        research = self.google_client.revise_script(research, fact_check); open(summary_file, "w", encoding="utf-8").write(research); self.update_status(2, "✅", 1.0)
                else:
                    logging.info("Fact-checking is disabled. Skipping."); self.update_status(1, "⏭️", 1.0); self.update_status(2, "⏭️", 1.0)
            self._check_stop()

            if "Podcast Script" in steps_to_run and os.path.exists(script_file):
                logging.info(f"Skipping Podcast Script, {script_file} already exists.")
                script = open(script_file, "r", encoding="utf-8").read()
                self.update_status(3, "☑️", 1.0)
            elif "Podcast Script" in steps_to_run: 
                self.update_status(3, "⏳", 0.2); script = self.google_client.generate_podcast_script(topic, research, self.config); open(script_file, "w", encoding="utf-8").write(script); self.update_status(3, "✅", 1.0)
            elif os.path.exists(script_file): 
                script = open(script_file, "r", encoding="utf-8").read(); self.update_status(3, "☑️", 1.0)
            self._check_stop()

            # --- Pause for Script Review ---
            if "Podcast Script" in steps_to_run and self.on_script_generated:
                import threading
                script_approved_event = threading.Event()
                logging.info("Pausing pipeline for script review...")
                self.on_script_generated(script, script_file, script_approved_event)
                script_approved_event.wait()
                self._check_stop()
                # Reload script in case it was modified by the user
                script = open(script_file, "r", encoding="utf-8").read()

            # --- Visuals and Audio ---
            if "Generate Thumbnail" in steps_to_run and self.config.get("GENERATE_THUMBNAIL", False) and os.path.exists(image_file):
                logging.info(f"Skipping Generate Thumbnail, {image_file} already exists.")
                self.update_status(4, "☑️", 1.0)
            elif "Generate Thumbnail" in steps_to_run:
                if self.config.get("GENERATE_THUMBNAIL", False):
                    self.update_status(4, "⏳", 0.2); title_text = seo_title or topic
                    left_path, right_path = os.path.join(output_dir, "thumb_left.png"), os.path.join(output_dir, "thumb_right.png")
                    try:
                        prompts = self.google_client.generate_thumbnail_prompts(topic, title_text)
                        logging.info(f"Character Prompt: {prompts['character_prompt']}")
                        logging.info(f"Text Prompt: {prompts['text_prompt']}")
                        image_engine = self.config.get("IMAGE_ENGINE", "Gemini API")
                        if image_engine == "WaveSpeed AI":
                            self.wavespeed_client.text_to_image(self.config.get("WAVESPEED_IMAGE_MODEL"), prompts['character_prompt'], left_path)
                            self._check_stop()
                            self.wavespeed_client.text_to_image(self.config.get("WAVESPEED_IMAGE_MODEL"), prompts['text_prompt'], right_path)
                        else:
                            self.google_client.gemini_nanobanana_image(prompts['character_prompt'], left_path)
                            self._check_stop()
                            self.google_client.gemini_nanobanana_image(prompts['text_prompt'], right_path)
                        self._check_stop()
                        ffmpeg_cmd = ["ffmpeg", "-y", "-i", left_path, "-i", right_path, "-filter_complex", "[0:v]scale=960:1080,setsar=1[left];[1:v]scale=960:1080,setsar=1[right];[left][right]hstack=inputs=2", image_file]
                        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                        self.update_status(4, "✅", 1.0)
                    except Exception as e: 
                        logging.error(f"Thumbnail generation failed: {e}", exc_info=True); self.update_status(4, "❌", 1.0)
                else: 
                    logging.info("Thumbnail generation is disabled. Skipping."); self.update_status(4, "⏭️", 1.0)
            self._check_stop()

            if "Analyze Tone" in steps_to_run: self.update_status(5, "✅", 1.0)
            
            if "Audio (TTS)" in steps_to_run and os.path.exists(audio_file):
                logging.info(f"Skipping Audio (TTS), {audio_file} already exists.")
                audio_len = self._get_audio_length(audio_file)
                self.update_status(6, f"☑️ {audio_len:.1f}s", 1.0)
            elif "Audio (TTS)" in steps_to_run:
                self.update_status(6, "⏳", 0.2)
                if self.config.get("AUDIO_ENGINE") == "WaveSpeed AI":
                    self.wavespeed_client.text_to_speech(self.config.get("WAVESPEED_AUDIO_MODEL"), sanitize_for_tts(script), audio_file, voice=self.config.get("VOICE_NAME", "Brian"))
                else:
                    self.google_client.generate_tts(sanitize_for_tts(script), audio_file, self.config)
                audio_len = self._get_audio_length(audio_file); self.update_status(6, f"✅ {audio_len:.1f}s", 1.0)
            elif os.path.exists(audio_file):
                audio_len = self._get_audio_length(audio_file); self.update_status(6, f"☑️ {audio_len:.1f}s", 1.0)
            
            # --- Post-Audio Steps ---
            need_timed_images = "Generate Timed Images" in steps_to_run and self.config.get("GENERATE_TIMED_IMAGES", False)
            need_captions = "Create Final Video" in steps_to_run and self.config.get("CAPTION_ENABLED", False)
            need_timestamps = "Generate Timestamps" in steps_to_run and self.config.get("GENERATE_TIMESTAMPS", True)
            need_video_timestamps = "Video Generation" in steps_to_run and self.config.get("BG_MODE", "AI Video") == "AI Video"
            
            logging.info(f"Caption state: CAPTION_ENABLED={self.config.get('CAPTION_ENABLED')} | need_captions={need_captions} | captions_file_exists={os.path.exists(captions_file)}")
            
            if (need_timed_images or need_captions or need_timestamps or need_video_timestamps):
                if os.path.exists(audio_file):
                    # Always regenerate the .ass file if captions are needed but the file is missing
                    captions_missing = need_captions and not os.path.exists(captions_file)
                    timestamps_file = os.path.join(output_dir, "timestamps.json")
                    
                    if not self.word_timestamps_for_images and os.path.exists(timestamps_file):
                        try:
                            with open(timestamps_file, "r") as f:
                                self.word_timestamps_for_images = json.load(f)
                            logging.info(f"Loaded timestamps from {timestamps_file}")
                        except Exception as e:
                            logging.error(f"Failed to load timestamps.json: {e}")
                    
                    if not self.word_timestamps_for_images or captions_missing:
                        # Whisper uses None for auto-detect or ISO codes like 'en', not full words like 'English'
                        lang = self.config.get("PODCAST_LANGUAGE", "English")
                        whisper_lang = None if lang.lower() in ("english", "auto", "") else lang
                        logging.info(f"Running Whisper transcription. need_captions={need_captions}, captions_missing={captions_missing}, lang={whisper_lang}")
                        self.word_timestamps_for_images = generate_captions(
                            audio_file,
                            captions_file if need_captions else None,
                            whisper_lang
                        )
                        try:
                            with open(timestamps_file, "w") as f:
                                json.dump(self.word_timestamps_for_images, f)
                        except Exception as e:
                            logging.error(f"Failed to save timestamps.json: {e}")
                    else:
                        logging.info(f"Skipping Whisper - word_timestamps already loaded ({len(self.word_timestamps_for_images)} words). captions_missing={captions_missing}")

            if "Generate Timed Images" in steps_to_run:
                if need_timed_images:
                    self.update_status(7, "⏳", 0.2)
                    image_count_target = self.config.get("IMAGE_COUNT", 8)
                    user_interval = self.config.get("IMAGE_GENERATION_INTERVAL", 0)
                    
                    if user_interval > 0:
                        image_interval = user_interval
                        image_count_target = int(audio_len / user_interval) + 1
                    else:
                        image_interval = max(1, int(audio_len / image_count_target)) if audio_len > 0 else 10
                        
                    image_count = 0
                    for i in range(0, int(audio_len), image_interval):
                        if image_count >= image_count_target:
                            break
                        segment_text = " ".join([w['word'] for w in self.word_timestamps_for_images if i <= w['start'] < i + image_interval])
                        if not segment_text.strip(): continue
                        image_count += 1; image_output_path = os.path.join(segment_images_dir, f"segment_{image_count:03d}.png")
                        if os.path.exists(image_output_path):
                            logging.info(f"Skipping image {image_count}, already exists.")
                            generated_images_with_times.append((i, image_output_path))
                            continue
                        
                        image_prompt = self.google_client.generate_image_prompt_for_segment(self.config.get("CONTENT_STYLE"), topic, segment_text, self.config.get("IMAGE_PROMPT_STYLE", ""))
                        try:
                            if self.config.get("IMAGE_ENGINE") == "WaveSpeed AI":
                                self.wavespeed_client.text_to_image(self.config.get("WAVESPEED_IMAGE_MODEL"), image_prompt, image_output_path)
                            else:
                                self.google_client.gemini_nanobanana_image(image_prompt, image_output_path)
                            generated_images_with_times.append((i, image_output_path))
                        except Exception as e: logging.error(f"Failed to generate image {image_count}: {e}")
                        self._wait()
                    self.update_status(7, f"✅ {image_count} images", 1.0)
                else:
                    logging.info("Timed image generation is disabled. Skipping."); self.update_status(7, "⏭️", 1.0)
            self._check_stop()
            
            bg_mode = self.config.get("BG_MODE", "AI Video")
            if "Video Generation" in steps_to_run and bg_mode == "AI Video" and os.path.exists(bg_video_file):
                logging.info(f"Skipping Video Generation, {bg_video_file} already exists.")
                self.update_status(8, "☑️", 1.0)
            elif "Video Generation" in steps_to_run:
                if bg_mode == "AI Video":
                    self.update_status(8, "⏳", 0.2)
                    aspect = self.config.get("VIDEO_ASPECT_RATIO")
                    content_style = self.config.get("CONTENT_STYLE", "Podcast")
                    clip_count = max(1, self.config.get("VIDEO_CLIP_COUNT", 1))
                    clip_paths = []
                    video_interval = max(1, int(audio_len / clip_count)) if audio_len > 0 else 10
                    for clip_idx in range(clip_count):
                        start_t = clip_idx * video_interval
                        end_t = start_t + video_interval
                        if self.word_timestamps_for_images:
                            segment_text = " ".join([w['word'] for w in self.word_timestamps_for_images if start_t <= w['start'] < end_t])
                            if not segment_text.strip(): segment_text = script[:500] # Fallback
                        else:
                            segment_text = script[:500] # Fallback

                        clip_path = bg_video_file.replace(".mp4", f"_clip{clip_idx+1}.mp4") if clip_count > 1 else bg_video_file
                        if os.path.exists(clip_path):
                            logging.info(f"Skipping video clip {clip_idx+1}, already exists.")
                            clip_paths.append(clip_path)
                            continue
                            
                        prompt = self.google_client.generate_video_prompt(topic, segment_text, self.config.get("VIDEO_PROMPT_BASE_STYLE"), content_style)
                        try:
                            if self.config.get("VIDEO_ENGINE") == "Vertex AI (Veo)":
                                self.google_client.vertex_ai_text_to_video(prompt, clip_path, "16:9" if aspect == "16:9 (Horizontal)" else "9:16")
                            else:
                                self.wavespeed_client.text_to_video(self.config.get("WAVESPEED_VIDEO_MODEL"), prompt, clip_path, aspect)
                            clip_paths.append(clip_path)
                            logging.info(f"Video clip {clip_idx+1}/{clip_count} generated.")
                        except Exception as e:
                            logging.error(f"Video clip {clip_idx+1} failed: {e}")
                        self._check_stop()
                    # Concatenate clips if multiple
                    if len(clip_paths) > 1:
                        concat_txt = bg_video_file.replace(".mp4", "_concat.txt")
                        with open(concat_txt, "w") as cf:
                            for cp in clip_paths: cf.write(f"file '{os.path.abspath(cp)}'\n")
                        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", bg_video_file], check=True, capture_output=True)
                        logging.info(f"Concatenated {len(clip_paths)} clips into {bg_video_file}")
                    elif len(clip_paths) == 1 and clip_paths[0] != bg_video_file:
                        import shutil; shutil.move(clip_paths[0], bg_video_file)
                    self.update_status(8, f"✅ {len(clip_paths)} clip(s)", 1.0) if clip_paths else self.update_status(8, "❌", 1.0)
                elif bg_mode == "Stock Video (Pixabay)":
                    self.update_status(8, "⏳", 0.2)
                    # Dynamically calculate clip count: 1 clip per 15 seconds of audio, capped at 40
                    clip_count = max(1, min(40, int(audio_len / 15))) if audio_len > 0 else 1
                    clip_paths = []
                    video_interval = max(1, int(audio_len / clip_count)) if audio_len > 0 else 10
                    for clip_idx in range(clip_count):
                        start_t = clip_idx * video_interval
                        end_t = start_t + video_interval
                        if self.word_timestamps_for_images:
                            segment_text = " ".join([w['word'] for w in self.word_timestamps_for_images if start_t <= w['start'] < end_t])
                            if not segment_text.strip(): segment_text = script[:500]
                        else:
                            segment_text = script[:500]

                        clip_path = bg_video_file.replace(".mp4", f"_clip{clip_idx+1}.mp4") if clip_count > 1 else bg_video_file
                        if os.path.exists(clip_path):
                            logging.info(f"Skipping Pixabay clip {clip_idx+1}, already exists.")
                            clip_paths.append(clip_path)
                            continue
                            
                        raw_clip_path = bg_video_file.replace(".mp4", f"_clip{clip_idx+1}_raw.mp4")
                        query = self.google_client.generate_search_query(topic, segment_text)
                        try:
                            is_vertical = self.config.get("VIDEO_ASPECT_RATIO", "16:9") == "9:16"
                            success = self.pixabay_client.download_video(query, raw_clip_path, is_vertical=is_vertical)
                            if success:
                                # Normalize video to standard resolution & 24fps so they can be concatenated
                                vf_scale = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" if is_vertical else "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
                                subprocess.run([
                                    "ffmpeg", "-y", "-i", raw_clip_path, 
                                    "-vf", vf_scale, "-r", "24", 
                                    "-c:v", "libx264", "-preset", "fast", "-c:a", "copy", 
                                    clip_path
                                ], check=True, capture_output=True)
                                
                                clip_paths.append(clip_path)
                                logging.info(f"Pixabay clip {clip_idx+1}/{clip_count} downloaded and normalized.")
                            else:
                                logging.error(f"Pixabay clip {clip_idx+1} failed to find footage for '{query}'")
                        except Exception as e:
                            logging.error(f"Pixabay clip {clip_idx+1} failed: {e}")
                        self._check_stop()
                    
                    if len(clip_paths) > 1:
                        concat_txt = bg_video_file.replace(".mp4", "_concat.txt")
                        with open(concat_txt, "w") as cf:
                            for cp in clip_paths: cf.write(f"file '{os.path.abspath(cp)}'\n")
                        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", bg_video_file], check=True, capture_output=True)
                        logging.info(f"Concatenated {len(clip_paths)} Pixabay clips into {bg_video_file}")
                    elif len(clip_paths) == 1 and clip_paths[0] != bg_video_file:
                        import shutil; shutil.move(clip_paths[0], bg_video_file)
                    self.update_status(8, f"✅ {len(clip_paths)} clip(s)", 1.0) if clip_paths else self.update_status(8, "❌", 1.0)
                else:
                    logging.info(f"BG Mode is '{bg_mode}'. Skipping video generation."); self.update_status(8, "⏭️", 1.0)
            self._check_stop()

            final_audio = audio_file
            if "Add Background Music" in steps_to_run and self.config.get("ADD_MUSIC", False) and os.path.exists(mixed_audio_file):
                logging.info(f"Skipping Add Background Music, {mixed_audio_file} already exists.")
                final_audio = mixed_audio_file
                self.update_status(9, "☑️", 1.0)
            elif "Add Background Music" in steps_to_run:
                if self.config.get("ADD_MUSIC", False):
                    self.update_status(9, "⏳", 0.2); final_audio = mix_audio_with_music(audio_file, "assets/background_music.mp3", mixed_audio_file); self.update_status(9, "✅", 1.0)
                else: 
                    self.update_status(9, "⏭️", 1.0)
            elif self.config.get("ADD_MUSIC", False) and os.path.exists(mixed_audio_file):
                final_audio = mixed_audio_file
                self.update_status(9, "☑️", 1.0)
            self._check_stop()

            if "Create Final Video" in steps_to_run and os.path.exists(final_video_file):
                # If captions are enabled, force re-assembly so they get baked into the video
                if need_captions and os.path.exists(captions_file):
                    logging.info("Captions are enabled — re-assembling final video to bake in subtitles.")
                    os.remove(final_video_file)
                else:
                    logging.info(f"Skipping Create Final Video, {final_video_file} already exists.")
                    self.update_status(10, "☑️", 1.0)
            if "Create Final Video" in steps_to_run and not os.path.exists(final_video_file):
                self.update_status(10, "⏳", 0.2)
                aspect = self.config.get("VIDEO_ASPECT_RATIO", "16:9")
                if aspect == "9:16": output_size = "1080x1920"
                elif aspect == "1:1": output_size = "1080x1080"
                else: output_size = "1920x1080"
                
                inputs = []            
                filter_segments = []   
                video_input_count = 0  
                final_video_map_tag = "[v_out]" 
                
                # Determine intermediate or final output path
                raw_video_file = final_video_file.replace(".mp4", "_raw.mp4") if need_captions else final_video_file
                skip_ffmpeg_first_pass = False

                if self.config.get("TIMED_IMAGES_AS_SLIDESHOW", False) and generated_images_with_times:
                    try:
                        import moviepy.editor as mpy
                        logging.info(f"Creating SLIDESHOW video with MoviePy (size {output_size})")
                        target_w, target_h = map(int, output_size.split('x'))
                        clips = []
                        for i, (timestamp, img_path) in enumerate(generated_images_with_times):
                            duration = (generated_images_with_times[i+1][0] - timestamp) if i + 1 < len(generated_images_with_times) else (audio_len - timestamp)
                            
                            clip = mpy.ImageClip(img_path).set_duration(duration)
                            
                            # Center pad to target aspect ratio
                            img_ratio = clip.w / clip.h
                            target_ratio = target_w / target_h
                            if img_ratio > target_ratio:
                                clip = clip.resize(width=target_w)
                            else:
                                clip = clip.resize(height=target_h)
                            clip = clip.on_color(size=(target_w, target_h), color=(0, 0, 0), pos='center')
                            
                            # Zoom effect (10% over clip duration)
                            # We use a closure factory to capture 'duration' properly for each clip
                            def make_zoom(dur):
                                return lambda t: 1.0 + 0.1 * (t / dur)
                            
                            clip = clip.resize(make_zoom(duration))
                            # Crop back to target size to remove bounds that expanded
                            clip = clip.crop(x_center=target_w/2, y_center=target_h/2, width=target_w, height=target_h)
                            
                            # Crossfade transition (0.5s)
                            if i > 0:
                                clip = clip.crossfadein(0.5)
                            clips.append(clip)
                            
                        # Compose clips with padding for the crossfade
                        final_clip = mpy.concatenate_videoclips(clips, padding=-0.5, method="compose")
                        
                        # Set audio
                        audio_clip = mpy.AudioFileClip(final_audio)
                        final_clip = final_clip.set_audio(audio_clip)
                        
                        logging.info("Rendering cinematic video with MoviePy (this may take a few minutes)...")
                        final_clip.write_videofile(raw_video_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
                        skip_ffmpeg_first_pass = True
                    except Exception as e:
                        logging.warning(f"MoviePy rendering failed or missing ({e}). Falling back to FFmpeg concat.")
                        logging.info(f"Creating SLIDESHOW video with size {output_size}")
                        concat_file_path = os.path.join(output_dir, "slideshow.txt")
                        with open(concat_file_path, "w") as f:
                            for i, (timestamp, img_path) in enumerate(generated_images_with_times):
                                duration = (generated_images_with_times[i+1][0] - timestamp) if i + 1 < len(generated_images_with_times) else (audio_len - timestamp)
                                f.write(f"file '{os.path.abspath(img_path)}'\n"); f.write(f"duration {duration}\n")
                        
                        inputs.extend(["-f", "concat", "-safe", "0", "-i", concat_file_path])
                        filter_segments.append(f"[{video_input_count}:v]scale={output_size}:force_original_aspect_ratio=decrease,pad={output_size.replace('x', ':')}:(ow-iw)/2:(oh-ih)/2,setsar=1[v_out]")
                        video_input_count += 1
                
                else:
                    logging.info(f"Creating OVERLAY video with size {output_size}")
                    if os.path.exists(bg_video_file): 
                        inputs.extend(["-stream_loop", "-1", "-i", bg_video_file])
                    else: 
                        inputs.extend(["-f", "lavfi", "-i", f"color=c=black:s={output_size}:d={audio_len}"])
                    
                    base_filter_chain = f"[{video_input_count}:v]scale={output_size},setsar=1[base_scaled]"
                    video_input_count += 1
                    last_video_output = "[base_scaled]"
                    
                    overlay_chain_segment = ""
                    if generated_images_with_times:
                        for i, (_, img_path) in enumerate(generated_images_with_times):
                            inputs.extend(["-i", img_path])
                            img_stream = f"[{video_input_count}:v]"
                            video_input_count += 1
                            
                            next_output_tag = f"[v{i+1}]"
                            timestamp, end_time = generated_images_with_times[i][0], (generated_images_with_times[i+1][0] if i + 1 < len(generated_images_with_times) else audio_len)
                            
                            overlay_chain_segment += f";{last_video_output}{img_stream}overlay=(W-w)/2:(H-h)/2:enable='between(t,{timestamp},{end_time})'{next_output_tag}"
                            last_video_output = next_output_tag
                        
                        base_filter_chain += overlay_chain_segment
                    
                    filter_segments.append(base_filter_chain)
                    final_video_map_tag = last_video_output

                if need_captions:
                    if os.path.exists(captions_file):
                        logging.info(f"Applying captions from: {captions_file}")
                    else:
                        logging.warning(f"⚠️ Captions are enabled but .ass file not found at '{captions_file}'. Subtitles will be skipped.")
                        need_captions = False  # Disable so we skip the second pass

                if not skip_ffmpeg_first_pass:
                    inputs.extend(["-i", final_audio])
                    
                    audio_map_index = video_input_count 
                    
                    ffmpeg_cmd = ["ffmpeg", "-y", *inputs]
                    
                    if filter_segments: 
                        final_filter_chain = ";".join(filter_segments)
                        logging.debug(f"Final Filter Chain: {final_filter_chain}")
                        ffmpeg_cmd.extend(["-filter_complex", final_filter_chain])
                    
                    ffmpeg_cmd.extend([
                        "-map", final_video_map_tag,
                        "-map", f"{audio_map_index}:a:0", 
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-t", str(audio_len), raw_video_file
                    ])
                    
                    logging.debug(f"Executing FFMPEG command: {' '.join(ffmpeg_cmd)}")
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')

                # Second pass: burn in subtitles using -vf subtitles= (more reliable than ass in filter_complex)
                if need_captions and os.path.exists(raw_video_file):
                    logging.info("🔤 Burning subtitles into video (second pass)...")
                    # subtitles= filter needs Windows-style escaped path
                    subs_path = os.path.abspath(captions_file).replace('\\', '/').replace(':', '\\:')
                    caption_cmd = [
                        "ffmpeg", "-y",
                        "-i", raw_video_file,
                        "-vf", f"subtitles='{subs_path}'",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "copy",
                        final_video_file
                    ]
                    logging.debug(f"Caption burn command: {' '.join(caption_cmd)}")
                    subprocess.run(caption_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                    os.remove(raw_video_file)  # Clean up intermediate file
                    logging.info("✅ Subtitles burned in successfully.")

                # --- Brand Assets ---
                logo_path = self.config.get("SOFTWARE_LOGO_PATH")
                intro_path = self.config.get("INTRO_VIDEO_PATH")
                outro_path = self.config.get("OUTRO_VIDEO_PATH")
                watermark_pos = self.config.get("WATERMARK_POSITION", "Bottom-Right")
                
                if (logo_path and os.path.exists(logo_path)) or (intro_path and os.path.exists(intro_path)) or (outro_path and os.path.exists(outro_path)):
                    logging.info("Applying Brand Assets...")
                    current_vid = final_video_file
                    branded_vid = os.path.join(output_dir, "branded_temp.mp4")
                    
                    if logo_path and os.path.exists(logo_path):
                        logging.info("Overlaying Watermark...")
                        pos_str = "main_w-overlay_w-20:main_h-overlay_h-20" # Bottom-Right
                        if watermark_pos == "Top-Left": pos_str = "20:20"
                        elif watermark_pos == "Top-Right": pos_str = "main_w-overlay_w-20:20"
                        elif watermark_pos == "Bottom-Left": pos_str = "20:main_h-overlay_h-20"
                        
                        subprocess.run([
                            "ffmpeg", "-y", "-i", current_vid, "-i", logo_path,
                            "-filter_complex", f"[1:v]scale=iw*0.15:-1[wm];[0:v][wm]overlay={pos_str}",
                            "-c:a", "copy", branded_vid
                        ], check=True, capture_output=True)
                        import shutil; shutil.move(branded_vid, current_vid)
                        
                    if (intro_path and os.path.exists(intro_path)) or (outro_path and os.path.exists(outro_path)):
                        logging.info("Stitching Intro/Outro...")
                        concat_txt = os.path.join(output_dir, "brand_concat.txt")
                        with open(concat_txt, "w") as f:
                            if intro_path and os.path.exists(intro_path):
                                f.write(f"file '{os.path.abspath(intro_path)}'\n")
                            f.write(f"file '{os.path.abspath(current_vid)}'\n")
                            if outro_path and os.path.exists(outro_path):
                                f.write(f"file '{os.path.abspath(outro_path)}'\n")
                        
                        subprocess.run([
                            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
                            "-c", "copy", branded_vid
                        ], check=True, capture_output=True)
                        import shutil; shutil.move(branded_vid, current_vid)

                self.update_status(10, "✅", 1.0)
            else:
                self.update_status(10, "⏭️", 1.0)
            self._check_stop()

            # --- Final Metadata (RUNS BEFORE TIMESTAMPS) ---
            if "Generate SEO Metadata" in steps_to_run:
                if self.config.get("GENERATE_SEO", False) or self.config.get("GENERATE_METADATA", False):
                    self.update_status(11, "⏳", 0.2)
                    metadata = self.google_client.generate_seo_metadata(topic, script) # Use script
                    if self.update_seo:
                        self.update_seo(metadata)
                    else:
                        with open(os.path.join(output_dir, "seo_metadata.json"), "w", encoding="utf-8") as f:
                            json.dump(metadata, f, indent=4)
                    self.update_status(11, "✅", 1.0)
                else: 
                    self.update_status(11, "⏭️", 1.0)

            # --- Timestamp Generation (RUNS AFTER SEO, TO APPEND) ---
            if "Generate Timestamps" in steps_to_run:
                if need_timestamps:
                    self.update_status(12, "⏳", 0.2)
                    logging.info("Generating accurate timestamps locally...")
                    
                    # 1. Get chapter titles from AI (fast, small payload)
                    chapter_titles = self.google_client.generate_chapter_titles(script)
                    
                    if not self.word_timestamps_for_images:
                        raise ValueError("Word timestamps are missing, cannot generate chapters.")
                        
                    # 2. Build a quick-lookup dictionary of the *first* time each word appears
                    word_map = {}
                    for word_data in self.word_timestamps_for_images:
                        word = word_data['word'].strip().lower()
                        if word not in word_map:
                            word_map[word] = word_data['start']

                    timestamp_output = "\n\n--- Timestamps ---\n"
                    found_chapters = 0
                    
                    # 3. Match titles locally
                    for title in chapter_titles:
                        # Find the first word of the title (e.g., "The Early Days" -> "the")
                        first_word_of_title = re.sub(r'[^\w]', '', title.split(' ')[0]).strip().lower()
                        
                        if first_word_of_title in word_map:
                            start_seconds = word_map[first_word_of_title]
                            timestamp_output += f"{format_timestamp(start_seconds)} - {title}\n"
                            found_chapters += 1
                        else:
                            logging.warning(f"Could not find timestamp match for chapter: '{title}' (word: '{first_word_of_title}')")

                    if found_chapters > 0:
                        if self.update_timestamps:
                            self.update_timestamps(timestamp_output)
                        else:
                            with open(os.path.join(output_dir, "timestamps.txt"), "w", encoding="utf-8") as f:
                                f.write(timestamp_output)
                    else:
                        logging.error("Failed to match any chapter titles to timestamp data.")

                    self.update_status(12, "✅", 1.0)
                else: 
                    self.update_status(12, "⏭️", 1.0)

            # --- Snippets ---
            if "Generate Snippets" in steps_to_run:
                if self.config.get("GENERATE_SNIPPETS", False):
                    self.update_status(13, "⏳", 0.2); snippets_dir = os.path.join(output_dir, "snippets"); os.makedirs(snippets_dir, exist_ok=True)
                    is_vertical = self.config.get("VIDEO_ASPECT_RATIO", "16:9") == "9:16"
                    for i in range(int(audio_len // 60)):
                        output_snippet_path = os.path.join(snippets_dir, f"snippet_{i+1}.mp4"); start_time = str(i * 60)
                        if is_vertical: 
                            ffmpeg_cmd = ["ffmpeg", "-y", "-i", final_video_file, "-ss", start_time, "-t", "60", "-c", "copy", output_snippet_path]
                        else: 
                            # FIX for "width not divisible by 2"
                            pan_scan_filter = f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280"
                            ffmpeg_cmd = ["ffmpeg", "-y", "-i", final_video_file, "-ss", start_time, "-t", "60", "-vf", pan_scan_filter, "-c:a", "copy", output_snippet_path]
                        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                    self.update_status(13, "✅", 1.0)
                else: 
                    logging.info("Snippet generation is disabled. Skipping."); self.update_status(13, "⏭️", 1.0)
            
            logging.info("✅✅ Pipeline completed successfully! ✅✅")
            success = True
            return final_video_file

        except (InterruptedError, FileNotFoundError) as e:
            logging.warning(str(e))
            raise e
        except subprocess.CalledProcessError as e: 
            logging.error(f"ffmpeg command failed with exit code {e.returncode}\nffmpeg stderr:\n{e.stderr if e.stderr else 'No stderr'}")
            self.update_status_on_error()
            raise e
        except Exception as e: 
            logging.error(f"Pipeline failed: {e}", exc_info=True)
            self.update_status_on_error()
            raise e
        finally:
            if self.on_finish: self.on_finish(success)

    def update_status_on_error(self):
        """No-op for headless mode. Errors are propagated and caught by the job manager."""
        pass

    def _extract_voice_name(self, val): 
        return val.split(" — ")[0] if " — " in val else val
