# D1 마이그레이션 셋업 — 사용자 액션 (15분 1회)

> **목표:** 정적 JSON → 진짜 DB (Cloudflare D1). 영원히 자동.

## 📋 사용자 액션 단 1회

### Step 1: Wrangler CLI 설치 (5분)

PC 명령창(cmd 또는 PowerShell):

```bash
npm install -g wrangler
```

(Node.js 없으면: https://nodejs.org 에서 LTS 버전 설치)

확인:
```bash
wrangler --version
```

---

### Step 2: Cloudflare 로그인 (1분)

```bash
wrangler login
```

브라우저에서 Cloudflare 계정 인증 → 자동 토큰 발급.

---

### Step 3: D1 데이터베이스 생성 (1분)

```bash
cd /d "E:\Cowork 작업\yeoguiseon-v4"
wrangler d1 create yeoguiseon-db
```

출력 예:
```
✅ Successfully created DB 'yeoguiseon-db'
[[d1_databases]]
binding = "DB"
database_name = "yeoguiseon-db"
database_id = "abc-123-def-456-..."  ← 이 UUID 복사!
```

---

### Step 4: wrangler.toml 셋업 (2분)

1. `scripts/wrangler.toml.template`을 프로젝트 루트에 **`wrangler.toml`** 로 복사
2. `YOUR_DATABASE_ID_HERE` 부분을 Step 3에서 받은 UUID로 교체
3. (선택) KV namespace ID도 채우기:
   ```bash
   wrangler kv namespace list
   ```
   에서 RATE_LIMIT_KV ID 확인 → wrangler.toml에 입력

---

### Step 5: D1에 데이터 마이그레이션 (3분)

```bash
wrangler d1 execute yeoguiseon-db --remote --file=data/migrations/v7_initial.sql
```

→ 765 items + 8,529 aliases + 250 regions + 53 region_exceptions 자동 삽입.

확인:
```bash
wrangler d1 execute yeoguiseon-db --remote --command="SELECT COUNT(*) FROM items"
```

---

### Step 6: Worker 재배포 (2분)

```bash
wrangler deploy
```

또는 Cloudflare 대시보드에서 v1.9 코드 (이미 push됨) 복사 붙여넣기 + 배포.

이제 Worker가 D1 binding (`env.DB`)을 인식.

---

## ✅ 셋업 완료 후 확인

브라우저에서:
```
https://yeoguiseon-proxy.ilsanintel0602.workers.dev/data/items/notebook
```
→ 노트북 데이터 JSON 응답이 오면 성공!

```
https://yeoguiseon-proxy.ilsanintel0602.workers.dev/data/search?q=노트북
```
→ alias 매칭 결과.

---

## 🎯 그 후 영원히 자동

| 작업 | 자동? |
|---|---|
| 데이터 조회 | ✅ D1 직접 (정적 JSON 폐기) |
| 매주 데이터 갱신 | ✅ GitHub Actions cron |
| Worker 캐싱 | ✅ KV 24h |
| 검증 | ✅ 자동 |

사용자 작업 0건/주.

---

## 🐛 트러블슈팅

### "command not found: wrangler"
- Node.js 설치 → `npm install -g wrangler` 다시

### "binding DB not configured"
- wrangler.toml의 database_id 채웠는지 확인
- `wrangler deploy` 다시

### "no such table: items"
- `--remote` 옵션 꼭 (D1은 로컬·원격 분리)
- migrations/v7_initial.sql 실행했는지 확인
