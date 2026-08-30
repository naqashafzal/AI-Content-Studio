import os
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime

from server.core.database import get_db, OAuthToken
from config import load_config

router = APIRouter()

# Note: In production, the client secrets should be securely loaded from env vars.
# For demo purposes, we will mock the YouTube OAuth flow so the UI works correctly.

@router.get("/status")
def get_social_status(db: Session = Depends(get_db)):
    """Returns the connection status of all social platforms."""
    tokens = db.query(OAuthToken).all()
    connected = {t.platform: True for t in tokens if t.access_token}
    
    return {
        "youtube": connected.get("youtube", False),
        "tiktok": connected.get("tiktok", False),
        "instagram": connected.get("instagram", False)
    }

@router.get("/youtube/auth")
def youtube_auth_url():
    """Returns a mock URL to start the YouTube OAuth flow."""
    # In a real app, you would use google_auth_oauthlib.flow.Flow.from_client_secrets_file
    return {"auth_url": "http://localhost:3000/publish?mock_oauth=youtube"}

@router.post("/youtube/callback")
def youtube_callback(request_data: dict, db: Session = Depends(get_db)):
    """Mocks receiving the OAuth code and saving a dummy token to SQLite."""
    code = request_data.get("code", "dummy_code")
    
    token_entry = db.query(OAuthToken).filter(OAuthToken.platform == "youtube").first()
    if not token_entry:
        token_entry = OAuthToken(platform="youtube")
        db.add(token_entry)
        
    token_entry.access_token = f"mock_access_{code}"
    token_entry.refresh_token = f"mock_refresh_{code}"
    token_entry.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "YouTube connected successfully."}

@router.post("/tiktok/auth")
def tiktok_auth_url():
    return {"auth_url": "http://localhost:3000/publish?mock_oauth=tiktok"}

@router.post("/instagram/auth")
def instagram_auth_url():
    return {"auth_url": "http://localhost:3000/publish?mock_oauth=instagram"}
    
@router.post("/publish/youtube")
def publish_to_youtube(video_data: dict, db: Session = Depends(get_db)):
    """Mocks the YouTube upload process."""
    token = db.query(OAuthToken).filter(OAuthToken.platform == "youtube").first()
    if not token or not token.access_token:
        raise HTTPException(status_code=401, detail="YouTube account not connected.")
        
    # In reality, use googleapiclient.discovery.build('youtube', 'v3', credentials=creds)
    # and MediaFileUpload(video_data['video_path'])
    
    return {"message": "Video successfully uploaded to YouTube!", "video_id": "mock_id_123"}
