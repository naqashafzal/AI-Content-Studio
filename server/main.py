import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from server.routers import (
    generation, publish, tools, brand, studio,
    campaigns, clipper, director, videofx,
    explainer, social, style, timeline
)
from server.core.scheduler import start_scheduler
from server.core.queue import stop_job
from server.core.model_gateway import gateway
from config import load_config, save_config

# Ensure workspace and output directories exist
for d in ("workspace", "outputs", "agent_workspace", "assets", "videofx_outputs"):
    os.makedirs(d, exist_ok=True)

from contextlib import asynccontextmanager
from filelock import FileLock, Timeout
from server.core.security import DATA_DIR, required_token
from server.core.queue import recover_pending_tasks, start_workers, shutdown_workers
import asyncio
from server.core.scheduler import stop_scheduler

@asynccontextmanager
async def lifespan(app):
    required_token()
    lock = FileLock(str(DATA_DIR / "server.lock"))
    try:
        lock.acquire(timeout=0)
    except Timeout:
        raise RuntimeError("Run exactly one backend worker per data directory")
    try:
        start_workers()
        recover_pending_tasks()
        start_scheduler()
        yield
    finally:
        await asyncio.to_thread(stop_scheduler)
        await asyncio.to_thread(shutdown_workers)
        lock.release()

app = FastAPI(
    lifespan=lifespan,
    title="AI Content Studio Engine",
    description="Scalable backend API for AI video generation",
    version="2.0.0"
)


# Restricted CORS configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8008",
        "http://127.0.0.1:8008"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

from server.core.security import authenticated, required_token, COOKIE_NAME
from fastapi import Form, HTTPException
from fastapi.responses import RedirectResponse
import hmac

@app.middleware("http")
async def api_token_auth_middleware(request: Request, call_next):
    public = {"/health", "/api/session", "/api/social/youtube/callback"}
    if request.method != "OPTIONS" and request.url.path.startswith("/api/") and request.url.path not in public:
        if not authenticated(request):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        # Cookie-authenticated writes must come from this site or an explicit CORS origin.
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD") and origin:
            if origin.rstrip("/") not in allowed_origins + [str(request.base_url).rstrip("/")]:
                return JSONResponse(status_code=403, content={"detail": "Invalid origin"})
    return await call_next(request)

@app.post("/api/session")
def login(request: Request, token: str = Form(...)):
    if not hmac.compare_digest(token.encode(), required_token().encode()):
        raise HTTPException(401, "Invalid token")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in allowed_origins + [str(request.base_url).rstrip("/")]:
        raise HTTPException(403, "Invalid origin")
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict",
                        secure=os.getenv("STUDIO_SECURE_COOKIES", "true").lower() == "true", max_age=43200)
    return response

@app.delete("/api/session")
def logout():
    response = JSONResponse({"message": "Signed out"})
    response.delete_cookie(COOKIE_NAME)
    return response

# Include routers
app.include_router(generation.router, prefix="/api/generate", tags=["Generation"])
app.include_router(clipper.router, prefix="/api/clipper", tags=["Clipper"])
app.include_router(videofx.router, prefix="/api/videofx", tags=["VideoFX Flow"])
app.include_router(director.router, prefix="/api/director", tags=["Director"])
app.include_router(explainer.router, prefix="/api/explainer", tags=["Explainer"])
app.include_router(brand.router, prefix="/api/brand", tags=["Brand"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])
app.include_router(publish.router, prefix="/api/publish", tags=["Publish"])
app.include_router(studio.router, prefix="/api/studio", tags=["Studio"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(social.router, prefix="/api/social", tags=["Social"])
# Mount both /api/styles and /api/style so singular & plural frontend calls succeed
app.include_router(style.router, prefix="/api/styles", tags=["Style Engine"])
app.include_router(style.router, prefix="/api/style", tags=["Style Engine"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["Timeline Editor"])

@app.post("/api/cancel/{job_id}")
def cancel_job_alias(job_id: str):
    """Alias route for job cancellation."""
    stop_job(job_id)
    return {"message": f"Cancellation requested for {job_id}"}

@app.get("/api/config")
def get_config():
    # Never expose unmasked secrets to the browser
    return load_config(masked=True)

@app.post("/api/config")
def update_config(new_config: dict):
    # Load current config to merge updates safely without clobbering with masked placeholders
    current = load_config()
    current.update(new_config)
    save_config(current)
    gateway.refresh_config()
    return {"message": "Configuration updated successfully."}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AI Content Studio Engine"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8008, reload=False)

@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str):
    from server.core.queue import retry_interrupted_task
    retry_interrupted_task(job_id)
    return {"job_id": job_id, "message": "Job queued for retry"}

from server.core.security import RequestSizeLimit
app.add_middleware(RequestSizeLimit)

@app.get("/api/jobs")
def recent_jobs():
    from server.core.queue import list_jobs
    return list_jobs()
