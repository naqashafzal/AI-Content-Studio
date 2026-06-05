"""
main.py

This is the main entry point for the Content Automation application.
It builds the GUI, handles user interactions, and orchestrates the pipeline.
This version includes a custom logging handler to display console output
directly within the application's UI and a button to check API quotas.
"""

import sys
print(f"--- Running application with Python from: {sys.executable}")
import os
import threading
import logging
import webbrowser
import shutil
import re
import requests
from tkinter import messagebox, filedialog
import pickle
from pathlib import Path
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

import customtkinter as ctk


# Google Auth Imports
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Modular components
from config import load_config, save_config
from pipeline import Pipeline
from api_clients import GoogleClient, NewsApiClient

# --- Constants for GUI Dropdowns ---
PIPELINE_STEPS = [
    "Deep Research",
    "Fact Check Research",
    "Revise Research",
    "Podcast Script",
    "Generate Thumbnail",
    "Analyze Tone",
    "Audio (TTS)",
    "Generate Timed Images",
    "Video Generation",
    "Add Background Music", 
    "Create Final Video",
    "Generate SEO Metadata",   # <-- MOVED UP
    "Generate Timestamps",     # <-- MOVED DOWN
    "Generate Snippets"
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
SCRIPT_LENGTHS = ["Short (~2 minutes)", "Medium (~5 minutes)", "Long (~10 minutes)"]


# --- Custom Logging Handler ---
class TextboxHandler(logging.Handler):
    """A custom logging handler that redirects logs to a CTkTextbox widget."""
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox

    def emit(self, record):
        """Writes the log message to the textbox."""
        msg = self.format(record)
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")


class ScriptEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent, script_content, file_path, resume_event):
        super().__init__(parent)
        self.title("📝 Script Editor & Review")
        self.geometry("800x600")
        self.attributes("-topmost", True)
        
        self.file_path = file_path
        self.resume_event = resume_event
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="Review and edit the generated script before continuing.", font=("Arial", 14, "bold")).grid(row=0, column=0, pady=10, padx=10, sticky="w")
        
        self.textbox = ctk.CTkTextbox(self, font=("Arial", 14), wrap="word")
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.textbox.insert("1.0", script_content)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=10)
        
        ctk.CTkButton(btn_frame, text="✅ Approve & Continue", fg_color="#00E5FF", text_color="#0A0A0A", hover_color="#00B3CC", font=("Arial", 14, "bold"), command=self.approve_script).pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def approve_script(self):
        edited_script = self.textbox.get("1.0", "end-1c")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(edited_script)
        logging.info("Script approved by user. Resuming pipeline...")
        self.resume_event.set()
        self.destroy()
        
    def on_close(self):
        logging.warning("Script editor closed without approval. Proceeding with unedited script.")
        self.resume_event.set()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎙️ Nullpk Content Automation")
        self.geometry("1100x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("cyberpunk.json")

        self.config = load_config()
        self.stop_event = threading.Event()
        self.progress_bars = []
        self.step_status_labels = []

        self._create_widgets()
        self.setup_logging()
        self.load_settings_into_gui()
        self.update_history_tab()

    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        if logger.hasHandlers(): logger.handlers.clear()
        handler = TextboxHandler(self.log_box)
        handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(handler)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(stream_handler)
        logging.info("Logging configured. Application started.")

    def _create_widgets(self):
        # Configure layout (1 row x 2 cols)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Build Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#0A0A0E")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="⚡ NULLPK V4", font=ctk.CTkFont(family="Consolas", size=22, weight="bold"), text_color="#00E5FF")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))
        
        self.sidebar_buttons = {}
        for i, name in enumerate(["Main", "Agent Studio", "Settings", "Publish", "Tools", "History", "About"]):
            btn = ctk.CTkButton(self.sidebar_frame, corner_radius=8, height=45, border_spacing=15, 
                                text=f"■ {name}", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
                                fg_color="transparent", text_color="#8F8F99", 
                                hover_color="#181824", anchor="w",
                                command=lambda n=name: self.select_frame_by_name(n))
            btn.grid(row=i+1, column=0, sticky="ew", padx=10, pady=5)
            self.sidebar_buttons[name] = btn

        # Main Content Frame
        self.main_content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)

        # Content frames instead of tabs
        self.main_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.agent_studio_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.settings_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.publish_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.tools_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.history_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.about_tab = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")

        self.frames = {
            "Main": self.main_tab,
            "Agent Studio": self.agent_studio_tab,
            "Settings": self.settings_tab,
            "Publish": self.publish_tab,
            "Tools": self.tools_tab,
            "History": self.history_tab,
            "About": self.about_tab
        }

        self._create_main_tab_widgets()
        self._create_agent_studio_widgets()
        self._create_settings_tab_widgets()
        self._create_publish_tab_widgets()
        self._create_tools_tab_widgets()
        self._create_about_tab_widgets()

        self.select_frame_by_name("Main")

    def select_frame_by_name(self, name):
        for btn_name, btn in self.sidebar_buttons.items():
            btn.configure(fg_color="#181824" if btn_name == name else "transparent",
                          text_color="#00E5FF" if btn_name == name else "#8F8F99")
                
        for frame_name, frame in self.frames.items():
            if frame_name == name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

    def _create_agent_studio_widgets(self):
        self.agent_studio_tab.columnconfigure(0, weight=1)
        self.agent_studio_tab.rowconfigure(2, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self.agent_studio_tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(header_frame, text="AI Agent Studio", font=("Arial", 24, "bold"), text_color="#00E5FF").pack(side="left")
        ctk.CTkLabel(header_frame, text="Full Production House Workflow", font=("Arial", 14)).pack(side="left", padx=15, pady=5)
        
        # Topic Input
        input_frame = ctk.CTkFrame(self.agent_studio_tab, fg_color="#181824", corner_radius=10)
        input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        input_frame.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(input_frame, text="Video Topic:").grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.agent_topic_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter the topic for your AI generated video...", height=40)
        self.agent_topic_entry.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        self.btn_start_agents = ctk.CTkButton(input_frame, text="🚀 START PRODUCTION", font=("Arial", 14, "bold"), height=40, fg_color="#00E5FF", text_color="black", hover_color="#00B3CC", command=self.start_agent_pipeline)
        self.btn_start_agents.grid(row=0, column=2, padx=15, pady=15)
        
        # Node Canvas View
        self.agent_canvas_frame = ctk.CTkFrame(self.agent_studio_tab, fg_color="#0A0A0E", corner_radius=15, border_width=1, border_color="#333")
        self.agent_canvas_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.agent_canvas_frame.rowconfigure(0, weight=1)
        self.agent_canvas_frame.columnconfigure(0, weight=1)
        
        # Create the nodes
        self.nodes_container = ctk.CTkFrame(self.agent_canvas_frame, fg_color="transparent")
        self.nodes_container.place(relx=0.5, rely=0.3, anchor="center")
        
        self.agent_nodes = {}
        
        node_names = ["Writer Agent", "Director Agent", "Image Gen Agent", "Video Gen Agent", "Editor Agent"]
        for i, name in enumerate(node_names):
            node_frame = ctk.CTkFrame(self.nodes_container, width=160, height=80, corner_radius=10, fg_color="#1E1E2E", border_width=2, border_color="#444")
            node_frame.grid_propagate(False)
            node_frame.grid(row=0, column=i*2, padx=10, pady=20)
            
            lbl_name = ctk.CTkLabel(node_frame, text=name, font=("Arial", 12, "bold"), text_color="#ccc")
            lbl_name.place(relx=0.5, rely=0.3, anchor="center")
            
            lbl_status = ctk.CTkLabel(node_frame, text="Idle", font=("Arial", 10), text_color="#777")
            lbl_status.place(relx=0.5, rely=0.7, anchor="center")
            
            self.agent_nodes[name] = {"frame": node_frame, "name_lbl": lbl_name, "status_lbl": lbl_status}
            
            if i < len(node_names) - 1:
                arrow = ctk.CTkLabel(self.nodes_container, text="➔", font=("Arial", 24, "bold"), text_color="#444")
                arrow.grid(row=0, column=i*2 + 1, padx=5)
                
        # Agent Logs
        log_frame = ctk.CTkFrame(self.agent_studio_tab, fg_color="#181824", corner_radius=10)
        log_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 20))
        log_frame.columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Terminal Logs", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        self.agent_log_textbox = ctk.CTkTextbox(log_frame, height=150, font=("Consolas", 11), state="disabled", fg_color="#0A0A0E", text_color="#00FF00")
        self.agent_log_textbox.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

    def log_to_agent_console(self, msg):
        self.agent_log_textbox.configure(state="normal")
        self.agent_log_textbox.insert("end", f"> {msg}\n")
        self.agent_log_textbox.see("end")
        self.agent_log_textbox.configure(state="disabled")
        
    def update_agent_node(self, node_name, status_text, state="idle"):
        if node_name not in self.agent_nodes: return
        node = self.agent_nodes[node_name]
        node["status_lbl"].configure(text=status_text)
        
        if state == "idle":
            node["frame"].configure(border_color="#444")
            node["name_lbl"].configure(text_color="#ccc")
            node["status_lbl"].configure(text_color="#777")
        elif state == "running":
            node["frame"].configure(border_color="#00E5FF")
            node["name_lbl"].configure(text_color="#00E5FF")
            node["status_lbl"].configure(text_color="white")
        elif state == "done":
            node["frame"].configure(border_color="#00FF00")
            node["name_lbl"].configure(text_color="#00FF00")
            node["status_lbl"].configure(text_color="#ccc")
        elif state == "error":
            node["frame"].configure(border_color="#FF3333")
            node["name_lbl"].configure(text_color="#FF3333")
            node["status_lbl"].configure(text_color="#FF3333")

    def start_agent_pipeline(self):
        topic = self.agent_topic_entry.get().strip()
        if not topic:
            messagebox.showerror("Error", "Please enter a topic.")
            return
            
        self.btn_start_agents.configure(state="disabled", text="Running...")
        self.agent_log_textbox.configure(state="normal")
        self.agent_log_textbox.delete("1.0", "end")
        self.agent_log_textbox.configure(state="disabled")
        
        # Reset nodes
        for node in self.agent_nodes:
            self.update_agent_node(node, "Idle", "idle")
            
        threading.Thread(target=self._run_agent_pipeline_thread, args=(topic,), daemon=True).start()

    def _run_agent_pipeline_thread(self, topic):
        import agents
        try:
            self.log_to_agent_console(f"Starting Production House Agent for: {topic}")
            orchestrator = agents.AgentOrchestrator(self.config, self)
            orchestrator.run(topic)
            self.after(0, lambda: messagebox.showinfo("Success", "Video generation complete!"))
        except Exception as e:
            self.log_to_agent_console(f"ERROR: {str(e)}")
            logging.error("Agent pipeline failed", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Agent Error", f"Agent pipeline failed:\n{e}"))
        finally:
            self.after(0, lambda: self.btn_start_agents.configure(state="normal", text="🚀 START PRODUCTION"))

    def _create_main_tab_widgets(self):
        self.main_tab.columnconfigure((0, 1), weight=1)
        self.main_tab.rowconfigure(0, weight=1)
        controls_frame = ctk.CTkFrame(self.main_tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # --- Preset Selector ---
        preset_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        preset_frame.pack(pady=(10, 5), fill="x", padx=20)
        ctk.CTkLabel(preset_frame, text="Quick Presets:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        self.preset_combo = ctk.CTkComboBox(preset_frame, values=["Custom", "Tech News Short", "Scary Story", "Educational Explainer"], width=200, command=self.apply_preset)
        self.preset_combo.pack(side="left")

        ctk.CTkLabel(controls_frame, text="Enter Topic", font=("Arial", 16, "bold")).pack(pady=(15, 5))
        self.topic_entry = ctk.CTkEntry(controls_frame, width=400, placeholder_text="e.g., 'The Future of AI'")
        self.topic_entry.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(controls_frame, text="Start From Step:", font=("Arial", 12)).pack(pady=(15, 5))
        self.start_step_combo = ctk.CTkComboBox(controls_frame, values=PIPELINE_STEPS, width=300)
        self.start_step_combo.pack(pady=5)
        ctk.CTkLabel(controls_frame, text="Content Style:", font=("Arial", 12)).pack(pady=(15, 5))
        self.content_style_combo = ctk.CTkComboBox(controls_frame, values=CONTENT_STYLES, width=300, command=self.update_features_based_on_style)
        self.content_style_combo.pack(pady=5)
        ctk.CTkLabel(controls_frame, text="Video Aspect Ratio:", font=("Arial", 12)).pack(pady=(10, 5))
        self.main_aspect_ratio_combo = ctk.CTkComboBox(controls_frame, values=["16:9 (Horizontal)", "9:16 (Vertical)", "1:1 (Square)"], width=300)
        self.main_aspect_ratio_combo.pack(pady=5)
        
        checkbox_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        checkbox_frame.pack(pady=20, padx=20, fill="x")
        
        self.fact_check_var = ctk.BooleanVar()
        self.fact_check_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Enable Fact-Checking", variable=self.fact_check_var)
        self.fact_check_checkbox.pack(anchor="w", pady=4)
        
        self.metadata_var = ctk.BooleanVar()
        self.metadata_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Generate SEO Metadata", variable=self.metadata_var)
        self.metadata_checkbox.pack(anchor="w", pady=4)

        self.timestamps_var = ctk.BooleanVar()
        self.timestamps_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Generate Timestamps", variable=self.timestamps_var)
        self.timestamps_checkbox.pack(anchor="w", pady=4)
        
        self.caption_var = ctk.BooleanVar()
        self.caption_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Enable Auto-Captioning", variable=self.caption_var)
        self.caption_checkbox.pack(anchor="w", pady=4)
        
        self.add_music_var = ctk.BooleanVar()
        self.add_music_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Add Background Music", variable=self.add_music_var)
        self.add_music_checkbox.pack(anchor="w", pady=4)
        
        self.generate_snippets_var = ctk.BooleanVar()
        self.snippets_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Generate Social Media Snippets", variable=self.generate_snippets_var)
        self.snippets_checkbox.pack(anchor="w", pady=4)
        
        self.generate_thumbnail_var = ctk.BooleanVar()
        self.thumbnail_checkbox = ctk.CTkCheckBox(checkbox_frame, text="Generate Thumbnail", variable=self.generate_thumbnail_var)
        self.thumbnail_checkbox.pack(anchor="w", pady=4)

        # --- Background Mode Selector ---
        bg_mode_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        bg_mode_frame.pack(pady=(5, 0), padx=20, fill="x")
        ctk.CTkLabel(bg_mode_frame, text="Background Mode:", font=("Arial", 12)).pack(anchor="w")
        self.bg_mode_var = ctk.StringVar(value="AI Video")
        bg_seg = ctk.CTkSegmentedButton(
            bg_mode_frame,
            values=["AI Video", "Image Slideshow", "Disabled"],
            variable=self.bg_mode_var,
            command=self._on_bg_mode_change,
            fg_color="#1a1a2e",
            selected_color="#00E5FF",
            selected_hover_color="#00B3CC",
            unselected_color="#2a2a3e",
            text_color="#0A0A0A",
            unselected_hover_color="#3a3a4e",
        )
        bg_seg.pack(fill="x", pady=(4, 0))

        # --- Image Count / Video Count row ---
        count_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        count_frame.pack(pady=(8, 0), padx=20, fill="x")
        count_frame.columnconfigure((0,1,2,3), weight=1)

        ctk.CTkLabel(count_frame, text="Images:", font=("Arial", 11)).grid(row=0, column=0, sticky="w")
        self.image_count_entry = ctk.CTkEntry(count_frame, width=60, placeholder_text="8")
        self.image_count_entry.grid(row=0, column=1, sticky="w", padx=(2, 12))

        self.video_count_label = ctk.CTkLabel(count_frame, text="Video Clips:", font=("Arial", 11))
        self.video_count_label.grid(row=0, column=2, sticky="w")
        self.video_count_entry = ctk.CTkEntry(count_frame, width=60, placeholder_text="1")
        self.video_count_entry.grid(row=0, column=3, sticky="w", padx=(2, 0))

        self.run_button = ctk.CTkButton(controls_frame, text="⚡ INITIALIZE SEQUENCE", command=self.start_pipeline_thread, font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), fg_color="#00E5FF", text_color="#0A0A0A", hover_color="#00B3CC", corner_radius=6)
        self.run_button.pack(pady=20, ipady=5, fill="x", padx=40)
        self.stop_button = ctk.CTkButton(controls_frame, text="🛑 ABORT PROTOCOL", command=self.stop_pipeline, font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), fg_color="#FF0044", text_color="#FFFFFF", hover_color="#CC0036", state="disabled", corner_radius=6)
        self.stop_button.pack(pady=10, ipady=5, fill="x", padx=40)
        
        log_frame = ctk.CTkFrame(self.main_tab)
        log_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        log_frame.rowconfigure(len(PIPELINE_STEPS) + 1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text="[ SYSTEM PROGRESS ]", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color="#00E5FF").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        for i, step_name in enumerate(PIPELINE_STEPS):
            row = ctk.CTkFrame(log_frame, fg_color="transparent")
            row.grid(row=i + 1, column=0, sticky="ew", padx=10, pady=2)
            row.columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=step_name, anchor="w", width=250, font=ctk.CTkFont(family="Consolas", size=12)).pack(side="left", padx=5)
            status_label = ctk.CTkLabel(row, text="⬜", width=60); status_label.pack(side="right", padx=5)
            progress_bar = ctk.CTkProgressBar(row, orientation="horizontal", width=200, progress_color="#00E5FF"); progress_bar.set(0); progress_bar.pack(side="right", padx=5)
            self.step_status_labels.append(status_label)
            self.progress_bars.append(progress_bar)
        self.log_box = ctk.CTkTextbox(log_frame, state="disabled")
        self.log_box.grid(row=len(PIPELINE_STEPS) + 1, column=0, padx=10, pady=(10, 10), sticky="nsew")

    def _create_settings_tab_widgets(self):
        settings_tabs = ctk.CTkTabview(self.settings_tab); settings_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        api_tab = settings_tabs.add("API Keys")
        persona_tab = settings_tabs.add("Personalization")
        advanced_tab = settings_tabs.add("Advanced")
        api_tab.columnconfigure(1, weight=1)
        ctk.CTkLabel(api_tab, text="Video Engine").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.video_engine_combo = ctk.CTkComboBox(api_tab, values=["WaveSpeed AI", "Vertex AI (Veo)"], width=300); self.video_engine_combo.grid(row=0, column=1, columnspan=2, sticky="w", padx=10)
        
        ctk.CTkLabel(api_tab, text="Image Engine").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.image_engine_combo = ctk.CTkComboBox(api_tab, values=["Gemini API", "WaveSpeed AI"], width=300); self.image_engine_combo.grid(row=1, column=1, columnspan=2, sticky="w", padx=10)
        
        ctk.CTkLabel(api_tab, text="Audio Engine").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.audio_engine_combo = ctk.CTkComboBox(api_tab, values=["Gemini API", "WaveSpeed AI"], width=300); self.audio_engine_combo.grid(row=2, column=1, columnspan=2, sticky="w", padx=10)
        
        ctk.CTkLabel(api_tab, text="WaveSpeed Video Model").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.ws_video_model_combo = ctk.CTkComboBox(api_tab, values=[
            "wavespeed-ai/ltx-2.3-text-to-video",
            "wavespeed-ai/ltx-2-19b-text-to-video",
            "wavespeed-ai/wan-2.2-t2v-720p",
            "wavespeed-ai/wan-2.2-t2v-480p",
            "wavespeed-ai/wan-2.1-t2v-720p",
            "wavespeed-ai/hunyuan-video-t2v",
        ], width=300); self.ws_video_model_combo.grid(row=3, column=1, columnspan=2, sticky="w", padx=10)

        ctk.CTkLabel(api_tab, text="WaveSpeed Image Model").grid(row=4, column=0, sticky="w", padx=10, pady=8)
        self.ws_image_model_combo = ctk.CTkComboBox(api_tab, values=["wavespeed-ai/flux-dev", "wavespeed-ai/flux-schnell"], width=300); self.ws_image_model_combo.grid(row=4, column=1, columnspan=2, sticky="w", padx=10)

        ctk.CTkLabel(api_tab, text="WaveSpeed Audio Model").grid(row=5, column=0, sticky="w", padx=10, pady=8)
        self.ws_audio_model_combo = ctk.CTkComboBox(api_tab, values=["elevenlabs/text-to-speech", "playht/play3.0-mini"], width=300); self.ws_audio_model_combo.grid(row=5, column=1, columnspan=2, sticky="w", padx=10)

        ctk.CTkLabel(api_tab, text="Gemini API Key").grid(row=6, column=0, sticky="w", padx=10, pady=8)
        self.gemini_key_entry = ctk.CTkEntry(api_tab, width=400, show="*"); self.gemini_key_entry.grid(row=6, column=1, padx=10, sticky="ew")
        ctk.CTkButton(api_tab, text="🛜 Check Connection", command=self.check_api_connection).grid(row=6, column=2, padx=10, sticky="w")
        
        ctk.CTkLabel(api_tab, text="WaveSpeed AI Key").grid(row=7, column=0, sticky="w", padx=10, pady=8)
        self.wavespeed_key_entry = ctk.CTkEntry(api_tab, width=400, show="*"); self.wavespeed_key_entry.grid(row=7, column=1, columnspan=2, padx=10, sticky="ew")
        
        ctk.CTkLabel(api_tab, text="News API Key").grid(row=8, column=0, sticky="w", padx=10, pady=8)
        self.news_api_key_entry = ctk.CTkEntry(api_tab, width=400, show="*"); self.news_api_key_entry.grid(row=8, column=1, columnspan=2, padx=10, sticky="ew")

        ctk.CTkLabel(api_tab, text="Text Engine").grid(row=9, column=0, sticky="w", padx=10, pady=8)
        self.text_engine_combo = ctk.CTkComboBox(api_tab, values=["Gemini API", "WaveSpeed AI", "Ollama"], width=300); self.text_engine_combo.grid(row=9, column=1, columnspan=2, sticky="w", padx=10)
        
        ctk.CTkLabel(api_tab, text="WaveSpeed Text Model").grid(row=10, column=0, sticky="w", padx=10, pady=8)
        self.ws_text_model_combo = ctk.CTkComboBox(api_tab, values=[
            "meta-llama/llama-3.3-70b-instruct",
            "meta-llama/llama-3.1-8b-instruct",
            "deepseek/deepseek-r1",
            "google/gemini-2.0-flash",
            "mistralai/mistral-large",
        ], width=300); self.ws_text_model_combo.grid(row=10, column=1, columnspan=2, sticky="w", padx=10)
        
        ctk.CTkLabel(api_tab, text="Ollama Base URL").grid(row=11, column=0, sticky="w", padx=10, pady=8)
        self.ollama_base_url_entry = ctk.CTkEntry(api_tab, width=400); self.ollama_base_url_entry.grid(row=11, column=1, columnspan=2, padx=10, sticky="ew")
        
        ctk.CTkLabel(api_tab, text="Ollama Model").grid(row=12, column=0, sticky="w", padx=10, pady=8)
        self.ollama_model_entry = ctk.CTkEntry(api_tab, width=400); self.ollama_model_entry.grid(row=12, column=1, columnspan=2, padx=10, sticky="ew")

        voice_list = [f"{v} — {d}" for v, d in VOICE_OPTIONS.items()]
        ctk.CTkLabel(persona_tab, text="Single-Speaker Voice").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.voice_combo = ctk.CTkComboBox(persona_tab, values=voice_list, width=400); self.voice_combo.grid(row=0, column=1, padx=10)
        ctk.CTkLabel(persona_tab, text="Speaker 1 (Host Voice)").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.speaker1_combo = ctk.CTkComboBox(persona_tab, values=voice_list, width=400); self.speaker1_combo.grid(row=1, column=1, padx=10)
        ctk.CTkLabel(persona_tab, text="Speaker 2 (Guest Voice)").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.speaker2_combo = ctk.CTkComboBox(persona_tab, values=voice_list, width=400); self.speaker2_combo.grid(row=2, column=1, padx=10)
        self.host_name_label = ctk.CTkLabel(persona_tab, text="Host Name")
        self.host_name_label.grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.host_entry = ctk.CTkEntry(persona_tab, width=300); self.host_entry.grid(row=3, column=1, padx=10)
        ctk.CTkLabel(persona_tab, text="Guest Name").grid(row=4, column=0, sticky="w", padx=10, pady=8)
        self.guest_entry = ctk.CTkEntry(persona_tab, width=300); self.guest_entry.grid(row=4, column=1, padx=10)
        self.host_persona_label = ctk.CTkLabel(persona_tab, text="Host Persona")
        self.host_persona_label.grid(row=5, column=0, sticky="nw", padx=10, pady=8)
        self.host_persona_entry = ctk.CTkTextbox(persona_tab, width=400, height=80); self.host_persona_entry.grid(row=5, column=1, padx=10)
        ctk.CTkLabel(persona_tab, text="Guest Persona").grid(row=6, column=0, sticky="nw", padx=10, pady=8)
        self.guest_persona_entry = ctk.CTkTextbox(persona_tab, width=400, height=80); self.guest_persona_entry.grid(row=6, column=1, padx=10)
        ctk.CTkLabel(advanced_tab, text="Channel Name").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.channel_entry = ctk.CTkEntry(advanced_tab, width=300); self.channel_entry.grid(row=0, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Subscribe Reminder Count").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.sub_count_entry = ctk.CTkEntry(advanced_tab, width=100); self.sub_count_entry.grid(row=1, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Subscribe Message").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.sub_message_entry = ctk.CTkEntry(advanced_tab, width=400); self.sub_message_entry.grid(row=2, column=1, padx=10, sticky="w")
        self.subscribe_random_var = ctk.BooleanVar()
        self.subscribe_random_check = ctk.CTkCheckBox(advanced_tab, text="Random Placement", variable=self.subscribe_random_var); self.subscribe_random_check.grid(row=3, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Podcast Style").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.style_combo = ctk.CTkComboBox(advanced_tab, values=PODCAST_STYLES, width=300); self.style_combo.grid(row=4, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Story Arc").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.story_arc_combo = ctk.CTkComboBox(advanced_tab, values=STORY_ARCS, width=300); self.story_arc_combo.grid(row=5, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Video Prompt Style Guide").grid(row=6, column=0, sticky="nw", padx=10, pady=5)
        self.video_style_textbox = ctk.CTkTextbox(advanced_tab, width=400, height=80); self.video_style_textbox.grid(row=6, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Image Prompt Template").grid(row=7, column=0, sticky="nw", padx=10, pady=5)
        self.image_style_textbox = ctk.CTkTextbox(advanced_tab, width=400, height=80); self.image_style_textbox.grid(row=7, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Image Interval (s)").grid(row=10, column=0, sticky="w", padx=10, pady=5)
        self.image_interval_entry = ctk.CTkEntry(advanced_tab, width=100, placeholder_text="0 for Auto"); self.image_interval_entry.grid(row=10, column=1, padx=10, sticky="w")
        self.language_enabled_var = ctk.BooleanVar()
        ctk.CTkCheckBox(advanced_tab, text="Enable Language Selection", variable=self.language_enabled_var).grid(row=11, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Podcast Language").grid(row=12, column=0, sticky="w", padx=10, pady=5)
        self.language_combo = ctk.CTkComboBox(advanced_tab, values=["English", "Spanish", "French", "German", "Urdu"], width=300); self.language_combo.grid(row=12, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Desired Script Length").grid(row=13, column=0, sticky="w", padx=10, pady=5)
        self.script_length_combo = ctk.CTkComboBox(advanced_tab, values=SCRIPT_LENGTHS, width=300); self.script_length_combo.grid(row=13, column=1, padx=10, sticky="w")
        ctk.CTkLabel(advanced_tab, text="Video Aspect Ratio").grid(row=14, column=0, sticky="w", padx=10, pady=5)
        self.aspect_ratio_combo = ctk.CTkComboBox(advanced_tab, values=["16:9 (Horizontal)", "9:16 (Vertical)"], width=300); self.aspect_ratio_combo.grid(row=14, column=1, padx=10, sticky="w")
        ctk.CTkButton(self.settings_tab, text="💾 Save Settings", command=self.save_settings_from_gui).pack(pady=20)
    
    def _create_publish_tab_widgets(self):
        self.publish_tab.columnconfigure(1, weight=1)
        metadata_frame = ctk.CTkFrame(self.publish_tab, fg_color="transparent")
        metadata_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10,5))
        ctk.CTkLabel(metadata_frame, text="Video Metadata", font=("Arial", 16, "bold")).pack(side="left")
        ctk.CTkButton(metadata_frame, text="✨ Generate SEO", command=lambda: self.generate_seo_only()).pack(side="left", padx=10)
        ctk.CTkLabel(self.publish_tab, text="Video Title:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.video_title_entry = ctk.CTkEntry(self.publish_tab, placeholder_text="Enter video title"); self.video_title_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(self.publish_tab, text="Description:").grid(row=2, column=0, sticky="nw", padx=10, pady=5)
        self.video_desc_entry = ctk.CTkTextbox(self.publish_tab, height=120); self.video_desc_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(self.publish_tab, text="Tags:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.video_tags_entry = ctk.CTkEntry(self.publish_tab, placeholder_text="tag1, tag2, tag3"); self.video_tags_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(self.publish_tab, text="--- Upload ---", font=("Arial", 16, "bold")).grid(row=4, column=0, columnspan=3, pady=(20,5), padx=10, sticky="w")
        
        ctk.CTkLabel(self.publish_tab, text="Video File:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.video_path_entry = ctk.CTkEntry(self.publish_tab, placeholder_text="Leave blank to use generated video"); self.video_path_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(self.publish_tab, text="📂 Browse...", command=lambda: self.browse_file(self.video_path_entry)).grid(row=5, column=2, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(self.publish_tab, text="Thumbnail:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.thumbnail_path_entry = ctk.CTkEntry(self.publish_tab, placeholder_text="Leave blank to use generated thumbnail"); self.thumbnail_path_entry.grid(row=6, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(self.publish_tab, text="📂 Browse...", command=lambda: self.browse_file(self.thumbnail_path_entry)).grid(row=6, column=2, sticky="w", padx=10, pady=5)
        
        self.upload_status_label = ctk.CTkLabel(self.publish_tab, text="", font=("Arial", 12))
        self.upload_status_label.grid(row=7, column=0, columnspan=3, pady=(10,0), padx=20, sticky="ew")
        self.upload_progress_bar = ctk.CTkProgressBar(self.publish_tab, orientation="horizontal")
        self.upload_progress_bar.set(0)
        self.upload_progress_bar.grid(row=8, column=0, columnspan=3, pady=(5,10), padx=20, sticky="ew")

        upload_frame = ctk.CTkFrame(self.publish_tab, fg_color="transparent")
        upload_frame.grid(row=9, column=0, columnspan=3, pady=10)
        self.youtube_upload_button = ctk.CTkButton(upload_frame, text="▶️ Upload to YouTube", command=self.start_youtube_upload_thread, fg_color="#FF0044", hover_color="#CC0036")
        self.youtube_upload_button.pack(side="left", padx=10)
        self.facebook_upload_button = ctk.CTkButton(upload_frame, text="🔵 Upload to Facebook", command=lambda: self.upload_facebook(), fg_color="#00E5FF", text_color="#0A0A0A", hover_color="#00B3CC")
        self.facebook_upload_button.pack(side="left", padx=10)
        
        ctk.CTkLabel(self.publish_tab, text="--- API Credentials for Publishing ---", font=("Arial", 12, "bold")).grid(row=10, column=0, columnspan=3, pady=(20,5), padx=10, sticky="w")
        ctk.CTkLabel(self.publish_tab, text="Facebook Access Token:").grid(row=11, column=0, sticky="w", padx=10, pady=5)
        self.facebook_token_entry = ctk.CTkEntry(self.publish_tab, width=400, show="*", placeholder_text="User/Page access token"); self.facebook_token_entry.grid(row=11, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
    
    def _create_tools_tab_widgets(self):
        self.tools_tab.columnconfigure(1, weight=1)
        ctk.CTkLabel(self.tools_tab, text="Auto-Caption Video Tool", font=("Arial", 20, "bold")).grid(row=0, column=0, columnspan=3, pady=(20, 10), padx=20, sticky="w")
        
        # File selection frame
        file_frame = ctk.CTkFrame(self.tools_tab, fg_color="transparent")
        file_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        file_frame.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(file_frame, text="Input Video:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.tools_input_video = ctk.CTkEntry(file_frame, placeholder_text="Path to original video")
        self.tools_input_video.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(file_frame, text="📂 Browse...", command=lambda: self.browse_file(self.tools_input_video)).grid(row=0, column=2, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(file_frame, text="Output Video:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.tools_output_video = ctk.CTkEntry(file_frame, placeholder_text="Where to save captioned video")
        self.tools_output_video.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(file_frame, text="📂 Save As...", command=lambda: self.browse_save_file(self.tools_output_video)).grid(row=1, column=2, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(file_frame, text="Spoken Language:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.tools_language_combo = ctk.CTkComboBox(file_frame, values=["English", "Spanish", "French", "German", "Urdu", "Auto"], width=200)
        self.tools_language_combo.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.tools_language_combo.set("English")
        
        # Style section
        style_frame = ctk.CTkFrame(self.tools_tab)
        style_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=10)
        style_frame.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(style_frame, text="Caption Styling", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        
        ctk.CTkLabel(style_frame, text="Template:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.style_template_combo = ctk.CTkComboBox(style_frame, values=["Default Yellow", "Cinematic White", "TikTok Bold"], command=self.update_live_preview)
        self.style_template_combo.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        self.style_template_combo.set("Default Yellow")
        
        ctk.CTkLabel(style_frame, text="Font Family:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.style_font_combo = ctk.CTkComboBox(style_frame, values=["Arial Black", "Impact", "Consolas", "Verdana"], command=self.update_live_preview)
        self.style_font_combo.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.style_font_combo.set("Arial Black")
        
        ctk.CTkLabel(style_frame, text="Font Size:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.style_size_slider = ctk.CTkSlider(style_frame, from_=20, to=100, number_of_steps=80, command=self.update_live_preview)
        self.style_size_slider.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        self.style_size_slider.set(46)
        
        # Live Preview
        self.live_preview_label = ctk.CTkLabel(style_frame, text="LIVE PREVIEW", width=300, height=80, corner_radius=10, fg_color="#333333")
        self.live_preview_label.grid(row=1, column=2, rowspan=3, sticky="nsew", padx=20, pady=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.tools_tab, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=20, pady=10)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        ctk.CTkButton(btn_frame, text="👁️ Show Video Preview", font=("Arial", 14), fg_color="#444444", hover_color="#cccccc", command=self.show_video_preview).grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.tools_caption_btn = ctk.CTkButton(btn_frame, text="🎙️ Generate Captions & Burn", font=("Arial", 14, "bold"), fg_color="#00E5FF", text_color="#0A0A0A", hover_color="#00B3CC", command=self.start_auto_caption_thread)
        self.tools_caption_btn.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        
        self.tools_status_label = ctk.CTkLabel(self.tools_tab, text="Ready", font=("Arial", 12))
        self.tools_status_label.grid(row=4, column=0, columnspan=3, pady=10, padx=20, sticky="ew")
        
        self.update_live_preview(None)

    def get_current_style_opts(self):
        import pysubs2
        template = self.style_template_combo.get()
        size = int(self.style_size_slider.get())
        font = self.style_font_combo.get()
        
        opts = {
            "fontname": font,
            "fontsize": size,
            "alignment": 2,
            "marginv": 40
        }
        
        if template == "Default Yellow":
            opts.update({
                "primarycolor": pysubs2.Color(255, 255, 0, 0),
                "outlinecolor": pysubs2.Color(0, 0, 0, 0),
                "backcolor": pysubs2.Color(0, 0, 0, 180),
                "bold": True,
                "outline": 3,
                "shadow": 1
            })
        elif template == "Cinematic White":
            opts.update({
                "primarycolor": pysubs2.Color(255, 255, 255, 0),
                "outlinecolor": pysubs2.Color(0, 0, 0, 0),
                "backcolor": pysubs2.Color(0, 0, 0, 255), # invisible shadow
                "bold": False,
                "outline": 1,
                "shadow": 0
            })
        elif template == "TikTok Bold":
            opts.update({
                "primarycolor": pysubs2.Color(255, 255, 255, 0),
                "outlinecolor": pysubs2.Color(0, 0, 0, 0),
                "backcolor": pysubs2.Color(0, 0, 0, 255),
                "bold": True,
                "outline": 5,
                "shadow": 0,
                "marginv": 150 # Higher up for TikTok
            })
        return opts

    def update_live_preview(self, _):
        template = self.style_template_combo.get()
        size = int(self.style_size_slider.get())
        ui_size = max(12, int(size * 0.5)) 
        font = self.style_font_combo.get()
        
        if template == "Default Yellow":
            self.live_preview_label.configure(text_color="yellow", font=(font, ui_size, "bold"))
        elif template == "Cinematic White":
            self.live_preview_label.configure(text_color="white", font=(font, ui_size, "normal"))
        elif template == "TikTok Bold":
            self.live_preview_label.configure(text_color="white", font=(font, ui_size, "bold"))

    def show_video_preview(self):
        in_vid = self.tools_input_video.get().strip()
        if not os.path.exists(in_vid):
            messagebox.showerror("Error", "Please select a valid input video first.")
            return
        
        self.tools_status_label.configure(text="⏳ Generating Video Preview...")
        threading.Thread(target=self._video_preview_worker, args=(in_vid,), daemon=True).start()

    def _video_preview_worker(self, in_vid):
        import subprocess
        import pysubs2
        try:
            temp_ass = "temp_preview.ass"
            subs = pysubs2.SSAFile()
            opts = self.get_current_style_opts()
            
            style = pysubs2.SSAStyle(
                fontname=opts.get("fontname"),
                fontsize=opts.get("fontsize"),
                primarycolor=opts.get("primarycolor"),
                outlinecolor=opts.get("outlinecolor"),
                backcolor=opts.get("backcolor"),
                bold=opts.get("bold"),
                outline=opts.get("outline"),
                shadow=opts.get("shadow"),
                alignment=opts.get("alignment"),
                marginv=opts.get("marginv")
            )
            subs.styles["Default"] = style
            subs.append(pysubs2.SSAEvent(start=0, end=5000, text="PREVIEW", style="Default"))
            subs.save(temp_ass)
            
            out_img = "temp_preview.jpg"
            subs_path = os.path.abspath(temp_ass).replace('\\', '/').replace(':', '\\:')
            cmd = [
                "ffmpeg", "-y", "-ss", "00:00:02", "-i", in_vid,
                "-vf", f"subtitles='{subs_path}'",
                "-vframes", "1", "-q:v", "2", out_img
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            self.after(0, self._show_preview_image, out_img)
            self.after(0, lambda: self.tools_status_label.configure(text="✅ Preview generated!"))
        except Exception as e:
            logging.error(f"Preview failed: {e}", exc_info=True)
            self.after(0, lambda e=e: messagebox.showerror("Preview Error", f"Failed to generate preview:\n{e}"))
            self.after(0, lambda: self.tools_status_label.configure(text="❌ Preview failed."))
            
    def _show_preview_image(self, img_path):
        from PIL import Image
        if not os.path.exists(img_path): return
        
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("Video Frame Preview")
        preview_win.geometry("800x600")
        preview_win.attributes("-topmost", True)
        
        img = Image.open(img_path)
        img.thumbnail((800, 600), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        
        lbl = ctk.CTkLabel(preview_win, image=ctk_img, text="")
        lbl.pack(expand=True, fill="both", padx=10, pady=10)

    def browse_save_file(self, entry_widget):
        filename = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")])
        if filename:
            entry_widget.delete(0, ctk.END)
            entry_widget.insert(0, filename)
            
    def start_auto_caption_thread(self):
        in_vid = self.tools_input_video.get().strip()
        out_vid = self.tools_output_video.get().strip()
        lang = self.tools_language_combo.get().strip()
        
        if not os.path.exists(in_vid):
            messagebox.showerror("Error", "Input video file does not exist.")
            return
        if not out_vid:
            messagebox.showerror("Error", "Please specify an output video path.")
            return
            
        self.tools_caption_btn.configure(state="disabled")
        self.tools_status_label.configure(text="⏳ Extracting audio from video...")
        
        # Pass the current style_opts to the thread
        style_opts = self.get_current_style_opts()
        threading.Thread(target=self.auto_caption_worker, args=(in_vid, out_vid, lang, style_opts), daemon=True).start()
        
    def auto_caption_worker(self, in_vid, out_vid, lang, style_opts):
        import subprocess
        from pipeline import generate_captions
        
        try:
            # 1. Extract Audio
            temp_audio = "temp_tools_audio.wav"
            temp_ass = "temp_tools_captions.ass"
            
            if os.path.exists(temp_audio): os.remove(temp_audio)
            if os.path.exists(temp_ass): os.remove(temp_ass)
            
            subprocess.run(["ffmpeg", "-y", "-i", in_vid, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", temp_audio], check=True, capture_output=True)
            
            # 2. Transcribe
            self.after(0, lambda: self.tools_status_label.configure(text="⏳ Transcribing audio with Whisper..."))
            whisper_lang = None if lang == "Auto" else lang
            generate_captions(temp_audio, temp_ass, whisper_lang, style_opts=style_opts)
            
            if not os.path.exists(temp_ass):
                raise Exception("Failed to generate .ass subtitle file.")
                
            # 3. Burn Subtitles
            self.after(0, lambda: self.tools_status_label.configure(text="⏳ Burning subtitles into video (This may take a while)..."))
            subs_path = os.path.abspath(temp_ass).replace('\\', '/').replace(':', '\\:')
            
            cmd = [
                "ffmpeg", "-y",
                "-i", in_vid,
                "-vf", f"subtitles='{subs_path}'",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                out_vid
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            self.after(0, lambda: self.tools_status_label.configure(text="✅ Captions successfully burned to video!"))
            self.after(0, lambda: messagebox.showinfo("Success", f"Video saved to:\n{out_vid}"))
            
        except Exception as e:
            logging.error(f"Auto-caption failed: {e}", exc_info=True)
            self.after(0, lambda e=e: self.tools_status_label.configure(text=f"❌ Error: {e}"))
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Failed to auto-caption video:\n{e}"))
        finally:
            self.after(0, lambda: self.tools_caption_btn.configure(state="normal"))
            if os.path.exists("temp_tools_audio.wav"): os.remove("temp_tools_audio.wav")
            if os.path.exists("temp_tools_captions.ass"): os.remove("temp_tools_captions.ass")

    def _create_about_tab_widgets(self):
        ctk.CTkLabel(self.about_tab, text="Nullpk Content Automation", font=("Arial", 20, "bold")).pack(pady=(40, 10))
        ctk.CTkLabel(self.about_tab, text="Version 3.2 (Slideshow Mode)", font=("Arial", 12)).pack(pady=5)
        ctk.CTkLabel(self.about_tab, text="Author: Naqash Afzal", font=("Arial", 12)).pack(pady=5)
        ctk.CTkLabel(self.about_tab, text="This tool automates the creation of YouTube videos using AI.", wraplength=500).pack(pady=20)
        ctk.CTkButton(self.about_tab, text="☕ Donate Now", command=lambda: webbrowser.open_new("https://nullpk.com/donate")).pack(pady=10)
    
    def check_api_connection(self):
        gemini_key = self.gemini_key_entry.get().strip()
        if not gemini_key:
            messagebox.showerror("Error", "Please enter a Gemini API Key to test.")
            return
        logging.info("Testing connection to Gemini servers...")
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-3-flash-preview")
            resp = model.generate_content("Respond with exactly one word: 'CONNECTED'.")
            messagebox.showinfo("Connection Successful", f"API Key is valid and active.\nResponse: {resp.text.strip()}")
            logging.info("Gemini API connection test passed.")
        except Exception as e:
            logging.error(f"API Connection Failed: {e}")
            messagebox.showerror("Connection Failed", f"Invalid API Key or network issue:\n{e}")

    def _extract_voice_name(self, val): return val.split(" — ")[0] if " — " in val else val
    
    def update_features_based_on_style(self, selected_style):
        is_podcast = selected_style == "Podcast"
        state = "normal" if is_podcast else "disabled"
        single_state = "disabled" if is_podcast else "normal"
        
        self.fact_check_checkbox.configure(state=state)
        self.style_combo.configure(state=state)
        self.story_arc_combo.configure(state="normal")
        self.voice_combo.configure(state=single_state)
        self.speaker1_combo.configure(state=state)
        self.speaker2_combo.configure(state=state)
        
        self.host_entry.configure(state="normal")
        self.host_persona_entry.configure(state="normal")
        self.host_name_label.configure(text="Host Name" if is_podcast else "Narrator Name")
        self.host_persona_label.configure(text="Host Persona" if is_podcast else "Narrator Persona")
        
        self.guest_entry.configure(state=state)
        self.guest_persona_entry.configure(state=state)

    def _on_bg_mode_change(self, mode):
        """Show/hide count fields based on selected background mode."""
        if mode == "AI Video":
            self.image_count_entry.configure(state="disabled")
            self.video_count_entry.configure(state="normal")
        elif mode == "Image Slideshow":
            self.image_count_entry.configure(state="normal")
            self.video_count_entry.configure(state="disabled")
        else:  # Disabled
            self.image_count_entry.configure(state="disabled")
            self.video_count_entry.configure(state="disabled")

    def apply_preset(self, preset_name):
        """Applies predefined settings based on the selected preset."""
        if preset_name == "Custom":
            return
            
        logging.info(f"Applying preset: {preset_name}")
        
        # Helper to set combo box if value exists in its options
        def safe_set_combo(combo, partial_value):
            for val in combo._values:
                if partial_value in val:
                    combo.set(val)
                    return
            combo.set(partial_value)
            
        if preset_name == "Tech News Short":
            self.content_style_combo.set("Podcast")
            self.update_features_based_on_style("Podcast")
            self.main_aspect_ratio_combo.set("9:16 (Vertical)")
            self.bg_mode_var.set("Image Slideshow")
            self._on_bg_mode_change("Image Slideshow")
            self.caption_var.set(True)
            self.add_music_var.set(True)
            self.style_combo.set("Informative News")
            self.script_length_combo.set("Short (~2 minutes)")
            self.image_interval_entry.delete(0, "end")
            self.image_interval_entry.insert(0, "4")
            safe_set_combo(self.speaker1_combo, "Achernar")
            safe_set_combo(self.speaker2_combo, "Leda")
            self.video_style_textbox.delete("1.0", "end")
            self.video_style_textbox.insert("1.0", "Cinematic, realistic, high-quality news footage.")
            
        elif preset_name == "Scary Story":
            self.content_style_combo.set("Horror Story")
            self.update_features_based_on_style("Horror Story")
            self.main_aspect_ratio_combo.set("16:9 (Horizontal)")
            self.bg_mode_var.set("Image Slideshow")
            self._on_bg_mode_change("Image Slideshow")
            self.caption_var.set(True)
            self.add_music_var.set(True)
            self.story_arc_combo.set("Hero's Journey")
            self.script_length_combo.set("Long (~10 minutes)")
            self.image_interval_entry.delete(0, "end")
            self.image_interval_entry.insert(0, "8")
            safe_set_combo(self.voice_combo, "Zubenelgenubi")
            self.image_style_textbox.delete("1.0", "end")
            self.image_style_textbox.insert("1.0", "Dark, moody, cinematic lighting, horror style, realistic: {topic}")
            
        elif preset_name == "Educational Explainer":
            self.content_style_combo.set("Documentary")
            self.update_features_based_on_style("Documentary")
            self.main_aspect_ratio_combo.set("16:9 (Horizontal)")
            self.bg_mode_var.set("AI Video")
            self._on_bg_mode_change("AI Video")
            self.caption_var.set(True)
            self.add_music_var.set(False)
            self.script_length_combo.set("Medium (~5 minutes)")
            safe_set_combo(self.voice_combo, "Autonoe")
            self.video_style_textbox.delete("1.0", "end")
            self.video_style_textbox.insert("1.0", "National Geographic style documentary footage, educational, clean, 4k.")
        
        # Save to memory
        self.update_config_from_all_gui()

    def update_status_callback(self, step_index, status, progress):
        if 0 <= step_index < len(self.progress_bars):
            self.progress_bars[step_index].set(progress)
            self.step_status_labels[step_index].configure(text=status)
    
    def start_pipeline_thread(self):
        topic = self.topic_entry.get().strip()
        if not topic: messagebox.showerror("Error", "Please enter a topic."); return
        if not self.config.get("GEMINI_API_KEY"): messagebox.showerror("API Key Missing", "Please enter your Gemini API key in Settings."); return
        
        self.run_button.configure(state="disabled"); self.stop_button.configure(state="normal")
        self.stop_event.clear()
        for i in range(len(PIPELINE_STEPS)): self.update_status_callback(i, "⬜", 0)
        
        # This function syncs all GUI settings to the in-memory config dict
        self.update_config_from_all_gui()
        
        on_finish_callback = lambda success: self.after(0, self.on_pipeline_finished, success, topic)
        
        # Pass all callbacks to the pipeline instance
        pipeline_instance = Pipeline(
            self.config, 
            self.stop_event, 
            self.update_status_callback, 
            self.update_seo_callback,          # Callback for SEO
            on_finish_callback,
            self.update_timestamps_callback,   # Callback for Timestamps
            on_script_generated=self.open_script_editor # Callback for Script Editor
        )
        threading.Thread(target=pipeline_instance.run, args=(topic, self.start_step_combo.get()), daemon=True).start()
    
    def open_script_editor(self, script_content, file_path, resume_event):
        """Callback from pipeline thread to open script editor in main thread."""
        self.after(0, lambda: ScriptEditorWindow(self, script_content, file_path, resume_event))
    
    def stop_pipeline(self):
        logging.info("🛑 Stop signal received. Finishing current step...")
        self.stop_event.set()
        self.run_button.configure(state="normal"); self.stop_button.configure(state="disabled")

    def on_pipeline_finished(self, success: bool, topic: str):
        """Handles UI updates when the pipeline completes, fails, or is stopped."""
        self.run_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.update_history_tab()
        if success:
            messagebox.showinfo("Pipeline Complete", f"Successfully generated content for topic:\n'{topic}'")
    
    def update_seo_callback(self, metadata):
        """Safely updates the publish tab UI with title, description, and tags. THIS RUNS FIRST."""
        def update_ui():
            self.video_title_entry.delete(0, "end")
            self.video_title_entry.insert(0, metadata.get("title", ""))
            self.video_desc_entry.delete("1.0", "end") # This CLEARS the box
            self.video_desc_entry.insert("1.0", metadata.get("description", "")) # This SETS the description
            self.video_tags_entry.delete(0, "end")
            self.video_tags_entry.insert(0, metadata.get("tags", ""))
            logging.info("📝 SEO metadata has been pre-filled in the Publish tab.")
        self.after(0, update_ui)

    def update_timestamps_callback(self, timestamps_text: str):
        """Safely appends the generated timestamps to the description box. THIS RUNS SECOND."""
        if not timestamps_text:
            return
        def update_ui():
            # This APPENDS to the description, which was already set by the SEO callback
            self.video_desc_entry.insert("end", timestamps_text) 
            logging.info("⏰ Timestamps have been appended to the description.")
        self.after(0, update_ui)

    def update_config_from_all_gui(self):
        """
        Synchronizes the in-memory self.config dictionary with the current state
        of ALL relevant UI elements. This ensures the pipeline runs with the settings
        the user currently sees.
        """
        logging.info("Syncing all current GUI settings to in-memory config for pipeline run...")
        
        # Main Tab Checkboxes
        self.config["FACT_CHECK_ENABLED"] = self.fact_check_var.get()
        self.config["GENERATE_METADATA"] = self.metadata_var.get()
        self.config["GENERATE_TIMESTAMPS"] = self.timestamps_var.get()
        self.config["CAPTION_ENABLED"] = self.caption_var.get()
        self.config["ADD_MUSIC"] = self.add_music_var.get()
        self.config["GENERATE_SNIPPETS"] = self.generate_snippets_var.get()
        self.config["GENERATE_THUMBNAIL"] = self.generate_thumbnail_var.get()
        self.config["CONTENT_STYLE"] = self.content_style_combo.get()
        # Background mode (replaces old GENERATE_TIMED_IMAGES + TIMED_IMAGES_AS_SLIDESHOW)
        bg_mode = self.bg_mode_var.get()
        self.config["BG_MODE"] = bg_mode
        self.config["GENERATE_TIMED_IMAGES"] = bg_mode == "Image Slideshow"
        self.config["TIMED_IMAGES_AS_SLIDESHOW"] = bg_mode == "Image Slideshow"
        try:
            self.config["IMAGE_COUNT"] = max(1, int(self.image_count_entry.get()))
        except (ValueError, TypeError):
            self.config["IMAGE_COUNT"] = 8
        try:
            self.config["VIDEO_CLIP_COUNT"] = max(1, int(self.video_count_entry.get()))
        except (ValueError, TypeError):
            self.config["VIDEO_CLIP_COUNT"] = 1
        
        # Settings Tab (API)
        self.config["GEMINI_API_KEY"] = self.gemini_key_entry.get().strip()
        self.config["WAVESPEED_AI_KEY"] = self.wavespeed_key_entry.get().strip()
        self.config["NEWS_API_KEY"] = self.news_api_key_entry.get().strip()
        self.config["VIDEO_ENGINE"] = self.video_engine_combo.get()
        self.config["IMAGE_ENGINE"] = self.image_engine_combo.get()
        self.config["AUDIO_ENGINE"] = self.audio_engine_combo.get()
        self.config["TEXT_ENGINE"] = self.text_engine_combo.get()
        self.config["OLLAMA_BASE_URL"] = self.ollama_base_url_entry.get().strip()
        self.config["OLLAMA_MODEL"] = self.ollama_model_entry.get().strip()
        self.config["WAVESPEED_IMAGE_MODEL"] = self.ws_image_model_combo.get()
        self.config["WAVESPEED_VIDEO_MODEL"] = self.ws_video_model_combo.get()
        self.config["WAVESPEED_AUDIO_MODEL"] = self.ws_audio_model_combo.get()
        self.config["WAVESPEED_TEXT_MODEL"] = self.ws_text_model_combo.get()

        # Settings Tab (Personalization)
        self.config["VOICE_NAME"] = self._extract_voice_name(self.voice_combo.get())
        self.config["SPEAKER1"] = self._extract_voice_name(self.speaker1_combo.get())
        self.config["SPEAKER2"] = self._extract_voice_name(self.speaker2_combo.get())
        self.config["HOST_NAME"] = self.host_entry.get().strip() or "Alex"
        self.config["GUEST_NAME"] = self.guest_entry.get().strip() or "Maya"
        self.config["HOST_PERSONA"] = self.host_persona_entry.get("1.0", "end-1c").strip()
        self.config["GUEST_PERSONA"] = self.guest_persona_entry.get("1.0", "end-1c").strip()

        # Settings Tab (Advanced)
        self.config["PODCAST_STYLE"] = self.style_combo.get()
        self.config["STORY_ARC"] = self.story_arc_combo.get()
        self.config["SCRIPT_LENGTH"] = self.script_length_combo.get()
        self.config["VIDEO_ASPECT_RATIO"] = self.main_aspect_ratio_combo.get()
        # Keep settings tab combo in sync
        self.aspect_ratio_combo.set(self.main_aspect_ratio_combo.get())
        self.config["LANGUAGE_ENABLED"] = self.language_enabled_var.get()
        self.config["PODCAST_LANGUAGE"] = self.language_combo.get()
        try: 
            self.config["IMAGE_GENERATION_INTERVAL"] = int(self.image_interval_entry.get())
        except (ValueError, TypeError): 
            self.config["IMAGE_GENERATION_INTERVAL"] = 0
        
        self.config["VIDEO_PROMPT_BASE_STYLE"] = self.video_style_textbox.get("1.0", "end-1c").strip()
        self.config["IMAGE_PROMPT_STYLE"] = self.image_style_textbox.get("1.0", "end-1c").strip()
        
    
    def save_settings_from_gui(self):
        """
        Updates the in-memory config from the GUI and then saves it to config.json.
        """
        self.update_config_from_all_gui()
        
        self.config["FACEBOOK_ACCESS_TOKEN"] = self.facebook_token_entry.get().strip()
        self.config["CHANNEL_NAME"] = self.channel_entry.get().strip() or "My AI Channel"
        try: 
            self.config["SUBSCRIBE_COUNT"] = int(self.sub_count_entry.get())
        except ValueError: 
            self.config["SUBSCRIBE_COUNT"] = 3
        self.config["SUBSCRIBE_MESSAGE"] = self.sub_message_entry.get().strip()
        self.config["SUBSCRIBE_RANDOM"] = self.subscribe_random_var.get()
        
        save_config(self.config)
        messagebox.showinfo("Success", "Settings have been saved successfully.")
    
    def load_settings_into_gui(self):
        cfg = self.config
        self.gemini_key_entry.insert(0, cfg.get("GEMINI_API_KEY", ""))
        self.wavespeed_key_entry.insert(0, cfg.get("WAVESPEED_AI_KEY", ""))
        self.news_api_key_entry.insert(0, cfg.get("NEWS_API_KEY", ""))
        self.facebook_token_entry.insert(0, cfg.get("FACEBOOK_ACCESS_TOKEN", ""))
        self.speaker1_combo.set(f"{cfg['SPEAKER1']} — {VOICE_OPTIONS.get(cfg['SPEAKER1'], '')}")
        self.speaker2_combo.set(f"{cfg['SPEAKER2']} — {VOICE_OPTIONS.get(cfg['SPEAKER2'], '')}")
        self.voice_combo.set(f"{cfg.get('VOICE_NAME', 'Kore')} — {VOICE_OPTIONS.get(cfg.get('VOICE_NAME', 'Kore'), '')}")
        self.host_entry.insert(0, cfg.get("HOST_NAME", "Alex"))
        self.guest_entry.insert(0, cfg.get("GUEST_NAME", "Maya"))
        self.host_persona_entry.insert("1.0", cfg.get("HOST_PERSONA", ""))
        self.guest_persona_entry.insert("1.0", cfg.get("GUEST_PERSONA", ""))
        self.channel_entry.insert(0, cfg.get("CHANNEL_NAME", "My AI Channel"))
        self.sub_count_entry.insert(0, str(cfg.get("SUBSCRIBE_COUNT", 3)))
        self.sub_message_entry.insert(0, cfg.get("SUBSCRIBE_MESSAGE", ""))
        self.subscribe_random_var.set(cfg.get("SUBSCRIBE_RANDOM", True))
        self.style_combo.set(cfg.get("PODCAST_STYLE", "Informative News"))
        self.story_arc_combo.set(cfg.get("STORY_ARC", "None"))
        self.video_style_textbox.insert("1.0", cfg.get("VIDEO_PROMPT_BASE_STYLE", "An animated and cinematic video. High-quality, 24fps."))
        self.image_style_textbox.insert("1.0", cfg.get("IMAGE_PROMPT_STYLE", "A cinematic, photorealistic image representing the podcast topic: {topic}"))
        self.image_interval_entry.insert(0, str(cfg.get("IMAGE_GENERATION_INTERVAL", 0)))
        self.language_enabled_var.set(cfg.get("LANGUAGE_ENABLED", False))
        self.language_combo.set(cfg.get("PODCAST_LANGUAGE", "English"))
        self.video_engine_combo.set(cfg.get("VIDEO_ENGINE", "WaveSpeed AI"))
        self.image_engine_combo.set(cfg.get("IMAGE_ENGINE", "Gemini API"))
        self.audio_engine_combo.set(cfg.get("AUDIO_ENGINE", "Gemini API"))
        self.text_engine_combo.set(cfg.get("TEXT_ENGINE", "Gemini API"))
        self.ollama_base_url_entry.insert(0, cfg.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.ollama_model_entry.insert(0, cfg.get("OLLAMA_MODEL", "llama3"))
        self.ws_text_model_combo.set(cfg.get("WAVESPEED_TEXT_MODEL", "meta-llama/llama-3.3-70b-instruct"))
        self.ws_image_model_combo.set(cfg.get("WAVESPEED_IMAGE_MODEL", "wavespeed-ai/flux-dev"))
        self.ws_video_model_combo.set(cfg.get("WAVESPEED_VIDEO_MODEL", "wavespeed-ai/ltx-2.3-text-to-video"))
        self.ws_audio_model_combo.set(cfg.get("WAVESPEED_AUDIO_MODEL", "elevenlabs/text-to-speech"))
        self.content_style_combo.set(cfg.get("CONTENT_STYLE", "Podcast"))
        self.script_length_combo.set(cfg.get("SCRIPT_LENGTH", "Medium (~5 minutes)"))
        aspect = cfg.get("VIDEO_ASPECT_RATIO", "16:9 (Horizontal)")
        self.aspect_ratio_combo.set(aspect)
        self.main_aspect_ratio_combo.set(aspect)
        self.fact_check_var.set(cfg.get("FACT_CHECK_ENABLED", False))
        self.metadata_var.set(cfg.get("GENERATE_METADATA", False))
        self.timestamps_var.set(cfg.get("GENERATE_TIMESTAMPS", True))
        self.caption_var.set(cfg.get("CAPTION_ENABLED", False))
        self.add_music_var.set(cfg.get("ADD_MUSIC", False))
        self.generate_snippets_var.set(cfg.get("GENERATE_SNIPPETS", False))
        self.generate_thumbnail_var.set(cfg.get("GENERATE_THUMBNAIL", False))
        # Restore background mode - derive from BG_MODE or fall back to old booleans
        saved_mode = cfg.get("BG_MODE", "")
        if not saved_mode:
            if cfg.get("TIMED_IMAGES_AS_SLIDESHOW", False): saved_mode = "Image Slideshow"
            elif cfg.get("GENERATE_TIMED_IMAGES", False): saved_mode = "Image Slideshow"
            else: saved_mode = "AI Video"
        self.bg_mode_var.set(saved_mode)
        self._on_bg_mode_change(saved_mode)
        # Restore counts
        self.image_count_entry.delete(0, "end")
        self.image_count_entry.insert(0, str(cfg.get("IMAGE_COUNT", 8)))
        self.video_count_entry.delete(0, "end")
        self.video_count_entry.insert(0, str(cfg.get("VIDEO_CLIP_COUNT", 1)))
        self.video_title_entry.insert(0, cfg.get("VIDEO_TITLE", ""))
        self.video_desc_entry.insert("1.0", cfg.get("VIDEO_DESCRIPTION", ""))
        self.video_tags_entry.insert(0, cfg.get("VIDEO_TAGS", ""))
        self.update_features_based_on_style(self.content_style_combo.get())

    
    def get_history_items(self):
        return [item for item in os.listdir('.') if os.path.isdir(item) and not item.startswith('.')]
    
    def delete_history_item(self, item_name):
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{item_name}'?"):
            try:
                shutil.rmtree(item_name); messagebox.showinfo("Success", f"Deleted '{item_name}'.")
                self.update_history_tab()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete '{item_name}': {e}")
    
    def update_history_tab(self):
        for widget in self.history_tab.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.history_tab, text="Generated Content History", font=("Arial", 20, "bold")).pack(pady=(20, 10))
        items = self.get_history_items()
        if not items:
            ctk.CTkLabel(self.history_tab, text="No history found.").pack(pady=20); return
        for item in items:
            row = ctk.CTkFrame(self.history_tab); row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(row, text=item, anchor="w", font=("Arial", 12)).pack(side="left", padx=10, expand=True, fill="x")
            ctk.CTkButton(row, text="Delete", command=lambda i=item: self.delete_history_item(i), fg_color="#c42034", hover_color="#851622").pack(side="right", padx=10)
    
    def generate_seo_only(self):
        topic = self.topic_entry.get().strip()
        if not topic: messagebox.showerror("Error", "Please enter a topic first."); return
        logging.info("📄 Generating SEO metadata only...")
        try:
            google_client = GoogleClient(self.config['GEMINI_API_KEY'])
            news_client = NewsApiClient(self.config.get("NEWS_API_KEY"))
            research = google_client.deep_research(topic, self.config.get("PODCAST_LANGUAGE", "English"), news_client)
            script = google_client.generate_podcast_script(topic, research, self.config) # Generate a dummy script for context
            metadata = google_client.generate_seo_metadata(topic, script)
            self.video_title_entry.delete(0, ctk.END); self.video_title_entry.insert(0, metadata.get("title", ""))
            self.video_desc_entry.delete("1.0", ctk.END); self.video_desc_entry.insert("1.0", metadata.get("description", ""))
            self.video_tags_entry.delete(0, ctk.END); self.video_tags_entry.insert(0, metadata.get("tags", ""))
            logging.info("✅ SEO metadata generated and pre-filled.")
            messagebox.showinfo("Success", "SEO Title and Description have been generated!")
        except Exception as e:
            logging.error(f"❌ SEO Generation Error: {e}", exc_info=True); messagebox.showerror("Error", f"Failed to generate SEO: {e}")
    
    def browse_file(self, entry_widget):
        filename = filedialog.askopenfilename()
        if filename:
            entry_widget.delete(0, ctk.END); entry_widget.insert(0, filename)
    
    def youtube_auth(self):
        CLIENT_SECRETS_FILE = "client_secrets.json"
        if not os.path.exists(CLIENT_SECRETS_FILE): 
            messagebox.showerror("Authentication Error", f"{CLIENT_SECRETS_FILE} not found. Please place it in the application's root directory.")
            return None
        credentials = None; pickle_file = Path("token.pickle")
        if pickle_file.exists():
            with open(pickle_file, "rb") as token: credentials = pickle.load(token)
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token: 
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    logging.error(f"Failed to refresh token: {e}")
                    pickle_file.unlink() # Delete bad token
                    credentials = None # Force re-authentication
            if not credentials:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=["https://www.googleapis.com/auth/youtube.upload"], redirect_uri='http://localhost:8080/')
                credentials = flow.run_local_server(port=8080)
            with open(pickle_file, "wb") as f: pickle.dump(credentials, f)
        return credentials

    def update_upload_progress(self, status_text, progress_value):
        """Safely updates the upload progress bar and status label from a background thread."""
        def update_ui():
            self.upload_status_label.configure(text=status_text)
            self.upload_progress_bar.set(progress_value)
        self.after(0, update_ui)

    def start_youtube_upload_thread(self):
        """Starts the YouTube upload process in a separate thread to avoid freezing the GUI."""
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', self.topic_entry.get().strip())
        
        video_path = self.video_path_entry.get().strip() or os.path.join(safe_topic, "final_podcast_video.mp4")
        thumbnail_path = self.thumbnail_path_entry.get().strip() or os.path.join(safe_topic, "generated_image.png")

        if not os.path.exists(video_path):
            messagebox.showerror("File Not Found", f"Video file not found at '{video_path}'. Please generate it first or select a valid file.")
            return

        self.youtube_upload_button.configure(state="disabled")
        self.update_upload_progress("Starting upload...", 0)

        upload_thread = threading.Thread(
            target=self.upload_youtube_logic,
            args=(video_path, thumbnail_path, self.video_title_entry.get(), self.video_desc_entry.get("1.0", ctk.END), self.video_tags_entry.get().split(",")),
            daemon=True
        )
        upload_thread.start()
    
    def upload_youtube_logic(self, video_path, thumbnail_path, title, description, tags):
        """The core logic for uploading to YouTube, designed to be run in a thread."""
        try:
            self.update_upload_progress("Authenticating with YouTube...", 0.05)
            credentials = self.youtube_auth()
            if not credentials: 
                logging.error("❌ YouTube authentication failed."); return

            youtube = build("youtube", "v3", credentials=credentials)
            
            request_body = {
                "snippet": {"title": title, "description": description, "tags": [tag.strip() for tag in tags], "categoryId": "22"},
                "status": {"privacyStatus": "public"}
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=",".join(request_body.keys()), body=request_body, media_body=media)
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.update_upload_progress(f"Uploading video... {progress}%", float(progress / 100))
            
            video_id = response.get('id')
            logging.info(f"✅ Video uploaded! Video ID: {video_id}")
            
            if os.path.exists(thumbnail_path):
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
                logging.info("✅ Thumbnail uploaded successfully.")
            
            messagebox.showinfo("Upload Complete", f"Successfully uploaded to YouTube!\nURL: https://youtube.com/watch?v={video_id}")

        except Exception as e:
            logging.error(f"❌ YouTube upload failed: {e}", exc_info=True)
            messagebox.showerror("Upload Error", f"An error occurred during upload: {e}")
        finally:
            self.after(0, self.youtube_upload_button.configure, {"state": "normal"})

    def upload_facebook(self):
        safe_topic = re.sub(r'[\\/:*?"<>|]', '', self.topic_entry.get().strip())
        video_path = self.video_path_entry.get().strip() or os.path.join(safe_topic, "final_podcast_video.mp4")
        if not os.path.exists(video_path): messagebox.showerror("Error", f"Video not found at '{video_path}'."); return
        access_token = self.config.get("FACEBOOK_ACCESS_TOKEN", "")
        if not access_token: messagebox.showerror("Error", "Facebook Access Token not found in Settings."); return
        logging.info("▶️ Uploading to Facebook...")
        try:
            with open(video_path, 'rb') as f: video_data = f.read()
            init_url = "https://graph-video.facebook.com/v20.0/me/videos"
            init_params = {"access_token": access_token, "upload_phase": "start", "file_size": os.path.getsize(video_path)}
            init_response = requests.post(init_url, params=init_params).json()
            if "error" in init_response: raise RuntimeError(f"API Error: {init_response['error']['message']}")
            
            upload_session_id = init_response["upload_session_id"]
            upload_url = f"https://graph-video.facebook.com/v20.0/{upload_session_id}"
            upload_headers = {"Authorization": f"OAuth {access_token}", "file_offset": "0"}
            requests.post(upload_url, headers=upload_headers, data=video_data).json()

            finish_url = "https://graph-video.facebook.com/v20.0/me/videos"
            finish_params = {
                "access_token": access_token, "upload_phase": "finish", "upload_session_id": upload_session_id,
                "title": self.video_title_entry.get(), "description": self.video_desc_entry.get("1.0", ctk.END)
            }
            requests.post(finish_url, params=finish_params).json()
            messagebox.showinfo("Upload Complete", "Successfully published to Facebook!")
        except Exception as e:
            logging.error(f"❌ Facebook upload failed: {e}", exc_info=True); messagebox.showerror("Upload Error", f"An error occurred: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
