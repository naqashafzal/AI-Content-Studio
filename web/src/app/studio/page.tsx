"use client";

import { apiFetch } from "@/lib/api";

import { useState, useEffect } from "react";
import { Play, Square, CheckCircle2, Loader2, Film, Settings, Zap, Ghost, Rocket, Landmark, ShoppingBag } from "lucide-react";
import { TabSelect } from "@/components/TabSelect";
import { ToggleSwitch } from "@/components/ToggleSwitch";
import { useConfig } from "@/context/ConfigContext";
import type { StudioConfig } from "@/lib/config";
import { API_BASE_URL, WS_BASE_URL, getMediaUrl } from "@/lib/api";
import { Download } from "lucide-react";

const PIPELINE_STEPS = [
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
  "Generate SEO Metadata",
  "Generate Timestamps",
  "Generate Snippets"
];

export default function CreatorStudio() {
  const { config, status } = useConfig();
  if (status === "loading") {
    return <div role="status" className="p-8 text-zinc-400">Loading saved Studio settings…</div>;
  }
  return <CreatorStudioForm initialConfig={config} />;
}

function CreatorStudioForm({ initialConfig }: { initialConfig: StudioConfig }) {
  const [topic, setTopic] = useState("");
  const [startStep, setStartStep] = useState(PIPELINE_STEPS[0]);
  const [quickPreset, setQuickPreset] = useState("Custom");
  
  const [contentStyle, setContentStyle] = useState(initialConfig.CONTENT_STYLE ?? "Documentary");
  const [style, setStyle] = useState("Cinematic Documentary");
  const [audioEngine, setAudioEngine] = useState(initialConfig.AUDIO_ENGINE ?? "Gemini API");
  const [videoEngine, setVideoEngine] = useState(initialConfig.VIDEO_ENGINE ?? "WaveSpeed AI");
  const [voice, setVoice] = useState(initialConfig.VOICE_NAME ?? "Kore");
  const [elevenVoice, setElevenVoice] = useState("Brian");
  const [aspectRatio, setAspectRatio] = useState(initialConfig.VIDEO_ASPECT_RATIO ?? "16:9");
  const [bgMode, setBgMode] = useState(initialConfig.BG_MODE ?? "AI Video");
  const [scriptLength, setScriptLength] = useState(initialConfig.SCRIPT_LENGTH ?? "Medium (~5 minutes)");
  
  const [imageCount] = useState(initialConfig.IMAGE_COUNT ?? 8);
  const [videoCount] = useState(initialConfig.VIDEO_CLIP_COUNT ?? 1);
  
  const [omnichannel, setOmnichannel] = useState(false);
  const [bgMusic, setBgMusic] = useState(initialConfig.ADD_MUSIC ?? true);
  const [autoCaptions, setAutoCaptions] = useState(initialConfig.CAPTION_ENABLED ?? true);
  const [factCheck] = useState(initialConfig.FACT_CHECK ?? false);
  const [genThumbnail] = useState(initialConfig.GENERATE_THUMBNAIL ?? false);
  const [genSeo, setGenSeo] = useState(initialConfig.GENERATE_METADATA ?? false);
  const [genTimestamps] = useState(initialConfig.GENERATE_TIMESTAMPS ?? false);
  const [genSnippets] = useState(initialConfig.GENERATE_SNIPPETS ?? false);

  const [status, setStatus] = useState("idle");
  const [jobId, setJobId] = useState("");
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState("Waiting to start...");
  const [logs, setLogs] = useState<string[]>([]);
  const [finalVideo, setFinalVideo] = useState("");

  const handlePreset = (preset: string) => {
    setQuickPreset(preset);
    
    // Reset to defaults first for consistent behavior
    setContentStyle("Podcast");
    setStyle("Cinematic Documentary");
    setVoice("Kore");
    setAspectRatio("16:9");
    setOmnichannel(false);
    setBgMusic(true);
    setAutoCaptions(true);
    setGenSeo(false);

    if (preset === "Tech News Short") {
      setContentStyle("Viral Video");
      setStyle("TikTok Viral");
      setAudioEngine("Gemini API");
      setVoice("Kore");
      setAspectRatio("9:16");
      setOmnichannel(true);
      setGenSeo(true);
    } else if (preset === "Scary Story") {
      setContentStyle("Story");
      setStyle("Cinematic Documentary");
      setVoice("Charon");
      setAspectRatio("9:16");
      setBgMusic(true);
    } else if (preset === "Motivation / Hustle") {
      setContentStyle("Viral Video");
      setStyle("Cyberpunk / Neon");
      setVoice("Fenrir");
      setAspectRatio("9:16");
      setBgMusic(true);
      setAutoCaptions(true);
      setOmnichannel(true);
    } else if (preset === "Historical Deep Dive") {
      setContentStyle("Documentary");
      setStyle("Cinematic Documentary");
      setVoice("Kore");
      setAspectRatio("16:9");
      setGenSeo(true);
    } else if (preset === "Product Promo") {
      setContentStyle("Product Ad");
      setStyle("TikTok Viral");
      setVoice("Kore");
      setAspectRatio("1:1");
      setOmnichannel(true);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("starting");
    setLogs(["Initializing Next-Gen Pipeline..."]);
    
    try {
      const payload = {
        topic, start_point: startStep, content_style: contentStyle,
        style, voice: audioEngine === "Gemini API" ? voice : elevenVoice, 
        audio_engine: audioEngine, video_engine: videoEngine, aspect_ratio: aspectRatio, bg_mode: bgMode,
        image_count: imageCount, video_count: videoCount,
        omnichannel, bg_music: bgMusic, auto_captions: autoCaptions,
        fact_check: factCheck, generate_thumbnail: genThumbnail,
        generate_seo: genSeo, generate_timestamps: genTimestamps,
        generate_snippets: genSnippets, script_length: scriptLength
      };

      const res = await apiFetch(`${API_BASE_URL}/api/generate/quick`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setJobId(data.job_id);
      setStatus("running");
    } catch {
      setStatus("error");
      setLogs(prev => [...prev, "Failed to connect to API."]);
    }
  };

  const handleCancel = async () => {
    if (jobId) {
      await apiFetch(`${API_BASE_URL}/api/generate/cancel/${jobId}`, { method: "POST" });
    }
    setStatus("idle");
    setLogs(prev => [...prev, "Job cancelled by user."]);
  };

  useEffect(() => {
    let ws: WebSocket;
    
    if (status === "running" && jobId) {
      ws = new WebSocket(`${WS_BASE_URL}/api/generate/ws/${jobId}`);
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          if (msg.type === "full_state") {
            const data = msg.data;
            if (typeof data.progress === "number") setProgress(data.progress <= 1.0 ? data.progress * 100 : data.progress);
            if (data.step) setCurrentStep(data.step);
            if (data.logs) setLogs(data.logs);
          } else if (msg.type === "update") {
            const data = msg.data;
            if (data.status === "completed") {
              setStatus("completed");
              setFinalVideo(data.result || "");
              ws.close();
            } else if (data.status === "failed") {
              setStatus("error");
              ws.close();
            }
            if (typeof data.progress === "number") setProgress(data.progress <= 1.0 ? data.progress * 100 : data.progress);
            if (data.step) setCurrentStep(data.step);
          } else if (msg.type === "log") {
            setLogs(prev => [...prev, msg.data]);
          }
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error", error);
      };
    }
    
    return () => {
      if (ws) ws.close();
    };
  }, [status, jobId]);

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Quick Creator</h1>
        <p className="text-zinc-400 mt-1">Configure and launch high-retention video generation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-5 space-y-6">
          <form onSubmit={handleGenerate} className="space-y-6">
            
            <div className="glass-card p-6 space-y-6">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-white/10 pb-3 mb-4">Core Setup</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Quick Presets</label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {[
                      { id: "Custom", icon: Settings },
                      { id: "Tech News Short", icon: Zap },
                      { id: "Scary Story", icon: Ghost },
                      { id: "Motivation / Hustle", icon: Rocket },
                      { id: "Historical Deep Dive", icon: Landmark },
                      { id: "Product Promo", icon: ShoppingBag },
                    ].map(preset => (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() => handlePreset(preset.id)}
                        className={`flex flex-col items-center justify-center gap-2 p-3 rounded-xl border transition-all ${
                          quickPreset === preset.id 
                            ? "bg-[#66fcf1]/10 border-[#66fcf1] text-[#66fcf1]" 
                            : "bg-black/50 border-white/5 text-zinc-400 hover:bg-white/5 hover:text-white"
                        }`}
                      >
                        <preset.icon className="h-5 w-5" />
                        <span className="text-[10px] font-bold uppercase tracking-wider text-center">{preset.id}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Start From Step</label>
                  <div className="relative">
                    <select value={startStep} onChange={e => setStartStep(e.target.value)} className="modern-select">
                      {PIPELINE_STEPS.map(step => <option key={step} value={step} className="bg-black">{step}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Video Topic</label>
                <input type="text" placeholder="e.g. History of Rome" value={topic} onChange={(e) => setTopic(e.target.value)} required disabled={status === "running"} className="modern-input" />
              </div>
            </div>

            <div className="glass-card p-6 space-y-6">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-white/10 pb-3 mb-4">Style & Persona</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Content Style</label>
                  <select value={contentStyle} onChange={e => setContentStyle(e.target.value)} className="modern-select">
                    {["Podcast", "Documentary", "Story", "Viral Video", "Product Ad"].map(s => <option key={s} value={s} className="bg-black">{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Visual Style</label>
                  <select value={style} onChange={e => setStyle(e.target.value)} className="modern-select">
                    {["Cinematic Documentary", "TikTok Viral", "Sci-Fi / Futuristic", "Cyberpunk / Neon"].map(s => <option key={s} value={s} className="bg-black">{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Audio Engine</label>
                  <TabSelect options={["Gemini API", "WaveSpeed AI"]} value={audioEngine} onChange={setAudioEngine} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Voice</label>
                  {audioEngine === "Gemini API" ? (
                    <TabSelect options={["Kore", "Fenrir", "Charon", "Aoede", "Puck"]} value={voice} onChange={setVoice} />
                  ) : (
                    <input type="text" value={elevenVoice} onChange={e => setElevenVoice(e.target.value)} placeholder="e.g. Brian, Rachel, or ID" className="modern-input" />
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Aspect Ratio</label>
                  <TabSelect options={["16:9", "9:16", "1:1"]} value={aspectRatio} onChange={setAspectRatio} />
                </div>
                {bgMode === "AI Video" && (
                  <div>
                    <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Video Engine</label>
                    <select value={videoEngine} onChange={e => setVideoEngine(e.target.value)} className="modern-select">
                      {["WaveSpeed AI", "Vertex AI (Veo)"].map(s => <option key={s} value={s} className="bg-black">{s}</option>)}
                    </select>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Background Mode</label>
                  <TabSelect options={["AI Video", "Stock Video (Pixabay)"]} value={bgMode} onChange={setBgMode} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Video Length</label>
                  <select value={scriptLength} onChange={e => setScriptLength(e.target.value)} className="modern-select">
                    {["Micro (< 1 minute)", "Short (~2 minutes)", "Medium (~5 minutes)", "Long (~10 minutes)"].map(s => <option key={s} value={s} className="bg-black">{s}</option>)}
                  </select>
                </div>
              </div>
            </div>

            <div className="glass-card p-6">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-white/10 pb-3 mb-6">Advanced Options</h3>
              <div className="grid grid-cols-2 gap-y-6 gap-x-4">
                <ToggleSwitch checked={omnichannel} onChange={setOmnichannel} label="Omnichannel" />
                <ToggleSwitch checked={bgMusic} onChange={setBgMusic} label="Background Music" />
                <ToggleSwitch checked={autoCaptions} onChange={setAutoCaptions} label="Auto Captions" />
                <ToggleSwitch checked={genSeo} onChange={setGenSeo} label="SEO Metadata" />
              </div>
            </div>

            <div className="pt-2">
              {status === "running" || status === "starting" ? (
                <button type="button" onClick={handleCancel} className="w-full py-3.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 font-bold rounded-xl hover:bg-rose-500/20 transition-all flex items-center justify-center gap-2">
                  <Square className="h-4 w-4 fill-current" /> Abort Generation
                </button>
              ) : (
                <button type="submit" className="btn-primary">
                  <Play className="h-4 w-4 fill-current" /> Generate Video
                </button>
              )}
            </div>
          </form>
        </div>

        <div className="lg:col-span-7 space-y-6">
          <div className="glass-card p-6 min-h-[500px] flex flex-col justify-between">
            <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3 flex items-center justify-between">
              Live Monitor
              <span className="text-zinc-500">
                Job: {jobId ? `${jobId.slice(0, 8)}...` : "Idle"}
              </span>
            </h2>

            {status === "idle" && (
              <div className="my-auto text-center space-y-4 py-12">
                <div className="w-full max-w-lg mx-auto aspect-video bg-black border border-white/10 rounded-xl flex items-center justify-center relative overflow-hidden group">
                  <div className="p-5 bg-white/5 rounded-full text-zinc-600 group-hover:text-white transition-colors border border-white/5">
                    <Film className="h-10 w-10" />
                  </div>
                </div>
                <p className="text-sm text-zinc-500 pt-4">Configure parameters and click <span className="text-white font-bold">Generate Video</span></p>
              </div>
            )}

            {(status === "starting" || status === "running") && (
              <div className="my-auto space-y-6 py-8">
                <div className="flex items-center gap-4">
                  <Loader2 className="h-7 w-7 text-white animate-spin" />
                  <div>
                    <h3 className="text-white font-bold text-base">{currentStep}</h3>
                    <p className="text-xs text-zinc-400 font-medium">Processing background task...</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-bold tracking-wider uppercase">
                    <span className="text-zinc-500">Progress</span>
                    <span className="text-white">{Math.round(progress)}%</span>
                  </div>
                  <div className="h-2 w-full bg-black rounded-full overflow-hidden border border-white/10">
                    <div className="h-full bg-white transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>

                <div className="mt-4 bg-black border border-white/10 rounded-xl p-4 h-48 overflow-y-auto font-mono text-xs text-zinc-400 space-y-1.5 shadow-inner">
                  {logs.length === 0 ? <div className="text-zinc-600 italic">Waiting for logs...</div> : logs.map((log, idx) => <div key={idx} className="break-words leading-relaxed">{log}</div>)}
                </div>
              </div>
            )}

            {status === "completed" && (
              <div className="my-auto space-y-4 py-4 text-center">
                <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto" />
                <h3 className="text-xl font-bold text-white">Video Generated Successfully!</h3>
                {finalVideo && (
                  <div className="space-y-4 max-w-xl mx-auto">
                    <div className="aspect-video bg-black rounded-xl overflow-hidden border border-white/15">
                      <video src={getMediaUrl(finalVideo)} controls autoPlay className="w-full h-full object-contain" />
                    </div>
                    <a
                      href={getMediaUrl(finalVideo)}
                      download
                      className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-black font-bold rounded-xl text-xs transition-all"
                    >
                      <Download className="h-4 w-4" /> Download Master Video
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}