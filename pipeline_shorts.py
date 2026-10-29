import os
import re
import json
import math
import logging
import statistics
import subprocess
import tempfile
import pysubs2
import cv2
import numpy as np
import requests
from server.core.youtube_downloader import download_youtube_video
from server.core import clip_intelligence as ci
from pipeline import generate_captions
from api_clients import GoogleClient
from config import load_config

OUT_W, OUT_H = 1080, 1920  # YouTube Shorts native resolution


def fetch_b_roll_video(query: str, api_key: str, output_path: str) -> bool:
    if not api_key: return False
    try:
        res = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": query, "video_type": "film", "per_page": 3},
            timeout=10,
        )
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

def compute_audio_energy_peaks(video_path: str, sample_interval_sec: float = 1.0) -> list:
    """Computes audio RMS energy envelope per interval to detect excitement, vocal spikes, and volume peaks."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(video_path)
        chunk_len_ms = int(sample_interval_sec * 1000)
        energies = []
        for i in range(0, len(audio), chunk_len_ms):
            chunk = audio[i:i + chunk_len_ms]
            energies.append(chunk.rms)
        if not energies:
            return []
        max_rms = max(energies) or 1
        return [float(e) / float(max_rms) for e in energies]
    except Exception as e:
        logging.warning(f"Audio energy profile note: {e}")
        return []

def compute_visual_motion_profile(video_path: str, sample_interval_sec: float = 1.0) -> list:
    """Computes visual scene change & motion intensity envelope using OpenCV HSV histogram differences."""
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval = max(1, int(fps * sample_interval_sec))
        
        scores = []
        prev_hist = None
        frame_idx = 0
        
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            
            small = cv2.resize(frame, (160, 90))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            
            if prev_hist is not None:
                diff = 1.0 - cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                scores.append(max(0.0, float(diff)))
            else:
                scores.append(0.0)
                
            prev_hist = hist
            frame_idx += frame_interval
            
        cap.release()
        if not scores:
            return []
        max_s = max(scores) or 1
        return [float(s) / float(max_s) for s in scores]
    except Exception as e:
        logging.warning(f"Visual motion profile note: {e}")
        return []

def get_multimodal_boost(start: float, end: float, audio_profile: list, visual_profile: list, interval: float = 1.0) -> float:
    """Calculates multimodal excitement boost (0 to 15 bonus score) combining audio volume peaks and visual cuts."""
    if not audio_profile and not visual_profile:
        return 0.0
    s_idx = int(start / interval)
    e_idx = max(s_idx + 1, int(end / interval))
    
    a_score = 0.0
    if audio_profile and s_idx < len(audio_profile):
        clip_audio = audio_profile[s_idx:min(e_idx, len(audio_profile))]
        if clip_audio:
            a_score = sum(clip_audio) / len(clip_audio)
            
    v_score = 0.0
    if visual_profile and s_idx < len(visual_profile):
        clip_vis = visual_profile[s_idx:min(e_idx, len(visual_profile))]
        if clip_vis:
            v_score = sum(clip_vis) / len(clip_vis)
            
    return (a_score * 0.65 + v_score * 0.35) * 15.0


# --------------------------------------------------------------------------- #
# FFmpeg helpers
# --------------------------------------------------------------------------- #
def _run_ffmpeg(args: list):
    proc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {(proc.stderr or '').strip()[-800:]}")


def _has_audio(path: str) -> bool:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
             "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
        return bool(out.stdout.strip())
    except Exception:
        return True


# --------------------------------------------------------------------------- #
# Smart vertical reframing
# --------------------------------------------------------------------------- #
_YUNET_MODEL = os.path.join("assets", "models", "face_detection_yunet_2023mar.onnx")


def _make_face_detector():
    """
    Returns detect(gray_or_bgr_frame) -> list[(x, y, w, h)], or None if no detector is available.
    Prefers Haar (OpenCV 4.x); falls back to YuNet (OpenCV >= 4.5.4 / 5.x) when its ONNX model
    is present in assets/models. Never raises: reframing degrades to a centred crop instead.
    """
    try:
        if hasattr(cv2, "CascadeClassifier"):
            path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            cascade = cv2.CascadeClassifier(path)
            if not cascade.empty():
                def detect(frame, min_size):
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    return list(cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                                         minSize=(min_size, min_size)))
                return detect
        if hasattr(cv2, "FaceDetectorYN") and os.path.exists(_YUNET_MODEL):
            yunet = cv2.FaceDetectorYN.create(_YUNET_MODEL, "", (320, 320), 0.7)
            def detect(frame, min_size):
                h, w = frame.shape[:2]
                yunet.setInputSize((w, h))
                _, faces = yunet.detect(frame)
                if faces is None:
                    return []
                return [tuple(int(v) for v in f[:4]) for f in faces if f[2] >= min_size]
            return detect
    except Exception as e:
        logging.warning(f"Face detector unavailable: {e}")
    logging.warning("No face detector available (OpenCV 5 removed Haar cascades). "
                    "Install 'opencv-python<5' or add the YuNet model to assets/models. Using centred crop.")
    return None


def _plan_crop_shots(segment_path: str, width: int, height: int, target_w: int, fps: float,
                     sample_sec: float = 0.25, min_shot_sec: float = 1.5) -> list:
    """
    Speaker-aware reframing plan. Samples frames sequentially (no costly seeks),
    detects faces, splits on real scene cuts, and only re-frames when the subject
    moves consistently (2 consecutive samples), so the crop doesn't jitter.
    Each shot's crop is the median subject position, which keeps it steady.
    """
    detect = _make_face_detector()
    cap = cv2.VideoCapture(segment_path)
    step = max(1, int(round(fps * sample_sec)))
    det_scale = 480.0 / width if width > 480 else 1.0
    min_face = max(24, int(40 * det_scale))

    samples = []  # (t, center_x or None, scene_cut)
    prev_hist, frame_idx = None, 0
    while True:
        if not cap.grab():
            break
        if frame_idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            cx = None
            if detect is not None:
                small = cv2.resize(frame, (int(width * det_scale), int(height * det_scale))) if det_scale != 1.0 else frame
                faces = detect(small, min_face)
                if len(faces) > 0:
                    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
                    cx = (x + w / 2.0) / det_scale

            hsv = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            cut = prev_hist is not None and (1.0 - cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)) > 0.55
            prev_hist = hist
            samples.append((frame_idx / fps, cx, cut))
        frame_idx += 1
    cap.release()

    duration = frame_idx / fps if fps else 0.0
    default_cx = width / 2.0
    if not samples:
        return [{"start": 0.0, "end": duration, "crop_x": int((width - target_w) // 2)}]

    # Fill detection gaps with the nearest known face position
    filled, last = [], None
    for t, cx, cut in samples:
        if cut:
            last = None
        if cx is not None:
            last = cx
        filled.append([t, cx if cx is not None else last, cut])
    nxt = None
    for s in reversed(filled):
        if s[1] is not None:
            nxt = s[1]
        elif nxt is not None:
            s[1] = nxt
    for s in filled:
        if s[1] is None:
            s[1] = default_cx

    jump = width * 0.15
    shots, cur = [], {"start": 0.0, "centers": []}
    pending = 0
    for t, cx, cut in filled:
        shot_len = t - cur["start"]
        med = statistics.median(cur["centers"]) if cur["centers"] else cx
        moved = abs(cx - med) > jump
        pending = pending + 1 if moved else 0
        if cur["centers"] and shot_len >= min_shot_sec and (cut or pending >= 2):
            cur["end"] = t
            shots.append(cur)
            cur = {"start": t, "centers": []}
            pending = 0
        cur["centers"].append(cx)
    cur["end"] = duration
    shots.append(cur)

    plan = []
    for s in shots:
        med = statistics.median(s["centers"]) if s["centers"] else default_cx
        crop_x = int(max(0, min(med - target_w / 2.0, width - target_w)))
        if plan and abs(plan[-1]["crop_x"] - crop_x) < width * 0.04:
            plan[-1]["end"] = s["end"]  # merge visually identical neighbouring shots
        else:
            plan.append({"start": round(s["start"], 3), "end": round(s["end"], 3), "crop_x": crop_x})
    return plan


def render_scene_aware_clip(video_path: str, start_time: float, end_time: float, out_path: str):
    """Cuts [start, end] and reframes it to 1080x1920, following the active subject."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        segment_path = tmp.name
    try:
        _run_ffmpeg(["-ss", f"{start_time:.3f}", "-i", video_path, "-t", f"{max(0.5, end_time - start_time):.3f}",
                     "-map", "0:v:0", "-map", "0:a:0?",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                     segment_path])

        cap = cv2.VideoCapture(segment_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        target_w = int(height * 9 / 16) // 2 * 2
        audio_map = ["-map", "0:a?"]
        encode = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy"]

        # Source is already vertical / narrower than 9:16 -> scale to cover, centre-crop
        if width <= target_w + 2:
            _run_ffmpeg(["-i", segment_path,
                         "-vf", f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},setsar=1",
                         "-map", "0:v"] + audio_map + encode + [out_path])
            return

        plan = _plan_crop_shots(segment_path, width, height, target_w, fps)
        scale = f"scale={OUT_W}:{OUT_H},setsar=1"
        if len(plan) == 1:
            _run_ffmpeg(["-i", segment_path, "-vf", f"crop={target_w}:{height}:{plan[0]['crop_x']}:0,{scale}",
                         "-map", "0:v"] + audio_map + encode + [out_path])
        else:
            parts, concat = [], ""
            for i, shot in enumerate(plan):
                parts.append(f"[0:v]trim=start={shot['start']}:end={shot['end']},setpts=PTS-STARTPTS,"
                             f"crop={target_w}:{height}:{shot['crop_x']}:0,{scale}[v{i}]")
                concat += f"[v{i}]"
            parts.append(f"{concat}concat=n={len(plan)}:v=1:a=0[outv]")
            _run_ffmpeg(["-i", segment_path, "-filter_complex", ";".join(parts),
                         "-map", "[outv]"] + audio_map + encode + [out_path])
    finally:
        try:
            os.remove(segment_path)
        except OSError:
            pass


