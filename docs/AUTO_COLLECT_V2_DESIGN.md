# 시연 사진 자동 누적 시스템 v2 설계 (v5.79 Opus)

## 배경

현재 사진 벤치마크 데이터 수집:
- **collect_samples.py** (v5.76): Wikimedia Commons 자동 다운로드 (라이센스 문제 X, 라벨 정확도 한계)
- **사용자 수동 촬영**: 정확도 최고, 시간·물리 비효율 (사용자 본인 지적)

**문제:**
- 50장 수집해도 한국 사물 특화 부족 (Wikimedia 한계)
- 정작 사용자가 평소 시연하는 사진 = 가장 본질적인 데이터인데 활용 X
- 한 번 분석 후 사라짐 (Worker 캐시는 24h)

## 목표

1. **사용자 평소 시연 자체가 데이터 수집** — 추가 행동 0
2. **30장 누적 시 자동 export** — 사용자가 검토만
3. **회귀 자동 차단** — push 전 누적 사진 + 정답 자동 측정

## 아키텍처

### 옵션 비교

| 옵션 | 저장 위치 | 사용자 동의 | 구현 분량 | 본질 가치 |
|---|---|---|---|---|
| **A. IndexedDB (브라우저)** | 사용자 폰 | 옵션 OFF 기본 | 중간 | 중간 (export 수동) |
| **B. Worker R2 (Cloudflare)** | 클라우드 | 옵션 ON 필수 | 큼 | 큼 (자동 동기화) |
| **C. 하이브리드** | IndexedDB + R2 | 양쪽 | 가장 큼 | 가장 큼 |

**권장: 옵션 A 먼저 → 안정화 후 옵션 B 추가**

### A. IndexedDB 누적 시스템

```
[사용자 사진 촬영]
    ↓
[analyzeWithLLM() 호출]
    ↓
[Gemini 응답 받음]
    ↓
[(NEW) benchmarkCollector.save(b64, result)]
    ↓
[IndexedDB store: yeoguiseon-benchmark]
    ↓
[30장 도달 시 toast 알림: "벤치마크 export 가능"]
    ↓
[설정에서 Export → JSON zip 다운로드]
    ↓
[benchmark/auto_samples/ 에 풀기]
    ↓
[python scripts/benchmark.py --auto 실측]
```

### 구현

#### 1. js/benchmark_collector.js (신규, ~150줄)

```js
// 여기선 v4 — 시연 사진 자동 누적 (옵션, 사용자 동의 필요)
'use strict';

const BC = {
  DB_NAME: 'yeoguiseon-benchmark',
  STORE: 'samples',
  TARGET_COUNT: 30,
  enabled: false,  // localStorage에서 갱신

  async init() {
    this.enabled = localStorage.getItem('benchmark.enabled') === 'true';
    if (!this.enabled) return;

    this.db = await new Promise((resolve, reject) => {
      const req = indexedDB.open(this.DB_NAME, 1);
      req.onupgradeneeded = e => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(this.STORE)) {
          const store = db.createObjectStore(this.STORE, {
            keyPath: 'id', autoIncrement: true
          });
          store.createIndex('ts', 'ts');
        }
      };
      req.onsuccess = e => resolve(e.target.result);
      req.onerror = e => reject(e.target.error);
    });
  },

  async save(imageBase64, geminiResult) {
    if (!this.enabled || !this.db) return;
    const tx = this.db.transaction(this.STORE, 'readwrite');
    await tx.objectStore(this.STORE).add({
      image: imageBase64.slice(0, 200000),  // 200KB 캡
      result: geminiResult,
      ts: Date.now(),
      version: window.APP_VERSION || 'unknown',
    });
  },

  async count() {
    if (!this.db) return 0;
    return new Promise(r => {
      const req = this.db.transaction(this.STORE, 'readonly')
        .objectStore(this.STORE).count();
      req.onsuccess = () => r(req.result);
    });
  },

  async export() {
    if (!this.db) return null;
    return new Promise(r => {
      const req = this.db.transaction(this.STORE, 'readonly')
        .objectStore(this.STORE).getAll();
      req.onsuccess = () => {
        const blob = new Blob([JSON.stringify(req.result, null, 2)],
                             { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `benchmark_${new Date().toISOString().slice(0,10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        r(req.result.length);
      };
    });
  },

  async clear() {
    if (!this.db) return;
    const tx = this.db.transaction(this.STORE, 'readwrite');
    await tx.objectStore(this.STORE).clear();
  },

  setEnabled(v) {
    this.enabled = v;
    localStorage.setItem('benchmark.enabled', v ? 'true' : 'false');
    if (v && !this.db) this.init();
  },
};
window.benchmarkCollector = BC;
BC.init();
```

#### 2. app.html 통합 (3줄 추가)

```html
<!-- head에 추가 -->
<script src="./js/benchmark_collector.js"></script>

