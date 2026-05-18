# 여기선 — 아키텍처 문서

## 시스템 개요

```
┌─────────────────────────────────────────┐
│            브라우저 (PWA-ready)          │
│  ┌─────────────────────────────────┐   │
│  │ app.html (단일 파일, 외부 의존성 0) │   │
│  │  • UI (HTML + 인라인 CSS)         │   │
│  │  • Logic (IIFE JS)              │   │
│  │  • RULES 데이터 (인라인 + 외부)   │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ localStorage                    │   │
│  │  • apiKey, provider             │   │
│  │  • regionCurrent, regionPrevious│   │
│  │  • cache.{hash}.{provider}      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
              ↓ HTTPS
┌─────────────────────────────────────────┐
│   외부 API (사용자 BYO 키)               │
│   • Google Gemini Vision                │
│   • Anthropic Claude Vision             │
└─────────────────────────────────────────┘
```

## 핵심 설계 원칙

### 1. 단일 파일 (Single File Architecture)
- 모든 코드(HTML/CSS/JS/데이터)가 `app.html` 안에
- 외부 fetch 없음 → 404 발생 불가
- Service Worker 없음 → 캐시 충돌 없음

### 2. LLM과 룰 엔진 분리
- **LLM**: "이게 무슨 물건인지" (item_id만 반환)
- **룰 엔진**: "어디에 버려야 하는지" (지역×물건 매트릭스)
- LLM 환각으로 잘못된 카테고리 반환해도 룰 엔진이 차단

### 3. BYO API Key (Bring Your Own Key)
- 서버 없음 → 키 보호 불가 → 사용자가 자기 키 입력
- localStorage에만 저장 (외부 전송 없음)
- 운영 비용 0원

### 4. 이미지 해시 캐싱
- 같은 사진 두 번째부터 LLM 호출 0회
- SHA-256 첫 8바이트 + base64 일부로 해시
- 비용 60~80% 절감

### 5. 60대 친화 UI
- 본문 18px, 헤더 24~28px
- 모든 버튼 56px+ 터치 영역
- 큰 픽토그램, 한국어 우선

## 데이터 흐름

```
사용자 셔터 클릭
   ↓
camera.capture() → 800px JPEG
   ↓
imageHash() → SHA-256 단축
   ↓
LS.get(cacheKey) ───── hit ──→ renderResult() [LLM 호출 0]
   ↓ miss
analyze() → Gemini or Claude
   ↓
parseAiResponse() → { item_id, confidence, fallback_categories }
   ↓
matchRule(itemId, region) → { category, note, steps }
   ↓
LS.set(cacheKey, result)
   ↓
renderResult() → 바텀시트 슬라이드업
```

## 모듈 구조 (IIFE 내부)

```javascript
(function() {
  'use strict';

  // 1. 상수
  const RULES = {...};
  const SYSTEM_PROMPT = `...`;

  // 2. 상태
  const state = {...};
  const LS = {...};

  // 3. UI 헬퍼
  function toast(), $(), openSheet(), closeSheet()

  // 4. 카메라
  async function startCamera(), capturePhoto(), pickFromGallery()

  // 5. AI 분석
  async function analyze(), analyzeGemini(), analyzeClaude()
  function parseAiResponse()

  // 6. 룰 매칭
  function matchRule(), renderResult()

  // 7. 설정
  function openSettings(), saveSettings(), clearAllData()

  // 8. GPS
  function findRegionByCoords(), detectLocation()

  // 9. 초기화
  function init()
})();
```

## 데이터 모델

### RULES.regions
```json
{
  "region_id": {
    "name": "전체 이름",
    "shortName": "약칭",
    "code": "행정코드",
    "boundingBox": { "minLat, maxLat, minLng, maxLng" },
    "officialSource": "URL",
    "phone": "전화번호"
  }
}
```

### RULES.items
```json
{
  "item_id": {
    "name": "한국어 이름",
    "rules": {
      "region_id": {
        "category": "plastic|vinyl|paper|...",
        "note": "주의사항",
        "confidence": "high|medium|low"
      }
    },
    "differenceWarning": true
  }
}
```

## 확장 가능성

### 단기 (~3개월)
- regions 2개 → 56개 (서울 25 + 경기 31)
- items 20개 → 100개
- GPS 박스 매칭 → Kakao Local API

### 중기 (~6개월)
- 전국 226개 시군구
- 자체 LLM 키 + 무료 한도
- 사용자 신고 대시보드

### 장기 (~1년)
- React Native 모바일 앱
- 배출일 푸시 알림
- B2B2C 파트너십 (아파트 관리사무소·이사업체)

## 기술 결정 트레이드오프

| 결정 | 채택 | 포기 |
|---|---|---|
| 단일 파일 vs 모듈 분리 | **단일 파일** | 모듈식 클린 코드 |
| 정적 호스팅 vs 백엔드 | **정적** | 키 숨김, 사용량 통제 |
| Service Worker | **사용 안 함** | 오프라인, PWA 자동 업데이트 |
| 데이터 인라인 vs 외부 JSON | **둘 다** (인라인 우선, JSON 백업) | 깔끔한 분리 |
| AI 분류 방식 | **LLM 식별만 + 룰 매칭** | 프롬프트 1방 (환각 위험) |
