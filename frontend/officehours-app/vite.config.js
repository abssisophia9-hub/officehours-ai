import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Sub-path deploy (AUI CDN): VITE_ROOT_PATH=/officehours-ai
// Local default stays "/" so Windows scripts on :5180 are unchanged.
const rootPath = (process.env.VITE_ROOT_PATH || "").trim().replace(/\/$/, "");

export default defineConfig({
  base: rootPath ? `${rootPath}/` : "/",
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5180,
  },
});
