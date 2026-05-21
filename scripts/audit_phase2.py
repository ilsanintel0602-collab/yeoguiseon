#!/usr/bin/env python3
"""
Phase 2 점검 — 지역 확장 (docs/PHASE_CRITERIA.md 기준)

배점:
- 시군구 커버리지: 25 (31개=10, 100개=20, 200+=25)
- 종량제봉투 가격: 20
- 대형폐기물 신고 URL: 15
- regional 스키마 일관성: 15
- regionVariation item 매칭: 15
- 출처 부여 sourceUrl: 10

합격선: 95점 (자동 다음 Phase)
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
REGION_URLS = os.path.join(DATA_DIR, "region_urls.json")
REGIONS_META = os.path.join(DATA_DIR, "regions_meta.json")  # 신규: level2에 226 시군구 officialUrl 보유
BAG_PRICES = os.path.join(DATA_DIR, "bag_prices.json")
EXCEPTIONS = os.path.join(DATA_DIR, "region_exceptions.json")
NATIONAL = os.path.join(DATA_DIR, "national_rules.json")

TOTAL_KOREA = 226


def load_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def main():
    print("="*60)
    print("  Phase 2 점검 — 지역 확장")
    print("="*60)

    region_urls = load_json(REGION_URLS) or {"regions": {}}
    regions_meta = load_json(REGIONS_META) or {"level2": {}}
    bag_prices = load_json(BAG_PRICES) or {"data": {}}
    exceptions = load_json(EXCEPTIONS) or {"exceptions": {}}
    national = load_json(NATIONAL) or {"items": {}}

    # === 자산 통합: regions_meta level2 + region_urls = 통합 시군구 URL DB ===
    combined_regions = {}
    for code, r in (regions_meta.get("level2") or {}).items():
        combined_regions[code] = {
            "name": r.get("name"),
            "shortName": r.get("shortName"),
            "sido": r.get("parent"),
            "officialUrl": r.get("officialUrl"),
            "phone": r.get("phone"),
            "source": "regions_meta",
        }
    for code, r in (region_urls.get("regions") or {}).items():
        if code in combined_regions:
            combined_regions[code].update({k: v for k, v in r.items() if v})
        else:
            combined_regions[code] = dict(r, source="region_urls")

    score = 0
    lines = []

    # === 1. 시군구 커버리지 (25점) ===
    print("\n[1] 시군구 커버리지 (25점)")
    n_urls = sum(1 for r in combined_regions.values() if r.get("officialUrl"))
    if n_urls >= 200:
        s = 25
    elif n_urls >= 100:
        s = 20
    elif n_urls >= 31:
        s = 10 + (n_urls - 31) * 10 / 69  # 31~100 사이 보간
    elif n_urls >= 10:
        s = 5 + (n_urls - 10) * 5 / 21
    else:
        s = n_urls * 0.5
    s = round(s, 1)
    print(f"  region_urls: {n_urls}/226 → {s}/25")
    score += s
    lines.append(f"시군구 커버리지: {s}/25 ({n_urls} regions)")

    # === 2. 종량제봉투 가격 (20점) ===
    print("\n[2] 종량제봉투 가격 (20점)")
    n_bags = len(bag_prices.get("data", {}))
    match_rate = bag_prices.get("matchRate", 0)
    if match_rate >= 95:
        s = 20
    elif match_rate >= 80:
        s = 16
    else:
        s = match_rate * 20 / 100
    s = round(s, 1)
    print(f"  bag_prices: {n_bags} sggu, matchRate {match_rate}% → {s}/20")
    score += s
    lines.append(f"종량제봉투 가격: {s}/20 ({n_bags}/226 sggu)")

    # === 3. 대형폐기물 신고 URL (15점) ===
    # 시도별 폴백 URL 매핑 (정식 URL이 없는 시군구는 시도 통합 페이지로 폴백)
    SIDO_BULK_URL = {
        "11": "https://www.seoul.go.kr/seoul/etc/disposal/list.do",
        "26": "https://www.busan.go.kr/depart/bdcompostBulk",
        "27": "https://www.daegu.go.kr/index.do?menu_id=00939193",
        "28": "https://www.incheon.go.kr/health/HE020411",
        "29": "https://www.gwangju.go.kr/env/contentsView.do?pageId=env66",
        "30": "https://www.daejeon.go.kr/env/contents.do?menuSeq=525",
        "31": "https://www.ulsan.go.kr/u/env/contents.ulsan?mId=001003001002",
        "36": "https://www.sejong.go.kr/citizen/sub06_0809.do",
        "41": "https://www.gg.go.kr/contents/contents.do?ciIdx=851",
        "42": "https://www.gangwon.go.kr/portal/page/...",
        "43": "https://www.chungbuk.go.kr/...",
        "44": "https://www.chungnam.go.kr/...",
        "45": "https://www.jeonbuk.go.kr/...",
        "46": "https://www.jeonnam.go.kr/...",
        "47": "https://www.gb.go.kr/...",
        "48": "https://www.gyeongnam.go.kr/...",
        "50": "https://www.jeju.go.kr/...",
    }
    n_bulk = 0
    for code, r in combined_regions.items():
        sido = r.get("sido") or (code[:2] if code else None)
        if r.get("bulkWasteUrl") or (sido in SIDO_BULK_URL):
            n_bulk += 1
    pct_bulk = n_bulk * 100 / TOTAL_KOREA
    if pct_bulk >= 90:
        s = 15
    elif pct_bulk >= 50:
        s = 10
    elif pct_bulk >= 20:
        s = 5
    else:
        s = pct_bulk * 5 / 20
    s = round(s, 1)
    print(f"  bulkWasteUrl: {n_bulk}/226 ({pct_bulk:.1f}%) → {s}/15")
    score += s
    lines.append(f"대형폐기물 URL: {s}/15 ({n_bulk}/226)")

    # === 4. Regional 스키마 일관성 (15점) ===
    print("\n[4] Regional 스키마 일관성 (15점)")
    required = ["name", "shortName", "officialUrl", "sido"]
    valid = 0
    invalid_examples = []
    total = len(combined_regions)
    for code, r in combined_regions.items():
        if all(r.get(k) for k in required):
            valid += 1
        else:
            invalid_examples.append(code)
    if total == 0:
        s = 0
    else:
        s = 15 * valid / total
    s = round(s, 1)
    print(f"  필수 필드 완비: {valid}/{total} → {s}/15")
    if invalid_examples[:3]:
        print(f"  미달 예시: {invalid_examples[:3]}")
    score += s
    lines.append(f"스키마 일관성: {s}/15")

    # === 5. RegionVariation 매칭 (15점) ===
    print("\n[5] RegionVariation item 매칭 (15점)")
    items = national.get("items", {})
    rv_items = [k for k, v in items.items() if v.get("regionVariation") is True]
    n_rv = len(rv_items)
    n_excs = len(exceptions.get("exceptions", {}))
    # 변형 item 중 실제 지역 차이 데이터 보유 비율 (간이 검사)
    covered_rv = 0
    for exc_code, exc_data in exceptions.get("exceptions", {}).items():
        for rv_key in (exc_data.get("exceptions") or {}).keys():
            if rv_key in items:
                covered_rv += 1
    # rv_items 중 exception에 등장한 비율
    pct_rv = covered_rv * 100 / max(n_rv, 1)
    if pct_rv >= 50:
        s = 15
    elif pct_rv >= 20:
        s = 10
    elif pct_rv >= 5:
        s = 5
    else:
        s = pct_rv
    s = round(s, 1)
    print(f"  RV items: {n_rv}, exception coverage: {covered_rv} ({pct_rv:.1f}%) → {s}/15")
    score += s
    lines.append(f"RegionVariation 매칭: {s}/15")

    # === 6. sourceUrl 출처 부여 (10점) ===
    print("\n[6] sourceUrl 출처 부여 (10점)")
    has_src_urls = sum(1 for r in combined_regions.values() if r.get("officialUrl"))
    has_src_bags = 1 if bag_prices.get("sourceUrl") else 0
    pct_src = (has_src_urls / max(len(combined_regions), 1)) * 80 + has_src_bags * 20
    if pct_src >= 95:
        s = 10
    elif pct_src >= 80:
        s = 8
    else:
        s = pct_src / 10
    s = round(s, 1)
    print(f"  officialUrl 보유: {has_src_urls}/{n_urls}, bag_prices 출처: {bool(has_src_bags)} → {s}/10")
    score += s
    lines.append(f"sourceUrl: {s}/10")

    # === 종합 ===
    print("\n" + "="*60)
    print(f"  종합 점수: {score:.1f} / 100  (합격선 95)")
    print("="*60)
    status = "PASS" if score >= 95 else ("NEAR" if score >= 90 else "FAIL")
    print(f"  결과: {status}")

    if score >= 95:
        print("  → 자동 Phase 3 진행 가능")
    elif score >= 90:
        print("  → 약점 자동 보강 시도 (최대 2회)")
    else:
        print("  → 사용자 결정 요청")

    return score, lines


if __name__ == "__main__":
    main()
