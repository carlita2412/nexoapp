import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import { VitePWA } from '@vite-pwa/astro';

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
          }
        ]
      }
    })
  ]
});
