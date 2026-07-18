import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend dev server. Proxies /api -> FastAPI backend so cookies are same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
