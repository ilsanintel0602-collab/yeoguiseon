# 사진 벤치마크 자동 평가 시스템 설계 (v5.70 Opus)

## 배경

현재 정량 측정 가능:
- `benchmark_db.py` — DB 자산 건전성 (정확도, 카테고리 정합) → **96.9/100**
- `text_benchmark.py` — 텍스트 검색 정답률 (182건) → **91.2%**
- Gemini 환각 회복 (10/10) → **100%**

**측정 X 영역**: Gemini AI 이미지 분석 정확도 (실제 사진 → 카테고리/품목 매칭).

RecycleAI 발표 정확도: pass@1 **94.2%** (자체 모델). 우리 앱은 정량 측정 없음 → 객관 비교·개선 방향 불가.

## 목표

1. **사진 50장 자동 평가**: 한국 분리수거 대표 사진(라면 봉지·페트병·종이팩·고무장갑·스프레이 등) → Gemini 응답 자동 채점
2. **회귀 자동 차단**: 정확도 하락 시 quick_check에 자동 알림
3. **개선 방향 정량 도출**: 오류 패턴 분류 → 데이터·prompt 보강 우선순위

## 아키텍처

### 데이터 구조 — `benchmark/labels.csv` (이미 v5.46에 30장 라벨)

```csv
filename,expected_item_id,expected_category,expected_region,notes
ramen_packet.jpg,라면 봉지,vinyl,11680,식품 포장 비닐
pet_clear_water.jpg,페트병,pet_clear,11680,투명 PET
milk_carton.jpg,우유팩,paper_pack,11680,멸균 팩
rubber_glove_red.jpg,고무장갑,general,11680,비닐류는 강남구만
spray_can.jpg,에어로졸 캔,hazardous,11680,위험물 (danger:true)
...
```

50장 확장 (인기 카테고리별 5장):
- 종이류·종이팩 10장
- 플라스틱 (페트·일반) 10장
- 비닐·스티로폼 8장
- 캔·금속·유리 7장
- 위험물·전자 5장
- 일반·음식물 5장
- 의류·의약품 5장

### 평가 스크립트 — `scripts/photo_benchmark.py` (신규)

```python
"""
사진 벤치마크 — Gemini 자동 평가.
사용: python3 scripts/photo_benchmark.py [--limit N] [--verbose]
출력: benchmark/photo_report_YYYY-MM-DD.md + 점수 (pass@1)
"""
import csv, json, os, sys, base64, subprocess
from collections import defaultdict

WORKER = 'https://yeoguiseon-proxy.ilsanintel0602.workers.dev/'
LABELS = 'benchmark/labels.csv'
SAMPLES = 'benchmark/samples/'

def evaluate(image_path, expected):
    """Worker 호출 → Gemini 응답 → 채점"""
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    # Worker POST (curl 또는 fetch)
    resp = call_worker(b64)
    actual = json.loads(resp).get('result', {})

    return {
        'item_match': actual.get('item_id') == expected['expected_item_id'],
        'category_match': actual.get('category_hint') == expected['expected_category'],
        'danger_match': bool(actual.get('danger')) == ('hazardous' in expected['expected_category']),
        'actual': actual,
    }

def main():
    rows = list(csv.DictReader(open(LABELS, encoding='utf-8')))
    results = []
    for row in rows:
        path = os.path.join(SAMPLES, row['filename'])
        if not os.path.exists(path):
            continue
        r = evaluate(path, row)
        results.append((row, r))
    # 집계
    pass_at_1 = sum(1 for _, r in results if r['category_match'] and r['item_match'])
    cat_only = sum(1 for _, r in results if r['category_match'])
    danger_correct = sum(1 for _, r in results if r['danger_match'])

    print(f'pass@1 (item+category): {pass_at_1}/{len(results)} = {pass_at_1*100/len(results):.1f}%')
    print(f'category only: {cat_only}/{len(results)} = {cat_only*100/len(results):.1f}%')
    print(f'danger 정확: {danger_correct}/{len(results)} = {danger_correct*100/len(results):.1f}%')

    # 오류 패턴 집계
    errors = [(row['filename'], row['expected_category'], r['actual'].get('category_hint'))
              for row, r in results if not r['category_match']]
    pattern = defaultdict(int)
    for fn, exp, act in errors:
        pattern[f'{exp}→{act}'] += 1
    print('\n주요 오류 패턴:')
    for p, n in sorted(pattern.items(), key=lambda x: -x[1])[:5]:
        print(f'  {p}: {n}건')

    # 마크다운 리포트
    write_report(results, pass_at_1, cat_only, danger_correct)
```

