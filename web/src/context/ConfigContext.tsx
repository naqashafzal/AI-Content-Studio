"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface ConfigContextType {
  config: any;
  updateConfig: (key: string, value: any) => void;
  saveConfig: () => Promise<void>;
  status: string;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<any>({});
  const [status, setStatus] = useState("loading"); // loading, idle, saving, saved, error

  // Load config on mount
  useEffect(() => {
    fetch("http://localhost:8008/api/config")
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

  const updateConfig = (key: string, value: any) => {
    setConfig((prev: any) => ({ ...prev, [key]: value }));
  };

  const saveConfig = async () => {
    setStatus("saving");
    try {
      const res = await fetch("http://localhost:8008/api/config", {
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
