"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Video, Settings, History, Wrench, Share2, Layers, Sparkles, Bot, Scissors, Film, MonitorPlay, Clapperboard } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Quick Creator", href: "/studio", icon: Video },
    { name: "VideoFX Flow", href: "/videofx", icon: MonitorPlay },
    { name: "Auto-Pilot Bots", href: "/campaigns", icon: Bot },
    { name: "Magic Clipper", href: "/clipper", icon: Scissors },
    { name: "Director Mode", href: "/director", icon: Film },
    { name: "Movie Explainer", href: "/explainer", icon: Clapperboard },
    { name: "Brand Assets", href: "/brand", icon: Layers },
    { name: "History & Projects", href: "/history", icon: History },
    { name: "Video Tools", href: "/tools", icon: Wrench },
    { name: "Publish & SEO", href: "/publish", icon: Share2 },
    { name: "Settings & APIs", href: "/settings", icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-white/5 bg-black/40 backdrop-blur-3xl p-6 flex flex-col justify-between shadow-[4px_0_24px_rgba(0,0,0,0.5)] z-10 relative">
      <div>
        <div className="flex items-center gap-3 mb-10">
          <div className="p-2.5 bg-gradient-to-br from-[#66fcf1] to-[#45f3e5] rounded-xl text-black shadow-[0_0_15px_rgba(102,252,241,0.5)]">
            <Sparkles className="h-5 w-5 fill-black" />
          </div>
          <div>
            <h1 className="font-extrabold text-white tracking-wide text-base">STUDIO<span className="text-[#66fcf1]">PRO</span></h1>
            <span className="text-[9px] text-[#66fcf1] font-bold tracking-[0.2em] block uppercase opacity-80">AI Engine Engine</span>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
            return (
              <Link 
                key={item.href} 
                href={item.href} 
                className={`group flex items-center gap-3 px-4 py-3 text-sm font-bold rounded-xl transition-all relative overflow-hidden ${
                  isActive 
                    ? "text-[#66fcf1] bg-[#66fcf1]/10 shadow-[inset_2px_0_0_#66fcf1]" 
                    : "text-zinc-500 hover:bg-white/5 hover:text-white"
                }`}
              >
                {isActive && (
                   <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#66fcf1] shadow-[0_0_10px_#66fcf1]"></div>
                )}
                <item.icon className={`h-4 w-4 ${isActive ? "text-[#66fcf1]" : "text-zinc-500 group-hover:text-white transition-colors"}`} /> 
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="pt-6 border-t border-white/10 mt-6">
        <div className="flex items-center gap-3 bg-black/40 p-3 rounded-xl border border-white/5">
          <div className="h-2.5 w-2.5 rounded-full bg-[#66fcf1] shadow-[0_0_10px_rgba(102,252,241,0.6)] animate-pulse" />
          <div>
             <span className="text-[10px] font-bold text-white block">API Connected</span>
             <span className="text-[9px] font-medium text-zinc-500 block">Port 8008</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
