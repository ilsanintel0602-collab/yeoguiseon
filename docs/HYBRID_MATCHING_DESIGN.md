# 하이브리드 매칭 설계 — v6.0 로드맵

**목표**: 일상 폐기물 85% 케이스 ms 단위 응답 + Gemini 비용 -85% (한국 사물 특화 모델 94.2% pass@1 모범)

---

## 현재 상태 (v5.39)

```
사진 → 모든 케이스 Gemini Flash 2.5 호출 (0.5~2초)
       └─ COCO-SSD 부분 라이브 박스 표시만 (분류 의사결정 X)

검색 → searchByText (Gemini X, ms 단위) ✅
```

- COCO-SSD 매핑 10개 (bottle·book·banana·cell phone·laptop·chair·couch·dining table·bed·backpack)
- 나머지 = Gemini 호출
- 비용·속도: 모든 사진 Gemini = 730ms 평균 + 비용

---

## v6.0 목표 아키텍처

```
사진 (촬영) 
  │
  ├─ 1차: COCO-SSD 객체 인식 (50ms, 브라우저 로컬)
  │   ├─ 명확 매핑 (확장 50+ 케이스) → 즉시 DB lookup → 결과 카드
  │   └─ 매핑 없음 또는 모호 → 2차로
  │
  ├─ 2차: Gemini Flash 호출 (필요한 케이스만, 15%)
  │   └─ JSON {item_id, category_hint} → matchRule
  │
  └─ 후처리 (공통):
      ├─ matchRule alias (v5.39)
      ├─ ambiguous_map 검사 → 모호 분기 UI
      └─ cityGuide 결합 → 결과 카드 (출처 라벨)
```

---

## 3단계 점진 도입

### Stage 1 (v5.40, 단기): COCO 매핑 확장
- COCO-SSD 80 클래스 중 매핑 가능한 것 다 추가 (10 → 50+)
- 추가 후보: cup/bowl/vase/scissors (사용자 영역 지정 시), tv/microwave/oven (대형가전 안내), umbrella (대형폐기물)
- 효과: 30~40% 케이스를 Gemini 없이 처리
- **PWA 환경 그대로 (TF.js 이미 가동)**

### Stage 2 (v5.50, 중기): YOLOv8 웹 모델 도입
- YOLOv8n (3MB) ONNX 또는 TFLite 웹 변환
- 200+ 클래스 (COCO 80 + 한국 분리수거 자체 학습)
- 인식 신뢰도 측정 → 95% 이상이면 Gemini X
- 효과: 70% 케이스를 Gemini 없이 처리

### Stage 3 (v6.0, 장기): 자체 한국 분리수거 모델
- 분리배출.kr 730 품목 + 사용자 피드백 데이터로 자체 학습
- 한국 사물·각도·조명 특화
- Roboflow·Edge Impulse 같은 플랫폼 활용
- 한국 사물 특화 모델 94.2% 같은 정량 평가
- 효과: 85% 케이스를 Gemini 없이 처리 — 한국 사물 특화 모델 동등 정확도·속도

---

## 한국 사물 특화 모델 차이점

| 영역 | 한국 사물 특화 모델 | 여기선 v6.0 (목표) |
|---|---|---|
| 플랫폼 | Native Android (Compose) | **PWA (크로스플랫폼)** |
| 객체 인식 | Google ML Kit (Native) | **YOLOv8 + COCO-SSD (웹)** |
| 매칭 전략 | 자체 730 DB 1차 + Gemini 2차 | **NATIONAL 773 + region 239 + Gemini 2차** |
| 위치 매핑 | 행안부 API 실시간 | regions_meta 정적 (속도·안정 ↑) |
| pass@1 | 94.2% (벤치마크) | 87.9 → 95%+ (목표) |
| 응답 latency | 로컬 45ms / Gemini 780ms | 동일 목표 |

---

## 비용·속도 효과 추정

### 현재 (v5.39)
- 모든 사진 Gemini 호출 = $X (월)
- 응답: 0.5~2초

### v6.0 (Stage 3)
- 85% COCO/YOLO 매칭 (Gemini X) = **$0**
- 15% Gemini fallback = **$0.15X**
- 응답: 85% ms 단위 / 15% 1~2초
- **비용 -85%, 속도 10배 ↑ (대다수 케이스)**

---

## 단기 즉시 가치 (Stage 1)

COCO 매핑 확장만으로도:
- bottle·wine glass·book·cell phone·laptop·book → 즉시 매핑 (현재 가동)
- + 추가: chair·couch·dining table·bed → furniture 안내
- + 추가: tv·microwave·oven·refrigerator → electronics + 1599-0903

→ 일상 30~40% 케이스 Gemini 호출 없이 즉시 응답.

---

## 사용자 영역 지정 강화 (한국 사물 특화 모델 모범)

한국 사물 특화 모델: 녹색 박스(AI 자동) + 주황 박스(사용자 드래그)

여기선 현재: "영역을 손가락으로 표시" 안내 + 영역 캡처

개선 방향:
- 사용자 드래그 박스 = 주황색 표시 (한국 사물 특화 모델 차별화 UX)
- COCO-SSD가 객체 자동 포착 = 녹색 박스
- 두 색 구분으로 사용자 조작감 명확

---

## 진행 조건

이 설계는 **v5.39 시연 검증 + 자산 안정화 후** Stage 1부터 점진 도입. 한꺼번에 안 함.

| 우선순위 | 트리거 |
|---|---|
| Stage 1 (COCO 확장) | v5.39 시연 안정 후 즉시 |
| Stage 2 (YOLOv8) | 사용자 피드백 누적 + 학습 데이터 확보 후 |
| Stage 3 (자체 모델) | v6.0 별도 프로젝트 |
