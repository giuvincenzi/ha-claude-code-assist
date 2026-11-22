import { defineConfig } from "vite";

// Relative base: Ingress serves the panel under /api/hassio_ingress/<token>/.
export default defineConfig({
  base: "./",
  build: { outDir: "dist" },
});
