import os
import yt_dlp
import logging

def download_youtube_video(url: str, output_dir: str, max_duration_mins: int = 120) -> str:
    """
    Downloads a YouTube video to the output_dir.
    Returns the path to the downloaded .mp4 file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # We want a decent quality but not necessarily 4K since we are cropping for shorts
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'match_filter': lambda info, *args, **kwargs: 'Video is too long' if info.get('duration', 0) > (max_duration_mins * 60) else None,
        'quiet': False,
        'no_warnings': True,
    }

    logging.info(f"[Clipper] Downloading YouTube video: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_id = info_dict.get("id", None)
        ext = info_dict.get("ext", "mp4")
        
        filepath = os.path.join(output_dir, f"{video_id}.{ext}")
        if not os.path.exists(filepath):
            # Fallback if outtmpl resulted in something else
            filepath = ydl.prepare_filename(info_dict)
            
        logging.info(f"[Clipper] Download complete: {filepath}")
        return filepath
