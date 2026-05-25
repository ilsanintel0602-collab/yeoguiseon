# app.html 모듈 분할 설계 — truncation 영구 종결

## 현황 분석 (2026-05-25)

- **파일 크기**: 158,704 bytes (139,137 chars), 3,045 줄
- **구조**:
  - header: 36줄 (메타·OG)
  - style: 286줄 (CSS)
  - html: 156줄 (UI 구조)
  - **script: 2,565줄 (84%)** ← 주된 위험 지점
  - end: 2줄
- **함수·const 정의**: 378개
- **truncation 사고**: 누적 20회 (전부 script 영역 큰 Edit 시 발생)

## 근본 원인

- 단일 파일에 2,565줄 inline JS — Edit 도구가 큰 한국어 블록 처리 시 끝부분 byte 단위 잘림
- 자동 회복 시스템 (snapshot 차이 추출)이 잘 작동하지만 매번 1~2분 사고 처리 비용
- 대규모 push 시점 사고 가능성 (auto_push.bat이 quick_check로 차단하지만 안전 마진 ↓)

## 설계 옵션 4가지 비교

### 옵션 A. ES Modules (`<script type="module">`)
**장점**: 빌드 단계 X, 모던 브라우저 즉시 동작, import/export 표준
**단점**:
- HTTP/2 multiplex 의존 (파일 N개 = N개 fetch)
- Service Worker 캐시 전략 재설계 필요
- localStorage·전역 state 공유 패턴 재작성
- iOS Safari 호환성 점검 필요

**작업량**: 큼 (1~2일). 함수 378개를 5~8개 모듈로 분류 + import 체인 설계.

### 옵션 B. 빌드 단계 도입 (Vite·esbuild)
**장점**: 단일 번들 출력 → 운영 환경 변화 X
**단점**:
- Node.js 의존 (사용자 환경에 빌드 단계 추가)
- 사용자 명령 1단계 추가: `npm run build`
- 디버깅 어려움 (sourcemap 필요)
- 사용자 본질 명령 "운영비 0원, 단순" 위배

**작업량**: 중간 (반나절). 단 사용자 workflow 변경.

### 옵션 C. 부분 추출 — Hybrid (권장)
**장점**:
- 점진적 분할 (사고 빈도 큰 영역만 추출)
- 기존 워크플로 유지 (단일 app.html 진입점)
- 위험 점진적 감소
- 빌드 단계 X (별도 .js 파일을 `<script src="">`로 로드)

**단점**: 완전 모듈화 X (절반은 inline 유지)

**작업량**: 작음 (2~3시간). 가장 큰 함수·데이터 영역만 분리.

**분할 대상 (우선순위)**:
1. **`SYSTEM_PROMPT` 정의** (~30줄, 한국어 큰 블록 ← 핵심 truncation 위험) → `js/prompts.js`
2. **`matchRule` + cityGuide 로직** (~150줄) → `js/match.js`
3. **`renderResult` 결과 카드** (~500줄, 한국어 HTML 템플릿 다수 ← 두 번째 위험) → `js/render.js`
4. **OCR·brand 매칭** (~200줄) → `js/ocr_brand.js`
5. **카메라·detect** (~300줄) → `js/camera.js`

남는 app.html: 약 1,400줄 = inline 유지 (DOMContentLoaded + 전역 state + UI 이벤트 핸들러)

### 옵션 D. 단일 파일 유지 + 자동 회복 강화
**장점**: 변경 0, 위험 0
**단점**: 사고 빈도 ↓ X (계속 20+회 누적)

**작업량**: 없음. 현 상태 그대로.

## 권장: **옵션 C (Hybrid 부분 추출)**

### 단계별 실행 계획 (시연 안정 후)

**단계 1 (1시간)**: `js/prompts.js` 분리
- `SYSTEM_PROMPT` 상수 1개만 추출 (가장 큰 한국어 블록)
- app.html에 `<script src="./js/prompts.js"></script>` 추가
- 전역 변수 `window.SYSTEM_PROMPT`로 노출
- quick_check 통과 + 모바일 검증
- truncation 위험 영역 1개 제거

**단계 2 (1시간)**: `js/render.js` 분리
- `renderResult` + 보조 HTML 템플릿 함수 추출
- 의존: `matchRule`, `cat`, regionMeta 등 — 매개변수 전달 또는 전역 참조
- 가장 큰 위험 영역 제거

**단계 3 (30분)**: 나머지 (옵션)
- match.js · ocr_brand.js · camera.js
- 추가 안정성 ↑

### 위험 평가

| 변경 | truncation 위험 | 작동 위험 |
|---|---|---|
| 단계 1 (prompts.js) | 즉시 0 (한국어 블록 분리) | 매우 작음 (상수 1개) |
| 단계 2 (render.js) | 큰 ↓ | 작음 (함수 분리, 전역 참조 검증 필요) |
| 단계 3 (선택) | 추가 ↓ | 중간 (의존 체인 재설계) |

### Service Worker 영향

- 새 .js 파일들도 sw.js 캐시 목록에 추가 (`APP_SHELL` 배열)
- 버전 bump 시 모두 무효화 (현재 패턴 그대로)

### 마이그레이션 안전 룰

1. **각 단계마다 snapshot 저장** (auto_snapshot save)
2. **quick_check 통과 후만 다음 단계**
3. **단계 1만 push → 시연 검증 → 단계 2 진행**
4. **truncation 사고 발생 시 즉시 snapshot restore + 단계 polyfill 시도**

### 결정 시점

- **시연 결과 안정 (사용자 v5.46 OK 확인)** 후 단계 1 시도
- 단계 1 성공 시 단계 2 진행
- 단계 2 성공 시 단계 3은 선택 (추가 가치 vs 의존 복잡도)

## 최종 권장

**지금은 옵션 C 단계 1 (prompts.js)만 시연 후 즉시 시도 권장**. 가장 큰 truncation 위험 영역 (한국어 SYSTEM_PROMPT) 제거. 30분 작업, 위험 작음, 즉시 효과.

옵션 A·B는 시연 안정 후 별도 큰 작업 사이클로 검토.
