#!/usr/bin/env python3
"""
룰 기반 Alias 사전 증강 (Gemini 호출 0)
========================================

목적: Gemini augment 전에 안전한 패턴으로 alias 기본기 강화.
- 띄어쓰기 변형
- 외래어 음역 사전 (영↔한)
- 흔한 약자/줄임말
- 카테고리별 합성어 패턴

특징:
- Gemini API 호출 0 (비용 0, 즉시 적용)
- 매우 보수적 (오염 안전) — 명백한 패턴만
- 카테고리 충돌 검사

사용:
  python scripts/expand_aliases_rules.py --dry   # 미리보기
  python scripts/expand_aliases_rules.py          # 적용
  python scripts/expand_aliases_rules.py --limit 20  # 처음 20개만
"""
import json
import os
import re
import sys
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
NAT = os.path.join(ROOT, "data", "national_rules.json")

# 외래어 음역 사전 (보수적 — 명백한 매핑만)
# 한→영 또는 영→한 양방향
LOANWORD_MAP = {
    # 가전
    "노트북": ["laptop", "랩탑", "랩톱", "노트북pc", "노트북컴퓨터"],
    "컴퓨터": ["computer", "pc", "데스크탑", "desktop"],
    "데스크탑": ["desktop", "데스크톱", "pc", "본체"],
    "프린터": ["printer", "프린트", "프린트기"],
    "스캐너": ["scanner", "스캔기"],
    "모니터": ["monitor", "디스플레이", "display", "화면"],
    "키보드": ["keyboard", "자판"],
    "마우스": ["mouse"],
    "스피커": ["speaker", "스피커폰"],
    "이어폰": ["earphone", "earphones", "이어버드", "에어팟"],
    "헤드폰": ["headphone", "headphones", "헤드셋", "headset"],
    "충전기": ["charger", "어댑터", "adapter", "전원어댑터"],
    "케이블": ["cable", "선", "전선"],
    "리모컨": ["remote", "리모트", "리모트컨트롤"],
    "텔레비전": ["tv", "티비", "텔레비"],
    "냉장고": ["refrigerator", "fridge", "냉장"],
    "세탁기": ["washer", "washing machine", "세탁"],
    "건조기": ["dryer", "건조"],
    "에어컨": ["aircon", "ac", "에어컨디셔너", "냉방기"],
    "선풍기": ["fan", "팬"],
    "전자레인지": ["microwave", "마이크로웨이브", "전자렌지"],
    "오븐": ["oven"],
    "토스터": ["toaster", "토스트기", "토스터기"],
    "믹서": ["mixer", "블렌더", "blender", "믹서기"],
    "커피머신": ["coffee machine", "에스프레소머신", "espresso machine", "커피메이커"],
    "다리미": ["iron"],
    "청소기": ["vacuum", "진공청소기", "vacuum cleaner"],
    "공기청정기": ["air purifier", "purifier"],

    # 주방
    "냄비": ["pot", "팟"],
    "프라이팬": ["pan", "후라이팬", "후라이펜", "frypan"],
    "웍": ["wok"],
    "밥솥": ["rice cooker", "전기밥솥", "전기압력밥솥"],
    "압력솥": ["pressure cooker"],
    "주전자": ["kettle", "케틀"],
    "도마": ["cutting board"],
    "젓가락": ["chopsticks"],
    "숟가락": ["spoon", "스푼"],
    "포크": ["fork"],
    "나이프": ["knife", "칼"],

    # 가구
    "의자": ["chair"],
    "책상": ["desk"],
    "식탁": ["dining table"],
    "테이블": ["table"],
    "소파": ["sofa", "couch", "쇼파"],
    "침대": ["bed"],
    "옷장": ["wardrobe", "closet", "장롱"],
    "서랍": ["drawer"],
    "선반": ["shelf"],
    "거울": ["mirror"],

    # 의류
    "옷": ["clothes", "의류"],
    "셔츠": ["shirt", "와이셔츠", "y셔츠"],
    "바지": ["pants", "팬츠"],
    "치마": ["skirt", "스커트"],
    "양말": ["socks", "삭스"],
    "신발": ["shoes", "구두", "운동화"],
    "가방": ["bag", "백", "백팩", "backpack"],
    "모자": ["hat", "cap", "캡"],

    # 전기/배터리
    "건전지": ["battery", "베터리"],
    "전구": ["bulb", "lightbulb", "라이트벌브", "백열등"],
    "형광등": ["fluorescent", "형광"],

    # 일반
    "박스": ["box", "상자", "종이박스"],
    "병": ["bottle"],
    "캔": ["can"],
    "통": ["container"],
    "봉투": ["bag", "비닐봉투"],
    "포장": ["packaging", "포장재"],

    # 플라스틱
    "페트병": ["pet bottle", "플라스틱병", "음료수병"],
    "플라스틱": ["plastic"],
}

# 흔한 한국어 변형 (보수적)
KOREAN_VARIATIONS = {
    "케이스": ["케이스", "케이스류", "케스"],  # 거의 변형 없음
    "기": ["기기", "기계"],  # ~기 → ~기기
}

# 띄어쓰기 패턴: 띄어쓰기 있으면 → 합친 형태 추가
def gen_spacing_variants(name):
    out = []
    if " " in name:
        out.append(name.replace(" ", ""))
    return out


