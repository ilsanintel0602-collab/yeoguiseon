#!/usr/bin/env python3
"""
여기선 데이터 자산 벤치마크 — pass@1 객관 정량 측정
================================================================

NATIONAL.items 자산의 정확도·건전성을 정량 측정.
v5.x 정정 효과를 객관 수치로 추적.

사용: python scripts/benchmark_db.py
저장: docs/benchmarks/db_YYYY-MM-DD_HHMM.md

측정 항목:
1. 자산 건전성 (출처·alias·카테고리 표준)
2. alias 충돌 추세
3. searchByText 자기검색 정확도
4. Gemini 환각 회복률 (영문 ID → matchRule alias)
5. 종합 점수
"""
import json
import os

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
import sys
from collections import Counter, defaultdict
from datetime import datetime

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def norm(s):
    return (s or '').strip().lower().replace(' ', '')


def load_items():
    with open(os.path.join(ROOT, 'data', 'national_rules.json'), encoding='utf-8') as f:
        return json.load(f)['items']


def eval_assets(items):
    src_keys = ['source', 'source_url', 'sourceUrl', 'src']
    exact = sum(1 for it in items.values()
                if any('typeItem' in str(it.get(k) or '') or 'dictionaryView' in str(it.get(k) or '')
                       for k in src_keys))
    no_src = sum(1 for it in items.values()
                 if not any(it.get(k) for k in src_keys))
    total_aliases = sum(len(it.get('aliases', []) or []) for it in items.values())
    return {
        'total_items': len(items),
        'exact_source_pct': round(exact / max(len(items), 1) * 100, 1),
        'no_source_count': no_src,
        'avg_aliases': round(total_aliases / max(len(items), 1), 1),
        'total_aliases': total_aliases,
    }


def eval_conflicts(items):
    alias_map = defaultdict(set)
    for iid, it in items.items():
        for term in [it.get('name', '')] + (it.get('aliases', []) or []):
            k = norm(term)
            if k:
                alias_map[k].add(iid)
    conflicts = {al: list(ids) for al, ids in alias_map.items() if len(ids) > 1}
    truly_ambig = sum(1 for al, ids in conflicts.items()
                      if len(set(items[i].get('category') for i in ids)) > 1)
    return {
        'total_conflicts': len(conflicts),
        'truly_ambiguous': truly_ambig,
        'same_category': len(conflicts) - truly_ambig,
    }


def search_score(query, item_id, item):
    q = norm(query)
    idl = norm(item_id)
    name = norm(item.get('name', item_id))
    aliases = [norm(a) for a in (item.get('aliases', []) or [])]
    if idl == q: return 100
    if name == q: return 95
    if q in aliases: return 90
    if name.startswith(q): return 80
    if any(a.startswith(q) for a in aliases): return 70
    if q in name: return 50
    if any(q in a for a in aliases): return 40
    return 0


def eval_search_self(items):
    correct_by_name = 0
    correct_by_alias = 0
    total_alias_tests = 0
    items_list = list(items.items())
    for iid, it in items_list:
        name = it.get('name', iid)
        scores = [(search_score(name, k, v), k) for k, v in items_list]
        scores.sort(key=lambda x: -x[0])
        if scores and scores[0][1] == iid:
            correct_by_name += 1
        for a in (it.get('aliases', []) or [])[:3]:
            total_alias_tests += 1
            scores = [(search_score(a, k, v), k) for k, v in items_list]
            scores.sort(key=lambda x: -x[0])
            if scores and scores[0][1] == iid:
                correct_by_alias += 1
    return {
        'name_match_pct': round(correct_by_name / max(len(items), 1) * 100, 1),
        'alias_match_pct': round(correct_by_alias / max(total_alias_tests, 1) * 100, 1),
        'alias_tests': total_alias_tests,
    }


def eval_hallucination_recovery(items):
    test_cases = [
        ('spray_can', '에어로졸'),
        ('pressure_cooker', '압력솥'),
        ('coffee_maker', '커피'),
        ('hand_blender', '블렌더'),
        ('mug', '머그'),
        ('newspaper', '신문지'),
        ('milk_carton', '우유팩'),
        ('battery', '폐건전지'),
        ('aerosol_can', '에어로졸'),
        ('vinyl_bag', '비닐'),
    ]
    hits = 0
    matched_items = []
    for fake_id, expected_keyword in test_cases:
        n = norm(fake_id)
        found = None
        for k, v in items.items():
            if norm(k) == n:
                found = k; break
            if norm(v.get('name', '')) == n:
                found = k; break
            if n in [norm(a) for a in (v.get('aliases', []) or [])]:
                found = k; break
        if found and expected_keyword in items[found].get('name', ''):
            hits += 1
            matched_items.append((fake_id, found))
    return {
        'total_tests': len(test_cases),
        'recovery_hits': hits,
        'recovery_pct': round(hits / max(len(test_cases), 1) * 100, 1),
        'matched': matched_items,
    }


STANDARD_RECYCLE = ['paper', 'paper_pack', 'pet_clear', 'plastic', 'vinyl', 'styrofoam',
                    'glass', 'can', 'clothes', 'battery', 'lamp', 'electronics']
