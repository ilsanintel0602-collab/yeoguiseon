# DATA_INVENTORY — 데이터 자산 + 앱 활용 매트릭스

> 🛡️ **여기선 v6의 모든 데이터 자산을 완전 명시.** 새 데이터 추가 시 반드시 이 문서 갱신.
>
> 마지막 갱신: 2026-05-21 (v5.24 — _inherits + cityGuide UI + augment_v2 진행 중)

---

## 데이터 파일 전체 목록 (v5.24 기준)

| 파일 | 용도 | 크기 | 출처 |
|---|---|---|---|
| **national_rules.json** | 전국 표준 분리수거 룰 | **765 items** (+27 vs v5.13) | 환경부 분리배출.kr + 행안부 표준 + 일상 어휘 |
| **regions_meta.json** | 226 시군구 메타 | 226 + 광역시 본청 = 250 | 행안부 행정표준코드 |
| **region_exceptions.json** | 지역 예외 룰 | **20개 시군구** (vs 5개) — _inherits 상속 지원 | 각 시군구 공식 페이지 |
| **region_urls.json** | 시군구 URL DB (분리수거·대형폐기물) | 32 (시범) | 공식 도메인 |
| **bag_prices.json** | 종량제봉투 가격 | 249 시군구 (98.4%) | 행안부 #15025538 |
| **recycle_centers.json** | 전국 재활용센터 | 전국 | 행안부 + 시군구 |
| **ocr_keywords.json** | OCR 한국어 매핑 | 단순화됨 (AA 등 위험 키워드 제거) | 자체 구축 |
| **brand_db.json** | 한국 제품 브랜드 DB | — | 자체 구축 |
| **raw_bunribaechul_730.json** | 환경부 원본 (참고용) | 730 품목 | 환경부 분리배출.kr |
| **.augment_progress.json** ⭐ | augment_v2 진행 상황 | 동적 (실시간) | 자동 |
| **alias backup_*.json** | 데이터 변경 시 자동 백업 | 다수 | 자동 |

### 📈 v5.24 데이터 변화 (오늘)

| 항목 | v5.13 | v5.24 | 증감 |
|---|---|---|---|
| **alias 총 수** | ~12,000 (오염 포함) → ~2,061 (정리) | **2,336** | +275 (룰 기반) |
| **alias 평균/item** | 2.7 | **3.1** | +0.4 |
| **electronics 평균** | 1.2 | **1.97** | 약점 해소 |
| **furniture 평균** | 1.3 | **1.55** | 약점 해소 |
| **시군구 cityGuide** | 5 | **20** | +15 (+300%) |
| **시군구 룰 (일산동구 기준)** | 30 | **37** | +7 |

---

## national_rules.json 필드별 활용 매트릭스

| 필드 | 데이터 유무 | app.html 활용 라인 | 사용자 노출 | 상태 |
|---|---|---|---|---|
| `name` | 738 (100%) | 곳곳 | 결과 카드 제목 | ✅ |
| `category` | 738 (100%) | 곳곳 | 카테고리 뱃지 | ✅ |
| `note` | 737 (99.9%) | 1456 | 💡 안내 박스 | ✅ |
| `steps` | 738 (100%) | 1449~1454 | 📋 배출 방법 | ✅ |
| `aliases` | 11,949 총 (16/item) | matching 로직 | 매칭에 활용 | ✅ |
| `regionVariation` | bool | 471 | 일산동구 전용 배너 | ✅ |
| `confidence` | high/medium/low | 1376~ | 신뢰도 표시 | ✅ |
| **`sourceUrl`** | 694/738 (94%) | **1523~1527** (v5.9 폴백) | **📚 데이터 출처 링크** | ✅ |
| **`feature`** | 651 (88%) | **1458~1465** (v5.9 신규) | **📖 환경부 추가 안내 (펼치기)** | ✅ |
| **`caution`** | 423 (57%) | **1466~1471** (v5.9 신규) | **⚠️ 주의 박스** | ✅ |
| `official_classification` | 환경부 통합 | **1505~1513** (v5.12) | **🏷️ 환경부 분류 트리** | ✅ |
| `sourceName` | 일부 | 1523 | 출처 라벨 | ✅ |
| `sourceGrade` | 일부 (A/B) | 1525 | 등급 뱃지 | ✅ |
| `lastVerified` | 일부 | 1527 | 📅 확인일 | ✅ |
| `dischargeMethodFull` | 환경부 통합 | 미사용 | — | 🟡 백업용 |

