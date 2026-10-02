import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          three: ['three'],
        }
      }
    }
  },
  server: {
    port: 5173,
    host: "localhost",
    proxy: {
      "/ask": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/ready": "http://127.0.0.1:8000",
      "/chat": "http://127.0.0.1:8000",
      "/api": "http://127.0.0.1:8000",
    }
  },
  preview: {
    port: 4173,
    host: "localhost"
  }
})
