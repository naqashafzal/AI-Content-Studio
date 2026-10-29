"use client";

import { apiFetch } from "@/lib/api";

import { useState, useEffect } from "react";
import { Film, Upload, CheckCircle2, Play, MonitorPlay, FileText, Loader2, Tag, Info, Smartphone, Download, Link2 } from "lucide-react";
import { API_BASE_URL, getMediaUrl } from "@/lib/api";

function YoutubeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
    </svg>
  );
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="20" x="2" y="2" rx="5" ry="5"/>
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/>
    </svg>
  );
}

interface PublishingProject {
  id: string;
  name: string;
  video_path: string;
  seo?: { title?: string; description?: string; tags?: string };
}

interface PlatformStatus {
  connected: boolean;
  expired?: boolean;
  updated_at?: string | null;
}

export default function PublishPage() {
  const [projects, setProjects] = useState<PublishingProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<PublishingProject | null>(null);
  
  // Edit Form State
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [status, setStatus] = useState("idle");
  const [bundleReady, setBundleReady] = useState(false);

  const [socialStatus, setSocialStatus] = useState<Record<string, PlatformStatus>>({
    youtube: { connected: false },
    tiktok: { connected: false },
    instagram: { connected: false }
  });
  const [selectedPlatforms, setSelectedPlatforms] = useState({ youtube: true, tiktok: false, instagram: false });

  useEffect(() => {
    apiFetch(`${API_BASE_URL}/api/publish/library`)
      .then(res => res.json())
      .then(data => {
        setProjects(data.projects || []);
      })
      .catch(err => console.error(err));
      
    apiFetch(`${API_BASE_URL}/api/social/status`)
      .then(res => res.json())
      .then(data => {
        if (data) setSocialStatus(data);
      })
      .catch(err => console.error(err));
  }, []);

  const selectProject = (proj: PublishingProject) => {
    setSelectedProject(proj);
    setTitle(proj.seo?.title || "");
    setDescription(proj.seo?.description || "");
    setTags(proj.seo?.tags || "");
    setStatus("idle");
    setBundleReady(false);
  };

  const handleConnectYouTube = async () => {
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/social/youtube/auth`);
      const data = await res.json();
      if (data.auth_url) {
        window.open(data.auth_url, "_blank");
      } else {
        alert(data.message || "Please configure YOUTUBE_CLIENT_ID in Settings or place client_secrets.json in the project root.");
      }
    } catch {
      alert("Failed to initiate YouTube OAuth flow.");
    }
  };

  const handleExportBundle = async () => {
    if (!selectedProject) return;
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/social/export-bundle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: selectedProject.video_path,
          title,
          description,
          tags,
          platform: "all"
        })
      });
      if (res.ok) {
        setBundleReady(true);
      } else {
        const err = await res.json();
        alert("Export Bundle failed: " + (err.detail || "Unknown error"));
      }
    } catch {
      alert("Failed to create export bundle.");
    }
  };

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;
    
    setStatus("publishing");
    
    try {
      const payload = {
        video_path: selectedProject.video_path,
        title,
        description,
        tags,
        privacy_status: "private"
      };
      
      const res = await apiFetch(`${API_BASE_URL}/api/publish/youtube`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (!res.ok) {
        alert("Upload Failed: " + (data.detail || "Unknown error"));
        setStatus("idle");
      } else {
        setStatus("published");
      }
    } catch {
      alert("Failed to connect to API.");
      setStatus("idle");
    }
  };

  const isYoutubeConnected = Boolean(socialStatus.youtube?.connected);
  const isTiktokConnected = Boolean(socialStatus.tiktok?.connected);
  const isInstagramConnected = Boolean(socialStatus.instagram?.connected);

  return (
    <div className="max-w-[1400px] mx-auto animate-in fade-in duration-500 flex flex-col h-[calc(100vh-6rem)]">
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Publish & Distribution</h1>
          <p className="text-zinc-400 mt-1">Manage your generated content and publish directly to social channels.</p>
        </div>
        {!isYoutubeConnected && (
          <button
            type="button"
            onClick={handleConnectYouTube}
            className="px-4 py-2 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 text-xs font-bold flex items-center gap-2 self-start sm:self-auto transition-all"
          >
            <Link2 className="h-4 w-4" /> Connect YouTube OAuth
          </button>
        )}
      </div>
      
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
        {/* Left Side: Library Grid */}
        <div className="lg:col-span-7 xl:col-span-8 flex flex-col overflow-hidden">
          <div className="glass-card p-6 flex-1 flex flex-col overflow-hidden">
            <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3 mb-6">
              Content Library ({projects.length})
            </h2>
            
            <div className="flex-1 overflow-y-auto pr-2 space-y-4 pb-12">
              {projects.length === 0 ? (
                <div className="h-full flex items-center justify-center text-zinc-500 flex-col gap-4">
                  <Film className="h-12 w-12 opacity-20" />
                  <p>No generated videos found in workspace.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {projects.map((proj) => (
                    <div 
                      key={proj.id} 
                      onClick={() => selectProject(proj)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-4 ${
                        selectedProject?.id === proj.id 
                          ? 'bg-white/10 border-white/30 shadow-[0_0_15px_rgba(255,255,255,0.05)]' 
                          : 'bg-transparent border-white/10 hover:border-white/20 hover:bg-white/5'
                      }`}
                    >
                      <div className="aspect-video bg-black rounded-lg border border-white/10 flex items-center justify-center relative overflow-hidden group">
                        <Play className="h-8 w-8 text-white/50 group-hover:text-white transition-colors" />
                        <div className="absolute bottom-2 right-2 bg-black/80 backdrop-blur-md px-2 py-1 rounded text-[10px] font-bold text-white border border-white/10">
                          READY
                        </div>
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white line-clamp-1">{proj.name}</h3>
                        <p className="text-xs text-zinc-500 mt-1 line-clamp-1">{proj.seo?.title || "No SEO Data"}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Right Side: Edit & Publish Panel */}
        <div className="lg:col-span-5 xl:col-span-4 overflow-y-auto pb-12 pr-2">
          {selectedProject ? (
            <div className="glass-card p-6 space-y-6">
              <h2 className="text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 pb-3 flex items-center justify-between">
                Publish settings
                <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded text-[10px]">Draft</span>
              </h2>
              
              <div className="aspect-video bg-black rounded-xl border border-white/10 overflow-hidden">
                <video 
                  src={getMediaUrl(selectedProject.video_path)}
                  controls 
                  className="w-full h-full object-contain"
                />
              </div>

              <form onSubmit={handlePublish} className="space-y-5">
                <div>
                  <label className="flex items-center gap-2 text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">
                    <FileText className="h-3.5 w-3.5" /> Video Title
                  </label>
                  <input 
                    type="text" 
                    value={title} 
                    onChange={e => setTitle(e.target.value)} 
                    className="modern-input !text-lg !font-bold" 
                    required 
                  />
                </div>
                
                <div>
                  <label className="flex items-center justify-between text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">
                    <span className="flex items-center gap-2"><Info className="h-3.5 w-3.5" /> Description</span>
                    <span>{description.length} chars</span>
                  </label>
                  <textarea 
                    value={description} 
                    onChange={e => setDescription(e.target.value)} 
                    className="modern-input min-h-[160px] resize-y" 
                    required 
                  />
                </div>
                
                <div>
                  <label className="flex items-center gap-2 text-xs font-bold text-zinc-500 mb-2 uppercase tracking-wider">
                    <Tag className="h-3.5 w-3.5" /> Tags (Comma separated)
                  </label>
                  <input 
                    type="text" 
                    value={tags} 
                    onChange={e => setTags(e.target.value)} 
                    className="modern-input" 
                  />
                </div>
                
                <div className="pt-2">
                   <label className="flex items-center gap-2 text-xs font-bold text-zinc-500 mb-3 uppercase tracking-wider">
                      Select Platforms
                   </label>
                   <div className="grid grid-cols-3 gap-3">
                      <button type="button" onClick={() => setSelectedPlatforms(p => ({...p, youtube: !p.youtube}))} className={`flex flex-col items-center gap-2 p-3 rounded-lg border ${selectedPlatforms.youtube ? 'bg-red-500/20 border-red-500/50 text-white' : 'bg-white/5 border-white/10 text-zinc-500 hover:bg-white/10'}`}>
                         <YoutubeIcon className="h-6 w-6" />
                         <span className="text-[10px] font-bold">YouTube</span>
                         {isYoutubeConnected ? <span className="text-[8px] text-emerald-400 bg-emerald-500/20 px-1.5 rounded-sm">Connected</span> : <span className="text-[8px] text-zinc-500">Not Connected</span>}
                      </button>
                      <button type="button" onClick={() => setSelectedPlatforms(p => ({...p, tiktok: !p.tiktok}))} className={`flex flex-col items-center gap-2 p-3 rounded-lg border ${selectedPlatforms.tiktok ? 'bg-zinc-800 border-zinc-500 text-white' : 'bg-white/5 border-white/10 text-zinc-500 hover:bg-white/10'}`}>
                         <Smartphone className="h-6 w-6" />
                         <span className="text-[10px] font-bold">TikTok</span>
                         {isTiktokConnected ? <span className="text-[8px] text-emerald-400 bg-emerald-500/20 px-1.5 rounded-sm">Connected</span> : <span className="text-[8px] text-zinc-500">Bundle Export</span>}
                      </button>
                      <button type="button" onClick={() => setSelectedPlatforms(p => ({...p, instagram: !p.instagram}))} className={`flex flex-col items-center gap-2 p-3 rounded-lg border ${selectedPlatforms.instagram ? 'bg-pink-500/20 border-pink-500/50 text-white' : 'bg-white/5 border-white/10 text-zinc-500 hover:bg-white/10'}`}>
                         <InstagramIcon className="h-6 w-6" />
                         <span className="text-[10px] font-bold">Instagram</span>
                         {isInstagramConnected ? <span className="text-[8px] text-emerald-400 bg-emerald-500/20 px-1.5 rounded-sm">Connected</span> : <span className="text-[8px] text-zinc-500">Bundle Export</span>}
                      </button>
                   </div>
                </div>

                <div className="pt-4 border-t border-white/10 space-y-3">
                  {status === "publishing" ? (
                    <button type="button" disabled className="w-full py-3 bg-white/20 text-white font-bold rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                      <Loader2 className="h-5 w-5 animate-spin" /> Publishing to YouTube...
                    </button>
                  ) : status === "published" ? (
                    <div className="w-full py-3 bg-emerald-500/20 text-emerald-400 font-bold rounded-xl flex items-center justify-center gap-2 border border-emerald-500/30">
                      <CheckCircle2 className="h-5 w-5" /> Published Successfully!
                    </div>
                  ) : (
                    <button type="submit" className="w-full py-3 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 transition-all shadow-[0_0_15px_rgba(5,150,105,0.3)] hover:shadow-[0_0_25px_rgba(5,150,105,0.5)] flex items-center justify-center gap-2">
                      <MonitorPlay className="h-5 w-5" /> Publish to YouTube
                    </button>
                  )}

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleExportBundle}
                      className="flex-1 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-200 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all"
                    >
                      <FileText className="h-4 w-4" /> {bundleReady ? "Metadata Bundle Saved!" : "Prepare Export Bundle"}
                    </button>
                    <a
                      href={getMediaUrl(selectedProject.video_path)}
                      download
                      className="py-2.5 px-4 bg-white/10 hover:bg-white/20 border border-white/15 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all"
                    >
                      <Download className="h-4 w-4" /> MP4
                    </a>
                  </div>
                </div>
              </form>
            </div>
          ) : (
            <div className="glass-card p-6 h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50 min-h-[400px]">
              <Upload className="h-10 w-10 text-zinc-500" />
              <div>
                <p className="text-sm font-bold text-white">No Project Selected</p>
                <p className="text-xs text-zinc-500 mt-1">Select a video from the library to edit SEO and publish.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
