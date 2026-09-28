import { defineConfig } from "vite";

export default defineConfig({
  // GitHub Pages serves the site from /<repo>/; CI sets BASE_PATH.
  base: process.env.BASE_PATH ?? "/",
  build: { target: "es2022" }, // top-level await in src/main.js
});
