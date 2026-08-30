from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
import os
import pickle
import traceback
import json

router = APIRouter()

class PublishRequest(BaseModel):
    video_path: str
    title: str
    description: str
    tags: str
    privacy_status: str = "private"

@router.get("/library")
def get_publishing_library():
    workspace_dir = "workspace"
    if not os.path.exists(workspace_dir):
        return {"projects": []}
        
    projects = []
    # Sort folders by creation time descending (newest first)
    try:
        folders = sorted(os.listdir(workspace_dir), key=lambda x: os.path.getctime(os.path.join(workspace_dir, x)), reverse=True)
    except:
        folders = os.listdir(workspace_dir)

    for folder in folders:
        folder_path = os.path.join(workspace_dir, folder)
        if not os.path.isdir(folder_path):
            continue
            
        video_file = os.path.join(folder_path, "final_podcast.mp4")
        if not os.path.exists(video_file):
            video_file = os.path.join(folder_path, "final_podcast_video.mp4")
            if not os.path.exists(video_file):
                continue # Only show projects that actually finished video generation
                
        # Parse SEO
        seo_data = {"title": folder, "description": "", "tags": ""}
        seo_json_path = os.path.join(folder_path, "seo_metadata.json")
        if os.path.exists(seo_json_path):
            try:
                with open(seo_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    seo_data["title"] = data.get("title", folder)
                    seo_data["description"] = data.get("description", "")
                    tags = data.get("tags", [])
                    if isinstance(tags, list):
                        seo_data["tags"] = ", ".join(tags)
                    else:
                        seo_data["tags"] = str(tags)
            except Exception as e:
                print(f"Error reading {seo_json_path}: {e}")
                
        # Append Timestamps to description if they exist
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
            "name": folder.replace("_", " ").title(),
            "path": folder_path,
            "video_path": video_file,
            "seo": seo_data
        })
        
    return {"projects": projects}

@router.post("/youtube")
def publish_to_youtube(req: PublishRequest):
    if not req.video_path or not os.path.exists(req.video_path):
        raise HTTPException(status_code=400, detail="Invalid video path.")
        
    if not os.path.exists("client_secrets.json"):
        raise HTTPException(status_code=400, detail="client_secrets.json not found! Please download your OAuth 2.0 Client IDs from Google Cloud Console.")
        
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        
        credentials = None
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                credentials = pickle.load(token)
                
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secrets.json", 
                    scopes=["https://www.googleapis.com/auth/youtube.upload"],
                    redirect_uri='http://localhost:8080/'
                )
                # This will open a browser window on the server.
                # In a real headless server, you'd need a different OAuth flow.
                # For this local desktop app, run_local_server is fine.
                credentials = flow.run_local_server(port=8080)
            with open("token.pickle", "wb") as f:
                pickle.dump(credentials, f)
                
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
        
        media = MediaFileUpload(req.video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            # Could stream progress here using websockets or SSE, but for simplicity we block.
            
        return {"message": "Video uploaded successfully!", "video_id": response.get("id")}
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
