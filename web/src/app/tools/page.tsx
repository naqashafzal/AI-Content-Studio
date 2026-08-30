"use client";

import { useState } from "react";
import { Type, Crop, Mic, Upload, Download, Loader2, Play } from "lucide-react";

export default function ToolsPage() {
  // Caption State
  const [captionFile, setCaptionFile] = useState<File | null>(null);
  const [captionStyle, setCaptionStyle] = useState("Podcast");
  const [captionLang, setCaptionLang] = useState("English");
  const [captionStatus, setCaptionStatus] = useState("idle");
  const [captionResult, setCaptionResult] = useState("");

  // AR State
  const [arFile, setArFile] = useState<File | null>(null);
  const [targetAr, setTargetAr] = useState("9:16");
  const [arStatus, setArStatus] = useState("idle");
  const [arResult, setArResult] = useState("");

  // TTS State
  const [ttsText, setTtsText] = useState("");
  const [ttsVoice, setTtsVoice] = useState("Kore");
  const [ttsStatus, setTtsStatus] = useState("idle");
  const [ttsResult, setTtsResult] = useState("");

  const handleCaption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!captionFile) return;
    setCaptionStatus("loading");
    
    const formData = new FormData();
    formData.append("file", captionFile);
    formData.append("style", captionStyle);
    formData.append("language", captionLang);

    try {
      const res = await fetch("http://localhost:8008/api/tools/caption", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      setCaptionResult(data.path.replace(/\\/g, '/').split('workspace/')[1]);
      setCaptionStatus("done");
    } catch (e) {
      alert("Caption generation failed.");
      setCaptionStatus("idle");
    }
  };

  const handleConvert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!arFile) return;
    setArStatus("loading");
    
    const formData = new FormData();
    formData.append("file", arFile);
    formData.append("target_ar", targetAr);

    try {
      const res = await fetch("http://localhost:8008/api/tools/convert", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      setArResult(data.path.replace(/\\/g, '/').split('workspace/')[1]);
      setArStatus("done");
    } catch (e) {
      alert("Conversion failed.");
      setArStatus("idle");
    }
  };

  const handleTTS = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ttsText) return;
    setTtsStatus("loading");

    try {
      const res = await fetch("http://localhost:8008/api/tools/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: ttsText, voice: ttsVoice })
      });
      const data = await res.json();
      setTtsResult(data.path.replace(/\\/g, '/').split('workspace/')[1]);
      setTtsStatus("done");
    } catch (e) {
      alert("TTS generation failed.");
      setTtsStatus("idle");
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Video Tools</h1>
        <p className="text-zinc-400 mt-1">Standalone utilities for rapid audio and video manipulation.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Tool 1: Auto-Captioner */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 rounded-lg bg-blue-500/20 text-blue-400">
              <Type className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Auto-Captioner</h2>
              <p className="text-xs text-zinc-400">Burn animated subs into any video</p>
            </div>
          </div>

          <form onSubmit={handleCaption} className="space-y-4 flex-1 flex flex-col">
            <div className="flex-1 space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Source Video</label>
                <div className="relative">
                  <input type="file" accept="video/mp4" onChange={e => setCaptionFile(e.target.files?.[0] || null)} className="hidden" id="cap-file" />
                  <label htmlFor="cap-file" className="flex items-center justify-center gap-2 p-4 rounded-xl border border-dashed border-white/20 hover:border-white/50 hover:bg-white/5 transition-all cursor-pointer text-sm font-medium text-zinc-300">
                    <Upload className="h-4 w-4" /> {captionFile ? captionFile.name : 'Upload MP4...'}
                  </label>
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Style</label>
                <select value={captionStyle} onChange={e => setCaptionStyle(e.target.value)} className="modern-select">
                  <option className="bg-black" value="Hormozi">Hormozi Style</option>
                  <option className="bg-black" value="Podcast">Podcast Style</option>
                </select>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 mt-auto">
              {captionStatus === "loading" ? (
                <button disabled className="w-full py-3 bg-white/20 text-white font-bold rounded-xl flex justify-center items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" /> Processing...
                </button>
              ) : captionStatus === "done" ? (
                <a href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(captionResult)}`} download className="w-full py-3 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold rounded-xl flex justify-center items-center gap-2 hover:bg-emerald-500/30 transition-all">
                  <Download className="h-5 w-5" /> Download Result
                </a>
              ) : (
                <button type="submit" className="w-full py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                  Generate Captions
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Tool 2: AR Converter */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 rounded-lg bg-fuchsia-500/20 text-fuchsia-400">
              <Crop className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Ratio Converter</h2>
              <p className="text-xs text-zinc-400">Resize videos for TikTok / YouTube</p>
            </div>
          </div>

          <form onSubmit={handleConvert} className="space-y-4 flex-1 flex flex-col">
            <div className="flex-1 space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Source Video</label>
                <div className="relative">
                  <input type="file" accept="video/mp4" onChange={e => setArFile(e.target.files?.[0] || null)} className="hidden" id="ar-file" />
                  <label htmlFor="ar-file" className="flex items-center justify-center gap-2 p-4 rounded-xl border border-dashed border-white/20 hover:border-white/50 hover:bg-white/5 transition-all cursor-pointer text-sm font-medium text-zinc-300">
                    <Upload className="h-4 w-4" /> {arFile ? arFile.name : 'Upload MP4...'}
                  </label>
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Target Ratio</label>
                <select value={targetAr} onChange={e => setTargetAr(e.target.value)} className="modern-select">
                  <option className="bg-black" value="9:16">9:16 (TikTok / Shorts)</option>
                  <option className="bg-black" value="16:9">16:9 (YouTube)</option>
                  <option className="bg-black" value="1:1">1:1 (Instagram)</option>
                </select>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 mt-auto">
              {arStatus === "loading" ? (
                <button disabled className="w-full py-3 bg-white/20 text-white font-bold rounded-xl flex justify-center items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" /> Processing...
                </button>
              ) : arStatus === "done" ? (
                <a href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(arResult)}`} download className="w-full py-3 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold rounded-xl flex justify-center items-center gap-2 hover:bg-emerald-500/30 transition-all">
                  <Download className="h-5 w-5" /> Download Result
                </a>
              ) : (
                <button type="submit" className="w-full py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                  Convert Ratio
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Tool 3: TTS Generator */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 rounded-lg bg-amber-500/20 text-amber-400">
              <Mic className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">AI Voice (TTS)</h2>
              <p className="text-xs text-zinc-400">Generate studio-quality voiceovers</p>
            </div>
          </div>

          <form onSubmit={handleTTS} className="space-y-4 flex-1 flex flex-col">
            <div className="flex-1 space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Script</label>
                <textarea 
                  value={ttsText} 
                  onChange={e => setTtsText(e.target.value)} 
                  className="modern-input min-h-[120px] resize-y" 
                  placeholder="Enter text to speak..." 
                  required 
                />
              </div>
              
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Voice Profile</label>
                <select value={ttsVoice} onChange={e => setTtsVoice(e.target.value)} className="modern-select">
                  <option className="bg-black" value="Kore">Kore (Standard Male)</option>
                  <option className="bg-black" value="Aoede">Aoede (Standard Female)</option>
                  <option className="bg-black" value="Charon">Charon (Deep/Gritty Male)</option>
                  <option className="bg-black" value="Fenrir">Fenrir (Hype Male)</option>
                </select>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 mt-auto">
              {ttsStatus === "loading" ? (
                <button disabled className="w-full py-3 bg-white/20 text-white font-bold rounded-xl flex justify-center items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" /> Generating...
                </button>
              ) : ttsStatus === "done" ? (
                <div className="space-y-3">
                  <audio controls className="w-full h-10" src={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(ttsResult)}`} />
                  <a href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(ttsResult)}`} download className="w-full py-2 bg-white/10 text-white border border-white/20 text-sm font-bold rounded-lg flex justify-center items-center gap-2 hover:bg-white/20 transition-all">
                    <Download className="h-4 w-4" /> Download MP3
                  </a>
                </div>
              ) : (
                <button type="submit" className="w-full py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.2)]">
                  Generate Audio
                </button>
              )}
            </div>
          </form>
        </div>

      </div>
    </div>
  );
}