<!-- analyzeWithLLM() 끝에 1줄 추가 -->
if (window.benchmarkCollector?.enabled) {
  benchmarkCollector.save(base64, parsedResult);
}

<!-- 설정 모달에 토글 추가 -->
<label>
  <input type="checkbox" id="benchmarkToggle">
  벤치마크 모드 (사진·결과를 폰에 누적, 30장 시 export 가능)
</label>
```

#### 3. sw.js APP_SHELL 등록

```js
const APP_SHELL = [
  ...,
  './js/benchmark_collector.js',  // 추가
];
```

#### 4. scripts/import_benchmark.py (신규)

```python
# benchmark_YYYY-MM-DD.json (사용자 export) → benchmark/auto_samples/ + labels.csv
import json, base64, os, csv
data = json.load(open('benchmark_2026-05-28.json'))
for item in data:
    fname = f"auto_{item['id']}_{item['result']['item_id']}.jpg"
    with open(f'benchmark/auto_samples/{fname}', 'wb') as f:
        f.write(base64.b64decode(item['image']))
    # labels.csv 자동 채움 (Gemini 결과 = 임시 정답, 사용자 검토 가능)
```

#### 5. 본질 룰 ⑲ 추가

```python
# scripts/check_essence_v565.py에 추가
# ⑲ 벤치마크 모듈 정합성 (옵션 ON 사용자 데이터 보호)
if 'benchmarkCollector' in _app and not os.path.exists(
        os.path.join(ROOT, 'js/benchmark_collector.js')):
    all_ok = False  # 모듈 누락 차단
```

## 단계별 실행

### 단계 A (한 사이클): 핵심 IndexedDB 누적
- js/benchmark_collector.js 작성 (150줄)
- app.html 3줄 추가
- sw.js APP_SHELL 등록
- 설정 토글 1개
- 시연 검증 (사용자 시연 사진 → 누적 확인)

### 단계 B (한 사이클): Export + Import
- 30장 도달 시 toast 알림
- Export 버튼 (JSON zip 다운로드)
- import_benchmark.py 작성

### 단계 C (옵션, 큰 사이클): Worker R2 동기화
- 사용자 동의 시 자동 R2 업로드
- 다중 사용자 데이터 통합 (익명화)
- 회귀 자동 측정 (월 1회)

## 사용자 본질 가치

✅ **추가 행동 0** — 평소 시연 = 데이터 수집
✅ **개인정보 보호** — IndexedDB 사용자 폰만, 옵션 ON 사용자만
✅ **정확도 영구 향상** — 진짜 사용 케이스 측정 → 회귀 차단
✅ **객관 정량 측정 가능** — 한국 사물 특화 데이터 무료 누적

## 위험 점검

- **IndexedDB 용량** (50장 × 200KB = 10MB, 브라우저 한도 50MB+ 안전)
- **사용자 동의 필수** (개인정보보호법, 첫 토글 시 안내)
- **모바일 Safari 호환** (IndexedDB 지원 OK, 다만 14일 미사용 시 자동 삭제 — 알림 필요)

## 권장 시작

v5.77 push 안정 + 시연 사진 자동 누적 옵션 D 검토 결정 → 단계 A 한 사이클로 진행.

---
작성: 2026-05-28 (Opus 4.7, v5.79 사이클)
