/* Oflayn ishlash: sahifa va so'zlar avval tarmoqdan (yangilanish uchun), bo'lmasa keshdan.
   Audio fayllar ?v=<hash> bilan keladi — ular o'zgarmaydi, shuning uchun avval keshdan. */
const CACHE = 'ruski-v1';
const CORE = ['./', 'index.html', 'words.json', 'audio/index.json', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function put(req, res){
  const c = await caches.open(CACHE);
  if (new URL(req.url).searchParams.has('v')){ // eski versiyadagi shu faylni o'chiramiz
    const path = new URL(req.url).pathname;
    for (const k of await c.keys()) if (new URL(k.url).pathname === path) await c.delete(k);
  }
  await c.put(req, res);
}

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin || req.headers.has('range')) return;
  if (url.searchParams.has('v')){
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok) e.waitUntil(put(req, res.clone()));
      return res;
    })));
    return;
  }
  e.respondWith(fetch(req).then(res => {
    if (res.ok) e.waitUntil(put(req, res.clone()));
    return res;
  }).catch(() => caches.match(req).then(hit => hit || (req.mode === 'navigate' ? caches.match('index.html') : Response.error()))));
});
