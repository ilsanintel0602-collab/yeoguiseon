# 자동 크롤링 인프라 셋업 — 사용자 액션 2회 (10분)

> 한 번 셋업하면 **영원히 자동**. 매주 일요일 새벽 data.go.kr에서 5개 영역 자동 크롤링 → GitHub 자동 commit.

## ✅ 사용자 액션 단 2회

### 액션 1: data.go.kr API 키 신청 (5분)

1. https://www.data.go.kr 로그인 (이미 함)
2. 검색: **"폐의약품 수거함"**
3. 결과에서 **"오픈 API"** 라벨 있는 항목 클릭 (CSV 아님!)
4. **"활용 신청"** 버튼 클릭
5. 사용 목적 입력:
   ```
   여기선 분리수거 PWA 앱에서 폐의약품 수거함 위치 안내
   ```
6. **신청 → 자동 승인** (대부분 즉시, 또는 1~2일)
7. **마이페이지 → 개발계정 → 인증키(serviceKey) 복사**

같은 절차로 4개 더 신청:
- "의류수거함"
- "무인회수기" (또는 "IoT 페트병")
- "폐형광등 수거함"
- "폐건전지 수거함"

(같은 API 키 하나로 모두 사용 가능)

### 액션 2: GitHub Secrets에 API 키 등록 (3분)

1. https://github.com/ilsanintel0602-collab/yeoguiseon 접속
2. **Settings** 탭 (저장소 상단)
3. 좌측 메뉴 **Secrets and variables** → **Actions**
4. **"New repository secret"** 클릭
5. 입력:
   - Name: `DATA_GO_KR_API_KEY`
   - Secret: (data.go.kr에서 복사한 serviceKey)
6. **"Add secret"** 클릭

### (선택) endpoint URL 등록

각 영역별 API 활용 신청하면 **요청 URL**이 나옵니다. 그걸 GitHub Secrets에 추가:
- `ENDPOINT_MEDICINE` = 폐의약품 API URL
- `ENDPOINT_CLOTHES` = 의류수거함 API URL
- `ENDPOINT_IOT` = 무인회수기 API URL
- `ENDPOINT_LAMP` = 폐형광등 API URL
- `ENDPOINT_BATTERY` = 폐건전지 API URL

(코드에 기본 endpoint 들어 있지만 실제 URL 다를 수 있어 안전하게 환경변수)

---

## 🚀 첫 자동 실행 (수동 트리거)

1. GitHub repo → **Actions** 탭
2. 좌측 메뉴 **"주간 자동 데이터 크롤링 (data.go.kr API)"** 선택
3. 우측 **"Run workflow"** 버튼 → **"Run workflow"**
4. 1~2분 후 자동 commit 됨 (`🤖 weekly auto-crawl: ...`)

확인:
- `data/medicine_bins.json` 등 5개 파일 생성됨
- GitHub Pages 자동 빌드 후 모바일 PWA에 자동 반영

---

## ⏰ 자동 실행 시간

- **매주 일요일 새벽 3시 (한국시간)**
- 사용자 작업 0
- 변경 있으면 자동 commit + push
- 변경 없으면 commit 안 함

---

## 🐛 트러블슈팅

### "endpoint 미설정 — SKIP"

GitHub Secrets에 `ENDPOINT_MEDICINE` 등 추가하면 해결. 또는 코드의 기본 endpoint 그대로 사용.

### "API 호출 실패"

- API 키가 정확한지 확인
- 신청 후 *승인* 됐는지 마이페이지에서 확인 (보통 즉시)
- 일일 호출 제한 (보통 1000회/일) 충분

### "데이터가 비어있어요"

- 영역별 활용 신청 안 됨 → data.go.kr 마이페이지에서 확인
- 또는 endpoint URL이 다름 → 마이페이지 → 신청 내역 → 요청 URL 확인 → GitHub Secrets 갱신

---

## 🎯 효과

| Before | After |
|---|---|
| 수동 CSV 다운 5번 | 자동 (사용자 작업 0) |
| 매주 수동 push | 자동 commit |
| 신규 데이터 늦음 | 주간 자동 갱신 |
| 사람 실수 (60+ 잘못 매핑) | API라 자동 무결성 |

---

## 다음 단계 (Phase B 인프라)

- Cloudflare KV로 데이터 이전 (실시간 갱신)
- 다중 AI 모델 앙상블 (Gemini + Claude)
- 사용자 피드백 → 자동 보강 파이프라인
- 모니터링 (Sentry, Cloudflare Analytics)
