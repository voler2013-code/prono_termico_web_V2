const CACHE_NAME = "prono-termico-v4-skewt-250";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./skewt.js",
  "./skewt-view.js",
  "./skewt_data.py",
  "./worker.mjs",
  "./manifest.webmanifest",
  "./requests.py",
  "./prono_core.py",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith("prono-termico-") && key !== CACHE_NAME)
      .map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Open-Meteo y Pyodide se consultan por red; los archivos propios se cachean.
  if (url.origin !== self.location.origin) return;

  if (req.method !== "GET") return;
  event.respondWith((async () => {
    // Consultar solo la versión activa; una petición vieja podría recrear otra caché.
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(req);
    if (cached) return cached;
    const response = await fetch(req);
    if (response.ok) await cache.put(req, response.clone());
    return response;
  })());
});
