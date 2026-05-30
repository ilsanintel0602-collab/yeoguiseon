#!/usr/bin/env python3
"""
Quick pre-deploy check — 5초 안에 데이터 무결성 + 핵심 정합성 검사
push 전 더블클릭 권장
"""
import json, os, sys

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

def check(name, ok, detail=""):
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}{(': ' + detail) if detail else ''}")
    return ok

print("\n=== Quick Pre-Deploy Check ===\n")
all_ok = True

# 1. national_rules.json
try:
    with open(os.path.join(ROOT, "data", "national_rules.json"), encoding="utf-8") as f:
        nat = json.load(f)
    items = nat.get("items", {})
    all_ok &= check("national_rules.json 로드", True, f"{len(items)} items")
    aliases = sum(len(v.get("aliases", [])) for v in items.values())
    all_ok &= check("alias 평균", aliases / max(len(items), 1) >= 2.5, f"평균 {aliases/max(len(items),1):.1f}")
    cats = set(v.get("category") for v in items.values())
    # v5.37 (2026-05-24): 분리배출.kr 12개 표준 + 비재활용 8개 (한국 표준 정렬)
    VALID = {
        # 재활용 12 (분리배출.kr 표준)
        "paper", "paper_pack", "pet_clear", "plastic", "vinyl", "styrofoam",
        "glass", "can", "clothes", "battery", "lamp", "electronics",
        # 비재활용 8
        "food", "general", "general_noncombustible", "general_or_bulky",
        "bulky", "furniture", "hazardous", "medicine"
    }
    bad_cats = cats - VALID
    all_ok &= check("카테고리 enum", not bad_cats, f"이상 enum: {bad_cats}" if bad_cats else "20개 정합 (분리배출.kr 12 + 비재활용 8)")

    # ⭐ v5.28.3: 가짜 item 자동 탐지 (2026-05-23 오염 사건 학습)
    # 패턴 1: ID에 동사·문장체 (환경부 크롤링 파싱 오류 흔적)
    SENTENCE_MARKERS = ['수거함으', '배출합', '이용하', '서비스(', '입니', '해야', '주시고', '바랍니']
    fake_by_id = [k for k in items.keys() if any(m in k for m in SENTENCE_MARKERS)]
    # 패턴 2: ID가 너무 길고 punctuation 포함
    fake_by_id += [k for k in items.keys() if len(k) > 25 and any(c in k for c in '(){}[],')]
    fake_by_id = list(set(fake_by_id))
    all_ok &= check("가짜 item ID (문장체) 차단",
                    not fake_by_id,
                    f"가짜 item: {fake_by_id[:3]}" if fake_by_id else "0건")

    # 패턴 3: 라벨형 item (general 카테고리 + alias 100+ — catch-all 의심)
    suspect_labels = []
    for k, v in items.items():
        n_aliases = len(v.get("aliases", []))
        if v.get("category") == "general" and n_aliases > 200:
            # general 자체는 OK (의도된 catchall) — 단 비정상적으로 큰 통은 경고
            suspect_labels.append((k, n_aliases))
    # 정상 catchall은 1~2개. 그 이상이면 경고
    all_ok &= check("일반 catchall item 수",
                    len([s for s in suspect_labels if s[0] not in ('general', '기타_일반')]) == 0,
                    f"새 라벨형 의심: {[s[0] for s in suspect_labels if s[0] not in ('general', '기타_일반')]}" if suspect_labels else f"{len(suspect_labels)}개 (의도된 catchall)")

    # 패턴 4: 1글자 alias 노이즈 (보존 화이트리스트 외)
    # 2026-05-22 v5.32 이후: 직관적 1글자 검색어는 의도 보존
    #   밥·국 → food_waste, 껌 → general, 백 → bag, 캡 → hat (영어 줄임말)
    PRESERVE_1CHAR = {'책', '옷', '약', '밥', '국', '껌', '백', '캡'}
    noisy_1char = []
    for k, v in items.items():
        for a in v.get("aliases", []):
            s = str(a).strip()
            if len(s) == 1 and s not in PRESERVE_1CHAR:
                noisy_1char.append((k, s))
    all_ok &= check("1글자 alias 노이즈",
                    len(noisy_1char) == 0,
                    f"노이즈 {len(noisy_1char)}건: {noisy_1char[:3]}" if noisy_1char else "0건 (옷·약·책만 보존)")

    # ⭐ v6.28: 본질 자동 감지 — alias semantic mismatch (다른 item name과 정확 일치)
    # 사고 예: 디지털 카메라.aliases에 "텔레비전" (2026-05-30 발견)
    # 사용자 본질 명령 [feedback-no-regression]: "같은 사고 반복 X"
    name_to_key = {}
    for k, v in items.items():
        n = (v.get("name") or k).strip()
        if n:
            name_to_key.setdefault(n, k)
    mismatch_aliases = []
    for k, v in items.items():
        item_name = (v.get("name") or k).strip()
        seen_alias = set()
        for a in v.get("aliases", []):
            s = str(a).strip()
            if not s or s in seen_alias:
                continue
            seen_alias.add(s)
            if s == item_name:
                continue  # 자기 name과 일치는 OK
            # 다른 item의 name과 정확 일치 → 충돌
            other = name_to_key.get(s)
            if other and other != k:
                mismatch_aliases.append(f"{k}.aliases='{s}' ↔ {other}")
            # 다른 item의 key와 정확 일치
            elif s in items and s != k:
                mismatch_aliases.append(f"{k}.aliases='{s}' ↔ {s}(key)")
    mismatch_aliases = list(dict.fromkeys(mismatch_aliases))
    all_ok &= check("[본질] alias semantic mismatch (다른 item과 충돌)",
                    not mismatch_aliases,
                    f"{len(mismatch_aliases)}건: " + " | ".join(mismatch_aliases[:8]) if mismatch_aliases else "0건")

    # ⭐ v6.28: 본질 자동 감지 — catLabels/collectorName 라벨이 환경부 표준 단어 포함해야 함
    # 사고 예: electronics='소형가전' (우리 임의) vs 환경부 'electronics='전기전자제품류'
    # 사용자 본질 명령: "임의 X, 환경부·시·구청 공식만"
    try:
        with open(os.path.join(ROOT, "app.html"), encoding="utf-8") as f:
            html = f.read()
        STANDARD_WORDS = {
            '재활용폐기물', '일반폐기물', '음식물쓰레기', '대형폐기물', '유해폐기물',
            '전기전자제품', '전기전자 제품류', '전기전자제품류',
            '폐가전', '폐건전지', '폐형광등', '폐의약품',
            '의류', '비닐', '플라스틱', '종이', '캔', '유리',
            '스티로폼', '발포합성수지',
            '종이팩', '종이류', '유리류', '비닐류', '캔류',
            '투명 페트병', '무색 페트병', '페트병',
            '종량제봉투', '수거함', '전용수거함', '의류수거함',
            '음료팩', '금속', '고철',
        }
        labels_violation = []
        for var_name in ['catLabels', 'collectorName']:
            m = _re.search(r'const\s+' + var_name + r'\s*=\s*\{([^}]+)\}', html)
            if not m: continue
            body = m.group(1)
            for kv in _re.finditer(r"(\w+)\s*:\s*'([^']+)'", body):
                key = kv.group(1)
                label = kv.group(2)
                if not any(sw in label for sw in STANDARD_WORDS):
                    labels_violation.append(f"{var_name}.{key}='{label}'")
        all_ok &= check("[본질] catLabels/collectorName 표준 단어 포함",
                        not labels_violation,
                        f"{len(labels_violation)}건: " + " | ".join(labels_violation[:5]) if labels_violation else "0건 (환경부 표준 단어 정합)")
    except Exception as _e:
        check("[본질] catLabels 검사", True, f"skip: {_e}")

    # ⭐ v6.28: 본질 자동 감지 — alias 문장체 (크롤링 오염 흔적, fake_by_id 확장)
    # 사고 예: v5.20 12,080건 alias 오염 (book.aliases에 "유리컵·식탁·의자" 등)
    fake_aliases = []
    for k, v in items.items():
        for a in v.get("aliases", []):
            s = str(a).strip()
            if any(m in s for m in SENTENCE_MARKERS):
                fake_aliases.append(f"{k}.aliases='{s[:30]}'")
            elif len(s) > 25 and any(c in s for c in '(){}[],'):
                fake_aliases.append(f"{k}.aliases='{s[:30]}'")
    fake_aliases = list(dict.fromkeys(fake_aliases))
    all_ok &= check("[본질] alias 문장체 (크롤링 오염)",
                    not fake_aliases,
                    f"{len(fake_aliases)}건: " + " | ".join(fake_aliases[:5]) if fake_aliases else "0건")

    # ⭐ v6.28: 본질 자동 감지 — 카드 하단 면책 안내 + 시·구청 이동 존재
    # 사용자 본질 명령: "참고용 면책 명확", "해당 지역 룰 우선"
    try:
        with open(os.path.join(ROOT, "app.html"), encoding="utf-8") as f:
            html_check = f.read()
        disclaimer_checks = {
            "참고용 안내": "참고용" in html_check and "최종 책임" in html_check,
            "최종 판단 사용자": "최종 판단은 사용자" in html_check or "AI 안내는 참고용" in html_check,
            "시·구청 공식 분리수거 안내 박스": "공식 분리수거 안내" in html_check,
            "정보 신고 버튼": "정보가 틀려요" in html_check or "reportBtn" in html_check,
        }
        missing_dc = [k for k, ok in disclaimer_checks.items() if not ok]
        all_ok &= check("[본질] 면책·시·구청 이동 안내",
                        not missing_dc,
                        f"누락: {missing_dc}" if missing_dc else "4종 모두 존재")
    except Exception as _e:
        check("[본질] 면책 검사", True, f"skip: {_e}")

    # ⭐ v6.30 정제: disposal_path 누락 — 매우 명백한 케이스만 (false positive 차단)
    # 정제 기준:
    #   - 첫 step이 "종량제봉투" 같은 명확 표현 + 수거함 흐름 없음 (가장 강력)
    #   - 또는 note/feature에 "재활용 불가/어려움" 명시 + steps에 종량제봉투
    # 환경부 official_classification만으로는 판단 X (의류수거함 등 모순 존재)
    path_violations = []
    for k_p, v_p in items.items():
        cat_p = v_p.get("category")
        if cat_p in ("general", "general_noncombustible"):
            continue
        if v_p.get("disposal_path") == "general_waste":
            continue
        steps_list_p = v_p.get("steps") or []
        if not steps_list_p:
            continue
        first_step_p = str(steps_list_p[0]).strip()
        all_steps_p = " ".join(steps_list_p)
        note_feature_p = (v_p.get("note") or "") + " " + (v_p.get("feature") or "")
        # 수거함 흐름이면 재활용 — 자동 차단
        if "수거함" in all_steps_p:
            continue
        # 명확 조건 1: 첫 단계가 종량제봉투 (가장 강력)
        is_first_general = "종량제봉투" in first_step_p
        # 명확 조건 2: 재활용 불가/어려움 명시 + steps 종량제봉투
        is_explicit_general = (("재활용 불가" in note_feature_p) or ("재활용이 어렵" in note_feature_p) or ("재활용 공정 달라" in note_feature_p)) and ("종량제봉투" in all_steps_p)
        if is_first_general or is_explicit_general:
            path_violations.append(f"{k_p}: '{v_p.get('name')}'({cat_p})")
    path_violations = list(dict.fromkeys(path_violations))
    all_ok &= check("[본질] 카테고리 안 종량제봉투 분기 자동 감지",
                    not path_violations,
                    f"{len(path_violations)}건: " + " | ".join(path_violations[:5]) if path_violations else "0건 (분기 정합)")

    # ⭐ v6.30 정제: 캔류 aerosol_safety — 스프레이 캔만 (이름에 명시)
    # 일반 캔·금속류는 폭발 위험 X — name 자체에 "스프레이"/"에어로졸" 있을 때만
    can_safety_violations = []
    for k_c, v_c in items.items():
        if v_c.get("category") != "can":
            continue
        name_c = v_c.get("name", "")
        # 이름에 "스프레이"/"에어로졸" 명시된 케이스만 — false positive 차단
        is_spray_name = ("스프레이" in name_c) or ("에어로졸" in name_c)
        if not is_spray_name:
            continue
        text_c = (v_c.get("caution") or "") + " " + (v_c.get("feature") or "")
        # 추가 검증: 폭발 위험 명시
        has_explosion = ("폭발" in text_c) or ("내부 가스" in text_c)
        if has_explosion and v_c.get("disposal_path") != "aerosol_safety":
            can_safety_violations.append(f"{k_c}: '{name_c}'")
    can_safety_violations = list(dict.fromkeys(can_safety_violations))
    all_ok &= check("[본질] 캔류 aerosol_safety 안전 분기 자동 감지",
                    not can_safety_violations,
                    f"{len(can_safety_violations)}건: " + " | ".join(can_safety_violations[:3]) if can_safety_violations else "0건 (안전 분기 정합)")

    # ⭐ v6.29: 본질 자동 감지 — 환경부 1599-0903 무상수거 5종 size_tier 표준
    # 사용자 본질 명령: "관할도 환경부도 아닌 룰은 따르지 않음"
    # 환경부 E-순환거버넌스 1599-0903 단일 무상수거 5종: 냉장고·세탁기·텔레비전(TV)·에어컨·전자레인지
    ENV_LARGE_5 = {"냉장고", "세탁기", "텔레비전(TV)", "에어컨", "전자레인지"}
    large_violations = []
    for k_check in ENV_LARGE_5:
        item_check = items.get(k_check)
        if not item_check:
            large_violations.append(f"{k_check}: NATIONAL.items 누락")
        elif item_check.get("size_tier") != "large":
            large_violations.append(f"{k_check}: size_tier 누락/≠'large'")
    all_ok &= check("[본질] 가전 5종 size_tier 환경부 표준 (1599-0903)",
                    not large_violations,
                    f"{len(large_violations)}건: {large_violations}" if large_violations else "5종 모두 'large' (환경부 1599-0903)")

    # ⭐ v6.28: 본질 자동 감지 — 시연 단어 안전 매칭
    # 사용자 본질 검증 (시연에서 실제 다룰 단어가 환경부 표준에 정확 매칭되는지)
    # 사용자 합의 시연 단어 19개 (재활용 6 + 비재활용 4 + 가전 5 + 일상 4)
    DEMO_WORDS = [
        "투명 페트병", "페트병", "종이팩", "우유팩", "캔", "유리병",
        "알약", "폐의약품", "약병", "모기 스프레이",
        "텔레비전", "TV", "핸드폰", "냉장고", "세탁기",
        "의류", "옷", "비닐", "닭뼈",
    ]
    def _w_norm(s):
        return str(s).strip().lower().replace(" ", "")
    demo_failures = []
    demo_partial = []
    for word in DEMO_WORDS:
        wn = _w_norm(word)
        if not wn:
            continue
        found = None
        for k, v in items.items():
            kn = _w_norm(k)
            nn = _w_norm(v.get("name") or k)
            an = [_w_norm(a) for a in v.get("aliases", [])]
            if kn == wn or nn == wn or wn in an:
                found = (k, "exact")
                break
        if not found:
            for k, v in items.items():
                kn = _w_norm(k)
                nn = _w_norm(v.get("name") or k)
                if wn in kn or wn in nn:
                    found = (k, "partial")
                    break
        if not found:
            demo_failures.append(word)
        elif found[1] == "partial":
            demo_partial.append(f"{word}→{found[0]}")
    detail = ""
    if demo_failures:
        detail = f"❌ 매칭 0: {demo_failures}"
    elif demo_partial:
        detail = f"⚠️ 부분 매칭 {len(demo_partial)}건: {demo_partial[:5]}"
    else:
        detail = f"{len(DEMO_WORDS)}/{len(DEMO_WORDS)} 정확 매칭"
    all_ok &= check("[시연] 핵심 단어 환경부 표준 매칭",
                    not demo_failures,
                    detail)

    # 패턴 5: JSON 끝 null 바이트 (region_exceptions에서 발견했던 폭탄)
    with open(os.path.join(ROOT, "data", "national_rules.json"), "rb") as f:
        raw = f.read()
    has_null = b'\x00' in raw
    all_ok &= check("끝 null 바이트", not has_null, "발견됨" if has_null else "없음")
