---
name: upgrade-model
description: YOLO 모델을 COCO-SSD에서 더 정확한 TACO(쓰레기 전용) 또는 커스텀 학습 모델로 업그레이드. 분리수거 정확도 85% → 95% 목표.
---

# YOLO 모델 업그레이드 스킬

## 언제 사용?
- COCO-SSD의 한계 (한국 분리수거 특화 클래스 부족) 극복하고 싶을 때
- 사용자 신고가 누적되어 모델 개선이 필요할 때
- vinyl/styrofoam/can 카테고리 정확도가 낮을 때

## 처리 단계

### 1. 후보 모델 평가
- TACO (Trash Annotations in Context) - 60개 쓰레기 클래스
- TrashNet - 6개 카테고리 (간단)
- 커스텀 YOLOv8 학습 (Roboflow에서 한국 데이터셋)

### 2. TensorFlow.js 호환 변환
- Python으로 학습된 모델을 tfjs-converter로 변환
- 또는 ONNX → TF.js 경로

### 3. app.html 통합
- CDN URL 교체
- 새 클래스 매핑 추가
- A/B 테스트 (기존 COCO-SSD vs 신모델)

### 4. 검증
- 박정호 시나리오 18개 물건 정확도 측정
- 응답 속도 비교
- 모델 크기 변화 (5MB → ?MB)
