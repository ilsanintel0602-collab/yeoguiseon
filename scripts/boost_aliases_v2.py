#!/usr/bin/env python3
"""
NATIONAL.items 3차 보강 - 모바일 검증에서 발견된 약점 보강
(노트북, 의류, 주방기구, 운동기구)

사용법: python scripts\\boost_aliases_v2.py

효과 기대: 일관성 문제 해결, 매칭률 92% → 96%+
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data", "national_rules.json"))
BACKUP_PATH = DATA_PATH + ".backup_pre_v2.json"

# 3차 보강 — 모바일 검증에서 발견된 약점
ALIAS_BOOST_V2 = {
    # 노트북 변형
    "electronics": [
        "노트북", "랩탑", "맥북", "그램", "LG그램", "삼성노트북", "갤럭시북",
        "데스크탑", "PC", "모니터", "키보드", "마우스", "스피커",
        "충전 케이블", "어댑터", "보조배터리", "USB허브", "공유기",
        "선풍기", "공기청정기", "가습기", "전기포트", "토스터",
    ],
    # 의류 종류
    "clothes": [
        "군복", "외투", "패딩", "코트", "재킷", "점퍼", "조끼",
        "청바지", "면바지", "정장바지", "반바지", "원피스", "치마",
        "잠옷", "교복", "유니폼", "운동복", "트레이닝복",
        "후드티", "맨투맨", "스웨터", "니트", "카디건", "블라우스",
        "양말", "스타킹", "내복", "속옷",
    ],
    # 운동기구 (toy_general에 추가)
    "toy_general": [
        "폼롤러", "요가매트", "마사지볼", "스트레칭 도구",
        "덤벨(작은)", "운동공", "짐볼", "훌라후프",
        "장난감 자동차", "블록", "퍼즐", "보드게임",
    ],
    # 화장품 추가
    "cosmetic_container": [
        "향수병", "마스카라", "아이브로우", "쿠션", "파운데이션",
        "토너", "에센스", "세럼", "아이크림", "바디로션",
        "샤워젤", "바디워시", "헤어에센스", "트리트먼트",
    ],
    # 가구 변형
    "furniture": [
        "행거", "옷장", "옷걸이(큰)", "수납장", "신발장",
        "테이블", "탁자", "협탁", "스툴", "발판",
    ],
    # 캔/금속 주방
    "small_metal_utensil": [
        "냄비", "프라이팬", "양푼", "찜기", "주방기구(작은)",
        "국자", "뒤집개", "젓가락통", "수저통",
    ],
    # 음식물 추가
    "food_waste": [
        "사과 껍질", "귤 껍질", "양파 껍질", "감자 껍질",
        "고기 양념", "남은 국물", "쌀밥(소량)", "면류 잔반",
    ],
    # 위험물 추가
    "battery": [
        "노트북 배터리", "휴대폰 배터리", "전동공구 배터리",
        "리모컨 배터리", "장난감 배터리",
    ],
}

# 신규 item — 압력솥 같은 재사용 주방기구
NEW_ITEMS_V2 = {
    "reusable_kitchenware": {
        "name": "재사용 주방기구 (압력솥·냄비 등)",
        "category": "reusable",
        "note": "고장 X 깨끗 = 계속 사용. 버릴 때만 폐기 절차.",
        "steps": ["세척 후 본인이 다시 사용", "고장난 경우 금속이면 캔류, 도자기면 일반쓰레기"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": [
            "압력솥", "전기밥솥(고장X)", "냄비(고장X)", "프라이팬(고장X)",
            "주방기구 재사용", "스테인리스 냄비", "양은냄비",
        ]
    },
    "exercise_equipment": {
        "name": "운동기구",
        "category": "general",
        "note": "소형 운동기구는 일반쓰레기. 대형은 대형폐기물 신고.",
        "steps": ["소형: 일반쓰레기(종량제봉투)", "대형: 대형폐기물 신고 (지자체)"],
        "regionVariation": True,
        "confidence": "high",
        "aliases": [
            "운동기구", "헬스기구", "런닝머신(소형)", "사이클(소형)",
            "스텝퍼", "악력기", "줄넘기",
        ]
    },
    "bag_backpack": {
        "name": "가방/배낭/지갑",
        "category": "clothes",
        "note": "재사용 가능하면 의류수거함, 훼손시 일반쓰레기",
        "steps": ["재사용 가능 → 의류수거함", "훼손 심함 → 일반쓰레기"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": [
            "가방", "배낭", "백팩", "핸드백", "크로스백",
            "지갑", "동전지갑", "에코백", "장지갑",
        ]
    },
}


def main():
    print(f"📂 작업 파일: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        print(f"❌ 파일 없음")
        sys.exit(1)

    if not os.path.exists(BACKUP_PATH):
        import shutil
        shutil.copy(DATA_PATH, BACKUP_PATH)
        print(f"💾 백업: {BACKUP_PATH}")

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    before = len(items)
    print(f"\n📊 Before: {before} items")

    # 신규 추가
    added = 0
    for k, v in NEW_ITEMS_V2.items():
        if k not in items:
            items[k] = v
            added += 1
    print(f"  신규 추가: {added}개")

    # aliases 보강
    boosted = 0
    total_aliases = 0
    for k, new_aliases in ALIAS_BOOST_V2.items():
        if k not in items:
            print(f"  ⚠️ {k} 없음 (스킵)")
            continue
        existing = items[k].get("aliases", []) or []
        merged = list(dict.fromkeys(existing + new_aliases))
        added_count = len(merged) - len(existing)
        if added_count > 0:
            items[k]["aliases"] = merged
            boosted += 1
            total_aliases += added_count
    print(f"  Boosted: {boosted} items, +{total_aliases} aliases")
    print(f"\n📊 After: {len(items)} items")

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료")

    # 확장 검증 (이전 92% → 96%+ 기대)
    common = [
        # 1차 92%에서 OK
        "투명페트병", "페트병", "콜라병", "물병", "종이박스", "택배상자", "책", "신문", "잡지",
        "우유팩", "주스팩", "두유팩", "비닐봉지", "과자봉지",
        "음료캔", "맥주캔", "참치캔", "통조림", "유리병", "소주병", "맥주병",
        "스티로폼", "음식물", "영수증", "휴지", "도자기", "깨진유리", "건전지", "형광등",
        "텀블러", "머그컵", "유리컵", "의자", "소파", "식탁", "침대",
        # v2 추가 검증
        "노트북", "랩탑", "맥북", "그램", "데스크탑",
        "군복", "외투", "패딩", "코트", "후드티", "맨투맨",
        "압력솥", "냄비", "프라이팬", "전기밥솥",
        "폼롤러", "요가매트", "덤벨", "운동기구",
        "가방", "배낭", "핸드백", "지갑",
        "화장품", "선크림", "립밤", "마스카라",
        "충전기", "케이블", "보조배터리", "어댑터",
    ]
    matched = sum(
        1 for q in common
        if q in items or any(v.get("name") == q or q in (v.get("aliases") or []) for v in items.values())
    )
    print(f"\n🎯 확장 {len(common)}개 품목 매칭: {matched}/{len(common)} ({matched*100/len(common):.0f}%)")


if __name__ == "__main__":
    main()
