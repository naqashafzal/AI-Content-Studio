"use client";

import { apiFetch } from "@/lib/api";
import { 
  Video, 
  Clock, 
  TrendingUp, 
  Sparkles, 
  Plus, 
  Play, 
  Scissors, 
  Film, 
  ArrowRight, 
  Activity, 
  Palette, 
  Bot,
  Zap,
  CheckCircle2,
  Cpu,
  Layers,
  Wrench,
  Clapperboard,
  ArrowUpRight
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { API_BASE_URL, getMediaUrl } from "@/lib/api";

interface RecentProject {
  id: string;
  title: string;
  type: string;
  created_at: number;
  video_count: number;
  video_path?: string | null;
}

function getGreeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

function subscribeToClock(onChange: () => void) {
  const interval = setInterval(onChange, 60_000);
  return () => clearInterval(interval);
}

export default function Dashboard() {
  const greeting = useSyncExternalStore(subscribeToClock, getGreeting, () => "Welcome back");
  const [stats, setStats] = useState({
    total_generated: 0,
    total_projects: 0,
    render_hours: 0,
    active_jobs: 0,
    completed_jobs: 0,
    configured_providers: 0,
  });
  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);
  const [previewVideo, setPreviewVideo] = useState<string | null>(null);

  useEffect(() => {
    apiFetch(`${API_BASE_URL}/api/generate/stats`)
      .then(res => (res.ok ? res.json() : null))
      .then(data => {
        if (data) {
          setStats({
            total_generated: data.total_generated ?? 0,
            total_projects: data.total_projects ?? 0,
            render_hours: data.render_hours ?? 0,
            active_jobs: data.active_jobs ?? 0,
            completed_jobs: data.completed_jobs ?? 0,
            configured_providers: data.configured_providers ?? 0,
          });
          if (Array.isArray(data.recent_projects)) {
            setRecentProjects(data.recent_projects);
          }
        }
      })
      .catch(err => console.error("Failed to load dashboard telemetry:", err));
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500 pb-16">
      
      {/* Hero Showcase Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#0d131f] via-[#090e17] to-[#0d1624] border border-white/10 p-8 md:p-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-[0_20px_50px_rgba(0,0,0,0.6)]">
        {/* Glow Effects */}
        <div className="absolute top-0 right-1/4 -mt-20 w-96 h-96 bg-[#66fcf1] rounded-full blur-[140px] opacity-[0.12] pointer-events-none"></div>
        <div className="absolute bottom-0 right-0 -mb-24 w-80 h-80 bg-[#38bdf8] rounded-full blur-[120px] opacity-[0.08] pointer-events-none"></div>
        
        <div className="relative z-10 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#66fcf1]/10 border border-[#66fcf1]/25 text-[#66fcf1] text-[11px] font-extrabold tracking-widest uppercase mb-4 shadow-[0_0_15px_rgba(102,252,241,0.2)]">
            <Sparkles className="h-3.5 w-3.5 fill-[#66fcf1]" />
            AI Content Studio 2.0 Autonomous Engine
          </div>
          <h1 className="text-3xl md:text-5xl font-black text-white tracking-tight leading-tight mb-3">
            {greeting}, <span className="bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">Creator.</span>
          </h1>
          <p className="text-zinc-400 text-sm md:text-base leading-relaxed">
            Autonomous multi-modal video pipelines are operational. You have produced{" "}
            <span className="text-white font-bold">{stats.total_generated} high-retention videos</span> across{" "}
            <span className="text-white font-bold">{stats.total_projects} active projects</span>.
          </p>
        </div>

        <div className="relative z-10 flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <Link 
            href="/studio" 
            className="btn-primary !w-full sm:!w-auto px-7 py-4 text-sm font-black shadow-[0_0_25px_rgba(102,252,241,0.4)]"
          >
            <Plus className="h-4 w-4 stroke-[3]" />
            Launch Creator Studio
          </Link>
          <Link 
            href="/director" 
            className="btn-secondary !w-full sm:!w-auto px-6 py-4 text-sm font-bold"
          >
            <Film className="h-4 w-4 text-[#66fcf1]" />
            Director Mode
          </Link>
        </div>
      </div>

      {/* Telemetry Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Videos Rendered", value: String(stats.total_generated), icon: Video, trend: `${stats.total_projects} Projects`, color: "text-[#66fcf1]" },
          { label: "Total Render Hours", value: String(stats.render_hours), icon: Clock, trend: `${stats.completed_jobs} Jobs Done`, color: "text-[#38bdf8]" },
          { label: "Active Queue", value: String(stats.active_jobs), icon: TrendingUp, trend: stats.active_jobs > 0 ? "Rendering Now" : "Queue Ready", color: "text-[#34d399]" },
          { label: "AI Engines", value: `${stats.configured_providers}/4`, icon: Cpu, trend: stats.configured_providers > 0 ? "Online" : "Needs API Keys", color: "text-[#fca311]" },
        ].map((stat, i) => (
          <div key={i} className="glass-card glass-card-hover p-5 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
                {stat.label}
              </span>
              <div className="text-2xl font-black text-white tracking-tight">
                {stat.value}
              </div>
              <span className="text-[11px] font-semibold text-zinc-500 mt-1 block">
                {stat.trend}
              </span>
            </div>
            <div className={`p-3.5 rounded-2xl bg-white/[0.03] border border-white/5 ${stat.color} shadow-inner`}>
              <stat.icon className="h-6 w-6" />
            </div>
          </div>
        ))}
      </div>

      {/* Creation Suites Launchpad */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-black text-white uppercase tracking-[0.15em] flex items-center gap-2">
            <Activity className="h-4 w-4 text-[#66fcf1]" /> Production Suites
          </h2>
          <span className="text-xs text-zinc-400 font-medium">Click to open production workflow</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { 
              title: "Autonomous Director", 
              desc: "Deep research, scene storyboard, script generation, and selective regeneration.", 
              icon: Film, 
              href: "/director", 
              tag: "Flagship",
              accent: "from-cyan-500/20 to-blue-500/10 border-cyan-500/30 text-[#66fcf1]" 
            },
            { 
              title: "Magic AI Clipper 2.0", 
              desc: "Auto-extract viral hooks from long videos using audio peaks and scene changes.", 
              icon: Scissors, 
              href: "/clipper", 
              tag: "Viral",
              accent: "from-amber-500/20 to-orange-500/10 border-amber-500/30 text-[#fca311]" 
            },
            { 
              title: "VideoFX Flow", 
              desc: "Interactive video generation pipeline with live browser automation frames.", 
              icon: Zap, 
              href: "/videofx", 
              tag: "Flow",
              accent: "from-violet-500/20 to-purple-500/10 border-violet-500/30 text-[#c084fc]" 
            },
            { 
              title: "Movie & Story Explainer", 
              desc: "Transform film summaries and stories into engaging animated commentary videos.", 
              icon: Clapperboard, 
              href: "/explainer", 
              tag: "Story",
              accent: "from-emerald-500/20 to-teal-500/10 border-emerald-500/30 text-[#34d399]" 
            },
            { 
              title: "Brand Assets & Styles", 
              desc: "Reverse-engineer editing rules from reference clips & configure logo watermarks.", 
              icon: Palette, 
              href: "/brand", 
              tag: "Studio Kit",
              accent: "from-pink-500/20 to-rose-500/10 border-pink-500/30 text-[#f43f5e]" 
            },
            { 
              title: "Auto-Pilot Campaigns", 
              desc: "Set-and-forget scheduling engine to publish automated content around the clock.", 
              icon: Bot, 
              href: "/campaigns", 
              tag: "24/7",
              accent: "from-sky-500/20 to-indigo-500/10 border-sky-500/30 text-[#38bdf8]" 
            },
          ].map((action, i) => (
            <Link 
              key={i} 
              href={action.href} 
              className="glass-card glass-card-hover p-6 flex flex-col justify-between group cursor-pointer"
            >
              <div>
                <div className="flex justify-between items-start mb-5">
                  <div className={`p-3 rounded-2xl bg-gradient-to-br border ${action.accent}`}>
                    <action.icon className="h-6 w-6" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-zinc-400">
                      {action.tag}
                    </span>
                    <div className="h-7 w-7 rounded-full bg-white/5 flex items-center justify-center text-zinc-400 group-hover:text-white group-hover:bg-[#66fcf1]/20 transition-all">
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </div>
                  </div>
                </div>
                <h3 className="text-base font-bold text-white mb-1.5 group-hover:text-[#66fcf1] transition-colors">
                  {action.title}
                </h3>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {action.desc}
                </p>
              </div>

              <div className="pt-4 mt-4 border-t border-white/5 flex items-center justify-between text-[11px] font-semibold text-zinc-500 group-hover:text-zinc-300 transition-colors">
                <span>Launch Tool</span>
                <span className="text-[#66fcf1] opacity-0 group-hover:opacity-100 transition-opacity">Open →</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Workspace Projects */}
      {recentProjects.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-black text-white uppercase tracking-[0.15em] flex items-center gap-2">
              <Film className="h-4 w-4 text-[#66fcf1]" /> Recent Projects
            </h2>
            <Link href="/history" className="text-xs text-[#66fcf1] hover:underline font-semibold flex items-center gap-1">
              View all history <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recentProjects.slice(0, 3).map((proj) => (
              <div key={proj.id} className="glass-card p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-0.5">
                    <h4 className="text-sm font-bold text-white line-clamp-1">{proj.title}</h4>
                    <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">
                      {proj.type} • {new Date(proj.created_at * 1000).toLocaleDateString()}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#66fcf1]/10 text-[#66fcf1] border border-[#66fcf1]/20">
                    {proj.video_count} videos
                  </span>
                </div>

                {proj.video_path ? (
                  <button
                    onClick={() => setPreviewVideo(getMediaUrl(proj.video_path!))}
                    className="w-full py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all border border-white/5"
                  >
                    <Play className="h-3.5 w-3.5 fill-white" /> Preview Video
                  </button>
                ) : (
                  <Link
                    href="/history"
                    className="w-full py-2 bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all border border-white/5"
                  >
                    View in Project History
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Video Modal Preview */}
      {previewVideo && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in"
          onClick={() => setPreviewVideo(null)}
        >
          <div 
            className="max-w-4xl w-full bg-[#0c1017] border border-white/10 rounded-2xl overflow-hidden shadow-2xl p-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-3 px-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Rendered Media Preview</span>
              <button 
                onClick={() => setPreviewVideo(null)}
                className="text-xs text-zinc-400 hover:text-white px-2 py-1 rounded-md bg-white/5"
              >
                Close ✕
              </button>
            </div>
            <video src={previewVideo} controls autoPlay className="w-full rounded-xl max-h-[75vh] bg-black" />
          </div>
        </div>
      )}
    </div>
  );
}
