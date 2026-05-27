"""
본질 위반 영구 차단 룰 (v5.51~v5.75 사이클에서 발견된 패턴 자동화)
quick_check.py에서 호출. 매 push마다 자동 차단.
"""
import json, os


def run_checks(check, ROOT):
    """check(name, ok, detail) 헬퍼 받아 16개 룰 검사. all_ok 누적 반환."""
    all_ok = True
    try:
        r = json.load(open(os.path.join(ROOT, "data", "region_exceptions.json"), encoding="utf-8"))
        n = json.load(open(os.path.join(ROOT, "data", "national_rules.json"), encoding="utf-8"))
        b = json.load(open(os.path.join(ROOT, "data", "bag_prices.json"), encoding="utf-8"))
        ex = r.get("exceptions", {})
        items = n.get("items", {})

        # ① itemExceptions source_url 누락 차단 (정직성 — source_url 필수 룰)
        no_src = []
        for c, info in ex.items():
            if not isinstance(info, dict):
                continue
            for iid, ct in (info.get("exceptions") or {}).items():
                if isinstance(ct, dict) and not (ct.get("source") or ct.get("source_url")):
                    no_src.append(f"{c}/{iid}")
        all_ok &= check("[본질①] itemExceptions source_url 누락 차단", len(no_src) == 0,
                        f"{len(no_src)}건: {no_src[:3]}" if no_src else "0건")

        # ② phones 중복 (대표 = 부서, 잘못된 마이그레이션) 차단
        dup = []
        for c, info in ex.items():
            if not isinstance(info, dict):
                continue
            ph = info.get("cityGuide", {}).get("phones") or {}
            if not isinstance(ph, dict):
                continue
            mk = None
            for k in ph:
                if ("구청대표" in k) or ("시청대표" in k) or ("군청대표" in k):
                    mk = k
                    break
            if not mk:
                continue
            for k, v in ph.items():
                if k != mk and v == ph[mk]:
                    dup.append(f"{c}/{k}={mk}")
        all_ok &= check("[본질②] phones 중복(대표=부서) 차단", len(dup) == 0,
                        f"{len(dup)}건: {dup[:3]}" if dup else "0건")

        # ③ bag_prices 첫 bag 특수규격마대 차단 (벌금 위험 — 일반 봉투 우선)
        bad = []
        for c, info in b.get("data", {}).items():
            if not isinstance(info, dict):
                continue
            bags = info.get("bags")
            if isinstance(bags, list) and bags:
                if "특수" in str(bags[0].get("종류", "")):
                    bad.append(c)
        all_ok &= check("[본질③] bag_prices 첫 bag 특수규격마대 차단 (벌금 위험)", len(bad) == 0,
                        f"{len(bad)}건: {bad[:3]}" if bad else "0건")

        # ④ knownVariations 특정 구 직접 언급 차단 (지역 일반화 강제)
        SPECIFIC = ["강남구", "강서구", "노원구", "송파구", "강동구", "서초구",
                    "성동구", "광진구", "마포구", "양천구", "은평구", "관악구", "영등포구"]
        kv = []
        for iid, item in items.items():
            if not isinstance(item, dict):
                continue
            v = item.get("knownVariations", "")
            for g in SPECIFIC:
                if g in v:
                    kv.append(f"{iid}/{g}")
                    break
        all_ok &= check("[본질④] knownVariations 특정 구 언급 차단 (일반화)", len(kv) == 0,
                        f"{len(kv)}건: {kv[:3]}" if kv else "0건")

        # ⑤ cityGuide.phone(string) 잔존 차단 (phones 객체 표준)
        ps = []
        for c, info in ex.items():
            if not isinstance(info, dict):
                continue
            p = info.get("cityGuide", {}).get("phone")
            if isinstance(p, str) and p:
                ps.append(c)
        all_ok &= check("[본질⑤] cityGuide.phone(string) 차단 (phones 객체 표준)", len(ps) == 0,
                        f"{len(ps)}건: {ps[:3]}" if ps else "0건")

        # ⑥ cityGuide.phones에 시청/구청/군청대표 라벨 차단 (regions_meta.phone과 중복)
        dup_main = []
        for c, info in ex.items():
            if not isinstance(info, dict):
                continue
            ph = info.get("cityGuide", {}).get("phones") or {}
            if not isinstance(ph, dict):
                continue
            for label in ("시청대표", "구청대표", "군청대표"):
                if label in ph:
                    dup_main.append(f"{c}/{label}")
        all_ok &= check("[본질⑥] cityGuide.phones 대표 라벨 차단 (regions_meta와 중복)", len(dup_main) == 0,
                        f"{len(dup_main)}건: {dup_main[:3]}" if dup_main else "0건")

        # v5.68: cross-reference 자동 검증 (⑦⑧⑨)
        m = json.load(open(os.path.join(ROOT, "data", "regions_meta.json"), encoding="utf-8"))
        meta_codes = set(m.get("level2", {}).keys())
        ex_codes = set(ex.keys())
        bp_codes = set(b.get("data", {}).keys())

        # ⑦ regions_meta ↔ region_exceptions 코드 정합성
        sym_diff_7 = (meta_codes ^ ex_codes)
        all_ok &= check("[본질⑦] regions_meta ↔ region_exceptions 코드 정합성", len(sym_diff_7) == 0,
                        f"{len(sym_diff_7)}건: {sorted(sym_diff_7)[:3]}" if sym_diff_7 else "261/261")

        # ⑧ bag_prices ↔ regions_meta 코드 정합성
        sym_diff_8 = (meta_codes ^ bp_codes)
        all_ok &= check("[본질⑧] bag_prices ↔ regions_meta 코드 정합성", len(sym_diff_8) == 0,
                        f"{len(sym_diff_8)}건: {sorted(sym_diff_8)[:3]}" if sym_diff_8 else f"{len(bp_codes)}/{len(meta_codes)}")

        # ⑨ itemExceptions 카테고리 ↔ national_rules enum
        valid_cats = set()
        for it in items.values():
            if isinstance(it, dict) and it.get("category"):
                valid_cats.add(it["category"])
        bad_cats = []
        for c, info in ex.items():
            if not isinstance(info, dict):
                continue
            for iid, ct in (info.get("exceptions") or {}).items():
                if isinstance(ct, dict):
                    cat = ct.get("category")
                    if cat and cat not in valid_cats:
                        bad_cats.append(f"{c}/{iid}={cat}")
        all_ok &= check("[본질⑨] itemExceptions 카테고리 enum 일치", len(bad_cats) == 0,
                        f"{len(bad_cats)}건: {bad_cats[:3]}" if bad_cats else "0건")

        # ⑩ app.html script src 참조 파일 존재 확인 (404 차단, v5.48 회귀 영구 방지)
        import re as _re
        app_path = os.path.join(ROOT, "app.html")
        if os.path.exists(app_path):
            with open(app_path, "r", encoding="utf-8") as _f:
                _app = _f.read()
            local_srcs = [_m.group(1) for _m in _re.finditer(r'<script\s+src="(\./[^"]+)"', _app)]
            missing_srcs = []
            for _s in local_srcs:
                _p = os.path.join(ROOT, _s.lstrip("./"))
                if not os.path.exists(_p):
                    missing_srcs.append(_s)
            all_ok &= check("[본질⑩] app.html script src 파일 존재 (404 차단)",
                            len(missing_srcs) == 0,
                            f"{len(missing_srcs)}건 누락: {missing_srcs[:3]}" if missing_srcs else f"{len(local_srcs)}개 OK")

        # ⑪ bag_prices isHeadOffice 정합성 (본청 vs 자치구 구조 검증)
        bp_inconsistent = []
        for c, info in b.get("data", {}).items():
            if not isinstance(info, dict):
                continue
            is_ho = info.get("isHeadOffice", False)
            has_bags = bool(info.get("bags"))
            inherits = info.get("inheritsFrom")
            if is_ho and has_bags:
                bp_inconsistent.append(f"{c} 본청인데 bags")
            elif not is_ho and not has_bags and not inherits:
                bp_inconsistent.append(f"{c} 자치구인데 데이터 없음")
        all_ok &= check("[본질⑪] bag_prices 본청·자치구 구조 정합성", len(bp_inconsistent) == 0,
                        f"{len(bp_inconsistent)}건: {bp_inconsistent[:3]}" if bp_inconsistent else "0건")

        # ⑬ items category vs note 모순 자동 감지 (v5.75 텀블러 케이스 영구 차단)
        AMBIG_KW = ["재질 확인", "재질이 다양", "재질이 다름", "재질에 따라",
                    "두 종류", "여러 재질", "종류가 다"]
        ambig_violations = []
        for iid, it in items.items():
            if not isinstance(it, dict):
                continue
            note = it.get("note", "") or ""
            cat = it.get("category", "")
            if not note or not cat:
                continue
            if cat in ("other", "general", "general_or_bulky", "general_noncombustible"):
                continue
            for kw in AMBIG_KW:
                if kw in note and not it.get("multi_material"):
                    ambig_violations.append(f"{iid}({cat})")
                    break
        all_ok &= check("[본질⑫] items category vs note 모순 차단 (multi_material flag 강제)",
                        len(ambig_violations) == 0,
                        f"{len(ambig_violations)}건: {ambig_violations[:3]}" if ambig_violations else "0건")

        # ⑭ items 이름이 'X의 재질' / 'X 재질' 패턴이면 multi_material:true 강제
        meta_items = []
        for iid, it in items.items():
            if not isinstance(it, dict):
                continue
            name = it.get("name", "") or iid
            if ("의 재질" in name or name.endswith("재질")) and not it.get("multi_material"):
                meta_items.append(name)
        all_ok &= check("[본질⑬] '재질' 메타 items multi_material:true 강제",
                        len(meta_items) == 0,
                        f"{len(meta_items)}건: {meta_items[:3]}" if meta_items else "0건")

        # ⑮ regions_meta boundingBox 동일 4튜플 중복 차단 (잘못 복제 감지)
        bbox_seen = {}
        bbox_dup = []
        for c, info in m.get("level2", {}).items():
            bb = info.get("boundingBox")
            if not bb:
                continue
            key = (bb.get("minLat"), bb.get("maxLat"), bb.get("minLng"), bb.get("maxLng"))
            if None in key:
                continue
            if key in bbox_seen:
                name1 = m["level2"][bbox_seen[key]].get("name", bbox_seen[key])
                name2 = info.get("name", c)
                bbox_dup.append(f"{name1}({bbox_seen[key]}) = {name2}({c})")
            else:
                bbox_seen[key] = c
        all_ok &= check("[본질⑭] regions_meta boundingBox 동일 복제 차단 (잘못 복제 감지)",
                        len(bbox_dup) == 0,
                        f"{len(bbox_dup)}건: {bbox_dup[:3]}" if bbox_dup else f"{len(bbox_seen)}개 unique")

        # ⑯ SYSTEM_PROMPT external + inline fallback 동시 존재 강제 (v5.69 회귀 영구 차단)
        if os.path.exists(app_path):
            has_ext = '<script src="./js/prompts.js"></script>' in _app
            has_fallback = "if (typeof SYSTEM_PROMPT === 'undefined')" in _app
            sp_ok = has_ext and has_fallback
            all_ok &= check("[본질⑮] SYSTEM_PROMPT external+inline fallback 강제 (v5.69 회귀 차단)",
                            sp_ok, f"external={has_ext} fallback={has_fallback}")

        # ⑰ items aliases 중복 차단 (검색 충돌 영구 방지)
        alias_owner = {}
        alias_dup = []
        for iid, it in items.items():
            if not isinstance(it, dict):
                continue
            for a in (it.get("aliases", []) or []):
                a_norm = str(a).strip().lower()
                if not a_norm:
                    continue
                if a_norm in alias_owner:
                    alias_dup.append(f'"{a}": {alias_owner[a_norm]} ↔ {iid}')
                else:
                    alias_owner[a_norm] = iid
        all_ok &= check("[본질⑯] items aliases 중복 차단 (검색 충돌 영구 방지)",
                        len(alias_dup) == 0,
                        f"{len(alias_dup)}건: {alias_dup[:3]}" if alias_dup else f"{len(alias_owner)}개 unique")

        # ⑰ items sourceUrl 결측 차단 (정직성·출처 필수 — 사용자 본질 명령)
        no_src_url = []
        for iid, it in items.items():
            if not isinstance(it, dict):
                continue
            if not it.get("sourceUrl"):
                no_src_url.append(iid)
        all_ok &= check("[본질⑰] items sourceUrl 결측 차단 (정직성 — 출처 필수)",
                        len(no_src_url) == 0,
                        f"{len(no_src_url)}건: {no_src_url[:3]}" if no_src_url else f"{len(items)}개 모두 출처 있음")

        # ⑱ sw.js APP_SHELL ↔ app.html script src 정합성 (v5.69 SYSTEM_PROMPT 회귀 영구 차단)
        sw_path = os.path.join(ROOT, "sw.js")
        if os.path.exists(app_path) and os.path.exists(sw_path):
            with open(sw_path, "r", encoding="utf-8") as _f:
                _sw = _f.read()
            app_modules = sorted(set(_re.findall(r'<script\s+src="\./(js/[^"]+)"', _app)))
            shell_match = _re.search(r'const\s+APP_SHELL\s*=\s*\[(.*?)\]', _sw, _re.DOTALL)
            shell_modules = []
            if shell_match:
                shell_modules = sorted(set(_re.findall(r"['\"]\./(js/[^'\"]+)['\"]", shell_match.group(1))))
            missing_in_shell = [m for m in app_modules if m not in shell_modules]
            all_ok &= check("[본질⑱] sw.js APP_SHELL ↔ app.html script src 정합성 (PWA 오프라인 차단)",
                            len(missing_in_shell) == 0,
                            f"{len(missing_in_shell)}건 sw.js APP_SHELL 누락: {missing_in_shell}" if missing_in_shell else f"{len(app_modules)}/{len(app_modules)}개 정합")

        # ⑲ 경쟁사 직접 언급 차단 (라이브 + scripts + js, GitHub 공개 평판 보호)
        # 검사 대상: app.html, sw.js, scripts/*.py, js/*.js (docs/HANDOFF*는 과거 기록이라 예외)
        # 키워드 동적 생성 (자기 파일에 직접 문자열 회피)
        _base = chr(82)+chr(101)+chr(99)+chr(121)+chr(99)+chr(108)+chr(101)
        COMPETITOR_KW = [_base+"AI", _base+"Ai", _base.lower()+"ai", _base.upper()+"AI"]
        SELF_FILE = "check_essence_v565.py"
        target_files = [app_path, sw_path]
        for sub in ["scripts", "js"]:
            sub_path = os.path.join(ROOT, sub)
            if os.path.isdir(sub_path):
                for fn in os.listdir(sub_path):
                    if fn.endswith((".py", ".js")) and fn != SELF_FILE:
                        target_files.append(os.path.join(sub_path, fn))
        leaks = []
        for fpath in target_files:
            if not os.path.exists(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as _f:
                    _txt = _f.read()
                for kw in COMPETITOR_KW:
                    if kw in _txt:
                        leaks.append(f"{os.path.basename(fpath)}:{kw}")
                        break
            except Exception:
                pass
        all_ok &= check("[본질⑲] 경쟁사 직접 언급 차단 (GitHub 공개 평판 보호)",
                        len(leaks) == 0,
                        f"{len(leaks)}건: {leaks[:3]}" if leaks else f"{len(target_files)}개 파일 깨끗")

        # ⑳ 금액·법적 정책 안내 검증 (자극적 거짓정보 차단)
        # note/feature/caution에 금액·환급·보증금 키워드 → policyScope/policySourceUrl/policyLastVerified 필수
        POLICY_KW = ["원 환급", "원 보증금", "보증금제", "자원순환보증금"]
        policy_violations = []
        for iid, it in items.items():
            if not isinstance(it, dict):
                continue
            combined = " ".join([
                str(it.get("note", "")),
                str(it.get("feature", "")),
                str(it.get("caution", "")),
            ])
            has_policy = any(kw in combined for kw in POLICY_KW)
            if has_policy:
                missing = []
                if not it.get("policyScope") and "세종" not in combined and "제주" not in combined and "일부 매장" not in combined:
                    missing.append("policyScope/시행범위")
                if not it.get("policySourceUrl") and not it.get("sourceUrl"):
                    missing.append("policySourceUrl")
                if missing:
                    policy_violations.append(f"{iid}: {missing}")
        all_ok &= check("[본질⑳] 금액·정책 안내 검증 (시행범위·출처 필수, 거짓정보 차단)",
                        len(policy_violations) == 0,
                        f"{len(policy_violations)}건: {policy_violations[:3]}" if policy_violations else "0건")

        # ㉑ 일반화·단정 표현 차단 (자극적 안내 영구 방지)
        # "전국 모든 매장·반드시 환급·100% 환급·언제나" 같은 단정 표현 차단
        ABS_KW = ["전국 모든 매장", "모든 매장에서 환급", "반드시 환급", "100% 환급", "언제나 환급", "어디서나 환급"]
        abs_violations = []
        for iid, it in items.items():
            if not isinstance(it, dict):
                continue
            combined = " ".join([
                str(it.get("note", "")),
                str(it.get("feature", "")),
                str(it.get("caution", "")),
            ])
            for kw in ABS_KW:
                if kw in combined:
                    abs_violations.append(f"{iid}: \"{kw}\"")
                    break
        all_ok &= check("[본질㉑] 일반화·단정 표현 차단 (자극적 안내 영구 방지)",
                        len(abs_violations) == 0,
                        f"{len(abs_violations)}건: {abs_violations[:3]}" if abs_violations else "0건")
    except Exception as e:
        check("[본질] 자동 감지 실행", False, f"검사 실패: {e}")
        all_ok = False
    return all_ok
