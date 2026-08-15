// 오프라인 지원용 서비스 워커 — 네트워크 우선, 실패하면 저장해 둔 것을 준다.
// 새 버전을 배포할 때는 아래 VERSION 을 바꿔야 옛 캐시가 지워진다 (08_build_reader.py 가 자동으로 바꿔 준다).
const VERSION = 'ts-reader-20260816081158';
const FILES = ['./', './index.html', './manifest.webmanifest', './icon.svg'];
self.addEventListener('install', e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match('./index.html'))));
});
