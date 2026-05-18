---
name: add-region
description: 여기선 앱에 새로운 지역(시·군·구)의 분리수거 규칙을 추가합니다. 환경부 자료와 지자체 공식 홈페이지를 검색해서 데이터를 수집하고, regions.json과 app.html에 동기화합니다.
---

# 새 지역 추가 스킬

여기선 앱에 새 지역의 분리수거 규칙을 안전하게 추가하는 자동화 스킬.

## 언제 사용?

- 사용자가 "OO구도 추가해줘" 라고 요청할 때
- "전국 확장 작업 시작" 같은 명령
- 새 지자체 공식 자료가 업데이트됐을 때

## 입력
- 추가할 지역명 (예: "부산 해운대구")
- 또는 지역 코드 (예: "26350")

## 처리 단계

### 1단계: 지역 정보 수집
```
WebSearch로 다음 정보 수집:
- 정확한 행정구역 명 ("부산광역시 해운대구")
- 행정구역 코드 (통계청 SGIS 또는 행안부 코드)
- 지자체 공식 홈페이지
- 청소행정과 전화번호
- 대략적인 좌표 박스 (지역의 동서남북 위도/경도)
```

### 2단계: 분리수거 규칙 검색
```
WebSearch + WebFetch로:
- "{지역명} 분리수거 안내"
- "{지역명} 청소행정과 분리배출"
- 지자체 공식 PDF 또는 HTML
- 환경부 '내손안에 분리배출' 데이터
```

### 3단계: 헷갈리는 케이스 검증
필수 확인 18개 물건:
- rubber_glove (고무장갑)
- pet_bottle (페트병)
- instant_rice_bowl (즉석밥 용기)
- receipt (영수증)
- paper_cup_coated (코팅 종이컵)
- vinyl_bag (비닐봉투)
- milk_carton (우유팩)
- paper_box (종이박스)
- glass_bottle (유리병)
- can, styrofoam, food_waste
- broken_glass_bottle, broken_ceramic
- small_plastic_cap, toothbrush, hanger
- cosmetic_pump, food_contaminated_vinyl

각 물건마다:
- category (plastic/vinyl/paper/can/glass/styrofoam/food/general)
- note (지역별 주의사항)
- confidence (high/medium/low)

### 4단계: 데이터 작성
`regions.json` 업데이트:
```json
"haeundae-gu": {
  "name": "부산광역시 해운대구",
  "shortName": "해운대",
  "code": "26350",
  "boundingBox": { "minLat": ..., "maxLat": ..., "minLng": ..., "maxLng": ... },
  "officialSource": "https://www.haeundae.go.kr/...",
  "phone": "051-..."
}
```

각 item의 rules에 새 지역 추가:
```json
"rubber_glove": {
  "rules": {
    ...
    "haeundae-gu": { "category": "...", "note": "...", "confidence": "high" }
  }
}
```

### 5단계: app.html 동기화
app.html 안의 인라인 RULES 객체에도 동일하게 반영:
- RULES.regions[지역ID]
- RULES.items[각].rules[지역ID]
- REGION_BOXES[지역ID]
- 설정 패널 `<select>` 옵션 추가

### 6단계: 검증
- JSON 유효성 (python -m json.tool regions.json)
- 모든 물건에 새 지역 룰 존재
- 좌표 박스 합리적인지 (실제 지도 확인)
- 출처 URL 작동하는지

### 7단계: 보고
- 추가된 지역
- 검증된 물건 수
- 출처
- confidence 분포 (high/medium/low 비율)
- 다른 지역과의 차이점 (differenceWarning 후보)

## 안전 가드레일

- ❌ 추측으로 카테고리 채우지 말 것 → "확인 필요" 플래그
- ❌ 같은 지역의 다른 사용자 데이터를 그대로 복사하지 말 것
- ✅ 모든 룰에 출처 URL 또는 confidence: low 명시
- ✅ 좌표 박스는 실제 지도와 교차 검증
- ✅ 시민 신고가 누적된 정보는 더 높은 신뢰도

## 예시 사용

사용자: "여기선에 부산 해운대구도 추가해줘"

스킬 실행:
1. WebSearch "부산 해운대구 분리수거"
2. 해운대구청 청소행정과 페이지 fetch
3. 환경부 자료 교차 확인
4. 18개 물건 룰 작성 (confidence 표기)
5. regions.json + app.html 업데이트
6. JSON 검증
7. 보고: "해운대구 추가 완료. 18개 물건, high 12 + medium 6, 출처: 해운대구청 2025.03 안내"
