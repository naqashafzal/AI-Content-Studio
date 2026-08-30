"use client";

import React, { useState } from "react";
import { Play, Pause, FastForward, Rewind, Scissors, Type, Image as ImageIcon } from "lucide-react";

interface TimelineEditorProps {
  clip: any;
  onSave: (adjustedClip: any) => void;
  onCancel: () => void;
}

export default function TimelineEditor({ clip, onSave, onCancel }: TimelineEditorProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(clip?.start || 0);
  
  // These would ideally be draggable handles, simulating state here
  const [startHandle, setStartHandle] = useState(clip?.start || 0);
  const [endHandle, setEndHandle] = useState(clip?.end || 30);

  const duration = endHandle - startHandle;

  return (
    <div className="flex flex-col h-full bg-zinc-950 border border-white/10 rounded-xl overflow-hidden shadow-2xl">
      {/* Top Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-zinc-900/50">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Scissors className="h-4 w-4 text-emerald-400" />
          Timeline Editor - {clip?.title || "Draft Clip"}
        </h3>
        <div className="flex items-center gap-3">
          <button onClick={onCancel} className="px-4 py-1.5 text-xs font-bold text-zinc-400 hover:text-white transition-colors">
            Cancel
          </button>
          <button 
            onClick={() => onSave({ ...clip, start: startHandle, end: endHandle })} 
            className="px-4 py-1.5 text-xs font-bold bg-emerald-500/20 text-emerald-400 rounded-md border border-emerald-500/30 hover:bg-emerald-500/30 transition-all"
          >
            Save Cuts
          </button>
        </div>
      </div>

      {/* Video Preview Area */}
      <div className="flex-1 p-6 flex flex-col items-center justify-center bg-black/40 relative">
        <div className="aspect-[9/16] h-full max-h-[400px] bg-black border border-white/10 rounded-lg flex items-center justify-center shadow-lg relative overflow-hidden">
           {/* Mock Video Element */}
           <div className="text-zinc-600 text-xs text-center p-4">
             <p className="font-bold text-white mb-2">Video Preview</p>
             <p>Start: {startHandle.toFixed(1)}s | End: {endHandle.toFixed(1)}s</p>
             <p className="text-[10px] mt-4 opacity-50">Real video element would bind to these timestamps</p>
           </div>
        </div>
        
        {/* Controls */}
        <div className="flex items-center gap-6 mt-6">
          <button className="text-zinc-400 hover:text-white transition-colors"><Rewind className="h-5 w-5" /></button>
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className="h-12 w-12 rounded-full bg-white text-black flex items-center justify-center hover:scale-105 transition-transform"
          >
            {isPlaying ? <Pause className="h-5 w-5 fill-black" /> : <Play className="h-5 w-5 fill-black ml-1" />}
          </button>
          <button className="text-zinc-400 hover:text-white transition-colors"><FastForward className="h-5 w-5" /></button>
        </div>
      </div>

      {/* Timeline Tracks */}
      <div className="h-64 bg-zinc-900 border-t border-white/10 flex flex-col">
        {/* Scrubber Area */}
        <div className="h-8 border-b border-white/5 relative flex items-center px-4">
            {/* Playhead */}
            <div className="absolute top-0 bottom-0 w-px bg-red-500 z-50 pointer-events-none" style={{ left: '30%' }}>
                <div className="w-3 h-3 bg-red-500 rounded-full -ml-1.5 -mt-1 shadow-[0_0_10px_rgba(239,68,68,0.5)]"></div>
            </div>
            <div className="w-full text-[9px] text-zinc-500 flex justify-between font-mono">
                <span>0:00</span>
                <span>0:15</span>
                <span>0:30</span>
                <span>0:45</span>
                <span>1:00</span>
            </div>
        </div>

        {/* Tracks container */}
        <div className="flex-1 overflow-y-auto p-2 space-y-2 relative">
            
            {/* Main Video Track */}
            <div className="flex gap-2 items-center group">
                <div className="w-24 text-[10px] font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Scissors className="h-3 w-3" /> Master
                </div>
                <div className="flex-1 h-12 bg-white/5 rounded-md border border-white/10 relative cursor-col-resize group-hover:bg-white/10 transition-colors overflow-hidden">
                    {/* Mock Waveform / Frame strip */}
                    <div className="absolute inset-0 opacity-20 flex" style={{ backgroundImage: 'linear-gradient(90deg, #ffffff 1px, transparent 1px)', backgroundSize: '20px 100%' }}></div>
                    
                    {/* Selected Region */}
                    <div 
                        className="absolute top-0 bottom-0 bg-emerald-500/20 border-l-2 border-r-2 border-emerald-500 flex items-center justify-center overflow-hidden backdrop-blur-sm"
                        style={{ left: '20%', right: '30%' }}
                    >
                        <span className="text-[10px] font-bold text-emerald-400 bg-black/50 px-2 py-0.5 rounded">Duration: {duration.toFixed(1)}s</span>
                    </div>
                </div>
            </div>

            {/* B-Roll Track */}
            <div className="flex gap-2 items-center">
                <div className="w-24 text-[10px] font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <ImageIcon className="h-3 w-3" /> B-Roll
                </div>
                <div className="flex-1 h-10 bg-white/5 rounded-md border border-white/10 relative">
                     <div className="absolute top-1 bottom-1 bg-purple-500/30 border border-purple-500/50 rounded flex items-center px-2 text-[9px] text-purple-200" style={{ left: '35%', width: '15%' }}>
                        Stock: Bitcoin
                     </div>
                </div>
            </div>

            {/* Captions Track */}
            <div className="flex gap-2 items-center">
                <div className="w-24 text-[10px] font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Type className="h-3 w-3" /> Text
                </div>
                <div className="flex-1 h-8 bg-white/5 rounded-md border border-white/10 relative">
                    <div className="absolute top-1 bottom-1 bg-blue-500/30 border border-blue-500/50 rounded flex items-center justify-center text-[9px] text-blue-200" style={{ left: '20%', right: '30%' }}>
                        Auto-Captions (Viral Style)
                    </div>
                </div>
            </div>

        </div>
      </div>
    </div>
  );
}
