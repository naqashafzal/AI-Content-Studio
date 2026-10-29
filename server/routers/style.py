from server.core.security import copy_upload
import os
import uuid
import json
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any

from server.core.style_engine import (
    StyleProfile, get_all_style_profiles, save_style_profile,
    delete_style_profile, analyze_reference_video
)

router = APIRouter()

@router.get("/")
def list_styles() -> List[Dict[str, Any]]:
    profiles = get_all_style_profiles()
    return [p.model_dump() for p in profiles]

@router.post("/")
def create_or_update_style(profile: StyleProfile) -> Dict[str, Any]:
    saved = save_style_profile(profile)
    return {"message": "Style profile saved successfully.", "profile": saved.model_dump()}

@router.delete("/{profile_id}")
def remove_style(profile_id: str):
    success = delete_style_profile(profile_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete default system presets or profile not found.")
    return {"message": "Style profile deleted successfully."}

@router.post("/analyze-reference")
async def extract_style_from_reference(name: str = Form("Custom Reference Style"), file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Reference video must have a filename.")
        
    temp_dir = os.path.abspath("workspace/style_temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_video_path = os.path.join(temp_dir, f"ref_{uuid.uuid4().hex}.mp4")

    try:
        copy_upload(file.file, temp_video_path)

        profile = analyze_reference_video(temp_video_path, name=name)
        return {
            "message": "Reference video analyzed and style profile extracted.",
            "profile": profile.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze reference video: {str(e)}")
    finally:
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception:
                pass

@router.get("/{profile_id}/export")
def export_style_profile(profile_id: str):
    profiles = get_all_style_profiles()
    match = next((p for p in profiles if p.id == profile_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Style profile not found.")
    return match.model_dump()

@router.post("/import")
def import_style_profile(profile_data: Dict[str, Any]):
    try:
        profile = StyleProfile(**profile_data)
        profile.id = str(uuid.uuid4()) # generate new unique ID on import
        saved = save_style_profile(profile)
        return {"message": "Style profile imported successfully.", "profile": saved.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid profile schema: {str(e)}")
