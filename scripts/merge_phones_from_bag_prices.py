#!/usr/bin/env python3
"""
v6.07 작업: bag_prices.json의 phone+dept → region_exceptions.json cityGuide.phones 자동 병합

배경:
  - bag_prices.json: 249/261 시군구 phone + dept 정보 보유 (검증됨, 행안부 표준)
  - region_exceptions.json cityGuide.phones: 24/261 만 (수동 추가)
  - 동일 데이터가 두 곳에 분산 → 사용자가 "신고하기"에서 237곳 빈 결과

목표:
  - bag_prices의 phone+dept를 region_exceptions cityGuide.phones에 자동 병합
  - 기존 cityGuide.phones는 절대 덮어쓰기 X (수동 추가된 더 정확한 정보 우선)
  - 본질 룰 ⑥ 통과 확인: 대표번호·-0000 차단

사용: python scripts/merge_phones_from_bag_prices.py [--dry-run]
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BAG_PATH = os.path.join(ROOT, "data", "bag_prices.json")
EXC_PATH = os.path.join(ROOT, "data", "region_exceptions.json")

# 본질 룰 ⑥: 대표번호/안내데스크 차단 패턴
BLOCKED_PATTERNS = [
    re.compile(r"-0000$"),         # 대표번호 패턴
    re.compile(r"^120$|-120$"),    # 다산콜 등 안내
    re.compile(r"-1588-"),         # 전국 안내번호
    re.compile(r"-1577-"),
]


def is_valid_phone(phone):
    """전화번호 형식 검증 + 대표번호 차단"""
    if not phone or not isinstance(phone, str):
        return False
    # 한국 지역번호 형식: 02-XXX-XXXX, 0XX-XXX-XXXX
    if not re.match(r"^\d{2,3}-\d{3,4}-\d{4}$", phone):
        return False
    for pat in BLOCKED_PATTERNS:
        if pat.search(phone):
            return False
    return True


def is_meaningful_dept(dept):
    """부서명 검증 — 본질 룰 ⑥ 대표 라벨 차단"""
    if not dept or not isinstance(dept, str):
        return False
    blocked = ["대표", "안내", "민원", "교환", "당직"]
    return not any(b in dept for b in blocked)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="병합 결과만 보고, 파일 쓰기 X")
    args = ap.parse_args()

    print("=== bag_prices → region_exceptions phones 병합 ===")
    print()

    with open(BAG_PATH, "r", encoding="utf-8") as f:
        bag = json.load(f)
    with open(EXC_PATH, "r", encoding="utf-8") as f:
        exc = json.load(f)

    bag_data = bag.get("data", {})
    exceptions = exc.get("exceptions", {})

    # bag_prices 코드 → region_exceptions 코드 매칭 (둘 다 행안부 sgg 코드)
    added = []
    skipped_existing = []
    skipped_invalid = []
    no_match = []

    for code, info in bag_data.items():
        phone = info.get("phone")
        dept = info.get("dept")
        name = info.get("name", code)

        if not (phone and dept):
            continue

        # 검증
        if not is_valid_phone(phone):
            skipped_invalid.append(f"{name} — phone 형식 위반: {phone}")
            continue
        if not is_meaningful_dept(dept):
            skipped_invalid.append(f"{name} — dept 대표라벨: {dept}")
            continue

        # 도-시 표기 정리 (예: "경상남도 창원시 자원순환과" → "자원순환과")
        dept_clean = dept.split()[-1] if " " in dept else dept

        # exceptions에서 매칭 코드 찾기
        target = None
        for ex_code, region in exceptions.items():
            if not isinstance(region, dict):
                continue
            # code 직접 매칭 (시군구 코드)
            ex_sgg = region.get("sggCode") or region.get("sgg_code") or ex_code
            if str(ex_sgg) == str(code) or ex_code == code:
                target = (ex_code, region)
                break
            # name 매칭 폴백
            if region.get("name") == name:
                target = (ex_code, region)
                break

        if not target:
            no_match.append(f"{code} {name}")
            continue

        ex_code, region = target
        cg = region.setdefault("cityGuide", {})
        phones = cg.setdefault("phones", {})

        # 기존 phones에 같은 부서 있으면 skip (수동 추가 우선)
        if phones and (dept_clean in phones or any(dept_clean in k for k in phones.keys())):
            skipped_existing.append(f"{name} — {dept_clean} 이미 있음")
            continue

        # 기존 phones에 다른 부서가 있어도 추가 (자원순환과는 핵심)
        phones[dept_clean] = phone
        added.append(f"{name} — {dept_clean}: {phone}")

    print(f"[결과]")
    print(f"  ✅ 추가: {len(added)}건")
    print(f"  ⏭  기존 유지 (덮어쓰기 X): {len(skipped_existing)}건")
    print(f"  ❌ 형식·대표라벨 차단: {len(skipped_invalid)}건")
    print(f"  ⚠️  region_exceptions 매칭 실패: {len(no_match)}건")
    print()

    if added[:10]:
        print("[추가 예시 (처음 10건)]:")
        for a in added[:10]:
            print(f"  + {a}")
        print()

    if skipped_invalid[:5]:
        print("[차단 예시]:")
        for s in skipped_invalid[:5]:
            print(f"  ✗ {s}")
        print()

    if no_match[:5]:
        print("[매칭 실패 (region_exceptions에 코드 없음)]:")
        for n in no_match[:5]:
            print(f"  ? {n}")
        print()

    if args.dry_run:
        print("[DRY RUN] 파일 쓰기 안 함. --dry-run 빼고 다시 실행하면 적용됩니다.")
        return 0

    # 백업
    backup_path = EXC_PATH + ".bak.v607"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(exc, f, ensure_ascii=False, indent=2)
    print(f"[백업] {os.path.basename(backup_path)}")

    # 저장
    exc["lastUpdated"] = "2026-05-28"
    if "v6.07_merge_log" not in exc:
        exc["v6.07_merge_log"] = f"bag_prices → cityGuide.phones 자동 병합 {len(added)}건 (2026-05-28)"

    with open(EXC_PATH, "w", encoding="utf-8") as f:
        json.dump(exc, f, ensure_ascii=False, indent=2)

    # fsync
    with open(EXC_PATH, "rb+") as f:
        os.fsync(f.fileno())

    print(f"[저장] region_exceptions.json — {len(added)}건 phones 추가")
    return 0


if __name__ == "__main__":
    sys.exit(main())
