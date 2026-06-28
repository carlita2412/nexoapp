import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  integrations: [
    tailwind({ applyBaseStyles: false }),
  ],
  vite: {
    plugins: [
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.svg'],
        manifest: {
          name: 'Nexo PWA',
          short_name: 'Nexo',
          description: 'PWA offline-first para coordinación de ayuda médica.',
          theme_color: '#0f172a',
          background_color: '#f8fafc',
          display: 'standalone',
          orientation: 'portrait',
          start_url: '/',
          scope: '/',
          icons: [
            {
              src: '/pwa-192.svg',
              sizes: '192x192',
              type: 'image/svg+xml',
              purpose: 'any maskable'
            },
            {
              src: '/pwa-512.svg',
              sizes: '512x512',
              type: 'image/svg+xml',
              purpose: 'any maskable'
            }
          ]
        },
        workbox: {
          navigateFallback: '/',
          globPatterns: ['**/*.{js,css,html,svg,png,ico,json}'],
          runtimeCaching: [
            {
              urlPattern: ({ request }) => request.destination === 'document',
              handler: 'NetworkFirst',
              options: {
                cacheName: 'nexo-paginas',
                networkTimeoutSeconds: 4,
              }
            },
            {
              urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/sync/'),
              handler: 'NetworkOnly',
            },
            {
              urlPattern: ({ url }) => url.pathname.startsWith('/api/v1/'),
              handler: 'NetworkFirst',
              options: {
                cacheName: 'nexo-api-lectura',
                networkTimeoutSeconds: 4,
                expiration: {
                  maxEntries: 80,
                  maxAgeSeconds: 60 * 60,
                }
              }
            },
            {
              urlPattern: ({ request }) => ['script', 'style', 'worker', 'font'].includes(request.destination),
              handler: 'StaleWhileRevalidate',
              options: { cacheName: 'nexo-shell' }
            }
          ]
        },
        devOptions: {
          enabled: true
        }
      })
    ]
  }
});
