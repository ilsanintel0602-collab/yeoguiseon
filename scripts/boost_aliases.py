#!/usr/bin/env python3
"""
NATIONAL.items 한글 별칭 자동 보강 + 누락 케이스 신규 추가
사용법: python scripts\\boost_aliases.py

효과: 일상 92개 품목 매칭 39% → 92% (+53%p)
"""
import json
import os
import sys

# 외장하드 본체 기준 path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "national_rules.json")
DATA_PATH = os.path.normpath(DATA_PATH)

BACKUP_PATH = DATA_PATH + ".backup_pre_boost.json"

# ===== 1차 보강: 핵심 한글 별칭 =====
ALIAS_BOOST = {
    "pet_bottle": ["페트병", "투명페트병", "콜라병", "사이다병", "물병(플라스틱)", "플라스틱병(투명)", "PET병"],
    "plastic_bottle": ["플라스틱병", "유색페트병", "샴푸통", "세제통", "린스통", "비누통", "선크림통(큰)", "음료수병(색)"],
    "milk_carton": ["우유팩", "주스팩", "두유팩", "멸균팩", "종이팩"],
    "newspaper": ["신문", "신문지", "잡지", "전단지", "광고지"],
    "paper_box": ["종이박스", "택배상자", "박스", "상자", "골판지", "박스종이"],
    "book": ["책", "공책", "잡지책", "동화책", "교과서", "백과사전", "메모노트", "수첩", "달력", "잡지", "전단지"],
    "beverage_can": ["음료캔", "맥주캔", "콜라캔", "사이다캔", "에너지드링크캔", "캔(음료)"],
    "food_can": ["통조림", "참치캔", "햄캔", "꽁치캔", "콩캔", "캔(식품)"],
    "glass_bottle": ["유리병", "와인병", "잼병", "꿀병", "올리브유병"],
    "vinyl_bag": ["비닐봉지", "비닐", "검정봉지", "마트봉지", "비닐백"],
    "snack_bag": ["과자봉지", "라면봉지", "스낵봉지", "스낵포장", "초콜릿포장"],
    "styrofoam_box": ["스티로폼", "스티로폼박스", "발포플라스틱", "포장스티로폼"],
    "food_waste": ["음식물", "음식쓰레기", "과일껍질", "음식찌꺼기", "남은음식", "음식 쓰레기"],
    "battery": ["건전지", "AA건전지", "AAA건전지", "리튬배터리", "충전지", "보조배터리", "체온계", "수은 체온계"],
    "lamp": ["형광등", "LED등", "백열전구", "전구", "조명"],
    "clothes": ["옷", "헌옷", "의류", "셔츠", "바지", "양말", "신발", "모자", "수건", "이불"],
    "electronics": ["충전기", "케이블", "이어폰", "USB", "마우스", "키보드", "드라이어", "청소기", "리모컨"],
    "reusable_cup": ["유리 컵", "스테인리스 잔"],
    "reusable_tumbler": ["보온병", "물병(스테인리스)"],
    "furniture": ["침대", "매트리스", "책장", "책상", "장롱", "쇼파"],
    "medicine": ["약통", "약", "연고", "물약", "알약", "캡슐약", "의약품"],
}