# 끝 글자 변형: ~기 → ~ (예: "토스터기" → "토스터")
SUFFIX_TRIM = ["기", "함", "통", "박스"]
def gen_suffix_trim(name):
    out = []
    for sfx in SUFFIX_TRIM:
        if name.endswith(sfx) and len(name) > len(sfx) + 1:
            out.append(name[:-len(sfx)])
    return out


# 외래어 매칭: 정확 일치만 (오염 방지)
def gen_loanword_aliases(name):
    out = []
    name_lower = name.lower().strip()
    # 정확한 한국어 이름 매칭
    for k, vals in LOANWORD_MAP.items():
        if k == name.strip() or k == name_lower:
            out.extend(vals)
            return out
    # 영어 → 한국어 역방향
    for k, vals in LOANWORD_MAP.items():
        for v in vals:
            if v.lower() == name_lower:
                out.append(k)
                out.extend([x for x in vals if x.lower() != name_lower])
                return out
    return out


# 카테고리별 부분 매칭 (안전한 키워드만)
PARTIAL_MATCH_AUG = {
    "electronics": {
        "노트북": ["laptop", "랩탑", "노트북pc"],
        "프린터": ["printer"],
        "모니터": ["monitor", "디스플레이"],
        "키보드": ["keyboard"],
        "마우스": ["mouse"],
        "이어폰": ["earphone"],
        "헤드폰": ["headphone", "헤드셋"],
        "충전기": ["charger"],
        "스피커": ["speaker"],
    },
    "furniture": {
        "의자": ["chair"],
        "책상": ["desk"],
        "소파": ["sofa", "couch", "쇼파"],
        "침대": ["bed"],
        "테이블": ["table"],
    },
}

def gen_partial_match(name, category):
    out = []
    name_l = name.strip()
    rules = PARTIAL_MATCH_AUG.get(category, {})
    for kw, alts in rules.items():
        if kw in name_l and name_l != kw:
            # 예: "사무용의자" → 의자 매칭 → chair 추가
            out.extend(alts)
    return out


def validate(new_aliases, name, category, existing, all_known):
    """안전 검증 — 명백한 오염만 차단"""
    out = []
    # 다른 카테고리의 '강한' 키워드 차단
    BAD_CROSS = {
        "electronics": ["음식", "밥", "종이박스", "신문지", "옷장"],
        "furniture": ["음식", "건전지", "프린트", "노트북"],
        "plastic": ["종이", "유리병", "캔", "음식"],
        "paper": ["페트병", "캔", "유리", "플라스틱병"],
        "food": ["플라스틱", "유리", "캔", "전자"],
        "battery": ["옷", "책", "음식", "유리병", "노트북"],
    }
    bad = BAD_CROSS.get(category, [])
    seen = set()
    for a in new_aliases:
        if not isinstance(a, str): continue
        a = a.strip()
        if len(a) < 2 or len(a) > 30: continue
        if a in existing or a == name: continue
        if a in all_known: continue  # 다른 item이 이미 가짐
        if a in seen: continue
        if any(b in a for b in bad): continue
        seen.add(a)
        out.append(a)
    return out


def main():
    args = sys.argv[1:]
    dry_run = "--dry" in args
    limit = None
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    # 백업
    BAK = NAT + ".backup_pre_rules_expand.json"
    if not dry_run and not os.path.exists(BAK):
        shutil.copy(NAT, BAK)
        print(f"백업 생성: {BAK}")

    with open(NAT, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]

    # 전체 알려진 단어
    all_known = set()
    for k, v in items.items():
        all_known.add(k.lower())
        n = v.get("name")
        if n: all_known.add(n.strip().lower())
        for a in (v.get("aliases") or []):
            all_known.add(a.strip().lower())

    print(f"\n전체 known: {len(all_known)} terms")
    print(f"items: {len(items)}")
    print(f"DRY={dry_run}, limit={limit}\n")

    target = list(items.items())
    if limit: target = target[:limit]

    total_added = 0
    cat_counts = {}
    for i, (key, item) in enumerate(target, 1):
        name = item.get("name", key).strip()
        category = item.get("category", "general")
        existing = item.get("aliases") or []

        # 다양한 룰 적용
        new_set = set()
        new_set.update(gen_spacing_variants(name))
        new_set.update(gen_suffix_trim(name))
        new_set.update(gen_loanword_aliases(name))
        new_set.update(gen_partial_match(name, category))

        # 검증
        valid = validate(list(new_set), name, category, existing, all_known)
        if not valid: continue

        # 적용
        if not dry_run:
            new_aliases = sorted(set(existing + valid))
            item["aliases"] = new_aliases
            for v in valid:
                all_known.add(v.lower())

        total_added += len(valid)
        cat_counts[category] = cat_counts.get(category, 0) + len(valid)
        if i <= 30 or i % 50 == 0:
            print(f"[{i:3d}] {name:20s} ({category:12s}) +{len(valid)}: {valid[:5]}{'...' if len(valid) > 5 else ''}")

    # 저장
    if not dry_run:
        with open(NAT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 저장 완료. 추가 alias: {total_added}")
    else:
        print(f"\n[dry-run] 추가될 alias: {total_added} (저장 안 함)")

    print(f"\n카테고리별 추가:")
    for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {c:15s}: +{n}")


if __name__ == "__main__":
    main()
