"use client";

import { apiFetch } from "@/lib/api";

import { useState, useEffect } from "react";
import { Palette, Upload, Sparkles, Film, Trash2, Layers, Type, Volume2, Camera, Save, Loader2, Check } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

interface CaptionStyle {
  words_per_group: number;
  font_name: string;
  font_size: number;
  primary_color: string;
  highlight_color: string;
  position: string;
  animation: string;
}

interface EditingRules {
  avg_shot_duration_sec: number;
  cut_frequency_per_min: number;
  adaptive_cutting: boolean;
  semantic_zoom: boolean;
  broll_interval_sec: number;
  preserve_natural_pauses: boolean;
}

interface AudioStyle {
  duck_music_under_dialogue: boolean;
  music_volume_ducked: number;
  normalize_loudness: boolean;
  target_lufs: number;
}

interface StyleProfile {
  id: string;
  name: string;
  description?: string;
  target_duration: number;
  caption_style: CaptionStyle;
  editing: EditingRules;
  audio: AudioStyle;
}

async function loadStyles(): Promise<StyleProfile[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/styles`);
  if (!response.ok) throw new Error("Failed to load styles");
  return response.json();
}

export default function BrandStudioPage() {
  const [activeTab, setActiveTab] = useState<"brand" | "styles">("styles");
  
  // Brand Kit State
  const [channelName, setChannelName] = useState("Alpha Tech Studio");
  const [primaryColor, setPrimaryColor] = useState("#66FCF1");
  const [secondaryColor, setSecondaryColor] = useState("#45F3E5");
  const [fontFamily, setFontFamily] = useState("Outfit");
  const [watermarkPos, setWatermarkPos] = useState("Bottom-Right");
  const [watermarkOpacity, setWatermarkOpacity] = useState(80);
  const [logoFilename, setLogoFilename] = useState<string | null>(null);
  const [introFilename, setIntroFilename] = useState<string | null>(null);
  const [brandSaved, setBrandSaved] = useState(false);

  // Style Profiles State
  const [styles, setStyles] = useState<StyleProfile[]>([]);
  const [selectedStyleId, setSelectedStyleId] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [refVideoFile, setRefVideoFile] = useState<File | null>(null);
  const [refStyleName, setRefStyleName] = useState("");
  const [savingStyle, setSavingStyle] = useState(false);

  // Active Style Edit Form
  const [editingProfile, setEditingProfile] = useState<StyleProfile | null>(null);

  const fetchStyles = async () => {
    try {
      const data = await loadStyles();
      setStyles(data);
      if (data.length > 0 && !selectedStyleId) {
        setSelectedStyleId(data[0].id);
        setEditingProfile(data[0]);
      }
    } catch (e) {
      console.error("Failed to load styles", e);
    }
  };

  useEffect(() => {
    let active = true;
    loadStyles().then(data => {
      if (!active) return;
      setStyles(data);
      if (data.length > 0) {
        setSelectedStyleId(data[0].id);
        setEditingProfile(data[0]);
      }
    }).catch(error => console.error("Failed to load styles", error));
    apiFetch(`${API_BASE_URL}/api/config`)
      .then(res => (res.ok ? res.json() : null))
      .then(cfg => {
        if (!active || !cfg) return;
        if (cfg.CHANNEL_NAME) setChannelName(cfg.CHANNEL_NAME);
        if (cfg.BRAND_PRIMARY_COLOR) setPrimaryColor(cfg.BRAND_PRIMARY_COLOR);
        if (cfg.BRAND_SECONDARY_COLOR) setSecondaryColor(cfg.BRAND_SECONDARY_COLOR);
        if (cfg.BRAND_HEADING_FONT) setFontFamily(cfg.BRAND_HEADING_FONT);
        if (cfg.BRAND_LOGO_POSITION) setWatermarkPos(cfg.BRAND_LOGO_POSITION);
        if (typeof cfg.BRAND_WATERMARK_OPACITY === "number") setWatermarkOpacity(cfg.BRAND_WATERMARK_OPACITY);
        if (cfg.SOFTWARE_LOGO_PATH) setLogoFilename(cfg.SOFTWARE_LOGO_PATH.split(/[\\/]/).pop() || "logo.png");
        if (cfg.INTRO_VIDEO_PATH) setIntroFilename(cfg.INTRO_VIDEO_PATH.split(/[\\/]/).pop() || "intro.mp4");
      })
      .catch(e => console.error("Failed to load brand config:", e));
    return () => { active = false; };
  }, []);

  const handleSelectStyle = (profile: StyleProfile) => {
    setSelectedStyleId(profile.id);
    setEditingProfile(JSON.parse(JSON.stringify(profile)));
  };

  const handleAnalyzeReference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refVideoFile) {
      alert("Please upload a reference video file.");
      return;
    }
    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append("file", refVideoFile);
    formData.append("name", refStyleName || "Extracted Reference Style");

    try {
      const res = await apiFetch(`${API_BASE_URL}/api/styles/analyze-reference`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok && data.profile) {
        alert("Style pattern analyzed and extracted successfully!");
        setRefVideoFile(null);
        setRefStyleName("");
        await fetchStyles();
        handleSelectStyle(data.profile);
      } else {
        alert("Reference analysis failed: " + (data.detail || "Unknown error"));
      }
    } catch {
      alert("API request failed.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSaveEditedStyle = async () => {
    if (!editingProfile) return;
    setSavingStyle(true);
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/styles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editingProfile)
      });
      if (res.ok) {
        alert("Style profile saved successfully!");
        fetchStyles();
      } else {
        alert("Failed to save style profile.");
      }
    } catch {
      alert("API Error");
    } finally {
      setSavingStyle(false);
    }
  };

  const handleDeleteStyle = async (id: string) => {
    if (id.startsWith("preset_")) {
      alert("Default system presets cannot be deleted.");
      return;
    }
    if (!confirm("Are you sure you want to delete this custom style profile?")) return;

    try {
      const res = await apiFetch(`${API_BASE_URL}/api/styles/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        fetchStyles();
      } else {
        alert("Failed to delete style profile.");
      }
    } catch {
      alert("Error deleting style profile.");
    }
  };

  const handleUploadBrandAsset = async (assetType: "logo" | "intro", file: File | null) => {
    if (!file) return;
    if (assetType === "logo") setLogoFilename(file.name);
    else setIntroFilename(file.name);

    const formData = new FormData();
    formData.append("file", file);
    try {
      await apiFetch(`${API_BASE_URL}/api/brand/upload?type=${assetType}`, {
        method: "POST",
        body: formData
      });
    } catch (e) {
      console.error(`Failed to upload ${assetType}`, e);
    }
  };

  const handleSaveBrandKit = async () => {
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          CHANNEL_NAME: channelName,
          BRAND_PRIMARY_COLOR: primaryColor,
          BRAND_SECONDARY_COLOR: secondaryColor,
          BRAND_HEADING_FONT: fontFamily,
          BRAND_LOGO_POSITION: watermarkPos,
          BRAND_WATERMARK_OPACITY: watermarkOpacity,
        })
      });
      if (res.ok) {
        setBrandSaved(true);
        setTimeout(() => setBrandSaved(false), 3000);
      } else {
        alert("Failed to save Brand Identity Kit.");
      }
    } catch {
      alert("Error connecting to server while saving Brand Identity Kit.");
    }
  };

  return (
    <div className="max-w-[1500px] mx-auto animate-in fade-in duration-500 pb-16 flex flex-col min-h-[calc(100vh-6rem)]">
      
      {/* Page Title & Tab Selector */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
            <Palette className="h-8 w-8 text-[#66fcf1]" /> Brand Kit & Style Studio
          </h1>
          <p className="text-zinc-400 mt-1">
            Engineered style profiles, reference video pacing extraction, and universal brand identity kits.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex bg-black/60 p-1.5 rounded-xl border border-white/10 self-start md:self-auto">
          <button 
            onClick={() => setActiveTab("styles")}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "styles" 
                ? "bg-[#66fcf1] text-black shadow-[0_0_15px_rgba(102,252,241,0.25)]" 
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Film className="h-4 w-4" /> Editing Style Profiles
          </button>
          <button 
            onClick={() => setActiveTab("brand")}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "brand" 
                ? "bg-[#66fcf1] text-black shadow-[0_0_15px_rgba(102,252,241,0.25)]" 
                : "text-zinc-400 hover:text-white"
            }`}
          >
            <Sparkles className="h-4 w-4" /> Brand Identity Kit
          </button>
        </div>
      </div>

      {/* TAB 1: Editing Style Profiles */}
      {activeTab === "styles" && (
        <div className="space-y-8">
          
          {/* Top Panel: Reference Video Cloner */}
          <div className="glass-card p-6 border border-white/10 shadow-2xl">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-2">
              <Camera className="h-4 w-4 text-[#66fcf1]" /> Clone Editing Style from Reference Video
            </h2>
            <p className="text-xs text-zinc-400 mb-6">
              Upload any high-performing creator video (e.g. MrBeast, Alex Hormozi, Vox). OpenCV analyzes cut rhythms, average shot lengths, and caption animations to build a custom style profile.
            </p>

            <form onSubmit={handleAnalyzeReference} className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
              <div className="md:col-span-4">
                <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5">
                  Style Profile Name
                </label>
                <input 
                  type="text"
                  value={refStyleName}
                  onChange={e => setRefStyleName(e.target.value)}
                  placeholder="e.g. Vox Explainer Fast-Paced"
                  className="modern-input text-xs"
                />
              </div>

              <div className="md:col-span-5">
                <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5">
                  Reference Video (.mp4, .mov)
                </label>
                <input 
                  type="file" 
                  accept="video/*" 
                  onChange={e => setRefVideoFile(e.target.files?.[0] || null)}
                  className="modern-input text-xs file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-bold file:bg-[#66fcf1] file:text-black cursor-pointer"
                />
              </div>

              <div className="md:col-span-3">
                <button 
                  type="submit"
                  disabled={isAnalyzing}
                  className="w-full py-2.5 bg-[#66fcf1] hover:bg-[#45f3e5] text-black font-bold rounded-xl text-xs transition-all shadow-[0_0_15px_rgba(102,252,241,0.2)] flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Analyzing Pacing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" /> Extract Style Profile
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Main Grid: Profiles List (Left) & Customizer Inspector (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            {/* Style Profiles List */}
            <div className="lg:col-span-4 space-y-4">
              <h2 className="text-xs font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <Layers className="h-4 w-4 text-[#66fcf1]" /> Available Style Profiles ({styles.length})
              </h2>

              <div className="space-y-3">
                {styles.map(p => (
                  <div 
                    key={p.id}
                    onClick={() => handleSelectStyle(p)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                      selectedStyleId === p.id 
                        ? "bg-[#66fcf1]/10 border-[#66fcf1] shadow-[0_0_15px_rgba(102,252,241,0.15)]" 
                        : "bg-black/40 border-white/5 hover:border-white/20 hover:bg-white/5"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-white text-sm flex items-center gap-2">
                        {p.name}
                        {p.id.startsWith("preset_") && (
                          <span className="text-[10px] px-2 py-0.5 bg-white/10 text-zinc-400 rounded-md uppercase font-mono">
                            Preset
                          </span>
                        )}
                      </h3>

                      {!p.id.startsWith("preset_") && (
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleDeleteStyle(p.id); }}
                          className="text-zinc-500 hover:text-red-400 p-1 transition-colors"
                          title="Delete custom profile"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>

                    <p className="text-xs text-zinc-400 mt-2 line-clamp-2">
                      {p.description || "Custom style profile"}
                    </p>

                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      <span className="text-[10px] bg-white/5 text-zinc-300 px-2 py-0.5 rounded font-mono">
                        ~{p.editing?.avg_shot_duration_sec ?? 3}s / shot
                      </span>
                      <span className="text-[10px] bg-white/5 text-zinc-300 px-2 py-0.5 rounded font-mono">
                        {p.editing?.cut_frequency_per_min ?? 20} cuts/min
                      </span>
                      <span className="text-[10px] bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded">
                        {p.caption_style?.animation ?? "pop"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Selected Style Inspector & Editor */}
            <div className="lg:col-span-8">
              {editingProfile ? (
                <div className="glass-card p-6 border border-white/10 space-y-6">
                  
                  {/* Header & Save Action */}
                  <div className="flex items-center justify-between border-b border-white/10 pb-4">
                    <div>
                      <h2 className="text-xl font-black text-white">{editingProfile.name}</h2>
                      <p className="text-xs text-zinc-400 mt-1">Configure pacing, caption typography, and audio mastering.</p>
                    </div>

                    <button 
                      onClick={handleSaveEditedStyle}
                      disabled={savingStyle}
                      className="px-5 py-2.5 bg-[#66fcf1] hover:bg-[#45f3e5] text-black font-black rounded-xl text-xs flex items-center gap-2 shadow-[0_0_15px_rgba(102,252,241,0.25)] transition-all"
                    >
                      <Save className="h-4 w-4" /> Save Style Parameters
                    </button>
                  </div>

                  {/* Section 1: Visual Pacing & Editing Rules */}
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold text-[#66fcf1] uppercase tracking-wider flex items-center gap-2">
                      <Film className="h-4 w-4" /> Shot Pacing & Camera Dynamics
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Avg Shot Duration (Seconds)
                        </label>
                        <input 
                          type="number"
                          step="0.1"
                          value={editingProfile.editing.avg_shot_duration_sec}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            editing: { ...editingProfile.editing, avg_shot_duration_sec: parseFloat(e.target.value) || 2.5 }
                          })}
                          className="modern-input text-xs"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Cuts Frequency (Per Minute)
                        </label>
                        <input 
                          type="number"
                          step="1"
                          value={editingProfile.editing.cut_frequency_per_min}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            editing: { ...editingProfile.editing, cut_frequency_per_min: parseFloat(e.target.value) || 20 }
                          })}
                          className="modern-input text-xs"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          B-Roll Interval (Seconds)
                        </label>
                        <input 
                          type="number"
                          step="0.5"
                          value={editingProfile.editing.broll_interval_sec}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            editing: { ...editingProfile.editing, broll_interval_sec: parseFloat(e.target.value) || 5.0 }
                          })}
                          className="modern-input text-xs"
                        />
                      </div>
                    </div>

                    <div className="flex items-center gap-6 pt-2">
                      <label className="flex items-center gap-2 text-xs text-white cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={editingProfile.editing.semantic_zoom}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            editing: { ...editingProfile.editing, semantic_zoom: e.target.checked }
                          })}
                          className="accent-[#66fcf1]"
                        />
                        Dynamic Punch-In / Semantic Zooms
                      </label>

                      <label className="flex items-center gap-2 text-xs text-white cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={editingProfile.editing.preserve_natural_pauses}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            editing: { ...editingProfile.editing, preserve_natural_pauses: e.target.checked }
                          })}
                          className="accent-[#66fcf1]"
                        />
                        Preserve Natural Breath Pauses
                      </label>
                    </div>
                  </div>

                  {/* Section 2: Captions & Typography */}
                  <div className="space-y-4 pt-4 border-t border-white/10">
                    <h3 className="text-xs font-bold text-[#66fcf1] uppercase tracking-wider flex items-center gap-2">
                      <Type className="h-4 w-4" /> Subtitle & Caption Design
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Words Per Group
                        </label>
                        <select 
                          value={editingProfile.caption_style.words_per_group}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            caption_style: { ...editingProfile.caption_style, words_per_group: parseInt(e.target.value) }
                          })}
                          className="modern-select text-xs py-2"
                        >
                          <option className="bg-black" value={1}>1 Word (High Velocity)</option>
                          <option className="bg-black" value={2}>2 Words (TikTok standard)</option>
                          <option className="bg-black" value={3}>3 Words (Hormozi style)</option>
                          <option className="bg-black" value={4}>4 Words (Documentary)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Font Family
                        </label>
                        <input 
                          type="text"
                          value={editingProfile.caption_style.font_name}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            caption_style: { ...editingProfile.caption_style, font_name: e.target.value }
                          })}
                          className="modern-input text-xs"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Highlight Color
                        </label>
                        <div className="flex items-center gap-2">
                          <input 
                            type="color"
                            value={editingProfile.caption_style.highlight_color}
                            onChange={e => setEditingProfile({
                              ...editingProfile,
                              caption_style: { ...editingProfile.caption_style, highlight_color: e.target.value }
                            })}
                            className="h-8 w-10 bg-transparent cursor-pointer rounded border border-white/10"
                          />
                          <span className="font-mono text-xs text-white uppercase">{editingProfile.caption_style.highlight_color}</span>
                        </div>
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Animation Type
                        </label>
                        <select 
                          value={editingProfile.caption_style.animation}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            caption_style: { ...editingProfile.caption_style, animation: e.target.value }
                          })}
                          className="modern-select text-xs py-2"
                        >
                          <option className="bg-black" value="pop">Pop (Active highlight)</option>
                          <option className="bg-black" value="bounce">Bounce (Dynamic)</option>
                          <option className="bg-black" value="fade">Smooth Fade</option>
                          <option className="bg-black" value="none">Static</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Section 3: Audio Mastering & Music Ducking */}
                  <div className="space-y-4 pt-4 border-t border-white/10">
                    <h3 className="text-xs font-bold text-[#66fcf1] uppercase tracking-wider flex items-center gap-2">
                      <Volume2 className="h-4 w-4" /> Audio Mastering & Loudness Targets
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Target Loudness (LUFS)
                        </label>
                        <select 
                          value={editingProfile.audio.target_lufs}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            audio: { ...editingProfile.audio, target_lufs: parseFloat(e.target.value) }
                          })}
                          className="modern-select text-xs py-2"
                        >
                          <option className="bg-black" value={-14.0}>-14.0 LUFS (YouTube / TikTok Standard)</option>
                          <option className="bg-black" value={-16.0}>-16.0 LUFS (Podcast / Apple Standard)</option>
                          <option className="bg-black" value={-13.0}>-13.0 LUFS (Punchy Commercial)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                          Music Ducking Volume
                        </label>
                        <input 
                          type="number"
                          step="0.01"
                          min="0.01"
                          max="0.5"
                          value={editingProfile.audio.music_volume_ducked}
                          onChange={e => setEditingProfile({
                            ...editingProfile,
                            audio: { ...editingProfile.audio, music_volume_ducked: parseFloat(e.target.value) || 0.08 }
                          })}
                          className="modern-input text-xs"
                        />
                      </div>

                      <div className="flex items-center pt-5">
                        <label className="flex items-center gap-2 text-xs text-white cursor-pointer">
                          <input 
                            type="checkbox"
                            checked={editingProfile.audio.normalize_loudness}
                            onChange={e => setEditingProfile({
                              ...editingProfile,
                              audio: { ...editingProfile.audio, normalize_loudness: e.target.checked }
                            })}
                            className="accent-[#66fcf1]"
                          />
                          Broadcast EBU R128 Loudnorm Enabled
                        </label>
                      </div>
                    </div>
                  </div>

                </div>
              ) : (
                <div className="glass-card p-12 text-center text-zinc-500">
                  Select a style profile on the left to view and modify its editing parameters.
                </div>
              )}
            </div>

          </div>

        </div>
      )}

      {/* TAB 2: Brand Identity Kit */}
      {activeTab === "brand" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Form: Colors, Typography & Assets */}
          <div className="lg:col-span-7 space-y-6">
            <div className="glass-card p-6 border border-white/10 space-y-6">
              
              <div className="border-b border-white/10 pb-4">
                <h2 className="text-lg font-bold text-white">Global Brand Parameters</h2>
                <p className="text-xs text-zinc-400 mt-1">Applied across automated short renders, explainers, and video exports.</p>
              </div>

              {/* Channel Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                    Channel / Studio Name
                  </label>
                  <input 
                    type="text" 
                    value={channelName} 
                    onChange={e => setChannelName(e.target.value)}
                    className="modern-input text-sm"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                    Primary Font Family
                  </label>
                  <select 
                    value={fontFamily}
                    onChange={e => setFontFamily(e.target.value)}
                    className="modern-select text-sm py-2"
                  >
                    <option className="bg-black" value="Outfit">Outfit (Modern)</option>
                    <option className="bg-black" value="Inter">Inter (Clean)</option>
                    <option className="bg-black" value="Montserrat">Montserrat (Cinematic)</option>
                    <option className="bg-black" value="Impact">Impact (Viral)</option>
                  </select>
                </div>
              </div>

              {/* Brand Colors */}
              <div className="space-y-3 pt-2">
                <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                  Brand Color Palette
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-black/40 rounded-xl border border-white/5 flex items-center justify-between">
                    <div>
                      <p className="text-xs text-zinc-400">Primary Accent</p>
                      <p className="font-mono text-sm text-white font-bold">{primaryColor}</p>
                    </div>
                    <input 
                      type="color" 
                      value={primaryColor} 
                      onChange={e => setPrimaryColor(e.target.value)}
                      className="h-10 w-12 bg-transparent cursor-pointer rounded border border-white/10"
                    />
                  </div>

                  <div className="p-3 bg-black/40 rounded-xl border border-white/5 flex items-center justify-between">
                    <div>
                      <p className="text-xs text-zinc-400">Secondary Accent</p>
                      <p className="font-mono text-sm text-white font-bold">{secondaryColor}</p>
                    </div>
                    <input 
                      type="color" 
                      value={secondaryColor} 
                      onChange={e => setSecondaryColor(e.target.value)}
                      className="h-10 w-12 bg-transparent cursor-pointer rounded border border-white/10"
                    />
                  </div>
                </div>
              </div>

              {/* Watermark Placement */}
              <div className="space-y-4 pt-2">
                <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                  Watermark & Bug Position
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"].map(pos => (
                    <button 
                      key={pos}
                      type="button"
                      onClick={() => setWatermarkPos(pos)}
                      className={`py-2 px-3 rounded-lg text-xs font-bold border transition-all ${
                        watermarkPos === pos 
                          ? "bg-[#66fcf1] text-black border-[#66fcf1]" 
                          : "bg-white/5 text-zinc-300 border-white/5 hover:bg-white/10"
                      }`}
                    >
                      {pos}
                    </button>
                  ))}
                </div>

                <div>
                  <div className="flex justify-between text-xs text-zinc-400 mb-1">
                    <span>Watermark Opacity</span>
                    <span className="font-mono text-white">{watermarkOpacity}%</span>
                  </div>
                  <input 
                    type="range" 
                    min="10" 
                    max="100" 
                    value={watermarkOpacity}
                    onChange={e => setWatermarkOpacity(parseInt(e.target.value))}
                    className="w-full accent-[#66fcf1] cursor-pointer"
                  />
                </div>
              </div>

              {/* Brand Asset Uploads */}
              <div className="space-y-4 pt-2">
                <label className="block text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                  Brand Media Assets
                </label>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border border-dashed border-white/15 p-4 rounded-xl flex flex-col items-center justify-center text-center hover:bg-white/5 transition-all cursor-pointer relative">
                    <input 
                      type="file" 
                      accept="image/png,image/svg+xml" 
                      onChange={e => handleUploadBrandAsset("logo", e.target.files?.[0] || null)}
                      className="absolute inset-0 opacity-0 cursor-pointer"
                    />
                    <Upload className="h-5 w-5 text-[#66fcf1] mb-2" />
                    <p className="text-xs font-bold text-white">{logoFilename || "Upload PNG Logo / Watermark"}</p>
                    <p className="text-[10px] text-zinc-500 mt-1">Transparent PNG (max 2MB)</p>
                  </div>

                  <div className="border border-dashed border-white/15 p-4 rounded-xl flex flex-col items-center justify-center text-center hover:bg-white/5 transition-all cursor-pointer relative">
                    <input 
                      type="file" 
                      accept="video/mp4" 
                      onChange={e => handleUploadBrandAsset("intro", e.target.files?.[0] || null)}
                      className="absolute inset-0 opacity-0 cursor-pointer"
                    />
                    <Film className="h-5 w-5 text-purple-400 mb-2" />
                    <p className="text-xs font-bold text-white">{introFilename || "Upload Stinger Intro Video"}</p>
                    <p className="text-[10px] text-zinc-500 mt-1">2-3 sec MP4 animation</p>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-white/10">
                <button 
                  onClick={handleSaveBrandKit}
                  className="w-full py-3.5 bg-[#66fcf1] hover:bg-[#45f3e5] text-black font-black rounded-xl text-xs flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(102,252,241,0.25)] transition-all"
                >
                  {brandSaved ? (
                    <>
                      <Check className="h-4 w-4" /> Brand Kit Saved!
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" /> Save Brand Identity Kit
                    </>
                  )}
                </button>
              </div>

            </div>
          </div>

          {/* Right Live Preview: Studio Card Mockup */}
          <div className="lg:col-span-5">
            <div className="glass-card p-6 border border-white/10 space-y-4">
              <h2 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                Live Brand Preview
              </h2>

              {/* 9:16 Short Preview Card */}
              <div className="aspect-[9/16] max-w-[280px] mx-auto bg-black rounded-2xl border border-white/10 overflow-hidden relative shadow-2xl flex flex-col justify-between p-4">
                
                {/* Watermark in corner */}
                <div className={`absolute p-3 ${
                  watermarkPos === "Top-Left" ? "top-0 left-0" :
                  watermarkPos === "Top-Right" ? "top-0 right-0" :
                  watermarkPos === "Bottom-Left" ? "bottom-0 left-0" :
                  "bottom-0 right-0"
                }`}>
                  <div 
                    className="px-2 py-1 bg-black/60 rounded text-[10px] font-bold text-white border border-white/20"
                    style={{ opacity: watermarkOpacity / 100 }}
                  >
                    {logoFilename ? logoFilename.split('.')[0] : channelName}
                  </div>
                </div>

                {/* Simulated Visual Video Frame */}
                <div className="flex-1 flex flex-col items-center justify-center text-center">
                  <div className="w-12 h-12 rounded-full border border-white/20 flex items-center justify-center mb-3" style={{ borderColor: primaryColor }}>
                    <Sparkles className="h-6 w-6" style={{ color: primaryColor }} />
                  </div>
                  <span className="text-[10px] tracking-widest uppercase font-mono text-zinc-400">AI Preview</span>
                </div>

                {/* Simulated Subtitle Pop */}
                <div className="mb-8 text-center">
                  <span className="text-base font-black px-2 py-1 rounded" style={{ 
                    color: "#FFFFFF",
                    fontFamily: fontFamily,
                    textShadow: `0 0 10px ${primaryColor}` 
                  }}>
                    THIS IS <span style={{ color: primaryColor }}>REVOLUTIONARY</span>
                  </span>
                </div>

              </div>

              <div className="text-center text-xs text-zinc-500 pt-2">
                Preview updates live as you adjust colors, watermark position, and typography.
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}