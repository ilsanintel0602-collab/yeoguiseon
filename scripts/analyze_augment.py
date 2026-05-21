#!/usr/bin/env python3
"""
Augment 결과 분석 — 백업 vs 현재 데이터 비교
========================================

augment_full.bat 끝난 후 더블클릭. 자동으로:
- 카테고리별 alias 증가량
- 평균 alias 변화
- 빈 응답 받은 아이템 (Gemini 변덕)
- 큰 증가 받은 아이템 (성공 케이스)
"""
import json
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
NAT = os.path.join(ROOT, "data", "national_rules.json")
BAK = NAT + ".backup_pre_augment.json"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    if not os.path.exists(BAK):
        print(f"[ERR] 백업 없음: {BAK}")
        print("augment 실행이 아직 안 됐거나 백업 위치 다름.")
        return

    print("=== Augment 결과 분석 ===\n")

    cur = load(NAT)["items"]
    bak = load(BAK)["items"]

    # 전체 통계
    cur_total = sum(len(v.get("aliases", [])) for v in cur.values())
    bak_total = sum(len(v.get("aliases", [])) for v in bak.values())
    print(f"전체 alias: {bak_total} → {cur_total}  (+{cur_total - bak_total})")
    print(f"평균: {bak_total/len(bak):.1f} → {cur_total/len(cur):.1f}\n")

    # 카테고리별
    cat_bak = defaultdict(int)
    cat_cur = defaultdict(int)
    cat_items = defaultdict(int)
    for k, v in cur.items():
        c = v.get("category", "?")
        cat_cur[c] += len(v.get("aliases", []))
        cat_items[c] += 1
    for k, v in bak.items():
        c = v.get("category", "?")
        cat_bak[c] += len(v.get("aliases", []))

    print("카테고리별 변화:")
    print(f"{'카테고리':15s} {'items':>6s} {'백업':>6s} → {'현재':>6s}  {'증가':>6s}  {'평균↑':>6s}")
    print("-" * 60)
    for c in sorted(cat_cur.keys(), key=lambda x: -(cat_cur[x] - cat_bak[x])):
        items = cat_items[c]
        before = cat_bak[c]
        after = cat_cur[c]
        diff = after - before
        avg_before = before / items if items else 0
        avg_after = after / items if items else 0
        print(f"{c:15s} {items:6d} {before:6d} → {after:6d}  +{diff:5d}  {avg_before:.1f}→{avg_after:.1f}")
    print()

    # 빈 응답 받은 아이템 (변화 0)
    no_change = []
    big_wins = []
    for k, v in cur.items():
        c = v.get("category", "?")
        n = v.get("name", k)
        cur_count = len(v.get("aliases", []))
        bak_count = len(bak.get(k, {}).get("aliases", []))
        diff = cur_count - bak_count
        if diff == 0:
            no_change.append((n, c))
        elif diff >= 10:
            big_wins.append((n, c, diff))

    print(f"⚠️  변화 0건 아이템 (Gemini 빈 응답 또는 모두 차단): {len(no_change)}건")
    for n, c in no_change[:15]:
        print(f"  - {n} ({c})")
    if len(no_change) > 15:
        print(f"  ... 외 {len(no_change) - 15}건")
    print()

    print(f"🎯 큰 증가 (+10 이상) 아이템: {len(big_wins)}건")
    for n, c, d in sorted(big_wins, key=lambda x: -x[2])[:15]:
        print(f"  +{d:3d} {n} ({c})")
    print()

    # 추천 다음 조치
    print("=== 다음 조치 ===")
    if no_change:
        print(f"1. 변화 0건 {len(no_change)}건 재시도 가능 (augment_aliases.py --limit N)")
    print(f"2. push 진행 → 모바일 PWA 자동 반영")
    print(f"3. (선택) 카톡 친구 피드백 받기 → 약점 카테고리 추가 보강")


if __name__ == "__main__":
    main()
