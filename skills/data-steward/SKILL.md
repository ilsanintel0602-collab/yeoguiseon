---
name: data-steward
description: 여기선 v6 데이터의 최고 담당 에이전트. 모든 데이터 작업(추가·검증·앱 활용·백업·일관성)이 이 스킬을 거치도록 강제. 데이터 자산 100% 활용 보장 + 반복 작업 방지 + 일관성 + 충돌·에러 0.
---

# Data Steward — 데이터 자산 최고 담당 에이전트

> 🛡️ **이 스킬은 여기선 v6의 모든 데이터 작업의 헌법입니다.**
>
> 데이터 파일을 추가하거나 변경하기 전에 **반드시** 이 절차를 따른다.

---

## 핵심 원칙 (절대 변경 금지)

### 1. 데이터 = 사용자 가치
- 모든 데이터 필드는 **사용자가 모바일에서 볼 수 있어야** 의미가 있음
- 데이터에만 있고 앱에서 안 쓰이는 필드 = **죽은 데이터**. 즉시 노출 또는 제거.
- 예: Phase 1 sourceUrl 94% 부여했는데 모바일에 미노출 → v5.9에서 정비

### 2. 추가 = 자동 통합
- 새 데이터 필드 추가 시:
  1. 데이터 파일에 필드 추가
  2. **즉시** app.html 렌더링 코드에 통합
  3. **즉시** audit 스크립트에 검사 항목 추가
  4. 백업 + 버전 갱신
- 셋 중 하나라도 누락 → 작업 미완성

### 3. 일관성 = 절대 규칙
- 카테고리 enum 17개 고정 (`CONSISTENCY_RULES.md` 참고)
- sourceUrl 필수 (모든 새 item)
- 백업 명명 표준: `<file>.backup_pre_<phase>_<step>.json`
- 버전 동기 4곳 (`app.html title/brand`, `sw.js VERSION`)

### 4. 반복 vs 오류 — 절대 혼동 금지

**세 가지를 명확히 구분**:

| 개념 | 의미 | 행동 |
|---|---|---|
| **결과 반복 (헛수고)** | 같은 산출물 또 생산 | ❌ 금지 |
| **오류 체크 (안전)** | 새 입력에 대한 일관성 검사 | ✅ 매번 강제 |
| **오류 수정 (책임)** | 새로 발견된 오류 시정 | ✅ 즉시 처리 |

- 같은 결과를 또 생산 = 시스템 실패 (보지 마 + 안 함)
- 새 데이터·코드 추가 = 검사 매번 강제 (이전에 깨끗했어도)
- 새 오류 발견 = 즉시 시정 (WORK_HISTORY에 '완료'로 적혀 있어도 새로운 사례면 다시 시정)

작업 전 `docs/WORK_HISTORY.md` 확인:
- "결과 반복 금지" 섹션 = 동일 결과물 재생산 금지
- "항상 해야 할 것" 섹션 = 오류 검사·시정은 매번 강제

비슷한 스크립트(boost_v1~v4) 만들기 전에 기존 스크립트 **확장** 우선 — 이건 결과 반복 방지.
그러나 **새로운 오류·약점 발견 시 → 기존 스크립트 확장으로 처리**하는 건 책임 영역.

---

## 표준 작업 절차 (SOP)

### 데이터 추가/변경 시 (Pre-flight Checklist)

```
□ 1. 백업 생성 (자동)
□ 2. CONSISTENCY_RULES.md의 11가지 규칙 통과 확인
□ 3. WORK_HISTORY.md에 비슷한 작업 있는지 확인 (반복 방지)
□ 4. 추가/변경할 필드가 app.html에서 어떻게 노출될지 미리 계획
□ 5. data_audit_full.py 사전 실행 → 현 점수 측정
□ 6. 데이터 추가/변경 실행
□ 7. app.html 렌더링 코드 즉시 통합
□ 8. audit 스크립트 검사 항목 추가
□ 9. data_audit_full.py 사후 실행 → 점수 향상 확인
□ 10. WORK_HISTORY.md에 작업 기록
□ 11. 버전 갱신 (v5.9 → v5.10 등) 4곳 동기
```

각 단계 누락 시 작업 **재개 불가**.

---

## 데이터 자산 매트릭스 (반드시 갱신)

`docs/DATA_INVENTORY.md`에 모든 데이터 파일·필드와 앱 활용 상태를 명시.

새 필드 추가 시 → DATA_INVENTORY에 행 추가 + 활용 코드 라인 명시.

### 매트릭스 예시
| 데이터 | 필드 | 출처 | app.html 활용 라인 | 사용자 노출 |
|---|---|---|---|---|
| national_rules.json | sourceUrl | 환경부 730 통합 | 1523~1527 | ✅ 결과 카드 출처 링크 |
| national_rules.json | feature | 환경부 730 | 1458~1465 | ✅ 펼치기 추가 안내 |
| region_urls.json | bulkWasteUrl | 시도별 | 1509~1521 | ✅ 가구·전자 카드 |

