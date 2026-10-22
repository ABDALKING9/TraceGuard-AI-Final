import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173 },
  preview: { host: "127.0.0.1", port: 4173 },
  build: {
    chunkSizeWarningLimit: 700,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: "react-vendor", test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: "chart-vendor", test: /node_modules[\\/]recharts[\\/]/ },
            { name: "graph-vendor", test: /node_modules[\\/]cytoscape[\\/]/ },
            { name: "icon-vendor", test: /node_modules[\\/]lucide-react[\\/]/ },
          ],
        },
      },
    },
  },
});
