# 데이터 추가 가이드

새로운 지역과 물건을 추가하는 방법.

## 1. 새 지역 추가

### 1-1. regions.json 수정 (예: 부산 해운대구)

```json
"haeundae-gu": {
  "name": "부산광역시 해운대구",
  "shortName": "해운대",
  "code": "26350",
  "boundingBox": {
    "minLat": 35.15, "maxLat": 35.22,
    "minLng": 129.13, "maxLng": 129.22
  },
  "officialSource": "https://www.haeundae.go.kr/",
  "phone": "051-749-4000"
}
```

### 1-2. app.html의 RULES.regions 객체도 동일하게 추가

(현재 인라인 데이터를 쓰고 있어서 app.html에도 반영 필요)

### 1-3. 설정 패널 드롭다운에 옵션 추가

```html
<option value="haeundae-gu">부산광역시 해운대구</option>
```

### 1-4. REGION_BOXES에 좌표 박스 추가

```javascript
const REGION_BOXES = {
  ...
  'haeundae-gu': { minLat: 35.15, maxLat: 35.22, minLng: 129.13, maxLng: 129.22 }
};
```

## 2. 새 물건 추가

### items 객체에 추가

```json
"used_battery": {
  "name": "폐건전지",
  "rules": {
    "gangnam-gu": {
      "category": "general",
      "note": "지정 수거함 또는 동주민센터",
      "confidence": "high"
    },
    "ilsanseo-gu": {
      "category": "general",
      "note": "지정 수거함 또는 동주민센터",
      "confidence": "high"
    }
  }
}
```

### LLM 시스템 프롬프트에 item_id 추가

```javascript
const SYSTEM_PROMPT = `...
알려진 item_id: ..., used_battery, ...`;
```

## 3. 신뢰도 표기 규칙

| confidence | 의미 | 출처 |
|---|---|---|
| high | 환경부/지자체 공식 자료 직접 확인 | 공식 홈페이지, 공식 안내문 |
| medium | 언론 보도 또는 종합 자료 | 뉴스 기사, 정리 블로그 |
| low | 일반 가이드라인 추정 | 추정, 검증 필요 |

## 4. 검증 체크리스트

새 데이터 추가 시 확인:

- [ ] 지자체 공식 홈페이지 또는 PDF에서 직접 확인
- [ ] 출처 URL을 regions.json에 기록
- [ ] confidence 표기
- [ ] 같은 구 안에서도 동·단지마다 다를 수 있음 → note에 명시
- [ ] 한국어 표기 자연스러운가?

## 5. 헷갈리는 케이스 (지역마다 다른 처리)

`differenceWarning: true` 표시하면 결과 화면에서 경고 띠가 뜸.

대표 사례:
- 고무장갑 (강남=비닐, 일산=일반)
- 즉석밥 용기 (강남=플라스틱, 일산=일반)
- 코팅 종이컵 (강남=종이팩, 일산=일반)
- 작은 플라스틱 뚜껑 (강남=재활용, 일산=일반)

## 6. 데이터 출처 우선순위

1. **환경부 '내손안에 분리배출'** — https://www.recycling-info.or.kr/
2. **각 지자체 청소행정과 공식 안내**
3. **지자체 홈페이지 PDF/HTML**
4. **언론 보도 (검증 필요)**
5. **사용자 신고 후 검증 통과 (커뮤니티)**

## 7. 향후 자동화 (Phase 2~3)

- 사용자 신고 누적 시 자동 confidence 강등
- 지자체 사이트 변경 감지 봇 (정기 크롤링)
- 검증된 사용자 등급별 가중치
