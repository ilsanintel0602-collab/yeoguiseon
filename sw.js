/* 여기선 v5.1 — Service Worker (Stale-While-Revalidate + 정책 변경 알림)
   - 룰 JSON: 캐시 즉시 반환 + 백그라운드 fresh 검사 + 변경 시 클라이언트 알림
   - 앱 셸: 캐시 우선
   - 외부 API/모델 CDN: 캐시 안 함
*/

const VERSION = 'v5.48';
const APP_SHELL_CACHE = `yeoguiseon-shell-${VERSION}`;
const DATA_CACHE = `yeoguiseon-data-${VERSION}`;

const APP_SHELL = [
  './',
  './app.html',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
];

const DATA_FILES = [
  './data/national_rules.json',
  './data/regions_meta.json',
  './data/region_exceptions.json',
  './data/bag_prices.json',           // 신규 (v5)
  './data/recycle_centers.json',      // 신규 (v5)
  './data/ocr_keywords.json',
  './data/brand_db.json',
];

// ==================== Install ====================
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(Promise.all([
    caches.open(APP_SHELL_CACHE).then((cache) =>
      Promise.all(APP_SHELL.map((url) =>
        cache.add(url).catch((err) => console.warn('[SW] shell 캐시 실패:', url, err))
      ))
    ),
    caches.open(DATA_CACHE).then((cache) =>
      Promise.all(DATA_FILES.map((url) =>
        cache.add(url).catch((err) => console.warn('[SW] data 캐시 실패:', url, err))
      ))
    ),
  ]));
});

// ==================== Activate ====================
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((k) => k.startsWith('yeoguiseon-') && k !== APP_SHELL_CACHE && k !== DATA_CACHE)
        .map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

// ==================== Fetch ====================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  if (!request.url.startsWith('http')) return;

  const url = new URL(request.url);

  // 외부 모델·API: 패스 (캐시 안 함)
  const externalSkip = [
    'api.anthropic.com',
    'generativelanguage.googleapis.com',
    'tensorflow',
    'jsdelivr',
    'tessdata',
    'tesseract',
  ];
  if (externalSkip.some((d) => url.hostname.includes(d) || url.pathname.includes(d))) {
    return; // 네트워크 직통
  }

  // 데이터 JSON: stale-while-revalidate (캐시 즉시 + 백그라운드 fresh)
  if (url.pathname.includes('/data/') && url.pathname.endsWith('.json')) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // 앱 셸 + 기타: cache-first
  event.respondWith((async () => {
    try {
      const cached = await caches.match(request);
      if (cached) return cached;
      const response = await fetch(request);
      if (response && response.ok && response.type !== 'opaque') {
        const cache = await caches.open(APP_SHELL_CACHE);
        cache.put(request, response.clone()).catch(() => {});
      }
      return response;
    } catch (err) {
      const cached = await caches.match(request);
      if (cached) return cached;
      return new Response('Offline', { status: 503 });
    }
  })());
});

// ==================== Stale-While-Revalidate ====================
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DATA_CACHE);
  const cachedResponse = await cache.match(request);

  // 백그라운드 fetch (변경 감지 + 클라이언트 알림)
  const networkPromise = fetch(request)
    .then(async (response) => {
      if (!response || !response.ok) return response;

      // 변경 감지: ETag 또는 본문 길이/해시 비교
      const newETag = response.headers.get('etag');
      const oldETag = cachedResponse ? cachedResponse.headers.get('etag') : null;
      let changed = false;

      if (newETag && oldETag && newETag !== oldETag) {
        changed = true;
      } else if (cachedResponse) {
        // ETag 없으면 본문 비교 (느림, 폴백)
        try {
          const [newText, oldText] = await Promise.all([
            response.clone().text(),
            cachedResponse.clone().text(),
          ]);
          changed = newText !== oldText;
        } catch (_) { /* 무시 */ }
      }

      // 새 응답 캐시 저장
      cache.put(request, response.clone()).catch(() => {});

      if (changed) {
        notifyClients('rules-updated', {
          url: request.url,
          file: new URL(request.url).pathname.split('/').pop(),
          ts: Date.now(),
        });
      }
      return response;
    })
    .catch(() => null);

  // 캐시 있으면 즉시 반환 (네트워크는 백그라운드에서 계속 진행)
  return cachedResponse || networkPromise || fetch(request);
}

// ==================== 클라이언트에 메시지 전송 ====================
function notifyClients(type, data) {
  self.clients.matchAll({ includeUncontrolled: true }).then((clients) => {
    for (const client of clients) {
      client.postMessage({ type, data });
    }
  });
}

// ==================== 수동 동기화 메시지 ====================
self.addEventListener('message', (event) => {
  if (!event.data) return;
  if (event.data.type === 'CHECK_UPDATES') {
    // 앱이 직접 요청한 데이터 fresh 검사
    Promise.all(DATA_FILES.map((url) => fetch(url, { cache: 'no-cache' })))
      .then((responses) => {
        const cache = caches.open(DATA_CACHE);
        return Promise.all(responses.map((r, i) => {
          if (r && r.ok) {
            return cache.then((c) => c.put(DATA_FILES[i], r.clone()));
          }
        }));
      })
      .then(() => notifyClients('check-complete', { ts: Date.now() }))
      .catch(() => {});
  } else if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// ==================== Periodic Background Sync (옵션, 권한 필요) ====================
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'sync-rules') {
    event.waitUntil(
      Promise.all(DATA_FILES.map((url) =>
        fetch(url, { cache: 'no-cache' }).then((r) => {
          if (r && r.ok) {
            return caches.open(DATA_CACHE).then((c) => c.put(url, r.clone()));
          }
        }).catch(() => {})
      ))
    );
  }
});
