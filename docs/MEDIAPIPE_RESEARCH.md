# MediaPipe Object Detection 사전 조사 — 카메라 정확도 점프 옵션

## 사용자 v5.44 시연 호소 (재인용)

> "그냥 카메라를 누르면 인식이 늦거나 인식실패해요... 손가락영역은 그나마 오류가 적네요."

= 현재 COCO-SSD (TensorFlow.js) 자동 인식의 정확도·속도 한계. v5.42에서 박스 표시 폐기, v5.45에서 손가락 영역 드래그(customBox) crop으로 우회.

## RecycleAI 대비 비교

| 항목 | RecycleAI | 여기선 v5.46 |
|---|---|---|
| 카메라 모델 | Google ML Kit Object Detection | COCO-SSD (TensorFlow.js 80 클래스) |
| 모바일 성능 | Native (Android) | WebView TF.js (느림) |
| 한국 사물 정확도 | ML Kit 일반 객체 (영문 라벨, 한국 제품 fine-tune X) | 동일 한계 (살충제→bottle 등 false-positive) |
| 차별점 | 빠름·매끄러움 | 정직 안내·전국 100%·환경부 표준 |

## MediaPipe 옵션 3가지

### A. MediaPipe Object Detector (웹)
- **출처**: Google 공식 (`@mediapipe/tasks-vision`)
- **모델**: EfficientDet-Lite0 (80 클래스 COCO 사전학습)
- **장점**: WASM 가속, COCO-SSD보다 2~3배 빠름, 동일 80 클래스
- **한계**: 한국 사물 fine-tune X → 같은 false-positive 문제
- **결론**: 속도 ↑, 정확도 변화 ≈ 0

### B. MediaPipe Image Classifier (한국 사물 fine-tune 가능)
- **모델**: EfficientNet-Lite (이미지 분류, custom training 가능)
- **장점**: Roboflow·TFLite Model Maker로 한국 분리수거 클래스 재학습 가능 (예: 햇반·종이팩·페트병·우유팩 50~100 클래스)
- **단점**: 데이터셋 구축 필수 (이미지 ≥500/class)
- **결론**: 정확도 ↑ 가능. 단 데이터 수집 큰 작업

### C. Gemini 2.5 Flash 직접 (현재 + 보강)
- **현재**: 카메라 → Gemini Vision API → JSON 반환 (Worker 프록시)
- **장점**: 한국어 라벨·문맥 이해 100% (실제 사용자 검증)
- **단점**: API 호출 비용·지연 (사용자 호소 "느림")
- **개선 가능**:
  - **v5.45 customBox crop** 이미 적용 (영역만 전송 → 빠르고 정확)
  - **이미지 압축 강화** (640px → 480px → API 30% ↓)
  - **사용자 사진 캐시** (같은 사진 반복 시 즉시 응답)
  - **Worker edge cache** (이미지 hash 기준 5분 캐시)

## 권장 — 단계별

### 1단계: Gemini 최적화 (현재 강화)
- customBox crop ✓ (v5.45 완료)
- 이미지 압축 적용 (480px) — 30분 작업
- Worker edge cache (이미지 hash) — 1시간 작업
- **효과**: 속도 30~50% ↑, 정확도 그대로

### 2단계: MediaPipe Object Detector 도입 (선택)
- Pre-filter: 카메라에서 즉시 사물 영역 박스 감지 → 사용자가 어느 박스 탭 → Gemini로 정확 분석
- 사용자 본질 X (현재 customBox 드래그로 해결)
- **효과**: 속도 ↑, 정확도 변화 ≈ 0

### 3단계: 자체 학습 모델 (장기, 큰 작업)
- Roboflow 한국 분리수거 데이터셋 구축 (사용자 사진 수집)
- TFLite Model Maker로 EfficientNet-Lite fine-tune
- 한국 사물 정확 분류
- **효과**: 정확도 큰 ↑, RecycleAI 능가 가능

## 비교 결론

| 작업 | 비용 | 속도 효과 | 정확도 효과 | 본질 가치 |
|---|---|---|---|---|
| **1단계 (Gemini 최적화)** | 1.5시간 | +30~50% | 0 | 즉시 |
| 2단계 (MediaPipe) | 1일 | +20% | 0 | 작음 (customBox로 이미 해결) |
| 3단계 (자체 학습) | 1~2주 | 0 | 큰 ↑ | RecycleAI 능가 (장기 목표) |

## 권장 시점

- **시연 결과 받기 전**: 1단계만 코드 준비 (이미지 압축 480px, Worker 캐시 설계 문서)
- **시연 결과 ↓ 속도 호소 지속**: 1단계 즉시 적용 → push
- **3단계는 별도 큰 프로젝트** — 사용자 사진 수집 필수, 시연 안정 후 검토

## 결론

**MediaPipe는 직접 가치 작음** (정확도 변화 X). 같은 자원으로 Gemini 최적화가 더 효과적. v5.45의 customBox crop이 이미 핵심 우회. 3단계 자체 학습이 진짜 RecycleAI 능가의 길.
