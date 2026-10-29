# Deployment

This deployment is a single administrator Studio. All authenticated browsers share
configuration, jobs, media, and publishing accounts. It does not provide tenant
isolation. Run one backend process per data directory; startup enforces this.

## Existing installations

Stop the old server and back up the repository's generated data first. Run:

```sh
python scripts/migrate_data.py
```

This copies the old SQLite database, configuration, OAuth token, campaigns, and
VideoFX browser profile to `data/` without replacing existing destination files.
Google client credentials are imported into the private config. Keep old files
as backups until the new deployment has been verified. Never serve `data/` as a
static directory. Media download routes also reject database and JSON files.

## Compose

1. Copy `.env.example` to `.env`. Set a long random `STUDIO_API_TOKEN` and the
   actual `STUDIO_PUBLIC_ORIGIN` (for example `https://studio.example.com`). Generate
   a token with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`.
2. Create `data`, `workspace`, `outputs`, `assets`, `agent_workspace`, and
   `videofx_outputs`. The backend runs as UID/GID 1000; make these directories
   writable by that account. Keep `data/` private (`0700`).
3. Run `docker compose up --build -d`. Backend and frontend ports are internal;
   the proxy listens only on host loopback port 8080.
4. Put your HTTPS reverse proxy in front of `127.0.0.1:8080`, preserving Host and
   WebSocket upgrade headers. Sign in at `/login` with the Studio token. Secure
   cookies are enabled by default. For a local HTTP evaluation only, set
   `STUDIO_SECURE_COOKIES=false` and origin `http://localhost:8080`.

Frontend URLs use the browser's origin. API calls, media, and WebSockets all go
through the same proxy; no public API token is compiled into JavaScript. The
proxy limits uploads and login attempts. The application additionally limits
request bodies, including chunked uploads, and deletes partial oversized files.

All persistent directories are mounted. Back up `data/` and media together while
jobs are stopped; use SQLite's backup API for a live database backup. Rotating
`STUDIO_API_TOKEN` and restarting the backend invalidates existing sessions.

## Local development

Use Python 3.12, Node 22+, and FFmpeg. Install `requirements.lock` and run
`npm ci` inside `web/`. Set `STUDIO_SECURE_COOKIES=false` for HTTP development,
then start the backend on port 8008 and the frontend on port 3000. Next.js proxies
`/api/` to `127.0.0.1:8008`. Set `CORS_ORIGINS=http://localhost:3000` when needed.
When `STUDIO_API_TOKEN` is unset, a private token is generated in
`data/studio-token`; use it at `/login`. Authentication is never disabled.

For a backend elsewhere, set `STUDIO_BACKEND_URL` before building Next.js. The
Compose reverse proxy routes WebSockets directly; use that proxy if a development
Next.js server does not forward a WebSocket upgrade in your environment.

## YouTube

Configure `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` through the authenticated
`POST /api/config` endpoint (or migrate an existing `client_secrets.json`). Register
`${STUDIO_PUBLIC_ORIGIN}/api/social/youtube/callback` as the exact Google OAuth web
redirect URI. Compose sets `YOUTUBE_REDIRECT_URI` to that URL. The callback uses
GET, a browser-bound expiring state value, and single-use state consumption.
Actual OAuth and uploads require your Google credentials and consent setup.

## Job recovery

Work is committed to SQLite before submission. Queued tasks are resubmitted when
the server starts. Interrupted running work is marked `interrupted`; it is never
automatically repeated because provider calls can charge or produce side effects.
Use authenticated `POST /api/jobs/{job_id}/retry` to retry a failed or interrupted
job from its saved arguments. Storyboard orchestration retains its existing stage
checkpoints; other pipelines can repeat earlier work when explicitly retried.
A job cannot have two active tasks. Queue admission is capped at 100 tasks and two
worker threads. Shutdown waits for workers before releasing the process lock.

## Checks

```sh
pip install -r requirements.lock
pip check
pytest tests/ -q
cd web
npm ci
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
```

GitHub Actions runs these checks. Lint fails on errors or warnings.
Changes still need a staging run with real provider credentials before launch.
