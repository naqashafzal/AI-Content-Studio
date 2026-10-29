import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.STUDIO_BACKEND_URL || "http://127.0.0.1:8008"}/api/:path*` }];
  },
};
export default nextConfig;
