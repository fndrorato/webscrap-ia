import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

export default defineConfig({
  base: './',
  plugins: [
    react(),
    svgr({
      svgrOptions: {
        icon: true,
        exportType: "named",
        namedExport: "ReactComponent",
      },
    }),
  ],
  preview: {
    port: 5000,
    strictPort: true,
    host: true,
    proxy: {
      // Proxy para a API
      '/api': {
        target: 'http://10.1.1.142:5001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // 🔥 ADICIONE: Proxy para arquivos de media
      '/media': {
        target: 'http://10.1.1.142:5001',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  server: {
    port: 8080,
    strictPort: true,
    host: true,
    origin: "http://0.0.0.0:8080",
    proxy: {
      '/api': {
        target: 'http://10.1.1.142:5001',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Proxy para arquivos de media
      '/media': {
        target: 'http://10.1.1.142:5001',
        changeOrigin: true,
        secure: false,
      }
    }
  },
});