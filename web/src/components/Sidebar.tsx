"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Video, 
  Settings, 
  History, 
  Wrench, 
  Share2, 
  Layers, 
  Sparkles, 
  Bot, 
  Scissors, 
  Film, 
  MonitorPlay, 
  Clapperboard,
  Activity,
  Zap,
  Coffee,
  Heart
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navGroups = [
    {
      group: "Core Studio",
      items: [
        { name: "Dashboard", href: "/", icon: LayoutDashboard },
        { name: "Quick Creator", href: "/studio", icon: Video, badge: "Hot" },
        { name: "VideoFX Flow", href: "/videofx", icon: MonitorPlay },
        { name: "Director Mode", href: "/director", icon: Film, badge: "AI" },
      ]
    },
    {
      group: "AI Production",
      items: [
        { name: "Magic Clipper", href: "/clipper", icon: Scissors },
        { name: "Movie Explainer", href: "/explainer", icon: Clapperboard },
        { name: "Auto-Pilot Bots", href: "/campaigns", icon: Bot },
        { name: "Brand & Styles", href: "/brand", icon: Layers },
      ]
    },
    {
      group: "Manage & Export",
      items: [
        { name: "Project History", href: "/history", icon: History },
        { name: "Media Utilities", href: "/tools", icon: Wrench },
        { name: "Publish & SEO", href: "/publish", icon: Share2 },
        { name: "Settings & APIs", href: "/settings", icon: Settings },
      ]
    }
  ];

  return (
    <aside className="w-72 border-r border-white/5 bg-[#090d14]/90 backdrop-blur-2xl p-5 flex flex-col justify-between shadow-[8px_0_32px_rgba(0,0,0,0.6)] z-20 relative select-none">
      <div>
        {/* Brand Header */}
        <Link href="/" className="flex items-center gap-3.5 px-2 py-3 mb-6 group cursor-pointer">
          <div className="relative">
            <div className="p-2.5 bg-gradient-to-br from-[#66fcf1] via-[#45f3e5] to-[#38bdf8] rounded-2xl text-slate-950 shadow-[0_0_20px_rgba(102,252,241,0.45)] group-hover:scale-105 transition-transform duration-300">
              <Sparkles className="h-5 w-5 fill-slate-950" />
            </div>
            <div className="absolute -inset-1 bg-[#66fcf1] rounded-2xl blur-md opacity-25 group-hover:opacity-60 transition-opacity"></div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="font-black text-white tracking-wider text-base">STUDIO</h1>
              <span className="px-1.5 py-0.5 rounded-md bg-[#66fcf1]/15 border border-[#66fcf1]/30 text-[10px] font-black text-[#66fcf1] tracking-wider">
                PRO 2.0
              </span>
            </div>
            <span className="text-[10px] text-zinc-400 font-semibold tracking-wider block uppercase opacity-75">
              Next-Gen AI Media Engine
            </span>
          </div>
        </Link>

        {/* Navigation Categories */}
        <div className="space-y-6 overflow-y-auto max-h-[calc(100vh-270px)] pr-1 scrollbar-hide">
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1.5">
              <div className="px-3 text-[10px] font-extrabold uppercase tracking-[0.18em] text-zinc-500">
                {group.group}
              </div>
              <nav className="space-y-1">
                {group.items.map((item) => {
                  const isActive = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
                  return (
                    <Link 
                      key={item.href} 
                      href={item.href} 
                      className={`group flex items-center justify-between px-3.5 py-2.5 text-xs font-bold rounded-xl transition-all duration-200 relative ${
                        isActive 
                          ? "text-white bg-gradient-to-r from-[#66fcf1]/15 to-transparent border border-[#66fcf1]/30 shadow-[0_0_20px_rgba(102,252,241,0.08)]" 
                          : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.04] border border-transparent"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <item.icon className={`h-4 w-4 transition-colors ${
                          isActive ? "text-[#66fcf1] drop-shadow-[0_0_8px_rgba(102,252,241,0.6)]" : "text-zinc-400 group-hover:text-zinc-200"
                        }`} /> 
                        <span>{item.name}</span>
                      </div>

                      {item.badge && (
                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-md uppercase tracking-wider ${
                          item.badge === "Hot" 
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : "bg-[#66fcf1]/15 text-[#66fcf1] border border-[#66fcf1]/30"
                        }`}>
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Actions: Buy Me a Coffee & System Status */}
      <div className="pt-3 border-t border-white/5 space-y-2.5">
        {/* Buy Me A Coffee Button */}
        <a 
          href="https://buymeacoffee.com/naqash" 
          target="_blank" 
          rel="noopener noreferrer"
          className="group flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-[#FFDD00]/15 via-[#FFDD00]/10 to-transparent border border-[#FFDD00]/30 hover:border-[#FFDD00]/60 transition-all duration-300 shadow-[0_0_15px_rgba(255,221,0,0.08)] hover:shadow-[0_0_20px_rgba(255,221,0,0.2)]"
        >
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-[#FFDD00] text-black shadow-sm group-hover:rotate-6 transition-transform">
              <Coffee className="h-4 w-4 stroke-[2.5]" />
            </div>
            <div>
              <span className="text-xs font-black text-white group-hover:text-[#FFDD00] transition-colors block">
                Buy Me a Coffee
              </span>
              <span className="text-[9px] font-semibold text-zinc-400 block">
                Support Open-Source
              </span>
            </div>
          </div>
          <Heart className="h-3.5 w-3.5 text-[#FFDD00] fill-[#FFDD00]/30 group-hover:scale-125 transition-transform" />
        </a>

        {/* Live System Status Widget */}
        <div className="flex items-center justify-between bg-black/40 p-2.5 rounded-xl border border-white/5 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#66fcf1] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#66fcf1]"></span>
            </span>
            <div>
              <span className="text-[10px] font-bold text-white block leading-tight">Engine Ready</span>
              <span className="text-[8.5px] font-semibold text-zinc-500 block leading-tight">Port 8008 • Next 16</span>
            </div>
          </div>
          <div className="p-1 rounded-md bg-white/5 text-zinc-400">
            <Zap className="h-3 w-3 text-[#66fcf1]" />
          </div>
        </div>
      </div>
    </aside>
  );
}
