import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig(({ command }) => ({
  // The Cloudflare plugin emulates Workers for deployment builds. It is not
  // needed for the local SPA dev server and can fail when no Worker config
  // exists, so only attach it to production builds.
  plugins: command === "build" ? [react(), cloudflare()] : [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
    css: false,
    restoreMocks: true,
  },
}));