# 🛠️ AI Content Studio - Complete Installation Guide

This guide will walk you through the complete installation process from scratch, including how to install required system dependencies like FFmpeg.

## Step 1: System Requirements

Before touching the code, you need to ensure three core dependencies are installed on your computer:

### 1. Python 3.10+
- **Windows:** Download from [python.org](https://www.python.org/downloads/). During the installer, **ensure you check the box that says "Add Python to PATH"**.
- **Mac:** Install via Homebrew: `brew install python`

### 2. Node.js (v18+)
- Download and install the LTS version from [nodejs.org](https://nodejs.org/). This will install both `node` and `npm`.

### 3. FFmpeg (Crucial Step)
FFmpeg is the video processing engine that slices, crops, and burns subtitles into the videos. If this is not installed, the app **will crash** during video generation.

**Windows Installation:**
1. Download a Windows build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z).
2. Extract the folder using 7-Zip or WinRAR.
3. Rename the extracted folder to `ffmpeg` and move it to the root of your `C:\` drive (so it sits at `C:\ffmpeg`).
4. **Add to PATH:** 
   - Press the Windows Key and search for "Environment Variables".
   - Click "Edit the system environment variables".
   - Click the "Environment Variables..." button at the bottom.
   - Under "System variables", find the variable named `Path`, select it, and click "Edit".
   - Click "New" and paste: `C:\ffmpeg\bin`
   - Click OK on all windows to save.
   - *Restart your computer or terminal to apply the changes.*

**Mac Installation:**
```bash
brew install ffmpeg
```

---

## Step 2: Backend Setup (FastAPI & AI Pipeline)

The backend handles the AI video processing, downloading, and API interactions.

1. Open a terminal and navigate to the root directory of this project:
   ```bash
   cd AI-Content-Studio
   ```

2. Create a virtual environment to isolate the Python dependencies:
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   - **Windows:** `.venv\Scripts\activate`
   - **Mac/Linux:** `source .venv/bin/activate`

4. Install all required Python packages (FastAPI, yt-dlp, whisper, etc.):
   ```bash
   pip install -r requirements.txt
   
   # Note: Ensure python-multipart is installed for file uploads to work:
   pip install python-multipart
   ```

---

## Step 3: Frontend Setup (Next.js Dashboard)

The frontend provides the sleek UI and dashboard to control the AI tools.

1. Open a **new, separate terminal window** (leave the backend one open).
2. Navigate to the `web` folder inside the project:
   ```bash
   cd AI-Content-Studio/web
   ```
3. Install the Node modules:
   ```bash
   npm install
   ```

---

## Step 4: Running the Studio

To run AI Content Studio, you need to run **both** servers simultaneously.

**Terminal 1 (Backend):**
Ensure your virtual environment is active (you should see `(.venv)` in the prompt), then run:
```bash
python server/main.py
```
*(The backend runs on http://localhost:8008)*

**Terminal 2 (Frontend):**
Navigate to the `web` folder, then run:
```bash
npm run dev
```
*(The frontend runs on http://localhost:3000)*

---

## Step 5: Setting Up Your API Keys

1. Open your browser and go to `http://localhost:3000`.
2. Click on the **Settings** tab in the sidebar.
3. Paste in your **Google Gemini API Key** (You can get a free one from [Google AI Studio](https://aistudio.google.com/)).
4. Click **Save Settings**.

**🎉 You're all set! Head over to the Magic Clipper or Podcast Studio tabs to start creating viral AI content!**
