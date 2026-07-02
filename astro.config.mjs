import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import { VitePWA } from '@vite-pwa/astro';

const LIMITE_ZOOM_TILES = 15;

export default defineConfig({
  output: 'static',
  integrations: [
    tailwind(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'manifest.webmanifest'],
      manifest: false,
      workbox: {
        globPatterns: ['**/*.{html,js,css,svg,png,webmanifest}'],
        navigateFallback: '/',
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/sync/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'nexo-api-sync',
              expiration: { maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 },
              networkTimeoutSeconds: 5
            }
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'nexo-api-lectura',
              expiration: { maxEntries: 80, maxAgeSeconds: 60 * 60 * 24 * 7 },
              networkTimeoutSeconds: 5
            }
          },
          {
            urlPattern: ({ url }) => {
              if (url.hostname !== 'tile.openstreetmap.org') return false;
              const partes = url.pathname.split('/').filter(Boolean);
              const zoom = Number(partes[0]);
              return Number.isInteger(zoom) && zoom >= 0 && zoom <= LIMITE_ZOOM_TILES;
            },
            handler: 'CacheFirst',
            options: {
              cacheName: 'nexo-osm-tiles-z15',
              expiration: {
                maxEntries: 450,
                maxAgeSeconds: 60 * 60 * 24 * 30,
                purgeOnQuotaError: true
              },
              cacheableResponse: { statuses: [0, 200] }
            }
          }
        ]
      }
    })
  ]
});
