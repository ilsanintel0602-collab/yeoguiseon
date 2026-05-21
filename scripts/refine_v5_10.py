#!/usr/bin/env python3
"""
v5.10 정비 — 모바일 검증에서 발견된 약점 시정
- 압력솥/프라이팬 명시 item 추가 (Gemini 일관성 보장)
- sourceName 누락 items에 일괄 부여 ("공식 출처" → "분리배출.kr (환경부)")
- 백업 자동 + data-steward SOP 준수

WORK_HISTORY 원칙: 새 boost_v5 만들지 않고 refine_v5_10으로 의미 있는 이름 사용.

사용: python scripts\\refine_v5_10.py
"""
import json
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "national_rules.json"))
BACKUP_PATH = DATA_PATH + ".backup_pre_v5_10.json"

BUNRI_SOURCE = "https://xn--oy2b29bd3a601b.kr/front/dischargeMethod/index.do"
BUNRI_NAME = "분리배출.kr (한국폐기물협회·환경부)"
BUNRI_GRADE = "A"

# v5.10 새 items — 모바일 약점 (압력솥 일관성·프라이팬)
NEW_ITEMS_V5_10 = {
    "pressure_cooker": {
        "name": "압력솥/압력밥솥",
        "category": "general",
        "note": "버리려는 경우 종량제봉투. 깨끗·작동 → 본인이 계속 사용.",
        "steps": [
            "사용 가능 상태 → 본인이 계속 사용 (재사용 권장)",
            "버릴 때만 → 종량제봉투에 담아 배출",
            "대형이면 → 대형폐기물 신고"
        ],
        "regionVariation": True,
        "confidence": "high",
        "aliases": [
            "압력솥", "압력밥솥", "압력 밥솥", "압력 솥",
            "프레셔쿠커", "프레셔 쿠커", "압력솥류"
        ],
        "sourceUrl": BUNRI_SOURCE,
        "sourceName": BUNRI_NAME,
        "sourceGrade": BUNRI_GRADE,
    },
    "frying_pan": {
        "name": "프라이팬/후라이팬",
        "category": "general",
        "note": "코팅 프라이팬은 코팅·금속·플라스틱 손잡이 복합재질로 재활용 불가. 종량제봉투 배출.",
        "steps": [
            "코팅 벗겨진·소형 → 종량제봉투",
            "큰 프라이팬 → 대형폐기물 신고",
            "스테인리스 단일 재질 → 캔/금속류 (재질 확실 시)"
        ],
        "regionVariation": True,
        "confidence": "high",
        "aliases": [
            "프라이팬", "후라이팬", "팬", "코팅 팬", "프라이 팬",
            "후라이 팬", "테플론팬", "스테인리스 팬", "철판"
        ],
        "sourceUrl": BUNRI_SOURCE,
        "sourceName": BUNRI_NAME,
        "sourceGrade": BUNRI_GRADE,
    },
    "wok": {
        "name": "웍/중식 팬",
        "category": "general",
        "note": "중식 웍·궁중팬. 종량제봉투 또는 대형폐기물 신고.",
        "steps": [
            "소형 → 종량제봉투",
            "대형 → 대형폐기물 신고"
        ],
        "regionVariation": True,
        "confidence": "high",
        "aliases": ["웍", "중식 팬", "궁중팬", "궁중 팬", "차이나 팬"],
        "sourceUrl": BUNRI_SOURCE,
        "sourceName": BUNRI_NAME,
        "sourceGrade": BUNRI_GRADE,
    },
}


def main():
    if not os.path.exists(DATA_PATH):
        print(f"FAIL: 파일 없음 {DATA_PATH}")
        return

    # 백업
    if not os.path.exists(BACKUP_PATH):
        shutil.copy(DATA_PATH, BACKUP_PATH)
        print(f"백업 생성: {os.path.basename(BACKUP_PATH)}")
    else:
        print(f"기존 백업 있음 (덮어쓰기 안 함)")

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    before = len(items)
    print(f"\n  before: {before} items")

    # === Step 1: 새 items 추가 ===
    print(f"\n  [Step 1] 새 items 추가 (압력솥/프라이팬/웍)")
    added = 0
    merged = 0
    for k, v in NEW_ITEMS_V5_10.items():
        if k in items:
            existing = set(items[k].get("aliases") or [])
            for a in v["aliases"]:
                existing.add(a)
            items[k]["aliases"] = sorted(existing)
            if not items[k].get("sourceUrl"):
                items[k]["sourceUrl"] = v["sourceUrl"]
            if not items[k].get("sourceName"):
                items[k]["sourceName"] = v["sourceName"]
            merged += 1
        else:
            items[k] = v
            added += 1
    print(f"    신규 {added}개, 머지 {merged}개")

    # === Step 2: sourceName 일괄 부여 ===
    # sourceUrl 있고 sourceName 없는 items에 "분리배출.kr (환경부)" 부여
    print(f"\n  [Step 2] sourceName 누락 items에 일괄 부여")
    name_added = 0
    for k, v in items.items():
        src = v.get("sourceUrl") or v.get("source")
        if src and (("bunribaechul" in src) or ("xn--oy2b29bd3a601b" in src)):
            if not v.get("sourceName"):
                v["sourceName"] = BUNRI_NAME
                name_added += 1
            if not v.get("sourceGrade"):
                v["sourceGrade"] = BUNRI_GRADE
    print(f"    sourceName 추가: {name_added}건")

    # === Step 3: 검증 ===
    after = len(items)
    src_count = sum(1 for v in items.values() if v.get("sourceUrl") or v.get("source"))
    src_name_count = sum(1 for v in items.values() if v.get("sourceName"))
    print(f"\n  after:  {after} items")
    print(f"    sourceUrl: {src_count} ({src_count*100/after:.1f}%)")
    print(f"    sourceName: {src_name_count} ({src_name_count*100/after:.1f}%)")

    # 매칭 검증
    print(f"\n  [Step 4] 새 alias 매칭 검증")
    targets = ["압력솥", "압력밥솥", "프라이팬", "후라이팬", "웍"]
    for t in targets:
        found = (
            t in items
            or any(v.get("name") == t for v in items.values())
            or any(t in (v.get("aliases") or []) for v in items.values())
        )
        mark = "OK " if found else "FAIL"
        print(f"    {mark}  '{t}'")

    # 저장
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  저장 완료: {os.path.basename(DATA_PATH)}")


if __name__ == "__main__":
    main()
