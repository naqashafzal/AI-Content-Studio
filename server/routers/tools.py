from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import os
import subprocess
from pydantic import BaseModel
import tempfile
import uuid
from server.core.security import copy_upload
import pipeline
from api_clients import STYLE_PROFILES, WaveSpeedClient, GoogleClient
from config import load_config, VOICE_OPTIONS

router = APIRouter()

TOOLS_DIR = "workspace/tools_output"
os.makedirs(TOOLS_DIR, exist_ok=True)

GEMINI_VOICES = set(VOICE_OPTIONS.keys()) | {"Kore", "Aoede", "Charon", "Fenrir", "Puck", "Zephyr", "Orus"}

@router.post("/caption")
def generate_captions(
    file: UploadFile = File(...),
    style: str = Form("Podcast"),
    language: str = Form("English")
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
            tmp_in_path = tmp_in.name
        copy_upload(file.file, tmp_in_path)
            
        filename_base = uuid.uuid4().hex
        out_path = os.path.join(TOOLS_DIR, f"{filename_base}_captioned.mp4")
        ass_path = os.path.join(TOOLS_DIR, f"{filename_base}.ass")
        
        style_opts = STYLE_PROFILES.get(style, STYLE_PROFILES["Podcast"])
        
        # 1. Generate ASS file using pipeline's generate_captions
        pipeline.generate_captions(tmp_in_path, ass_path, language, style_opts=style_opts)
        
        # 2. Burn subtitles with FFmpeg
        subs_path = os.path.abspath(ass_path).replace('\\', '/').replace(':', '\\:')
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_in_path,
            "-vf", f"subtitles='{subs_path}'",
            "-c:v", "libx264", "-c:a", "copy",
            out_path
        ], check=True, capture_output=True)
        
        os.remove(tmp_in_path)
        
        # Return normalized workspace path for /api/generate/media
        return {"message": "Captions generated successfully", "path": out_path.replace("\\", "/")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "tmp_in_path" in locals():
            from pathlib import Path
            Path(tmp_in_path).unlink(missing_ok=True)


@router.post("/convert")
def convert_aspect_ratio(
    file: UploadFile = File(...),
    target_ar: str = Form("16:9")
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
            tmp_in_path = tmp_in.name
        copy_upload(file.file, tmp_in_path)
            
        filename_base = uuid.uuid4().hex
        ar_str = "horizontal" if "16:9" in target_ar else "vertical"
        out_path = os.path.join(TOOLS_DIR, f"{filename_base}_{ar_str}.mp4")
        
        if "16:9" in target_ar:
            vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        else:
            vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
            
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_in_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-c:a", "copy",
            out_path
        ], check=True, capture_output=True)
        
        os.remove(tmp_in_path)
        
        return {"message": "Video converted successfully", "path": out_path.replace("\\", "/")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "tmp_in_path" in locals():
            from pathlib import Path
            Path(tmp_in_path).unlink(missing_ok=True)

class TTSRequest(BaseModel):
    text: str
    voice: str = "Kore"

@router.post("/tts")
def generate_tts(req: TTSRequest):
    try:
        if not req.text or not req.text.strip():
            raise ValueError("Text is required for speech generation.")

        config = load_config()
        ws_key = config.get("WAVESPEED_API_KEY") or config.get("WAVESPEED_AI_KEY") or ""
        gemini_key = config.get("GEMINI_API_KEY", "")

        # Route to Gemini TTS if voice is a Gemini voice and Gemini key is available, else WaveSpeed TTS
        if gemini_key and (req.voice in GEMINI_VOICES or not ws_key):
            filename = f"tts_{uuid.uuid4().hex}.wav"
            out_path = os.path.join(TOOLS_DIR, filename)
            g_client = GoogleClient(config)
            g_client.generate_tts(req.text, out_path, {"SPEAKER1": req.voice, "CONTENT_STYLE": "Narration"})
        elif ws_key:
            filename = f"tts_{uuid.uuid4().hex}.mp3"
            out_path = os.path.join(TOOLS_DIR, filename)
            tts_client = WaveSpeedClient(ws_key)
            audio_model = config.get("WAVESPEED_AUDIO_MODEL", "elevenlabs/text-to-speech")
            tts_client.generate_speech(req.text, req.voice, out_path, model_id=audio_model)
        else:
            raise ValueError("No TTS API key configured. Please set GEMINI_API_KEY or WAVESPEED_API_KEY in Settings.")

        return {"message": "Audio generated successfully", "path": out_path.replace("\\", "/")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
