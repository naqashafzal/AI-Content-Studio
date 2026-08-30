import uuid
import threading
import time
import logging
from typing import Dict, Any, List
import contextvars
import datetime
import asyncio
from fastapi import WebSocket
import json
from concurrent.futures import ThreadPoolExecutor

# In memory store for now, can be swapped with Redis/SQL later
_JOBS: Dict[str, Dict[str, Any]] = {}

current_job_id = contextvars.ContextVar("current_job_id", default=None)

# ---------------------------------------------------------------------------
# Worker Pool Configuration
# We limit to 2 concurrent generation tasks to prevent resource exhaustion
# ---------------------------------------------------------------------------
worker_pool = ThreadPoolExecutor(max_workers=2)

def submit_to_queue(func, *args, **kwargs):
    """Submits a job to the background worker pool."""
    return worker_pool.submit(func, *args, **kwargs)

# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        # Maps job_id -> list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # We need a reference to the running event loop to broadcast safely
        # from synchronous threads. This should be set on app startup or first use.
        self.loop = None 

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        # Ensure we capture the event loop
        if self.loop is None:
            self.loop = asyncio.get_running_loop()
        
        # Send initial state immediately
        job_state = get_job(job_id)
        if job_state:
            await websocket.send_text(json.dumps({"type": "full_state", "data": job_state}))

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def _send_message_async(self, job_id: str, message: dict):
        if job_id in self.active_connections:
            # Create a copy to avoid modification during iteration
            for connection in list(self.active_connections[job_id]):
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logging.error(f"WebSocket send error: {e}")
                    self.disconnect(connection, job_id)

    def broadcast(self, job_id: str, message: dict):
        """Thread-safe method to send messages to WebSockets from sync code."""
        if not self.active_connections.get(job_id):
            return
            
        # If we are already in an event loop (e.g., normal async route), await it directly.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_message_async(job_id, message))
        except RuntimeError:
            # We are in a synchronous thread (like pipeline running), use threadsafe.
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._send_message_async(job_id, message), self.loop)

manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Custom Logging Handler to Broadcast via WS
# ---------------------------------------------------------------------------
class JobLogHandler(logging.Handler):
    def emit(self, record):
        job_id = current_job_id.get()
        if job_id and job_id in _JOBS:
            msg = self.format(record)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {msg}"
            _JOBS[job_id]["logs"].append(log_line)
            # Broadcast the new log line via WebSockets instantly
            manager.broadcast(job_id, {"type": "log", "data": log_line})

# Setup root logger with the job handler
job_handler = JobLogHandler()
job_handler.setFormatter(logging.Formatter('%(message)s')) # We append timestamp manually above
logging.getLogger().addHandler(job_handler)
logging.getLogger().setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Job Management Methods
# ---------------------------------------------------------------------------
def create_job(topic: str) -> str:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "id": job_id,
        "topic": topic,
        "status": "pending",
        "progress": 0.0,
        "step": "Waiting in queue...",
        "result": None,
        "error": None,
        "logs": [],
        "stop_event": threading.Event()
    }
    return job_id

def update_job(job_id: str, status: str = None, progress: float = None, step: str = None, result: str = None, error: str = None):
    if job_id not in _JOBS:
        return
    job = _JOBS[job_id]
    
    updated = False
    if status is not None and job["status"] != status: 
        job["status"] = status
        updated = True
    if progress is not None and job["progress"] != progress: 
        job["progress"] = progress
        updated = True
    if step is not None and job["step"] != step: 
        job["step"] = step
        updated = True
    if result is not None: 
        job["result"] = result
        updated = True
    if error is not None: 
        job["error"] = error
        updated = True
        
    if updated:
        # Broadcast minimal state update
        manager.broadcast(job_id, {
            "type": "update",
            "data": {
                "status": job["status"],
                "progress": job["progress"],
                "step": job["step"],
                "result": job["result"],
                "error": job["error"]
            }
        })

def add_log(job_id: str, msg: str):
    # This is an explicit manual log addition (e.g. from a tool)
    if job_id in _JOBS:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {msg}"
        _JOBS[job_id]["logs"].append(log_line)
        manager.broadcast(job_id, {"type": "log", "data": log_line})

def get_job(job_id: str) -> Dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        return None
    # Don't serialize the stop event
    return {k: v for k, v in job.items() if k != "stop_event"}

def stop_job(job_id: str):
    if job_id in _JOBS:
        _JOBS[job_id]["stop_event"].set()
        _JOBS[job_id]["status"] = "cancelled"
        update_job(job_id, status="cancelled") # trigger broadcast
