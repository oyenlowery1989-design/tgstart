import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// base: "/app/" — the built assets are served from dashboard/app.py under
// StaticFiles(directory="frontend/dist"), mounted at /app.
export default defineConfig({
  base: "/app/",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
  },
});
