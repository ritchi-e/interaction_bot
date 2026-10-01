import type { NextConfig } from "next";

const api = process.env.API_PROXY_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  skipTrailingSlashRedirect: true,
  async rewrites() {
    if (process.env.DISABLE_API_PROXY === "1") return [];
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*/` },
      { source: "/health", destination: `${api}/health/` },
    ];
  },
};

export default nextConfig;
