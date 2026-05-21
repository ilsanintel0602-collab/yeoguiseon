# WORK_HISTORY — 완료 작업 + 다시 하지 말 것

> 🛡️ **이 문서는 반복 작업 방지를 위한 것.** 새 작업 시작 전 반드시 확인.
>
> 마지막 갱신: 2026-05-21 v5.9 Phase 3 완료 시점

---

## ✅ 완료된 작업 (다시 안 함)

### Phase 1: 코어 데이터 보강 (2026-05-19 ~ 05-21)
- [x] 환경부 분리배출.kr 730 품목 크롤링 (`scripts/crawl_bunribaechul.py`)
- [x] 환경부 730 → national_rules.items 통합 (`scripts/merge_bunribaechul.py`)
- [x] categories 섹션 6개 누락 보완 (paper_pack·electronics·furniture·hazardous·medicine·reusable)
- [x] 8개 누락 alias 보강 (포장재·알루미늄캔·헌 옷·종이컵·덤벨·꽃병·이쑤시개·포장재 스티로폼)
- [x] alias 오염 정리 (12,080건 → 0)
- [x] sourceUrl 부여 (0% → 94%)
- [x] 일상 매칭률 100% 도달 (87/87)
- [x] 카테고리 enum 17개 확정 + 4곳 동기

### Phase 2: 지역 확장 (2026-05-21)
- [x] regions_meta.json 226 시군구 메타 + 250 officialUrl
- [x] bag_prices.json 249 시군구 가격 (98.4% match)
- [x] region_urls.json 32 시범 지역 URL DB
- [x] 시도별 대형폐기물 신고 URL 17개 폴백
- [x] regional 스키마 일관성 (CONSISTENCY_RULES.md 정립)

### Phase 3: 데이터-앱 연동 정비 (2026-05-21)
- [x] **rule.source || rule.sourceUrl 폴백** (app.html line 1523) — boost_v3 추가 items 출처 노출
- [x] **feature `<details>` 토글** (app.html line 1458~1465) — 환경부 풍부 정보 노출
- [x] **caution 주의 박스** (app.html line 1466~1471) — 환경부 경고 노출
- [x] **bulkWasteUrl 통합 카드** (app.html line 1509~1521) — 가구·전자 카드에 시군구 신고 URL
- [x] **region_urls.json fetch + REGION_URLS 전역 변수** (app.html line 401~415)
- [x] VERSION v5.8.1 → v5.9 4곳 동기 (app.html title/brand + sw.js)

### 인프라
- [x] auto_push.bat + auto_push.ps1 (GitHub Git Data API)
- [x] pre-deploy-check 스킬 (6가지 사전 검사)
- [x] phase-progression 스킬 (Phase 진행 표준)
- [x] data-steward 스킬 (데이터 작업 헌법)
- [x] PHASE_CRITERIA.md (각 Phase 95점 기준)
- [x] CONSISTENCY_RULES.md (11가지 절대 규칙)
- [x] DATA_INVENTORY.md (자산-앱 활용 매트릭스)
- [x] WORK_HISTORY.md (이 문서)

### 코드 패치
- [x] v5.6.4 Gemini safetySettings 4종 BLOCK_NONE
- [x] v5.6.5~6.7 책·노트북·가구류 매핑
- [x] v5.6.9 일반쓰레기·종이·플라스틱 균형
- [x] v5.8 SKIP_CLASSES에서 laptop·cell phone·backpack 제거
- [x] v5.8.1 Gemini 빈 응답 1회 자동 재시도
- [x] v5.9 데이터-앱 연동 정비

### Worker
- [x] v1.4 maxOutputTokens 2048 (Cloudflare 배포 완료)
- [x] safetySettings + finishReason 노출

---

## ⚖️ 반복 vs 오류 — 절대 혼동 금지

**이 구분이 무너지면 시스템이 무너집니다.**

