import os
import json
import time
import threading
import uuid
import datetime
import traceback
import logging

from config import load_config
from agents import TrendAgent
from server.core.queue import create_job, submit_to_queue
from server.routers.generation import run_pipeline_task, GenerationRequest

CAMPAIGNS_FILE = "campaigns.json"

class CampaignManager:
    def __init__(self):
        self.campaigns = []
        self.load()

    def load(self):
        if os.path.exists(CAMPAIGNS_FILE):
            try:
                with open(CAMPAIGNS_FILE, "r") as f:
                    self.campaigns = json.load(f)
            except Exception as e:
                print(f"Error loading campaigns: {e}")
                self.campaigns = []

    def save(self):
        with open(CAMPAIGNS_FILE, "w") as f:
            json.dump(self.campaigns, f, indent=4)

    def add_campaign(self, name, niche, preset, frequency_hours):
        c = {
            "id": str(uuid.uuid4()),
            "name": name,
            "niche": niche,
            "preset": preset,
            "frequency_hours": float(frequency_hours),
            "next_run": time.time(), # Run immediately on creation
            "active": True,
            "last_run": None,
            "last_topic": None
        }
        self.campaigns.append(c)
        self.save()
        return c

    def get_campaigns(self):
        return self.campaigns

    def toggle(self, cid):
        for c in self.campaigns:
            if c["id"] == cid:
                c["active"] = not c["active"]
                self.save()
                return c
        return None

    def delete(self, cid):
        self.campaigns = [c for c in self.campaigns if c["id"] != cid]
        self.save()

campaign_mgr = CampaignManager()

class DummyUI:
    def log_to_agent_console(self, msg): pass
    def update_agent_node(self, name, status, state): pass

def scheduler_loop():
    while True:
        try:
            now = time.time()
            for c in campaign_mgr.campaigns:
                if c["active"] and now >= c.get("next_run", 0):
                    logging.info(f"[Auto-Pilot] Campaign '{c['name']}' triggered! Fetching topic in niche: {c['niche']}")
                    
                    try:
                        # 1. Fetch a viral topic via TrendAgent
                        config = load_config()
                        # Pass niche to TrendAgent by wrapping it in a custom prompt or just relying on its logic
                        # For simplicity, we just use the niche directly as the topic or prefix it
                        # TrendAgent usually gets generic topics, but we'll adapt:
                        trend = TrendAgent(config, DummyUI(), "TrendAgent")
                        # Override the find_viral_topics locally to use the niche
                        prompt = f"Generate 1 highly engaging viral video title about: {c['niche']}. Output only the title."
                        topic = trend.google_client._generate_text(prompt).strip().strip('"').strip("'")
                        
                        logging.info(f"[Auto-Pilot] Selected topic: {topic}")
                        
                        # 2. Build GenerationRequest based on preset
                        # Defaults
                        req = GenerationRequest(
                            topic=topic,
                            start_point="Deep Research",
                            content_style="Podcast",
                            style="Cinematic Documentary",
                            voice="Kore",
                            aspect_ratio="16:9",
                            omnichannel=False,
                            bg_music=True,
                            auto_captions=True,
                            generate_seo=True,
                            generate_timestamps=True
                        )
                        
                        if c["preset"] == "Tech News Short":
                            req.content_style = "Viral Video"
                            req.style = "TikTok Viral"
                            req.aspect_ratio = "9:16"
                            req.omnichannel = True
                        elif c["preset"] == "Scary Story":
                            req.content_style = "Story"
                            req.voice = "Charon"
                            req.aspect_ratio = "9:16"
                        elif c["preset"] == "Motivation / Hustle":
                            req.content_style = "Viral Video"
                            req.style = "Cyberpunk / Neon"
                            req.voice = "Fenrir"
                            req.aspect_ratio = "9:16"
                            req.omnichannel = True
                            
                        # 3. Submit to queue
                        job_id = create_job(req.topic)
                        submit_to_queue(run_pipeline_task, job_id, req)
                        logging.info(f"[Auto-Pilot] Job {job_id} queued successfully for campaign '{c['name']}'.")
                        
                        # 4. Update campaign
                        c["last_run"] = now
                        c["last_topic"] = topic
                        c["next_run"] = now + (c["frequency_hours"] * 3600)
                        campaign_mgr.save()
                        
                    except Exception as e:
                        logging.error(f"[Auto-Pilot] Campaign '{c['name']}' failed: {e}")
                        # Push next run back slightly to avoid rapid retry loops on failure
                        c["next_run"] = now + 300 # Try again in 5 minutes
                        campaign_mgr.save()
                        
        except Exception as e:
            traceback.print_exc()
            
        time.sleep(60) # Check every 1 minute

def start_scheduler():
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    logging.info("[Auto-Pilot] Autonomous Scheduler Engine started.")