# ===== 신규 items =====
NEW_ITEMS = {
    "soju_bottle": {
        "name": "소주병/맥주병",
        "category": "glass",
        "note": "공병 보증금 환불 가능 (소매점). 깨끗이 비워서 배출.",
        "steps": ["내용물 비우기", "라벨 가능하면 제거", "보증금 환불 또는 유리류 배출함"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["소주병", "맥주병", "막걸리병", "공병"]
    },
    "plastic_container": {
        "name": "플라스틱 용기",
        "category": "plastic",
        "note": "음식물 묻은 것은 깨끗이 씻어서 플라스틱류로 배출",
        "steps": ["내용물 비우고 헹구기", "라벨 제거", "플라스틱류 배출함"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["플라스틱 용기", "플라스틱 통", "포장재(플라스틱)", "투명 용기", "반찬통"]
    },
    "receipt": {
        "name": "영수증/감열지",
        "category": "general",
        "note": "감열지는 비스페놀A 함유. 종이류로 분리배출 불가 → 일반쓰레기",
        "steps": ["일반쓰레기(종량제봉투)로 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["영수증", "감열지", "신용카드 영수증", "택배 송장"]
    },
    "tissue_diaper": {
        "name": "휴지/기저귀/생리대",
        "category": "general",
        "note": "위생용품은 모두 일반쓰레기. 분리수거 불가",
        "steps": ["일반쓰레기(종량제봉투)로 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["휴지", "두루마리 휴지", "물티슈", "기저귀", "생리대", "위생용품", "키친타올"]
    },
    "ceramic_broken_glass": {
        "name": "도자기/깨진 유리/거울",
        "category": "general",
        "note": "불연성 폐기물. 깨진 유리는 신문지로 감싸 '위험' 표시",
        "steps": ["깨진 유리는 신문지로 안전하게 감싸기", "'위험' 표시", "불연성 종량제봉투 또는 일반쓰레기"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["도자기", "깨진 유리", "깨진 그릇", "거울", "사기 그릇", "토기"]
    },
    "mask_glove": {
        "name": "마스크/일회용 장갑",
        "category": "general",
        "note": "위생상 일반쓰레기. 끈은 자르고 배출",
        "steps": ["마스크 끈 자르기", "일반쓰레기(종량제봉투)로 배출"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["마스크", "KF94", "보건용 마스크", "비닐장갑", "일회용 장갑", "라텍스 장갑"]
    },
    "cigarette_butt": {
        "name": "담배꽁초/담배갑",
        "category": "general",
        "note": "필터에 화학물질. 일반쓰레기",
        "steps": ["완전히 끄고 일반쓰레기(종량제봉투)"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["담배꽁초", "꽁초", "담배갑", "담배 케이스", "라이터"]
    },
    "toy_general": {
        "name": "장난감/인형/공",
        "category": "general",
        "note": "복합소재. 큰 것은 대형폐기물 신고",
        "steps": ["일반쓰레기 또는 대형폐기물 신고 (크기에 따라)"],
        "regionVariation": True,
        "confidence": "medium",
        "aliases": ["장난감", "인형", "테디베어", "공", "농구공", "축구공", "고무공"]
    },
    "cosmetic_container": {
        "name": "화장품 용기",
        "category": "plastic",
        "note": "비우고 헹궈서 플라스틱류. 작은 것은 일반쓰레기 가능",
        "steps": ["내용물 비우기", "헹구기", "라벨 제거", "플라스틱류 또는 일반쓰레기"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["화장품", "선크림", "립밤", "립스틱", "마스카라", "스킨", "로션통", "샴푸통(소형)"]
    },
    "small_metal_utensil": {
        "name": "수저/젓가락/포크 (금속)",
        "category": "can",
        "note": "스테인리스/금속은 캔류와 함께. 작은 것은 일반쓰레기 가능",
        "steps": ["금속이면 캔류 배출함", "플라스틱이면 일반쓰레기"],
        "regionVariation": False,
        "confidence": "medium",
        "aliases": ["수저", "숟가락", "젓가락(금속)", "포크", "스푼", "스테인리스 수저"]
    },
    "plant_flower": {
        "name": "꽃/화분/식물",
        "category": "general",
        "note": "흙은 별도 분리. 화분(플라스틱)은 플라스틱류",
        "steps": ["흙 털어내기", "식물은 음식물 X 일반쓰레기", "화분은 재질별 분리"],
        "regionVariation": False,
        "confidence": "medium",
        "aliases": ["꽃다발", "꽃", "시든 꽃", "화분", "분재", "다육이"]
    },
    "glasses_lens": {
        "name": "안경/콘택트렌즈",
        "category": "general",
        "note": "복합소재. 일반쓰레기 또는 안경점에 기부",
        "steps": ["일반쓰레기 또는 시각장애인 단체에 기부"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["안경", "선글라스", "콘택트렌즈", "렌즈", "안경테"]
    },
    "lunchbox_container": {
        "name": "도시락통/반찬통 (재사용)",
        "category": "reusable",
        "note": "깨끗이 세척 후 본인이 다시 사용",
        "steps": ["세척 후 재사용", "버릴 때만 플라스틱류 또는 캔류"],
        "regionVariation": False,
        "confidence": "high",
        "aliases": ["도시락통", "반찬통", "보관 용기", "타파웨어", "락앤락"]
    },
}


def main():
    print(f"📂 작업 파일: {DATA_PATH}")
    if not os.path.exists(DATA_PATH):
        print(f"❌ 파일 없음. 외장하드 연결 확인.")
        sys.exit(1)

    # 백업
    if not os.path.exists(BACKUP_PATH):
        import shutil
        shutil.copy(DATA_PATH, BACKUP_PATH)
        print(f"💾 백업: {BACKUP_PATH}")

    # 로드
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    before = len(items)
    print(f"\n📊 Before: {before} items")

    # 신규 추가
    added = 0
    for k, v in NEW_ITEMS.items():
        if k not in items:
            items[k] = v
            added += 1
    print(f"  신규 추가: {added}개")

    # aliases 보강
    boosted = 0
    total_aliases = 0
    for k, new_aliases in ALIAS_BOOST.items():
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
    print(f"  Boosted items: {boosted}개, aliases 추가: {total_aliases}개")

    # 저장
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ After: {len(items)} items 저장 완료")
    print(f"   {DATA_PATH}")

    # 매칭 점검
    common = [
        "투명페트병", "페트병", "콜라병", "물병", "종이박스", "택배상자", "책", "신문", "잡지",
        "우유팩", "주스팩", "두유팩", "멸균팩", "비닐봉지", "과자봉지", "라면봉지", "스낵봉지",
        "음료캔", "맥주캔", "참치캔", "통조림", "부탄가스", "유리병", "소주병", "맥주병", "와인병",
        "스티로폼", "도시락통", "포장재", "음식물", "과일껍질", "달걀껍데기", "뼈",
        "영수증", "휴지", "기저귀", "도자기", "깨진유리", "거울", "건전지", "형광등", "체온계", "수은",
        "화장품", "샴푸통", "선크림", "립밤", "치약", "칫솔",
        "이어폰", "충전기", "케이블", "리모컨", "마우스",
        "옷", "신발", "양말", "모자", "수저", "젓가락", "포크", "빨대",
        "마스크", "장갑", "수세미", "랩",
        "텀블러", "머그컵", "유리컵", "의자", "소파", "식탁", "침대", "책장",
        "전자레인지", "선풍기", "청소기", "드라이어",
        "꽃다발", "화분", "장난감", "인형", "공",
        "안경", "렌즈", "콘택트", "약통", "약", "연고",
        "라이터", "담배꽁초", "담배갑",
    ]
    matched = sum(
        1 for q in common
        if q in items or any(v.get("name") == q or q in (v.get("aliases") or []) for v in items.values())
    )
    print(f"\n🎯 일상 {len(common)}개 품목 매칭: {matched}/{len(common)} ({matched*100/len(common):.0f}%)")
    print(f"   (어제 정리 직후 39% → 보강 후 {matched*100/len(common):.0f}%)")


if __name__ == "__main__":
    main()
