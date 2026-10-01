import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  plugins: [tailwindcss(), react()],
  build: {
    assetsInlineLimit: Number.POSITIVE_INFINITY,
    cssCodeSplit: false,
    lib: {
      entry: "src/entry.tsx",
      formats: ["iife"],
      name: "CRMChatWidget",
      fileName: () => "chat-widget.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
