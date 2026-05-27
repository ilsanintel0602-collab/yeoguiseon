"""
본질 위반 영구 차단 룰 (v5.51~v5.65 사이클에서 발견된 패턴 자동화)
quick_check.py에서 호출. 매 push마다 자동 차단.
"""
import json, os


def run_checks(check, ROOT):
    """check(name, ok, detail) 헬퍼 받아 5개 룰 검사. all_ok 누적 반환."""
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
    except Exception as e:
        check("[본질] 자동 감지 실행", False, f"검사 실패: {e}")
        all_ok = False
    return all_ok
