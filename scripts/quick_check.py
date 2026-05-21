#!/usr/bin/env python3
"""
Quick pre-deploy check — 5초 안에 데이터 무결성 + 핵심 정합성 검사
push 전 더블클릭 권장
"""
import json, os, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

def check(name, ok, detail=""):
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}{(': ' + detail) if detail else ''}")
    return ok

print("\n=== Quick Pre-Deploy Check ===\n")
all_ok = True

# 1. national_rules.json
try:
    with open(os.path.join(ROOT, "data", "national_rules.json"), encoding="utf-8") as f:
        nat = json.load(f)
    items = nat.get("items", {})
    all_ok &= check("national_rules.json 로드", True, f"{len(items)} items")
    aliases = sum(len(v.get("aliases", [])) for v in items.values())
    all_ok &= check("alias 평균", aliases / max(len(items), 1) >= 2.5, f"평균 {aliases/max(len(items),1):.1f}")
    cats = set(v.get("category") for v in items.values())
    VALID = {"plastic", "paper", "paper_pack", "vinyl", "can", "glass", "styrofoam", "food", "general",
             "battery", "lamp", "clothes", "electronics", "furniture", "hazardous", "medicine", "reusable"}
    bad_cats = cats - VALID
    all_ok &= check("카테고리 enum", not bad_cats, f"이상 enum: {bad_cats}" if bad_cats else "17개 정합")
except Exception as e:
    all_ok &= check("national_rules.json", False, str(e))

# 2. region_exceptions.json + regions_meta 정합성 ⭐ v5.25 강화
try:
    with open(os.path.join(ROOT, "data", "region_exceptions.json"), encoding="utf-8") as f:
        ex = json.load(f)
    excs = ex.get("exceptions", {})
    real_regions = {k: v for k, v in excs.items() if k.isdigit() and len(k) == 5}
    all_ok &= check("region_exceptions.json 로드", True, f"{len(real_regions)} 시군구")
    has_city = sum(1 for v in real_regions.values() if v.get("cityGuide"))
    all_ok &= check("cityGuide 보유", has_city == len(real_regions), f"{has_city}/{len(real_regions)}")
    inherits = {k: v for k, v in real_regions.items() if v.get("_inherits")}
    bad_inh = [k for k, v in inherits.items() if v["_inherits"] not in real_regions]
    all_ok &= check("_inherits 체인", not bad_inh, f"끊긴 체인: {bad_inh}" if bad_inh else "OK")

    # ⭐ NEW: regions_meta와 코드/이름 정합성 검사
    with open(os.path.join(ROOT, "data", "regions_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    valid_codes = set(meta.get("level2", {}).keys())
    # ⭐ 통합 시 코드 화이트리스트 — 자치구가 있는 시는 시-level 코드로 통합 운영 (의도적)
    INTEGRATED_CITY_CODES = {
        "41130",  # 경기 성남시 (분당·수정·중원구 통합)
        "43110",  # 충북 청주시 (상당·서원·흥덕·청원구 통합)
        "44130",  # 충남 천안시 (동남·서북구 통합)
        "45110",  # 전북 전주시 (완산·덕진구 통합)
        "47110",  # 경북 포항시 (남·북구 통합)
        "48120",  # 경남 창원시 (의창·성산·마산합포·마산회원·진해구 통합)
    }
    invalid_codes = [k for k in real_regions
                     if k not in valid_codes and k not in INTEGRATED_CITY_CODES]
    all_ok &= check("코드 행안부 표준 일치", not invalid_codes,
                    f"비표준 코드: {invalid_codes[:5]}{'...' if len(invalid_codes) > 5 else ''}" if invalid_codes else f"{len(real_regions)} 모두 유효 (통합 시 {len(INTEGRATED_CITY_CODES)} 포함)")
    # 이름 매칭 (간단)
    mismatched = []
    for code, val in real_regions.items():
        if code in valid_codes:
            meta_name = meta["level2"][code].get("name", "")
            ex_name = val.get("name", "")
            # 이름 일부라도 일치하면 OK (예: "경기도 광명시" ↔ "경기도 광명시")
            if meta_name and ex_name:
                key_word = meta_name.split()[-1].replace("시", "").replace("구", "").replace("군", "")[:2]
                if key_word and key_word not in ex_name:
                    mismatched.append(f"{code}={ex_name[:15]}(실제={meta_name[:15]})")
    all_ok &= check("시군구 이름 매칭", not mismatched,
                    f"불일치 {len(mismatched)}건: {mismatched[:3]}{'...' if len(mismatched) > 3 else ''}" if mismatched else "정확")
except Exception as e:
    all_ok &= check("region_exceptions.json", False, str(e))

# 3. app.html
try:
    with open(os.path.join(ROOT, "app.html"), encoding="utf-8") as f:
        html = f.read()
    all_ok &= check("v5.28 버전", "v5.28" in html, "")
    all_ok &= check("_escGlobal 정의", "_escGlobal" in html, "검색 함수 안전")
    all_ok &= check("searchByText 정의", "function searchByText" in html, "")
    all_ok &= check("_inherits 처리", "_inherits" in html and "safetyCounter" in html, "")
    all_ok &= check("cityGuide UI", "cityHtml" in html, "")
except Exception as e:
    all_ok &= check("app.html", False, str(e))

# 4. sw.js
try:
    with open(os.path.join(ROOT, "sw.js"), encoding="utf-8") as f:
        sw = f.read()
    all_ok &= check("sw.js VERSION v5.28", "v5.28" in sw, "")
except Exception as e:
    all_ok &= check("sw.js", False, str(e))

print("\n" + ("=" * 40))
if all_ok:
    print("🎉 모든 검사 통과! push 안전.")
else:
    print("⚠️  실패 항목 있음. 위 ❌ 확인 후 수정.")
print("=" * 40 + "\n")
sys.exit(0 if all_ok else 1)
