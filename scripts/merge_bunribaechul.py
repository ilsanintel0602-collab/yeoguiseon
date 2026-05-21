#!/usr/bin/env python3
"""
환경부 분리배출.kr 730 데이터 → national_rules.items 통합
- 기존 items의 name·alias를 환경부 name과 매칭
- 매칭 성공: sourceUrl, official_classification, feature, caution 부여
- 매칭 실패: 새 item으로 추가 (카테고리 자동 추정)
- similar → aliases 머지 (중복 제거)

사용:
    python scripts\\merge_bunribaechul.py            # 통합 + 저장
    python scripts\\merge_bunribaechul.py --dry      # 미리보기 (저장 X)
"""
import json
import os
import re
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
NATIONAL = os.path.join(DATA_DIR, "national_rules.json")
BUNRI = os.path.join(DATA_DIR, "raw_bunribaechul_730.json")
BACKUP = os.path.join(DATA_DIR, "national_rules.json.backup_pre_bunri.json")

DRY = "--dry" in sys.argv

# 환경부 classification[키워드] → 우리 category 매핑
CAT_MAP = [
    # (키워드, 우리 category)
    ("종이팩", "paper_pack"),
    ("우유팩", "paper_pack"),
    ("종이류", "paper"),
    ("종이", "paper"),
    ("신문", "paper"),
    ("책", "paper"),
    ("박스", "paper"),
    ("골판지", "paper"),
    ("유리", "glass"),
    ("병류", "glass"),
    ("캔", "can"),
    ("금속", "can"),
    ("철", "can"),
    ("알루미늄", "can"),
    ("스티로폼", "styrofoam"),
    ("발포", "styrofoam"),
    ("EPS", "styrofoam"),
    ("플라스틱", "plastic"),
    ("PET", "plastic"),
    ("페트", "plastic"),
    ("합성수지", "plastic"),
    ("비닐", "vinyl"),
    ("필름", "vinyl"),
    ("음식물", "food"),
    ("폐전지", "battery"),
    ("건전지", "battery"),
    ("배터리", "battery"),
    ("리튬", "battery"),
    ("폐형광등", "lamp"),
    ("형광등", "lamp"),
    ("의류", "clothes"),
    ("헌옷", "clothes"),
    ("신발", "clothes"),
    ("가방", "clothes"),
    ("가전제품", "electronics"),
    ("가전", "electronics"),
    ("소형가전", "electronics"),
    ("대형폐기물", "furniture"),
    ("가구", "furniture"),
    ("유해", "hazardous"),
    ("의약", "medicine"),
    ("폐의약", "medicine"),
    ("약", "medicine"),
    ("주사기", "hazardous"),
    ("페인트", "hazardous"),
]

def guess_category(classif):
    """환경부 classification 배열 → 우리 category 키 추정"""
    text = " ".join(classif) if isinstance(classif, list) else str(classif)
    for keyword, cat in CAT_MAP:
        if keyword in text:
            return cat
    # 마지막 폴백
    if "재활용" in text:
        return "general"  # 모호한 재활용은 일반으로
    return "general"


def slugify(name):
    """한글 이름 → key. 영문/숫자 변환 어려우니 짧은 한글 키 사용."""
    # 공백·괄호 제거, 30자 cap
    s = re.sub(r"[\s\(\)\[\]\/\\]+", "_", name.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:40] if s else "unknown"


def steps_from_discharge(text):
    """dischargeMethod 텍스트(· 구분) → steps 배열"""
    if not text: return []
    # · 또는 ·, 또는 ㆍ로 split
    parts = re.split(r"[·•ㆍ]\s*", text)
    parts = [p.strip().rstrip(".") for p in parts if p.strip()]
    return parts[:6]  # 최대 6단계


def build_index(items):
    """items의 name·alias → key 역인덱스"""
    idx = {}
    for k, v in items.items():
        name = (v.get("name") or "").strip()
        if name:
            idx.setdefault(name, []).append(k)
        for a in (v.get("aliases") or []):
            a = a.strip()
            if a:
                idx.setdefault(a, []).append(k)
    return idx


