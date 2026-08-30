"use client";

import { useState, useEffect } from "react";
import { Play, Loader2, Maximize, AlertCircle, StopCircle, LogIn, SlidersHorizontal } from "lucide-react";

export default function VideoFXFlowPage() {
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [browserFrame, setBrowserFrame] = useState<string | null>(null);
  const [videoResult, setVideoResult] = useState<string | null>(null);
  const [style, setStyle] = useState("Cinematic");
  const [aspectRatio, setAspectRatio] = useState("16:9");

  useEffect(() => {
    let ws: WebSocket;
    if (jobId && status === "running") {
      ws = new WebSocket(`ws://localhost:8008/api/videofx/ws/${jobId}`);
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "status") {
            const data = msg.data;
            if (data.status === "completed") {
              setStatus("completed");
              if (data.result) setVideoResult(data.result);
              ws.close();
            } else if (data.status === "failed") {
              setStatus("error");
              setLogs(prev => [...prev, `Error: ${data.error}`]);
              ws.close();
            }
          } else if (msg.type === "log") {
            setLogs(prev => [...prev, msg.data]);
          } else if (msg.type === "browser_frame") {
            setBrowserFrame(msg.data);
          }
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };
    }
    
    return () => {
      if (ws) ws.close();
    };
  }, [status, jobId]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    
    setStatus("running");
    setLogs(["Starting VideoFX automation..."]);
    setBrowserFrame(null);
    setVideoResult(null);
    
    const finalPrompt = `${prompt}, ${style} style, ${aspectRatio === "16:9" ? "horizontal 16:9" : aspectRatio === "9:16" ? "vertical 9:16" : "square 1:1"} aspect ratio`;
    
    try {
      const res = await fetch("http://localhost:8008/api/videofx/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: finalPrompt })
      });
      const data = await res.json();
      setJobId(data.job_id);
    } catch (err) {
      setStatus("error");
      setLogs(prev => [...prev, "Failed to connect to API."]);
    }
  };

  const handleStop = async () => {
    if (!jobId) return;
    try {
      await fetch(`http://localhost:8008/api/videofx/job/${jobId}`, { method: "DELETE" });
      setStatus("error");
      setLogs(prev => [...prev, "Generation cancelled by user."]);
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogin = async () => {
    try {
      await fetch("http://localhost:8008/api/videofx/login", { method: "POST" });
      alert("A browser window will open shortly on your computer. Please log in to your Google Account there. Your session will be saved forever, so you only need to do this once!");
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">VideoFX Flow</h1>
          <p className="text-zinc-400 mt-1">Generate high-quality video clips using Google VideoFX browser automation.</p>
        </div>
        <button onClick={handleLogin} className="modern-button bg-zinc-800/50 hover:bg-zinc-800 border-zinc-700/50 text-xs px-4 py-2 flex items-center gap-2 text-zinc-300">
          <LogIn className="h-4 w-4" /> Connect Google Account
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-6">
          <form onSubmit={handleGenerate} className="glass-card p-6 space-y-6">
            <div>
              <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">Video Prompt</label>
              <textarea
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                placeholder="Describe the video you want to generate in detail..."
                className="modern-textarea h-40"
                required
                disabled={status === "running"}
              />
            </div>
            
            <div className="space-y-4 pt-2 border-t border-white/5">
              <div className="flex items-center gap-2 text-zinc-400">
                <SlidersHorizontal className="h-4 w-4" />
                <span className="text-xs font-bold uppercase tracking-widest">Advanced Options</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">Visual Style</label>
                  <select value={style} onChange={e => setStyle(e.target.value)} disabled={status === "running"} className="modern-select text-sm py-2">
                    {["Cinematic", "Cyberpunk", "3D Render", "Anime", "Photorealistic", "Watercolor", "Claymation"].map(s => (
                      <option key={s} value={s} className="bg-black">{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 mb-1.5 uppercase tracking-wider">Aspect Ratio</label>
                  <select value={aspectRatio} onChange={e => setAspectRatio(e.target.value)} disabled={status === "running"} className="modern-select text-sm py-2">
                    <option value="16:9" className="bg-black">16:9 (Horizontal)</option>
                    <option value="9:16" className="bg-black">9:16 (Vertical)</option>
                    <option value="1:1" className="bg-black">1:1 (Square)</option>
                  </select>
                </div>
              </div>
            </div>
            
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={status === "running"}
                className="modern-button flex-1 flex items-center justify-center gap-2"
              >
                {status === "running" ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> GENERATING...</>
                ) : (
                  <><Play className="h-4 w-4" /> GENERATE VIDEO</>
                )}
              </button>
              
              {status === "running" && (
                <button
                  type="button"
                  onClick={handleStop}
                  className="modern-button !bg-red-500/20 !border-red-500/50 !text-red-400 hover:!bg-red-500/30 px-6"
                  title="Stop Generation"
                >
                  <StopCircle className="h-5 w-5" />
                </button>
              )}
            </div>
            
            {status === "error" && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex gap-3 text-red-400 text-sm">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <p>Generation failed. Please check the logs or ensure your Google account is logged in.</p>
              </div>
            )}
          </form>

          {/* Logs */}
          <div className="glass-card p-4">
            <h3 className="text-xs font-bold text-zinc-500 mb-3 uppercase tracking-wider border-b border-white/5 pb-2">Automation Logs</h3>
            <div className="bg-black/50 rounded-lg p-3 font-mono text-[10px] text-zinc-400 h-48 overflow-y-auto space-y-1">
              {logs.length === 0 && <div className="text-zinc-600">Waiting to start...</div>}
              {logs.map((log, i) => (
                <div key={i} className="border-b border-white/5 pb-1 mb-1 last:border-0 last:pb-0 last:mb-0">
                  <span className="text-[#66fcf1] opacity-50 mr-2">{">"}</span>
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-8">
          <div className="glass-card p-2 min-h-[500px] flex items-center justify-center relative overflow-hidden group">
            {status === "idle" && !videoResult && (
              <div className="text-zinc-600 flex flex-col items-center gap-3">
                <Maximize className="h-10 w-10 opacity-20" />
                <p className="text-sm font-medium tracking-wide">ENTER A PROMPT TO START</p>
              </div>
            )}

            {status === "running" && !browserFrame && (
              <div className="text-[#66fcf1] flex flex-col items-center gap-4">
                <Loader2 className="h-8 w-8 animate-spin opacity-50" />
                <p className="text-xs font-bold tracking-widest uppercase animate-pulse">Launching Automation Browser...</p>
              </div>
            )}

            {status === "running" && browserFrame && (
              <div className="w-full h-full relative flex items-center justify-center bg-black rounded-lg overflow-hidden">
                <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-black/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-red-500/30">
                  <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-[10px] font-bold text-red-400 tracking-widest">LIVE AUTOMATION</span>
                </div>
                <img 
                  src={`data:image/jpeg;base64,${browserFrame}`} 
                  alt="Live Browser Feed" 
                  className="w-full h-auto object-contain opacity-90 transition-opacity duration-300"
                />
              </div>
            )}
            
            {status === "completed" && videoResult && (
              <div className="w-full h-full relative flex items-center justify-center bg-black rounded-lg overflow-hidden">
                <video src={`http://localhost:8008/${videoResult}`} controls className="w-full h-full object-contain" autoPlay loop />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
