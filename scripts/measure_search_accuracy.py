#!/usr/bin/env python3
"""
v5.85 검색 정확도 자기점검 + 약점 발견 시스템
본질 "빠르게·정확하게" 직접 측정.

검사 항목:
1. alias 매칭률 (sample 검색어 → 정확 매칭 vs unknown)
2. 다중 매칭 충돌 (한 검색어 → 여러 items)
3. 약점 검색어 발견 (매칭 실패 또는 모호)
4. 카테고리별 alias 분포 (특정 카테고리 alias 부족 발견)

사용: python scripts/measure_search_accuracy.py [--verbose]
출력: 자기점검 보고서 (마크다운)
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PATH = os.path.join(ROOT, "data", "national_rules.json")
# 참고: 폴더명 'benchmark/'는 영문 변수명 유지 (기존 호환). 사용자 노출 메시지는 '자기점검'으로 통일
REPORT_DIR = os.path.join(ROOT, "benchmark")

# 일상 검색어 sample (사용자가 실제로 칠 법한 단어들)
# 시연 발견 패턴 + 환경부 자주 검색 카테고리
SAMPLE_QUERIES = [
    # 페트·플라스틱
    "페트병", "생수병", "투명페트", "콜라병", "샴푸통", "플라스틱병",
    "락앤락", "보관용기", "버터통", "요거트통",
    # 종이류
    "신문지", "박스", "종이박스", "잡지", "전단지", "영수증",
    "코팅종이", "달력", "포스터",
    # 종이팩
    "우유팩", "두유팩", "주스팩", "멸균팩", "테트라팩",
    # 캔·금속
    "음료캔", "맥주캔", "통조림", "참치캔", "스프레이", "에어로졸",
    "압력솥", "냄비", "프라이팬",
    # 유리
    "유리병", "와인병", "소주병", "맥주병", "유리컵",
    # 비닐
    "비닐봉지", "과자봉지", "라면봉지", "택배비닐", "에어캡",
    # 스티로폼
    "스티로폼", "택배 스티로폼", "스티로폼 트레이", "포장 스티로폼",
    # 의류
    "헌옷", "옷", "신발", "운동화", "양말", "속옷", "교복",
    # 전구·건전지
    "건전지", "리튬배터리", "형광등", "LED 전구", "백열등", "충전기",
    # 전자
    "휴대폰", "노트북", "모니터", "TV", "에어컨", "냉장고", "이어폰",
    "키보드", "마우스", "리모컨", "케이블", "공유기", "선풍기", "청소기",
    # 위험
    "부탄가스", "페인트", "살충제", "방향제", "라이터",
    # 일반·기타
    "기저귀", "물티슈", "휴지", "도자기", "거울", "이쑤시개",
    # 의약품
    "약", "연고", "알약", "물약", "주사기",
    # 음식물
    "음식물", "수박껍질", "닭뼈", "조개껍질", "계란껍질",
    # 다재질
    "텀블러", "카페일회용컵", "필통", "연필꽂이", "사다리", "소화기", "매트리스",
    # 가구
    "의자", "책상", "장롱", "침대",
]


def normalize(s):
    return str(s).strip().lower().replace(" ", "")


def match_search(query, items):
    """검색어 → 매칭되는 items 찾기 (이름·alias)"""
    q_norm = normalize(query)
    matches = []
    for iid, it in items.items():
        if not isinstance(it, dict):
            continue
        # name 매칭
        name_norm = normalize(it.get("name", iid))
        if name_norm == q_norm or q_norm in name_norm:
            matches.append((iid, "name"))
            continue
        # alias 매칭
        for a in (it.get("aliases", []) or []):
            a_norm = normalize(a)
            if a_norm == q_norm or q_norm in a_norm:
                matches.append((iid, f"alias:{a}"))
                break
    return matches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print(f"=== v5.85 검색 정확도 자기점검 ===")
    print(f"sample 검색어: {len(SAMPLE_QUERIES)}개")
    print()

    with open(PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", {})
    print(f"items 로드: {len(items)}개")
    print()

    # === 측정 ===
    results = []
    for q in SAMPLE_QUERIES:
        matches = match_search(q, items)
        results.append({
            "query": q,
            "match_count": len(matches),
            "matches": matches,
        })

    # === 통계 ===
    n_total = len(results)
    n_zero = sum(1 for r in results if r["match_count"] == 0)
    n_one = sum(1 for r in results if r["match_count"] == 1)
    n_multi = sum(1 for r in results if r["match_count"] > 1)

    zero_match_pct = n_zero * 100 / n_total
    single_match_pct = n_one * 100 / n_total
    multi_match_pct = n_multi * 100 / n_total

    print(f"=== 결과 요약 ===")
    print(f"  0 매칭 (FAIL): {n_zero}/{n_total} ({zero_match_pct:.1f}%)")
    print(f"  1 매칭 (정확): {n_one}/{n_total} ({single_match_pct:.1f}%)")
    print(f"  2+ 매칭 (충돌): {n_multi}/{n_total} ({multi_match_pct:.1f}%)")
    print()

    # === 약점 검색어 (0 매칭) ===
    if n_zero > 0:
        print(f"=== ❌ 약점 검색어 ({n_zero}건, alias 보강 필요) ===")
        for r in results:
            if r["match_count"] == 0:
                print(f"  - '{r['query']}'")
        print()

    # === 충돌 검색어 (2+ 매칭) ===
    if n_multi > 0:
        print(f"=== ⚠️ 충돌 검색어 ({n_multi}건, 우선순위 정렬 필요) ===")
        for r in results:
            if r["match_count"] > 1:
                iids = [m[0] for m in r["matches"][:3]]
                print(f"  - '{r['query']}' → {iids}")
        print()

    # === 카테고리별 alias 분포 ===
    cat_aliases = defaultdict(int)
    cat_items = defaultdict(int)
    for it in items.values():
        if not isinstance(it, dict):
            continue
        cat = it.get("category", "unknown")
        cat_items[cat] += 1
        cat_aliases[cat] += len(it.get("aliases", []) or [])

    print(f"=== 카테고리별 alias 분포 ===")
    print(f"{'카테고리':24s} {'items':>6s} {'aliases':>8s} {'평균/item':>10s}")
    print("-" * 55)
    for cat in sorted(cat_items, key=lambda c: -cat_items[c]):
        n_items = cat_items[cat]
        n_aliases = cat_aliases[cat]
        avg = n_aliases / max(n_items, 1)
        print(f"  {cat:22s} {n_items:>6d} {n_aliases:>8d} {avg:>10.1f}")
    print()

    # === 보강 우선순위 ===
    print(f"=== 🎯 보강 우선순위 (Opus 추천) ===")
    if n_zero > 0:
        print(f"  1순위: 약점 검색어 {n_zero}건 alias 추가 (즉시 +{zero_match_pct:.1f}%p)")
    if n_multi > 0:
        print(f"  2순위: 충돌 검색어 {n_multi}건 alias 분리 (정확도 ↑)")
    weak_cats = [(c, cat_aliases[c]/max(cat_items[c], 1))
                 for c in cat_items if cat_items[c] >= 5]
    weak_cats.sort(key=lambda x: x[1])
    print(f"  3순위: alias 평균 낮은 카테고리:")
    for cat, avg in weak_cats[:3]:
        print(f"     - {cat}: 평균 {avg:.1f} alias/item")
    print()

    # === 마크다운 리포트 ===
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_path = os.path.join(REPORT_DIR, f"search_accuracy_{ts}.md")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 검색 정확도 자기점검 보고서 (v5.85)\n\n")
        f.write(f"- 일시: {datetime.now().isoformat()}\n")
        f.write(f"- sample 검색어: {n_total}개\n")
        f.write(f"- items: {len(items)}개\n\n")
        f.write(f"## 점수\n\n")
        f.write(f"- **정확 매칭 (1 단독): {single_match_pct:.1f}%**\n")
        f.write(f"- 약점 (0 매칭): {zero_match_pct:.1f}%\n")
        f.write(f"- 충돌 (2+ 매칭): {multi_match_pct:.1f}%\n\n")
        if n_zero > 0:
            f.write(f"## 약점 검색어 ({n_zero}건)\n\n")
            for r in results:
                if r["match_count"] == 0:
                    f.write(f"- `{r['query']}`\n")
            f.write("\n")
        if n_multi > 0:
            f.write(f"## 충돌 검색어 ({n_multi}건)\n\n")
            for r in results:
                if r["match_count"] > 1:
                    iids = ", ".join([f"`{m[0]}`" for m in r["matches"][:3]])
                    f.write(f"- `{r['query']}` → {iids}\n")
            f.write("\n")
        f.write(f"## 카테고리별 alias 분포\n\n")
        f.write(f"| 카테고리 | items | aliases | 평균/item |\n|---|---|---|---|\n")
        for cat in sorted(cat_items, key=lambda c: -cat_items[c]):
            n_items = cat_items[cat]
            n_aliases = cat_aliases[cat]
            avg = n_aliases / max(n_items, 1)
            f.write(f"| {cat} | {n_items} | {n_aliases} | {avg:.1f} |\n")

    print(f"보고서 저장: {report_path}")

    return 0 if zero_match_pct < 10 else 1


if __name__ == "__main__":
    sys.exit(main())
