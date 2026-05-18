#!/usr/bin/env python3
"""
크롤/다운로드된 원본 데이터를 우리 스키마로 정규화 + 통합:
1. raw_bunribaechul_730.json → national_rules.json (한글 키 + 영어 키 별칭)
2. raw_bag_prices_mois.json → bag_prices.json (시군구 매핑)
3. raw_recycling_centers.json → recycle_centers.json
"""
import os
import json
from collections import Counter, defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def save(name, data):
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 {name} ({os.path.getsize(path)/1024:.0f} KB)", flush=True)


# ==================== 카테고리 매핑 ====================
CATEGORY_MAP = {
    "종이": "paper", "종이팩": "paper", "종이박스": "paper",
    "신문지": "paper", "잡지류": "paper", "책자": "paper",
    "일반팩": "paper", "멸균팩": "paper",
    "비닐": "vinyl", "합성수지 비닐류": "vinyl", "비닐류": "vinyl",
    "플라스틱": "plastic", "합성수지 용기류": "plastic",
    "페트": "plastic", "페트병": "plastic", "PET": "plastic",
    "무색페트병": "plastic", "유색페트병": "plastic", "투명페트병": "plastic",
    "PET, PP, PS, PE, OTHER": "plastic",
    "스티로폼": "styrofoam", "발포합성수지": "styrofoam",
    "발포합성수지(스티로폼 등)": "styrofoam",
    "발포합성수지(스티로폼류)": "styrofoam",
    "유리": "glass", "유리병": "glass", "유리잔": "glass",
    "빈용기보증금 대상 유리병": "glass",
    "캔": "can", "캔류": "can", "금속류": "can", "고철": "can",
    "기타캔류": "can", "금속캔": "can", "알루미늄": "can",
    "캔/금속": "can", "기타 캔류": "can",
    "의류 및 원단": "clothes", "의류": "clothes", "의류및원단": "clothes",
    "전기전자 제품류": "electronics", "소형 가전": "electronics",
    "대형 가전": "electronics", "전기전자제품류": "electronics",
    "음식물류폐기물": "food", "음식물": "food", "음식물쓰레기": "food",
    "일반폐기물": "general", "일반종량제폐기물": "general",
    "불연성종량제폐기물": "general", "공사장 생활폐기물": "general",
    "기타": "general",
    "대형폐기물": "furniture", "가구": "furniture",
    "생활계 유해폐기물": "hazardous",
    "폐페인트, 폐광택제, 폐접착제": "hazardous",
    "수은함유 폐기물": "hazardous",
    "천연방사성제품": "hazardous",
    "건전지": "battery", "전지": "battery", "전지류": "battery",
    "폐전지": "battery", "리튬전지": "battery", "리튬이온": "battery",
    "형광등": "lamp", "조명제품": "lamp", "폐형광등": "lamp", "LED": "lamp",
    "폐의약품": "medicine", "의약품": "medicine",
    "폐농약": "hazardous", "농약": "hazardous",
    "재활용폐기물": "recyclable",
}


def map_category(classification, name=""):
    for c in reversed(classification):
        c = c.strip()
        if c in CATEGORY_MAP:
            m = CATEGORY_MAP[c]
            if m != "recyclable":
                return m
    if any(x in name for x in ["건전지", "전지", "배터리"]):
        return "battery"
    if any(x in name for x in ["형광등", "LED"]):
        return "lamp"
    if any(x in name for x in ["의약품", "약통", "약병"]):
        return "medicine"
    if "페트" in name or "PET" in name:
        return "plastic"
    if "캔" in name:
        return "can"
    if "유리" in name:
        return "glass"
    if "종이" in name or "박스" in name:
        return "paper"
    if "비닐" in name or "봉지" in name:
        return "vinyl"
    if "스티로폼" in name:
        return "styrofoam"
    if any(x in name for x in ["페인트", "광택", "접착", "수은", "방사"]):
        return "hazardous"
    for c in classification:
        if c in CATEGORY_MAP:
            return CATEGORY_MAP[c]
    return "general"


