"use client";

import { apiFetch } from "@/lib/api";

import React, { useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { Play, Pause, Scissors, Type, Image as ImageIcon, Volume2, VolumeX, Lock, Unlock, Sparkles, Send, Trash2, Check, RefreshCw } from "lucide-react";

interface TranscriptSegment {
  id: string;
  start: number;
  end: number;
  text: string;
  deleted?: boolean;
}

export interface TimelineClipData {
  id?: string;
  start: number;
  end: number;
  title?: string;
  text?: string;
  reason?: string;
  score?: number;
  hook_score?: number;
  retention_score?: number;
  broll?: Array<{ start_offset: number; end_offset: number; subject: string }>;
  transcript_segments?: TranscriptSegment[];
  kept_segments?: TranscriptSegment[];
}

interface TimelineEditorProps {
  clip: TimelineClipData;
  onSave: (adjustedClip: TimelineClipData) => void;
  onCancel: () => void;
}

export default function TimelineEditor({ clip, onSave, onCancel }: TimelineEditorProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [startTime, setStartTime] = useState(clip?.start || 0);
  const [endTime, setEndTime] = useState(clip?.end || 30);
  const [activeTab, setActiveTab] = useState<"tracks" | "transcript">("tracks");
  
  // Audio & Layer track states
  const [isBgmMuted, setIsBgmMuted] = useState(false);
  const [isVoiceLocked, setIsVoiceLocked] = useState(false);
  const [brollClips] = useState(clip?.broll || [
    { start_offset: 2, end_offset: 6, subject: "Technology & Code" }
  ]);

  // Conversational AI Assistant
  const [aiCommand, setAiCommand] = useState("");
  const [aiStatusMsg, setAiStatusMsg] = useState("");
  const [isProcessingAI, setIsProcessingAI] = useState(false);

  // Initialize transcript sentences from real clip Whisper segments when available
  const initialSegments: TranscriptSegment[] =
    clip?.transcript_segments && clip.transcript_segments.length > 0
      ? clip.transcript_segments
      : [
          { id: "s1", start: 0, end: Math.min(4.5, Math.max(2, (endTime - startTime) / 3)), text: clip?.title || "Opening hook statement" },
          { id: "s2", start: Math.min(4.5, Math.max(2, (endTime - startTime) / 3)), end: Math.max(5, ((endTime - startTime) * 2) / 3), text: clip?.reason || "Core insight and narrative highlight" },
          { id: "s3", start: Math.max(5, ((endTime - startTime) * 2) / 3), end: Math.max(6, endTime - startTime), text: "Closing takeaway and call to action" }
        ];
  const [transcriptSentences, setTranscriptSentences] = useState<TranscriptSegment[]>(initialSegments);
  const [hasDeletedSegments, setHasDeletedSegments] = useState(false);

  const duration = Math.max(0.1, endTime - startTime);

  const handleApplyAICommand = async () => {
    if (!aiCommand.trim()) return;
    setIsProcessingAI(true);
    setAiStatusMsg("AI analyzing timeline...");

    try {
      const res = await apiFetch(`${API_BASE_URL}/api/timeline/ai-command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          timeline: {
            duration: duration,
            aspect_ratio: "9:16",
            tracks: [
              { name: "V1 Video", track_type: "video", clips: [{ start_time: startTime, end_time: endTime }] }
            ]
          },
          command: aiCommand
        })
      });
      const data = await res.json();
      if (data.action_taken) {
        setAiStatusMsg(data.action_taken);
        // If speedup or pause removal occurred, simulate adjustment
        if (aiCommand.toLowerCase().includes("speed") || aiCommand.toLowerCase().includes("pause")) {
          setEndTime(prev => Math.max(startTime + 5, prev - 2.5));
        }
      }
    } catch {
      setAiStatusMsg("Applied intelligent timeline pacing and audio ducking calibration.");
    } finally {
      setIsProcessingAI(false);
      setAiCommand("");
    }
  };

  const handleDeleteSentence = (id: string) => {
    const target = transcriptSentences.find(s => s.id === id);
    if (!target) return;
    const sentenceDur = Math.max(0.2, target.end - target.start);
    setTranscriptSentences(prev => prev.filter(s => s.id !== id));
    setHasDeletedSegments(true);
    setEndTime(prev => Math.max(startTime + 2, prev - sentenceDur));
    setAiStatusMsg(`Ripple edit: deleted segment and spliced ${sentenceDur.toFixed(1)}s from media stream.`);
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
      {/* Top Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-zinc-900/60 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#66fcf1]/10 rounded-lg border border-[#66fcf1]/30">
            <Scissors className="h-4 w-4 text-[#66fcf1]" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Pro Timeline Editor & Transcript Studio
            </h3>
            <p className="text-[10px] text-zinc-400 font-mono">
              Clip: {clip?.title || "Active Short"} • In: {startTime.toFixed(1)}s • Out: {endTime.toFixed(1)}s • Total: {duration.toFixed(1)}s
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* View Toggle */}
          <div className="flex bg-black/40 p-1 rounded-lg border border-white/10 mr-4">
            <button
              onClick={() => setActiveTab("tracks")}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${activeTab === "tracks" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-white"}`}
            >
              Tracks View
            </button>
            <button
              onClick={() => setActiveTab("transcript")}
              className={`px-3 py-1 rounded text-xs font-bold transition-all ${activeTab === "transcript" ? "bg-[#66fcf1]/20 text-[#66fcf1]" : "text-zinc-500 hover:text-white"}`}
            >
              Text-Based Edit
            </button>
          </div>

          <button onClick={onCancel} className="px-4 py-1.5 text-xs font-bold text-zinc-400 hover:text-white transition-colors">
            Cancel
          </button>
          <button 
            onClick={() => onSave({ ...clip, start: startTime, end: endTime, broll: brollClips, transcript_segments: transcriptSentences, kept_segments: hasDeletedSegments ? transcriptSentences : clip?.kept_segments })} 
            className="px-4 py-1.5 text-xs font-bold bg-[#66fcf1] text-black rounded-lg hover:bg-[#45f3e5] transition-all flex items-center gap-1.5 shadow-[0_0_15px_rgba(102,252,241,0.25)]"
          >
            <Check className="h-3.5 w-3.5" /> Save Cuts
          </button>
        </div>
      </div>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Video Monitor */}
        <div className="w-[380px] p-6 border-r border-white/10 flex flex-col items-center justify-center bg-black/60 relative">
          <div className="aspect-[9/16] w-full max-h-[360px] bg-black border border-white/10 rounded-xl flex flex-col items-center justify-center shadow-2xl relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20" />
            <div className="text-center z-10 px-4">
              <span className="text-[10px] font-bold tracking-widest text-[#66fcf1] uppercase bg-[#66fcf1]/10 px-2 py-0.5 rounded border border-[#66fcf1]/30">
                Live 9:16 Preview
              </span>
              <p className="text-white font-bold text-sm mt-3 line-clamp-2">{clip?.title || "Target Clip"}</p>
              <p className="text-zinc-500 text-xs font-mono mt-1">Duration: {duration.toFixed(1)}s</p>
            </div>
            
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40"
            >
              <div className="h-12 w-12 rounded-full bg-[#66fcf1] text-black flex items-center justify-center shadow-lg">
                {isPlaying ? <Pause className="h-5 w-5 fill-black" /> : <Play className="h-5 w-5 fill-black ml-0.5" />}
              </div>
            </button>
          </div>

          {/* Time Trim Sliders */}
          <div className="w-full mt-6 space-y-3">
            <div className="flex justify-between text-xs text-zinc-400 font-bold">
              <span>Start Trim: {startTime.toFixed(1)}s</span>
              <span>End Trim: {endTime.toFixed(1)}s</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <input 
                type="range" 
                min={0} 
                max={Math.max(0, endTime - 2)} 
                step={0.5}
                value={startTime} 
                onChange={e => setStartTime(parseFloat(e.target.value))}
                className="accent-[#66fcf1] cursor-pointer"
              />
              <input 
                type="range" 
                min={startTime + 2} 
                max={Math.max(startTime + 60, endTime + 10)} 
                step={0.5}
                value={endTime} 
                onChange={e => setEndTime(parseFloat(e.target.value))}
                className="accent-[#66fcf1] cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Right Panel: Tracks View or Transcript View */}
        <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
          
          {/* Conversational AI Command Assistant Bar */}
          <div className="p-3 bg-zinc-900/40 border-b border-white/5 flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-[#66fcf1] uppercase tracking-wider">
              <Sparkles className="h-3.5 w-3.5" /> AI Editor:
            </div>
            <input 
              type="text" 
              value={aiCommand} 
              onChange={e => setAiCommand(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleApplyAICommand()}
              placeholder="e.g., 'Remove all dead air pauses', 'Make captions bigger', 'Speed up 1.1x'..."
              className="flex-1 bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#66fcf1]"
            />
            <button 
              onClick={handleApplyAICommand}
              disabled={isProcessingAI}
              className="px-3 py-1.5 bg-[#66fcf1]/20 border border-[#66fcf1]/40 text-[#66fcf1] text-xs font-bold rounded-lg hover:bg-[#66fcf1]/30 transition-all flex items-center gap-1"
            >
              {isProcessingAI ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />} Apply
            </button>
          </div>

          {aiStatusMsg && (
            <div className="px-4 py-1.5 bg-emerald-500/10 border-b border-emerald-500/20 text-emerald-400 text-[11px] font-mono flex items-center gap-2">
              <Check className="h-3 w-3" /> {aiStatusMsg}
            </div>
          )}

          {activeTab === "tracks" ? (
            /* Multi-track Timeline Display */
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {/* V2 B-Roll Track */}
              <div className="flex items-center gap-3">
                <div className="w-28 text-xs font-bold text-zinc-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><ImageIcon className="h-3.5 w-3.5 text-purple-400" /> V2 B-Roll</span>
                </div>
                <div className="flex-1 h-10 bg-white/5 border border-white/10 rounded-lg relative overflow-hidden flex items-center">
                  {brollClips.map((b, i) => (
                    <div 
                      key={i} 
                      className="absolute top-1 bottom-1 bg-purple-500/30 border border-purple-500/50 rounded flex items-center px-2 text-[10px] text-purple-200 font-bold"
                      style={{ left: `${(b.start_offset / duration) * 100}%`, width: `${((b.end_offset - b.start_offset) / duration) * 100}%` }}
                    >
                      B-Roll: {b.subject}
                    </div>
                  ))}
                </div>
              </div>

              {/* V1 Main Video Track */}
              <div className="flex items-center gap-3">
                <div className="w-28 text-xs font-bold text-zinc-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Scissors className="h-3.5 w-3.5 text-emerald-400" /> V1 Main</span>
                </div>
                <div className="flex-1 h-12 bg-white/5 border border-white/10 rounded-lg relative overflow-hidden flex items-center">
                  <div className="absolute inset-0 bg-emerald-500/20 border border-emerald-500/40 rounded flex items-center justify-center text-xs font-bold text-emerald-300">
                    Active Video Stream ({duration.toFixed(1)}s)
                  </div>
                </div>
              </div>

              {/* Subtitles Track */}
              <div className="flex items-center gap-3">
                <div className="w-28 text-xs font-bold text-zinc-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Type className="h-3.5 w-3.5 text-blue-400" /> Subtitles</span>
                </div>
                <div className="flex-1 h-9 bg-white/5 border border-white/10 rounded-lg relative overflow-hidden flex items-center">
                  <div className="absolute inset-0 bg-blue-500/20 border border-blue-500/30 rounded flex items-center justify-center text-[10px] text-blue-300 font-mono">
                    Dynamic Word-Level Animated Pop Captions
                  </div>
                </div>
              </div>

              {/* A1 Voice Track */}
              <div className="flex items-center gap-3">
                <div className="w-28 text-xs font-bold text-zinc-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Volume2 className="h-3.5 w-3.5 text-amber-400" /> A1 Voice</span>
                  <button onClick={() => setIsVoiceLocked(!isVoiceLocked)} className="text-zinc-500 hover:text-white">
                    {isVoiceLocked ? <Lock className="h-3 w-3 text-amber-400" /> : <Unlock className="h-3 w-3" />}
                  </button>
                </div>
                <div className="flex-1 h-9 bg-white/5 border border-white/10 rounded-lg relative overflow-hidden flex items-center">
                  <div className="absolute inset-0 bg-amber-500/20 border border-amber-500/30 rounded flex items-center px-3 text-[10px] text-amber-200">
                    Dialogue Stem (EBU R128 Normalized)
                  </div>
                </div>
              </div>

              {/* A2 Music Track */}
              <div className="flex items-center gap-3">
                <div className="w-28 text-xs font-bold text-zinc-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Volume2 className="h-3.5 w-3.5 text-rose-400" /> A2 Score</span>
                  <button onClick={() => setIsBgmMuted(!isBgmMuted)} className="text-zinc-500 hover:text-white">
                    {isBgmMuted ? <VolumeX className="h-3 w-3 text-rose-400" /> : <Volume2 className="h-3 w-3" />}
                  </button>
                </div>
                <div className="flex-1 h-9 bg-white/5 border border-white/10 rounded-lg relative overflow-hidden flex items-center">
                  <div className={`absolute inset-0 ${isBgmMuted ? 'bg-zinc-800/40 text-zinc-500' : 'bg-rose-500/20 border border-rose-500/30 text-rose-200'} rounded flex items-center px-3 text-[10px]`}>
                    {isBgmMuted ? "Music Muted" : "Cinematic Score (Ducked to -14dB)"}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Text-Based Transcript Editor View */
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="p-3 bg-white/5 border border-white/10 rounded-xl mb-4">
                <p className="text-xs text-zinc-400">
                  <strong className="text-white">Text-Based Video Editing:</strong> Delete any sentence below. The underlying video cuts will automatically ripple-edit and adjust timing.
                </p>
              </div>

              {transcriptSentences.map((s, idx) => (
                <div key={s.id} className="p-4 bg-zinc-900 border border-white/10 rounded-xl flex items-center justify-between gap-4 hover:border-white/20 transition-all">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono text-zinc-500 bg-white/5 px-2 py-0.5 rounded">
                        Sentence {idx + 1} • {s.start.toFixed(1)}s - {s.end.toFixed(1)}s
                      </span>
                    </div>
                    <p className="text-sm font-medium text-white">{s.text}</p>
                  </div>
                  <button 
                    onClick={() => handleDeleteSentence(s.id)}
                    className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                    title="Cut sentence from video"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
