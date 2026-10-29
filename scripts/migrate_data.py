"""Copy legacy state into data/ before the first Compose deployment; never overwrite."""
import json
import os
from pathlib import Path
import shutil
import sqlite3

root = Path(__file__).resolve().parents[1]
data = root / "data"
data.mkdir(mode=0o700, exist_ok=True)
for name in ("config.json", "token.json", "campaigns.json"):
    source, destination = root / name, data / name
    if source.is_file() and not destination.exists():
        shutil.copy2(source, destination)
        destination.chmod(0o600)
source, destination = root / "workspace/app.db", data / "app.db"
if source.is_file() and not destination.exists():
    with sqlite3.connect(source) as old, sqlite3.connect(destination) as new:
        old.backup(new)
    destination.chmod(0o600)
profile = root / "server/core/videofx_profile"
if profile.is_dir() and not (data / "videofx_profile").exists():
    shutil.copytree(profile, data / "videofx_profile")
client_secrets = root / "client_secrets.json"
if client_secrets.is_file():
    config_path = data / "config.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    document = json.loads(client_secrets.read_text())
    client = document.get("web") or document.get("installed") or {}
    for key, source in (("YOUTUBE_CLIENT_ID", "client_id"), ("YOUTUBE_CLIENT_SECRET", "client_secret")):
        if not config.get(key):
            config[key] = client.get(source, "")
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(config, stream, indent=2)
print("State copied to data/. Existing destination files were preserved; keep legacy files as backups until verified.")