---

## 자동 검증 트리거

### data_audit_full.py 한 번에 검사:
1. **JSON 무결성** — 모든 데이터 파일 JSON valid
2. **필수 필드 완비** — name/category/steps 100%
3. **카테고리 enum 정합** — 17개 외 사용 0
4. **sourceUrl 부여율** — ≥ 90%
5. **앱 활용도** — 모든 데이터 필드가 app.html에서 사용되는지
6. **버전 동기** — 4곳 일치
7. **백업 보존** — 모든 백업 파일 존재
8. **카테고리 ↔ catLabels ↔ SYSTEM_PROMPT 3자 정합**
9. **fetch URL 정합** — app.html이 load 시도하는 모든 파일이 실제 존재
10. **alias cross-item 중복** — 모호한 매칭 방지

총 10개 검사. 합격선 95.

---

## 반복 작업 방지 규칙

**작업 시작 전 필독**:
1. `docs/WORK_HISTORY.md`의 "완료 작업" 섹션 확인
2. "다시 하지 말 것" 섹션 확인
3. 비슷한 스크립트 (`scripts/`) 검색 — `boost_*.py`, `audit_*.py` 등

**같은 패턴 또 만드는 게 발견되면**:
- 기존 스크립트 **확장**으로 우회 (예: `boost.py` 통합)
- 새로 만들기 전 사용자에게 알림

---

## 변경 명시 (어떤 작업 후 무엇이 보장되는가)

### 단일 보강 (boost) 작업 후 보장
- 새 items의 sourceUrl 부여 (환경부 메인 URL 최소)
- 백업 생성 (`*.backup_pre_<work>.json`)
- audit 점수 측정
- 매칭 검증 (새로 추가한 단어들이 정확 매칭되는지)

### 새 데이터 파일 추가 후 보장
- app.html의 `loadAllData()` 함수에 fetch 추가
- 전역 변수 선언 (예: `let NEW_DATA = null;`)
- 활용 코드 작성 (renderResult 등)
- DATA_INVENTORY 갱신

### Phase 종결 후 보장
- audit_phase{N}.py 95+ 도달 (또는 정직히 미달 명시)
- WORK_HISTORY 갱신
- 메모리 (`project_v4_status.md`) 갱신
- HANDOFF 누적

---

## 데이터 자산 100% 활용 보장

### 현재 자산 (Phase 1·2 완료 후)

| 데이터 | items 수 | 앱 활용 | 미활용 영역 |
|---|---|---|---|
| national_rules.json | 738 | ✅ name/category/steps/note/sourceUrl/feature/caution | dischargeMethodFull(미사용 OK, 백업용) |
| regions_meta.json | 226 시군구 | ✅ officialUrl/phone | boundingBox(GPS용 미래) |
| bag_prices.json | 249 시군구 | ✅ 가격 표시 | 전체 봉투 종류(현재 가정용만) |
| recycle_centers.json | 전국 | ✅ 표시 | — |
| region_urls.json | 32+218=250 | ✅ bulkWasteUrl 활용 | cleanUrl(일부만 노출) |
| region_exceptions.json | 5 | ✅ EXCEPTIONS 매칭 | — |

**미활용 = 0건** 목표. 발견 시 즉시 통합.

---

## 에러 방지 — 자주 발생하는 오류 패턴 + 대처

| 오류 | 원인 | 대처 |
|---|---|---|
| 모바일에 새 데이터 안 보임 | sw.js VERSION 미갱신 → PWA 캐시 | VERSION 4곳 동기 갱신 (체크리스트) |
| Gemini 응답에 알 수 없는 카테고리 | SYSTEM_PROMPT enum과 items.category 불일치 | CONSISTENCY_RULES 11번 카테고리 enum 17개 고정 |
| 새 item 매칭 안 됨 | aliases에 등록 안 됨 | boost 스크립트 매칭 검증 단계 필수 |
| 사용자가 카드에서 출처 못 봄 | rule.source ≠ rule.sourceUrl 필드 차이 | source \|\| sourceUrl 폴백 코드 |
| audit 점수 매번 다름 | audit 스크립트 자체 갱신 안 됨 | data_audit_full.py 단일 진입점 사용 |

---

## 작업 명령 (사용자 → 에이전트)

사용자가 데이터 관련 요청을 했을 때 **이 스킬 자동 호출**:

> "데이터 추가해줘" / "보강해줘" / "정비" / "점검" / "왜 안 보여" / "충돌" / "에러" / "일관성"

→ data-steward 스킬을 invoke해서 SOP에 따라 진행.

---

## 종합

이 스킬은 **빈틈없는 데이터 운영의 헌법**입니다. 빠지는 게 없도록, 같은 작업 두 번 안 하도록, 일관성과 신뢰성을 보장합니다. **여기선 v6의 본질 = 정확한 분리 안내**의 토대.
