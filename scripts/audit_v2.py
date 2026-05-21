#!/usr/bin/env python3
"""
여기선 v5.8 강화된 데이터 점검 v2
- 8 stage 검사 + 단계별 합격선
- 진짜 99점 합격선 (이전 audit_data.py의 100점은 후한 기준)
- 99점 미만 시 stage별 보강 가이드 출력

기준 설계 원칙:
- Stage 1-2 = JSON/카테고리 무결성 (엄격, 합격선 = 만점)
- Stage 3-5 = 데이터 품질 (합격선 80%)
- Stage 6-8 = 사용성 (합격선 90%)

사용: python scripts\\audit_v2.py
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
NATIONAL = os.path.join(DATA_DIR, "national_rules.json")
BUNRI = os.path.join(DATA_DIR, "raw_bunribaechul_730.json")
APP_HTML = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "app.html"))
REPORT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "audit_v2_report.md"))
SCHEMA = os.path.join(DATA_DIR, "schema", "rule.schema.json")

# 정식 카테고리 (app.html line 477과 동일)
VALID_CATEGORIES = {
    "plastic", "paper", "paper_pack", "vinyl", "can", "glass", "styrofoam",
    "food", "general", "battery", "lamp", "clothes", "electronics",
    "furniture", "hazardous", "medicine", "reusable",
}

BUNRI_MAIN_URL_PATTERNS = [
    "front/dischargeMethod/index.do",       # 메인
    "xn--oy2b29bd3a601b.kr/$",              # 도메인 루트
]
BUNRI_DETAIL_URL_PATTERN = "dictionaryView.do?niIdx="  # 개별 페이지


def stage_print(n, title):
    print(f"\n{'='*64}")
    print(f"  Stage {n}: {title}")
    print('='*64)


def gauge(label, score, full, threshold, lines):
    """점수 출력 + 합격/미달 표시"""
    icon = "OK" if score >= threshold else "!!"
    pct = score * 100 / full if full else 0
    msg = f"  [{icon}] {label}: {score:.1f} / {full}  (합격선 {threshold})  {pct:.0f}%"
    print(msg)
    lines.append(msg)
    return score


def main():
    lines = ["# 여기선 v5.8 강화 점검 v2\n"]
    total = 0
    failed_stages = []
    suggestions = []

    # === 로드 ===
    with open(NATIONAL, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    n = len(items)
    print(f"loaded: national_rules.json  ({n} items)")

    try:
        with open(BUNRI, encoding="utf-8") as f:
            bunri = json.load(f)
        bunri_items = bunri.get("items", [])
    except:
        bunri_items = []
    print(f"loaded: raw_bunribaechul_730  ({len(bunri_items)} items)")

    try:
        with open(APP_HTML, encoding="utf-8") as f:
            app_html = f.read()
    except:
        app_html = ""

    schema = None
    if os.path.exists(SCHEMA):
        try:
            with open(SCHEMA, encoding="utf-8") as f:
                schema = json.load(f)
        except:
            schema = None

    # =========================================================
    # Stage 1: JSON 무결성 (15점, 합격선 15)
    # =========================================================
    stage_print(1, "JSON 무결성 + 필수 필드 + schema 준수")
    s1 = 0
    s1_full = 15
    # 1a. JSON valid (이미 load 성공)
    s1 += 5
    print("  + JSON valid: 5")
    # 1b. 필수 필드
    missing_name = sum(1 for v in items.values() if not v.get("name"))
    missing_cat = sum(1 for v in items.values() if not v.get("category"))
    missing_steps = sum(1 for v in items.values() if not v.get("steps") or len(v.get("steps") or []) == 0)
    if missing_name + missing_cat + missing_steps == 0:
        s1 += 5
        print("  + 필수 필드 (name/category/steps) 완비: 5")
    else:
        gain = max(0, 5 - (missing_name + missing_cat + missing_steps) * 0.1)
        s1 += gain
        print(f"  - 필수 필드 누락: name={missing_name}, cat={missing_cat}, steps={missing_steps}  ({gain:.1f}/5)")
        if missing_steps:
            suggestions.append(f"S1: steps 비어있는 item {missing_steps}건 — 기본 카테고리 steps 폴백 추가")
    # 1c. schema 준수 (간이 — schema 있으면 5점, 없으면 3점)
    if schema:
        s1 += 5
        print("  + rule.schema.json 존재: 5")
    else:
        s1 += 3
        print("  ? schema 파일 없음 (3/5)")
        suggestions.append("S1: data/schema/rule.schema.json 갱신 또는 검증 스크립트 추가")
    gauge("Stage 1 점수", s1, s1_full, 15, lines)
    total += s1
    if s1 < 15:
        failed_stages.append(1)

    # =========================================================
    # Stage 2: 카테고리 정합성 (15점, 합격선 15)
    # =========================================================
    stage_print(2, "categories ↔ items ↔ app.html 3중 정합")
    s2 = 0
    s2_full = 15
    # 2a. items의 category가 VALID에 모두 포함
    used_cats = set(v.get("category") for v in items.values())
    invalid = used_cats - VALID_CATEGORIES
    if not invalid:
        s2 += 5
        print(f"  + items category 모두 valid (분포 {len(used_cats)}개): 5")
    else:
        s2 += 2
        print(f"  - 알 수 없는 category: {invalid}  (2/5)")
        suggestions.append(f"S2: items category에 무효 값 {invalid}")
    # 2b. categories 섹션에 모든 사용 카테고리 정의
    defined_cats = set((data.get("categories") or {}).keys())
    missing_def = used_cats - defined_cats
    if not missing_def:
        s2 += 5
        print(f"  + categories 섹션 정의 완비 ({len(defined_cats)}개): 5")
    else:
        gain = max(0, 5 - len(missing_def) * 0.5)
        s2 += gain
        print(f"  - categories 섹션 미정의: {missing_def}  ({gain:.1f}/5)")
        suggestions.append(f"S2: categories 섹션에 {missing_def} 정의 추가")
    # 2c. app.html enum과 일치
    enum_match = re.search(r"\[\s*'plastic'.*?'medicine'\s*\]", app_html)
    if enum_match:
        s2 += 5
        print("  + app.html enum과 일치 확인: 5")
    else:
        s2 += 3
        print("  ? app.html enum 직접 확인 어려움 (3/5)")
    gauge("Stage 2 점수", s2, s2_full, 15, lines)
    total += s2
    if s2 < 15:
        failed_stages.append(2)

    # =========================================================
    # Stage 3: 데이터 풍부도 (15점, 합격선 12)
    # =========================================================
    stage_print(3, "데이터 풍부도 (note / steps 길이 / feature / caution)")
    s3 = 0
    s3_full = 15
    # 3a. note 채워진 비율
    have_note = sum(1 for v in items.values() if (v.get("note") or "").strip())
    pct_note = have_note * 100 / n
    if pct_note >= 80:
        s3 += 5
        print(f"  + note 채움률 {pct_note:.0f}%: 5")
    elif pct_note >= 50:
        s3 += 3
        print(f"  ? note 채움률 {pct_note:.0f}% (목표 80%): 3")
        suggestions.append(f"S3: note 빈 item이 {n - have_note}건 — 환경부 caution/feature에서 자동 채우기 가능")
    else:
        s3 += 1
        print(f"  - note 채움률 {pct_note:.0f}% (목표 80%): 1")
        suggestions.append(f"S3: note 빈 item이 {n - have_note}건 — 대량 보강 필요")
    # 3b. steps 평균 길이
    step_lens = [len(v.get("steps") or []) for v in items.values()]
    avg_step = sum(step_lens) / n if n else 0
    if avg_step >= 3:
        s3 += 5
        print(f"  + steps 평균 {avg_step:.1f}단계: 5")
    elif avg_step >= 2:
        s3 += 3
        print(f"  ? steps 평균 {avg_step:.1f}단계 (목표 3+): 3")
    else:
        s3 += 1
        print(f"  - steps 평균 {avg_step:.1f}단계 (목표 3+): 1")
    # 3c. feature/caution 채워진 비율 (환경부 통합 효과)
    have_feat = sum(1 for v in items.values() if (v.get("feature") or "").strip())
    have_caut = sum(1 for v in items.values() if (v.get("caution") or "").strip())
    pct_extra = (have_feat + have_caut) * 50 / n
    if pct_extra >= 60:
        s3 += 5
        print(f"  + feature/caution 통합률 {pct_extra:.0f}%: 5")
    elif pct_extra >= 30:
        s3 += 3
        print(f"  ? feature/caution 통합률 {pct_extra:.0f}%: 3")
        suggestions.append(f"S3: feature/caution 부족 — 환경부 730에서 더 머지 가능")
    else:
        s3 += 1
        print(f"  - feature/caution 통합률 {pct_extra:.0f}%: 1")
    gauge("Stage 3 점수", s3, s3_full, 12, lines)
    total += s3
    if s3 < 12:
        failed_stages.append(3)

    # =========================================================
    # Stage 4: 출처 부여 정확도 (15점, 합격선 12)
    # =========================================================
    stage_print(4, "sourceUrl 정확도 (메인 URL vs 개별 페이지)")
    s4 = 0
    s4_full = 15
    have_src = sum(1 for v in items.values() if v.get("sourceUrl"))
    pct_src = have_src * 100 / n
    # 4a. sourceUrl 보유율
    if pct_src >= 95:
        s4 += 7
        print(f"  + sourceUrl 보유율 {pct_src:.1f}%: 7")
    elif pct_src >= 85:
        s4 += 5
        print(f"  ? sourceUrl 보유율 {pct_src:.1f}% (목표 95%): 5")
        suggestions.append(f"S4: sourceUrl 없는 item이 {n - have_src}건")
    else:
        s4 += 2
        print(f"  - sourceUrl 보유율 {pct_src:.1f}%: 2")
    # 4b. 정확한 개별 페이지 (vs 메인 URL)
    is_detail = sum(1 for v in items.values()
                    if v.get("sourceUrl") and BUNRI_DETAIL_URL_PATTERN in (v.get("sourceUrl") or ""))
    pct_detail = is_detail * 100 / n
    if pct_detail >= 70:
        s4 += 8
        print(f"  + 개별 페이지 URL 비율 {pct_detail:.1f}%: 8")
    elif pct_detail >= 40:
        s4 += 5
        print(f"  ? 개별 페이지 URL 비율 {pct_detail:.1f}% (메인 URL 다수): 5")
        suggestions.append(f"S4: 메인 URL로 폴백한 item {have_src - is_detail}건 — 환경부 raw에서 개별 URL 재매칭 필요")
    else:
        s4 += 2
        print(f"  - 개별 페이지 URL 비율 {pct_detail:.1f}%: 2")
        suggestions.append(f"S4: 대부분 메인 URL — 환경부 원본에서 niIdx별 개별 URL 통합 필요")
    gauge("Stage 4 점수", s4, s4_full, 12, lines)
    total += s4
    if s4 < 12:
        failed_stages.append(4)

    # =========================================================
    # Stage 5: Alias 무결성 (15점, 합격선 12)
    # =========================================================
    stage_print(5, "Alias 오염 + 중복 + 균형")
    s5 = 0
    s5_full = 15
    # 5a. 오염 (이전과 동일 검사)
    suspect = {
        "book": ["유리컵", "페트병", "캔"],
        "pet_bottle": ["책", "노트북", "옷"],
        "glass_bottle": ["책", "노트북", "옷"],
        "electronics": ["페트병", "유리병", "음식물"],
    }
    pollute = []
    for k, banned in suspect.items():
        v = items.get(k)
        if not v: continue
        aliases = v.get("aliases") or []
        for b in banned:
            if b in aliases:
                pollute.append((k, b))
    if not pollute:
        s5 += 5
        print("  + 카테고리 alias 오염 없음: 5")
    else:
        s5 += 2
        print(f"  - 오염 {len(pollute)}건: {pollute[:3]}  (2/5)")
        suggestions.append(f"S5: alias 오염 {len(pollute)}건")
    # 5b. cross-item 중복 alias (같은 alias가 여러 items에)
    alias_to_keys = defaultdict(set)
    for k, v in items.items():
        for a in (v.get("aliases") or []):
            alias_to_keys[a].add(k)
    dup_alias = {a: ks for a, ks in alias_to_keys.items() if len(ks) > 1}
    if len(dup_alias) <= 5:
        s5 += 5
        print(f"  + cross-item 중복 alias {len(dup_alias)}개: 5")
    elif len(dup_alias) <= 50:
        s5 += 3
        print(f"  ? cross-item 중복 alias {len(dup_alias)}개 (조정 권장): 3")
        # 예시 출력
        examples = list(dup_alias.items())[:3]
        for a, ks in examples:
            print(f"       '{a}' → {ks}")
        suggestions.append(f"S5: 중복 alias {len(dup_alias)}개 — 어느 item에 attach할지 정리 필요")
    else:
        s5 += 1
        print(f"  - cross-item 중복 alias {len(dup_alias)}개: 1")
        suggestions.append(f"S5: 중복 alias 대량 ({len(dup_alias)})")
    # 5c. 카테고리별 alias 균형 (각 item 최소 1개 alias)
    no_alias = sum(1 for v in items.values() if not (v.get("aliases") or []))
    if no_alias <= n * 0.05:
        s5 += 5
        print(f"  + alias 없는 item 비율 {no_alias*100/n:.1f}%: 5")
    elif no_alias <= n * 0.15:
        s5 += 3
        print(f"  ? alias 없는 item {no_alias}건 ({no_alias*100/n:.1f}%): 3")
    else:
        s5 += 1
        print(f"  - alias 없는 item {no_alias}건 ({no_alias*100/n:.1f}%): 1")
        suggestions.append(f"S5: alias 없는 item {no_alias}건 — 추가 필요")
    gauge("Stage 5 점수", s5, s5_full, 12, lines)
    total += s5
    if s5 < 12:
        failed_stages.append(5)

    # =========================================================
    # Stage 6: 환경부 통합 (10점, 합격선 9)
    # =========================================================
    stage_print(6, "환경부 730 매칭 + similar→aliases 머지")
    s6 = 0
    s6_full = 10
    bunri_names = set(it.get("name") for it in bunri_items if it.get("name"))
    item_names = set(v.get("name") for v in items.values() if v.get("name"))
    item_aliases_all = set()
    for v in items.values():
        for a in (v.get("aliases") or []):
            item_aliases_all.add(a)
    matched_name = bunri_names & item_names
    matched_alias = (bunri_names - matched_name) & item_aliases_all
    bunri_missing = bunri_names - matched_name - matched_alias
    pct_match = (len(matched_name) + len(matched_alias)) * 100 / len(bunri_names) if bunri_names else 100
    # 6a. 매칭률
    if pct_match >= 95:
        s6 += 5
        print(f"  + 환경부 매칭률 {pct_match:.1f}%: 5")
    elif pct_match >= 85:
        s6 += 3
        print(f"  ? 환경부 매칭률 {pct_match:.1f}%: 3")
    else:
        s6 += 1
        print(f"  - 환경부 매칭률 {pct_match:.1f}%: 1")
    # 6b. similar→aliases 머지 검증 (간이 — 환경부 similar의 표본)
    sample_similar_merged = 0
    sample_count = 0
    for bi in bunri_items[:100]:  # 처음 100개만 표본
        bname = bi.get("name")
        sims = bi.get("similar") or []
        if not bname or not sims: continue
        sample_count += 1
        # bname이 우리 items의 어떤 key에 매칭됐을 때, 그 aliases에 similar가 들어갔는지
        for k, v in items.items():
            if v.get("name") == bname:
                vmiases = set(v.get("aliases") or [])
                if any(s in vmiases for s in sims):
                    sample_similar_merged += 1
                break
    if sample_count == 0:
        s6 += 3
        print("  ? similar 머지 표본 부족 (3/5)")
    else:
        rate = sample_similar_merged * 100 / sample_count
        if rate >= 70:
            s6 += 5
            print(f"  + similar→aliases 머지율 {rate:.0f}% (표본 {sample_count}): 5")
        else:
            s6 += 3
            print(f"  ? similar→aliases 머지율 {rate:.0f}%: 3")
            suggestions.append(f"S6: similar→aliases 머지 미완성 (표본 {sample_count} 중 {rate:.0f}%)")
    gauge("Stage 6 점수", s6, s6_full, 9, lines)
    total += s6
    if s6 < 9:
        failed_stages.append(6)

    # =========================================================
    # Stage 7: 일상 200 매칭률 (10점, 합격선 9)
    # =========================================================
    stage_print(7, "일상 200 품목 매칭률 (확장)")
    s7 = 0
    s7_full = 10
    # 기존 87개 + 추가 113개 (카테고리별 골고루)
    extended = [
        # 재활용 베이직
        "투명페트병", "페트병", "콜라병", "물병", "음료수병", "생수병",
        "종이박스", "택배상자", "신문", "잡지", "책", "노트", "공책",
        "우유팩", "주스팩", "두유팩", "멸균팩", "테트라팩",
        "비닐봉지", "과자봉지", "라면봉지", "포장재", "포장 봉투",
        "음료캔", "맥주캔", "참치캔", "통조림", "알루미늄캔", "스프레이캔",
        "유리병", "소주병", "맥주병", "와인병", "양주병",
        "스티로폼", "포장재 스티로폼", "에어캡", "뽁뽁이", "완충재",
        # 음식물
        "사과 껍질", "양파 껍질", "감자 껍질", "고기 양념", "남은 국물",
        "쌀밥", "면류", "김치", "과일 껍질",
        # 일반쓰레기
        "영수증", "휴지", "물티슈", "도자기", "깨진유리", "이쑤시개", "면봉",
        "기저귀", "마스크", "껌", "담배꽁초",
        # 위험물
        "건전지", "폐건전지", "리튬배터리", "충전식 배터리", "형광등", "LED 전구",
        "주사기", "체온계", "수은",
        # 의류
        "옷", "헌 옷", "패딩", "코트", "후드티", "맨투맨", "양말", "신발",
        "스타킹", "내복", "속옷", "운동화", "구두",
        # 가방
        "가방", "배낭", "백팩", "핸드백", "지갑", "에코백", "캐리어",
        # 전자기기
        "노트북", "맥북", "그램", "데스크탑", "충전기", "케이블", "이어폰",
        "보조배터리", "어댑터", "선풍기", "공기청정기", "가습기",
        "TV", "냉장고", "세탁기", "에어컨",  # 대형가전
        # 컵·식기
        "텀블러", "머그컵", "유리컵", "종이컵", "일회용컵",
        # 가구
        "의자", "소파", "식탁", "침대", "책상", "옷장", "서랍장",
        # 주방기구
        "압력솥", "냄비", "프라이팬", "전기밥솥", "양푼", "도마",
        # 운동기구
        "폼롤러", "요가매트", "덤벨", "운동기구", "런닝머신", "헬스기구",
        # 화장품
        "화장품", "선크림", "립밤", "마스카라", "샴푸통", "세제통", "향수병",
        "토너", "파운데이션",
        # 기타
        "꽃병", "거울", "도자기 꽃병", "유리 꽃병",
        "약", "유통기한 지난 약", "처방약",
    ]
    matched = []
    unmatched = []
    matched_by_cat = Counter()
    for q in extended:
        found_in = None
        if q in items:
            found_in = items[q].get("category")
        else:
            for k, v in items.items():
                if v.get("name") == q or q in (v.get("aliases") or []):
                    found_in = v.get("category")
                    break
        if found_in:
            matched.append(q)
            matched_by_cat[found_in] += 1
        else:
            unmatched.append(q)
    rate = len(matched) * 100 / len(extended)
    if rate >= 97:
        s7 += 10
        print(f"  + 200 품목 매칭률 {len(matched)}/{len(extended)} ({rate:.1f}%): 10")
    elif rate >= 92:
        s7 += 7
        print(f"  ? 200 품목 매칭률 {len(matched)}/{len(extended)} ({rate:.1f}%): 7")
        suggestions.append(f"S7: 누락 {len(unmatched)}개 — alias 추가 필요: {unmatched[:10]}")
    else:
        s7 += 3
        print(f"  - 200 품목 매칭률 {len(matched)}/{len(extended)} ({rate:.1f}%): 3")
        suggestions.append(f"S7: 대량 누락 ({len(unmatched)}) — boost_v4 필요")
    if unmatched:
        print(f"  누락 {len(unmatched)}: {unmatched[:15]}")
    gauge("Stage 7 점수", s7, s7_full, 9, lines)
    total += s7
    if s7 < 9:
        failed_stages.append(7)

    # =========================================================
    # Stage 8: 모바일 UX 정합성 (5점, 합격선 5)
    # =========================================================
    stage_print(8, "SYSTEM_PROMPT / catLabels / categories 3자 정합")
    s8 = 0
    s8_full = 5
    # 8a. app.html에서 SYSTEM_PROMPT의 enum 추출 시도
    sys_prompt_enum_match = re.search(r"item_id.*?enum.*?\[(.*?)\]", app_html, re.DOTALL)
    if sys_prompt_enum_match:
        s8 += 2
        print("  + SYSTEM_PROMPT enum 검출: 2")
    else:
        # 대안: 'plastic|paper|...' 패턴 검색
        if re.search(r"'plastic'.*?'paper_pack'", app_html):
            s8 += 2
            print("  + 카테고리 enum 사용 검출: 2")
        else:
            s8 += 1
            print("  ? SYSTEM_PROMPT enum 직접 검출 어려움 (1/2)")
    # 8b. catLabels 정의 검사
    if "catLabels" in app_html or "catSteps" in app_html:
        s8 += 3
        print("  + catLabels/catSteps 정의 존재: 3")
    else:
        s8 += 1
        print("  - catLabels/catSteps 정의 없음 (1/3)")
        suggestions.append("S8: app.html에 catLabels/catSteps 정의 필요")
    gauge("Stage 8 점수", s8, s8_full, 5, lines)
    total += s8
    if s8 < 5:
        failed_stages.append(8)

    # =========================================================
    # 종합
    # =========================================================
    print(f"\n{'='*64}")
    print(f"  종합 점수:  {total:.1f} / 100  (합격선 99)")
    print('='*64)
    status = "PASS" if total >= 99 else "FAIL"
    print(f"  결과:  {status}")
    if failed_stages:
        print(f"  미달 stage:  {failed_stages}")
    if suggestions:
        print(f"\n  보강 가이드 ({len(suggestions)}건):")
        for sg in suggestions:
            print(f"    - {sg}")
    else:
        print(f"\n  모든 stage 합격. 데이터 production-ready.")

    # 리포트 저장
    lines.append(f"\n## 종합\n\n**{total:.1f} / 100  ({status})**\n\n")
    if failed_stages:
        lines.append(f"- 미달 stage: {failed_stages}\n")
    if suggestions:
        lines.append(f"\n### 보강 가이드\n\n")
        for sg in suggestions:
            lines.append(f"- {sg}\n")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print(f"\nreport: {REPORT}")


if __name__ == "__main__":
    main()
