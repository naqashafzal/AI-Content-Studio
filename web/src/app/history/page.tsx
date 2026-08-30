"use client";

import { useEffect, useState } from "react";
import { Film, FileText, Download, Play, Trash2, Calendar, Loader2, RefreshCw } from "lucide-react";

interface ProjectVideo {
  title: string;
  path: string;
}

interface Project {
  id: string;
  type: "podcast" | "clipper";
  created_at: number;
  videos: ProjectVideo[];
  scripts: string[];
}

export default function HistoryPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8008/api/generate/history");
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this project? This cannot be undone.")) return;
    
    setDeletingId(id);
    try {
      const res = await fetch(`http://localhost:8008/api/generate/history/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setProjects(prev => prev.filter(p => p.id !== id));
      } else {
        alert("Failed to delete project");
      }
    } catch (e) {
      console.error("Error deleting", e);
      alert("Error deleting project");
    }
    setDeletingId(null);
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500 pb-20">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">History & Projects</h1>
          <p className="text-zinc-400 mt-1">View, play, and download your previously generated content.</p>
        </div>
        <button 
          onClick={fetchHistory}
          disabled={loading}
          className="p-3 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-all"
          title="Refresh"
        >
          <RefreshCw className={`h-5 w-5 ${loading ? "animate-spin text-[#66fcf1]" : ""}`} />
        </button>
      </div>

      {loading && projects.length === 0 ? (
        <div className="glass-card p-20 flex flex-col items-center justify-center gap-4 text-zinc-400">
          <Loader2 className="h-10 w-10 animate-spin text-[#66fcf1]" />
          <p>Loading your creative history...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-card p-20 flex flex-col items-center justify-center gap-4 text-zinc-500">
          <Film className="h-16 w-16 opacity-20" />
          <p className="text-lg">No projects found. Go make something awesome!</p>
        </div>
      ) : (
        <div className="space-y-12">
          {projects.map((project) => (
            <div key={project.id} className="flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-md ${project.type === "podcast" ? "bg-purple-500/20 text-purple-400" : "bg-[#66fcf1]/20 text-[#66fcf1]"}`}>
                    <Film className="h-5 w-5" />
                  </div>
                  <h2 className="text-lg font-bold text-white">
                    {project.type === "podcast" ? "AI Podcast: " : "Magic Clipper: "}
                    <span className="font-normal text-zinc-300">{project.id.replace("clipper_", "")}</span>
                  </h2>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-zinc-500 flex items-center gap-1">
                    <Calendar className="h-3 w-3" /> {formatDate(project.created_at)}
                  </span>
                  <button 
                    onClick={() => handleDelete(project.id)}
                    disabled={deletingId === project.id}
                    className="p-2 text-red-400/50 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-all"
                    title="Delete Project"
                  >
                    {deletingId === project.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {project.videos.map((vid, idx) => (
                  <div key={idx} className="flex flex-col gap-3 group">
                    <div className={`bg-black rounded-xl border border-white/10 overflow-hidden relative shadow-lg ${project.type === "podcast" ? "aspect-video" : "aspect-[9/16]"}`}>
                      <video 
                        src={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(vid.path.replace(/\\/g, '/'))}`} 
                        controls 
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="px-1">
                      <p className="text-sm font-bold text-white line-clamp-1" title={vid.title}>
                        {vid.title}
                      </p>
                      <a 
                        href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(vid.path.replace(/\\/g, '/'))}`} 
                        download 
                        className="mt-3 py-2 w-full bg-white/5 hover:bg-white/10 text-white rounded-lg flex items-center justify-center gap-2 text-xs font-bold transition-all border border-white/10"
                      >
                        <Download className="h-4 w-4" /> Download Video
                      </a>
                    </div>
                  </div>
                ))}
              </div>
              
              {project.scripts.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-2">
                  {project.scripts.map((script, idx) => (
                    <a 
                      key={idx}
                      href={`http://localhost:8008/api/generate/media?path=${encodeURIComponent(script.replace(/\\/g, '/'))}`} 
                      download
                      className="py-2 px-4 bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 rounded-lg flex items-center gap-2 text-sm font-medium transition-all"
                    >
                      <FileText className="h-4 w-4" /> Download Script
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}