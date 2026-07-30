import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev proxy: the SPA calls same-origin paths and Vite forwards them to
// FastAPI — keeps the session cookie same-site in development.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://localhost:8000",
      "/listings": "http://localhost:8000",
      "/categories": "http://localhost:8000",
      "/uploads": "http://localhost:8000",
      "/admin": "http://localhost:8000",
      "/config": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
