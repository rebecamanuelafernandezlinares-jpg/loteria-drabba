// Service worker mínimo: la app necesita internet (datos y Zoho), así que no
// guardamos nada en caché; solo mostramos un aviso claro si no hay conexión.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

const OFFLINE = '<!doctype html><html lang="es"><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>Sin conexión</title><body style="font-family:sans-serif;background:#faf7f4;' +
  'color:#1a1a1a;display:flex;min-height:100vh;align-items:center;justify-content:center;' +
  'text-align:center;padding:24px"><div><h2 style="color:#7a1f2e">Sin conexión</h2>' +
  '<p>Conéctate a internet e intenta de nuevo.</p></div></body></html>';

self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).catch(() => new Response(OFFLINE, {
    headers: { 'Content-Type': 'text/html; charset=utf-8' }
  })));
});
