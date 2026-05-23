# HANDOFF 2026-05-22 v17 — A2 cron 완전 활성 + A1-2 진입 대기

> 다음 세션은 이 문서 + project_v4_status 메모리 2개로 큰 그림 즉시 파악.
> **첫 작업: data.go.kr 비밀번호 재설정 → A1-2 진입.**

---

## ✅ 이번 세션 성과 (2026-05-22)

### Phase A2 cron — 완전 활성 ⭐
- Worker **v1.9.5 → v1.9.6.1** (코드 + 핫픽스 1회)
- `scheduled()` 핸들러 + 두 cron 등록 라이브:
  - `5 15 * * *` (KST 00:05) — D1/KV 카운트 → `metrics:daily:YYYY-MM-DD` (90일 TTL)
  - `0 */6 * * *` — 빈/이상 캐시(`item_id=unknown`) 청소 안전망
- `/admin/health` 엔드포인트 — 평생 북마크용 모니터링
- `/feedback/dump` 변수명 버그(`url`→`reqUrl`) 핫픽스
- `/admin/health` + `/feedback/dump` Origin 검증 순서 핫픽스 (v1.9.6.1)
- 검증 완료: `worker_version: "v1.9.6.1"`, `d1_bound: true`, `kv_bound: true` 응답 확인

### push 전 자체점검 강화
- `quick_check.py` 동적 버전 일치 검사(sw.js↔app.html)
- Worker JS 문법 검사 추가
- PRESERVE_1CHAR 보강(밥·국·껌·백·캡)
- 모든 검사 통과 (exit=0)

### Cloudflare Worker URL
- 운영: `https://yeoguiseon-proxy.ilsanintel0602.workers.dev`
- 모니터링: `https://yeoguiseon-proxy.ilsanintel0602.workers.dev/admin/health`
- Current Version ID: `ea3ea666-db69-4d06-aee1-923cc2b5da12`

---

## ⚠️ 이번 세션 발견된 사실 (메모리 박힘)

### D1 ↔ 정적 JSON drift
- D1: **761 items / 8,516 aliases** (v5.30.2 시점 멈춤)
- 정적 JSON: **771 items / 8,698 aliases** (라이브 검색에 사용)
- 차이 +10 items / +182 aliases
- **메모리 정정**: "D1 비어있음" → "D1은 옛 데이터로 멈춤". 라이브 검색은 정적 JSON.
- D1 우선 복귀 시 **재마이그레이션 필수** (정확도 하락 방지). 메모리 `project_d1_drift.md` 참고.

### Edit 도구 한국어 truncation
- 한국어 큰 블록 Edit 시 끝부분 byte 단위 잘림 두 번 발생
- 회복 절차: `wc -l` + `python3 -c "import ast; ast.parse(...)"` 즉시 검증, 필요 시 Python 재구성
- 메모리 `feedback_edit_korean_truncation.md` 박힘

---

## ⏳ A1-2 + C1 진입 — 사용자 대기 (다음 세션 첫 작업)

### 합리적 진행 방향 (이번 세션에서 결정)

**Worker 자동 크롤 방식** (옛 SETUP_BINS.md의 3줄 명령 방식 대체):
- 사용자 작업: API key 발급 + Cloudflare Worker secret 등록 **5분 1회만**
- 그 후 Worker cron이 주간 자동 크롤 + D1 입력
- 가이드: `docs/SETUP_BINS_v2_AUTO.md` 작성됨

### 사용자 다음 단계 (5분)

1. **data.go.kr 비밀번호 재설정** (이번 세션 4회 틀려서 1회 남음 — 락 회피)
   - https://www.data.go.kr/uat/uia/joinUsr/loginSerch.do
   - 이메일(`ilsanintel0602@gmail.com`) 또는 휴대폰 본인인증
   - 임시 비밀번호 → 새 비밀번호 설정
2. 가입 이력 없을 가능성 → 아이디 찾기 먼저, 없으면 회원가입(무료, 1분)
3. 로그인 후 5개 데이터셋 활용신청:
   - "폐의약품 수거함"
   - "의류수거함"
   - "무인회수기"
   - "폐형광등 수거함"
   - "폐건전지 수거함"
4. 마이페이지 → 인증키 → **General 인증키** 복사
5. Cloudflare 대시보드 → Workers → yeoguiseon-proxy → Settings → Variables and Secrets → Add Secret:
   - Name: `DATA_GO_KR_API_KEY`
   - Value: 복사한 키