| 개념 | 정의 | 행동 |
|---|---|---|
| **결과 반복 (헛수고)** | 동일한 산출물을 또 생산 | ❌ 금지 |
| **오류 체크 (안전)** | 새 데이터·코드 추가 시 일관성 검사 | ✅ 매번 강제 |
| **오류 수정 (책임)** | 새로 발견된 오류 시정 | ✅ 즉시 처리 |

> 아래 "결과 반복 금지" 항목은 **결과물 다시 생성**을 금지할 뿐, **새로운 오류·오염이 발견되면 반드시 점검·수정**해야 합니다.

---

## 🚫 결과 반복 금지 (헛수고 방지) — 단, 새로운 오류 발견 시 적용 안 함

### 점검 스크립트
- ❌ **새로운 boost_v5.py 만들지 말 것** — 통합 진입점(`boost.py` 또는 `data_audit_full.py`)으로 **확장**
  - 단, 진짜 새로운 약점 카테고리가 발견되면 → 기존 스크립트 확장으로 처리
- ❌ **새로운 audit_v3.py 만들지 말 것** — `data_audit_full.py`(steward) 확장
  - 단, 새 검사 항목이 필요하면 → `data_audit_full.py`에 stage 추가

### 데이터 영역 (재생산 금지) — 단, 변경 발견 시 갱신 필수
- ❌ 환경부 730 다시 크롤링 X — `raw_bunribaechul_730.json` 이미 있음
  - ✅ 단, 환경부 사이트 업데이트 감지 시 → 재크롤링 OK (현 데이터와 diff 검증)
- ❌ regions_meta.json officialUrl 재생성 X — 250개 이미 있음
  - ✅ 단, 시군구 통폐합·URL 변경 발견 시 → 해당 항목만 갱신
- ❌ bag_prices.json 재크롤링 X — 249개 (98.4%)
  - ✅ 단, 행안부에서 신규 가격 발표 시 → 차이만 갱신
- ❌ alias 12,080건 정리 다시 X — 이미 깨끗
  - ✅ 단, **새로운 alias 오염이 발견되면 반드시 정리** (이건 오류 수정)

### 코드 패치 (재패치 금지) — 단, 새로운 오류 발견 시 우선
- ❌ SKIP_CLASSES 다시 건드리지 X — v5.8에서 laptop/cell phone/backpack 제거 완료
  - ✅ 단, 새로운 COCO 클래스 오인 패턴이 발견되면 → 즉시 추가/제거
- ❌ COCO_TO_ITEM 가구 매핑 재작업 X — v5.6.7 완료
  - ✅ 단, 새로운 매핑 오류 발견 시 → 해당 항목 수정
- ❌ Worker safetySettings 재추가 X — v1.1부터 적용
  - ✅ 단, 새로운 BLOCK 패턴 발견 시 → 추가 설정 검토
- ❌ maxOutputTokens 재조정 X — v1.4에서 2048 확정
  - ✅ 단, 또 잘림 현상이 광범위 발견 시 → 재검토 가능

### 모바일 검증
- ❌ 동일 사물 1장씩 패치 X — Phase 8 (피드백 시스템)에서 누적
- ❌ 백업 파일 삭제 X — `*.backup_pre_*.json` 모두 보존

---

## ✅ 항상 해야 할 것 (오류 발견 시 강제, 절대 생략 금지)

이 행동들은 **WORK_HISTORY에 '완료'로 적혀 있어도 매번 다시 한다**. 시스템 안전의 토대.

### 🔁 매번 강제 검사
- ✅ **데이터 추가/변경 시 → `data_audit_full.py` 자동 실행** (steward.bat)
- ✅ **새 item 추가 시 → 카테고리 enum 17개 안에 있는지 확인** (CONSISTENCY_RULES 1번)
- ✅ **새 sourceUrl 부여 시 → 환경부/지자체 공식 도메인인지 검증**
- ✅ **버전 갱신 시 → 4곳(title/brand/sw.js + 메모리) 동기**
- ✅ **백업 자동 생성** (`*.backup_pre_<work>.json`)