# ==================== 통합시 매핑 ====================
INTEGRATED_CITIES = {
    "경기도 수원시": ["41111", "41113", "41115", "41117"],
    "경기도 성남시": ["41131", "41133", "41135"],
    "경기도 안양시": ["41171", "41173"],
    "경기도 안산시": ["41271", "41273"],
    "경기도 고양시": ["41281", "41285", "41287"],
    "경기도 용인시": ["41461", "41463", "41465"],
    "경상북도 포항시": ["47111", "47113"],
    "경상남도 창원시": ["48121", "48123", "48125", "48127", "48129"],
    "충청북도 청주시": ["43111", "43112", "43113", "43114"],
    "충청남도 천안시": ["44131", "44133"],
    "전라북도 전주시": ["45111", "45113"],
    "전북특별자치도 전주시": ["45111", "45113"],
}


def normalize_bunribaechul():
    raw = load("raw_bunribaechul_730.json")
    items_out = {}
    unmapped = Counter()
    dup = 0
    for it in raw["items"]:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        cls = it.get("classification", [])
        for c in cls:
            if c not in CATEGORY_MAP:
                unmapped[c] += 1
        cat = map_category(cls, name)
        key = name
        if key in items_out:
            if len(it.get("dischargeMethod", "") or "") <= len(items_out[key].get("dischargeMethodFull", "") or ""):
                dup += 1
                continue
            dup += 1
        items_out[key] = {
            "name": name, "category": cat, "classification": cls,
            "aliases": it.get("similar", []),
            "note": (it.get("feature", "") or "")[:200],
            "steps": [s.strip() for s in (it.get("dischargeMethod", "") or "").replace("· ", "|").split("|") if s.strip()],
            "caution": (it.get("caution", "") or "")[:200],
            "dischargeMethodFull": it.get("dischargeMethod", ""),
            "regionVariation": "지역" in (it.get("caution", "") or ""),
            "confidence": "high",
            "source": it.get("sourceUrl"),
            "sourceGrade": "A",
            "sourceName": "분리배출.kr (한국폐기물협회·환경부)",
            "lastVerified": raw["crawledAt"][:10],
            "_bunribaechulSeq": it.get("seq"),
        }
    print(f"📊 분리배출.kr: 입력 {raw['count']} → 출력 {len(items_out)} (중복 {dup}, 미매핑 {sum(unmapped.values())})", flush=True)
    return items_out


def normalize_bag_prices(regions):
    raw = load("raw_bag_prices_mois.json")
    name_to_sgg = {}
    for code, info in regions.get("level2", {}).items():
        name_to_sgg[info["name"]] = code
        name_to_sgg[info["shortName"]] = code
        parts = info["name"].split()
        if len(parts) >= 2:
            name_to_sgg[parts[-1]] = code

    by_sgg = defaultdict(lambda: {"name": None, "shortName": None, "sggCode": None, "phone": None, "dept": None, "lastUpdated": None, "bags": []})
    for r in raw["records"]:
        sido = (r.get("시도명") or "").strip()
        sgg = (r.get("시군구명") or "").strip()
        full = f"{sido} {sgg}"
        codes = INTEGRATED_CITIES.get(full) or [name_to_sgg.get(full) or name_to_sgg.get(sgg) or full]
        sizes = {}
        for sk in ["1ℓ가격", "1.5ℓ가격", "2ℓ가격", "2.5ℓ가격", "3ℓ가격", "5ℓ가격", "10ℓ가격", "20ℓ가격", "30ℓ가격", "50ℓ가격", "60ℓ가격", "75ℓ가격", "100ℓ가격", "120ℓ가격", "125ℓ가격"]:
            v = r.get(sk, "0")
            try:
                vv = int(v) if v else 0
            except Exception:
                vv = 0
            if vv > 0:
                sizes[sk.replace("가격", "")] = vv
        if not sizes:
            continue
        bag = {
            "종류": r.get("종량제봉투종류", ""),
            "처리방식": r.get("종량제봉투처리방식", ""),
            "용도": r.get("종량제봉투용도", ""),
            "사용대상": r.get("종량제봉투사용대상", ""),
            "prices": sizes,
        }
        for code in codes:
            e = by_sgg[code]
            e["name"] = full
            e["shortName"] = sgg
            e["sggCode"] = code if code in regions.get("level2", {}) else None
            e["phone"] = r.get("관리부서전화번호")
            e["dept"] = r.get("관리부서명")
            e["lastUpdated"] = r.get("데이터기준일자")
            e["bags"].append(bag)
    final = {k: v for k, v in by_sgg.items() if v["bags"]}
    print(f"📊 봉투 가격: {len(final)} 시군구", flush=True)
    return final


