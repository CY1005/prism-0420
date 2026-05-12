import type { NextConfig } from "next";

// Phase 2.3 cleanup follow-up: /auth/* + /api/* 转 FastAPI backend
// 配合 services/http-client.ts BASE_URL="" / 走同源避免 mixed-content + CORS
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/auth/:path*", destination: `${BACKEND_URL}/auth/:path*` },
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
