# 일관성 유지 규칙 (충돌·에러 방지)

> **이 문서는 절대 규칙입니다.** 모든 작업에서 반드시 준수.
>
> 마지막 갱신: 2026-05-21 (v5.25 — _inherits + cityGuide UI + 텍스트 검색 규칙 추가)

---

## 0. v5.25 추가 규칙 (NEW)

### 0.1 region_exceptions.json — 시군구 코드 표준
- **5자리 행안부 표준 코드**만 사용 (예: 11680 강남, 41285 일산동구)
- 메타 키 (예: `_app_compat_note`) 절대 추가 X — `EXCEPTIONS[code].exceptions?.[item]` 검사 시 .exceptions 못 찾으면 빈 객체로 fallback되지만, 깔끔하게 5자리 키만
- 동일 코드 중복 추가 금지 (JSON 파싱 시 마지막이 이김)

### 0.2 _inherits 체인
- 동일 시 내 자치구가 같은 룰 → `_inherits: "부모코드"` 사용 (예: 덕양구 → 일산동구)
- 무한 루프 방지: app.html의 matchRule에 `safetyCounter = 5` 설정됨
- 부모 코드는 반드시 region_exceptions에 존재해야 함

### 0.3 cityGuide 필드 (5자리 코드 모두)
필수: `city`, `officialUrl`, `phones` 또는 `applianceRecycle.phone`  
선택: `disposalTime`, `pickupTime`, `garbageBag`, `bulkyWasteUrl`, `paperPackExchange`

### 0.4 텍스트 검색 (v5.25)
- 전역 `_escGlobal()` 함수만 사용 (renderResult 안의 `_esc`는 지역변수)
- 검색 결과 클릭 → matchRule → renderResult 흐름 유지
- 검색은 NATIONAL.items + aliases 매칭 (region_exceptions 키 검색 X)

---

## 1. 카테고리 enum (절대 변경 금지)

**17개 고정 enum**:

```
plastic, paper, paper_pack, vinyl, can, glass, styrofoam,
food, general, battery, lamp, clothes, electronics,
furniture, hazardous, medicine, reusable
```

### 충돌 위험 요소
- ❌ `food_waste` 사용 금지 (정식: `food`)
- ❌ `metal` 사용 금지 (정식: `can`)
- ❌ `appliance` 사용 금지 (정식: `electronics`)
- ❌ `paper_milk` 사용 금지 (정식: `paper_pack`)

### 동기 위치
- `data/national_rules.json` items.<key>.category
- `app.html` line 477 (categoryHint 폴백 로직)
- `app.html` SYSTEM_PROMPT enum (Gemini 응답 규제)
- `data/national_rules.json` categories.<key> (UI 라벨)

→ **4곳 모두 일치 필수**. 한 곳 추가 시 4곳 동시 갱신.

---

## 2. 데이터 키 명명 규칙

### items.<key> 명명
- **영문 snake_case 권장**: `pet_bottle`, `aluminum_can`, `food_waste`
- **환경부 한글명 허용**: 환경부 730 통합으로 들어온 한글 키 (예: `필통의 재질`) 유지 OK
- **충돌 회피**: 신규 추가 시 기존 키와 중복 확인 후 `_2`, `_3` 접미사

### regional 데이터 키
- 형식: `<sido_code>_<sigun_code>_<dong_code>`
- 예: `41281` = 일산동구, `11680` = 강남구
- 행안부 행정코드 사용 (5자리 시군구 코드)

---

## 3. sourceUrl 필수 규칙

**모든 새 item에 sourceUrl 부여 필수**:
- 환경부 분리배출.kr: `https://www.xn--oy2b29bd3a601b.kr/front/dischargeMethod/dictionaryView.do?niIdx={seq}`
- 행안부 공공데이터포털: `https://www.data.go.kr/data/{publicDataPk}/...`
- 시군구 홈페이지: 정확한 페이지 URL (메인이 아닌)

**금지**:
- ❌ 빈 sourceUrl
- ❌ 출처 없는 룰 추가
- ❌ 사이트 메인 URL만 (개별 페이지 우선)

---

## 4. 백업 자동 생성 규칙

**데이터 수정 시 항상 백업**:

```
data/national_rules.json
  ├── .backup_pre_boost.json       (Phase 1 - 1차 보강 전)
  ├── .backup_pre_v2.json          (Phase 1 - 2차 보강 전)
  ├── .backup_pre_v3.json          (Phase 1 - 3차 보강 전)
  ├── .backup_pre_v4.json          (Phase 1 - 4차 보강 전)
  ├── .backup_pre_bunri.json       (환경부 730 통합 전)
  └── .backup_pre_phase2.json      (Phase 2 시작 전, 곧 생성)
```

