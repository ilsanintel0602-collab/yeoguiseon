# 🚀 여기선 v4.0 로드맵

> **미션:** API 없이 RecycleAi 능가 — 정확도 최우선
> **모바일 전용 사용자** 기준 설계

## 🎯 v4의 4가지 핵심 무기

```
정확도 = (Custom YOLO 학습) × (OCR 보조) × (브랜드 DB) × (사용자 학습)
```

## Phase A: 즉시 효과 (3~5일) ⭐ 먼저

### A1. OCR 통합 (1일)
**무엇:** Tesseract.js 한국어 라벨 읽기

```html
<script src="https://cdn.jsdelivr.net/npm/tesseract.js@5"></script>
```

**효과:**
- "환원수" → 비닐
- "스킨" / "토너" → 플라스틱
- "우유" → 종이팩
- "맥주" → 유리

**작업:**
1. Tesseract.js 추가 (kor.traineddata)
2. YOLO 박스 안 영역만 OCR
3. 키워드 → 카테고리 매핑 JSON
4. 결과: YOLO + OCR 결합

### A2. 한국 제품 브랜드 DB (1~2일)
**무엇:** 주요 한국 생활용품 100개 사전 등록

```json
// data/brand_db.json
{
  "라네즈 슬리핑마스크": { "category": "plastic", "confidence": "high" },
  "비비고 즉석밥": { "category": "plastic", "note": "씻으면 재활용" },
  "농심 신라면": { "category": "vinyl", "note": "포장지" },
  ...100개
}
```

**효과:** OCR로 브랜드명 읽으면 → 즉시 정답 95%

### A3. 후보 선택 UI (1~2일)
**무엇:** "혹시 이것인가요?" Top 5 표시 (RecycleAi 패턴)

```html
<div class="candidates">
  <button>플라스틱</button>
  <button>화장수 통</button>
  <button>샴푸 통</button>
  <button>세제 통</button>
  <button>기타 (수동 선택)</button>
</div>
```

**효과:** 신뢰도 < 80%일 때 자동 표시. 사용자가 선택 → localStorage에 학습.

**Phase A 종료 시 예상 정확도:** 60% → **85%**

---

## Phase B: 본질적 개선 (2주)

### B1. Custom YOLO 학습
**무엇:** TACO + AI Hub 데이터로 한국 분리수거 전용 모델

**데이터셋:**
1. TACO (Trash Annotations in Context) - 60 클래스, 60K 이미지
2. AI Hub '생활폐기물 이미지 데이터셋' - 60만 장 (가입 필요)
3. Roboflow Universe 한국 데이터셋

**학습 환경:**
- Google Colab (T4 GPU 무료)
- YOLOv8n (3.2MB, 가벼움)
- 4시간 학습

**변환:**
- PyTorch → TensorFlow → TF.js
- 약 5~10MB 모델

**예상 정확도:** 85% → **92%**

### B2. 실시간 카메라 박스
**무엇:** 카메라 켜면 즉시 객체 박스 (RecycleAi 패턴)

```javascript
async function realTimeDetect() {
  while (cameraActive) {
    const detections = await model.detect(video);
    drawBoxes(detections);
    await sleep(500);  // 2fps (배터리 절약)
  }
}
```

**효과:** UX 대폭 개선. 사용자가 박스 탭 → 그 객체만 정밀 분석.

---

## Phase C: 자가 보정 (1주)

### C1. 사용자 학습 (Local FL)
**무엇:** 사용자 정정한 데이터 누적 → 다음 추론에 반영

```javascript
LS.set('user_corrections', [
  { image_hash: 'abc123', ai_said: 'general', user_said: 'plastic' },
  ...
]);
```

**다음 추론:**
- 비슷한 이미지 해시 → 사용자 정답 우선

**효과:** 100명 사용자 = 1000+ 학습 데이터, 자가 보정.

### C2. 다각도 가중 평균
**무엇:** 한 물건 3장 (앞/뒤/라벨) → 평균 신뢰도

```javascript
const results = await Promise.all([
  analyze(photo1), analyze(photo2), analyze(photo3)
]);
const final = weightedAverage(results);
```

**효과:** 한 사진 신뢰도 70% × 3장 = 평균 90% 가능.

---

## 📋 v4 자동 작업 To-Do List

