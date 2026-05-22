# HANDOFF 2026-05-22 v16 — Phase A2 cron 활성 (Worker v1.9.6)

> v15(v5.32) → 이번 푸시는 **A2 cron 자동화 가동**. PAT workflow 권한 무관, `wrangler deploy` 한 줄로 무인 운영 진입.

---

## 🎯 이번 변경 한눈에

| 파일 | 변경 | 효과 |
|---|---|---|
| `scripts/cloudflare_worker.js` | **v1.9.5 → v1.9.6** — `scheduled()` 핸들러 + `/admin/health` + `/feedback/dump` 버그픽스 | 무인 cron 진입, 헬스 모니터링 |
| `wrangler.toml` | `[triggers] crons = ["5 15 * * *", "0 */6 * * *"]` | Cloudflare 자체 cron 활성 |
| `scripts/quick_check.py` | 동적 버전 검사(stale 하드코딩 폐기) + Worker JS 문법 검사 + `PRESERVE_1CHAR` 보강 | push 전 자체검증 강화 |

---

## ⏰ 등록된 cron

| cron (UTC) | KST | 작업 | 저장 위치 |
|---|---|---|---|
| `5 15 * * *` | 매일 00:05 | D1 items/aliases/regions 카운트 + KV 피드백/캐시 카운트 → KV에 기록 | `metrics:daily:YYYY-MM-DD` (90일 TTL) |
| `0 */6 * * *` | 6시간마다 | 빈/이상 응답 캐시(`item_id=unknown`) 청소 | 정리 결과 → `cron:last_run` |

두 cron 모두 실행 종료 시 **`cron:last_run`** KV에 마지막 실행 메타 기록 → `/admin/health`에서 즉시 확인.

---

## 🔍 새 엔드포인트

```
GET https://<worker-host>/admin/health
```

응답 예:
```json
{
  "ok": true,
  "worker_version": "v1.9.6",
  "now": "2026-05-23T00:05:12.345Z",
  "d1_bound": true,
  "kv_bound": true,
  "d1_items_now": 771,
  "d1_aliases_now": 8698,
  "metrics_today": { "date": "2026-05-23", "d1_items": 771, ... },
  "metrics_yesterday": { ... },
  "last_cron": { "cron": "5 15 * * *", "kind": "daily_metrics", "ts": ..., "duration_ms": 234 }
}
```

→ 사용자가 평생 한 번 북마크해두면 끝. 매일 자동 갱신.

---

## 🚀 사용자 명령 (이번 한 번만, 2분)

### 1단계 — GitHub Push (변경 파일 자동 업로드)
```
scripts\auto_push.bat
```
- 더블클릭하면 PAT으로 자동 push (커밋 메시지 자동)
- 푸시 파일: `scripts/cloudflare_worker.js`, `wrangler.toml`, `scripts/quick_check.py`, HANDOFF 등

### 2단계 — Cloudflare Worker 배포 + cron 등록
```
cd "E:\Cowork 작업\yeoguiseon-v4"
npx wrangler deploy
```
- `[triggers] crons`가 wrangler.toml에 있어서 deploy 시 Cloudflare 대시보드 cron 자동 등록
- 결과 확인: `npx wrangler tail` 또는 위 `/admin/health` URL

### 3단계 — 확인 (옵션, 5초)
브라우저 또는 PowerShell:
```
curl https://yeoguiseon-proxy.<your-subdomain>.workers.dev/admin/health
```
→ `worker_version: "v1.9.6"`, `kv_bound: true` 보이면 끝.
→ 다음 날 00:05 KST 이후엔 `metrics_today` 채워짐.

---

## ⚠️ 알려진 경계

- **GitHub Actions yml은 여전히 비활성**: `.github/workflows/*.yml`이 PAT workflow 권한 없어서 자동 push X. Cloudflare Worker cron이 그 역할을 부분 대체. yml이 필요한 경우(주간 데이터 크롤링 등)는 PAT에 `workflow` scope 추가 후 GitHub 웹에서 yml 수동 업로드 1회.
- **Worker cron은 D1과 KV가 둘 다 bind되어야 의미**: 현재 `wrangler.toml`에 둘 다 있음. ✅
- **첫 metrics 기록은 다음 자정 KST 이후**: 그 전엔 `/admin/health`의 `metrics_today`가 null.

---

## 📦 quick_check 결과 (push 전 통과 확인)

```
✅ national_rules.json 로드: 771 items
✅ alias 평균: 평균 11.3
✅ 카테고리 enum: 17개 정합
✅ 가짜 item ID 차단: 0건
✅ 일반 catchall: 0개 (의도된 catchall)
✅ 1글자 alias 노이즈: 0건 (옷·약·책·밥·국·껌·백·캡 보존)
✅ 끝 null 바이트: 없음
✅ region_exceptions: 228 시군구, cityGuide 228/228
✅ 행안부 표준 일치 + 이름 매칭 정확
✅ sw.js ↔ app.html 버전 일치: v5.32 = v5.32
✅ _escGlobal / searchByText / _inherits / cityGuide UI 정의
✅ cloudflare_worker.js 문법 OK
========================================
[OK] 모든 검사 통과! push 안전.
```

---

## 🗺 마스터 플랜 위치 (업데이트)

```
Phase A 인프라             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 85%
  A1 D1 [✅]  A1-2 bins [⏳]  A1-3 bag_prices [⏳]
  A2 cron [✅ Worker cron 활성]  A3 자동 검증 [⏳ yml 수동]  A4 KV [✅]
Phase D 운영               ━━━━━━━━━━━━━━ 45%
  D1 Sentry [⏳]  D2 벤치마크 [✅ text 자동]  D3 헬스 [✅ /admin/health]
```

---

## 🎯 다음 옵션 (자동 진입 가능 순)

1. **B2 자체 CNN** (1주, 정확도+속도 점프) — B4 인프라 위에 진행
2. **A1-2 + C1 패키지** (사용자 API key 5분 → 자동 진행) — GPS+수거함 큰 UX
3. **B3 한국어 벡터 검색** (3-5일, semantic matching)
4. **모바일 v5.32 + cron 검증 피드백** (다음 자정 이후)

---

## 💬 다음 세션 첫 인사 템플릿

```
경숙님! v5.32 라이브 + Phase A2 cron 활성 완료.
Worker v1.9.6 — 매일 00:05 KST에 D1/KV 카운트 자동 기록.
/admin/health 북마크해두면 평생 모니터링 끝.

다음 큰 옵션: B2 CNN / A1-2+C1 / B3 벡터 / 모바일 피드백
뭐부터 갈까요?
```
