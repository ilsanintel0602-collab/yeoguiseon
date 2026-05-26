# Worker Edge Cache 설계 — Gemini 응답 30~50% ↑ 추가 속도

## 배경 (사용자 v5.44 호소)

> "카메라를 누르면 인식이 늦거나 인식실패해요"

**v5.45 customBox crop**: drag 영역만 분석 → 정확도 ↑
**v5.46.1 480px 압축**: 전송량 -40% → 응답 30% ↑
**v5.46.x edge cache** (이번 설계): 같은 사진 = 즉시 응답 (0초)

## 핵심 아이디어

같은 사용자가 같은 사진을 다시 찍을 가능성 (특히 시연·재시도) — Gemini 호출 X, 캐시된 응답 즉시 반환.

## 구현 (Cloudflare Worker + KV)

### 키: 이미지 SHA-256 해시

```js
async function imageHash(base64) {
  const buf = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
  const hashBuf = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(hashBuf))
    .map(b => b.toString(16).padStart(2, '0')).join('');
}
```

### KV 저장 (TTL 7일)

```js
// 캐시 키: "img:{first16}" (앞 16자만, 충돌 0)
const cacheKey = 'img:' + (await imageHash(base64)).slice(0, 16);
const cached = await env.RATE_LIMIT_KV.get(cacheKey, 'json');
if (cached) {
  log('cache_hit', { key: cacheKey });
  return new Response(JSON.stringify({ ...cached, _cache: 'hit' }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

// Gemini 호출 후 캐시 저장
await env.RATE_LIMIT_KV.put(cacheKey, JSON.stringify(parsed), {
  expirationTtl: 7 * 24 * 60 * 60  // 7일
});
```

### 클라이언트 응답 라벨

캐시 hit 시 `_cache: 'hit'` 필드로 사용자에게 "⚡ 빠른 캐시" 배지 (이미 v5.20에 cache 배지 있음).

## 효과 예측

| 시나리오 | 비용·시간 |
|---|---|
| 새 사진 (첫 분석) | Gemini API 호출, ~2초 |
| **같은 사진 재시도** (캐시 hit) | KV lookup, ~50ms = **40배 빠름** |
| 비슷한 사진 (다른 hash) | Gemini 새로 호출 |

**비용**: KV write·read 무료 (Cloudflare 무료 한도 내).

## 부수 효과

- **Gemini API 호출 절감** — 비용 ↓
- **rate limit 회피** — 사용자 30회 분당 룰 절약
- **시연 반복 빠름** — 같은 사진 검증 시 즉시

## 위험·고려

1. **개인정보**: KV에 이미지 해시 + 응답만 (이미지 X). 안전.
2. **중복 키 충돌**: SHA-256 first 16 chars = 2^64 공간 → 충돌 ~0
3. **사용자별 캐시 X**: 같은 사진 = 같은 응답 (정확). 사용자별 다르게 할 필요 X.

## 구현 위치

`scripts/cloudflare_worker.js`의 메인 POST 핸들러:
```js
// 1. 요청 받음
// 2. base64 추출 → 해시
// 3. KV.get(cacheKey) → hit 시 즉시 반환
// 4. miss 시 Gemini 호출
// 5. 응답 → KV.put + 사용자 반환
```

작업량: 30분 (Worker 패턴 그대로, KV 이미 바인딩됨).

## 권장 시점

- 시연 결과 **속도 호소 지속** 시 → 즉시 적용
- 시연 결과 OK시 → 다음 큰 작업과 묶음

## v5.46.x 시리즈

- v5.46 = tier 라벨 + 정직성
- v5.46.1 = prompts.js 분리 + 480px 압축
- **v5.46.2 (proposed)** = Worker edge cache + KV TTL