def normalize_centers(regions):
    raw = load("raw_recycling_centers.json")
    name_to_sgg = {}
    for code, info in regions.get("level2", {}).items():
        name_to_sgg[info["name"]] = code
        name_to_sgg[info["shortName"]] = code
        parts = info["name"].split()
        if len(parts) >= 2:
            name_to_sgg[parts[-1]] = code
    centers = []
    for r in raw:
        instt = (r.get("INSTT_NM") or "").strip()
        sgg_code = name_to_sgg.get(instt)
        if not sgg_code:
            parts = instt.split()
            if parts:
                sgg_code = name_to_sgg.get(parts[-1])
        centers.append({
            "name": r.get("CNTER_NM", "").strip(),
            "sggCode": sgg_code, "sggName": instt,
            "address": (r.get("RDNMADR") or "").strip(),
            "lat": r.get("LATITUDE"), "lng": r.get("LONGITUDE"),
            "operationType": r.get("CNTER_OPER_SE"),
            "treatmentItems": r.get("TRTMNT_PRDLST"),
            "phone": r.get("OPER_PHONE_NUMBER"),
            "weekdayOpen": r.get("WEEKDAY_OPER_OPEN_HHMM"),
            "weekdayClose": r.get("WEEKDAY_OPER_COLSE_HHMM"),
            "holidayOpen": r.get("HOLIDAY_OPER_OPEN_HHMM"),
            "holidayClose": r.get("HOLIDAY_CLOSE_OPEN_HHMM"),
            "closedDays": r.get("RSTDE_INFO"),
            "homepage": r.get("HOMEPAGE_URL"),
            "institutionName": r.get("INSTITUTION_NM"),
            "referenceDate": r.get("REFERENCE_DATE"),
        })
    print(f"📊 재활용센터: {len(centers)}개", flush=True)
    return centers


def main():
    regions = load("regions_meta.json")
    crawl_items = normalize_bunribaechul()
    bag_data = normalize_bag_prices(regions)
    centers = normalize_centers(regions)

    # national_rules 통합 (기존 영어 키 보존 + 새 한글 키 추가)
    nat = load("national_rules.json")
    for ko_key, new_item in crawl_items.items():
        if ko_key in nat["items"]:
            nat["items"][ko_key]["category"] = new_item["category"]
        else:
            nat["items"][ko_key] = new_item
    nat["version"] = "5.1.0"
    nat["count"] = len(nat["items"])
    from datetime import datetime, timezone
    nat["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save("national_rules.json", nat)

    save("bag_prices.json", {
        "$schema": "여기선 v5.1 - 시군구별 종량제봉투 가격",
        "version": "5.1.0", "lastUpdated": nat["lastUpdated"],
        "source": "행정안전부 #15025538", "sgguCount": len(bag_data), "data": bag_data,
    })
    save("recycle_centers.json", {
        "$schema": "여기선 v5 - 전국 재활용센터",
        "version": "5.0.0", "lastUpdated": nat["lastUpdated"],
        "source": "행정안전부 #15021108", "count": len(centers), "data": centers,
    })


if __name__ == "__main__":
    main()
