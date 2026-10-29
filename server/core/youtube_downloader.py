import os
import glob
import logging
import yt_dlp
from typing import Optional
from config import load_config

def _find_cookie_file() -> Optional[str]:
    """Finds cookies.txt file if present in workspace or root."""
    config = load_config()
    configured_path = config.get("YOUTUBE_COOKIES_FILE", "")
    if configured_path and os.path.exists(configured_path):
        return configured_path
    
    candidates = [
        "cookies.txt",
        "youtube_cookies.txt",
        os.path.join("workspace", "cookies.txt"),
        os.path.join("workspace", "youtube_cookies.txt"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None

def download_youtube_video(url: str, output_dir: str, max_duration_mins: int = 120) -> str:
    """
    Downloads a YouTube video to output_dir with anti-bot bypass strategies.
    Uses multi-client cascades (Android / iOS / mweb / TV) and optional cookie integration
    to bypass 'Sign in to confirm you're not a bot' challenges.
    """
    os.makedirs(output_dir, exist_ok=True)
    config = load_config()
    
    cookie_file = _find_cookie_file()
    browser_cookies = config.get("YOUTUBE_COOKIES_BROWSER", "").strip() or None

    # Client cascades ordered by anti-bot resilience
    strategies = [
        # Strategy 1: Mobile clients (Android + iOS) - very resilient against web bot detection
        {"player_client": ["android", "ios"], "name": "Mobile API (Android/iOS)"},
        # Strategy 2: TV & Mobile Web clients
        {"player_client": ["tv", "mweb"], "name": "Embedded/TV API"},
        # Strategy 3: Web creator + Web
        {"player_client": ["web_creator", "web"], "name": "Web Creator API"},
    ]

    last_error = None
    for strat in strategies:
        client_list = strat["player_client"]
        strat_name = strat["name"]
        logging.info(f"[Clipper] Attempting YouTube download via {strat_name}: {url}")
        
        ydl_opts = {
            # Prefer 1080p/720p mp4, merge audio+video into mp4
            "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "match_filter": lambda info, *args, **kwargs: (
                "Video is too long" if info.get("duration", 0) > (max_duration_mins * 60) else None
            ),
            "extractor_args": {
                "youtube": {
                    "player_client": client_list
                }
            },
            "quiet": False,
            "no_warnings": False,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "retries": 3,
            "fragment_retries": 3,
        }

        # Apply cookies if present
        if cookie_file:
            logging.info(f"[Clipper] Using YouTube cookies from {cookie_file}")
            ydl_opts["cookiefile"] = cookie_file
        elif browser_cookies:
            logging.info(f"[Clipper] Using browser cookies from {browser_cookies}")
            ydl_opts["cookiesfrombrowser"] = (browser_cookies,)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                if not info_dict:
                    raise RuntimeError("yt_dlp returned empty info dictionary.")
                    
                video_id = info_dict.get("id")
                # Locate downloaded file (could be .mp4 or .mkv before/after remux)
                if video_id:
                    possible_files = glob.glob(os.path.join(output_dir, f"{video_id}.*"))
                    for pf in possible_files:
                        if pf.lower().endswith((".mp4", ".mkv", ".webm")) and os.path.getsize(pf) > 0:
                            logging.info(f"[Clipper] Download complete ({strat_name}): {pf}")
                            return os.path.abspath(pf)
                
                prepared = ydl.prepare_filename(info_dict)
                if os.path.exists(prepared) and os.path.getsize(prepared) > 0:
                    logging.info(f"[Clipper] Download complete: {prepared}")
                    return os.path.abspath(prepared)
                    
        except Exception as e:
            err_msg = str(e)
            last_error = e
            logging.warning(f"[Clipper] Download strategy {strat_name} failed: {err_msg[:200]}")
            # If it's a duration limit violation, don't retry with other clients
            if "Video is too long" in err_msg:
                raise e
            continue

    # If all cascades failed, try one last attempt with local browser cookies auto-detection if on Windows/Mac
    if not cookie_file and not browser_cookies:
        for auto_browser in ("chrome", "edge", "firefox"):
            try:
                logging.info(f"[Clipper] Trying browser cookie auto-detection from {auto_browser}...")
                fallback_opts = {
                    "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[height<=1080]/best",
                    "merge_output_format": "mp4",
                    "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
                    "cookiesfrombrowser": (auto_browser,),
                    "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
                    "quiet": True,
                    "no_warnings": True,
                }
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    video_id = info_dict.get("id")
                    if video_id:
                        possible = glob.glob(os.path.join(output_dir, f"{video_id}.*"))
                        for pf in possible:
                            if pf.lower().endswith((".mp4", ".mkv", ".webm")) and os.path.getsize(pf) > 0:
                                logging.info(f"[Clipper] Download succeeded with {auto_browser} cookies: {pf}")
                                return os.path.abspath(pf)
            except Exception:
                continue

    raise RuntimeError(
        f"Failed to download YouTube video. YouTube bot protection active. Details: {last_error}"
    )
