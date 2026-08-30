import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import { ConfigProvider } from "@/context/ConfigContext";
import { Sidebar } from "@/components/Sidebar";

const outfit = Outfit({ subsets: ["latin"], weight: ["300", "400", "500", "600", "700", "800", "900"] });

export const metadata: Metadata = {
  title: "AI Content Studio | Pro",
  description: "Commercial-grade automated AI video generation studio.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={outfit.className}>
      <body className="flex h-screen overflow-hidden bg-[var(--bg-main)] text-zinc-100 font-sans">
        
        <Sidebar />

        <main className="flex-1 overflow-y-auto p-8 relative">
          <ConfigProvider>
            {children}
          </ConfigProvider>
        </main>
      </body>
    </html>
  );
}