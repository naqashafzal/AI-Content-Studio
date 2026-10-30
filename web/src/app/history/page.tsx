"use client";

import { apiFetch } from "@/lib/api";
import { API_BASE_URL, getMediaUrl } from "@/lib/api";
import { useEffect, useState } from "react";
import { Film, Download, Trash2, Loader2, RefreshCw, Play, Clock, AlertTriangle, CheckCircle, ArrowRight } from "lucide-react";

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

interface Job {
  id: string;
  topic: string;
  status: string;
}

async function loadHistory(): Promise<{ projects: Project[]; jobs: Job[] }> {
  const [projects, jobs] = await Promise.all([
    apiFetch(`${API_BASE_URL}/api/generate/history`),
    apiFetch(`${API_BASE_URL}/api/jobs`),
  ]);
  if (!projects.ok || !jobs.ok) throw new Error("Failed to load history");
  return { projects: await projects.json(), jobs: await jobs.json() };
}

export default function HistoryPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [activeMedia, setActiveMedia] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await loadHistory();
      setProjects(data.projects);
      setJobs(data.jobs);
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    let active = true;
    loadHistory().then(data => {
      if (!active) return;
      setProjects(data.projects);
      setJobs(data.jobs);
      setLoading(false);
    }).catch(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this project?")) return;
    
    setDeletingId(id);
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/generate/history/${id}`, {
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

  const retryJob = async (id: string) => {
    setRetrying(id);
    try {
      const response = await apiFetch(`${API_BASE_URL}/api/jobs/${id}/retry`, { method: "POST" });
      if (!response.ok) throw new Error((await response.json()).detail || "Retry failed");
      await fetchHistory();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Retry failed");
    } finally {
      setRetrying(null);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#66fcf1]/10 text-[#66fcf1] border border-[#66fcf1]/20 text-[10px] font-black uppercase tracking-wider mb-2">
            <Film className="h-3 w-3" /> Creative Archive
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Project History & Media</h1>
          <p className="text-zinc-400 text-sm mt-1">Review, play, stream, and export your previously generated video assets.</p>
        </div>

        <button 
          onClick={fetchHistory}
          disabled={loading}
          className="btn-secondary !w-auto px-4 py-2.5 text-xs font-bold self-start sm:self-auto"
          title="Refresh Archive"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-[#66fcf1]" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Background Queue Tasks Banner if any */}
      {jobs.length > 0 && (
        <section className="glass-card p-6 space-y-4 border-amber-500/20 bg-amber-500/[0.02]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Clock className="h-5 w-5 text-amber-400" />
              <h2 className="text-sm font-extrabold text-white tracking-wide uppercase">Recent Task Queue</h2>
            </div>
            <span className="text-xs text-zinc-400 font-medium">Automatic recovery enabled</span>
          </div>

          <div className="space-y-2">
            {jobs.slice(0, 5).map(job => (
              <div key={job.id} className="flex items-center justify-between gap-4 bg-black/40 p-3 rounded-xl border border-white/5">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-white truncate">{job.topic}</p>
                  <span className={`text-[10px] font-extrabold uppercase tracking-wider inline-flex items-center gap-1.5 ${
                    job.status === "completed" ? "text-emerald-400" :
                    job.status === "failed" ? "text-rose-400" : "text-amber-400"
                  }`}>
                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                    {job.status}
                  </span>
                </div>
                {["failed", "interrupted"].includes(job.status) && (
                  <button 
                    disabled={retrying === job.id} 
                    onClick={() => retryJob(job.id)} 
                    className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-bold transition-all"
                  >
                    {retrying === job.id ? "Queuing…" : "Retry Job"}
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Projects Grid */}
      {loading && projects.length === 0 ? (
        <div className="glass-card p-24 flex flex-col items-center justify-center gap-4 text-zinc-400">
          <Loader2 className="h-10 w-10 animate-spin text-[#66fcf1]" />
          <p className="text-sm font-medium">Loading your creative history...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-card p-24 text-center space-y-4">
          <Film className="h-12 w-12 text-zinc-600 mx-auto" />
          <h3 className="text-lg font-bold text-white">No Rendered Projects Found</h3>
          <p className="text-zinc-400 text-sm max-w-sm mx-auto">
            You haven't generated any videos yet. Launch Quick Creator or Director Mode to produce your first content.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {projects.map((proj) => (
            <div key={proj.id} className="glass-card glass-card-hover p-6 flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <span className="px-2.5 py-0.5 rounded-md bg-[#66fcf1]/10 text-[#66fcf1] border border-[#66fcf1]/20 text-[10px] font-black uppercase tracking-wider">
                    {proj.type}
                  </span>
                  <span className="text-[11px] text-zinc-400 font-medium">
                    {formatDate(proj.created_at)}
                  </span>
                </div>
                
                <h3 className="text-base font-bold text-white line-clamp-2">
                  {proj.videos[0]?.title || `Project #${proj.id.slice(0, 8)}`}
                </h3>
              </div>

              {/* Videos in Project */}
              <div className="space-y-2 pt-3 border-t border-white/5">
                {proj.videos.map((vid, idx) => {
                  const mediaUrl = getMediaUrl(vid.path);
                  return (
                    <div key={idx} className="flex items-center justify-between gap-2 p-2.5 bg-black/40 rounded-xl border border-white/5">
                      <span className="text-xs text-zinc-300 font-medium truncate">
                        {vid.title || `Video Clip ${idx + 1}`}
                      </span>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={() => setActiveMedia(mediaUrl)}
                          className="p-1.5 rounded-lg bg-white/5 hover:bg-[#66fcf1]/20 hover:text-[#66fcf1] text-zinc-300 transition-colors"
                          title="Play Video"
                        >
                          <Play className="h-3.5 w-3.5 fill-current" />
                        </button>
                        <a
                          href={mediaUrl}
                          download
                          target="_blank"
                          rel="noreferrer"
                          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white transition-colors"
                          title="Download Video"
                        >
                          <Download className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-zinc-400 font-semibold">
                  {proj.videos.length} video {proj.videos.length === 1 ? "asset" : "assets"}
                </span>

                <button
                  onClick={() => handleDelete(proj.id)}
                  disabled={deletingId === proj.id}
                  className="p-2 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                  title="Delete Project"
                >
                  {deletingId === proj.id ? (
                    <Loader2 className="h-4 w-4 animate-spin text-rose-400" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video Modal Player */}
      {activeMedia && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in"
          onClick={() => setActiveMedia(null)}
        >
          <div 
            className="max-w-4xl w-full bg-[#0c1017] border border-white/15 rounded-2xl overflow-hidden shadow-2xl p-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-3 px-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Video Playback</span>
              <button 
                onClick={() => setActiveMedia(null)}
                className="text-xs text-zinc-400 hover:text-white px-2 py-1 rounded-md bg-white/5"
              >
                Close ✕
              </button>
            </div>
            <video src={activeMedia} controls autoPlay className="w-full rounded-xl max-h-[75vh] bg-black" />
          </div>
        </div>
      )}
    </div>
  );
}