# Phase A1-2: bins (수거함 위치) D1 입력 가이드

> **목표:** 행안부 폐의약품·의류·IoT·형광등·건전지 수거함 데이터를 D1에 채워서 Phase C1 (GPS+지도) 진입 가능하게 만들기.
> **사용자 작업:** 명령 3줄 (약 15분).

---

## 사전 조건

- ✅ D1 인프라 (어제 완료)
- ✅ Worker v1.9.3
- ✅ bins 테이블 스키마 (이미 D1에 있음, 비어있음)
- ⏳ DATA_GO_KR_API_KEY (data.go.kr 회원가입 + 표준데이터셋 신청)

---

## Step 1 — DATA_GO_KR_API_KEY 발급 + 등록

### 1-A: data.go.kr API 키 발급 (5분)

1. https://www.data.go.kr/ 접속 → 로그인 (회원가입 무료)
2. 검색창에 **"폐의약품 수거함"** → 표준데이터셋 결과 클릭
3. 우측 **"인증키 신청"** → 활용신청서 작성 → 즉시 발급
4. 같은 방법으로 다음 4개 데이터셋도 신청 (각 1분):
   - "의류수거함"
   - "무인회수기" (또는 "IoT 페트병")
   - "폐형광등 수거함"
   - "폐건전지 수거함"
5. 마이페이지 → 인증키 → **General 인증키** 복사 (모든 데이터셋 공유 키)

### 1-B: GitHub Secret + Cloudflare Worker Secret 등록 (5분)

**GitHub** (cron 자동 크롤용):
1. https://github.com/ilsanintel0602-collab/yeoguiseon/settings/secrets/actions
2. **"New repository secret"** 클릭
3. Name: `DATA_GO_KR_API_KEY`, Value: 복사한 키 → Save

**Cloudflare Worker** (수동 호출용, 선택):
1. https://dash.cloudflare.com/ → Workers & Pages → yeoguiseon-proxy
2. Settings → Variables and Secrets → **"Add"**
3. Type: **Secret**, Name: `DATA_GO_KR_API_KEY`, Value: 키 → Save

---

## Step 2 — 5개 영역 크롤 (한 줄)

명령창에서:

```cmd
cd /d "E:\Cowork 작업\yeoguiseon-v4"
set DATA_GO_KR_API_KEY=발급받은_키_여기에_붙여넣기

python scripts\crawl_data_go_kr_api.py --area medicine --output data\medicine_bins.json
python scripts\crawl_data_go_kr_api.py --area clothes  --output data\clothes_bins.json
python scripts\crawl_data_go_kr_api.py --area iot      --output data\iot_bins.json
python scripts\crawl_data_go_kr_api.py --area lamp     --output data\lamp_bins.json
python scripts\crawl_data_go_kr_api.py --area battery  --output data\battery_bins.json
```

→ 각 영역당 1~3분 (행안부 데이터 양에 따라). 5개 JSON 생성됨.

---

## Step 3 — D1 입력 (자동 변환 → SQL → wrangler)

자동 변환 스크립트는 이미 만들어 두었어요. 한 줄:

```cmd
python scripts\bins_to_sql.py
wrangler d1 execute yeoguiseon-db --remote --file=data\migrations\bins_initial.sql
```

→ 5개 영역 데이터가 D1 `bins` 테이블에 입력됨.

---

## 확인 (선택)

```cmd
wrangler d1 execute yeoguiseon-db --remote --command="SELECT area_type, COUNT(*) FROM bins GROUP BY area_type"
```

출력 예:
```
┌────────────┬──────────┐
│ area_type  │ COUNT(*) │
├────────────┼──────────┤
│ battery    │ 3245     │
│ clothes    │ 12450    │
│ iot        │ 856      │
│ lamp       │ 1820     │
│ medicine   │ 5670     │
└────────────┴──────────┘
```

---

## 그 후 자동으로 활성화되는 것

- ✅ **Phase A2 cron** (다음 단계) — 매주 자동 갱신
- ✅ **Phase C1 GPS + 지도** (다음 단계) — bins 데이터 기반 가까운 수거함 표시

---

## 🐛 트러블슈팅

### "API 키가 유효하지 않습니다"
- data.go.kr 마이페이지에서 인증키 발급 상태 확인
- 신청 후 활성화까지 1~3시간 걸릴 수 있음

### "데이터셋 인증되지 않음"
- 영역별로 각각 활용신청해야 함 (5개 모두)

### "Connection timeout"
- 행안부 서버 부하 시간대 (낮 시간) → 새벽이나 저녁에 재시도
