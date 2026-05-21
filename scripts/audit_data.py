#!/usr/bin/env python3
"""
여기선 v5.8 데이터 종합 점검
- national_rules.json 무결성
- 환경부 730 데이터 통합률 (sourceUrl 비율)
- alias 오염 잔존 여부
- 카테고리 enum 일관성
- 일상 100 품목 매칭률

사용: python scripts\\audit_data.py
"""
import json
import os
import sys
import re
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
NATIONAL = os.path.join(DATA_DIR, "national_rules.json")
BUNRI = os.path.join(DATA_DIR, "raw_bunribaechul_730.json")
REPORT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "audit_report.md"))

# app.html line 477과 일치 (정식 enum). reusable은 모바일 카드용 보조.
VALID_CATEGORIES = {
    "plastic", "paper", "paper_pack", "vinyl", "can", "glass", "styrofoam",
    "food", "general", "battery", "lamp", "clothes", "electronics",
    "furniture", "hazardous", "medicine", "reusable"
}

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def main():
    report_lines = ["# 여기선 v5.8 데이터 종합 점검\n"]

    # === 1. JSON 무결성 ===
    section("1. JSON 무결성")
    try:
        with open(NATIONAL, encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", {})
        n = len(items)
        print(f"OK  national_rules.json  load OK  ({n} items)")
        report_lines.append(f"## 1. JSON 무결성\n\n- national_rules.json: {n} items, JSON valid\n")
    except Exception as e:
        print(f"FAIL  national_rules.json load:  {e}")
        sys.exit(1)

    try:
        with open(BUNRI, encoding="utf-8") as f:
            bunri = json.load(f)
        bunri_items = bunri.get("items", [])
        n_bunri = len(bunri_items)
        print(f"OK  raw_bunribaechul_730.json  load OK  ({n_bunri} items)")
        report_lines.append(f"- raw_bunribaechul_730.json: {n_bunri} items, JSON valid\n")
    except Exception as e:
        print(f"FAIL  raw_bunribaechul load:  {e}")
        bunri_items = []

    # === 2. 필수 필드 ===
    section("2. 필수 필드 (name / category / steps)")
    missing_name = [k for k, v in items.items() if not v.get("name")]
    missing_cat = [k for k, v in items.items() if not v.get("category")]
    missing_steps = [k for k, v in items.items() if not v.get("steps")]
    print(f"  name missing:  {len(missing_name)}")
    print(f"  category missing:  {len(missing_cat)}")
    print(f"  steps missing:  {len(missing_steps)}")
    if missing_name[:3]: print(f"    eg name missing: {missing_name[:3]}")
    if missing_cat[:3]: print(f"    eg cat missing:  {missing_cat[:3]}")
    if missing_steps[:3]: print(f"    eg steps missing: {missing_steps[:3]}")
    report_lines.append(f"\n## 2. 필수 필드\n\n- name missing: {len(missing_name)}\n- category missing: {len(missing_cat)}\n- steps missing: {len(missing_steps)}\n")

    # === 3. 카테고리 enum ===
    section("3. 카테고리 enum 일관성")
    cat_counter = Counter(v.get("category", "?") for v in items.values())
    invalid_cats = {k: c for k, c in cat_counter.items() if k not in VALID_CATEGORIES}
    print("  분포:")
    for k, c in cat_counter.most_common():
        flag = "  " if k in VALID_CATEGORIES else "!!"
        print(f"   {flag} {k:18s} {c}")
    if invalid_cats:
        print(f"  ⚠  알 수 없는 카테고리: {invalid_cats}")
    else:
        print("  OK  모든 카테고리 valid")
    report_lines.append(f"\n## 3. 카테고리 enum\n\n")
    for k, c in cat_counter.most_common():
        report_lines.append(f"- `{k}`: {c}{' (UNKNOWN)' if k not in VALID_CATEGORIES else ''}\n")

    # === 4. 환경부 730 통합률 (sourceUrl 비율) ===
    section("4. 환경부 730 데이터 통합률")
    with_source = [k for k, v in items.items() if v.get("sourceUrl") or v.get("source_url")]
    pct = len(with_source) * 100 / n if n else 0
    print(f"  sourceUrl 있는 items:  {len(with_source)} / {n}  ({pct:.1f}%)")

    # 환경부 730 품목 이름이 national_rules에 직접 있는지
    bunri_names = set(it.get("name") for it in bunri_items if it.get("name"))
    item_names = set(v.get("name") for v in items.values() if v.get("name"))
    item_aliases = set()
    for v in items.values():
        for a in (v.get("aliases") or []):
            item_aliases.add(a)

    matched_direct = bunri_names & item_names
    matched_alias = (bunri_names - matched_direct) & item_aliases
    unmatched = bunri_names - matched_direct - matched_alias

    print(f"  환경부 품목 매칭:")
    print(f"    name 직접 매칭:  {len(matched_direct)} / {len(bunri_names)}")
    print(f"    alias 매칭:      {len(matched_alias)}")
    print(f"    누락:            {len(unmatched)}")
    if unmatched:
        sample_missing = list(unmatched)[:15]
        print(f"    예시 누락: {sample_missing}")

    report_lines.append(f"\n## 4. 환경부 730 통합률\n\n")
    report_lines.append(f"- sourceUrl 보유 items: {len(with_source)} / {n} ({pct:.1f}%)\n")
    report_lines.append(f"- 환경부 품목 name 직접 매칭: {len(matched_direct)} / {len(bunri_names)}\n")
    report_lines.append(f"- alias 매칭: {len(matched_alias)}\n")
    report_lines.append(f"- 누락: {len(unmatched)}\n")
    if unmatched:
        report_lines.append(f"- 예시 누락: {', '.join(sorted(unmatched)[:30])}\n")

    # === 5. Alias 오염 검사 ===
    section("5. Alias 오염 잔존 검사")
    # 예: book.aliases에 '유리컵' 같은 명백히 잘못된 항목
    suspect_pairs = {
        "book": ["유리컵", "페트병", "캔", "스티로폼"],
        "paper_book": ["유리컵", "페트병", "캔"],
        "pet_bottle": ["책", "노트북", "옷"],
        "glass_bottle": ["책", "노트북", "옷"],
        "can": ["책", "노트북", "옷"],
        "electronics": ["페트병", "유리병", "음식물"],
    }
    pollution = []
    for k, banned in suspect_pairs.items():
        v = items.get(k)
        if not v: continue
        aliases = v.get("aliases") or []
        for b in banned:
            if b in aliases:
                pollution.append((k, b))
    if pollution:
        print(f"  ⚠  오염 발견:  {pollution}")
    else:
        print("  OK  주요 카테고리 alias 오염 없음")
    report_lines.append(f"\n## 5. Alias 오염 검사\n\n- 오염 발견: {len(pollution)}건\n")
    if pollution:
        for k, b in pollution:
            report_lines.append(f"- `{k}` aliases에 `{b}`\n")

    # 전체 alias 통계
    total_aliases = sum(len(v.get("aliases") or []) for v in items.values())
    avg_aliases = total_aliases / n if n else 0
    print(f"  총 alias 수: {total_aliases}, 평균 {avg_aliases:.1f}개/item")
    report_lines.append(f"- 총 alias 수: {total_aliases} (평균 {avg_aliases:.1f}개/item)\n")

    # === 6. 일상 100 품목 매칭률 ===
    section("6. 일상 100 품목 매칭률 (실사용 시나리오)")
    common = [
        # 재활용 베이직
        "투명페트병", "페트병", "콜라병", "물병", "음료수병",
        "종이박스", "택배상자", "신문", "잡지", "책", "노트",
        "우유팩", "주스팩", "두유팩", "멸균팩",
        "비닐봉지", "과자봉지", "라면봉지", "포장재",
        "음료캔", "맥주캔", "참치캔", "통조림", "알루미늄캔",
        "유리병", "소주병", "맥주병", "음료수병",
        "스티로폼", "포장재 스티로폼", "에어캡",
        # 음식물
        "사과 껍질", "양파 껍질", "고기 양념",
        # 일반쓰레기
        "영수증", "휴지", "도자기", "깨진유리", "이쑤시개",
        # 위험물
        "건전지", "폐건전지", "리튬배터리", "형광등",
        # 의류
        "옷", "헌 옷", "패딩", "코트", "후드티", "맨투맨", "양말", "신발",
        # 가방
        "가방", "배낭", "백팩", "핸드백", "지갑",
        # 전자기기
        "노트북", "맥북", "충전기", "케이블", "이어폰", "보조배터리", "어댑터",
        # 컵·식기
        "텀블러", "머그컵", "유리컵", "종이컵",
        # 가구
        "의자", "소파", "식탁", "침대",
        # 주방기구
        "압력솥", "냄비", "프라이팬", "전기밥솥",
        # 운동기구
        "폼롤러", "요가매트", "덤벨", "운동기구",
        # 화장품
        "화장품", "선크림", "립밤", "마스카라", "샴푸통", "세제통",
        # 기타
        "꽃병", "거울",
    ]
    matched_q = []
    unmatched_q = []
    for q in common:
        if q in items:
            matched_q.append((q, "key"))
            continue
        hit = None
        for k, v in items.items():
            if v.get("name") == q:
                hit = ("name", k); break
            if q in (v.get("aliases") or []):
                hit = ("alias", k); break
        if hit:
            matched_q.append((q, hit[0]))
        else:
            unmatched_q.append(q)
    rate = len(matched_q) * 100 / len(common)
    print(f"  {len(matched_q)} / {len(common)} 매칭  ({rate:.1f}%)")
    if unmatched_q:
        print(f"  누락: {unmatched_q}")
    report_lines.append(f"\n## 6. 일상 {len(common)} 품목 매칭률\n\n")
    report_lines.append(f"- 매칭: {len(matched_q)} / {len(common)} ({rate:.1f}%)\n")
    if unmatched_q:
        report_lines.append(f"- 누락: {', '.join(unmatched_q)}\n")

    # === 7. 종합 평가 ===
    section("7. 종합 평가")
    score = 0
    issues = []

    # JSON valid (10점)
    score += 10

    # 필수 필드 완비 (20점)
    if not missing_name and not missing_cat and not missing_steps:
        score += 20
    else:
        score += 10
        issues.append(f"필수 필드 누락 {len(missing_name)+len(missing_cat)+len(missing_steps)}건")

    # 카테고리 enum (10점)
    if not invalid_cats:
        score += 10
    else:
        issues.append(f"알 수 없는 카테고리 {len(invalid_cats)}개")

    # 환경부 통합 (20점)
    if pct >= 90:
        score += 20
    elif pct >= 50:
        score += 12
        issues.append(f"환경부 sourceUrl 보유 {pct:.0f}% (목표 90%+)")
    else:
        score += 5
        issues.append(f"환경부 sourceUrl 보유 {pct:.0f}% (대량 통합 필요)")

    # alias 오염 (15점)
    if not pollution:
        score += 15
    else:
        issues.append(f"alias 오염 {len(pollution)}건")

    # 매칭률 (25점)
    if rate >= 99:
        score += 25
    elif rate >= 95:
        score += 22
    elif rate >= 90:
        score += 18
    else:
        score += 10
        issues.append(f"일상 매칭률 {rate:.0f}% (목표 95%+)")

    print(f"  종합 점수:  {score} / 100")
    if issues:
        print("  주요 이슈:")
        for i in issues:
            print(f"    - {i}")

    report_lines.append(f"\n## 7. 종합 평가\n\n**{score} / 100점**\n\n")
    if issues:
        report_lines.append("주요 이슈:\n")
        for i in issues:
            report_lines.append(f"- {i}\n")
    else:
        report_lines.append("주요 이슈 없음. 바로 사용 가능.\n")

    # 리포트 저장
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("".join(report_lines))
    print(f"\nreport saved: {REPORT}")


if __name__ == "__main__":
    main()
