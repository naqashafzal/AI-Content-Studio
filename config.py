"""
config.py

Handles loading and saving of application configuration settings from a JSON file.
"""

import json
import os
import logging

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            logging.error("Configuration file '%s' is corrupted. Loading default config.", CONFIG_FILE)
            config_data = {}
    else:
        config_data = {}

    default_config = {
        "GEMINI_API_KEY": "",
        "WAVESPEED_API_KEY": "",
        "WAVESPEED_IMAGE_MODEL": "black-forest-labs/flux-1.1-pro-ultra",
        "WAVESPEED_VIDEO_MODEL": "wavespeed-ai/ltx-2.3-text-to-video",
        "WAVESPEED_AUDIO_MODEL": "elevenlabs/text-to-speech",
        "NEWS_API_KEY": "",
        "PIXABAY_API_KEY": "",
        "VIDEO_ENGINE": "WaveSpeed AI",
        "IMAGE_ENGINE": "Gemini API",
        "TEXT_ENGINE": "Gemini API",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3",
        "WAVESPEED_TEXT_MODEL": "meta-llama/llama-3.3-70b-instruct",
        "SPEAKER1": "Kore",
        "SPEAKER2": "Puck",
        "HOST_NAME": "Alex",
        "GUEST_NAME": "Maya",
        "HOST_PERSONA": "A friendly podcast host who loves technology.",
        "GUEST_PERSONA": "An expert on the topic with a calm and informative style.",
        "CHANNEL_NAME": "My AI Channel",
        "SUBSCRIBE_COUNT": 3,
        "SUBSCRIBE_MESSAGE": "Don’t forget to subscribe to {channel} for more awesome content!",
        "SUBSCRIBE_RANDOM": True,
        "PODCAST_STYLE": "Informative News",
        "VIDEO_PROMPT_BASE_STYLE": "An animated and cinematic video. High-quality, 24fps.",
        "IMAGE_PROMPT_STYLE": "A cinematic, photorealistic image representing the podcast topic: {topic}",
        "STORY_ARC": "None",
        "API_DELAY": 2,
        "FACT_CHECK_ENABLED": False,
        "CAPTION_ENABLED": False,
        "CAPTION_FONT": "Arial",
        "CAPTION_FONT_SIZE": 22,
        "CAPTION_THEME": "default",
        "GENERATE_METADATA": False,
        "GENERATE_THUMBNAIL": False,
        "GENERATE_TIMED_IMAGES": False,
        "GENERATE_TIMESTAMPS": True,
        "BG_MODE": "AI Video",
        "IMAGE_COUNT": 8,
        "VIDEO_CLIP_COUNT": 1,
        "YOUTUBE_CLIENT_ID": "",
        "YOUTUBE_CLIENT_SECRET": "",
        "FACEBOOK_ACCESS_TOKEN": "",
        "VIDEO_TITLE": "",
        "VIDEO_DESCRIPTION": "",
        "VIDEO_TAGS": "",
        "LANGUAGE_ENABLED": False,
        "PODCAST_LANGUAGE": "English",
        "VIDEO_ASPECT_RATIO": "16:9 (Horizontal)",
        "SCRIPT_LENGTH": "Medium (~5 minutes)",
        "ADD_MUSIC": False,
        "GENERATE_SNIPPETS": False,
        "IMAGE_GENERATION_INTERVAL": 10,
        "TIMED_IMAGES_AS_SLIDESHOW": False,
    }

    config_updated = False
    for key, value in default_config.items():
        if key not in config_data:
            config_data[key] = value
            config_updated = True
    
    if config_updated:
        logging.info("Configuration updated with new default values. Saving.")
        save_config(config_data)

    return config_data

def save_config(config, config_path=CONFIG_FILE):
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logging.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logging.error(f"Error saving config: {e}")

DEFAULT_PIPELINE_STEPS = [
    "Write Script", "Generate Voiceover", "Generate Images", "Video Generation",
    "Add Background Music", "Create Final Video", "Generate SEO Metadata", "Generate Timestamps", "Generate Snippets"
]

VOICE_OPTIONS = {
    "Achernar": "Clear, mid-range, enthusiastic & approachable", "Achird": "Youthful, breathy, inquisitive tone",
    "Algenib": "Warm, confident, friendly authority", "Alnilam": "Energetic, low pitch, promotional tone",
    "Aoede": "Clear, conversational, thoughtful", "Autonoe": "Mature, resonant, calm and wise",
    "Callirrhoe": "Confident, professional, energetic", "Despina": "Warm, inviting, trustworthy",
    "Erinome": "Professional, articulate, thoughtful", "Gacrux": "Authoritative yet approachable",
    "Iapetus": "Casual, relatable, ‘everyman’ tone", "Kore": "Energetic, youthful, clear & bright",
    "Laomedeia": "Inquisitive, intelligent & engaging", "Leda": "Composed, professional, calm",
    "Orus": "Resonant, authoritative, thoughtful", "Puck": "Confident, informal, trustworthy",
    "Pulcherrima": "Bright, enthusiastic, youthful", "Rasalgethi": "Conversational, thoughtful, quirky",
    "Sadachbia": "Deep, textured, confident, cool", "Sadaltager": "Friendly, enthusiastic, professional",
    "Schedar": "Down-to-earth, approachable", "Sulafat": "Warm, persuasive, articulate",
    "Umbriel": "Authoritative, clear, engaging", "Vindemiatrix": "Calm, mature, smooth, reassuring",
    "Zephyr": "Energetic, bright, perky & enthusiastic", "Zubenelgenubi": "Deep, resonant, powerful authority"
}

PODCAST_STYLES = ["Informative News", "Comedy / Entertaining", "Educational / Explainer", "Motivational / Inspiring", "Casual Conversational", "Serious Debate", "Story Mode", "Documentary", "ASMR"]
STORY_ARCS = ["None", "Hero's Journey", "Three-Act Structure", "Man vs. Nature", "Rags to Riches", "Voyage and Return"]
CONTENT_STYLES = ["Podcast", "ASMR Video", "Documentary", "Product Ad", "Story", "Kids Story", "Horror Story", "Viral Video"]
SCRIPT_LENGTHS = ["Micro (< 1 minute)", "Short (~2 minutes)", "Medium (~5 minutes)", "Long (~10 minutes)"]
