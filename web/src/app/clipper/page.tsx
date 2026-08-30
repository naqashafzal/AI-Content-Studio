"use client";

import { useState, useEffect, useRef } from "react";
import { MonitorPlay, Scissors, Loader2, Play, Download, Settings2, ScissorsSquare, Share2, CheckCircle2, Circle, Edit2 } from "lucide-react";
import TimelineEditor from "@/components/TimelineEditor";

export default function ClipperPage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("idle"); // idle, processing, selection, completed, failed
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [logMsg, setLogMsg] = useState("");
  const [logs, setLogs] = useState<{message: string, time: string}[]>([]);
  const [clips, setClips] = useState<{title: string, path: string}[]>([]);
  const [numClips, setNumClips] = useState(3);
  
  // Phase 1 UI state
  const [analyzedClips, setAnalyzedClips] = useState<any[]>([]);
  const [videoPath, setVideoPath] = useState("");
  const [selectedClipIndices, setSelectedClipIndices] = useState<Set<number>>(new Set());
  const [editingClipIndex, setEditingClipIndex] = useState<number | null>(null);
  
  // Phase 5 Publishing state
  const [publishModal, setPublishModal] = useState<{path: string, defaultTitle: string} | null>(null);
  const [pubTitle, setPubTitle] = useState("");
  const [pubDesc, setPubDesc] = useState("#Shorts #Viral");
  const [pubTags, setPubTags] = useState("");
  const [pubStatus, setPubStatus] = useState("idle");
  
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
          const state = data.data || data; // handle both structures
          if (state.status === "failed") {
            setStatus("failed");
            setLogMsg(`Error: ${state.error}`);
            return;
          }
          
          if (data.type === "full_state") {
            setProgress(state.progress * 100);
            setLogMsg(state.step);
          }
          
          if (state.result) {
            try {
              const res = JSON.parse(state.result);
              if (res.type === "selection") {
                setStatus("selection");
                setAnalyzedClips(res.clips);
                setVideoPath(res.video_path);
                // auto-select all by default
                setSelectedClipIndices(new Set(res.clips.map((_: any, i: number) => i)));
              } else if (res.type === "finished") {
                setStatus("completed");
                setClips(res.clips);
              }
            } catch (e) {
              console.error("Failed to parse clips result", e);
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
    if (!url || !url.includes("youtu")) {
      alert("Please enter a valid YouTube URL");
      return;
    }
    
    setStatus("processing");
    setClips([]);
    setAnalyzedClips([]);
    setProgress(0);
    setLogMsg("Analyzing video...");
    setLogs([{ message: "Queuing analysis...", time: new Date().toLocaleTimeString() }]);
    
    try {
      const res = await fetch("http://localhost:8008/api/clipper/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          url: url, 
          num_clips: numClips
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to start analysis: " + data.detail);
        setStatus("idle");
      } else {
        setJobId(data.job_id);
      }
    } catch (err) {
      alert("API Error");
      setStatus("idle");
    }
  };

  const handleRenderSelected = async () => {
    if (selectedClipIndices.size === 0) return;
    setStatus("processing");
    setProgress(0);
    setLogMsg("Starting render engine...");
    
    const selected = analyzedClips.filter((_, i) => selectedClipIndices.has(i));
    
    try {
      await fetch("http://localhost:8008/api/clipper/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          job_id: jobId,
          video_path: videoPath,
          selected_clips: selected
        })
      });
    } catch (err) {
      alert("API Error");
    }
  };

  const toggleSelection = (index: number) => {
    const next = new Set(selectedClipIndices);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelectedClipIndices(next);
  };

  const handleSaveTimeline = (adjustedClip: any) => {
    if (editingClipIndex === null) return;
    const newAnalyzed = [...analyzedClips];
    newAnalyzed[editingClipIndex] = adjustedClip;
    setAnalyzedClips(newAnalyzed);
    setEditingClipIndex(null);
  };

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!publishModal) return;
    
    setPubStatus("publishing");
    try {
      const res = await fetch("http://localhost:8008/api/publish/youtube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          video_path: publishModal.path,
          title: pubTitle,
          description: pubDesc,
          tags: pubTags,
          privacy_status: "private" // default private so user can review on YT
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to publish: " + data.detail);
      } else {
        alert("Successfully uploaded to YouTube!");
        setPublishModal(null);
      }
    } catch (err) {
      alert("API Error");
    } finally {
      setPubStatus("idle");
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto animate-in fade-in duration-500 flex flex-col h-[calc(100vh-6rem)]">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Scissors className="h-8 w-8 text-[#66fcf1]" /> Magic AI Clipper 2.0
        </h1>
        <p className="text-zinc-400 mt-1">Advanced transcript analysis and auto-rendering for viral shorts.</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
        
        {/* Left Side: Input & Progress */}
        <div className="lg:col-span-4 flex flex-col space-y-6">
          <div className="glass-card p-6">
            <form onSubmit={handleGenerate} className="space-y-6">
              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <MonitorPlay className="h-4 w-4" /> YouTube Video URL
                </label>
                <input 
                  type="text" 
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="modern-input"
                  disabled={status === "processing"}
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center justify-between">
                  <span className="flex items-center gap-2"><Settings2 className="h-4 w-4" /> Number of Clips</span>
                  <span className="text-[#66fcf1]">{numClips} Clips</span>
                </label>
                <input 
                  type="range" 
                  min="1" 
                  max="10" 
                  value={numClips}
                  onChange={e => setNumClips(parseInt(e.target.value))}
                  className="w-full accent-[#66fcf1] h-2 bg-white/10 rounded-lg appearance-none cursor-pointer"
                  disabled={status === "processing"}
                />
                <div className="flex justify-between text-[10px] text-zinc-600 mt-2 font-bold px-1">
                  <span>1</span>
                  <span>5</span>
                  <span>10</span>
                </div>
              </div>

              <div className="pt-2">
                {status === "processing" ? (
                  <button type="button" disabled className="w-full py-4 bg-white/20 text-white font-bold rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                    <Loader2 className="h-5 w-5 animate-spin" /> Processing...
                  </button>
                ) : (
                  <button type="submit" className="w-full py-4 bg-[#66fcf1] text-black font-bold rounded-xl hover:bg-[#45f3e5] transition-all shadow-[0_0_20px_rgba(102,252,241,0.3)] flex items-center justify-center gap-2">
                    <ScissorsSquare className="h-5 w-5" /> Analyze Video
                  </button>
                )}
              </div>
            </form>
          </div>

          {status !== "idle" && status !== "selection" && (
            <div className="glass-card p-6 flex flex-col gap-4 flex-1">
              <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3">
                Live Progress
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
        <div className="lg:col-span-8 flex flex-col">
          <div className="glass-card p-6 flex-1 flex flex-col overflow-hidden">
            
            {status === "selection" ? (
              <>
                <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3 mb-6 flex justify-between items-center">
                  <span>Viral Analysis Complete</span>
                  <span className="text-[#66fcf1]">{selectedClipIndices.size} selected</span>
                </h2>
                <div className="flex-1 overflow-y-auto pr-2 space-y-4 pb-8">
                  {editingClipIndex !== null ? (
                     <TimelineEditor 
                        clip={analyzedClips[editingClipIndex]} 
                        onSave={handleSaveTimeline}
                        onCancel={() => setEditingClipIndex(null)}
                     />
                  ) : (
                  analyzedClips.map((clip, i) => (
                    <div 
                      key={i} 
                      onClick={() => toggleSelection(i)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer flex gap-4 ${selectedClipIndices.has(i) ? 'bg-[#66fcf1]/10 border-[#66fcf1]' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}
                    >
                      <div className="pt-1">
                        {selectedClipIndices.has(i) ? <CheckCircle2 className="h-6 w-6 text-[#66fcf1]" /> : <Circle className="h-6 w-6 text-zinc-500" />}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-bold text-white text-lg">{clip.title}</h3>
                          <span className="bg-[#66fcf1]/20 text-[#66fcf1] px-3 py-1 rounded-full text-xs font-bold whitespace-nowrap">
                            Score: {clip.score}/100
                          </span>
                        </div>
                        <p className="text-sm text-zinc-400 mb-2">{clip.reason}</p>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 text-xs font-bold text-zinc-500">
                              <span>{clip.start}s - {clip.end}s</span>
                              <span>•</span>
                              <span>{Math.round(clip.end - clip.start)}s duration</span>
                            </div>
                            <button 
                               onClick={(e) => { e.stopPropagation(); setEditingClipIndex(i); }}
                               className="px-3 py-1 bg-white/10 hover:bg-white/20 text-white rounded flex items-center gap-2 text-[10px] font-bold transition-colors"
                            >
                               <Edit2 className="h-3 w-3" /> Adjust Cuts
                            </button>
                        </div>
                      </div>
                    </div>
                  ))
                  )}
                </div>
                <div className="pt-6 border-t border-white/10 mt-auto">
                  <button 
                    onClick={handleRenderSelected}
                    disabled={selectedClipIndices.size === 0}
                    className="w-full py-4 bg-[#66fcf1] text-black font-bold rounded-xl hover:bg-[#45f3e5] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Render {selectedClipIndices.size} Selected Clips
                  </button>
                </div>
              </>
            ) : status === "completed" || clips.length > 0 ? (
              <>
                <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3 mb-6 flex justify-between items-center">
                  <span>Generated Shorts ({clips.length})</span>
                </h2>
                <div className="flex-1 overflow-y-auto pr-2 pb-8">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {clips.map((clip, i) => (
                      <div key={i} className="flex flex-col gap-3 group">
                        <div className="aspect-[9/16] bg-black rounded-xl border border-white/10 overflow-hidden relative shadow-lg">
                          <video 
                            src={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(clip.path.replace(/\\/g, '/'))}`} 
                            controls 
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="px-1">
                          <p className="text-sm font-bold text-white line-clamp-1" title={clip.title}>
                            {clip.title}
                          </p>
                          <div className="flex items-center gap-2 mt-3">
                            <a href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(clip.path.replace(/\\/g, '/'))}`} download className="flex-1 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg flex items-center justify-center gap-2 text-xs font-bold transition-all">
                              <Download className="h-4 w-4" /> Download
                            </a>
                            <button 
                              onClick={() => {
                                setPublishModal({path: clip.path, defaultTitle: clip.title});
                                setPubTitle(clip.title);
                              }}
                              className="flex-1 py-2 bg-[#66fcf1] hover:bg-[#45f3e5] text-black rounded-lg flex items-center justify-center gap-2 text-xs font-bold transition-all"
                            >
                              <Share2 className="h-4 w-4" /> Publish
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-zinc-500 flex-col gap-4 min-h-[300px]">
                <Scissors className="h-12 w-12 opacity-20" />
                <p>Awaiting YouTube input...</p>
              </div>
            )}
            
          </div>
        </div>
      </div>
      
      {/* Publish Modal */}
      {publishModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-[#111111] border border-white/10 p-6 rounded-xl w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Share2 className="h-5 w-5 text-[#66fcf1]" /> Publish to YouTube
            </h2>
            <form onSubmit={handlePublish} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-400 mb-1">Title</label>
                <input type="text" value={pubTitle} onChange={e => setPubTitle(e.target.value)} className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#66fcf1]" required />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-400 mb-1">Description</label>
                <textarea value={pubDesc} onChange={e => setPubDesc(e.target.value)} className="w-full h-24 bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#66fcf1]" />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-400 mb-1">Tags (comma separated)</label>
                <input type="text" value={pubTags} onChange={e => setPubTags(e.target.value)} placeholder="shorts, viral, podcast" className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#66fcf1]" />
              </div>
              <p className="text-xs text-zinc-500 mb-4">* Video will be uploaded as Private so you can review it on YouTube before making it Public.</p>
              
              <div className="flex gap-3 justify-end">
                <button type="button" onClick={() => setPublishModal(null)} className="px-4 py-2 text-sm font-bold text-white bg-white/10 rounded-lg hover:bg-white/20">Cancel</button>
                <button type="submit" disabled={pubStatus === "publishing"} className="px-4 py-2 text-sm font-bold text-black bg-[#66fcf1] rounded-lg hover:bg-[#45f3e5] flex items-center gap-2">
                  {pubStatus === "publishing" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upload to YouTube"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
