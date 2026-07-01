const CACHE = 'nexo-campo-v1';
const ASSETS = ['/', '/manifest.webmanifest', '/icon.svg', '/app.js'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copia = res.clone();
        caches.open(CACHE).then((cache) => cache.put(req, copia));
        return res;
      })
      .catch(() => caches.match(req).then((res) => res || caches.match('/')))
  );
});