**활용률: 12/15 핵심 필드 (80%)** — `official_classification`은 검색용으로 활용 가능, `dischargeMethodFull`은 백업.

---

## regions_meta.json 필드별 활용

| 필드 | 데이터 유무 | app.html 활용 | 사용자 노출 | 상태 |
|---|---|---|---|---|
| `level1.<sido>.name` | 17개 | 1519 | 지역 라벨 | ✅ |
| `level2.<sigun>.name` | 226 | 1519 | "○○구 공식 안내" | ✅ |
| `level2.<sigun>.officialUrl` | 250 | 1520 | 공식 페이지 링크 | ✅ |
| `level2.<sigun>.phone` | 250 | **1601** (v5.12) | **📞 전화번호 (공식 안내 옆)** | ✅ |
| `boundingBox` | 모두 | 미사용 | GPS 자동 위치 (미래) | 🔮 |

---

## region_urls.json 필드별 활용

| 필드 | 데이터 유무 | app.html 활용 | 사용자 노출 | 상태 |
|---|---|---|---|---|
| `regions.<code>.officialUrl` | 32 | 1511 (폴백) | — | ✅ |
| `regions.<code>.cleanUrl` | 강남·서초 등 | 1511 | 청소 페이지 링크 | ✅ |
| `regions.<code>.bulkWasteUrl` | 강남·강동·부산 | **1509~1521** (v5.9 신규) | 🏗️ 대형폐기물 신고 | ✅ |
| `regions.<code>.phone` | 32 | 1521 | 📞 전화 | ✅ |

---

## bag_prices.json 필드별 활용

| 필드 | 데이터 유무 | app.html 활용 라인 | 사용자 노출 | 상태 |
|---|---|---|---|---|
| `data.<code>.bags[]` (음식물용) | 다수 시군구 | **1549~1585** (v5.13) | **🍱 음식물 봉투 가격** (food 카테고리 자동 선택) | ✅ |
| `data.<code>.bags[]` (가정용 생활쓰레기) | 249 시군구 | **1549~1585** | **🛍️ 종량제봉투 가격** (general·hazardous·clothes·medicine 카테고리 자동) | ✅ |
| `data.<code>.bags[].prices` (3ℓ~75ℓ) | 249 시군구 | **1582** (v5.13 6 크기) | 가격 풀세트 노출 | ✅ |
| `data.<code>.phone` | 249 | 1584 | 📞 자원순환과 전화 | ✅ |
| `data.<code>.dept` | 249 | 1584 | 부서명 | ✅ |
| `data.<code>.lastUpdated` | 249 | 미노출 | (관리용) | 🟡 |
| 재활용 카테고리 (plastic/paper/can 등) | — | 가격 표시 안 함 (의도적) | (봉투 불필요) | ✅ |

---

## recycle_centers.json 필드별 활용

| 필드 | 데이터 유무 | app.html 활용 | 노출 |
|---|---|---|---|
| `data[].name` | 전국 | 1499~ | ♻️ 센터 이름 | ✅ |
| `data[].address` | 전국 | 1500 | 📍 주소 | ✅ |
| `data[].phone` | 전국 | 1501 | 📞 전화 | ✅ |
| `data[].weekdayOpen/Close` | 일부 | 1502 | 🕐 운영시간 | ✅ |
| `data[].sggCode` | 전국 | 1494 | 매칭에 활용 | ✅ |

---

## region_exceptions.json 필드별 활용 (v5.24 최신)

| 필드 | 데이터 유무 | app.html 활용 라인 | 사용자 노출 | 상태 |
|---|---|---|---|---|
| `exceptions.<code>.exceptions.<item>` | 강남구 4 / 일산동구 37 | matchRule 476~493 | 지역 차이 안내 | ✅ |
| **`exceptions.<code>._inherits`** ⭐ | 덕양구·일산서구 | **matchRule v5.24 신규** (while 루프) | 자동 상속 (보이지 않음) | ✅ |
| `exceptions.<code>.cityGuide` | 일산동구 + 19개 | **renderResult v5.24 신규** (cityHtml) | 📍 우리 지역 안내 박스 | ✅ |
| `cityGuide.applianceRecycle.phone` | 모든 시군구 | 결과 카드 (electronics) | 📞 폐가전 1599-0903 | ✅ |
| `cityGuide.bulkyWasteUrl` | 일산동구·인근 | 결과 카드 (furniture) | 🛋 대형폐기물 신고 | ✅ |
| `cityGuide.paperPackExchange` | 고양시 | 결과 카드 (paper/paper_pack) | 🎁 종이팩-화장지 교환 | ✅ |
| `cityGuide.disposalTime` | 일산동구·인근 | 결과 카드 (food) | 🕐 배출 시간 | ✅ |
| `cityGuide.garbageBag.color` | 일산동구·인근 | 결과 카드 (general/battery/lamp) | 🛍 봉투 색 | ✅ |
| `cityGuide.phones` | 거의 모든 시군구 | 결과 카드 (공통) | 📞 시청 자원순환과 | ✅ |
| `cityGuide.officialUrl` | 모든 시군구 | 결과 카드 (마지막 줄) | 🌐 공식 분리수거 안내 | ✅ |