### 사용자 작업 끝나면 Claude가 자동 진행

1. `/admin/probe-bins?key=...` 엔드포인트로 응답 사이즈 측정 (Worker CPU time 안전 설계 근거)
2. Worker `/admin/crawl-bins` 핸들러 + 주간 cron 추가 (코드 작성)
3. 한 묶음 push + `wrangler deploy` → 첫 크롤 트리거
4. C1 GPS UI 자동 활성 (app.html에 이미 `navigator.geolocation` 4곳 준비됨)
5. 검증: `/admin/health`에 bins 카운트 + last_crawl 추가

---

## 🗺 마스터 플랜 위치 (현재)

```
Phase A 인프라             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 85%
  A1 D1 [✅]  A2 Worker cron [✅ ⭐]  A1-2 bins [⏳ 사용자 API key 대기]
  A1-3 bag_prices [⏳]  A3 자동 검증 [⏳ yml 수동]  A4 KV [✅]
Phase B AI                 ━━━━━━━━━━━━━━━━━━━ 65%
  B1 앙상블 [✅]  B-aux 검색 100% [✅]  B4 학습 인프라 [✅]
  B2 CNN [⏳]  B3 벡터 [⏳]
Phase C UX                 ━━━━━━━━━━━━━━━━━━━━━ 75%
  C1 GPS [⏳ bins 대기]  C2 음성 [✅]  C4 onboard [✅]  C5 Discoverability [✅]
Phase D 운영               ━━━━━━━━━━━━━━ 45%
  D1 Sentry [⏳]  D2 벤치마크 [✅]  D3 헬스 /admin/health [✅ ⭐]
Phase E 데이터             ━━━━━━━━━━━━━━━━━━━━ 70%
  E1 backup [⏳]  E2/E3 오염 정리 [✅]
```

---

## 💬 다음 세션 첫 인사 (복붙용)

```
경숙님! v5.32 라이브 + Phase A2 cron 완전 활성 (Worker v1.9.6.1).
다음 작업: A1-2 + C1 패키지 진입.

대기 중인 사용자 작업:
1. data.go.kr 비밀번호 재설정 (4회 틀려서 1회 남음 — 락 회피 우선)
2. 5개 데이터셋 활용신청 + 인증키 복사
3. Cloudflare Worker secret에 DATA_GO_KR_API_KEY 등록

가이드: docs/SETUP_BINS_v2_AUTO.md (5분 한 번에 끝)

비밀번호 재설정부터 시작할까요?
```

---

## 📂 이번 세션에서 변경/생성된 파일

- `scripts/cloudflare_worker.js` (v1.9.5 → v1.9.6.1)
- `wrangler.toml` (`[triggers] crons` 추가)
- `scripts/quick_check.py` (동적 버전 검사 + JS 문법 검사 + PRESERVE_1CHAR 보강)
- `docs/HANDOFF_2026-05-22_v16_A2cron.md` (cron 가동 1차 가이드)
- `docs/HANDOFF_2026-05-22_v17_A2done_A1-2pending.md` (이 파일)
- `docs/SETUP_BINS_v2_AUTO.md` (A1-2 새 방식 — 사용자 5분 1회)

이미 GitHub push + Cloudflare deploy 완료. 로컬과 라이브 동기화됨.

---

## 🔧 알려진 함정 (메모리 박힘 — 다음 세션 자동 참조)

- D1 ↔ 정적 JSON drift (10 items / 182 aliases 차이)
- Edit 도구 한국어 큰 블록 truncation
- `.github/workflows/*.yml` PAT workflow 권한 부족 → Worker cron으로 우회
- CSS stacking context (backdrop-filter·opacity·transform → 모달 input 클릭 차단)
- D1 호환성 (BEGIN/COMMIT + self-ref FK 거부)

---

## 다음 큰 옵션 (A1-2 완료 후)

1. **B2 자체 CNN** (1주, 사진 정확도 점프) — B4 인프라 위
2. **B3 한국어 벡터 검색** (3-5일, semantic) — 검색 100% 위 추가
3. **모바일 v5.32 + cron metrics 검증 피드백** (10분, 시간 의존)
4. **A1-3 bag_prices** (종량제봉투 가격) — 작은 작업
