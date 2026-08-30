"use client";

import { useState, useEffect } from "react";
import { Film, Upload, CheckCircle2, Play, MonitorPlay, FileText, Loader2, Tag, Info, Youtube, Instagram, Smartphone } from "lucide-react";

export default function PublishPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  
  // Edit Form State
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [status, setStatus] = useState("idle");

  const [socialStatus, setSocialStatus] = useState({ youtube: false, tiktok: false, instagram: false });
  const [selectedPlatforms, setSelectedPlatforms] = useState({ youtube: true, tiktok: false, instagram: false });

  useEffect(() => {
    fetch("http://localhost:8008/api/publish/library")
      .then(res => res.json())
      .then(data => {
        setProjects(data.projects || []);
      })
      .catch(err => console.error(err));
      
    fetch("http://localhost:8008/api/social/status")
      .then(res => res.json())
      .then(data => setSocialStatus(data))
      .catch(err => console.error(err));
  }, []);

  const selectProject = (proj: any) => {
    setSelectedProject(proj);
    setTitle(proj.seo?.title || "");
    setDescription(proj.seo?.description || "");
    setTags(proj.seo?.tags || "");
    setStatus("idle");
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
        privacy_status: "private" // Default to private for safety
      };
      
      const res = await fetch("http://localhost:8008/api/publish/youtube", {
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
    } catch (err) {
      alert("Failed to connect to API.");
      setStatus("idle");
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto animate-in fade-in duration-500 flex flex-col h-[calc(100vh-6rem)]">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Publish & Distribution</h1>
        <p className="text-zinc-400 mt-1">Manage your generated content and publish directly to social channels.</p>
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
                {/* We use a simple video tag to preview the generated video directly from the backend via the media route we need to make sure exists */}
                <video 
                  src={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(selectedProject.video_path)}`}
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
                    className="modern-input min-h-[200px] resize-y" 
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
                
                <div className="pt-4">
                   <label className="flex items-center gap-2 text-xs font-bold text-zinc-500 mb-3 uppercase tracking-wider">
                      Select Platforms
                   </label>
                   <div className="grid grid-cols-3 gap-3">
                      <button type="button" onClick={() => setSelectedPlatforms(p => ({...p, youtube: !p.youtube}))} className={`flex flex-col items-center gap-2 p-3 rounded-lg border ${selectedPlatforms.youtube ? 'bg-red-500/20 border-red-500/50 text-white' : 'bg-white/5 border-white/10 text-zinc-500 hover:bg-white/10'}`}>
                         <Youtube className="h-6 w-6" />
                         <span className="text-[10px] font-bold">YouTube</span>
                         {socialStatus.youtube ? <span className="text-[8px] text-emerald-400 bg-emerald-500/20 px-1.5 rounded-sm">Connected</span> : <span className="text-[8px] text-zinc-500">Not Connected</span>}
                      </button>
                      <button type="button" onClick={() => setSelectedPlatforms(p => ({...p, tiktok: !p.tiktok}))} className={`flex flex-col items-center gap-2 p-3 rounded-lg border ${selectedPlatforms.tiktok ? 'bg-zinc-800 border-zinc-500 text-white' : 'bg-white/5 border-white/10 text-zinc-500 hover:bg-white/10'}`}>
                         <Smartphone className="h-6 w-6" />
                         <span className="text-[10px] font-bold">TikTok</span>
                         {socialStatus.tiktok ? <span className="text-[8px] text-emerald-400 bg-emerald-500/20 px-1.5 rounded-sm">Connected</span> : <span className="text-[8px] text-zinc-500">Not Connected</span>}
                      </button>
                      <button type="button" onClick={() => setSelectedPlatforms(p => ({...p, instagram: !p.instagram}))} className={`flex flex-col items-center gap-2 p-3 rounded-lg border ${selectedPlatforms.instagram ? 'bg-pink-500/20 border-pink-500/50 text-white' : 'bg-white/5 border-white/10 text-zinc-500 hover:bg-white/10'}`}>
                         <Instagram className="h-6 w-6" />
                         <span className="text-[10px] font-bold">Instagram</span>
                         {socialStatus.instagram ? <span className="text-[8px] text-emerald-400 bg-emerald-500/20 px-1.5 rounded-sm">Connected</span> : <span className="text-[8px] text-zinc-500">Not Connected</span>}
                      </button>
                   </div>
                </div>

                <div className="pt-4 border-t border-white/10">
                  {status === "publishing" ? (
                    <button type="button" disabled className="w-full py-3 bg-white/20 text-white font-bold rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                      <Loader2 className="h-5 w-5 animate-spin" /> Publishing to selected platforms...
                    </button>
                  ) : status === "published" ? (
                    <div className="w-full py-3 bg-emerald-500/20 text-emerald-400 font-bold rounded-xl flex items-center justify-center gap-2 border border-emerald-500/30">
                      <CheckCircle2 className="h-5 w-5" /> Published Successfully!
                    </div>
                  ) : (
                    <button type="submit" className="w-full py-3 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 transition-all shadow-[0_0_15px_rgba(5,150,105,0.3)] hover:shadow-[0_0_25px_rgba(5,150,105,0.5)] flex items-center justify-center gap-2">
                      <MonitorPlay className="h-5 w-5" /> Auto-Publish
                    </button>
                  )}
                  <p className="text-center text-[10px] text-zinc-600 mt-3">Requires active OAuth connection for each selected platform.</p>
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