"use client";

import { Video, Clock, TrendingUp, Sparkles, Plus, Play, Scissors, Film, ArrowRight, Activity, CalendarDays, MoreHorizontal } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const [greeting, setGreeting] = useState("Welcome back");

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good morning");
    else if (hour < 18) setGreeting("Good afternoon");
    else setGreeting("Good evening");
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
            Your high-performance AI video pipelines are standing by. You have generated <span className="text-white font-bold">14 videos</span> this week.
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
          <Activity className="h-4 w-4 text-[var(--accent)]" /> Launchpad
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            { title: "Quick Creator", desc: "AI script to full video in 2 mins", icon: Video, href: "/studio", color: "text-[var(--accent)]" },
            { title: "Magic Clipper", desc: "Extract viral shorts from podcasts", icon: Scissors, href: "/clipper", color: "text-[#fca311]" },
            { title: "Director Mode", desc: "Fine-tune and edit timelines", icon: Film, href: "/director", color: "text-[#ff00ff]" },
          ].map((action, i) => (
            <Link key={i} href={action.href} className="glass-card glass-card-hover p-6 flex flex-col group">
              <div className="flex justify-between items-start mb-4">
                <div className={`p-3 rounded-xl bg-white/5 border border-white/5 ${action.color}`}>
                  <action.icon className="h-6 w-6" />
                </div>
                <div className="h-8 w-8 rounded-full bg-white/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0">
                  <ArrowRight className="h-4 w-4 text-white" />
                </div>
              </div>
              <h3 className="text-lg font-bold text-white mb-1">{action.title}</h3>
              <p className="text-xs text-zinc-500">{action.desc}</p>
            </Link>
          ))}
        </div>
      </div>

      {/* Telemetry Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {[
          { label: "Total Generated", value: "128", icon: Video, trend: "+12%" },
          { label: "Render Hours", value: "42.5", icon: Clock, trend: "+5%" },
          { label: "Avg Engagement", value: "14.2%", icon: TrendingUp, trend: "+2.4%" },
          { label: "API Credits", value: "840", icon: Sparkles, trend: "Stable" },
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

      {/* Recent Generations */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/5">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-zinc-400" /> Recent Output
          </h2>
          <button className="text-xs font-bold text-[var(--accent)] hover:text-white transition-colors">View All</button>
        </div>
        
        <div className="space-y-3">
          {[
            { title: "History of Artificial Intelligence", style: "Documentary", time: "2 hours ago", status: "Ready", duration: "05:24" },
            { title: "Top 10 Tech Gadgets 2026", style: "Viral Video", time: "5 hours ago", status: "Ready", duration: "01:15" },
            { title: "ASMR Keyboard Typing", style: "ASMR", time: "Yesterday", status: "Failed", duration: "--:--" },
          ].map((item, i) => (
            <div key={i} className="group flex items-center justify-between p-3 bg-black/20 rounded-xl border border-white/5 hover:border-white/20 transition-all hover:bg-black/40">
              <div className="flex items-center gap-4">
                <div className="relative h-14 w-24 rounded-lg bg-zinc-900 overflow-hidden border border-white/10 group-hover:border-[var(--accent)] transition-colors flex items-center justify-center">
                  <Play className="h-5 w-5 text-white/50 group-hover:text-[var(--accent)] transition-colors" />
                  <div className="absolute bottom-1 right-1 bg-black/80 px-1.5 py-0.5 rounded text-[9px] font-mono text-white">
                    {item.duration}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white mb-0.5 group-hover:text-[var(--accent)] transition-colors">{item.title}</h3>
                  <p className="text-[11px] text-zinc-500 font-medium">{item.style} • {item.time}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-md border ${
                  item.status === 'Ready' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_10px_rgba(52,211,153,0.1)]' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                }`}>
                  {item.status}
                </span>
                <button className="p-2 hover:bg-white/10 rounded-lg text-zinc-500 hover:text-white transition-colors">
                  <MoreHorizontal className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
      
    </div>
  );
}