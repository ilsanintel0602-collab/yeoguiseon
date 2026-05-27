# AI 응답 검증 시스템 설계 (v5.78 Opus)

## 배경

현재 Worker (v1.9.15)는 Gemini 응답을 그대로 클라이언트에 전달. 클라이언트(app.html)에서 정합성 검증.

**문제:**
- 클라이언트 검증은 사후 — 잘못된 응답이 이미 사용자에게 노출될 수 있음
- 환각·모순 응답이 캐시에 저장되면 24시간 재사용 (Worker SHA-256 캐시)
- 회귀 추적 어려움 (어떤 응답이 통과/차단됐는지 로그 없음)

**v5.51~v5.77 시연 발견 패턴:**
- ① category vs item 불일치 (예: item="페트병" + category="paper")
- ② danger 누락 (스프레이·부탄가스인데 danger:false)
- ③ confidence 임계값 미만 (낮은 신뢰도 응답 그대로 노출)
- ④ enum 외 값 (예: category="reusable" 폐기됐는데 Gemini가 출력)
- ⑤ multi_material items 단순 추정 (텀블러 케이스)

## 목표

1. **Worker 단계에서 응답 검증** — 클라이언트 도달 전 차단·정정
2. **회귀 자동 차단** — 잘못된 응답 패턴 매 호출 자동 감지
3. **정량 로그** — KV에 검증 통계 누적 (월간 회귀 추적)

## 아키텍처

### 검증 레이어 (Worker 내부)

```
[Gemini 응답]
    ↓
[validateResponse()] ← 새 추가
    ↓
  ┌─OK──→ [캐시 저장 + 클라이언트 반환]
  │
  └─FAIL→ [정정 시도] ─OK──→ [캐시 저장 + 반환 (정정 표시)]
              │
              └─FAIL→ [unknown 반환 + KV 로그]
```

### validateResponse 룰 (12개)

#### A. 구조 룰 (3)
1. **필수 필드 존재**: item_id, category_hint, danger 모두 있어야
2. **타입 정합**: item_id=string, category_hint=string, danger=bool, confidence=number
3. **JSON 형식 정확**: 추가 텍스트·마크다운 codefence 차단

#### B. enum 룰 (3)
4. **category enum 일치** (v5.76 19개 + unknown):
   ```js
   const VALID_CATS = ['paper', 'paper_pack', 'pet_clear', 'plastic', 'vinyl',
     'styrofoam', 'glass', 'can', 'clothes', 'battery', 'lamp', 'electronics',
     'food', 'general', 'general_noncombustible', 'general_or_bulky',
     'furniture', 'hazardous', 'medicine', 'unknown'];
   ```
   위반 시 → unknown으로 정정
5. **item_id 한국어 강제**: ASCII만 있으면 차단 (영문 ID 노출 v5.62 회귀 영구 차단)
6. **폐기 카테고리 차단**: reusable, bulky 같은 v5.46 폐기 카테고리

#### C. 논리 룰 (4)
7. **category vs item 일관성** (best-effort): item에 "페트병"이면 category=pet_clear 기대
8. **danger 강제 매핑**: item에 ['가스', '부탄', '스프레이', '에어로졸', '주사기', '배터리 부풀'] 키워드 있으면 danger=true 강제
9. **confidence 임계값**: < 0.4면 unknown 정정 (사용자에게 추측 노출 X)
10. **다재질 items multi_material 안내**: 텀블러·카페일회용컵 → response에 `multi_material:true` 자동 추가

#### D. 정직성 룰 (2)
11. **unknown 강제 케이스**: enum 외 값 + 임계값 미만 + 환각 키워드 → unknown
12. **위험물 fallback**: danger:true인데 category 모호하면 hazardous로 정정

## 구현

### Worker 추가 코드 (~120줄)

