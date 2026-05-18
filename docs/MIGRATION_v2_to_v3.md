# v2.2 → v3.0 마이그레이션

## 🎯 비전 변화

**v2.2:** "강남↔일산 이주자 도구" (페르소나 중심)
**v3.0:** "대한민국 누구나 분리수거 도구" (전국민 중심)

## 🏗 아키텍처 변화

### 데이터 구조

**v2.2:**
```
RULES.items["rubber_glove"].rules["gangnam-gu"] = { category, note }
                          .rules["ilsanseo-gu"] = { ... }
```
→ 모든 물건이 모든 지역에 대해 정의돼야 함. 확장 불가.

**v3.0:**
```
national_rules.json    ← 모든 물건의 환경부 표준 룰 (1번만 정의)
region_exceptions.json ← 표준과 다른 지역만 정의 (예외 위주)
regions_meta.json      ← 226 시군구 메타 정보
```
→ 새 지역 추가 시 메타만 등록 (예외 없으면 자동으로 표준 적용)

### 매칭 함수

**v2.2:**
```javascript
match(item, region):
  return RULES.items[item].rules[region]
  // 지역 룰 없으면 fallback
```

**v3.0:**
```javascript
match(item, regionCode):
  // 1. 지역 예외 우선
  if (exceptions[regionCode]?.exceptions[item]) return that
  // 2. 환경부 표준
  if (NATIONAL.items[item]) return that
  // 3. 최종 폴백
  return { category: 'general', source: 'fallback' }
```

### UI 변화

**v2.2:**
- 거주지 드롭다운 = 2개 옵션만

**v3.0:**
- 광역시/도 (17개) → 시군구 (해당 광역의 시군구만) 2단계
- GPS 자동: 전국 매핑

### 포트

- v1: 8001
- v2: 8002
- **v3: 8003** (동시 실행 가능)

## 📊 영향 비교

| 지표 | v2.2 | v3.0 | 변화 |
|---|---|---|---|
| 사용 가능 인구 | 100만 | 5,200만 | **52배** |
| 시군구 커버리지 | 2/226 | 226/226 | **100%** |
| 데이터 효율 | 지역×물건 = 큰 매트릭스 | 표준 + 예외만 | 5배 컴팩트 |
| 새 지역 추가 비용 | 모든 룰 재작성 | 메타만 등록 | 90% 절감 |
| 코드 복잡도 | 비슷 | 약간 ↑ (트리 UI) | 관리 가능 |

## 🔄 기존 사용자 영향

### v2 사용자가 v3로 이동 시
- localStorage 키가 다름 (`regionLevel1`, `regionLevel2`)
- 기존 거주지 설정 → 다시 선택 필요 (한 번)
- 캐시·API 키는 유지 가능

### 데이터 손실 없음
- v2의 강남, 일산 룰 모두 v3의 `region_exceptions.json`에 보존
- 기존 18개 물건 모두 v3의 `national_rules.json`에 포함

## ⚠️ 변경 시 주의

- v3는 **외부 JSON fetch** 필요 → 반드시 서버 통해 실행 (file:// 안 됨)
- 첫 로드 시 데이터 3개 + YOLO 모델 → 약간 더 무거움
- 시군구 데이터는 110KB → 첫 로드 후 캐시됨

## 🚀 v3 이후 (v4 예정)

- 동·단지 단위 세부 룰 (`level3`)
- 사용자 신고 자동 반영 시스템
- 배출일 알림 (PWA 푸시)
- 다국어 (외국인 이주자)
- React Native 진짜 모바일 앱
