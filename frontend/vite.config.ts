import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  define: {
    // ketcher packages read Node globals at runtime
    "process.env": {},
    global: "globalThis",
  },
  build: {
    // ketcher ships modules that mix require() with ESM
    commonjsOptions: { transformMixedEsModules: true },
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        art: resolve(__dirname, "art.html"),
        sketcher: resolve(__dirname, "sketcher.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8814",
    },
  },
});