**보존**: 백업 절대 삭제 안 함 (audit 비교용)

---

## 5. 버전 번호 동기 규칙

**v5.8.1 같은 버전 번호는 5곳에서 동기 사용**:

1. `app.html` `<title>` 태그
2. `app.html` `.brand .version` 텍스트
3. `app.html` 상수/주석의 VERSION 표시
4. `sw.js` `const VERSION = 'v5.8.1';` (캐시 키 기반)
5. (선택) `data/national_rules.json` version 필드

→ **한 곳만 갱신하면 PWA 캐시 무효화 안 됨**. 모바일이 옛 버전 그대로.

---

## 6. JSON Schema 준수

`data/schema/rule.schema.json` 의 필수 필드:
- name (string, 1+ char)
- category (enum 17개 중 하나)
- steps (array, 1+ items)

**선택 필드**:
- note (string)
- aliases (array)
- sourceUrl (string)
- regionVariation (boolean)
- knownVariations (string)
- confidence ("high" | "medium" | "low")
- feature (string, 환경부 통합)
- caution (string, 환경부 통합)

---

## 7. 한글 인코딩 (UTF-8)

- 모든 JSON 파일: **UTF-8 (BOM 없음)**
- Python 스크립트: `# -*- coding: utf-8 -*-` 또는 PEP 3120 (default UTF-8)
- 파일 저장 시: `encoding="utf-8"` 명시

**금지**:
- ❌ Edit 도구로 한글 멀티바이트 경계 손상 (큰 패치는 Write로 통째)
- ❌ Notepad 기본 ANSI 저장

---

## 8. 카테고리별 첫 매칭 우선순위 (alias 중복 시)

같은 alias가 여러 items에 있을 때 매칭 우선순위:

1. **items 키 직접 매칭** (가장 우선)
2. **items.name 일치**
3. **items.aliases 포함** (먼저 발견된 item)

**알려진 우선 권한**:
- "음료캔" → `drink_can` 또는 `aluminum_can` (`can` 분류)
- "노트북" → `electronics`
- "헌 옷" → `old_clothes`
- "종이컵" → `disposable_paper_cup` 또는 `paper_cup`

---

## 9. 지역 룰 (Phase 2 신규 규칙)

### 우선순위
지역 룰 > 시군구 룰 > 시도 룰 > 전국 룰 (national_rules)

### 파일 구조
```
data/rules/
  ├── national.json              (전국 표준)
  ├── regional_<sido>_<name>.json  (시도, 예: regional_41_gyeonggi.json)
  ├── local_<sigun>_<name>.json    (시군, 예: local_41280_goyang.json)
  └── district_<dong>_<name>.json  (구·동, 예: district_41281_ilsandong.json)
```

### Schema (지역 룰)
```json
{
  "code": "41281",
  "name": "일산동구",
  "parent": "41280",
  "lastUpdated": "2026-05-21",
  "sourceUrl": "<시군구 공식 페이지>",
  "items": {
    "<item_key>": {
      "category": "general",  // (전국과 다른 경우만)
      "note": "<지역 특수 안내>",
      "steps": [...]
    }
  },
  "bagPrices": {
    "5L": 200, "10L": 400, "20L": 800
  },
  "bulkWasteUrl": "https://..."
}
```

---

## 10. 에러 발생 시 즉시 조치

1. **JSON 파싱 에러**: 백업으로 즉시 롤백
2. **카테고리 enum 위반**: 작업 중단 + 보고
3. **sourceUrl 누락**: 보강 안 됨 (Phase 종결 점검에서 발견)
4. **버전 동기 누락**: 모바일 캐시 무효화 실패 → 즉시 4~5곳 동시 갱신
5. **백업 누락**: 작업 중단, 백업 생성 후 재진행

---

## 11. Phase별 충돌 회피 체크리스트

각 Phase 시작 전:

- [ ] 카테고리 enum 17개 그대로인가?
- [ ] 새 데이터의 sourceUrl이 모두 부여되는가?
- [ ] 키 명명이 기존 규칙과 일관되는가?
- [ ] 백업이 생성되는가?
- [ ] 버전 번호 갱신 계획이 있는가?
- [ ] JSON schema 위반 가능성은?

→ 6개 모두 OK 후 진행.
