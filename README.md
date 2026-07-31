<p align="center">
  <a href="https://naqashafzal.gumroad.com/coffee" target="_blank">
    <img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me A Coffee">
  </a>
</p>

# 🤖 Nullpk AI Content Studio  
**Your AI-Powered YouTube Studio**  

Welcome to **Nullpk AI Content Studio**, a powerful all-in-one application designed to automate the **entire lifecycle of YouTube video creation** using cutting-edge generative AI.  

This tool takes a single topic as input and orchestrates a complete pipeline: from **deep research & scriptwriting** to **voice generation, video creation, thumbnails, captions, and direct publishing**.  
It’s your personal content studio — powered by AI.  

---

## 👑 Creator  
This application was created by **Naqash Afzal**.  

---

## 🔋 How to Use Tutorial:
-<a href="https://youtu.be/9JpSs57RjbY?si=5ihW2Pl_JFtwAz45" > Full Video Tutorial </a>

---

## ✨ Key Features  

### 📝 Automated Research & Scripting  
- **Deep Research**: Uses Google Search grounding for in-depth research.  
- **News Integration**: Pulls live headlines via NewsAPI.  
- **Fact-Checking & Revision**: Optional AI review for accuracy.  
- **Dynamic Scriptwriting**: Generates scripts for podcasts, documentaries, stories & more.  

### 🎙️ AI Voice & Audio Generation  
- **Multi-Speaker TTS**: Google’s latest models for natural host/guest voices.  
- **Background Music**: Auto-mixes music for a professional sound.  

### 🎬 Advanced Video & Visuals Production  
- **AI Video Generation**: Background videos via Vertex AI (Imagen 2) & WaveSpeed AI.  
- **Automated Thumbnails**: AI character + bold topic text (via ffmpeg).  
- **Context-Aware Images**: Timed overlays & slideshow-style videos.  

### 🚀 Publishing & SEO  
- **Auto-Captioning**: Whisper generates styled `.ass` captions.  
- **SEO Metadata**: Titles, descriptions & tags auto-generated.  
- **Chapter Timestamps**: Script-based smart timestamping.  
- **Direct Uploading**: Seamless upload to **YouTube & Facebook**.  

---

## 🛠️ Technology Stack  

- **Language**: Python  
- **GUI**: CustomTkinter  

### Core AI Models  
- **Text & Research**: Google Gemini (gemini-2.5-flash)  
- **TTS**: Google Gemini TTS  
- **Images**: Google Vertex AI (Imagen 3)  
- **Video**: Vertex AI (Imagen 2), WaveSpeed AI  

### APIs & Libraries  
- `google-generativeai`  
- `google-cloud-aiplatform`  
- `vertexai`  
- `newsapi-python`  
- `requests`  

### Audio & Video Processing  
- **ffmpeg** (Required)  
- `openai-whisper`  
- `pydub`  
- `pysubs2`  

---

## ⚙️ Installation & Setup  

### 1. Prerequisites  
- Python **3.10+** → [Download](https://www.python.org/)  
- Git → [Download](https://git-scm.com/)  
- FFmpeg → [Download](https://ffmpeg.org/)  
  - Add `ffmpeg/bin` to your PATH.  

### 2. Clone Repository  
```bash
git clone https://github.com/your-username/Nullpk-Ai-Content-Studio.git
cd Nullpk-Ai-Content-Studio
```

### 3. Virtual Environment  
```bash
python -m venv .venv

# Activate
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 4. Install Dependencies  
```bash
pip install -r requirements.txt
```

### 5. Configuration  
- On first run, a `config.json` will be created. Fill in your API keys:  
  - **Gemini API Key** (Google AI Studio)  
  - **GCP Project ID & Location**  
  - **WaveSpeed AI Key** *(optional)*  
  - **NewsAPI Key** *(optional)*  

#### YouTube Upload Setup  
1. Enable **YouTube Data API v3** in [Google Cloud Console](https://console.cloud.google.com/).  
2. Create OAuth 2.0 credentials (Desktop App).  
3. Download as `client_secrets.json` → place in root directory.  

#### Assets Folder  
Create an `assets` folder in the root:  
- `font.ttf` → Font for thumbnails.  
- `background_music.mp3` → Music for videos.  

---

## ▶️ Run the Application  
```bash
python main.py
```
The GUI will launch.  

---

## 🚀 Usage  
1. Enter a **topic**.  
2. Select **style & options** (Podcast, Documentary, Captions, Thumbnails, etc.).  
3. Configure **API keys, voices & prompts** in Settings.  
4. Click **🚀 Run Pipeline**.  
5. Review SEO metadata in **Publish tab** → upload directly.  

---

## 🤝 Contributing  
Contributions are welcome!  

1. Fork the repo  
2. Create a branch (`git checkout -b feature/AmazingFeature`)  
3. Commit (`git commit -m 'Add some AmazingFeature'`)  
4. Push (`git push origin feature/AmazingFeature`)  
5. Open a Pull Request  

---

## 📄 License  
This project is licensed under the **MIT License** – see [LICENSE](LICENSE).  

---

## 🙏 Acknowledgments  
- **Google AI** for Gemini & Vertex AI models.  
- **FFmpeg** & **Whisper** for amazing open-source tools.  
- **CustomTkinter** for GUI simplicity.  

---


## ☕ Support / Coffee

If you enjoy this tool and want to support continued development:

<p align="center">
  <a href="https://naqashafzal.gumroad.com/coffee" target="_blank">
    <img src="https://img.shields.io/badge/☕-Support%20My%20Work-FFDD00?style=for-the-badge" alt="Buy Me A Coffee">
  </a>
</p>

---

**Author:** Naqash Afzal — *Nullpk Content Automation*
