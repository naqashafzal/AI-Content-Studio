<div align="center">
  <h1>🎬 AI Content Studio</h1>
  <p><strong>The World's Best Open-Source AI Video & Podcast Generator</strong></p>
  
  [![Patreon](https://img.shields.io/badge/Support_on-Patreon-f96854?style=for-the-badge&logo=patreon)](https://www.patreon.com/c/naqashafzal)
  [![Instagram](https://img.shields.io/badge/Follow_on-Instagram-E4405F?style=for-the-badge&logo=instagram)](https://www.instagram.com/naqashafzal/)
  ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
</div>

---

**AI Content Studio** is the ultimate, fully-automated platform designed to generate viral social media content at the click of a button. Whether you want to generate full AI-powered video podcasts from scratch or automatically extract viral TikToks from long-form YouTube videos, AI Content Studio provides a sleek, unified dashboard to manage your entire content pipeline.

If you love this project and want to support its development, please consider helping out on **[Patreon](https://www.patreon.com/c/naqashafzal)** or follow my journey on **[Instagram](https://www.instagram.com/naqashafzal/)**!

## 🌟 Key Features

### ✂️ Magic AI Clipper (The Ultimate OpusClip Clone)
Convert any long-form YouTube video into viral, ready-to-post short-form content (TikToks, Instagram Reels, YouTube Shorts) in minutes.
- **Smart AI Curation:** Uses Google's Gemini AI and OpenAI's Whisper transcriptions to analyze the video and automatically find the most engaging 30-60 second highlights.
- **Automated Framing:** Automatically crops landscape (16:9) videos into vertical (9:16) format using advanced FFmpeg processing.
- **Dynamic Captions:** Burns professional, highly-accurate subtitles directly into the video for maximum viewer retention.
- **Custom Styling:** Fully control your caption aesthetics before generating. Choose your font (Arial, Roboto, Impact), dial in the exact pixel size, and apply custom color themes (e.g., Clean White, Viral Yellow, Neon Cyberpunk).

### 🎙️ AI Podcast Generator
Generate complete, multi-speaker podcast videos entirely from a single text prompt.
- **Script Writing:** AI dynamically writes conversational, engaging podcast scripts tailored to your niche.
- **Voice Synthesis:** Realistic text-to-speech engine brings the hosts to life with emotion and clarity.
- **Visuals & Assembly:** Automatically layers high-quality audio over dynamic background footage for a complete audio-visual experience.

### 📚 History & Projects Dashboard
- Easily browse your previously generated AI Podcasts and Magic Clipper shorts.
- Watch generated videos directly in the browser via a beautifully embedded video player.
- 1-click downloads for videos and raw text scripts.
- Safely delete and manage old projects to free up workspace storage.

## 🔋 How to Use Tutorial
Want a step-by-step guide? Check out the full walkthrough:
👉 **<a href="https://youtu.be/9JpSs57RjbY?si=5ihW2Pl_JFtwAz45">Full Video Tutorial</a>**

---

## 🛠️ Tech Stack & Architecture

Built with a modern, high-performance tech stack designed for speed and scalability:

### Frontend (Web UI)
- **Framework:** Next.js (React)
- **Styling:** Tailwind CSS + Glassmorphism UI
- **Icons:** Lucide React
- **Real-time Engine:** WebSockets for live pipeline logging and progress bars

### Backend (API Engine)
- **Server:** FastAPI (Python)
- **Video Processing:** FFmpeg (Core requirement for slicing, cropping, and caption burning)
- **Downloading:** `yt-dlp` (For bypassing YouTube blocks and downloading media)
- **Transcription:** OpenAI Whisper (Local, offline audio-to-text transcription)
- **Subtitles:** `pysubs2` (For generating and styling `.ass` subtitle files)
- **AI Brain:** Google Gemini API (For content curation, logic, and script writing)

---

## 🚀 Getting Started

### Prerequisites
Before running the application, ensure you have the following installed on your system:
1. **Python 3.10+**
2. **Node.js (v18+)** & npm
3. **FFmpeg** (Must be installed and added to your system's PATH variable)
4. A **Google Gemini API Key** (Set via the UI Settings tab)

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
   
   # Important Note: If you face issues with file uploads, ensure python-multipart is installed
   pip install python-multipart
   ```

3. **Setup the Next.js Frontend:**
   ```bash
   cd web
   npm install
   ```

### Running the Application

You need to run both the backend and frontend servers simultaneously.

**1. Start the Backend API (from the root directory):**
```bash
python server/main.py
# The FastAPI server will run on http://localhost:8008
```

**2. Start the Frontend UI (from the `/web` directory):**
```bash
npm run dev
# The Next.js app will run on http://localhost:3000
```

Open your browser and navigate to `http://localhost:3000` to start creating!

---

## 🤝 Support & Connect

Building and maintaining this open-source project takes a lot of time and effort! If this tool has helped you grow your channels, automate your workflows, or make money, please consider supporting me:

- 💖 **Support on Patreon:** [patreon.com/c/naqashafzal](https://www.patreon.com/c/naqashafzal)
- 📸 **Follow on Instagram:** [@naqashafzal](https://www.instagram.com/naqashafzal/)

Your support helps me keep updating the tool, adding new AI features, and keeping the core open-source for everyone!

---

## ⚠️ Troubleshooting

- **Clipper Audio is out of sync:** Ensure you are using the latest backend code. We force `-c:a aac` during FFmpeg extraction to prevent audio PTS drift.
- **0.00s Clips generated:** This means the AI couldn't read the timestamps. Ensure `pipeline_shorts.py` is formatting the transcript chunks with `[start - end]` brackets.
- **FFmpeg errors / "Subtitles not found":** Ensure FFmpeg is installed globally on your machine and that `ffmpeg` is a recognized terminal command.

## 📄 License
This project is licensed under the MIT License.
