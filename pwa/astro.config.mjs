import tailwind from "@astrojs/tailwind";
import { defineConfig } from "astro/config";
import { VitePWA } from "@vite-pwa/astro";

const API_BASE = process.env.PUBLIC_NEXO_API_BASE ?? "/api/v1";
const TILE_HOST = process.env.PUBLIC_NEXO_TILE_HOST ?? "https://tile.openstreetmap.org";

export default defineConfig({
  output: "static",
  integrations: [
    tailwind({ applyBaseStyles: false }),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Nexo Campo",
        short_name: "Nexo",
        description: "Mapa operativo offline-first para centros, necesidades y donaciones.",
        theme_color: "#0f172a",
        background_color: "#f8fafc",
        display: "standalone",
        orientation: "portrait",
        scope: "/",
        start_url: "/",
        icons: [
          {
            src: "/icon-192.svg",
            sizes: "192x192",
            type: "image/svg+xml",
            purpose: "any maskable"
          },
          {
            src: "/icon-512.svg",
            sizes: "512x512",
            type: "image/svg+xml",
            purpose: "any maskable"
          }
        ]
      },
      workbox: {
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,
        navigateFallback: "/",
        globPatterns: ["**/*.{html,css,js,svg,png,ico,json,txt,webmanifest}"],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.origin === TILE_HOST,
            handler: "CacheFirst",
            options: {
              cacheName: "nexo-osm-tiles-v1",
              expiration: {
                maxEntries: 120,
                maxAgeSeconds: 60 * 60 * 24 * 7,
                purgeOnQuotaError: true
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith(API_BASE),
            handler: "NetworkFirst",
            options: {
              cacheName: "nexo-api-v1",
              networkTimeoutSeconds: 4,
              expiration: {
                maxEntries: 40,
                maxAgeSeconds: 60 * 60 * 6,
                purgeOnQuotaError: true
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ]
      }
    })
  ],
  vite: {
    define: {
      __NEXO_API_BASE__: JSON.stringify(API_BASE),
      __NEXO_TILE_HOST__: JSON.stringify(TILE_HOST)
    }
  }
});