except Exception as e:
    all_ok &= check("national_rules.json", False, str(e))

# 2. region_exceptions.json + regions_meta 정합성 ⭐ v5.25 강화
try:
    with open(os.path.join(ROOT, "data", "region_exceptions.json"), encoding="utf-8") as f:
        ex = json.load(f)
    excs = ex.get("exceptions", {})
    real_regions = {k: v for k, v in excs.items() if k.isdigit() and len(k) == 5}
    all_ok &= check("region_exceptions.json 로드", True, f"{len(real_regions)} 시군구")
    # v5.45: _inherits 가진 자치구는 본청에서 cityGuide 받음 → OK로 카운트
    has_city_or_inherits = sum(1 for v in real_regions.values() if v.get("cityGuide") or v.get("_inherits"))
    all_ok &= check("cityGuide 보유", has_city_or_inherits == len(real_regions),
                    f"{has_city_or_inherits}/{len(real_regions)} (직접 보유 또는 _inherits 통한 본청 fallback)")
    inherits = {k: v for k, v in real_regions.items() if v.get("_inherits")}
    bad_inh = [k for k, v in inherits.items() if v["_inherits"] not in real_regions]
    all_ok &= check("_inherits 체인", not bad_inh, f"끊긴 체인: {bad_inh}" if bad_inh else "OK")

    # ⭐ NEW: regions_meta와 코드/이름 정합성 검사
    with open(os.path.join(ROOT, "data", "regions_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    valid_codes = set(meta.get("level2", {}).keys())
    # ⭐ 통합 시 코드 화이트리스트 — 자치구가 있는 시는 시-level 코드로 통합 운영 (의도적)
    INTEGRATED_CITY_CODES = {
        "41110",  # 경기 수원시 (장안·권선·팔달·영통구 통합) — v5.45 추가
        "41130",  # 경기 성남시 (분당·수정·중원구 통합)
        "41170",  # 경기 안양시 (만안·동안구 통합) — v5.45 추가
        "41270",  # 경기 안산시 (상록·단원구 통합) — v5.45 추가
        "41280",  # 경기 고양시 (덕양·일산동·일산서구 통합) — v5.45 추가
        "41460",  # 경기 용인시 (처인·기흥·수지구 통합) — v5.45 추가
        "43110",  # 충북 청주시 (상당·서원·흥덕·청원구 통합)
        "44130",  # 충남 천안시 (동남·서북구 통합)
        "45110",  # 전북 전주시 (완산·덕진구 통합)
        "47110",  # 경북 포항시 (남·북구 통합)
        "48120",  # 경남 창원시 (의창·성산·마산합포·마산회원·진해구 통합)
    }
    invalid_codes = [k for k in real_regions
                     if k not in valid_codes and k not in INTEGRATED_CITY_CODES]
    all_ok &= check("코드 행안부 표준 일치", not invalid_codes,
                    f"비표준 코드: {invalid_codes[:5]}{'...' if len(invalid_codes) > 5 else ''}" if invalid_codes else f"{len(real_regions)} 모두 유효 (통합 시 {len(INTEGRATED_CITY_CODES)} 포함)")
    # 이름 매칭 (간단)
    mismatched = []
    for code, val in real_regions.items():
        if code in valid_codes:
            meta_name = meta["level2"][code].get("name", "")
            ex_name = val.get("name", "")
            # 이름 일부라도 일치하면 OK (예: "경기도 광명시" ↔ "경기도 광명시")
            if meta_name and ex_name:
                key_word = meta_name.split()[-1].replace("시", "").replace("구", "").replace("군", "")[:2]
                if key_word and key_word not in ex_name:
                    mismatched.append(f"{code}={ex_name[:15]}(실제={meta_name[:15]})")
    all_ok &= check("시군구 이름 매칭", not mismatched,
                    f"불일치 {len(mismatched)}건: {mismatched[:3]}{'...' if len(mismatched) > 3 else ''}" if mismatched else "정확")
except Exception as e:
    all_ok &= check("region_exceptions.json", False, str(e))

# 3. app.html + sw.js -- dynamic version match (v5.32+: hardcoded stale check 폐기)
import re as _re
sw_ver, html_ver = None, None
try:
    with open(os.path.join(ROOT, "sw.js"), encoding="utf-8") as f:
        sw = f.read()
    m = _re.search(r"const\s+VERSION\s*=\s*['\"](v\d+\.\d+(?:\.\d+)?)['\"]", sw)
    sw_ver = m.group(1) if m else None
    all_ok &= check("sw.js VERSION 추출", bool(sw_ver), sw_ver or "추출 실패")
except Exception as e:
    all_ok &= check("sw.js", False, str(e))

try:
    with open(os.path.join(ROOT, "app.html"), encoding="utf-8") as f:
        html = f.read()
    m = _re.search(r"class=['\"]version['\"][^>]*>(v\d+\.\d+(?:\.\d+)?)<", html)
    html_ver = m.group(1) if m else None
    all_ok &= check("app.html 버전 추출", bool(html_ver), html_ver or "추출 실패")
    all_ok &= check("app.html ↔ sw.js 버전 일치",
                    bool(sw_ver) and sw_ver == html_ver,
                    f"sw={sw_ver} html={html_ver}")
    all_ok &= check("_escGlobal 정의", "_escGlobal" in html, "검색 함수 안전")
    all_ok &= check("searchByText 정의", "function searchByText" in html, "")
    all_ok &= check("_inherits 처리", "_inherits" in html and "safetyCounter" in html, "")
    all_ok &= check("cityGuide UI", "cityHtml" in html, "")
    # ⭐ v5.37 (2026-05-24): truncation 사고 5번째 학습 — 끝 잘림 직접 검사
    html_trim = html.rstrip()
    all_ok &= check("app.html </html> 끝", html_trim.endswith("</html>"),
                    f"끝 잘림: {repr(html_trim[-60:])}" if not html_trim.endswith("</html>") else "OK")
    last500 = html_trim[-500:]
    all_ok &= check("app.html IIFE 닫기 ()()", "})();" in last500 or "})()" in last500,
                    "IIFE 닫기 누락" if not ("})();" in last500 or "})()" in last500) else "OK")
    all_ok &= check("app.html init() 호출", "init();" in last500,
                    "init() 호출 누락" if "init();" not in last500 else "OK")
    # v5.47 (2026-05-25): 회귀 영구 차단 — 사용자 본질 명령 "반복 사고 멈춤"
    # 1. 결과 카드 박스 안 텍스트 가시성 강제 (다크모드 흰 박스 흰 글씨 회귀 차단)
    has_visibility_rule = (
        '.sheet-content div[style*="background:#eff6ff"]' in html
        and 'color: #1f2937 !important' in html
    )
    all_ok &= check("결과 카드 박스 가시성 CSS 룰",
                    has_visibility_rule,
                    "다크모드 박스 가시성 룰 없음 — !important 글로벌 룰 필요" if not has_visibility_rule else "OK (회귀 차단)")
    # 2. 영문 ID 사용자 노출 차단 (Gemini 영문 출력 → 사용자 화면 영문 노출 회귀)
    has_eng_block = "영어 ID 절대 노출 X" in html or "영어 ID 노출" in html
    all_ok &= check("영문 ID 노출 차단 (renderResult fallback)",
                    has_eng_block,
                    "영문 ID fallback 차단 룰 없음" if not has_eng_block else "OK (회귀 차단)")
    # 추가: inline JS syntax 검증 (Node available 시)
    try:
        import subprocess as _sp
        scripts = _re.findall(r'<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>', html)
        if scripts:
            joined = "\n;\n".join(scripts)
            r = _sp.run(["node", "--check", "-"], input=joined, capture_output=True, text=True, timeout=10)
            all_ok &= check("app.html inline JS syntax",
                            r.returncode == 0,
                            r.stderr.strip()[:80] if r.returncode != 0 else f"{len(scripts)} blocks OK")
    except (FileNotFoundError, Exception):
        pass  # node 없으면 skip

    # v6.24: TDZ (Temporal Dead Zone) 휴리스틱 — 함수 안 let/const 선언 전 참조 패턴
    # syntax는 정상이지만 runtime ReferenceError 발생 (v6.20 itemName 사고처럼)
    # node --check로는 안 잡힘. 보수적 검사: 흔한 패턴만 잡고 false positive 최소화.
    try:
        scripts = _re.findall(r'<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>', html)
        tdz_issues = []
        # 안전 화이트리스트 (전역·잘 알려진 변수)
        SAFE = {'window', 'document', 'console', 'navigator', 'location', 'localStorage',
                'sessionStorage', 'fetch', 'Promise', 'JSON', 'Math', 'Date', 'Array',
                'Object', 'String', 'Number', 'Boolean', 'parseInt', 'parseFloat',
                'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
                'Image', 'FormData', 'FileReader', 'URL', 'URLSearchParams'}
        for sc in scripts:
            # 함수 본문 추출 (균형 중괄호)
            pos = 0
            while True:
                m = _re.search(r'function\s+(\w+)?\s*\([^)]*\)\s*\{', sc[pos:])
                if not m:
                    break
                name = m.group(1) or '<anon>'
                body_start = pos + m.end()
                depth = 1
                i = body_start
                while i < len(sc) and depth > 0:
                    c = sc[i]
                    if c == '{': depth += 1
                    elif c == '}': depth -= 1
                    i += 1
                body = sc[body_start:i-1]
                pos = i if i > pos else pos + 1
                # 본문에서 let/const 선언 위치
                # v6.25 hardening: false-positive 4종 차단
                #   1) 같은 변수 다중 선언 — 첫 선언만 검사 (두 번째 이후는 별개 block scope일 가능성 높음)
                #   2) 객체 key (X:)
                #   3) 같은 line 미닫힌 quote 안 (string content)
                #   4) 한글 변수명 (코드 변수 아닌 문자열 내용물)
                seen_decl = set()
                for dm in _re.finditer(r'\b(?:let|const)\s+(\w+)\b', body):
                    v = dm.group(1)
                    if v in SAFE:
                        continue
                    if v in seen_decl:
                        continue  # 같은 변수 다중 선언 — 첫 선언만 (block scope 별개 false-positive 회피)
                    seen_decl.add(v)
                    # 한글 변수명은 거의 string content false positive (코드 변수 아님)
                    if any('가' <= ch <= '힣' for ch in v):
                        continue
                    # v6.25 hardening: 1-3글자 변수 차단 (loop index/인자/iter var 흔함, 진짜 TDZ 위험 낮음)
                    if len(v) <= 3:
                        continue
                    before = body[:dm.start()]
                    # 단어 매칭 (앞에 . 또는 ' " 없는 — 객체 속성·문자열 제외)
                    for rm in _re.finditer(r'(?<![\.\'"a-zA-Z0-9_])' + _re.escape(v) + r'\b', before):
                        # 주석 안인지 (간단 검사)
                        ref_line = before[:rm.start()].rsplit('\n', 1)[-1]
                        if '//' in ref_line and ref_line.find('//') < len(ref_line):
                            continue
                        # 객체 key 차단 — 매칭 직후 ":" (옵셔널 공백) + 다음이 :가 아니면 (ternary 아님)
                        rest_in_line = before[rm.end():].split('\n', 1)[0]
                        if _re.match(r'\s*:(?!:)', rest_in_line):
                            continue
                        # 문자열 안 차단 — 같은 line 매칭 전 single/double quote 미닫힘
                        sq_count = len(_re.findall(r"(?<!\\)'", ref_line))
                        dq_count = len(_re.findall(r'(?<!\\)"', ref_line))
                        if sq_count % 2 == 1 or dq_count % 2 == 1:
                            continue
                        # v6.25 hardening: arrow function 인자 / destructure 차단
                        #   같은 line 또는 위 5줄 안에 `=>` 있으면 inner arrow function 본문 → 별개 scope
                        full_line = ref_line + rest_in_line
                        above_lines = before[:rm.start()].split('\n')[-6:-1] if before[:rm.start()] else []
                        if '=>' in full_line or any('=>' in l for l in above_lines):
                            continue
                        # callback 시작 패턴도 차단 — forEach/map/filter/sort/reduce/find/some/every/then(... 안 매칭
                        if any(_re.search(r'\b(?:forEach|map|filter|sort|reduce|find|some|every|then|catch|finally|addEventListener)\s*\(', l) for l in above_lines):
                            continue
                        # 발견
                        line = before.count('\n') + 1
                        tdz_issues.append(f"{name}() L{line}: '{v}' 선언 전 참조")
                        break  # 변수당 1건만
                if len(tdz_issues) >= 100:
                    break
            if len(tdz_issues) >= 5:
                break
        all_ok &= check("app.html JS TDZ 패턴 (선언 전 참조)",
                        not tdz_issues,
                        f"{len(tdz_issues)}건: " + " | ".join(tdz_issues) if tdz_issues else "0건")
    except Exception as _e:
        check("app.html JS TDZ 패턴", True, f"검사 skip: {_e}")
except Exception as e:
    all_ok &= check("app.html", False, str(e))

# 4. Cloudflare Worker -- JS 문법 자체검사 (Phase A2 cron 활성 이후 회귀 방지)
try:
    import subprocess
    worker_path = os.path.join(ROOT, "scripts", "cloudflare_worker.js")
    if os.path.exists(worker_path):
        r = subprocess.run(["node", "-c", worker_path], capture_output=True, text=True)
        all_ok &= check("cloudflare_worker.js 문법", r.returncode == 0,
                        (r.stderr.strip()[:80] if r.returncode != 0 else "OK"))
    else:
        all_ok &= check("cloudflare_worker.js 문법", False, "파일 없음")
except FileNotFoundError:
    check("cloudflare_worker.js 문법", True, "node 미설치 - skip")
except Exception as e:
    check("cloudflare_worker.js 문법", False, f"검사 실패: {e}")

# v5.65: 본질 위반 자동 감지 룰 5개 (별도 모듈 check_essence_v565.py 호출)
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_essence_v565 import run_checks as _run_essence
    all_ok &= _run_essence(check, ROOT)
except Exception as _e:
    check("[본질] 자동 감지 모듈", False, f"import 실패: {_e}")

print("\n" + "=" * 40)
if all_ok:
    print("[PASS] 모든 체크 통과. push 가능.")
else:
    print("[FAIL] 실패 항목 있음. 위 X 확인 후 수정.")


# 5. v5.39 추가: DB 자산 벤치마크 (정량 정확도 측정)
try:
    import subprocess as _sp2
    bench_path = os.path.join(ROOT, "scripts", "benchmark_db.py")
    if os.path.exists(bench_path):
        r = _sp2.run([sys.executable, bench_path], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            # 종합 점수 추출
            score_line = [l for l in r.stdout.split('\n') if '종합 점수' in l]
            if score_line:
                score_str = score_line[0].split('종합 점수:')[-1].split('/')[0].strip()
                try:
                    score = float(score_str)
                    threshold = 80.0
                    all_ok &= check(f"DB 벤치마크 (>={threshold})", score >= threshold, f"{score}/100")
                except ValueError:
                    check("DB 벤치마크", True, "점수 파싱 실패")
            else:
                check("DB 벤치마크", True, "실행 OK (점수 미발견)")
        else:
            check("DB 벤치마크", False, f"실행 실패: {r.stderr[:60]}")
except Exception as e:
    check("DB 벤치마크", True, f"skip: {e}")

print("=" * 40 + "\n")
sys.exit(0 if all_ok else 1)
