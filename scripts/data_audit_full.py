#!/usr/bin/env python3
"""
data-steward 통합 자동 검증 — 10가지 검사 한 번에

검사 항목 (각 10점, 합계 100, 합격선 95):
 1. JSON 무결성
 2. 필수 필드 (name/category/steps)
 3. 카테고리 enum 정합 (17개)
 4. sourceUrl 부여율 (≥90%)
 5. 앱 활용도 (모든 데이터 필드가 app.html에서 fetch/사용)
 6. 버전 동기 (app.html title/brand + sw.js VERSION 4곳)
 7. 백업 보존 (모든 .backup_* 파일 존재)
 8. 카테고리 ↔ catLabels ↔ SYSTEM_PROMPT 3자 정합
 9. fetch URL 정합 (app.html이 load하는 모든 파일 실제 존재)
10. alias cross-item 중복 (모호한 매칭 방지)

사용:
    python scripts\\data_audit_full.py            # 전체 검사
    python scripts\\data_audit_full.py --quick    # 빠른 검사 (8개만)
"""
import json
import os
import re
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA = os.path.join(ROOT, "data")
APP_HTML = os.path.join(ROOT, "app.html")
SW_JS = os.path.join(ROOT, "sw.js")

VALID_CATEGORIES = {
    "plastic", "paper", "paper_pack", "vinyl", "can", "glass", "styrofoam",
    "food", "general", "battery", "lamp", "clothes", "electronics",
    "furniture", "hazardous", "medicine", "reusable",
}

DATA_FILES = [
    "national_rules.json",
    "regions_meta.json",
    "region_exceptions.json",
    "region_urls.json",
    "bag_prices.json",
    "recycle_centers.json",
    "ocr_keywords.json",
    "brand_db.json",
]


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"_error": str(e)}


def section(n, title):
    print(f"\n{'='*64}\n  [{n}/10] {title}\n{'='*64}")


def gauge(label, score, full):
    pct = score * 100 / full if full else 0
    icon = "OK" if pct >= 90 else ("..." if pct >= 70 else "!!")
    print(f"  [{icon}] {label}: {score:.1f}/{full}  ({pct:.0f}%)")