### Phase A (즉시, 3일)
- [ ] A1. Tesseract.js 통합 + 한국어 모델 다운로드
- [ ] A2. 한국 제품 100개 brand_db.json 작성
- [ ] A3. "혹시 이것?" 후보 UI 5개 옵션
- [ ] A.eval. 정확도 측정 (목표 85+)

### Phase B (2주)
- [ ] B0. AI Hub 데이터셋 신청 (1~3일 대기)
- [ ] B1. Google Colab 환경 세팅 + YOLOv8 학습
- [ ] B2. PyTorch → TF.js 변환
- [ ] B3. app.html에 새 모델 통합
- [ ] B4. 실시간 카메라 박스 구현
- [ ] B.eval. 정확도 측정 (목표 92+)

### Phase C (1주)
- [ ] C1. 사용자 학습 시스템 (localStorage)
- [ ] C2. 이미지 해시 매칭 (perceptual hash)
- [ ] C3. 다각도 가중 평균 UI
- [ ] C.eval. 사용자 50명 시뮬레이션

---

## 🎯 평가 기준 (각 Phase 90+ 보장)

### Phase A 평가 (100점)
| 항목 | 점수 |
|---|---|
| OCR 동작 (한국어 인식) | 25 |
| 브랜드 DB 100개 이상 | 20 |
| 후보 UI 5개 옵션 | 20 |
| 정확도 향상 (60→85%) | 25 |
| 코드 안정성 | 10 |

### Phase B 평가 (100점)
| 항목 | 점수 |
|---|---|
| Custom 모델 통합 | 30 |
| TF.js 변환 성공 | 20 |
| 실시간 박스 동작 | 20 |
| 정확도 향상 (85→92%) | 25 |
| 모델 크기 < 15MB | 5 |

### Phase C 평가 (100점)
| 항목 | 점수 |
|---|---|
| 사용자 학습 동작 | 30 |
| 자가 보정 검증 | 30 |
| 다각도 평균 동작 | 20 |
| UX 자연스러움 | 20 |

---

## ⚠️ 위험 & 대응

| 위험 | 대응 |
|---|---|
| AI Hub 가입·승인 늦음 | TACO만으로 시작, 추가는 나중 |
| Colab GPU 할당 거부 | 로컬 GPU 또는 Kaggle Notebook 활용 |
| Custom 모델 정확도 ↓ | OCR + 브랜드 DB로 보강 |
| Tesseract.js 한국어 부정확 | Top-3 후보로 폴백 |
| 모델 크기 > 15MB | Quantization (FP16, INT8) |
| 모바일 메모리 부족 | 모델 분할 로딩 |

---

## 📱 모바일 전용 최적화

사용자 명시: **모바일 전용 사용**

### 디자인 원칙
- ✅ 세로 화면 우선
- ✅ 큰 터치 영역 (56px+)
- ✅ 큰 글씨 (16px+)
- ✅ 한 손 사용 가능
- ✅ 데이터 절약 (와이파이 안내)
- ❌ PC UI 신경 안 씀

### 성능 최적화
- 모델 lazy load
- 이미지 800px 리사이즈
- WebGL → WASM 폴백
- 캐싱 적극 활용

---

## 💰 비용 추정

| 항목 | 비용 |
|---|---|
| 데이터셋 다운로드 | 무료 (TACO, AI Hub) |
| Colab GPU | 무료 (제한적) |
| Tesseract.js | 무료 |
| 호스팅 (Vercel) | 무료 |
| 운영비 | **0원** |
| 도메인 (선택) | 연 15,000원 |

**v4도 운영비 0원 모델 유지** ✅

---

## 🏁 v4 종료 시 기대 결과

- 정확도: COCO-SSD 40% → **92%** (RecycleAi 수준)
- 속도: 1~2초 (네이티브와 거의 동일)
- 모델 크기: ~10MB (5MB precache + 5MB on-demand)
- 사용자 만족도: ⭐⭐⭐⭐⭐
- RecycleAi 대비: **동등 + 다중 플랫폼 우위**

## 🔜 v5 이후 (미래)

- 동·단지 단위 세부 룰 (level3)
- 배출일 푸시 알림 (Android)
- 다국어 (외국인 이주자)
- React Native 진짜 모바일 앱
- B2B2C (아파트 관리사무소)

---

**다음 세션 추천 첫 작업: Phase A1 (OCR 통합) — 1일 작업, 즉시 효과**