def extract_clip_transcript_segments(word_timestamps: list, clip_start: float, clip_end: float) -> list:
    """Slices word timestamps for [clip_start, clip_end] into sentence/phrase segments for TimelineEditor."""
    clip_words = [
        w for w in word_timestamps
        if float(w.get("end", 0)) > clip_start and float(w.get("start", 0)) < clip_end
    ]
    if not clip_words:
        return []
    segments = []
    cur_words = []
    seg_start = max(0.0, round(float(clip_words[0]["start"]) - clip_start, 2))
    seg_idx = 1
    for i, w in enumerate(clip_words):
        word_text = str(w.get("word", "")).strip()
        if not word_text:
            continue
        if not cur_words:
            seg_start = max(0.0, round(float(w["start"]) - clip_start, 2))
        cur_words.append(word_text)
        seg_end = max(seg_start + 0.3, round(float(w["end"]) - clip_start, 2))
        ends_sentence = word_text.endswith((".", "!", "?"))
        if len(cur_words) >= 8 or ends_sentence or (seg_end - seg_start >= 4.5) or i == len(clip_words) - 1:
            segments.append({
                "id": f"seg_{seg_idx}",
                "start": seg_start,
                "end": seg_end,
                "text": " ".join(cur_words),
                "deleted": False
            })
            seg_idx += 1
            cur_words = []
    return segments


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def _llm_json(client, prompt: str):
    try:
        raw = client._generate_text(prompt, as_json=True)
    except TypeError:
        raw = client._generate_text(prompt)
    return ci.parse_llm_json(raw or "")


