import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["robots.txt"],
      manifest: {
        name: "لومن — منصة تعليمية",
        short_name: "Lumen",
        description: "منصّة تعليمية بالعربية: دروس، اختبارات، بطاقات مراجعة، وواجبات",
        lang: "ar",
        dir: "rtl",
        theme_color: "#0f172a",
        background_color: "#0f172a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        // Cache only the app shell at install time. Vite's default Workbox
        // patterns include every JS/CSS chunk, defeating lazy loading on slow links.
        globPatterns: [
          "**/*.html",
          "**/assets/index-*.js",
          "**/assets/index-*.css",
          "**/registerSW.js",
        ],
        // Hashed lazy chunks are cached only after the learner requests them.
        // This preserves repeat/offline access to previously visited features
        // without downloading every feature during service-worker installation.
        runtimeCaching: [
          {
            urlPattern: /\\/assets\\/(?!index-[^/]+\\.(?:js|css)$)[^/]+\\.(?:js|css)$/i,
            handler: "CacheFirst",
            options: {
              cacheName: "lumen-versioned-assets",
              expiration: {
                maxEntries: 60,
                maxAgeSeconds: 30 * 24 * 60 * 60,
              },
              cacheableResponse: {
                statuses: [200],
              },
            },
          },
        ],
        // WebSocket routes are interactive and must always use a live connection.
        navigateFallbackDenylist: [/^\\/ws/],
      },
    }),
  ],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
