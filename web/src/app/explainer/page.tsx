"use client";

import { useState, useEffect, useRef } from "react";
import { Film, Upload, Loader2, Play, Download, Wand2, Settings2, Clapperboard } from "lucide-react";

export default function ExplainerModePage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [logMsg, setLogMsg] = useState("");
  const [logs, setLogs] = useState<{message: string, time: string}[]>([]);
  const [finalVideo, setFinalVideo] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  
  const STEPS = [
    "Initializing Engine",
    "Fetching Video",
    "Extracting Audio",
    "Transcribing Audio",
    "Generating Explainer Script",
    "Generating TTS and extracting video clips",
    "Merging final video"
  ];
  
  // Settings
  const [duration, setDuration] = useState("5 minutes");
  const [language, setLanguage] = useState("English");
  const [audioEngine, setAudioEngine] = useState("WaveSpeed AI (ElevenLabs)");
  const [voice, setVoice] = useState("Brian");
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const ws = new WebSocket(`ws://localhost:8008/api/generate/ws/${jobId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          setLogMsg(data.message);
          
          // Try to match current step
          const msg = data.message.toLowerCase();
          if (msg.includes("fetching video")) setActiveStep(1);
          else if (msg.includes("extracting audio")) setActiveStep(2);
          else if (msg.includes("transcribing")) setActiveStep(3);
          else if (msg.includes("generating explainer script")) setActiveStep(4);
          else if (msg.includes("generating tts")) setActiveStep(5);
          else if (msg.includes("merging")) setActiveStep(6);
          else if (msg.includes("complete")) setActiveStep(7);
          
          if (data.progress) setProgress(data.progress * 100);
          setLogs(prev => {
            if (prev.length > 0 && prev[prev.length - 1].message === data.message) return prev;
            return [...prev, { message: data.message, time: new Date().toLocaleTimeString() }];
          });
        } else if (data.type === "update" || data.type === "full_state") {
          const state = data.data || data;
          if (state.status === "completed") {
            setStatus("completed");
            if (state.result) setFinalVideo(state.result);
          } else if (state.status === "failed") {
            setStatus("failed");
            setLogMsg(`Error: ${state.error}`);
          }
        }
      } catch (e) {
        console.error("WS Parse Error", e);
      }
    };

    return () => {
      ws.close();
    };
  }, [jobId]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) {
      alert("Please enter a movie URL or local path");
      return;
    }
    
    setStatus("processing");
    setFinalVideo(null);
    setProgress(0);
    setLogMsg("Initializing Explainer Engine...");
    setLogs([{ message: "Starting Movie Explainer...", time: new Date().toLocaleTimeString() }]);
    
    try {
      const res = await fetch("http://localhost:8008/api/explainer/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          url: url,
          target_duration: duration,
          language: language,
          voice: voice,
          text_engine: "Gemini API",
          audio_engine: audioEngine === "Gemini API" ? "Gemini API" : "WaveSpeed AI"
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to start explainer: " + data.detail);
        setStatus("idle");
      } else {
        setJobId(data.job_id);
      }
    } catch (err) {
      alert("API Error");
      setStatus("idle");
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto animate-in fade-in duration-500 flex flex-col h-[calc(100vh-6rem)]">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Clapperboard className="h-8 w-8 text-[#fca311]" /> Movie Explainer
        </h1>
        <p className="text-zinc-400 mt-1">Upload a full movie and let the AI script, cut, and narrate an explainer video automatically.</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
        
        {/* Left Side: Input & Progress */}
        <div className="lg:col-span-5 flex flex-col space-y-6">
          <div className="glass-card p-6">
            <form onSubmit={handleGenerate} className="space-y-6">
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Upload className="h-4 w-4" /> Full Movie File Path or YouTube URL
                </label>
                <input 
                  type="text" 
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="C:\Movies\Batman.mp4 or https://..."
                  className="modern-input"
                  disabled={status === "processing"}
                />
              </div>

              <div className="space-y-3 pt-2">
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Settings2 className="h-4 w-4" /> Explainer Settings
                </label>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">Target Duration</label>
                    <select value={duration} onChange={e => setDuration(e.target.value)} disabled={status === "processing"} className="modern-select text-sm py-2">
                      <option value="2 minutes" className="bg-black">~ 2 Minutes</option>
                      <option value="5 minutes" className="bg-black">~ 5 Minutes</option>
                      <option value="10 minutes" className="bg-black">~ 10 Minutes</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">Language</label>
                    <select value={language} onChange={e => setLanguage(e.target.value)} disabled={status === "processing"} className="modern-select text-sm py-2">
                      <option value="English" className="bg-black">English</option>
                      <option value="Hindi" className="bg-black">Hindi</option>
                      <option value="Urdu" className="bg-black">Urdu</option>
                      <option value="Spanish" className="bg-black">Spanish</option>
                      <option value="French" className="bg-black">French</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">TTS Engine</label>
                    <select value={audioEngine} onChange={e => setAudioEngine(e.target.value)} disabled={status === "processing"} className="modern-select text-sm py-2">
                      <option value="WaveSpeed AI (ElevenLabs)" className="bg-black">ElevenLabs (Pro)</option>
                      <option value="Gemini API" className="bg-black">Gemini (Fast)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">Voice Actor</label>
                    {audioEngine === "Gemini API" ? (
                      <select value={voice} onChange={e => setVoice(e.target.value)} disabled={status === "processing"} className="modern-select text-sm py-2">
                        <option value="Kore" className="bg-black">Kore (Neutral)</option>
                        <option value="Aoede" className="bg-black">Aoede (Warm)</option>
                        <option value="Fenrir" className="bg-black">Fenrir (Deep Male)</option>
                        <option value="Puck" className="bg-black">Puck (Energetic)</option>
                      </select>
                    ) : (
                      <select value={voice} onChange={e => setVoice(e.target.value)} disabled={status === "processing"} className="modern-select text-sm py-2">
                        <option value="Brian" className="bg-black">Brian (Deep)</option>
                        <option value="Drew" className="bg-black">Drew (News)</option>
                        <option value="Rachel" className="bg-black">Rachel (Calm)</option>
                        <option value="Callum" className="bg-black">Callum (Epic)</option>
                      </select>
                    )}
                  </div>
                </div>
              </div>

              <div className="pt-4">
                {status === "processing" ? (
                  <button type="button" disabled className="w-full py-4 bg-white/20 text-white font-bold rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                    <Loader2 className="h-5 w-5 animate-spin" /> Generating Explainer...
                  </button>
                ) : (
                  <button type="submit" className="w-full py-4 bg-[#fca311] text-black font-bold rounded-xl hover:bg-[#ffb703] transition-all shadow-[0_0_20px_rgba(252,163,17,0.3)] flex items-center justify-center gap-2">
                    <Wand2 className="h-5 w-5" /> Generate Movie Explainer
                  </button>
                )}
              </div>
            </form>
          </div>

          {status !== "idle" && (
            <div className="glass-card p-6 flex flex-col gap-4 flex-1">
              <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3">
                Live Timeline
              </h2>
              <div className="flex-1 flex flex-col justify-center gap-6">
                <div className="text-center">
                  <p className="text-4xl font-black text-white">{Math.round(progress)}%</p>
                  <p className="text-sm text-[#fca311] mt-2 font-medium">{logMsg}</p>
                </div>
                
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-[#fca311] to-[#ffb703] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                  {STEPS.map((step, idx) => (
                    <div key={step} className={`p-3 rounded-xl border flex items-center gap-3 transition-all ${
                      idx < activeStep ? 'bg-[#fca311]/10 border-[#fca311]/30 text-white' : 
                      idx === activeStep ? 'bg-[#fca311]/20 border-[#fca311] text-[#fca311] animate-pulse' : 
                      'bg-black/40 border-white/5 text-zinc-600'
                    }`}>
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        idx < activeStep ? 'bg-[#fca311] text-black' : 
                        idx === activeStep ? 'bg-[#fca311] text-black' : 
                        'bg-white/10 text-zinc-500'
                      }`}>
                        {idx < activeStep ? '✓' : idx + 1}
                      </div>
                      <span className="text-sm font-medium">{step}</span>
                    </div>
                  ))}
                </div>
                
                <div className="mt-2 flex-1 bg-black/40 rounded-xl p-4 overflow-y-auto border border-white/5 space-y-2 max-h-[100px]">
                  {logs.map((log, i) => (
                    <div key={i} className="flex gap-3 text-xs font-mono text-zinc-400">
                      <span className="text-zinc-600">[{log.time}]</span>
                      <span className={i === logs.length - 1 ? "text-[#fca311]" : ""}>{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Results */}
        <div className="lg:col-span-7 flex flex-col">
          <div className="glass-card p-6 flex-1 flex flex-col overflow-hidden">
            <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3 mb-6 flex justify-between items-center">
              <span>Final Explainer Video</span>
            </h2>
            
            <div className="flex-1 flex flex-col items-center justify-center h-full">
              {!finalVideo ? (
                <div className="text-zinc-500 flex-col gap-4 flex items-center">
                  <Clapperboard className="h-12 w-12 opacity-20" />
                  <p>Awaiting raw movie footage...</p>
                </div>
              ) : (
                <div className="w-full max-w-2xl mx-auto flex flex-col gap-6">
                  <div className="aspect-video bg-black rounded-xl border border-white/10 overflow-hidden relative shadow-2xl">
                    <video 
                      src={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(finalVideo.replace(/\\/g, '/'))}`} 
                      controls 
                      className="w-full h-full object-cover"
                    />
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <a href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(finalVideo.replace(/\\/g, '/'))}`} download className="flex-1 py-4 bg-[#fca311] hover:bg-[#ffb703] text-black rounded-xl flex items-center justify-center gap-2 text-sm font-bold transition-all shadow-[0_0_15px_rgba(252,163,17,0.2)]">
                      <Download className="h-5 w-5" /> Download Final Master
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
