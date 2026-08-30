"use client";

import React from "react";

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: React.ReactNode;
}

export function ToggleSwitch({ checked, onChange, label }: ToggleSwitchProps) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <div className="relative flex items-center">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div
          className={`block w-10 h-5 rounded-full transition-all duration-300 ease-in-out border ${
            checked 
              ? "bg-[var(--accent)] border-[var(--accent)] shadow-[0_0_10px_var(--accent-glow)]" 
              : "bg-black/50 border-white/10"
          }`}
        ></div>
        <div
          className={`absolute left-1 top-1 w-3 h-3 rounded-full transition-transform duration-300 ease-in-out ${
            checked ? "bg-black transform translate-x-5" : "bg-zinc-500"
          }`}
        ></div>
      </div>
      {label && <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">{label}</span>}
    </label>
  );
}
