from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import os
import subprocess
from pydantic import BaseModel
import tempfile
import pipeline
from api_clients import STYLE_PROFILES, WaveSpeedClient
from config import load_config

router = APIRouter()

TOOLS_DIR = "workspace/tools_output"
os.makedirs(TOOLS_DIR, exist_ok=True)

@router.post("/caption")
def generate_captions(
    file: UploadFile = File(...),
    style: str = Form("Podcast"),
    language: str = Form("English")
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
            content = file.file.read()
            tmp_in.write(content)
            tmp_in_path = tmp_in.name
            
        filename_base = file.filename.rsplit('.', 1)[0] if file.filename else "video"
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
        
        # Return URL to fetch the file (using the /api/generate/media endpoint)
        return {"message": "Captions generated successfully", "path": out_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert")
def convert_aspect_ratio(
    file: UploadFile = File(...),
    target_ar: str = Form("16:9")
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
            content = file.file.read()
            tmp_in.write(content)
            tmp_in_path = tmp_in.name
            
        filename_base = file.filename.rsplit('.', 1)[0] if file.filename else "video"
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
        
        return {"message": "Video converted successfully", "path": out_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TTSRequest(BaseModel):
    text: str
    voice: str = "Kore"

@router.post("/tts")
def generate_tts(req: TTSRequest):
    try:
        config = load_config()
        tts_client = WaveSpeedClient(config.get("WAVESPEED_API_KEY", ""))
        
        filename = f"tts_{req.voice}_{hash(req.text) % 10000}.mp3"
        out_path = os.path.join(TOOLS_DIR, filename)
        
        tts_client.generate_speech(req.text, req.voice, out_path)
        
        return {"message": "Audio generated successfully", "path": out_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
