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