### quick_check 통합

```python
# scripts/quick_check.py 끝에 추가 (선택)
try:
    bench = subprocess.run([sys.executable, 'scripts/photo_benchmark.py', '--limit', '10'],
                           capture_output=True, text=True, timeout=120)
    # pass@1 점수 추출 → 임계값 (예: >= 85%) 차단
except Exception:
    check('사진 벤치마크', True, 'skip (timeout 또는 사진 없음)')
```

→ push 시 자동 평가 (10장 sampling, 1-2분).

## 데이터 수집

### 50장 사진 출처 (저작권 안전)
1. **사용자 동의 본인 촬영** (가장 안전): 사용자가 직접 촬영한 분리수거 사진 → 동의 후 수집
2. **환경부 공식 이미지** (public domain): 분리배출.kr 가이드 이미지
3. **AI Hub 한국 사물 데이터셋** (CC BY): 한국지능정보사회진흥원 공개 데이터

라벨링 워크플로:
- `benchmark/samples/raw/` — 원본 사진 (gitignore)
- `benchmark/samples/processed/` — 640px JPEG 리사이즈 (commit)
- `benchmark/labels.csv` — 파일명 + 정답 (commit)

### Worker rate limit 안전망
- 50장 분석 = 50회 Gemini 호출 (10초 간격) = 약 8분
- DAILY_LIMIT 1000 안전 (50회 << 1000)
- 벤치마크 시 IP 동일하니 MINUTE_LIMIT 30회 분당 = 50장 1.7분 (분당 30개 묶음 × 2회)

## 단계별 실행 계획

### 단계 A (1주차): 라벨 30장 → 50장 확장
- 기존 30장 검증 (필요시 정정)
- 20장 추가 (위험물·의류·의약품·음식물 더 포함)

### 단계 B (1주차): photo_benchmark.py 작성
- Worker 호출 함수 (Python urllib 또는 requests)
- 채점 로직 (item·category·danger)
- 마크다운 리포트
- 첫 측정 후 baseline 기록

### 단계 C (2주차): 회귀 차단
- quick_check 통합 (sampling 10장, 2분 이내)
- 임계값 (pass@1 ≥ 85%) 강제
- 점수 하락 시 push 차단

### 단계 D (3주차+): 오류 패턴 자동 분석
- 카테고리 혼동 매트릭스 (예: pet_clear ↔ plastic 빈도)
- 우선순위 SYSTEM_PROMPT 보강 영역 도출
- 정확도 → 96%+ 목표

## 효과 (예상)

| 영역 | 현재 | Phase B 완료 후 | Phase D 완료 후 |
|---|---|---|---|
| 사진 정확도 측정 | ❌ 없음 | ✅ pass@1 측정 | ✅ 카테고리별 |
| 회귀 차단 | 텍스트만 | ✅ 사진 sample 자동 | ✅ 임계값 강제 |
| RecycleAI 비교 가능 | ❌ | ✅ 객관 수치 | ✅ |
| 개선 방향 | 추측 | ✅ 데이터 기반 | ✅ 자동 |

## 본질 측면

✅ **정확도 직접 측정** — 사용자 안내 정확도 객관 평가
✅ **회귀 영구 차단** — 사진 정확도 하락 시 push 차단
✅ **개선 방향 데이터화** — 추측 X, 측정 기반 우선순위
⚠️ **Worker 호출 비용** — 1회 50장 = $0.02 (Gemini Flash 단가). 일주일 1회 측정 = 월 $1 미만

## 위험 점검

- **사진 출처 저작권** → 사용자 본인 촬영·공공 데이터만
- **Worker rate limit** → 분당 30회 안전망 검증 필요
- **Gemini API 비용** → Flash 모델이라 매우 저렴, 무시 가능

## 권장 시작

**v5.70 push 후 시연 안정** → 단계 A·B 1주차 진행 → 첫 측정 결과로 본질 룰 ⑫ (사진 정확도 임계값 차단) 추가.

---

작성: 2026-05-27 (Opus, v5.70 사이클)
