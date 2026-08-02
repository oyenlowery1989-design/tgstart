import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// base: "/app/" — built assets are served by dashboard/app.py's StaticFiles
// mount at /app/assets and the /app/{path} catch-all. Do not change.
//
// frontend/public/ is NOT served in production — only /app/assets is mounted by
// dashboard/app.py. Anything that needs to ship (favicons, images) must be
// imported from src/ so Vite hashes it into dist/assets/, not dropped in public/.
export default defineConfig({
  base: "/app/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
