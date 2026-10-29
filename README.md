<div align="center">
  <h1>🎬 AI Content Studio — Next Generation (v2.0)</h1>
  <p><strong>The Most Intelligent Open-Source Autonomous AI Video, Podcast & Content Creation Platform</strong></p>
  
  [![YouTube](https://img.shields.io/badge/Subscribe_on-YouTube-FF0000?style=for-the-badge&logo=youtube)](https://www.youtube.com/@naqashai)
  [![Patreon](https://img.shields.io/badge/Support_on-Patreon-f96854?style=for-the-badge&logo=patreon)](https://www.patreon.com/c/naqashafzal)
  [![Instagram](https://img.shields.io/badge/Follow_on-Instagram-E4405F?style=for-the-badge&logo=instagram)](https://www.instagram.com/naqashafzal/)
  ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
  ![Tests](https://img.shields.io/badge/Tests-38%2F38%20Passing-brightgreen?style=for-the-badge)
</div>

---

**AI Content Studio Next-Gen (v2.0)** transforms video generation from a rigid script-to-video pipeline into an autonomous creative production system. Equipped with a supervisory multi-agent director, multimodal viral clipping, computer-vision style cloning, broadcast loudness mastering, and a nonlinear transcript ripple-editor, it handles your entire creative production workflow from research to export.

If you love this project and want to support its ongoing development, please consider helping out on **[Patreon](https://www.patreon.com/c/naqashafzal)** or follow the journey on **[Instagram](https://www.instagram.com/naqashafzal/)**!

---

## 🌟 Key Features (Complete Next-Gen Suite)

### 🎬 1. Autonomous AI Agent Director & Visual Storyboard
- **Supervisory Agent Team:** Orchestrates research, scriptwriting, quality assurance, and persistent memory across specialized agents (`StrategyAgent`, `TrendDiscoveryAgent`, `ResearchAgent`, `CreativeDirectorAgent`, `QualityAssuranceAgent`, `LearningAgent`).
- **Self-Healing QA Retry Loop:** Automatically inspects draft scripts against factual accuracy, hook retention, and narrative pacing. If the QA score is below 80/100, the director autonomously critiques and rewrites weak scenes before generating expensive media.
- **Interactive Storyboard Scene Cards:** Review and edit scene-by-scene script narrations, visual prompts, framing badges, and music/SFX cues.
- **Scene Locking & Selective Regeneration:** Lock approved scenes to keep them intact, and selectively regenerate individual scenes with custom user instructions (e.g., *"Make this shot a drone wide establishing shot with more suspense"*).

### ✂️ 2. Magic AI Clipper 2.0 (Multimodal OpusClip Engine)
Convert any long-form YouTube video, podcast, or stream into high-retention vertical shorts (TikTok, Reels, YouTube Shorts).
- **Multimodal Hotspot Fusion:** Combines Whisper transcriptions with **audio RMS volume peaks** (detecting applause, laughter, volume spikes, punchlines) and **OpenCV HSV histogram cuts** to identify true audio-visual moments of viral intensity.
- **Active Speaker Tracking with Cut Hysteresis:** Face detection with intelligent shot hysteresis (minimum 1.5s interval) prevents camera jitter on minor head turns.
- **B-Roll Auto-Injection:** Automatically fetches contextual stock B-roll to cover talking-head pauses and amplify viewer retention.
- **Dynamic Captions:** Renders high-accuracy karaoke subtitles directly into the video with custom fonts, colors, and word-grouping.

### 🎨 3. Intelligent Style Engine & Reference Video Cloner
- **Clone Editing Styles via Computer Vision:** Upload reference footage from creators like MrBeast, Alex Hormozi, or Vox. The engine calculates average shot durations, cut frequencies, and caption animations into reusable style profiles without infringing on copyrighted footage.
- **Live Brand Kit Studio:** Real-time 9:16 short preview with custom dual-accent color palettes, typography selection, watermark placement/opacity, and stinger intros.

### 🎞️ 4. Nonlinear Timeline & Transcript Ripple-Editor
- **Multi-Track Timeline:** Full multi-layered canvas supporting Video clips, B-Roll overlays, Audio/SFX tracks, and Subtitle events.
- **Text-Based Ripple Editing:** Delete words or sentences in the transcript, and the underlying video and audio automatically ripple-cut to match.
- **AI Timeline Assistant:** Natural language timeline adjustments (e.g., *"Speed up pacing"*, *"Mute section"*).

### 🔊 5. Studio Audio Mastering & Urdu / Roman Urdu Support
- **Broadcast Loudness Normalization:** Integrated FFmpeg EBU R128 `loudnorm=I=-14:TP=-1.5:LRA=11` audio mastering across all video renders, matching YouTube and TikTok loudness standards.
- **Urdu & Roman Urdu Phonetic Engine:** Comprehensive Urdu Unicode character normalization and Roman Urdu phonetic dictionary (e.g., *kese -> kaisay*, *kyun -> kyoon*, *mujhe -> mujhey*, *dunya -> duniya*, *acha -> ach-cha*) for natural, glitch-free neural TTS pronunciation.

### ⚡ 6. Resilient SQLite Queue & Multi-Model Gateway
- **Durable Task Queue:** SQLite-backed job engine with stage-by-stage checkpoints (`research`, `storyboard`, `qa_review`) and automatic recovery of interrupted jobs across restarts.
- **Multi-Model Router:** Unified provider gateway supporting Google Gemini, OpenAI-compatible endpoints, and local Ollama with automatic failover and error isolation.
- **Zero Mock Exploits:** True OAuth token management, SQLite credential storage, and manual publishing packages.

### 🤖 7. Auto-Pilot Campaigns & AI Explainer Videos
- **Automated Campaigns:** Schedule 24/7 background bots to scan trending topics and generate content on automated schedules.
- **Faceless Explainers:** Script, narrate, and compile multi-minute educational and storytelling videos from movie files or YouTube URLs.

### 🛠️ 8. Smart Media Utilities
- **Standalone Auto-Captioner:** Burn animated captions into pre-existing MP4 videos.
- **Aspect Ratio Converter:** Seamlessly crop and scale videos between 9:16, 16:9, and 1:1.
- **Studio TTS Generator:** Instant voiceover generator with character voice presets.

---

## 🔋 How to Use Tutorial
🔥 **NEW FULL DETAILED VIDEO TUTORIAL COMING SOON!** 🔥  
A complete step-by-step video for this Next-Gen v2.0 version is currently in production. Make sure to **[Subscribe to our YouTube Channel (@naqashai)](https://www.youtube.com/@naqashai)** so you don't miss it when it drops!

**Old Version References:**
- If you are looking for the original codebase, you can find the old version safely stored in the Git history.
- 👉 **<a href="https://youtu.be/9JpSs57RjbY?si=5ihW2Pl_JFtwAz45">Watch the Old Version Video Tutorial</a>**

---

## 🛠️ Tech Stack & Architecture

Built with a modern, high-performance tech stack designed for speed and scalability:

### Frontend (Web UI)
- **Framework:** Next.js (React) with Turbopack
- **Styling:** Vanilla CSS design system + Glassmorphism UI
- **Icons:** Lucide React
- **Real-time Engine:** WebSockets for live agent logs, progress updates, and timeline syncing

### Backend (API Engine)
- **Server:** FastAPI (Python 3.12) & Uvicorn
- **Database / Queue:** SQLite + SQLAlchemy ORM with stage checkpoints
- **Video Processing:** FFmpeg (multimodal slicing, cropping, loudnorm mastering, caption burning)
- **Downloading:** `yt-dlp` (bypasses YouTube blocks and downloads source media)
- **Transcription:** OpenAI Whisper (offline, word-level audio-to-text transcription)
- **Subtitles:** `pysubs2` (generates and styles `.ass` subtitle files)
- **AI Brain:** Multi-Model Gateway (Google Gemini, OpenAI-compatible APIs, local Ollama)
- **Computer Vision:** OpenCV (`cv2`) for active speaker tracking and histogram-based scene cut analysis

---

## Production deployment and security

See [DEPLOYMENT.md](DEPLOYMENT.md) for authenticated setup, HTTPS proxy configuration,
legacy data migration, persistent storage, OAuth, job recovery, and release checks.
The Studio uses one shared administrator account and one backend worker process.

## 🚀 Getting Started

### Prerequisites
Before running the application, ensure you have the following installed on your system:
1. **Python 3.12** (Make sure to check "Add Python to PATH" during installation)
2. **Node.js (v22+)** & npm
3. **FFmpeg** (Must be installed and added to your system's PATH variable)
   - *Windows via winget:* `winget install Gyan.FFmpeg`
   - *macOS via homebrew:* `brew install ffmpeg`
   - *Ubuntu/Debian:* `sudo apt update && sudo apt install -y ffmpeg`
4. A **Google Gemini API Key** (Set via the UI Settings tab)

---

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/naqashafzal/AI-Content-Studio.git
   cd AI-Content-Studio
   ```

2. **Setup the Python Backend:**
   ```bash
   # Create a virtual environment
   python -m venv .venv
   
   # Activate it (Windows)
   .venv\Scripts\activate
   # Activate it (Mac/Linux)
   source .venv/bin/activate
   
   # Install backend dependencies
   pip install -r requirements.txt
   ```

3. **Setup the Next.js Frontend:**
   ```bash
   cd web
   npm ci
   cd ..
   ```

---

### Running the Application

#### ⚡ 1-Click Launch (Windows - Recommended)
Simply run or double-click **`start.bat`**:
```cmd
start.bat
```
The automated launcher will verify Python 3.12, Node.js 18+, and FFmpeg, initialize storage folders, activate `.venv`, check dependencies, launch both server consoles, and automatically open your browser to `http://localhost:3000`!

#### 🛠️ Manual Launch (All Platforms)
You can run both servers manually in separate terminal windows:

**1. Start the Backend API (from the root directory):**
```bash
# Ensure your virtual environment is active
python server/main.py
# The FastAPI server will run on http://localhost:8008
```

**2. Start the Frontend UI (from the `/web` directory):**
```bash
cd web
npm run dev
# The Next.js app will run on http://localhost:3000
```

Open your browser and navigate to `http://localhost:3000` to start creating!

---

## 🧪 Testing

The repository includes a comprehensive automated test suite covering job queues, media processing, AI orchestrator loops, secret masking, and viral topic discovery:

```bash
# Run the full test suite
pytest tests/
# 38 passed
```

---

## 🤝 Support & Connect

Building and maintaining this open-source project takes a lot of time and effort! If this tool has helped you grow your channels, automate your workflows, or make money, please consider supporting me:

- 💖 **Support on Patreon:** [patreon.com/c/naqashafzal](https://www.patreon.com/c/naqashafzal)
- 📸 **Follow on Instagram:** [@naqashafzal](https://www.instagram.com/naqashafzal/)
- 📺 **Subscribe on YouTube:** [@naqashai](https://www.youtube.com/@naqashai)

Your support helps me keep updating the tool, adding new AI features, and keeping the core open-source for everyone!

---

## ⚠️ Troubleshooting

- **Clipper Audio is out of sync:** Ensure you are using the latest backend code. We force `-c:a aac` during FFmpeg extraction to prevent audio PTS drift.
- **0.00s Clips generated:** This means the AI couldn't parse the timestamps. Ensure `pipeline_shorts.py` formats the transcript chunks with `[start - end]` brackets.
- **FFmpeg errors / "Subtitles not found":** Ensure FFmpeg is installed globally on your machine and that `ffmpeg` is a recognized command in your terminal.
- **Secret Keys Showing as `sk-***`:** This is an intentional security hardening feature. When updating other configuration fields, your saved keys are securely retained without being overwritten by masked values.

---

## 📄 License

This project is licensed under the MIT License.
