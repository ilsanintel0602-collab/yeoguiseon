#!/usr/bin/env python3
"""
v5.84 광역도 7도 시군구 cityGuide 표준 필드 일괄 보강
- 대상: 강원(42)·충북(43)·충남(44)·전북(45)·전남(46)·경북(47)·경남(48) 시군구
- 추가 필드 (환경부 전국 공통, 결측 시군구에만 추가):
  · paperPackExchange (종이팩-화장지 교환)
  · bulkyWasteNote (대형폐기물 신고 가이드)
- 기존 데이터 보존 (이미 있으면 건드리지 않음)
- 회귀 위험 0 (환경부 표준만, 추측 X)

사용: python scripts/boost_provinces_v584.py [--dry-run]
"""
import json
import os
import sys
from datetime import date

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PATH = os.path.join(ROOT, "data", "region_exceptions.json")

# 환경부 전국 공통 표준 (이미 다른 시군구에서 검증됨 — 일산동구·춘천 등)
STANDARD_PAPER_PACK = {
    "name": "종이팩-화장지 교환 사업",
    "where": "동·읍·면 주민센터 (대부분 운영, 시·구청 자원순환과 문의)",
    "rule": "내용물 비우고 헹궈 말린 종이팩 1kg → 화장지 1롤 (재고 소진 시 수거만 가능)",
    "source": "환경부 자원순환정보시스템 — 종이팩 회수 사업 (전국 공통)",
    "sourceGrade": "B_standard"
}

STANDARD_BULKY_WASTE_NOTE = (
    "⚠ 시·구청 페이지 안에서 '대형폐기물' 탭 선택 → 신고 → 수수료 결제 → 스티커 → 지정 장소 배출. "
    "또는 폐가전은 1599-0903 무상수거"
)


def is_target_region(code):
    """광역도 시군구 (42·43·44·45·46·47·48 시작)"""
    return code.startswith(("42", "43", "44", "45", "46", "47", "48"))


def main():
    dry_run = "--dry-run" in sys.argv

    print(f"=== v5.84 광역도 7도 cityGuide 표준 필드 일괄 보강 ===")
    print(f"Mode: {'DRY-RUN (변경 안 함)' if dry_run else 'WRITE'}")
    print(f"Target: {PATH}")
    print()

    with open(PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    ex = data.get("exceptions", {})

    # 광역도 시군구 추출
    target_codes = sorted([c for c in ex if is_target_region(c)])
    print(f"광역도 7도 시군구: {len(target_codes)}개")

    # 광역도별 분포
    from collections import Counter
    sido_dist = Counter(c[:2] for c in target_codes)
    sido_names = {
        "42": "강원", "43": "충북", "44": "충남",
        "45": "전북", "46": "전남", "47": "경북", "48": "경남"
    }
    for sido_code in ["42", "43", "44", "45", "46", "47", "48"]:
        if sido_code in sido_dist:
            print(f"  {sido_names[sido_code]}: {sido_dist[sido_code]}개")
    print()

    # 보강 진행
    added_pp = []  # paperPackExchange 추가
    added_bw = []  # bulkyWasteNote 추가
    skipped_no_cg = []  # cityGuide 자체 없음 (_inherits 케이스)

    for code in target_codes:
        info = ex[code]
        if not isinstance(info, dict):
            continue
        cg = info.get("cityGuide")
        if not cg:
            skipped_no_cg.append(code)
            continue

        # paperPackExchange 결측 시 추가
        if not cg.get("paperPackExchange"):
            if not dry_run:
                cg["paperPackExchange"] = dict(STANDARD_PAPER_PACK)
            added_pp.append(f"{code} ({info.get('shortName', '')})")

        # bulkyWasteNote 결측 시 추가
        if not cg.get("bulkyWasteNote"):
            if not dry_run:
                cg["bulkyWasteNote"] = STANDARD_BULKY_WASTE_NOTE
            added_bw.append(f"{code} ({info.get('shortName', '')})")

    # 저장
    if not dry_run and (added_pp or added_bw):
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

    # 결과 보고
    print(f"=== 결과 ===")
    print(f"paperPackExchange 추가: {len(added_pp)}개 / 전체 {len(target_codes)}개")
    print(f"bulkyWasteNote 추가: {len(added_bw)}개 / 전체 {len(target_codes)}개")
    print(f"cityGuide 없음 (skip, _inherits 추정): {len(skipped_no_cg)}개")
    print()

    if added_pp:
        print(f"paperPackExchange 추가된 시군구 (처음 10개):")
        for s in added_pp[:10]:
            print(f"  + {s}")
        if len(added_pp) > 10:
            print(f"  ... 외 {len(added_pp) - 10}개")
    print()

    if added_bw:
        print(f"bulkyWasteNote 추가된 시군구 (처음 10개):")
        for s in added_bw[:10]:
            print(f"  + {s}")
        if len(added_bw) > 10:
            print(f"  ... 외 {len(added_bw) - 10}개")
    print()

    if dry_run:
        print("[DRY-RUN 완료] --dry-run 제거 후 다시 실행하면 실제 저장합니다.")
    else:
        print("[저장 완료] python scripts/quick_check.py 로 검증 후 push 권장.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
