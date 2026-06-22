import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// W1 web — static SPA, deployed to Vercel. Darwin UI is Tailwind v4-powered.
export default defineConfig({
  plugins: [react(), tailwindcss()],
});
