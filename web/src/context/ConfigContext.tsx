"use client";

import { apiFetch } from "@/lib/api";

import { API_BASE_URL } from "@/lib/api";

import { useRouter } from "next/navigation";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

import type { StudioConfig, ConfigValue } from "@/lib/config";

interface ConfigContextType {
  config: StudioConfig;
  updateConfig: (key: string, value: ConfigValue) => void;
  saveConfig: () => Promise<void>;
  status: string;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<StudioConfig>({});
  const [status, setStatus] = useState("loading"); // loading, idle, saving, saved, error

  const router = useRouter();
  useEffect(() => {
    const signIn = () => router.replace("/login");
    window.addEventListener("studio:unauthorized", signIn);
    return () => window.removeEventListener("studio:unauthorized", signIn);
  }, [router]);

  // Load config on mount
  useEffect(() => {
    if (window.location.pathname === "/login") return;
    apiFetch(`${API_BASE_URL}/api/config`)
      .then(res => res.json())
      .then(data => {
        setConfig(data);
        setStatus("idle");
      })
      .catch(err => {
        console.error("Failed to load global config:", err);
        setStatus("error");
      });
  }, []);

  const updateConfig = (key: string, value: ConfigValue) => {
    setConfig((prev: StudioConfig) => ({ ...prev, [key]: value }));
  };

  const saveConfig = async () => {
    setStatus("saving");
    try {
      const res = await apiFetch(`${API_BASE_URL}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config)
      });
      if (!res.ok) throw new Error("Failed to save config");
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 2000);
    } catch (error) {
      console.error("Failed to save global config:", error);
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  };

  return (
    <ConfigContext.Provider value={{ config, updateConfig, saveConfig, status }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error("useConfig must be used within a ConfigProvider");
  }
  return context;
}