### 🛠️ 새로운 오류 발견 시 즉시 시정 (회피 금지)
- ✅ alias 오염 발견 → 즉시 정리 (이전에 12,080건 했어도)
- ✅ 카테고리 enum 위반 → 즉시 수정
- ✅ 죽은 데이터(앱 미활용) 발견 → 즉시 통합
- ✅ 모바일에서 잘못된 분류 패턴 → 보강 (Phase 8 시스템에서 누적, 시급하면 즉시)
- ✅ 버전 동기 불일치 → 4곳 즉시 갱신

---

## 🧭 판단 기준 (헷갈릴 때)

**"이 작업 하지 말까?" 라고 망설일 때**:

```
물어볼 것: "이건 새로운 입력에 대한 반응인가, 옛 결과의 재생산인가?"
  
  - 새 입력 + 새로 발견된 문제 → ✅ 반드시 해야 함 (오류 수정)
  - 동일 입력 + 동일 결과 → ❌ 안 함 (헛수고)
  - 옛 작업의 보강·확장 → ✅ 기존 스크립트 확장으로 OK
```

**예시**:
- 사용자가 "alias 오염 또 있나 확인해줘" → ✅ 점검 (오류 체크는 매번)
- 진짜 새로운 오염 발견 → ✅ 정리 (오류 수정)
- 이전과 똑같이 깨끗 → 보고하고 종료 (헛수고 방지)
- "새로운 boost_v5 만들지 마" → 기존 `boost.py` 확장 (반복 방지)

---

## 🟡 보류 (필요 시 부활)

- AI Hub 데이터셋 다운로드 (Phase B — 해외 IP 차단 + 본질 충족으로 보류)
- YOLO 자체 학습 (Layer 2 — Layer 1+3 운영 충분)
- GCP 옛 키 3개 삭제 (위험도 매우 낮음)
- GitHub secret scanning 알림 dismiss

---

## ⬇️ 다음 진행 순서 (Phase별)

### 현재 위치
- ✅ Phase 1, 2 종결
- ✅ Phase 3 (데이터-앱 연동 정비) 약 95점 도달

### 다음
1. **Phase 4 (선택)** — 추가 데이터 보강 (재활용센터·무인회수기·의류수거함 위치 등)
2. **Phase 5 (선택)** — 벤치마크 자동화 (PC 기반 benchmark.py)
3. **Phase 6 (선택)** — UX 차별점 (OCR·음성·디자인)
4. **Phase 7 — 배포 통합** ⬅ **사용자가 적절 시점이라 판단 시**
   - v5.9 + 모든 누적 데이터 + Phase 3 정비 한 묶음 push
   - `scripts/auto_push.bat` 더블클릭
5. **Phase 8 (마지막)** — 사용자 피드백 시스템 (push 후 사용자 베이스 생긴 다음)

---

## 작업 명령어 매핑

| 사용자 명령 | 호출할 스킬/문서 | 결과물 |
|---|---|---|
| "데이터 추가" | data-steward SOP | 백업 + 통합 + 검증 + INVENTORY 갱신 |
| "점검" / "audit" | `scripts/cycle.bat` 또는 `audit_v2.py` | 점수 측정 + 보강 가이드 |
| "보강" / "보충" | data-steward SOP + boost.py(통합) | 새 items 추가 + 자동 검증 |
| "푸시" / "push" | `scripts/auto_push.bat` | 한 번에 commit + push |
| "정비" / "수정" | data-steward SOP + DATA_INVENTORY | 미활용 영역 발견 + 통합 |
| "에러" / "충돌" | CONSISTENCY_RULES + data-steward 자동 검사 | 원인 진단 + 즉시 시정 |

---

## 핵심 명세 — 잊지 말 것

- **버전 동기 4곳**: app.html `<title>`, `.brand .version`, sw.js `VERSION`, (선택) national_rules version 필드
- **백업 명명**: `*.backup_pre_<phase>_<step>.json`
- **카테고리 enum 17개 고정**: 절대 추가/변경 안 함
- **sourceUrl 필수**: 모든 새 item
- **데이터 = 사용자 노출**: 모바일에 안 보이면 죽은 데이터
- **반복 = 시스템 실패**: 같은 작업 두 번 = 즉시 멈춤
