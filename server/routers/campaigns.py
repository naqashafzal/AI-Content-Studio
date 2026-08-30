from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from server.core.scheduler import campaign_mgr

router = APIRouter()

class CampaignCreate(BaseModel):
    name: str
    niche: str
    preset: str
    frequency_hours: float

@router.get("/")
def get_campaigns():
    return {"campaigns": campaign_mgr.get_campaigns()}

@router.post("/")
def create_campaign(req: CampaignCreate):
    try:
        c = campaign_mgr.add_campaign(req.name, req.niche, req.preset, req.frequency_hours)
        return {"message": "Campaign created", "campaign": c}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{cid}/toggle")
def toggle_campaign(cid: str):
    c = campaign_mgr.toggle(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Toggled", "campaign": c}

@router.delete("/{cid}")
def delete_campaign(cid: str):
    campaign_mgr.delete(cid)
    return {"message": "Deleted"}
