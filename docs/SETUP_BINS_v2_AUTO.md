# Phase A1-2 + C1 — 수거함 데이터 자동 입력 (v2: Worker cron 방식)

> 기존 `SETUP_BINS.md`(사용자 매주 명령 3줄)를 Worker cron 자동화로 대체.
> **사용자 작업은 5분 1회만** — 그 후 매주 자동 갱신.

---

## 사용자가 할 일 (총 5분, 평생 1회)

### Step 1 — data.go.kr API key 발급 (3분)

1. https://www.data.go.kr/ 접속 → **로그인** (회원가입 무료, 1분)
2. 검색창에 **"폐의약품 수거함"** → 결과 클릭 → 우측 **"활용신청"** → 즉시 발급
3. 같은 방식으로 4개 더 신청 (각 30초):
   - **"의류수거함"**
   - **"무인회수기"** (또는 "IoT 페트병")
   - **"폐형광등 수거함"**
   - **"폐건전지 수거함"**
4. 마이페이지 → **인증키** → "General 인증키" 복사 (5개 데이터셋 공유 키)

### Step 2 — Cloudflare Worker Secret 등록 (2분)

1. https://dash.cloudflare.com/ → **Workers & Pages** → **yeoguiseon-proxy**
2. **Settings** → **Variables and Secrets** → **Add**
3. Type: **Secret**, Name: `DATA_GO_KR_API_KEY`, Value: 복사한 키 → **Save**

(GitHub Secret은 안 해도 됨 — Worker cron 방식이라 GitHub Actions 불필요)

### Step 3 — 첫 크롤 트리거 (브라우저 1번)

(Worker 크롤 핸들러 배포 후) 브라우저로:
```
https://yeoguiseon-proxy.ilsanintel0602.workers.dev/admin/crawl-bins?key=발급받은_키
```

→ JSON 응답에 `{"ok":true, "inserted":<카운트>}` 나오면 끝.
→ 이후 매주 일요일 03:00 KST에 자동 갱신.

---

## 그 후 자동 활성화

- ✅ **C1 GPS UI** — bins 데이터 들어가는 즉시 app.html에서 자동 활성 (현재 코드에 이미 `navigator.geolocation` 흐름 4곳 준비됨)
- ✅ **주간 자동 갱신** — Worker cron `0 18 * * 6` (토요일 18:00 UTC = 일요일 03:00 KST)
- ✅ **모니터링** — `/admin/health`에 `last_crawl` 필드 추가됨, 카운트·실패 즉시 확인

---

## 비교: 옛 방식 vs 새 방식

| 항목 | 옛 SETUP_BINS.md | v2 Worker cron |
|---|---|---|
| 첫 셋업 | 사용자 PC 명령 3줄 (15분) | 브라우저 1번 (5분) |
| 매주 갱신 | 사용자 매주 명령 3줄 | **자동** |
| GitHub Actions 의존 | yml 수동 업로드 필요 (PAT workflow 권한) | 불필요 |
| 의존성 | wrangler · python · D1 CLI | Worker 하나 |

---

## ⚠️ 주의

- API key는 발급 후 **활성화까지 1~3시간** 걸릴 수 있음 (data.go.kr 안내)
- 5개 데이터셋 **각각** 활용신청해야 함 (한 번에 안 됨)
- Cloudflare Worker secret은 한 번 등록하면 평생 안 봄 (사용자 메모리 룰)
