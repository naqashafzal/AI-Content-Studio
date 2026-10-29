"use client";

import { apiFetch } from "@/lib/api";

import { Video, Clock, TrendingUp, Sparkles, Plus, Play, Scissors, Film, ArrowRight, Activity, CalendarDays, Palette, Bot } from "lucide-react";
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
    <div className="max-w-7xl mx-auto space-y-10 animate-in fade-in duration-700 pb-12">
      
      {/* Premium Hero Section */}
      <div className="relative overflow-hidden rounded-3xl bg-black/40 border border-white/5 p-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 backdrop-blur-md">
        <div className="absolute top-0 right-0 -mt-20 -mr-20 w-96 h-96 bg-[var(--accent)] rounded-full blur-[120px] opacity-10 pointer-events-none"></div>
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-[var(--accent)]" />
            <span className="text-[var(--accent)] text-xs font-bold tracking-widest uppercase">Studio Pro Engine</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight mb-2">
            {greeting}, Creator.
          </h1>
          <p className="text-zinc-400 text-sm md:text-base max-w-lg">
            Your high-performance AI video pipelines are standing by. You have{" "}
            <span className="text-white font-bold">{stats.total_generated} rendered videos</span> across{" "}
            <span className="text-white font-bold">{stats.total_projects} workspace projects</span>.
          </p>
        </div>
        <div className="relative z-10">
          <Link href="/studio" className="btn-primary !w-auto px-8 py-4 text-base shadow-[0_0_20px_var(--accent-glow)]">
            <Plus className="h-5 w-5" />
            Create Video Now
          </Link>
        </div>
      </div>

      {/* Quick Action Hub */}
      <div>
        <h2 className="text-sm font-bold text-white uppercase tracking-widest mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-[var(--accent)]" /> Next-Gen Studio Launchpad
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            { title: "Autonomous Director", desc: "Storyboard scenes, QA critique & selective regeneration", icon: Film, href: "/director", color: "text-[#66fcf1]" },
            { title: "Magic AI Clipper 2.0", desc: "Multimodal audio peaks & visual scene change detection", icon: Scissors, href: "/clipper", color: "text-[#fca311]" },
            { title: "Brand & Style Studio", desc: "Clone editing styles from reference videos & brand kit", icon: Palette, href: "/brand", color: "text-[#c084fc]" },
            { title: "Multi-Track Studio", desc: "Nonlinear timeline with transcript ripple-editing", icon: Video, href: "/studio", color: "text-[#38bdf8]" },
            { title: "Auto-Pilot Campaigns", desc: "Schedule 24/7 automated topic generation sequences", icon: Bot, href: "/campaigns", color: "text-[#34d399]" },
            { title: "Smart Media Utilities", desc: "Auto-captioner, aspect ratio converter & neural TTS", icon: Sparkles, href: "/tools", color: "text-[#f43f5e]" },
          ].map((action, i) => (
            <Link key={i} href={action.href} className="glass-card glass-card-hover p-6 flex flex-col justify-between group">
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className={`p-3 rounded-xl bg-white/5 border border-white/5 ${action.color}`}>
                    <action.icon className="h-6 w-6" />
                  </div>
                  <div className="h-8 w-8 rounded-full bg-white/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0">
                    <ArrowRight className="h-4 w-4 text-white" />
                  </div>
                </div>
                <h3 className="text-lg font-bold text-white mb-1">{action.title}</h3>
                <p className="text-xs text-zinc-400">{action.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Telemetry Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {[
          { label: "Total Generated", value: String(stats.total_generated), icon: Video, trend: `${stats.total_projects} Projects` },
          { label: "Render Hours", value: String(stats.render_hours), icon: Clock, trend: `${stats.completed_jobs} Jobs Done` },
          { label: "Active Queue", value: String(stats.active_jobs), icon: TrendingUp, trend: stats.active_jobs > 0 ? "Processing" : "Idle" },
          { label: "API Providers", value: `${stats.configured_providers}/4`, icon: Sparkles, trend: stats.configured_providers > 0 ? "+Connected" : "Configure in Settings" },
        ].map((stat, i) => (
          <div key={i} className="glass-card p-5 relative overflow-hidden">
            <div className="flex justify-between items-start mb-4">
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-wider">{stat.label}</p>
              <stat.icon className="h-4 w-4 text-zinc-600" />
            </div>
            <div className="flex items-end justify-between">
              <p className="text-3xl font-extrabold text-white">{stat.value}</p>
              <span className={`text-xs font-bold ${stat.trend.startsWith('+') ? 'text-emerald-400' : 'text-zinc-500'}`}>
                {stat.trend}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Preview Modal if user clicks a recent video */}
      {previewVideo && (
        <div className="glass-card p-6 border border-[var(--accent)]/30 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Quick Preview</h3>
            <button onClick={() => setPreviewVideo(null)} className="text-xs text-zinc-400 hover:text-white">Close</button>
          </div>
          <video src={getMediaUrl(previewVideo)} controls autoPlay className="w-full max-h-[420px] rounded-xl bg-black" />
        </div>
      )}

      {/* Recent Generations */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/5">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-zinc-400" /> Recent Output
          </h2>
          <Link href="/history" className="text-xs font-bold text-[var(--accent)] hover:text-white transition-colors">
            View All
          </Link>
        </div>
        
        {recentProjects.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 text-sm">
            No generated projects yet. Launch <Link href="/studio" className="text-[var(--accent)] underline">Creator Studio</Link> or <Link href="/director" className="text-[var(--accent)] underline">Autonomous Director</Link> to produce your first video.
          </div>
        ) : (
          <div className="space-y-3">
            {recentProjects.map((item) => (
              <div
                key={item.id}
                onClick={() => item.video_path && setPreviewVideo(item.video_path)}
                className="group flex items-center justify-between p-3 bg-black/20 rounded-xl border border-white/5 hover:border-white/20 transition-all hover:bg-black/40 cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="relative h-14 w-24 rounded-lg bg-zinc-900 overflow-hidden border border-white/10 group-hover:border-[var(--accent)] transition-colors flex items-center justify-center">
                    <Play className="h-5 w-5 text-white/50 group-hover:text-[var(--accent)] transition-colors" />
                    <div className="absolute bottom-1 right-1 bg-black/80 px-1.5 py-0.5 rounded text-[9px] font-mono text-white">
                      {item.video_count} {item.video_count === 1 ? "clip" : "clips"}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white mb-0.5 group-hover:text-[var(--accent)] transition-colors">{item.title}</h3>
                    <p className="text-[11px] text-zinc-500 font-medium uppercase">
                      {item.type} • {new Date(item.created_at * 1000).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-md border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                    Ready
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
    </div>
  );
}