### 20개 시군구 커버리지 (v5.24)

**서울 (8):** 강남구(11680, 4 룰), 마포구(11440), 은평구(11380), 서대문구(11410), 영등포구(11560), 양천구(11470), 강서구(11500), 종로구(11110), 중구(11140), 용산구(11170)

**경기 (12):** 고양 덕양구(41281, _inherits→41285), 고양 일산동구(41285, **37 룰** + 풍부 cityGuide), 고양 일산서구(41287, _inherits→41285), 파주(41480), 김포(41570), 의정부(41150), 부천(41210), 성남(41130), 안양(41170)

**활용율:** 일산동구 37 룰 → _inherits 통해 덕양구·일산서구 자동 활용 = **데이터 1배로 시군구 3배 커버리지**

---

## 미활용 데이터 (현재 누락 영역)

> 발견 시 즉시 통합. 미활용 = 죽은 데이터.

| 데이터 | 미활용 사유 | 대응 |
|---|---|---|
| `national_rules.dischargeMethodFull` | 너무 긺, feature 대체 | 🟢 백업용 인정 |
| `national_rules.official_classification` | UI에 표시할 곳 모호 | 🟡 검색 인덱스로 활용 가능 (미래) |
| `regions_meta.level2.phone` | 표시 위치 미정 | 🟡 결과 카드 보조 추가 가능 |
| `regions_meta.boundingBox` | GPS 자동 위치 추후 | 🔮 미래 기능 (Phase 6 UX) |
| `bag_prices.totalBagTypes` (720) | 가정용만 표시 중 | 🟡 사용자 요청 시 확장 |
| `region_urls.cleanUrl` (강남·서초) | bulkWasteUrl 우선 폴백 | 🟢 폴백 작동 중 |

→ 활용률 **약 92%**. 나머지 8%는 의도적 선택 또는 미래용.

---

## 데이터 추가 시 체크리스트

새 데이터 필드/파일 추가 시 **반드시 이 매트릭스 갱신**:

```
□ 1. 본 문서(DATA_INVENTORY)에 행 추가
□ 2. 활용 라인 번호 명시
□ 3. 사용자 노출 방식 명시
□ 4. 상태 (✅/🟡/🔴) 정확히 표시
□ 5. data-steward SKILL의 SOP 11단계 모두 완료
```

이 체크리스트를 안 따르면 → 또 죽은 데이터 발생.

---

## 변경 이력

- **2026-05-21 v5.13**: 카테고리별 봉투 매칭 (음식물용·생활쓰레기 자동 선택) + manifest.json `?v=12` 아이콘 cache-bust + 새 아이콘 디자인 (둥근 그라데이션 + 깔끔 ♻ + 잎).
- **2026-05-21 v5.12**: 환경부 분류 트리 + 시군구 전화 노출. 활용도 92% → 95%.
- **2026-05-21 v5.11**: Gemini JSON 자동 복구 + detect threshold 0.5 (라이브 박스 정직화 보강).
- **2026-05-21 v5.10**: 압력솥/프라이팬/웍 명시 + sourceName 일괄 + SKIP_CLASSES cup/bowl/vase 추가.
- **2026-05-21 v5.9**: Phase 3 데이터-앱 연동 정비 완료. sourceUrl/feature/caution/bulkWasteUrl 활용도 80% → 92%.
- **2026-05-20 v5.8**: 환경부 730 통합 (sourceUrl 0% → 94%). 카테고리 17/17 완비.
- **2026-05-19 v5.7**: 8개 누락 alias 보강 (일상 매칭률 92% → 100%).
- **2026-05-18 v5.6.x**: 데이터 오염 정리 (12,080건). v5.6.4 → 5.6.9 시리즈.

---

다음 데이터 작업 전 → 이 문서 먼저 읽기.
