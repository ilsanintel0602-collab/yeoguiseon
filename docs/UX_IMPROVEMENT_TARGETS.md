# UX 개선 목표 (모바일 카메라 분리수거 PWA)

> 한국 분리수거 PWA의 UX 개선 우선순위. 환경부 분리배출.kr 표준 정확도·정직성을 본질 가치로 함.

## 핵심 본질 가치

**정확도·정직성·접근성** — 환경부 공식 표준에 100% 정합. 출처 명시. 모든 플랫폼 무료 사용.

| 영역 | 본질 가치 | 현재 상태 |
|---|---|---|
| **정확도** | 환경부 분리배출.kr 표준 12개 카테고리 100% 정합 | DB 97.3/100, pass@1 측정 시스템 구축 |
| **정직성** | 모든 안내에 출처 URL 표시 | items 777개 모두 sourceUrl 보유 (본질 룰 ⑰) |
| **접근성** | iOS·Android·PC 모두 PWA로 무료 | 설치 불필요, URL 공유 가능 |
| **운영비** | 0원 (API 무료 tier) | Cloudflare Worker + Gemini Flash 무료 한도 |

## 개선 우선순위

### 1순위: 카메라 분석 정확도

**현재:** Gemini 2.5 Flash + SYSTEM_PROMPT 한국 사물 특화 (v5.79 룰 7~12: 텀블러·카페일회용컵·다재질·소형가전·의약품 명시)

**목표:**
- pass@1 95% (item + category 모두 일치)
- 카테고리 정확도 98%+
- 다재질 items 안내 자동 (v5.79 multi_material UI 구현 완료)

**검증:** scripts/benchmark.py (mock 모드·실측·혼동 행렬·회귀 감지·임계값 차단)

### 2순위: 실시간 카메라 박스 (Object Detection)

**현재:** 사진 촬영 후 분석 (정적)

**목표:** 카메라 켜면 즉시 박스 표시 (객체 후보 시각화)
- on-device 모델 (MediaPipe Object Detection 등) 활용
- 박스 탭 → 해당 영역 자동 분석
- 정확도 영향 0 (정적 분석은 그대로 유지)

**고려:**
- COCO-SSD는 한국 사물 false-positive 다수 → v5.40에서 폐기
- MediaPipe Object Detection (Tasks API) — 더 유연한 한국 사물 학습 가능

### 3순위: 핀치 줌 (Pinch Zoom)

**현재:** 미지원

**목표:** 두 손가락으로 카메라 줌인/아웃
- 네이티브 카메라 API: `track.applyConstraints({ advanced: [{ zoom: 2.0 }] })`
- CSS transform scale fallback (구형 카메라용)
- 줌 인디케이터 UI (1.0x ~ 5.0x)

### 4순위: 다중 인식 + 탭 결과

**현재:** 한 사진에 한 물건 결과

**목표:** 한 사진에 여러 물건 자동 감지 + 박스 탭 시 해당 물건 결과 즉시 표시 (버튼 X)
- Gemini 응답 형식 array 변경
- 박스 overlay UI
- 탭 → 결과 카드 자동 이동

### 5순위: 카드형 결과 UI

**현재:** 단일 페이지 결과

**목표:** 카드 스와이프로 여러 결과·관련 안내 탐색

## 우리만의 강점 (지키기)

1. ✅ **전 플랫폼 PWA** — iOS·Android·PC·태블릿 모두 한 코드
2. ✅ **설치 불필요** — URL 공유로 즉시 사용
3. ✅ **전국 261 시군구 데이터** — 환경부·행안부 표준 100%
4. ✅ **지역별 비교 안내** — itemException 17 시군구 71 룰
5. ✅ **출처 100% 표시** — 모든 items sourceUrl (본질 룰 ⑰)
6. ✅ **본질 룰 18개 자동 차단** — 회귀 영구 방지
7. ✅ **다크 모드 + PWA 홈 화면 설치**
8. ✅ **빠른 배포·업데이트** — push 즉시 적용 (네이티브 앱스토어 X)

## 정량 측정 시스템 (v5.76 구축)

- **scripts/benchmark.py** — pass@1·카테고리별·혼동 행렬·회귀 감지·임계값 차단
- **scripts/collect_samples.py** — Wikimedia Commons 자동 수집 (CC BY-SA)
- **benchmark/labels.csv** — 30장 권장 라벨 자동 채움
- **DB 벤치마크 97.3/100** — items·alias·sourceUrl·multi_material 정합성

## 참고 자료

- 환경부 분리배출.kr 표준: https://www.xn--oy2b29bd3a601b.kr/
- 한국 AI Hub 생활폐기물 데이터: https://aihub.or.kr/
- Roboflow Universe (TACO 등 공개 데이터셋): https://universe.roboflow.com/
- Tesseract.js (한국어 OCR): https://github.com/naptha/tesseract.js
- MediaPipe Tasks API: https://developers.google.com/mediapipe

## 본질 원칙

- 비교·경쟁 표현 사용 금지 ([[feedback-no-competitor-mentions]])
- 자기 가치 (환경부 표준·정직성)로만 표현
- 정량 측정 기준은 "pass@1 95% 목표 (업계 양호 수준)" 같은 중립 표현

---
작성: 2026-05-28 (v5.79 본질 회복 사이클)
