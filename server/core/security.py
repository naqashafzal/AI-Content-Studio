"""Shared HTTP/WebSocket authentication and bounded media storage."""
import hmac
import os
import secrets
from pathlib import Path
from fastapi import HTTPException

DATA_DIR = Path(os.getenv("STUDIO_DATA_DIR", "data"))
COOKIE_NAME = "studio_session"
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ass", ".srt"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(256 * 1024 * 1024)))

def required_token():
    token = os.getenv("STUDIO_API_TOKEN")
    if token:
        return token
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = DATA_DIR / "studio-token"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_urlsafe(32))
    token = path.read_text().strip()
    if not token:
        raise RuntimeError("Studio authentication token is empty")
    return token

def authenticated(connection):
    expected = required_token()
    authorization = connection.headers.get("authorization", "")
    bearer = authorization[7:] if authorization.startswith("Bearer ") else ""
    return any(hmac.compare_digest(value.encode(), expected.encode()) for value in (
        connection.headers.get("x-api-key", ""), bearer,
        connection.cookies.get(COOKIE_NAME, "")))

def media_path(value, roots=None):
    roots = roots or ("workspace", "outputs", "agent_workspace", "assets", "videofx_outputs")
    path = Path(value.strip()).resolve()
    allowed = [Path(root).resolve() for root in roots]
    if not any(path.is_relative_to(root) for root in allowed):
        path = (Path("workspace") / value.lstrip("/\\")).resolve()
    if not any(path.is_relative_to(root) for root in allowed) or path.suffix.lower() not in MEDIA_EXTENSIONS:
        raise HTTPException(403, "Access denied: not an allowed media file")
    if not path.is_file():
        raise HTTPException(404, "Media file not found")
    return str(path)

def copy_upload(source, destination):
    """Never retain a partial file after an oversized or failed upload."""
    total = 0
    try:
        with open(destination, "wb") as output:
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Upload exceeds the configured limit")
                output.write(chunk)
    except BaseException:
        Path(destination).unlink(missing_ok=True)
        raise

class RequestSizeLimit:
    """Bound bodies before multipart parsing, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse
        from tempfile import SpooledTemporaryFile
        limit = MAX_UPLOAD_BYTES + 1024 * 1024
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length"}, 400)(scope, receive, send)
        if length > limit:
            return await JSONResponse({"detail": "Request body too large"}, 413)(scope, receive, send)
        total = 0
        with SpooledTemporaryFile(max_size=1024 * 1024) as body:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > limit:
                    return await JSONResponse({"detail": "Request body too large"}, 413)(scope, receive, send)
                body.write(chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            delivered = 0
            finished = False

            async def replay():
                nonlocal delivered, finished
                if finished:
                    return await receive()
                chunk = body.read(1024 * 1024)
                delivered += len(chunk)
                finished = delivered >= total
                return {"type": "http.request", "body": chunk, "more_body": not finished}

            await self.app(scope, replay, send)