def main():
    print(f"파일 경로:")
    print(f"  national:  {NATIONAL}")
    print(f"  bunri:     {BUNRI}")
    print(f"  backup:    {BACKUP}")
    print()

    # 1. 로드
    with open(NATIONAL, encoding="utf-8") as f:
        data = json.load(f)
    with open(BUNRI, encoding="utf-8") as f:
        bunri = json.load(f)

    items = data["items"]
    bunri_items = bunri["items"]
    print(f"기존 items: {len(items)}")
    print(f"환경부 raw: {len(bunri_items)}")
    print()

    # 2. 백업
    if not DRY and not os.path.exists(BACKUP):
        with open(BACKUP, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"백업 생성: {os.path.basename(BACKUP)}")
    print()

    # 3. 인덱스
    idx = build_index(items)

    # 4. 통합
    matched = 0       # 기존 item에 sourceUrl 부여 성공
    added = 0         # 새 item으로 추가
    skipped = 0       # 중복 환경부 품목 (같은 name)
    seen_names = set()
    cat_counter = Counter()
    sample_matched = []
    sample_added = []

    for bi in bunri_items:
        name = (bi.get("name") or "").strip()
        if not name:
            continue
        if name in seen_names:
            # 환경부 raw에 같은 이름이 여러 개 → 첫 번째만 사용
            skipped += 1
            continue
        seen_names.add(name)

        source_url = bi.get("sourceUrl") or ""
        classif = bi.get("classification") or []
        similar = bi.get("similar") or []
        discharge = bi.get("dischargeMethod") or ""
        feature = bi.get("feature") or ""
        caution = bi.get("caution") or ""

        # 매칭 시도
        candidates = idx.get(name) or []
        if candidates:
            # 첫 번째 candidate에 부여
            k = candidates[0]
            it = items[k]
            # 이미 sourceUrl 있으면 덮어쓰지 않고 환경부 데이터 보강만
            if not it.get("sourceUrl"):
                it["sourceUrl"] = source_url
                matched += 1
                if len(sample_matched) < 5:
                    sample_matched.append((name, k))
            # similar → aliases 머지 (dedup)
            existing_aliases = set(it.get("aliases") or [])
            for s in similar:
                s = s.strip()
                if s and s != name and s not in existing_aliases:
                    existing_aliases.add(s)
            it["aliases"] = sorted(existing_aliases)
            # 부가 정보 (환경부 공식 문구)
            if not it.get("official_classification"):
                it["official_classification"] = classif
            if not it.get("feature"):
                it["feature"] = feature
            if not it.get("caution"):
                it["caution"] = caution
        else:
            # 새 item 추가
            key = slugify(name)
            # 키 중복 회피
            base_key = key
            n = 1
            while key in items:
                n += 1
                key = f"{base_key}_{n}"

            category = guess_category(classif)
            cat_counter[category] += 1
            steps = steps_from_discharge(discharge) or [
                f"{category} 카테고리 분리배출함에 배출"
            ]

            new_item = {
                "name": name,
                "category": category,
                "note": caution[:120] if caution else feature[:120] if feature else "",
                "steps": steps,
                "regionVariation": True,  # 안전한 기본값
                "confidence": "high",     # 환경부 공식
                "aliases": [s.strip() for s in similar if s.strip() and s.strip() != name],
                "sourceUrl": source_url,
                "official_classification": classif,
                "feature": feature,
                "caution": caution,
            }
            items[key] = new_item
            added += 1
            if len(sample_added) < 5:
                sample_added.append((name, key, category))

    # 5. 결과 요약
    n_after = len(items)
    src_count = sum(1 for v in items.values() if v.get("sourceUrl"))
    src_pct = src_count * 100 / n_after if n_after else 0

    print("=" * 60)
    print("  통합 결과")
    print("=" * 60)
    print(f"  기존 매칭(sourceUrl 부여):  {matched}")
    print(f"  신규 추가:                  {added}")
    print(f"  중복 환경부 품목 스킵:      {skipped}")
    print(f"  items 총 수:                {len(items)}  (+{len(items) - len(items) + added})")
    print()
    print(f"  신규 카테고리 분포:")
    for cat, cnt in cat_counter.most_common():
        print(f"    {cat:14s} {cnt}")
    print()
    print(f"  sourceUrl 보유율:  {src_count}/{n_after}  ({src_pct:.1f}%)")
    print()

    if sample_matched:
        print("  매칭 예시:")
        for name, k in sample_matched:
            print(f"    '{name}' → {k}")
    if sample_added:
        print("  신규 예시:")
        for name, k, cat in sample_added:
            print(f"    '{name}' → key={k}, cat={cat}")

    # 6. 저장
    if DRY:
        print("\n[dry-run] 저장 안 함")
    else:
        with open(NATIONAL, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n저장 완료: {os.path.basename(NATIONAL)}")
        print(f"되돌리려면: {os.path.basename(BACKUP)} → national_rules.json")


if __name__ == "__main__":
    main()
