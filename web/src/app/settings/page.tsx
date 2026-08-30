"use client";

import { useState, useEffect } from "react";
import { Save, Settings, Key, Cpu, Sparkles, Loader2 } from "lucide-react";
import { TabSelect } from "@/components/TabSelect";
import { useConfig } from "@/context/ConfigContext";

export default function SettingsPage() {
  const { config, updateConfig, saveConfig, status: contextStatus } = useConfig();
  
  if (contextStatus === "loading") {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#66fcf1]" />
      </div>
    );
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await saveConfig();
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Platform Settings</h1>
        <p className="text-zinc-400 mt-1">Manage your API keys, engines, and system preferences.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
            <Key className="h-5 w-5 text-white" />
            <h2 className="text-xs font-bold text-white tracking-widest uppercase">API Keys</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Gemini API Key</label>
              <input type="password" value={config.GEMINI_API_KEY || ""} onChange={e => updateConfig("GEMINI_API_KEY", e.target.value)} className="modern-input" placeholder="AI Studio Key..." />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">WaveSpeed API Key</label>
              <input type="password" value={config.WAVESPEED_API_KEY || ""} onChange={e => updateConfig("WAVESPEED_API_KEY", e.target.value)} className="modern-input" placeholder="Video gen key..." />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Serper API Key</label>
              <input type="password" value={config.SERPER_API_KEY || ""} onChange={e => updateConfig("SERPER_API_KEY", e.target.value)} className="modern-input" placeholder="Search API key..." />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Pixabay API Key</label>
              <input type="password" value={config.PIXABAY_API_KEY || ""} onChange={e => updateConfig("PIXABAY_API_KEY", e.target.value)} className="modern-input" placeholder="For B-Roll..." />
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
            <Cpu className="h-5 w-5 text-white" />
            <h2 className="text-xs font-bold text-white tracking-widest uppercase">Generation Engines</h2>
          </div>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">LLM Engine</label>
              <TabSelect options={["Gemini API", "WaveSpeed AI", "Ollama"]} value={config.TEXT_ENGINE || "Gemini API"} onChange={v => updateConfig("TEXT_ENGINE", v)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Image Engine</label>
              <TabSelect options={["Gemini API", "WaveSpeed AI"]} value={config.IMAGE_ENGINE || "Gemini API"} onChange={v => updateConfig("IMAGE_ENGINE", v)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Audio TTS Engine</label>
              <TabSelect options={["Gemini API", "WaveSpeed AI"]} value={config.AUDIO_ENGINE || "Gemini API"} onChange={v => updateConfig("AUDIO_ENGINE", v)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Video Engine</label>
              <TabSelect options={["WaveSpeed AI", "Vertex AI (Veo)"]} value={config.VIDEO_ENGINE || "WaveSpeed AI"} onChange={v => updateConfig("VIDEO_ENGINE", v)} />
            </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-white/10">
            <h3 className="text-xs font-bold text-zinc-400 tracking-widest uppercase mb-4">WaveSpeed Custom Models</h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Text Model (LLM)</label>
                <input type="text" value={config.WAVESPEED_TEXT_MODEL || ""} onChange={e => updateConfig("WAVESPEED_TEXT_MODEL", e.target.value)} className="modern-input" placeholder="e.g. meta-llama/llama-3.3-70b-instruct" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Image Model</label>
                <input type="text" value={config.WAVESPEED_IMAGE_MODEL || ""} onChange={e => updateConfig("WAVESPEED_IMAGE_MODEL", e.target.value)} className="modern-input" placeholder="e.g. black-forest-labs/flux-1.1-pro-ultra" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Video Model</label>
                <input type="text" value={config.WAVESPEED_VIDEO_MODEL || ""} onChange={e => updateConfig("WAVESPEED_VIDEO_MODEL", e.target.value)} className="modern-input" placeholder="e.g. wavespeed-ai/ltx-2.3-text-to-video" />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Audio/Voice Model</label>
                <input type="text" value={config.WAVESPEED_AUDIO_MODEL || ""} onChange={e => updateConfig("WAVESPEED_AUDIO_MODEL", e.target.value)} className="modern-input" placeholder="e.g. elevenlabs/text-to-speech" />
              </div>
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
            <Sparkles className="h-5 w-5 text-[#66fcf1]" />
            <h2 className="text-xs font-bold text-white tracking-widest uppercase">Caption Aesthetics (Global)</h2>
          </div>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Font Style</label>
              <select 
                value={config.CAPTION_FONT || "Arial"} 
                onChange={e => updateConfig("CAPTION_FONT", e.target.value)} 
                className="modern-input cursor-pointer"
              >
                <option value="Arial">Arial (Modern)</option>
                <option value="Impact">Impact (Bold)</option>
                <option value="Roboto">Roboto (Clean)</option>
                <option value="Times New Roman">Times (Classic)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Color Theme</label>
              <select 
                value={config.CAPTION_THEME || "default"} 
                onChange={e => updateConfig("CAPTION_THEME", e.target.value)} 
                className="modern-input cursor-pointer"
              >
                <option value="default">Clean White</option>
                <option value="viral_yellow">Viral Yellow</option>
                <option value="neon_cyber">Neon Cyberpunk</option>
                <option value="black_white">High Contrast B&W</option>
              </select>
            </div>
          </div>
          
          <div className="mt-6">
            <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider">Live Preview</label>
            <div className="w-full aspect-video bg-black/60 rounded-lg relative overflow-hidden flex items-end justify-center pb-6 border border-white/5"
                 style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1536440136628-849c177e76a1?q=80&w=1925&auto=format&fit=crop")', backgroundSize: 'cover', backgroundPosition: 'center' }}>
              
              {/* Overlay gradient for readability */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
              
              <div 
                className="relative text-center px-4 py-2 text-xl md:text-3xl font-bold leading-tight"
                style={{
                  fontFamily: config.CAPTION_FONT === 'Times New Roman' ? '"Times New Roman", Times, serif' : 
                              config.CAPTION_FONT === 'Impact' ? 'Impact, charcoal, sans-serif' : 
                              config.CAPTION_FONT === 'Roboto' ? 'Roboto, sans-serif' : 'Arial, sans-serif',
                  
                  color: config.CAPTION_THEME === 'viral_yellow' ? '#FFFF00' :
                         config.CAPTION_THEME === 'neon_cyber' ? '#00FFFF' :
                         config.CAPTION_THEME === 'black_white' ? '#000000' : '#FFFFFF',
                         
                  backgroundColor: config.CAPTION_THEME === 'neon_cyber' ? 'transparent' :
                                   config.CAPTION_THEME === 'black_white' ? 'rgba(255, 255, 255, 0.5)' : 'rgba(0, 0, 0, 0.5)',
                                   
                  textShadow: config.CAPTION_THEME === 'neon_cyber' ? '0 0 5px #FF00FF, 0 0 10px #FF00FF, 2px 2px 0px #FF00FF, -2px -2px 0px #FF00FF, 2px -2px 0px #FF00FF, -2px 2px 0px #FF00FF' :
                              config.CAPTION_THEME === 'black_white' ? '2px 2px 0px #FFF, -2px -2px 0px #FFF, 2px -2px 0px #FFF, -2px 2px 0px #FFF' :
                              '2px 2px 0px #000, -2px -2px 0px #000, 2px -2px 0px #000, -2px 2px 0px #000'
                }}
              >
                Bruce Wayne stood in the darkness.
              </div>
            </div>
          </div>

          <div className="mt-6">
            <label className="block text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wider flex items-center justify-between">
              <span>Font Size</span>
              <span className="text-[#66fcf1]">{config.CAPTION_FONT_SIZE || 22}px</span>
            </label>
            <input 
              type="range" 
              min="16" 
              max="40" 
              step="2"
              value={config.CAPTION_FONT_SIZE || 22}
              onChange={e => updateConfig("CAPTION_FONT_SIZE", parseInt(e.target.value))}
              className="w-full accent-[#66fcf1] h-2 bg-white/10 rounded-lg appearance-none cursor-pointer"
            />
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-white/5 mt-8">
          <button type="submit" className="btn-primary !w-auto px-10">
            <Save className="h-4 w-4" />
            {contextStatus === "saving" ? "Saving..." : contextStatus === "saved" ? "Saved!" : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
  );
}