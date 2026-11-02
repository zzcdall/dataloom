import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.indexOf("node_modules/echarts") !== -1 || id.indexOf("node_modules/zrender") !== -1) return "echarts";
          if (id.indexOf("node_modules/react") !== -1) return "react";
          return undefined;
        },
      },
    },
  },
});

