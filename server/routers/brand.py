from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from config import load_config, save_config

router = APIRouter()

ASSETS_DIR = "assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

@router.post("/upload")
async def upload_asset(type: str, file: UploadFile = File(...)):
    if type not in ["logo", "intro", "outro"]:
        raise HTTPException(status_code=400, detail="Invalid asset type.")
        
    ext = ".png" if type == "logo" else ".mp4"
    file_path = os.path.join(ASSETS_DIR, f"{type}{ext}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # Update config
    config = load_config()
    if type == "logo":
        config["SOFTWARE_LOGO_PATH"] = file_path
    elif type == "intro":
        config["INTRO_VIDEO_PATH"] = file_path
    elif type == "outro":
        config["OUTRO_VIDEO_PATH"] = file_path
        
    save_config(config)
    
    return {"message": f"{type.capitalize()} uploaded successfully.", "path": file_path}

@router.delete("/delete/{type}")
def delete_asset(type: str):
    if type not in ["logo", "intro", "outro"]:
        raise HTTPException(status_code=400, detail="Invalid asset type.")
        
    ext = ".png" if type == "logo" else ".mp4"
    file_path = os.path.join(ASSETS_DIR, f"{type}{ext}")
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    config = load_config()
    if type == "logo" and "SOFTWARE_LOGO_PATH" in config:
        config["SOFTWARE_LOGO_PATH"] = ""
    elif type == "intro" and "INTRO_VIDEO_PATH" in config:
        config["INTRO_VIDEO_PATH"] = ""
    elif type == "outro" and "OUTRO_VIDEO_PATH" in config:
        config["OUTRO_VIDEO_PATH"] = ""
        
    save_config(config)
    
    return {"message": f"{type.capitalize()} deleted successfully."}
