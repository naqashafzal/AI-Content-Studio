"use client";

import { useState, useEffect, useRef } from "react";
import { Film, Upload, Loader2, Play, Download, Wand2, Settings2, FileAudio } from "lucide-react";

export default function DirectorModePage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [logMsg, setLogMsg] = useState("");
  const [logs, setLogs] = useState<{message: string, time: string}[]>([]);
  const [finalVideo, setFinalVideo] = useState<string | null>(null);
  
  // Settings
  const [removeSilence, setRemoveSilence] = useState(true);
  const [addPunchIns, setAddPunchIns] = useState(true);
  const [addSfx, setAddSfx] = useState(true);
  
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
          setProgress(data.progress * 100);
          setLogs(prev => {
            if (prev.length > 0 && prev[prev.length - 1].message === data.message) return prev;
            return [...prev, { message: data.message, time: new Date().toLocaleTimeString() }];
          });
        } else if (data.type === "update" || data.type === "full_state") {
          const state = data.data || data;
          if (state.status === "completed") {
            setStatus("completed");
            if (state.result) {
              setFinalVideo(state.result);
            }
          } else if (state.status === "failed") {
            setStatus("failed");
            setLogMsg(`Error: ${state.error}`);
          }
          if (data.type === "full_state") {
            setProgress(state.progress * 100);
            setLogMsg(state.step);
            if (state.status === "completed" && state.result) {
               setFinalVideo(state.result);
            }
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
      alert("Please enter a video URL");
      return;
    }
    
    setStatus("processing");
    setFinalVideo(null);
    setProgress(0);
    setLogMsg("Initializing Director Engine...");
    setLogs([{ message: "Starting Director Mode...", time: new Date().toLocaleTimeString() }]);
    
    try {
      const res = await fetch("http://localhost:8008/api/director/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          url: url,
          remove_silence: removeSilence,
          add_punch_ins: addPunchIns,
          add_sfx: addSfx
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to start director: " + data.detail);
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
          <Film className="h-8 w-8 text-[#66fcf1]" /> Director Mode
        </h1>
        <p className="text-zinc-400 mt-1">Autonomous AI video editor. Upload raw footage and let the AI edit it like MrBeast.</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
        
        {/* Left Side: Input & Progress */}
        <div className="lg:col-span-5 flex flex-col space-y-6">
          <div className="glass-card p-6">
            <form onSubmit={handleGenerate} className="space-y-6">
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Upload className="h-4 w-4" /> Raw Video URL (YouTube or Direct Link)
                </label>
                <input 
                  type="text" 
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://..."
                  className="modern-input"
                  disabled={status === "processing"}
                />
              </div>

              <div className="space-y-3 pt-2">
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Settings2 className="h-4 w-4" /> Editing Directives
                </label>
                
                <label className="flex items-center gap-3 p-3 bg-black/40 border border-white/5 rounded-xl cursor-pointer hover:bg-white/5 transition-all">
                  <input type="checkbox" checked={removeSilence} onChange={e => setRemoveSilence(e.target.checked)} className="w-4 h-4 accent-[#66fcf1]" disabled={status === "processing"} />
                  <div className="flex-1">
                    <p className="text-sm font-bold text-white">Silence & Umm Removal</p>
                    <p className="text-xs text-zinc-500">Automatically trims dead air for hyper-fast pacing.</p>
                  </div>
                  <FileAudio className="h-5 w-5 text-zinc-600" />
                </label>

                <label className="flex items-center gap-3 p-3 bg-black/40 border border-white/5 rounded-xl cursor-pointer hover:bg-white/5 transition-all">
                  <input type="checkbox" checked={addPunchIns} onChange={e => setAddPunchIns(e.target.checked)} className="w-4 h-4 accent-[#66fcf1]" disabled={status === "processing"} />
                  <div className="flex-1">
                    <p className="text-sm font-bold text-white">Dynamic Punch-ins</p>
                    <p className="text-xs text-zinc-500">Auto-zooms camera on high-impact sentences.</p>
                  </div>
                  <Film className="h-5 w-5 text-zinc-600" />
                </label>

                <label className="flex items-center gap-3 p-3 bg-black/40 border border-white/5 rounded-xl cursor-pointer hover:bg-white/5 transition-all">
                  <input type="checkbox" checked={addSfx} onChange={e => setAddSfx(e.target.checked)} className="w-4 h-4 accent-[#66fcf1]" disabled={status === "processing"} />
                  <div className="flex-1">
                    <p className="text-sm font-bold text-white">Keyword Sound Effects</p>
                    <p className="text-xs text-zinc-500">Injects swoosh and pop sounds to emphasize text.</p>
                  </div>
                  <Wand2 className="h-5 w-5 text-zinc-600" />
                </label>
              </div>

              <div className="pt-4">
                {status === "processing" ? (
                  <button type="button" disabled className="w-full py-4 bg-white/20 text-white font-bold rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                    <Loader2 className="h-5 w-5 animate-spin" /> Auto-Editing Video...
                  </button>
                ) : (
                  <button type="submit" className="w-full py-4 bg-[#66fcf1] text-black font-bold rounded-xl hover:bg-[#45f3e5] transition-all shadow-[0_0_20px_rgba(102,252,241,0.3)] flex items-center justify-center gap-2">
                    <Wand2 className="h-5 w-5" /> Start Director Mode
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
                  <p className="text-sm text-[#66fcf1] mt-2 font-medium">{logMsg}</p>
                </div>
                
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-[#66fcf1] to-[#45f3e5] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                
                <div className="mt-4 flex-1 bg-black/40 rounded-xl p-4 overflow-y-auto border border-white/5 space-y-2 max-h-[150px]">
                  {logs.map((log, i) => (
                    <div key={i} className="flex gap-3 text-xs font-mono text-zinc-400">
                      <span className="text-zinc-600">[{log.time}]</span>
                      <span className={i === logs.length - 1 ? "text-[#66fcf1]" : ""}>{log.message}</span>
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
              <span>Final Edited Video</span>
            </h2>
            
            <div className="flex-1 flex flex-col items-center justify-center h-full">
              {!finalVideo ? (
                <div className="text-zinc-500 flex-col gap-4 flex items-center">
                  <Film className="h-12 w-12 opacity-20" />
                  <p>Awaiting raw footage...</p>
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
                    <a href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(finalVideo.replace(/\\/g, '/'))}`} download className="flex-1 py-4 bg-[#66fcf1] hover:bg-[#45f3e5] text-black rounded-xl flex items-center justify-center gap-2 text-sm font-bold transition-all shadow-[0_0_15px_rgba(102,252,241,0.2)]">
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
