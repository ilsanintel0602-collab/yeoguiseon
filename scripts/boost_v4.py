#!/usr/bin/env python3
"""
v5.8 5차 보강 — audit_v2 Stage 5·7 약점 자동 보강
- Stage 5: cross-item 중복 alias 분석 + 가장 적절한 item에만 유지
- Stage 7: 추가 일상 13개 누락 매칭 보강

규칙:
- 가장 우선 보유 권한 = 동음이의 없는 item (예: "음료캔" → aluminum_can)
- 중복 발견 시 가장 매칭 권위 있는 item만 유지, 나머지 제거
- 백업 자동 생성

사용: python scripts\\boost_v4.py
"""
import json
import os
import shutil
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "national_rules.json"))
BACKUP_PATH = DATA_PATH + ".backup_pre_v4.json"

BUNRI_SOURCE = "https://xn--oy2b29bd3a601b.kr/front/dischargeMethod/index.do"

# Stage 7 누락 보강 — 추가 13개 일상 품목
# 안전한 새 items로 추가 (또는 기존 item aliases에 머지)
EXTRA_ITEMS_V4 = {
    "led_bulb": {
        "name": "LED 전구",
        "category": "general",
        "note": "LED 전구는 형광등과 달리 수은이 없어 일반쓰레기. 깨지지 않게 종량제봉투에.",
        "steps": ["깨지지 않게 신문지로 감싸기", "종량제봉투에 배출", "(형광등은 별도 전용수거함)"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["LED 전구", "LED 램프", "엘이디 전구", "에너지절약 전구"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "face_mask": {
        "name": "마스크",
        "category": "general",
        "note": "보건용·KF 마스크 모두 일반쓰레기. 사용한 마스크는 종량제봉투에.",
        "steps": ["끈 잘라서 분리", "종량제봉투에 담아 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["마스크", "KF94", "KF80", "보건용 마스크", "덴탈 마스크", "황사 마스크"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "thermometer": {
        "name": "체온계",
        "category": "hazardous",
        "note": "수은 체온계는 유해폐기물 (전자식은 소형가전). 깨진 체온계는 동주민센터로.",
        "steps": ["수은 체온계 → 유해폐기물 또는 동주민센터", "전자 체온계 → 소형가전"],
        "regionVariation": True,
        "confidence": "high",
        "aliases": ["체온계", "수은 체온계", "전자 체온계", "디지털 체온계"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "diaper": {
        "name": "기저귀",
        "category": "general",
        "note": "유아·성인용 기저귀 모두 일반쓰레기 (배설물 등 오염물 포함).",
        "steps": ["오염물 비우기 (가능한 경우)", "둘둘 말아서 종량제봉투에"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["기저귀", "유아 기저귀", "성인 기저귀", "패드"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "gum": {
        "name": "껌",
        "category": "general",
        "note": "씹은 껌은 일반쓰레기. 음식물쓰레기 아님 (재활용 불가).",
        "steps": ["껌은 종량제봉투에", "포장지(은박)는 비닐류 또는 종이류"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["껌", "씹은 껌", "풍선껌"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "cigarette_butt": {
        "name": "담배꽁초",
        "category": "general",
        "note": "꺼져 있는지 확인 후 종량제봉투에. 화재 위험 주의.",
        "steps": ["완전히 꺼진 후 배출", "물에 적셔 안전 처리", "종량제봉투에"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["담배꽁초", "꽁초", "담뱃재", "재떨이 꽁초"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "takeout_cup": {
        "name": "테이크아웃 컵",
        "category": "general",
        "note": "PE코팅 종이컵·플라스틱 컵 모두 음료 묻으면 일반쓰레기. 깨끗하면 재질별 분리.",
        "steps": ["내용물 비우기", "오염 → 종량제봉투", "깨끗 종이컵 → 종이류 / 깨끗 플라스틱 → 플라스틱"],
        "regionVariation": True,
        "confidence": "high",
        "aliases": ["테이크아웃 컵", "커피컵", "PE컵", "음료컵", "스타벅스 컵"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "treadmill": {
        "name": "런닝머신",
        "category": "furniture",
        "note": "대형 운동기구는 대형폐기물 신고. 소형 (스텝퍼 등)은 종량제봉투.",
        "steps": ["거주 지자체 대형폐기물 신고", "수수료 납부 + 필증 부착", "지정 일자에 배출"],
        "regionVariation": True,
        "confidence": "high",
        "aliases": ["런닝머신", "트레드밀", "헬스기구", "사이클", "에어로빅 자전거"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "ceramic_vase": {
        "name": "도자기 꽃병",
        "category": "general",
        "note": "도자기는 재활용 불가 일반쓰레기. 깨지면 신문지에 감싸 종량제봉투.",
        "steps": ["깨지지 않게 신문지로 감싸기", "종량제봉투에 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["도자기 꽃병", "세라믹 꽃병", "옹기 꽃병"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "glass_vase": {
        "name": "유리 꽃병",
        "category": "glass",
        "note": "깨지지 않은 유리 꽃병은 유리병 수거함. 깨진 유리는 신문지에 싸서 종량제봉투.",
        "steps": ["깨끗이 헹구기", "유리병 수거함에 배출", "깨진 유리는 신문지로 감싸 종량제봉투"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["유리 꽃병", "글래스 꽃병", "크리스탈 꽃병"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "cotton_swab": {
        "name": "면봉",
        "category": "general",
        "note": "면봉은 일반쓰레기. 사용한 것은 종량제봉투에.",
        "steps": ["종량제봉투에 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["면봉", "이어픽", "귀이개"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "wet_tissue": {
        "name": "물티슈",
        "category": "general",
        "note": "물티슈는 화학섬유 함유로 재활용 불가. 일반쓰레기.",
        "steps": ["종량제봉투에 배출", "(절대 변기에 버리지 말 것 — 막힘 원인)"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["물티슈", "젖은 티슈", "물수건", "베이비 티슈"],
        "sourceUrl": BUNRI_SOURCE,
    },
    "tetra_pack": {
        "name": "테트라팩 (멸균팩)",
        "category": "paper_pack",
        "note": "두유·주스 멸균팩. 내용물 비우고 헹궈서 종이팩 수거함.",
        "steps": ["내용물 비우기", "물로 헹구기", "펼쳐서 말리기", "종이팩 전용 수거함에 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["테트라팩", "멸균팩", "두유팩(멸균)", "주스팩(멸균)"],
        "sourceUrl": BUNRI_SOURCE,
    },
}

# Stage 5 — cross-item 중복 alias 정리 우선순위
# 같은 alias가 여러 items에 있으면, 더 적합한 item만 유지
# 형식: alias → (keep_in_item_keys, remove_from_others=True)
ALIAS_AUTHORITY = {
    # 음료캔 종류
    "음료캔": ["drink_can", "aluminum_can"],
    "맥주캔": ["drink_can", "aluminum_can"],
    "콜라캔": ["aluminum_can"],
    # 폐건전지
    "건전지": ["battery"],
    "폐건전지": ["battery"],
    # 종이컵
    "종이컵": ["disposable_paper_cup", "paper_cup"],
    # 헌 옷
    "헌 옷": ["old_clothes", "clothes_old"],
    "헌옷": ["old_clothes", "clothes_old"],
    # 노트북
    "노트북": ["electronics"],
    "맥북": ["electronics"],
}


def main():
    if not os.path.exists(DATA_PATH):
        print(f"FAIL: 파일 없음 {DATA_PATH}")
        return

    # 백업
    if not os.path.exists(BACKUP_PATH):
        shutil.copy(DATA_PATH, BACKUP_PATH)
        print(f"백업: {os.path.basename(BACKUP_PATH)}")

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    before = len(items)
    print(f"\n  before: {before} items")

    # === Stage 5 보강: cross-item 중복 alias 정리 ===
    print("\n  [Stage 5] cross-item 중복 alias 분석 중...")
    alias_to_keys = defaultdict(set)
    for k, v in items.items():
        for a in (v.get("aliases") or []):
            alias_to_keys[a].add(k)
    dup_alias = {a: ks for a, ks in alias_to_keys.items() if len(ks) > 1}
    print(f"    중복 alias 발견:  {len(dup_alias)}건")

    cleaned = 0
    for alias, owner_keys in dup_alias.items():
        # 권위 우선순위에 있으면 그 item만 유지
        authority = ALIAS_AUTHORITY.get(alias)
        if authority:
            preferred = next((a for a in authority if a in items), None)
            if preferred and preferred in owner_keys:
                for k in owner_keys:
                    if k != preferred:
                        aliases = items[k].get("aliases") or []
                        if alias in aliases:
                            aliases.remove(alias)
                            items[k]["aliases"] = aliases
                            cleaned += 1
    print(f"    정리 완료:        {cleaned}건")

    # === Stage 7 보강: 누락 13개 추가 ===
    print("\n  [Stage 7] 누락 13개 일상 품목 추가 중...")
    added = 0
    merged = 0
    for k, v in EXTRA_ITEMS_V4.items():
        if k in items:
            # 머지
            existing = set(items[k].get("aliases") or [])
            for a in v["aliases"]:
                existing.add(a)
            items[k]["aliases"] = sorted(existing)
            if not items[k].get("sourceUrl"):
                items[k]["sourceUrl"] = v["sourceUrl"]
            merged += 1
        else:
            items[k] = v
            added += 1
    print(f"    신규 추가: {added}, 머지: {merged}")

    after = len(items)
    src_after = sum(1 for v in items.values() if v.get("sourceUrl"))
    print(f"\n  after:  {after} items, sourceUrl {src_after} ({src_after*100/after:.1f}%)")

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  저장 완료")

    # Stage 7 검증
    print("\n  [Stage 7 검증]")
    targets = [
        "LED 전구", "마스크", "체온계", "기저귀", "껌", "담배꽁초",
        "테이크아웃 컵", "런닝머신", "도자기 꽃병", "유리 꽃병",
        "면봉", "물티슈", "테트라팩"
    ]
    hit = 0
    for t in targets:
        found = (
            t in items
            or any(v.get("name") == t for v in items.values())
            or any(t in (v.get("aliases") or []) for v in items.values())
        )
        mark = "OK " if found else "FAIL"
        print(f"    {mark}  '{t}'")
        if found:
            hit += 1
    print(f"\n  매칭: {hit}/{len(targets)}")


if __name__ == "__main__":
    main()