def _heuristic_candidates(sentences, words, audio_profile, visual_profile, min_dur, max_dur, target=30.0):
    """Signal-only fallback used when the LLM is unavailable. Scores reflect measurements only."""
    cands = []
    for i in range(len(sentences)):
        j = i
        while j + 1 < len(sentences) and sentences[j]["end"] - sentences[i]["start"] < target:
            j += 1
        st, en = sentences[i]["start"], sentences[j]["end"]
        if en - st < min_dur:
            continue
        cands.append({"start": st, "end": min(en, st + max_dur)})
    out = []
    for c in cands:
        m = ci.speech_metrics(words, c["start"], c["end"])
        mm = ci.multimodal_score(c["start"], c["end"], audio_profile, visual_profile)
        speech = 100.0 * (1 - m["dead_air_ratio"]) * (1.0 if 2.0 <= m["wps"] <= 3.8 else 0.75)
        c["score"] = int(round(0.55 * mm + 0.45 * speech))
        out.append(c)
    return ci.non_max_suppression(out, 0.2)


def analyze_video(source: str, is_local: bool, job_id: str, update_job_callback, num_clips: int = 10,
                  min_duration: float = 15.0, max_duration: float = 60.0, language: str = None):
    try:
        config = load_config()
        client = GoogleClient(config)
        output_dir = os.path.join("workspace", f"clipper_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        min_duration = max(5.0, float(min_duration))
        max_duration = max(min_duration + 5.0, float(max_duration))
        
        if is_local:
            update_job_callback(job_id, step="Processing Local Video", progress=0.05)
            video_path = source
        else:
            update_job_callback(job_id, step="Downloading Video", progress=0.05)
            video_path = download_youtube_video(source, output_dir)
        
        update_job_callback(job_id, step="Measuring vocal energy & scene dynamics", progress=0.15)
        audio_profile = compute_audio_energy_peaks(video_path)
        visual_profile = compute_visual_motion_profile(video_path)

        update_job_callback(job_id, step="Transcribing with word-level timing", progress=0.25)
        lang = None if not language or str(language).lower() in ("auto", "none", "") else language
        words = ci.clean_words(generate_captions(video_path, None, lang))
        if not words:
            raise Exception("Transcription failed or returned no words.")

        # Persist words so rendering can reuse them (no second Whisper pass per clip)
        with open(os.path.join(output_dir, "words.json"), "w", encoding="utf-8") as f:
            json.dump(words, f)

        sentences = ci.build_sentences(words)
        lines = ci.annotate_lines(sentences, audio_profile)
        windows = ci.build_windows(lines, max_chars=12000, overlap_lines=8)
        per_window = max(3, min(8, num_clips + 2))
        context_hint = ""
        if len(windows) > 1:
            context_hint = "- This is one part of a longer video, so prefer moments that make sense without the surrounding parts.\n"

        # ---- Pass 1: candidate generation per window ----
        raw_candidates = []
        llm_ok = False
        for w_idx, win in enumerate(windows):
            update_job_callback(job_id, step=f"AI scouting moments (part {w_idx + 1}/{len(windows)})",
                                progress=0.35 + 0.35 * (w_idx / max(1, len(windows))))
            try:
                parsed = _llm_json(client, ci.build_candidate_prompt(win, min_duration, max_duration, per_window, context_hint))
                found = ci.extract_clip_list(parsed)
                if found:
                    llm_ok = True
                raw_candidates.extend(found)
            except Exception as e:
                logging.warning(f"Clipper window {w_idx} LLM notice: {e}")

        # ---- Snap, measure, score ----
        update_job_callback(job_id, step="Snapping cuts to sentence boundaries & scoring", progress=0.72)
        video_end = words[-1]["end"]
        scored = []
        for c in raw_candidates:
            try:
                st, en = float(c.get("start", 0)), float(c.get("end", 0))
            except (TypeError, ValueError):
                continue
            if en <= st or st >= video_end:
                continue
            st, en, clean = ci.snap_to_boundaries(st, min(en, video_end + 0.5), sentences, min_duration, max_duration)
            c["start"], c["end"] = st, en
            metrics = ci.speech_metrics(words, st, en)
            mm = ci.multimodal_score(st, en, audio_profile, visual_profile)
            score, breakdown = ci.composite_score(c, metrics, mm, clean, min_duration, max_duration)
            c.update({
                "score": score,
                "score_breakdown": breakdown,
                "speech_metrics": metrics,
                "multimodal_boost": round(get_multimodal_boost(st, en, audio_profile, visual_profile), 1),
                "boundaries_snapped": True,
                "source": "ai",
            })
            c["hook_score"] = breakdown["hook"]
            c["retention_score"] = breakdown["retention"]
            c["payoff_score"] = breakdown["payoff"]
            scored.append(c)

        unique = ci.non_max_suppression(scored, iou_thresh=0.35)

        # ---- Pass 2: global calibrated re-rank ----
        if llm_ok and len(unique) >= 2:
            update_job_callback(job_id, step="AI editor re-ranking all candidates on one scale", progress=0.8)
            pool = unique[:25]
            for k, c in enumerate(pool):
                c["id"] = f"c{k}"
                c["_opening"], c["_ending"] = ci.text_between(sentences, c["start"], c["end"])
            try:
                parsed = _llm_json(client, ci.build_rerank_prompt(pool))
                ranks = (parsed or {}).get("rankings", []) if isinstance(parsed, dict) else (parsed or [])
                judge = {str(r.get("id")): r for r in ranks if isinstance(r, dict)}
                for c in pool:
                    r = judge.get(c["id"])
                    if r and r.get("judge_score") is not None:
                        js = ci._clamp_int(r.get("judge_score"))
                        c["score_breakdown"]["judge"] = js
                        c["judge_note"] = str(r.get("note", ""))[:120]
                        c["score"] = max(1, min(99, int(round(0.55 * c["score"] + 0.45 * js))))
            except Exception as e:
                logging.warning(f"Clipper re-rank skipped: {e}")
            for c in pool:
                c.pop("_opening", None)
                c.pop("_ending", None)
            unique = sorted(pool, key=lambda x: x["score"], reverse=True) + unique[25:]

        clips_data = ci.diversify(unique, num_clips)

        # ---- Fallback: measurable signals only (no fabricated AI scores) ----
        if not clips_data:
            update_job_callback(job_id, step="AI unavailable - selecting by audio energy & speech density", progress=0.85)
            for k, c in enumerate(_heuristic_candidates(sentences, words, audio_profile, visual_profile,
                                                         min_duration, max_duration)[:num_clips]):
                opening, _ = ci.text_between(sentences, c["start"], c["end"])
                c.update({
                    "title": f"Highlight {k + 1}",
                    "hook_text": "",
                    "category": "highlight",
                    "reason": "AI ranking was unavailable. This clip was picked from measured vocal energy and speech density only.",
                    "source": "heuristic",
                    "hook_score": None, "retention_score": None, "payoff_score": None,
                    "seo_title": f"{opening[:70]} #shorts" if opening else "Highlight #shorts",
                    "seo_description": opening[:200],
                    "seo_tags": "shorts",
                    "broll": [],
                    "speech_metrics": ci.speech_metrics(words, c["start"], c["end"]),
                    "boundaries_snapped": True,
                })
                clips_data.append(c)

        for c in clips_data:
            c.pop("id", None)
            c["start"], c["end"] = round(float(c["start"]), 2), round(float(c["end"]), 2)
            c.setdefault("broll", [])
            c["transcript_segments"] = extract_clip_transcript_segments(words, c["start"], c["end"])

        update_job_callback(job_id, step="Awaiting Selection", progress=0.6,
                            result=json.dumps({"type": "selection", "clips": clips_data, "video_path": video_path}))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e


# --------------------------------------------------------------------------- #
# Captions
# --------------------------------------------------------------------------- #
CAPTION_THEMES = {
    "viral_yellow": {"active": pysubs2.Color(255, 230, 0), "base": pysubs2.Color(255, 255, 255), "outline": 5.0},
    "neon_cyber": {"active": pysubs2.Color(0, 255, 255), "base": pysubs2.Color(255, 255, 255), "outline": 4.0},
    "black_white": {"active": pysubs2.Color(255, 255, 255), "base": pysubs2.Color(200, 200, 200), "outline": 5.0},
    "default": {"active": pysubs2.Color(102, 252, 241), "base": pysubs2.Color(255, 255, 255), "outline": 4.5},
}


def _ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def _ass_color_tag(c: pysubs2.Color) -> str:
    return f"{{\\c&H{c.b:02X}{c.g:02X}{c.r:02X}&}}"


def build_clip_ass(words: list, ass_path: str, config: dict, hook_text: str = "", hook_sec: float = 3.0):
    """
    Word-synced karaoke captions at native 1080x1920, positioned inside the Shorts
    safe zone. Adds an optional on-screen hook card for the first seconds.
    """
    theme = CAPTION_THEMES.get(config.get("CAPTION_THEME", "default"), CAPTION_THEMES["default"])
    font = config.get("CAPTION_FONT", "Arial")
    # CAPTION_FONT_SIZE was historically tuned for libass' 288px default canvas; scale to 1920px
    size = int(round(float(config.get("CAPTION_FONT_SIZE", 22)) * 3.6))

    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = str(OUT_W)
    subs.info["PlayResY"] = str(OUT_H)
    subs.info["WrapStyle"] = "0"
    subs.styles["Default"] = pysubs2.SSAStyle(
        fontname=font, fontsize=size, bold=True,
        primarycolor=theme["base"], outlinecolor=pysubs2.Color(0, 0, 0), backcolor=pysubs2.Color(0, 0, 0, 120),
        outline=theme["outline"], shadow=2, alignment=2, marginv=520, marginl=80, marginr=80,
    )
    subs.styles["Hook"] = pysubs2.SSAStyle(
        fontname=font, fontsize=int(size * 0.8), bold=True,
        primarycolor=pysubs2.Color(15, 15, 17), outlinecolor=theme["active"], backcolor=theme["active"],
        borderstyle=3, outline=18, shadow=0, alignment=8, marginv=300, marginl=90, marginr=90,
    )

    if hook_text:
        subs.append(pysubs2.SSAEvent(start=0, end=int(hook_sec * 1000),
                                     text="{\\fad(150,250)}" + _ass_escape(hook_text.upper()), style="Hook"))

    active, base = _ass_color_tag(theme["active"]), _ass_color_tag(theme["base"])
    for line in ci.group_caption_lines(words):
        line_end = line[-1]["end"]
        for i, aw in enumerate(line):
            st = int(aw["start"] * 1000)
            # Hold each highlight until the next word starts so captions don't flicker
            en = int((line[i + 1]["start"] if i + 1 < len(line) else line_end) * 1000)
            if en <= st:
                en = st + 80
            parts = []
            for j, w in enumerate(line):
                t = _ass_escape(w["word"].upper())
                parts.append(f"{active}{{\\fscx108\\fscy108}}{t}{{\\r}}" if j == i else f"{base}{t}")
            subs.append(pysubs2.SSAEvent(start=st, end=en, text=" ".join(parts), style="Default"))
    subs.save(ass_path)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _load_job_words(output_dir: str) -> list:
    p = os.path.join(output_dir, "words.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return ci.clean_words(json.load(f))
        except Exception as e:
            logging.warning(f"Could not load cached words: {e}")
    return []


def render_youtube_clips(job_id: str, video_path: str, selected_clips: list, update_job_callback):
    try:
        config = load_config()
        output_dir = os.path.join("workspace", f"clipper_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        source_words = _load_job_words(output_dir)
        
        update_job_callback(job_id, step="Reframing, cutting & captioning", progress=0.65)
        
        generated_clips = []
        failed = []
        total_clips = max(1, len(selected_clips))
        
        for idx, clip in enumerate(selected_clips):
            try:
                start = float(clip.get("start", 0))
                end = float(clip.get("end", 30))
                title = str(clip.get("title") or f"Clip {idx+1}")
                safe_title = re.sub(r'[^a-zA-Z0-9_]', '', title.replace(" ", "_"))[:60] or f"clip_{idx+1}"
                clip_name = f"{idx+1:02d}_{safe_title}.mp4"
            except (ValueError, TypeError) as e:
                logging.warning(f"Skipping malformed clip data: {clip} - {e}")
                continue

            try:
                update_job_callback(job_id, step=f"Clip {idx+1}/{total_clips}: speaker-aware reframing",
                                    progress=0.65 + 0.33 * (idx / total_clips))
                out_path = os.path.join(output_dir, clip_name)
                render_scene_aware_clip(video_path, start, end, out_path)
                has_audio = _has_audio(out_path)

                # ---- Text-based edits: actually remove sentences flagged as deleted ----
                kept = ci.kept_intervals_from_segments(clip.get("kept_segments") or [], end - start)
                if kept and has_audio:
                    try:
                        ripple_path = os.path.join(output_dir, f"ripple_{clip_name}")
                        v_parts, a_parts, pairs = [], [], ""
                        for s_i, (a, b) in enumerate(kept):
                            v_parts.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[rv{s_i}]")
                            a_parts.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,"
                                           f"afade=t=in:d=0.02,afade=t=out:st={max(0.0, b - a - 0.03):.3f}:d=0.03[ra{s_i}]")
                            pairs += f"[rv{s_i}][ra{s_i}]"
                        fc = ";".join(v_parts + a_parts + [f"{pairs}concat=n={len(kept)}:v=1:a=1[outv][outa]"])
                        _run_ffmpeg(["-i", out_path, "-filter_complex", fc, "-map", "[outv]", "-map", "[outa]",
                                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", ripple_path])
                        if os.path.exists(ripple_path) and os.path.getsize(ripple_path) > 0:
                            out_path = ripple_path
                        else:
                            kept = None
                    except Exception as ripple_err:
                        logging.warning(f"Transcript ripple splice skipped for {clip_name}: {ripple_err}")
                        kept = None

                # ---- Dynamic B-roll ----
                try:
                    pixabay_key = config.get("PIXABAY_API_KEY", "")
                    broll_timeline = clip.get("broll", []) or []
                    if pixabay_key and broll_timeline:
                        current_vid = out_path
                        for b_idx, b_item in enumerate(broll_timeline):
                            b_subj = str(b_item.get("subject", "")).lower().strip()
                            if not b_subj or b_subj == "none":
                                continue
                            b_start = float(b_item.get("start_offset", 2))
                            b_end = float(b_item.get("end_offset", b_start + 3))
                            if b_end <= b_start:
                                continue
                            b_roll_path = os.path.join(output_dir, f"broll_{idx}_{b_idx}.mp4")
                            if fetch_b_roll_video(b_subj, pixabay_key, b_roll_path):
                                overlay_path = os.path.join(output_dir, f"broll_overlay_{idx}_{b_idx}.mp4")
                                _run_ffmpeg([
                                    "-i", current_vid, "-i", b_roll_path, "-filter_complex",
                                    f"[1:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},"
                                    f"setpts=PTS-STARTPTS+{b_start}/TB[broll];"
                                    f"[0:v][broll]overlay=eof_action=pass:enable='between(t,{b_start},{b_end})'[v]",
                                    "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
                                    "-crf", "18", "-c:a", "copy", overlay_path])
                                current_vid = overlay_path
                        out_path = current_vid
                except Exception as e:
                    logging.error(f"Dynamic B-Roll injection failed for {clip_name}: {e}")

                # ---- Background music with real sidechain ducking (voice stays at full level) ----
                try:
                    bgm_path = "workspace/bgm.mp3"
                    if os.path.exists(bgm_path) and has_audio:
                        bgm_out_path = os.path.join(output_dir, f"bgm_{clip_name}")
                        _run_ffmpeg([
                            "-i", out_path, "-stream_loop", "-1", "-i", bgm_path, "-filter_complex",
                            "[0:a]asplit=2[voice][key];[1:a]volume=0.22[music];"
                            "[music][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[ducked];"
                            "[voice][ducked]amix=inputs=2:duration=first:normalize=0[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", bgm_out_path])
                        out_path = bgm_out_path
                except Exception as e:
                    logging.error(f"Audio ducking failed for {clip_name}: {e}")

                # ---- Captions: reuse analysis transcript, remapped through ripple cuts ----
                update_job_callback(job_id, step=f"Clip {idx+1}/{total_clips}: captions & mastering",
                                    progress=0.65 + 0.33 * ((idx + 0.7) / total_clips))
                ass_path = os.path.join(output_dir, f"{idx+1:02d}_{safe_title}.ass")
                clip_words = ci.remap_words(source_words, start, end, kept) if source_words else []
                if not clip_words:
                    # Older jobs without cached words: transcribe this clip only
                    clip_words = ci.clean_words(generate_captions(out_path, None, None))
                hook_text = str(clip.get("hook_text") or "").strip() if clip.get("show_hook", True) else ""
                build_clip_ass(clip_words, ass_path, config, hook_text=hook_text)

                final_out_path = os.path.join(output_dir, f"Final_{clip_name}")
                subs_path = os.path.abspath(ass_path).replace('\\', '/').replace(':', '\\:')
                final_args = ["-i", out_path, "-vf", f"subtitles='{subs_path}'",
                              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                              "-movflags", "+faststart"]
                if has_audio:
                    # Mastered to the -14 LUFS streaming target, with a true-peak ceiling to prevent clipping
                    final_args += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
                _run_ffmpeg(final_args + [final_out_path])

                generated_clips.append({
                    "title": title,
                    "path": final_out_path.replace("\\", "/"),
                    "duration": round(sum(b - a for a, b in kept) if kept else (end - start), 1),
                    "score": clip.get("score"),
                    "hook_text": hook_text,
                    "seo_title": clip.get("seo_title", title),
                    "seo_description": clip.get("seo_description", ""),
                    "seo_tags": clip.get("seo_tags", ""),
                })
            except Exception as clip_err:
                logging.error(f"Clip {idx+1} failed: {clip_err}", exc_info=True)
                failed.append({"title": title, "error": str(clip_err)[:300]})

            progress = 0.65 + 0.33 * ((idx + 1) / total_clips)
            update_job_callback(job_id, step=f"Rendered {idx+1}/{total_clips} Clips", progress=progress)

        if not generated_clips:
            raise RuntimeError(f"All clips failed to render: {failed[0]['error'] if failed else 'no clips selected'}")
        update_job_callback(job_id, step="Finished" + (f" ({len(failed)} failed)" if failed else ""), progress=1.0,
                            result=json.dumps({"type": "finished", "clips": generated_clips, "failed": failed}))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Clipper Error: {e}", exc_info=True)
        update_job_callback(job_id, step="Failed", progress=1.0, error=str(e))
