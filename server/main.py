import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import generation
from server.routers import generation, publish, tools, brand, studio, campaigns, clipper, director

# Ensure workspace dir exists
os.makedirs("workspace", exist_ok=True)

app = FastAPI(
    title="AI Content Studio Engine",
    description="Scalable backend API for AI video generation",
    version="2.0.0"
)

from server.core.scheduler import start_scheduler

@app.on_event("startup")
def on_startup():
    start_scheduler()

# Allow Next.js frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generation.router, prefix="/api/generate", tags=["Generation"])

from server.routers import clipper
app.include_router(clipper.router, prefix="/api/clipper", tags=["Clipper"])

from server.routers import videofx
app.include_router(videofx.router, prefix="/api/videofx", tags=["VideoFX Flow"])

from server.routers import director
app.include_router(director.router, prefix="/api/director", tags=["Director"])

from server.routers import explainer
app.include_router(explainer.router, prefix="/api/explainer", tags=["Explainer"])

from server.routers import brand
app.include_router(brand.router, prefix="/api/brand", tags=["Brand"])

from server.routers import tools
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])

from server.routers import publish
app.include_router(publish.router, prefix="/api/publish", tags=["Publish"])

from server.routers import studio
app.include_router(studio.router, prefix="/api/studio", tags=["Studio"])

from server.routers import campaigns
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])

from server.routers import social
app.include_router(social.router, prefix="/api/social", tags=["Social"])

from config import load_config, save_config

@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def update_config(new_config: dict):
    # Load current config to ensure we don't overwrite everything blindly
    current = load_config()
    current.update(new_config)
    save_config(current)
    return {"message": "Configuration updated successfully."}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AI Content Studio Engine"}

if __name__ == "__main__":
    import uvicorn
    # Run the server
    uvicorn.run("server.main:app", host="0.0.0.0", port=8008, reload=True)
