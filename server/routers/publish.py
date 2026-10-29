from server.core.security import DATA_DIR
TOKEN_PATH = str(DATA_DIR / "token.json")
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
import os
import glob
import traceback
import json

router = APIRouter()

class PublishRequest(BaseModel):
    video_path: str
    title: str
    description: str
    tags: str
    privacy_status: str = "private"

def validate_media_path(video_path: str) -> str:
    from server.core.security import media_path
    return media_path(video_path, roots=("workspace", "outputs", "agent_workspace", "videofx_outputs"))

@router.get("/library")
def get_publishing_library():
    workspace_dir = "workspace"
    if not os.path.exists(workspace_dir):
        return {"projects": []}
        
    projects = []
    try:
        folders = sorted(
            os.listdir(workspace_dir),
            key=lambda x: os.path.getctime(os.path.join(workspace_dir, x)),
            reverse=True
        )
    except Exception:
        folders = os.listdir(workspace_dir)

    for folder in folders:
        folder_path = os.path.join(workspace_dir, folder)
        if not os.path.isdir(folder_path) or folder == "tools_output":
            continue
            
        video_file = None
        for candidate in ("final_podcast.mp4", "final_podcast_video.mp4", "master_render.mp4", "final_director.mp4"):
            cand_path = os.path.join(folder_path, candidate)
            if os.path.exists(cand_path):
                video_file = cand_path
                break
        if not video_file:
            clips = glob.glob(os.path.join(folder_path, "Final_*.mp4"))
            if clips:
                video_file = clips[0]
        if not video_file:
            continue
                
        seo_data = {"title": folder.replace("_", " ").title(), "description": "", "tags": ""}
        seo_json_path = os.path.join(folder_path, "seo_metadata.json")
        if os.path.exists(seo_json_path):
            try:
                with open(seo_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    seo_data["title"] = data.get("title", seo_data["title"])
                    seo_data["description"] = data.get("description", "")
                    tags = data.get("tags", [])
                    if isinstance(tags, list):
                        seo_data["tags"] = ", ".join(tags)
                    else:
                        seo_data["tags"] = str(tags)
            except Exception as e:
                print(f"Error reading {seo_json_path}: {e}")
                
        timestamps_path = os.path.join(folder_path, "timestamps.txt")
        if os.path.exists(timestamps_path):
            try:
                with open(timestamps_path, "r", encoding="utf-8") as f:
                    ts = f.read()
                    if seo_data["description"]:
                        seo_data["description"] += f"\n\n{ts}"
                    else:
                        seo_data["description"] = ts
            except Exception as e:
                print(f"Error reading {timestamps_path}: {e}")
                
        projects.append({
            "id": folder,
            "name": seo_data["title"] or folder.replace("_", " ").title(),
            "path": folder_path.replace("\\", "/"),
            "video_path": video_file.replace("\\", "/"),
            "seo": seo_data
        })
        
    return {"projects": projects}

@router.post("/youtube")
def publish_to_youtube(req: PublishRequest):
    safe_video_path = validate_media_path(req.video_path)
        
    if not os.path.exists("client_secrets.json") and not os.path.exists(TOKEN_PATH):
        raise HTTPException(
            status_code=400,
            detail="client_secrets.json not found! Please configure YouTube OAuth 2.0 credentials in Settings."
        )
        
    try:
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials

        credentials = None
        token_json_path = TOKEN_PATH
        if os.path.exists(token_json_path):
            try:
                credentials = Credentials.from_authorized_user_file(
                    token_json_path,
                    scopes=["https://www.googleapis.com/auth/youtube.upload"]
                )
            except Exception as e:
                print(f"Failed to load token.json: {e}")
                
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                with open(token_json_path, "w", encoding="utf-8") as f:
                    f.write(credentials.to_json())
            else:
                raise HTTPException(
                    status_code=401,
                    detail="YouTube OAuth token is missing or expired. Please click 'Connect YouTube' in Publishing Hub."
                )
                
        youtube = build("youtube", "v3", credentials=credentials)
        
        body = {
            "snippet": {
                "title": req.title,
                "description": req.description,
                "tags": [t.strip() for t in req.tags.split(",") if t.strip()],
                "categoryId": "22"
            },
            "status": {"privacyStatus": req.privacy_status}
        }
        
        media = MediaFileUpload(safe_video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            
        return {"message": "Video uploaded successfully!", "video_id": response.get("id")}
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