```js
// scripts/cloudflare_worker.js 추가
function validateResponse(parsed) {
  const issues = [];
  const result = { ...parsed };

  // A1-A3 구조
  if (!result.item_id || !result.category_hint) {
    issues.push('필수 필드 누락');
    return { ok: false, result: { item_id: 'unknown', category_hint: 'unknown', danger: false }, issues };
  }

  // B4 enum
  const VALID_CATS = ['paper','paper_pack','pet_clear','plastic','vinyl','styrofoam',
    'glass','can','clothes','battery','lamp','electronics','food','general',
    'general_noncombustible','general_or_bulky','furniture','hazardous','medicine','unknown'];
  if (!VALID_CATS.includes(result.category_hint)) {
    issues.push(`enum 외 category: ${result.category_hint} → unknown`);
    result.category_hint = 'unknown';
  }

  // B5 영문 item_id 차단 (v5.62 회귀)
  if (result.item_id && /^[a-zA-Z_]+$/.test(result.item_id)) {
    issues.push(`영문 item_id 차단: ${result.item_id} → unknown`);
    result.item_id = 'unknown';
  }

  // C8 danger 강제 매핑
  const DANGER_KW = ['가스', '부탄', '스프레이', '에어로졸', '주사기', '부풀'];
  if (DANGER_KW.some(kw => result.item_id?.includes(kw))) {
    if (!result.danger) {
      issues.push(`danger 강제 true: ${result.item_id}`);
      result.danger = true;
    }
    if (!['hazardous', 'general_noncombustible'].includes(result.category_hint)) {
      issues.push(`위험물인데 cat=${result.category_hint} → hazardous`);
      result.category_hint = 'hazardous';
    }
  }

  // C9 confidence 임계값
  if (typeof result.confidence === 'number' && result.confidence < 0.4) {
    issues.push(`낮은 confidence ${result.confidence} → unknown`);
    result.item_id = 'unknown';
    result.category_hint = 'unknown';
  }

  // C10 다재질 자동 표시
  const MULTI_KW = ['텀블러', '카페 일회용컵', '필통', '연필꽂이', '사다리', '소화기'];
  if (MULTI_KW.some(kw => result.item_id?.includes(kw))) {
    result.multi_material = true;
  }

  return { ok: issues.length === 0, result, issues };
}

// 기존 응답 처리에 통합
const validation = validateResponse(parsed);
if (validation.issues.length > 0) {
  console.log('[validate]', validation.issues);
  // KV에 로그 (월간 통계용)
  await env.LOGS?.put(`validate:${Date.now()}`, JSON.stringify({
    original: parsed, corrected: validation.result, issues: validation.issues
  }), { expirationTtl: 30 * 86400 });
}
return validation.result;
```

### KV 로그 분석 스크립트

```bash
# scripts/analyze_validation_logs.py (신규)
# Worker KV에서 validation 로그 가져와서 월간 회귀 패턴 분석
```

## 단계별 실행

### 단계 A (1주차): 핵심 룰 6개만
- A1-A3 구조 + B4-B5 enum + B6 폐기 카테고리
- 즉시 효과: 90% 이상 회귀 차단

### 단계 B (2주차): 논리 룰 추가
- C7-C10 (논리·danger·confidence·multi_material)
- 정확도 +3~5% 예상

### 단계 C (3주차): 정직성 룰 + KV 로그
- D11-D12 + KV 로그 분석 자동화
- 월간 회귀 보고서

## 효과 (예상)

| 회귀 케이스 | 현재 | 단계 A | 단계 C |
|---|---|---|---|
| enum 외 category | 클라 차단 | Worker 차단 | + 자동 정정 |
| 영문 item_id | 클라 fallback | Worker 차단 | + 정정 |
| 위험물 danger 누락 | 노출 | 노출 | 자동 true |
| 다재질 안내 | 수동 | 수동 | 자동 표시 |
| 회귀 추적 | git log | git log | KV 통계 |

## 위험 점검

- **Worker 호출 시간 +5ms** (validation 12 룰 = 무시 가능)
- **KV 쓰기 비용** (10만 호출/월 = $0.50)
- **거짓 차단 위험** (validation 룰이 너무 strict하면) → 단계 A 핵심 6개만 시작 권장

## 권장 시작

v5.77 push 완료 + 시연 안정 확인 → 단계 A 6개 룰만 Worker 통합 (Worker v1.10.0 deploy).

---
작성: 2026-05-28 (Opus 4.7, v5.78 사이클)
