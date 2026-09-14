import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    dedupe: ["react", "react-dom"],
    alias: [
      {
        find: "@/services",
        replacement: path.resolve(__dirname, "./src/services"),
      },
      {
        find: "@/features",
        replacement: path.resolve(__dirname, "./src/features"),
      },
      { find: "@/", replacement: `${path.resolve(__dirname, "./src")}/` },
    ],
  },
  server: {
    host: "127.0.0.1",
    port: 3000,
    strictPort: true,
    proxy: {
      "/v0": {
        target: "http://127.0.0.1:4000",
        changeOrigin: true,
      },
      "/v1": {
        target: "http://127.0.0.1:4000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:4000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
