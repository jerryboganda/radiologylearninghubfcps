const CACHE = 'radbrain-shell-v1';
const PRECACHE = ['/manifest.webmanifest', '/favicon.svg', '/offline'];
const ASSET_EXTENSIONS = /\.(?:avif|css|gif|ico|jpe?g|js|mjs|png|svg|webp|woff2?)$/iu;

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/_app/') || ASSET_EXTENSIONS.test(url.pathname);
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/offline')));
    return;
  }
  if (!isStaticAsset(event.request)) return;
  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request).then((response) => {
          if (response.ok) {
            const copy = response.clone();
            void caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
    )
  );
});
