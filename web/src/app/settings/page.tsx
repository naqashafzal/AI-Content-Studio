"use client";

import { Save, Key, Cpu, Sparkles, Loader2, CheckCircle, ShieldCheck, Coffee, Heart } from "lucide-react";
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
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500 pb-20">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#66fcf1]/10 text-[#66fcf1] border border-[#66fcf1]/20 text-[10px] font-black uppercase tracking-wider mb-2">
            <ShieldCheck className="h-3 w-3" /> System Configuration
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Platform Settings & APIs</h1>
          <p className="text-zinc-400 text-sm mt-1">Configure your generation providers, API credentials, and default engines.</p>
        </div>

        <div>
          <button 
            onClick={handleSave} 
            disabled={contextStatus === "saving"}
            className="btn-primary !w-auto px-6 py-3 text-xs font-black shadow-[0_0_20px_rgba(102,252,241,0.3)] disabled:opacity-50"
          >
            {contextStatus === "saving" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-black" /> Saving...
              </>
            ) : contextStatus === "saved" ? (
              <>
                <CheckCircle className="h-4 w-4 text-black" /> Saved Changes
              </>
            ) : (
              <>
                <Save className="h-4 w-4 text-black stroke-[2.5]" /> Save Configuration
              </>
            )}
          </button>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* API Credentials Card */}
        <div className="glass-card p-6 md:p-8 space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-white/10">
            <div className="p-2 rounded-xl bg-[#66fcf1]/10 text-[#66fcf1] border border-[#66fcf1]/20">
              <Key className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">API Keys & Credentials</h2>
              <p className="text-xs text-zinc-400">Values are stored locally and encrypted before network transfers.</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">Gemini API Key</label>
              <input 
                type="password" 
                value={config.GEMINI_API_KEY || ""} 
                onChange={e => updateConfig("GEMINI_API_KEY", e.target.value)} 
                className="modern-input" 
                placeholder="AI Studio Key (AIzaSy...)" 
              />
              <span className="text-[10px] text-zinc-500">Power deep research, script writing, and image generation.</span>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">WaveSpeed AI Key</label>
              <input 
                type="password" 
                value={config.WAVESPEED_API_KEY || ""} 
                onChange={e => updateConfig("WAVESPEED_API_KEY", e.target.value)} 
                className="modern-input" 
                placeholder="WaveSpeed token (wsk_...)" 
              />
              <span className="text-[10px] text-zinc-500">Enables LTX-Video, Flux-1.1, and elevenlabs audio models.</span>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">Serper Search API Key</label>
              <input 
                type="password" 
                value={config.SERPER_API_KEY || ""} 
                onChange={e => updateConfig("SERPER_API_KEY", e.target.value)} 
                className="modern-input" 
                placeholder="Google Search API token..." 
              />
              <span className="text-[10px] text-zinc-500">Used by autonomous agents for real-time web intelligence.</span>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">Pixabay Media API Key</label>
              <input 
                type="password" 
                value={config.PIXABAY_API_KEY || ""} 
                onChange={e => updateConfig("PIXABAY_API_KEY", e.target.value)} 
                className="modern-input" 
                placeholder="Pixabay key for royalty-free stock..." 
              />
              <span className="text-[10px] text-zinc-500">Stock footage B-roll retrieval engine.</span>
            </div>
          </div>
        </div>

        {/* Generation Engines Matrix */}
        <div className="glass-card p-6 md:p-8 space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-white/10">
            <div className="p-2 rounded-xl bg-[#38bdf8]/10 text-[#38bdf8] border border-[#38bdf8]/20">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wider uppercase">Active Engine Selection</h2>
              <p className="text-xs text-zinc-400">Choose the default backend engine for each content generation stage.</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">LLM Engine</label>
              <TabSelect options={["Gemini API", "WaveSpeed AI", "Ollama"]} value={config.TEXT_ENGINE || "Gemini API"} onChange={v => updateConfig("TEXT_ENGINE", v)} />
            </div>

            <div className="space-y-2">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">Image Engine</label>
              <TabSelect options={["Gemini API", "WaveSpeed AI"]} value={config.IMAGE_ENGINE || "Gemini API"} onChange={v => updateConfig("IMAGE_ENGINE", v)} />
            </div>

            <div className="space-y-2">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">Audio TTS Engine</label>
              <TabSelect options={["Gemini API", "WaveSpeed AI"]} value={config.AUDIO_ENGINE || "Gemini API"} onChange={v => updateConfig("AUDIO_ENGINE", v)} />
            </div>

            <div className="space-y-2">
              <label className="block text-[11px] font-bold text-zinc-300 uppercase tracking-wider">Video Engine</label>
              <TabSelect options={["WaveSpeed AI", "Vertex AI (Veo)"]} value={config.VIDEO_ENGINE || "WaveSpeed AI"} onChange={v => updateConfig("VIDEO_ENGINE", v)} />
            </div>
          </div>
          
          {/* Custom Models Sub-card */}
          <div className="mt-6 pt-6 border-t border-white/10 space-y-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#66fcf1]" />
              <h3 className="text-xs font-black text-white tracking-widest uppercase">WaveSpeed Model IDs</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-[11px] font-semibold text-zinc-400">Text Model (LLM)</label>
                <input type="text" value={config.WAVESPEED_TEXT_MODEL || ""} onChange={e => updateConfig("WAVESPEED_TEXT_MODEL", e.target.value)} className="modern-input" placeholder="meta-llama/llama-3.3-70b-instruct" />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] font-semibold text-zinc-400">Image Model</label>
                <input type="text" value={config.WAVESPEED_IMAGE_MODEL || ""} onChange={e => updateConfig("WAVESPEED_IMAGE_MODEL", e.target.value)} className="modern-input" placeholder="black-forest-labs/flux-1.1-pro-ultra" />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] font-semibold text-zinc-400">Video Model</label>
                <input type="text" value={config.WAVESPEED_VIDEO_MODEL || ""} onChange={e => updateConfig("WAVESPEED_VIDEO_MODEL", e.target.value)} className="modern-input" placeholder="wavespeed-ai/ltx-2.3-text-to-video" />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] font-semibold text-zinc-400">Audio/Voice Model</label>
                <input type="text" value={config.WAVESPEED_AUDIO_MODEL || ""} onChange={e => updateConfig("WAVESPEED_AUDIO_MODEL", e.target.value)} className="modern-input" placeholder="elevenlabs/text-to-speech" />
              </div>
            </div>
          </div>
        </div>

        {/* Support & Community Card */}
        <div className="glass-card p-6 md:p-8 border-[#FFDD00]/25 bg-gradient-to-br from-[#FFDD00]/5 via-black/40 to-transparent flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="p-3 rounded-2xl bg-[#FFDD00] text-black shadow-[0_0_15px_rgba(255,221,0,0.3)]">
              <Coffee className="h-6 w-6 stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Support the Creator & Open-Source Studio
                <Heart className="h-4 w-4 text-[#FFDD00] fill-[#FFDD00]" />
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                If AI Content Studio accelerates your workflows and generates views, consider buying me a coffee to support maintenance!
              </p>
            </div>
          </div>

          <a 
            href="https://buymeacoffee.com/naqash" 
            target="_blank" 
            rel="noopener noreferrer"
            className="px-5 py-2.5 rounded-xl bg-[#FFDD00] hover:bg-[#ffe338] text-black text-xs font-black tracking-wide shadow-[0_0_15px_rgba(255,221,0,0.25)] transition-all flex items-center gap-2 shrink-0"
          >
            <Coffee className="h-4 w-4 stroke-[2.5]" />
            buymeacoffee.com/naqash
          </a>
        </div>

        {/* Floating Bottom Bar */}
        <div className="flex justify-end pt-2">
          <button 
            type="submit" 
            disabled={contextStatus === "saving"}
            className="btn-primary !w-auto px-8 py-3.5 text-sm font-black shadow-[0_0_25px_rgba(102,252,241,0.35)]"
          >
            <Save className="h-4 w-4 stroke-[2.5]" /> Save All Settings
          </button>
        </div>
      </form>
    </div>
  );
}