STANDARD_NON_RECYCLE = ['food', 'general', 'general_noncombustible', 'general_or_bulky',
                        'bulky', 'furniture', 'hazardous', 'medicine']


def eval_categories(items):
    cats = Counter(it.get('category', '?') for it in items.values())
    all_valid = set(STANDARD_RECYCLE) | set(STANDARD_NON_RECYCLE)
    invalid = {k: v for k, v in cats.items() if k not in all_valid}
    return {
        'total_categories': len(cats),
        'invalid_categories': dict(invalid),
        'recycle_count': sum(cats.get(c, 0) for c in STANDARD_RECYCLE),
        'non_recycle_count': sum(cats.get(c, 0) for c in STANDARD_NON_RECYCLE),
        'distribution': dict(cats),
    }


def main():
    items = load_items()
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"\n{'='*60}")
    print(f"여기선 DB 자산 벤치마크 — {ts}")
    print(f"{'='*60}\n")

    r1 = eval_assets(items)
    print(f"1. 자산 건전성")
    print(f"   item 총수: {r1['total_items']}")
    print(f"   정확 출처: {r1['exact_source_pct']}% (typeItem/dictionaryView)")
    print(f"   출처 없음: {r1['no_source_count']}건")
    print(f"   alias 총수: {r1['total_aliases']} (평균 {r1['avg_aliases']})\n")

    r2 = eval_conflicts(items)
    print(f"2. alias 충돌")
    print(f"   총 충돌: {r2['total_conflicts']}건")
    print(f"   진짜 모호 (재질 다름): {r2['truly_ambiguous']}건")
    print(f"   같은 카테고리: {r2['same_category']}건\n")

    r5 = eval_categories(items)
    print(f"3. 카테고리 (분리배출.kr 표준)")
    print(f"   재활용: {r5['recycle_count']}건")
    print(f"   비재활용: {r5['non_recycle_count']}건")
    print(f"   표준 외: {r5['invalid_categories'] or '없음'}\n")

    print(f"4. 검색 정확도 (searchByText 시뮬레이션) — 시간 소요...")
    r3 = eval_search_self(items)
    print(f"   name으로 자기 찾기: {r3['name_match_pct']}%")
    print(f"   alias로 자기 찾기 (상위 3개): {r3['alias_match_pct']}% ({r3['alias_tests']} 테스트)\n")

    r4 = eval_hallucination_recovery(items)
    print(f"5. Gemini 환각 회복 (영문 ID → matchRule alias)")
    print(f"   회복률: {r4['recovery_pct']}% ({r4['recovery_hits']}/{r4['total_tests']})")
    if r4['matched']:
        print(f"   매칭된 케이스: {r4['matched'][:5]}\n")

    score = round((
        r1['exact_source_pct'] * 0.2 +
        max(0, 100 - r2['total_conflicts']) * 0.2 +
        r3['name_match_pct'] * 0.25 +
        r3['alias_match_pct'] * 0.2 +
        r4['recovery_pct'] * 0.15
    ), 1)
    print(f"{'='*60}")
    print(f"  종합 점수: {score}/100")
    print(f"{'='*60}\n")

    out_dir = os.path.join(ROOT, 'docs', 'benchmarks')
    os.makedirs(out_dir, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d_%H%M')
    out_path = os.path.join(out_dir, f'db_{today}.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"# 여기선 DB 자산 벤치마크 — {ts}\n\n")
        f.write(f"## 종합 점수: **{score}/100**\n\n")
        f.write(f"## 1. 자산 건전성\n")
        f.write(f"- item 총수: **{r1['total_items']}**\n")
        f.write(f"- 정확 출처: **{r1['exact_source_pct']}%**\n")
        f.write(f"- 출처 없음: {r1['no_source_count']}건\n")
        f.write(f"- alias 총수: {r1['total_aliases']} (평균 {r1['avg_aliases']})\n\n")
        f.write(f"## 2. alias 충돌\n")
        f.write(f"- 총 **{r2['total_conflicts']}**건\n")
        f.write(f"- 진짜 모호: {r2['truly_ambiguous']}\n")
        f.write(f"- 같은 카테고리: {r2['same_category']}\n\n")
        f.write(f"## 3. 카테고리 (분리배출.kr 표준)\n")
        f.write(f"- 재활용: {r5['recycle_count']} / 비재활용: {r5['non_recycle_count']}\n")
        f.write(f"- 표준 외: {r5['invalid_categories'] or '없음'}\n\n")
        f.write(f"## 4. 검색 정확도\n")
        f.write(f"- name 자기검색: **{r3['name_match_pct']}%**\n")
        f.write(f"- alias 자기검색: **{r3['alias_match_pct']}%**\n\n")
        f.write(f"## 5. Gemini 환각 회복\n")
        f.write(f"- **{r4['recovery_pct']}%** ({r4['recovery_hits']}/{r4['total_tests']})\n")
        f.write(f"- 매칭 케이스: {r4['matched']}\n")
    print(f"저장: {out_path}\n")


if __name__ == '__main__':
    main()