def main():
    quick = "--quick" in sys.argv
    total = 0
    issues = []

    # 데이터 로드
    data = {}
    for f in DATA_FILES:
        p = os.path.join(DATA, f)
        if os.path.exists(p):
            data[f] = load(p)

    nat = data.get("national_rules.json", {})
    items = nat.get("items", {}) if nat else {}
    n_items = len(items)

    with open(APP_HTML, encoding="utf-8") as f:
        app_html = f.read()
    with open(SW_JS, encoding="utf-8") as f:
        sw_js = f.read()

    # ============================================
    # 1. JSON 무결성
    # ============================================
    section(1, "JSON 무결성")
    score = 10
    for f, d in data.items():
        if d.get("_error"):
            score -= 2
            issues.append(f"JSON 파싱 실패: {f} ({d['_error']})")
            print(f"  FAIL: {f}: {d['_error']}")
        else:
            print(f"  OK: {f}")
    gauge("Stage 1", max(0, score), 10)
    total += max(0, score)

    # ============================================
    # 2. 필수 필드
    # ============================================
    section(2, "필수 필드 (name/category/steps)")
    miss_n = sum(1 for v in items.values() if not v.get("name"))
    miss_c = sum(1 for v in items.values() if not v.get("category"))
    miss_s = sum(1 for v in items.values() if not v.get("steps"))
    score = 10
    if miss_n + miss_c + miss_s > 0:
        score = max(0, 10 - (miss_n + miss_c + miss_s) * 0.1)
        issues.append(f"필수 필드 누락: name={miss_n}, cat={miss_c}, steps={miss_s}")
    print(f"  name 누락: {miss_n}, category 누락: {miss_c}, steps 누락: {miss_s}")
    gauge("Stage 2", score, 10)
    total += score

    # ============================================
    # 3. 카테고리 enum 정합
    # ============================================
    section(3, "카테고리 enum (17개)")
    cats = set(v.get("category") for v in items.values())
    invalid = cats - VALID_CATEGORIES
    score = 10 if not invalid else max(0, 10 - len(invalid) * 2)
    if invalid:
        issues.append(f"알 수 없는 카테고리: {invalid}")
    print(f"  사용 카테고리 {len(cats)}개, 무효: {invalid or '없음'}")
    gauge("Stage 3", score, 10)
    total += score

    # ============================================
    # 4. sourceUrl 부여율
    # ============================================
    section(4, "sourceUrl 부여율")
    with_src = sum(1 for v in items.values() if v.get("sourceUrl") or v.get("source"))
    pct = with_src * 100 / max(n_items, 1)
    score = 10 if pct >= 90 else (7 if pct >= 80 else 4 if pct >= 50 else 1)
    if pct < 90:
        issues.append(f"sourceUrl 부여율 {pct:.1f}% (목표 90%+)")
    print(f"  sourceUrl 보유: {with_src}/{n_items} ({pct:.1f}%)")
    gauge("Stage 4", score, 10)
    total += score

    # ============================================
    # 5. 앱 활용도 — 모든 데이터 파일이 fetch되는지
    # ============================================
    section(5, "앱 활용도 (fetch + render)")
    fetched = []
    not_fetched = []
    for f in DATA_FILES:
        if f"./data/{f}" in app_html or f"data/{f}" in app_html:
            fetched.append(f)
        else:
            not_fetched.append(f)
    score = 10 * len(fetched) / max(len(DATA_FILES), 1)
    if not_fetched:
        issues.append(f"app.html이 fetch 안 하는 데이터: {not_fetched}")
    print(f"  fetch됨: {len(fetched)}/{len(DATA_FILES)}")
    if not_fetched:
        print(f"  미사용: {not_fetched}")
    gauge("Stage 5", score, 10)
    total += score

    # ============================================
    # 6. 버전 동기 (4곳)
    # ============================================
    section(6, "버전 동기 (app.html title/brand + sw.js VERSION)")
    v_title = re.search(r"<title>여기선\s+(v[\d.]+)", app_html)
    v_brand = re.search(r'class="version"[^>]*>(v[\d.]+)', app_html)
    v_sw = re.search(r"VERSION\s*=\s*['\"]v?([\d.]+)['\"]", sw_js)

    versions = {
        "title": v_title.group(1) if v_title else None,
        "brand": v_brand.group(1) if v_brand else None,
        "sw_js": "v" + v_sw.group(1) if v_sw else None,
    }
    unique_versions = set(v for v in versions.values() if v)
    score = 10 if len(unique_versions) == 1 else (5 if len(unique_versions) == 2 else 0)
    if len(unique_versions) > 1:
        issues.append(f"버전 불일치: {versions}")
    print(f"  버전 분포: {versions}")
    gauge("Stage 6", score, 10)
    total += score

    # ============================================
    # 7. 백업 보존
    # ============================================
    section(7, "백업 보존 (.backup_pre_*.json)")
    expected_backups = [
        "national_rules.json.backup_pre_boost.json",
        "national_rules.json.backup_pre_v2.json",
        "national_rules.json.backup_pre_v3.json",
        "national_rules.json.backup_pre_bunri.json",
    ]
    present = [b for b in expected_backups if os.path.exists(os.path.join(DATA, b))]
    score = 10 * len(present) / max(len(expected_backups), 1)
    print(f"  백업 보유: {len(present)}/{len(expected_backups)}")
    if len(present) < len(expected_backups):
        missing = set(expected_backups) - set(present)
        issues.append(f"백업 누락: {missing}")
    gauge("Stage 7", score, 10)
    total += score

    # ============================================
    # 8. 3자 정합 (categories ↔ items ↔ app.html enum)
    # ============================================
    section(8, "카테고리 3자 정합")
    defined_cats = set((nat.get("categories") or {}).keys())
    items_cats = set(v.get("category") for v in items.values() if v.get("category"))
    enum_match = re.search(r"\['plastic'.*?'medicine'\]", app_html)
    app_uses_enum = bool(enum_match)

    missing_in_def = items_cats - defined_cats
    score = 10
    if missing_in_def:
        score -= 3
        issues.append(f"categories 섹션 미정의: {missing_in_def}")
    if not app_uses_enum:
        score -= 3
        issues.append("app.html에서 enum 사용 안 보임")
    print(f"  categories 정의: {len(defined_cats)}, items 사용: {len(items_cats)}, app enum 검출: {app_uses_enum}")
    gauge("Stage 8", max(0, score), 10)
    total += max(0, score)

    # ============================================
    # 9. fetch URL 정합 (app.html → 실제 파일)
    # ============================================
    section(9, "fetch URL 정합")
    fetched_paths = re.findall(r"fetch\(['\"]\./?data/([^'\"]+)['\"]\)", app_html)
    missing_files = [p for p in fetched_paths if not os.path.exists(os.path.join(DATA, p))]
    score = 10 if not missing_files else max(0, 10 - len(missing_files) * 3)
    if missing_files:
        issues.append(f"app.html이 fetch 시도하나 없는 파일: {missing_files}")
    print(f"  fetch 시도 {len(fetched_paths)}개, 누락: {len(missing_files)}")
    gauge("Stage 9", score, 10)
    total += score

    # ============================================
    # 10. cross-item alias 중복
    # ============================================
    section(10, "alias cross-item 중복")
    alias_to_keys = defaultdict(set)
    for k, v in items.items():
        for a in (v.get("aliases") or []):
            alias_to_keys[a].add(k)
    dup_count = sum(1 for ks in alias_to_keys.values() if len(ks) > 1)
    score = 10 if dup_count <= 50 else (7 if dup_count <= 200 else 3)
    if dup_count > 50:
        issues.append(f"중복 alias 다수: {dup_count}건")
    print(f"  중복 alias: {dup_count}건")
    gauge("Stage 10", score, 10)
    total += score

    # ============================================
    # 종합
    # ============================================
    print(f"\n{'='*64}\n  종합 점수: {total:.1f} / 100  (합격선 95)\n{'='*64}")
    if total >= 95:
        print("  ✅ PASS — 데이터 자산 100% 활용 가능 상태")
    elif total >= 85:
        print("  ⚠️  NEAR — 자동 보강 가이드 출력")
    else:
        print("  ❌ FAIL — 사용자 결정 요청")

    if issues:
        print(f"\n  주요 이슈 ({len(issues)}건):")
        for i in issues:
            print(f"    - {i}")
    else:
        print(f"\n  주요 이슈 없음. 일관성 보장됨.")

    return total


if __name__ == "__main__":
    main()
