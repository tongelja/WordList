// Service worker: makes WordList installable and keeps visited words readable offline.
// Bump VERSION whenever the static files change so phones pick up the new ones.
const VERSION = 'wordlist-v4';
const PRECACHE = [
  '/',
  '/offline/',
  '/favorites/',
  '/static/favorites.js',
  '/api/words.json',
  '/static/styles.css',
  '/static/manifest.webmanifest',
  '/static/icons/icon-192.png',
  '/static/icons/apple-touch-icon.png',
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(VERSION).then(cache => cache.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET') return;

  // Fonts: serve from cache when we have them, otherwise fetch and keep a copy.
  if (url.host === 'fonts.googleapis.com' || url.host === 'fonts.gstatic.com') {
    event.respondWith(cacheFirst(request));
    return;
  }
  if (url.origin !== location.origin) return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request));
  } else {
    // Pages and API: always try the network for fresh data, fall back to the
    // copy saved the last time this word was opened.
    event.respondWith(networkFirst(request));
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok || response.type === 'opaque') {
    const cache = await caches.open(VERSION);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request) {
  const cache = await caches.open(VERSION);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (request.mode === 'navigate') return cache.match('/offline/');
    throw err;
  }
}
