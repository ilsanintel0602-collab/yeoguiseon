# 행안부 data.go.kr 5개 영역 받기 — 완전 가이드

> 한 번 회원가입 + 5번 CSV 다운로드 + 5번 스크립트 = 행안부 표준 데이터 완비

## 🎯 받을 5개 데이터

| 순서 | 영역 | 검색어 | 효과 |
|---|---|---|---|
| 1 | 폐의약품 수거함 | "폐의약품 수거함" | 약 분류 시 가까운 약국·보건소 |
| 2 | 의류수거함 | "의류수거함" 또는 "헌옷" | 옷 분류 시 가까운 수거함 |
| 3 | 무인회수기 (페트병) | "무인회수기" 또는 "IoT 페트병" | 페트병 인센티브 안내 |
| 4 | 폐형광등 수거함 | "폐형광등 수거함" | 형광등 분류 시 위치 |
| 5 | 폐건전지 수거함 | "폐건전지 수거함" | 건전지 분류 시 위치 |

## 📋 사전 준비 (1회만)

### 1. data.go.kr 회원가입 (5분)

1. https://www.data.go.kr 접속
2. 우측 상단 **"회원가입"** 클릭
3. 본인인증 (휴대폰)
4. 이메일·비밀번호 설정 → 완료

### 2. 폴더 만들기

PC 파일 탐색기에서:
```
E:\Cowork 작업\yeoguiseon-v4\scripts\raw_data\
```
폴더 없으면 새로 만들기 (마우스 우클릭 → 새 폴더).

---

## 📥 영역별 다운로드 + 변환 (각 5분)

### 영역 1: 폐의약품 수거함

**Step 1. 검색**
- data.go.kr 메인 → 검색창 → **"폐의약품 수거함"** 검색

**Step 2. 표준 데이터셋 찾기**
- 결과 화면에서 **"표준 데이터셋"** 라벨 있는 항목 클릭
- 제목 예: "전국폐의약품수거함표준데이터" 또는 비슷

**Step 3. publicDataPk 확인**
- 브라우저 주소창 확인: `https://www.data.go.kr/data/{숫자}/standard.do`
- {숫자}가 publicDataPk (예: 15012005)
- 메모해두기 (선택)

**Step 4. CSV 다운로드**
- 페이지 중간에 **"CSV 다운로드"** 버튼 클릭
- 다운로드 폴더에서 파일 받아짐 (예: `전국폐의약품수거함표준데이터.csv`)
- 파일을 다음 위치로 *복사+이름변경*:
  ```
  E:\Cowork 작업\yeoguiseon-v4\scripts\raw_data\medicine.csv
  ```

**Step 5. 변환 실행 (PC 명령창)**

PC에서 *시작 → cmd 입력 → 검은 창*:
```
cd /d "E:\Cowork 작업\yeoguiseon-v4"
python scripts\crawl_data_go_kr.py --csv scripts\raw_data\medicine.csv --output data\medicine_bins.json --type medicine
```

**Step 6. 결과 확인**

화면에 다음 출력 나오면 성공:
```
=== 💊 폐의약품 수거함 크롤러 ===
파싱 완료: N건
저장 완료: data/medicine_bins.json
```

---

### 영역 2: 의류수거함

위와 똑같이:
- 검색: "의류수거함" 또는 "헌옷"
- 파일명: `clothes.csv`
- 명령: `--csv scripts\raw_data\clothes.csv --output data\clothes_bins.json --type clothes`

---

### 영역 3~5: 무인회수기 / 폐형광등 / 폐건전지

| 영역 | 파일명 | --type |
|---|---|---|
| 무인회수기 | `iot.csv` | `iot` |
| 폐형광등 | `lamp.csv` | `lamp` |
| 폐건전지 | `battery.csv` | `battery` |

위 영역 1과 동일한 절차.

---

## ✅ 다 받으면 결과

`data/` 폴더에 5개 새 파일:
- `medicine_bins.json`
- `clothes_bins.json`
- `iot_bins.json`
- `lamp_bins.json`
- `battery_bins.json`

→ app.html이 자동으로 fetch (다음 세션 통합 작업 시 자동)

---

## 🐛 트러블슈팅

### "CSV가 인코딩 깨져요"
- 파일 인코딩 자동 감지하니까 보통 OK
- 만약 실패: 메모장으로 열어 "다른 이름으로 저장" → "UTF-8" 선택

### "필수 컬럼 매핑 안 됐어요"
- 가벼운 경고. 데이터는 변환됨
- 컬럼 명이 다른 표준 데이터셋도 자동 매핑

### "다운로드 안 됨"
- 회원가입 확인
- 로그인 상태 확인
- 다른 브라우저 시도 (Chrome / Edge)

---

## 🎁 한 번에 다 끝내는 팁

1. **5개 검색어 다 검색해서 publicDataPk 미리 메모**
2. **5개 CSV 한꺼번에 다운로드**
3. **5개 파일 이름 변경 후 raw_data 폴더로 이동**
4. **5번 명령창 실행 (또는 .bat 만들어서 한 번에)**

가장 시간 효율: **medicine + clothes 2개만 먼저** (가장 가치 큼).

---

## ⏳ 예상 시간

- 1회 회원가입: 5분
- 영역 1개당: 5~10분 (검색 + 다운 + 변환)
- 5개 전체: 30~60분

**핵심: medicine + clothes (15분)** → 큰 효과.
