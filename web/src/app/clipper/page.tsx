"use client";

import { apiFetch } from "@/lib/api";

import { API_BASE_URL, WS_BASE_URL } from "@/lib/api";

import { useState, useEffect, useRef } from "react";
import { MonitorPlay, Scissors, Loader2, Download, Settings2, ScissorsSquare, Share2, CheckCircle2, Circle, Edit2, Upload } from "lucide-react";
import TimelineEditor, { type TimelineClipData } from "@/components/TimelineEditor";

interface GeneratedClip {
  title: string;
  path: string;
  seo_title?: string;
  seo_description?: string;
  seo_tags?: string;
}

export default function ClipperPage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("idle"); // idle, processing, selection, completed, failed
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [logMsg, setLogMsg] = useState("");
  const [logs, setLogs] = useState<{message: string, time: string}[]>([]);
  const [clips, setClips] = useState<GeneratedClip[]>([]);
  const [numClips, setNumClips] = useState(3);
  const [minDuration, setMinDuration] = useState(15);
  const [maxDuration, setMaxDuration] = useState(60);
  const [language, setLanguage] = useState("auto");
  const [failedClips, setFailedClips] = useState<{title: string, error: string}[]>([]);
  
  // Local File vs YouTube
  const [inputType, setInputType] = useState<"youtube" | "local">("youtube");
  const [file, setFile] = useState<File | null>(null);
  
  // Phase 1 UI state
  const [analyzedClips, setAnalyzedClips] = useState<TimelineClipData[]>([]);
  const [videoPath, setVideoPath] = useState("");
  const [selectedClipIndices, setSelectedClipIndices] = useState<Set<number>>(new Set());
  const [editingClipIndex, setEditingClipIndex] = useState<number | null>(null);
  
  // Phase 5 Publishing state
  const [publishModal, setPublishModal] = useState<{path: string, defaultTitle: string, defaultDesc: string, defaultTags: string} | null>(null);
  const [pubTitle, setPubTitle] = useState("");
  const [pubDesc, setPubDesc] = useState("");
  const [pubTags, setPubTags] = useState("");
  const [pubStatus, setPubStatus] = useState("idle");
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/api/generate/ws/${jobId}`);
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
              const res: { type: "selection"; clips: TimelineClipData[]; video_path: string } | { type: "finished"; clips: GeneratedClip[] } = JSON.parse(state.result);
              if (res.type === "selection") {
                setStatus("selection");
                setAnalyzedClips(res.clips);
                setVideoPath(res.video_path);
                // auto-select all by default
                setSelectedClipIndices(new Set(res.clips.map((_, i) => i)));
              } else if (res.type === "finished") {
                setStatus("completed");
                setClips(res.clips);
                setFailedClips(res.failed || []);
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
    if (inputType === "youtube") {
      if (!url || !url.includes("youtu")) {
        alert("Please enter a valid YouTube URL");
        return;
      }
    } else {
      if (!file) {
        alert("Please select a video file");
        return;
      }
    }
    
    setStatus("processing");
    setClips([]);
    setAnalyzedClips([]);
    setProgress(0);
    setLogMsg("Analyzing video...");
    setLogs([{ message: "Queuing analysis...", time: new Date().toLocaleTimeString() }]);
    
    try {
      let res;
      if (inputType === "youtube") {
        res = await apiFetch(`${API_BASE_URL}/api/clipper/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            url: url, 
            num_clips: numClips,
            min_duration: minDuration,
            max_duration: maxDuration,
            language: language
          })
        });
      } else {
        const formData = new FormData();
        formData.append("file", file!);
        formData.append("num_clips", numClips.toString());
        formData.append("min_duration", minDuration.toString());
        formData.append("max_duration", maxDuration.toString());
        formData.append("language", language);

        res = await apiFetch(`${API_BASE_URL}/api/clipper/analyze_local`, {
          method: "POST",
          body: formData
        });
      }
      
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to start analysis: " + (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)));
        setStatus("idle");
      } else {
        setJobId(data.job_id);
      }
    } catch {
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
      const res = await fetch(`${API_BASE_URL}/api/clipper/render`, {
      await apiFetch(`${API_BASE_URL}/api/clipper/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          job_id: jobId,
          video_path: videoPath,
          selected_clips: selected
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert("Render failed to start: " + (data.detail || res.statusText));
        setStatus("selection");
      }
    } catch {
    } catch {
      alert("API Error");
      setStatus("selection");
    }
  };

  const toggleSelection = (index: number) => {
    const next = new Set(selectedClipIndices);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelectedClipIndices(next);
  };

  const handleSaveTimeline = (adjustedClip: TimelineClipData) => {
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
      const res = await apiFetch(`${API_BASE_URL}/api/publish/youtube`, {
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
    } catch {
      alert("API Error");
    } finally {
      setPubStatus("idle");
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto animate-in fade-in duration-500 flex flex-col min-h-[calc(100vh-6rem)] pb-16">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Scissors className="h-8 w-8 text-[#66fcf1]" /> Magic AI Clipper 2.0
        </h1>
        <p className="text-zinc-400 mt-1">Advanced transcript analysis and auto-rendering for viral shorts.</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Side: Input & Progress */}
        <div className="lg:col-span-4 flex flex-col space-y-6">
          <div className="glass-card p-6">
            <form onSubmit={handleGenerate} className="space-y-6">
              <div className="flex bg-black/40 rounded-lg p-1 border border-white/10 mb-6">
                <button
                  type="button"
                  onClick={() => setInputType("youtube")}
                  className={`flex-1 py-2 text-sm font-bold rounded-md transition-all ${inputType === "youtube" ? "bg-[#66fcf1] text-black shadow-md" : "text-zinc-500 hover:text-white"}`}
                >
                  YouTube URL
                </button>
                <button
                  type="button"
                  onClick={() => setInputType("local")}
                  className={`flex-1 py-2 text-sm font-bold rounded-md transition-all ${inputType === "local" ? "bg-[#66fcf1] text-black shadow-md" : "text-zinc-500 hover:text-white"}`}
                >
                  Local Video
                </button>
              </div>

              {inputType === "youtube" ? (
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
              ) : (
                <div>
                  <label className="block text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <Upload className="h-4 w-4" /> Local Video File
                  </label>
                  <div className="border-2 border-dashed border-white/10 rounded-xl p-4 flex flex-col items-center justify-center bg-black/20 hover:bg-black/40 transition-colors">
                    <input 
                      type="file" 
                      accept="video/*"
                      onChange={e => e.target.files && setFile(e.target.files[0])}
                      className="text-sm text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-bold file:bg-[#66fcf1]/10 file:text-[#66fcf1] hover:file:bg-[#66fcf1]/20 cursor-pointer"
                      disabled={status === "processing"}
                    />
                  </div>
                  {file && <p className="text-[10px] text-zinc-500 mt-2 text-center truncate">{file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)</p>}
                </div>
              )}

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

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 mb-1 uppercase tracking-wider">Min sec</label>
                  <input type="number" min={5} max={maxDuration - 5} value={minDuration}
                    onChange={e => setMinDuration(Math.max(5, parseInt(e.target.value) || 5))}
                    className="modern-input" disabled={status === "processing"} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 mb-1 uppercase tracking-wider">Max sec</label>
                  <input type="number" min={minDuration + 5} max={180} value={maxDuration}
                    onChange={e => setMaxDuration(Math.min(180, parseInt(e.target.value) || 60))}
                    className="modern-input" disabled={status === "processing"} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 mb-1 uppercase tracking-wider">Language</label>
                  <select value={language} onChange={e => setLanguage(e.target.value)}
                    className="modern-input" disabled={status === "processing"}>
                    <option value="auto">Auto</option>
                    <option value="en">English</option>
                    <option value="ur">Urdu</option>
                    <option value="hi">Hindi</option>
                    <option value="ar">Arabic</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                  </select>
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
        <div className="lg:col-span-8 flex flex-col min-h-[550px]">
          <div className="glass-card p-6 flex-1 flex flex-col">
            
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
                        <div className="flex items-center justify-between mb-3 gap-3">
                          <div className="min-w-0">
                            <h3 className="font-bold text-white text-lg">{clip.title}</h3>
                            <div className="flex flex-wrap items-center gap-2 mt-1">
                              {clip.category && (
                                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded">{clip.category}</span>
                              )}
                              {clip.source === "heuristic" && (
                                <span className="text-[10px] font-bold uppercase tracking-wider text-orange-300 bg-orange-400/10 border border-orange-400/30 px-2 py-0.5 rounded">Signal-only (AI unavailable)</span>
                              )}
                              {clip.self_contained === false && (
                                <span className="text-[10px] font-bold uppercase tracking-wider text-red-300 bg-red-400/10 border border-red-400/30 px-2 py-0.5 rounded">Needs context</span>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2 shrink-0">
                            {clip.hook_score != null && (
                              <span className="bg-[#66fcf1]/10 border border-[#66fcf1]/30 text-[#66fcf1] px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
                                Hook: {clip.hook_score}
                              </span>
                            )}
                            {clip.payoff_score != null && (
                              <span className="bg-purple-500/10 border border-purple-500/30 text-purple-400 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
                                Payoff: {clip.payoff_score}
                              </span>
                            )}
                            <span className="bg-white/10 text-white px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider">
                              Score: {clip.score}/100
                            </span>
                          </div>
                        </div>
                        {clip.hook_text && (
                          <div className="mb-3">
                            <label className="block text-[10px] font-bold text-zinc-500 mb-1 uppercase tracking-wider">On-screen hook (first 3s)</label>
                            <input
                              type="text"
                              value={clip.hook_text}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => {
                                const next = [...analyzedClips];
                                next[i] = { ...next[i], hook_text: e.target.value };
                                setAnalyzedClips(next);
                              }}
                              className="w-full bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-[#66fcf1]"
                            />
                          </div>
                        )}
                        <p className="text-sm text-zinc-400 mb-3 border-l-2 border-[#66fcf1] pl-3 py-1 bg-white/5 rounded-r">
                          {clip.reason}
                          {clip.judge_note && <span className="block text-xs text-zinc-500 mt-1">Editor: {clip.judge_note}</span>}
                        </p>
                        {clip.score_breakdown && (
                          <div className="grid grid-cols-5 gap-2 mb-3">
                            {[
                              ["AI", clip.score_breakdown.llm],
                              ["Judge", clip.score_breakdown.judge],
                              ["Energy", clip.score_breakdown.multimodal],
                              ["Pace", clip.score_breakdown.speech],
                              ["Length", clip.score_breakdown.duration_fit],
                            ].map(([label, val]) => (
                              <div key={label as string} title={`${label}: ${val ?? "n/a"}`}>
                                <div className="flex justify-between text-[9px] font-bold text-zinc-500 uppercase"><span>{label}</span><span>{val != null ? Math.round(val as number) : "–"}</span></div>
                                <div className="h-1 bg-white/5 rounded mt-1 overflow-hidden">
                                  <div className="h-full bg-[#66fcf1]/70" style={{ width: `${val != null ? Math.min(100, val as number) : 0}%` }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 text-xs font-bold text-zinc-500">
                              <span>{Number(clip.start).toFixed(1)}s - {Number(clip.end).toFixed(1)}s</span>
                              <span>•</span>
                              <span>{Math.round(clip.end - clip.start)}s duration</span>
                              {clip.speech_metrics && (<><span>•</span><span>{clip.speech_metrics.wps} words/s</span></>)}
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
                {failedClips.length > 0 && (
                  <div className="mb-4 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-xs text-red-300">
                    {failedClips.length} clip(s) failed: {failedClips.map(f => `${f.title} (${f.error})`).join("; ")}
                  </div>
                )}
                <div className="flex-1 overflow-y-auto pr-2 pb-8">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {clips.map((clip, i) => (
                      <div key={i} className="flex flex-col gap-3 group">
                        <div className="aspect-[9/16] bg-black rounded-xl border border-white/10 overflow-hidden relative shadow-lg">
                          <video 
                            src={`${API_BASE_URL}/api/generate/media?path=${encodeURIComponent(clip.path.replace(/\\/g, '/'))}`} 
                            controls 
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="px-1">
                          <p className="text-sm font-bold text-white line-clamp-1" title={clip.title}>
                            {clip.title}
                          </p>
                          <div className="flex items-center gap-2 mt-3">
                            <a href={`${API_BASE_URL}/api/generate/media?path=${encodeURIComponent(clip.path.replace(/\\/g, '/'))}`} download className="flex-1 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg flex items-center justify-center gap-2 text-xs font-bold transition-all">
                              <Download className="h-4 w-4" /> Download
                            </a>
                            <button 
                              onClick={() => {
                                setPublishModal({
                                  path: clip.path, 
                                  defaultTitle: clip.seo_title || clip.title,
                                  defaultDesc: clip.seo_description || "",
                                  defaultTags: clip.seo_tags || ""
                                });
                                setPubTitle(clip.seo_title || clip.title);
                                setPubDesc(clip.seo_description || "");
                                setPubTags(clip.seo_tags || "");
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
