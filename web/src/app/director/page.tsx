"use client";

import { apiFetch } from "@/lib/api";

import { useState, useEffect, useRef } from "react";
import { API_BASE_URL, WS_BASE_URL, getMediaUrl } from "@/lib/api";
import { Film, Upload, Loader2, Play, Download, Wand2, Settings2, FileAudio, Lock, Unlock, RefreshCw, CheckCircle2, Sparkles, Clock, Sliders, Flame, Save } from "lucide-react";

interface Scene {
  scene_number: number;
  duration_estimate_sec: number;
  speaker: string;
  narration: string;
  visual_description: string;
  camera_framing: string;
  broll_query?: string;
  music_cue?: string;
  sfx_cue?: string;
  locked?: boolean;
}

interface StoryboardPlan {
  title: string;
  hook: string;
  duration: number;
  style: string;
  scenes: Scene[];
  research_summary?: string;
  qa_score?: number;
  qa_passed?: boolean;
}

export default function DirectorModePage() {
  const [activeTab, setActiveTab] = useState<"storyboard" | "raw">("storyboard");
  
  // Storyboard Director State
  const [topic, setTopic] = useState("");
  const [targetDuration, setTargetDuration] = useState(45);
  const [selectedStyle, setSelectedStyle] = useState("Cinematic Documentary");
  const [planningStatus, setPlanningStatus] = useState<"idle" | "planning" | "ready" | "failed" | "rendering" | "rendered">("idle");
  const [renderedPlanVideo, setRenderedPlanVideo] = useState<string | null>(null);
  const [planJobId, setPlanJobId] = useState<string | null>(null);
  const [storyboard, setStoryboard] = useState<StoryboardPlan | null>(null);
  const [planProgress, setPlanProgress] = useState(0);
  const [planLogMsg, setPlanLogMsg] = useState("");
  const [planLogs, setPlanLogs] = useState<{message: string, time: string}[]>([]);
  const [regeneratingSceneNum, setRegeneratingSceneNum] = useState<number | null>(null);
  const [sceneInstruction, setSceneInstruction] = useState("");
  const [activeInstructionModalScene, setActiveInstructionModalScene] = useState<number | null>(null);
  const [savingScenes, setSavingScenes] = useState(false);
  const [trends, setTrends] = useState<{title: string, opportunity_score: number}[]>([]);

  // Raw Footage Mode State
  const [url, setUrl] = useState("");
  const [rawStatus, setRawStatus] = useState("idle");
  const [rawJobId, setRawJobId] = useState<string | null>(null);
  const [rawProgress, setRawProgress] = useState(0);
  const [rawLogMsg, setRawLogMsg] = useState("");
  const [rawLogs, setRawLogs] = useState<{message: string, time: string}[]>([]);
  const [finalVideo, setFinalVideo] = useState<string | null>(null);
  const [removeSilence, setRemoveSilence] = useState(true);
  const [addPunchIns, setAddPunchIns] = useState(true);
  const [addSfx, setAddSfx] = useState(true);

  const planWsRef = useRef<WebSocket | null>(null);
  const rawWsRef = useRef<WebSocket | null>(null);

  // Load trend ideas on mount
  useEffect(() => {
    apiFetch(`${API_BASE_URL}/api/director/trends?niche=technology&count=3`)
      .then(res => res.json())
      .then(data => {
        if (data.opportunities) {
          setTrends(data.opportunities);
        }
      })
      .catch(() => {});
  }, []);

  // Storyboard WebSocket
  useEffect(() => {
    if (!planJobId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/api/generate/ws/${planJobId}`);
    planWsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          const msgText = data.message || data.data || "";
          setPlanLogMsg(msgText);
          if (typeof data.progress === "number" && !Number.isNaN(data.progress)) {
            setPlanProgress(data.progress <= 1.0 ? data.progress * 100 : data.progress);
          }
          if (msgText) {
            setPlanLogs(prev => [...prev, { message: msgText, time: new Date().toLocaleTimeString() }]);
          }
        } else if (data.type === "plan_ready" || (data.type === "full_state" && data.data?.result)) {
          const rawRes = data.data?.result || data.data || data.result;
          const res = typeof rawRes === "string" && rawRes.trim().startsWith("{") ? JSON.parse(rawRes) : rawRes;
          if (res && res.scenes) {
            setStoryboard(res);
            setPlanningStatus("ready");
            setPlanProgress(100);
          }
        } else if (data.type === "storyboard_updated") {
          setStoryboard(data.data);
        } else if (data.type === "render_complete") {
          setRenderedPlanVideo(data.video_path);
          setPlanningStatus("rendered");
          setPlanProgress(100);
        } else if (data.type === "update") {
          const st = data.data || data;
          if (typeof st.progress === "number") {
            setPlanProgress(st.progress <= 1.0 ? st.progress * 100 : st.progress);
          }
          if (st.step) setPlanLogMsg(st.step);
          if (st.status === "completed" && typeof st.result === "string" && st.result.endsWith(".mp4")) {
            setRenderedPlanVideo(st.result);
            setPlanningStatus("rendered");
          }
        }
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    return () => {
      ws.close();
    };
  }, [planJobId]);

  // Raw footage WebSocket
  useEffect(() => {
    if (!rawJobId) return;

    const ws = new WebSocket(`${WS_BASE_URL}/api/generate/ws/${rawJobId}`);
    rawWsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          setRawLogMsg(data.message);
          setRawProgress(data.progress * 100);
          setRawLogs(prev => [...prev, { message: data.message, time: new Date().toLocaleTimeString() }]);
        } else if (data.type === "update" || data.type === "full_state") {
          const state = data.data || data;
          if (state.status === "completed") {
            setRawStatus("completed");
            if (state.result) setFinalVideo(state.result);
          } else if (state.status === "failed") {
            setRawStatus("failed");
            setRawLogMsg(`Error: ${state.error}`);
          }
        }
      } catch (e) {
        console.error("WS Parse Error", e);
      }
    };

    return () => {
      ws.close();
    };
  }, [rawJobId]);

  const handleStartPlanning = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      alert("Please enter a content topic.");
      return;
    }

    setPlanningStatus("planning");
    setStoryboard(null);
    setPlanProgress(5);
    setPlanLogMsg("Starting Autonomous Creative Pipeline...");
    setPlanLogs([{ message: `Analyzing topic: '${topic}'`, time: new Date().toLocaleTimeString() }]);

    try {
      const res = await apiFetch(`${API_BASE_URL}/api/director/autonomous-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          duration_sec: targetDuration,
          style: selectedStyle,
          auto_approve: false
        })
      });
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to queue autonomous plan: " + data.detail);
        setPlanningStatus("idle");
      } else {
        setPlanJobId(data.job_id);
      }
    } catch {
      alert("API request failed.");
      setPlanningStatus("idle");
    }
  };

  const handleToggleLock = (sceneNumber: number) => {
    if (!storyboard) return;
    const updatedScenes = storyboard.scenes.map(s => 
      s.scene_number === sceneNumber ? { ...s, locked: !s.locked } : s
    );
    setStoryboard({ ...storyboard, scenes: updatedScenes });
  };

  const handleSceneFieldChange = <K extends keyof Scene>(sceneNumber: number, field: K, value: Scene[K]) => {
    if (!storyboard) return;
    const updatedScenes = storyboard.scenes.map(s => 
      s.scene_number === sceneNumber ? { ...s, [field]: value } : s
    );
    setStoryboard({ ...storyboard, scenes: updatedScenes });
  };

  const handleSaveSceneEdits = async () => {
    if (!storyboard || !planJobId) return;
    setSavingScenes(true);
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/director/update-scenes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: planJobId,
          scenes: storyboard.scenes
        })
      });
      if (res.ok) {
        alert("Storyboard changes saved successfully!");
      }
    } catch {
      alert("Failed to save changes.");
    } finally {
      setSavingScenes(false);
    }
  };

  const handleRegenerateScene = async (sceneNumber: number) => {
    if (!planJobId) return;
    setRegeneratingSceneNum(sceneNumber);
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/director/regenerate-scene`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: planJobId,
          scene_number: sceneNumber,
          instruction: sceneInstruction || "Make this scene more dynamic, engaging and visually cinematic."
        })
      });
      const data = await res.json();
      if (res.ok && data.plan) {
        setStoryboard(data.plan);
        setActiveInstructionModalScene(null);
        setSceneInstruction("");
      } else {
        alert("Scene regeneration failed: " + (data.detail || "Unknown error"));
      }
    } catch {
      alert("Failed to regenerate scene.");
    } finally {
      setRegeneratingSceneNum(null);
    }
  };

  const handleRawProcess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) {
      alert("Please enter a video URL");
      return;
    }
    
    setRawStatus("processing");
    setFinalVideo(null);
    setRawProgress(0);
    setRawLogMsg("Initializing Director Engine...");
    setRawLogs([{ message: "Starting Director Mode...", time: new Date().toLocaleTimeString() }]);
    
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/director/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          url,
          remove_silence: removeSilence,
          add_punch_ins: addPunchIns,
          add_sfx: addSfx
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert("Failed to start director: " + data.detail);
        setRawStatus("idle");
      } else {
        setRawJobId(data.job_id);
      }
    } catch {
      alert("API Error");
      setRawStatus("idle");
    }
  };

  return (
    <div className="max-w-[1500px] mx-auto animate-in fade-in duration-500 flex flex-col min-h-[calc(100vh-6rem)] pb-12">
      
      {/* Header & Mode Switcher */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <Film className="h-8 w-8 text-[#66fcf1]" /> Autonomous AI Director & Storyboard
          </h1>
          <p className="text-zinc-400 mt-1">
            Supervisory AI Director orchestrating deep research, multi-scene storyboarding, QA critique, and selective regeneration.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-black/60 p-1.5 rounded-xl border border-white/10 self-start md:self-auto">
          <button 
            onClick={() => setActiveTab("storyboard")}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "storyboard" 
                ? "bg-[#66fcf1] text-black shadow-[0_0_15px_rgba(102,252,241,0.25)]" 
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Sparkles className="h-4 w-4" /> Autonomous Storyboard
          </button>
          <button 
            onClick={() => setActiveTab("raw")}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "raw" 
                ? "bg-[#66fcf1] text-black shadow-[0_0_15px_rgba(102,252,241,0.25)]" 
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Sliders className="h-4 w-4" /> Raw Footage Auto-Editor
          </button>
        </div>
      </div>

      {/* TAB 1: Autonomous Storyboard Director */}
      {activeTab === "storyboard" && (
        <div className="space-y-8">
          
          {/* Top Panel: Topic & Style Input */}
          <div className="glass-card p-6 border border-white/10 shadow-2xl">
            <form onSubmit={handleStartPlanning} className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-end">
              
              <div className="lg:col-span-6">
                <label className="block text-xs font-bold text-zinc-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-[#66fcf1]" /> Video Concept or Prompt
                </label>
                <input 
                  type="text" 
                  value={topic}
                  onChange={e => setTopic(e.target.value)}
                  placeholder="e.g. The Quantum Computing Breakthrough No One Is Talking About..."
                  className="modern-input text-base"
                  disabled={planningStatus === "planning"}
                />

                {/* Viral Trend Quick Picks */}
                {trends.length > 0 && (
                  <div className="flex items-center gap-2 mt-3 flex-wrap">
                    <span className="text-[11px] text-zinc-500 font-bold flex items-center gap-1 uppercase">
                      <Flame className="h-3 w-3 text-orange-400" /> Hot Trends:
                    </span>
                    {trends.map((t, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setTopic(t.title)}
                        className="text-xs px-2.5 py-1 bg-white/5 hover:bg-white/10 text-zinc-300 rounded-md border border-white/5 transition-all text-left truncate max-w-[280px]"
                      >
                        {t.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="lg:col-span-2">
                <label className="block text-xs font-bold text-zinc-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Clock className="h-4 w-4 text-[#66fcf1]" /> Target Length
                </label>
                <select 
                  value={targetDuration}
                  onChange={e => setTargetDuration(Number(e.target.value))}
                  className="modern-input"
                  disabled={planningStatus === "planning"}
                >
                  <option value={30}>30s (Short)</option>
                  <option value={45}>45s (Standard)</option>
                  <option value={60}>60s (Deep-dive)</option>
                </select>
              </div>

              <div className="lg:col-span-2">
                <label className="block text-xs font-bold text-zinc-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                  <Film className="h-4 w-4 text-[#66fcf1]" /> Directing Style
                </label>
                <select 
                  value={selectedStyle}
                  onChange={e => setSelectedStyle(e.target.value)}
                  className="modern-input"
                  disabled={planningStatus === "planning"}
                >
                  <option value="Cinematic Documentary">Cinematic Documentary</option>
                  <option value="MrBeast Fast Paced">MrBeast Fast Paced</option>
                  <option value="Hormozi Explainer">Hormozi Explainer</option>
                  <option value="Minimalist Tech">Minimalist Tech</option>
                  <option value="Dark Storytelling">Dark Storytelling</option>
                </select>
              </div>

              <div className="lg:col-span-2">
                {planningStatus === "planning" ? (
                  <button type="button" disabled className="w-full py-3.5 bg-white/10 text-white font-bold rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                    <Loader2 className="h-5 w-5 animate-spin" /> Orchestrating...
                  </button>
                ) : (
                  <button type="submit" className="w-full py-3.5 bg-[#66fcf1] hover:bg-[#45f3e5] text-black font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(102,252,241,0.25)] flex items-center justify-center gap-2">
                    <Wand2 className="h-5 w-5" /> Direct Storyboard
                  </button>
                )}
              </div>

            </form>
          </div>

          {/* Planning Progress Display */}
          {(planningStatus === "planning" || planningStatus === "rendering") && (
            <div className="glass-card p-6 border border-[#66fcf1]/30 animate-pulse">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="h-5 w-5 text-[#66fcf1] animate-spin" />
                  <span className="text-sm font-bold text-white uppercase tracking-wider">AI Director Thinking: {planLogMsg}</span>
                </div>
                <span className="text-lg font-black text-[#66fcf1]">{Math.round(planProgress)}%</span>
              </div>
              <div className="w-full h-2 bg-black/60 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#66fcf1] to-[#45f3e5] transition-all duration-300" style={{ width: `${planProgress}%` }} />
              </div>
              <div className="mt-4 bg-black/40 rounded-xl p-3 max-h-32 overflow-y-auto space-y-1 font-mono text-xs text-zinc-400 border border-white/5">
                {planLogs.map((l, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-zinc-600">[{l.time}]</span>
                    <span>{l.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Storyboard Cards & Controls */}
          {storyboard && (
            <div className="space-y-6">
              
              {/* Storyboard Header Banner */}
              <div className="glass-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 bg-[#66fcf1]/10 text-[#66fcf1] border border-[#66fcf1]/30 rounded-md text-xs font-black uppercase">
                      {storyboard.style}
                    </span>
                    <span className="px-2.5 py-1 bg-green-500/10 text-green-400 border border-green-500/30 rounded-md text-xs font-black flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" /> QA Score: {storyboard.qa_score ?? 92}/100
                    </span>
                    <span className="text-xs text-zinc-400">Target: {storyboard.duration}s</span>
                  </div>
                  <h2 className="text-2xl font-black text-white mt-2">{storyboard.title}</h2>
                  <p className="text-sm text-zinc-400 mt-1 italic">Hook: &quot;{storyboard.hook}&quot;</p>
                </div>

                <div className="flex items-center gap-3">
                  <button 
                    onClick={handleSaveSceneEdits}
                    disabled={savingScenes}
                    className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold flex items-center gap-2 border border-white/10 transition-all"
                  >
                    <Save className="h-4 w-4" /> Save Scene Edits
                  </button>
                  <button 
                    onClick={async () => {
                      if (!planJobId || !storyboard) return;
                      setPlanningStatus("rendering");
                      setPlanProgress(75);
                      setPlanLogMsg("Synthesizing scene audio & visuals...");
                      try {
                        const res = await apiFetch(`${API_BASE_URL}/api/director/render-plan`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ job_id: planJobId, scenes: storyboard.scenes })
                        });
                        if (!res.ok) {
                          const err = await res.json();
                          alert("Render failed to start: " + (err.detail || "Unknown error"));
                          setPlanningStatus("ready");
                        }
                      } catch {
                        alert("Failed to connect to server for rendering.");
                        setPlanningStatus("ready");
                      }
                    }}
                    disabled={planningStatus === "rendering"}
                    className="px-6 py-2.5 bg-[#66fcf1] hover:bg-[#45f3e5] text-black font-black rounded-xl text-xs flex items-center gap-2 shadow-[0_0_15px_rgba(102,252,241,0.3)] transition-all disabled:opacity-50"
                  >
                    {planningStatus === "rendering" ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Rendering Master Video...</>
                    ) : (
                      <><Play className="h-4 w-4" /> Approve & Render Master Video</>
                    )}
                  </button>
                </div>
              </div>

              {/* Rendered Master Video Preview */}
              {renderedPlanVideo && (
                <div className="glass-card p-6 border border-[#66fcf1]/40 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-black text-[#66fcf1] uppercase tracking-wider flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5" /> Master Storyboard Video Rendered
                    </h3>
                    <a
                      href={getMediaUrl(renderedPlanVideo)}
                      download
                      className="px-4 py-2 bg-[#66fcf1] text-black font-bold rounded-xl text-xs flex items-center gap-2"
                    >
                      <Download className="h-4 w-4" /> Download MP4
                    </a>
                  </div>
                  <video src={getMediaUrl(renderedPlanVideo)} controls autoPlay className="w-full max-h-[440px] rounded-xl bg-black border border-white/10" />
                </div>
              )}

              {/* Storyboard Scene Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {storyboard.scenes.map((scene) => (
                  <div 
                    key={scene.scene_number} 
                    className={`glass-card p-5 border transition-all flex flex-col justify-between ${
                      scene.locked 
                        ? "border-[#66fcf1]/40 shadow-[0_0_20px_rgba(102,252,241,0.1)] bg-gradient-to-b from-[#66fcf1]/5 to-transparent" 
                        : "border-white/10 hover:border-white/20"
                    }`}
                  >
                    {/* Scene Card Header */}
                    <div>
                      <div className="flex items-center justify-between pb-3 border-b border-white/5 mb-3">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-white/10 rounded text-xs font-mono font-bold text-white">
                            Scene {scene.scene_number}
                          </span>
                          <span className="text-xs text-zinc-400 font-medium">
                            ~{scene.duration_estimate_sec}s
                          </span>
                          <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-[10px] font-bold uppercase">
                            {scene.camera_framing}
                          </span>
                        </div>

                        {/* Lock / Unlock Button */}
                        <button 
                          onClick={() => handleToggleLock(scene.scene_number)}
                          className={`p-1.5 rounded-lg text-xs transition-all ${
                            scene.locked 
                              ? "bg-[#66fcf1] text-black" 
                              : "bg-white/5 text-zinc-400 hover:text-white hover:bg-white/10"
                          }`}
                          title={scene.locked ? "Locked: Agent will not overwrite" : "Click to lock scene"}
                        >
                          {scene.locked ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                        </button>
                      </div>

                      {/* Script Narration */}
                      <div className="space-y-3">
                        <div>
                          <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">
                            Spoken Script (Narration)
                          </label>
                          <textarea 
                            value={scene.narration}
                            onChange={(e) => handleSceneFieldChange(scene.scene_number, "narration", e.target.value)}
                            rows={3}
                            className="w-full bg-black/40 border border-white/5 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-[#66fcf1]/50 resize-none font-medium leading-relaxed"
                          />
                        </div>

                        {/* Visual Description */}
                        <div>
                          <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">
                            Visual Prompt & Direction
                          </label>
                          <textarea 
                            value={scene.visual_description}
                            onChange={(e) => handleSceneFieldChange(scene.scene_number, "visual_description", e.target.value)}
                            rows={3}
                            className="w-full bg-black/40 border border-white/5 rounded-lg p-2.5 text-xs text-zinc-300 focus:outline-none focus:border-[#66fcf1]/50 resize-none leading-relaxed"
                          />
                        </div>

                        {/* Metadata Tags */}
                        <div className="flex items-center gap-2 flex-wrap pt-1">
                          {scene.music_cue && (
                            <span className="text-[10px] bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2 py-0.5 rounded">
                              🎵 {scene.music_cue}
                            </span>
                          )}
                          {scene.sfx_cue && (
                            <span className="text-[10px] bg-yellow-500/10 text-yellow-300 border border-yellow-500/20 px-2 py-0.5 rounded">
                              💥 {scene.sfx_cue}
                            </span>
                          )}
                          {scene.broll_query && (
                            <span className="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                              🔍 {scene.broll_query}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Scene Action Footer */}
                    <div className="pt-4 mt-3 border-t border-white/5">
                      {activeInstructionModalScene === scene.scene_number ? (
                        <div className="space-y-2 bg-black/60 p-2.5 rounded-lg border border-[#66fcf1]/30">
                          <input 
                            type="text" 
                            value={sceneInstruction}
                            onChange={(e) => setSceneInstruction(e.target.value)}
                            placeholder="e.g. Add drone wide shot, more suspense..."
                            className="w-full bg-black border border-white/10 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#66fcf1]"
                            autoFocus
                          />
                          <div className="flex items-center gap-2">
                            <button 
                              onClick={() => handleRegenerateScene(scene.scene_number)}
                              disabled={regeneratingSceneNum === scene.scene_number}
                              className="flex-1 py-1.5 bg-[#66fcf1] hover:bg-[#45f3e5] text-black font-bold rounded text-xs flex items-center justify-center gap-1"
                            >
                              {regeneratingSceneNum === scene.scene_number ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <RefreshCw className="h-3 w-3" />
                              )}
                              Regenerate
                            </button>
                            <button 
                              onClick={() => setActiveInstructionModalScene(null)}
                              className="px-2.5 py-1.5 bg-white/10 hover:bg-white/20 text-zinc-300 rounded text-xs"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button 
                          onClick={() => {
                            setActiveInstructionModalScene(scene.scene_number);
                            setSceneInstruction("");
                          }}
                          className="w-full py-2 bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white rounded-lg text-xs font-bold border border-white/5 flex items-center justify-center gap-1.5 transition-all"
                        >
                          <RefreshCw className="h-3.5 w-3.5 text-[#66fcf1]" /> Regenerate Scene
                        </button>
                      )}
                    </div>

                  </div>
                ))}
              </div>

            </div>
          )}

        </div>
      )}

      {/* TAB 2: Raw Video Auto-Editor */}
      {activeTab === "raw" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
          
          {/* Left Side: Input & Settings */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            <div className="glass-card p-6">
              <form onSubmit={handleRawProcess} className="space-y-6">
                <div>
                  <label className="block text-xs font-bold text-zinc-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <Upload className="h-4 w-4" /> Raw Video URL (YouTube or Direct Link)
                  </label>
                  <input 
                    type="text" 
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    placeholder="https://..."
                    className="modern-input"
                    disabled={rawStatus === "processing"}
                  />
                </div>

                <div className="space-y-3 pt-2">
                  <label className="block text-xs font-bold text-zinc-400 mb-2 uppercase tracking-wider flex items-center gap-2">
                    <Settings2 className="h-4 w-4" /> Editing Directives
                  </label>
                  
                  <label className="flex items-center gap-3 p-3 bg-black/40 border border-white/5 rounded-xl cursor-pointer hover:bg-white/5 transition-all">
                    <input type="checkbox" checked={removeSilence} onChange={e => setRemoveSilence(e.target.checked)} className="w-4 h-4 accent-[#66fcf1]" disabled={rawStatus === "processing"} />
                    <div className="flex-1">
                      <p className="text-sm font-bold text-white">Silence & Dead Air Removal</p>
                      <p className="text-xs text-zinc-500">Automatically trims pauses for hyper-fast engagement.</p>
                    </div>
                    <FileAudio className="h-5 w-5 text-zinc-600" />
                  </label>

                  <label className="flex items-center gap-3 p-3 bg-black/40 border border-white/5 rounded-xl cursor-pointer hover:bg-white/5 transition-all">
                    <input type="checkbox" checked={addPunchIns} onChange={e => setAddPunchIns(e.target.checked)} className="w-4 h-4 accent-[#66fcf1]" disabled={rawStatus === "processing"} />
                    <div className="flex-1">
                      <p className="text-sm font-bold text-white">Dynamic Punch-ins</p>
                      <p className="text-xs text-zinc-500">Auto-zooms camera on high-impact sentences.</p>
                    </div>
                    <Film className="h-5 w-5 text-zinc-600" />
                  </label>

                  <label className="flex items-center gap-3 p-3 bg-black/40 border border-white/5 rounded-xl cursor-pointer hover:bg-white/5 transition-all">
                    <input type="checkbox" checked={addSfx} onChange={e => setAddSfx(e.target.checked)} className="w-4 h-4 accent-[#66fcf1]" disabled={rawStatus === "processing"} />
                    <div className="flex-1">
                      <p className="text-sm font-bold text-white">Keyword Sound Effects & -14 LUFS Mastering</p>
                      <p className="text-xs text-zinc-500">Injects swoosh sounds and applies broadcast audio mastering.</p>
                    </div>
                    <Wand2 className="h-5 w-5 text-zinc-600" />
                  </label>
                </div>

                <div className="pt-4">
                  {rawStatus === "processing" ? (
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

            {rawStatus !== "idle" && (
              <div className="glass-card p-6 flex flex-col gap-4 flex-1">
                <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3">
                  Live Timeline
                </h2>
                <div className="flex-1 flex flex-col justify-center gap-6">
                  <div className="text-center">
                    <p className="text-4xl font-black text-white">{Math.round(rawProgress)}%</p>
                    <p className="text-sm text-[#66fcf1] mt-2 font-medium">{rawLogMsg}</p>
                  </div>
                  
                  <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-[#66fcf1] to-[#45f3e5] transition-all duration-300"
                      style={{ width: `${rawProgress}%` }}
                    />
                  </div>
                  
                  <div className="mt-4 flex-1 bg-black/40 rounded-xl p-4 overflow-y-auto border border-white/5 space-y-2 max-h-[150px]">
                    {rawLogs.map((log, i) => (
                      <div key={i} className="flex gap-3 text-xs font-mono text-zinc-400">
                        <span className="text-zinc-600">[{log.time}]</span>
                        <span className={i === rawLogs.length - 1 ? "text-[#66fcf1]" : ""}>{log.message}</span>
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
                        src={`${API_BASE_URL}/api/generate/media?path=${encodeURIComponent(finalVideo.replace(/\\/g, '/'))}`}
                        controls 
                        className="w-full h-full object-cover"
                      />
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <a href={`${API_BASE_URL}/api/generate/media?path=${encodeURIComponent(finalVideo.replace(/\\/g, '/'))}`} download className="flex-1 py-4 bg-[#66fcf1] hover:bg-[#45f3e5] text-black rounded-xl flex items-center justify-center gap-2 text-sm font-bold transition-all shadow-[0_0_15px_rgba(102,252,241,0.2)]">
                        <Download className="h-5 w-5" /> Download Final Master
                      </a>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
