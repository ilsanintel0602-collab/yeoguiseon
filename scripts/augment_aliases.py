#!/usr/bin/env python3
"""
🎯 진짜 자동 데이터 증강 (Data Augmentation) — Gemini 기반

수동 alias 추가 방식 폐기. 한 번 실행으로 765 items × 10~20 = 약 10,000+ alias 자동 생성.

작동 흐름:
  1. national_rules.json 765 items 로드
  2. 각 item의 name + category + 기존 aliases → Gemini에 전달
  3. Gemini가 동의어·변형·구어체·외래어·유아어·지역어 자동 생성
  4. 검증 (오염 차단, 중복 제거)
  5. 자동 aliases에 추가

증강 영역 (각 item별 Gemini 요청):
  - 한국어 변형 (예: "노트북" → "랩탑", "맥북", "삼성노트북")
  - 외래어/영어 (예: "프린터" → "printer", "프린트기")
  - 구어체 (예: "냉장고" → "냉장", "내장고")
  - 유아어/방언 (예: "기저귀" → "기저구", "다이어퍼")
  - 약자/줄임말 (예: "에어컨" → "에어컨디셔너", "AC")

비용 추정:
  - 765 items × 1 Gemini Flash 호출 = 765 호출
  - 응답당 약 200~500 토큰 = 평균 300 토큰
  - Gemini 2.0 Flash 가격: $0.075 / 1M 토큰 (입력), $0.30 / 1M 토큰 (출력)
  - 총 비용: 약 0.1 USD (≈ 130원) 한 번 실행

사용 (사용자 PC):
  python scripts/augment_aliases.py                 # 기본: Worker /augment (키 노출 0)
  python scripts/augment_aliases.py --dry --limit 5 # 처음 5개만 미리보기
  python scripts/augment_aliases.py --limit 50      # 50개만 처리
  python scripts/augment_aliases.py --direct --api-key <KEY>  # 직접 Gemini (테스트용)
"""
import json
import os
import sys
import time
import re
import urllib.request
import urllib.error
import shutil
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
NAT = os.path.join(ROOT, "data", "national_rules.json")
WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev"

VALID_CATEGORIES = {
    "plastic", "paper", "paper_pack", "vinyl", "can", "glass", "styrofoam",
    "food", "general", "battery", "lamp", "clothes", "electronics",
    "furniture", "hazardous", "medicine", "reusable",
}

PROMPT_TEMPLATE = """한국 분리수거 앱의 데이터 증강 작업입니다.

물건: "{name}"
카테고리: {category}
기존 별칭: {existing_aliases}

이 물건의 다양한 한국어 표현을 12개 생성해주세요. 다음 종류를 골고루:
1. 한국어 변형/동의어 (예: 노트북 → 랩탑)
2. 영어/외래어 (예: 프린터 → printer)
3. 구어체/줄임말 (예: 냉장고 → 냉장이)
4. 브랜드명·일반명 (예: 신라면, 삼다수)
5. 유아어·방언 (예: 우유팩 → 우유 통)

규칙:
- 기존 별칭과 중복 안 됨
- 다른 카테고리와 혼동 안 됨 (예: 음식물 → 종이 절대 안 됨)
- 너무 짧은 단어(2자 이하) 피하기
- JSON 배열만 응답: ["단어1", "단어2", ...]

JSON 응답만:"""


def call_worker(name, category, existing_aliases, count=12):
    """Cloudflare Worker /augment 호출 — API 키 노출 0 (Worker 환경변수 사용)"""
    url = f"{WORKER_URL}/augment"
    payload = json.dumps({
        "item_name": name,
        "category": category,
        "existing_aliases": existing_aliases[:5] if existing_aliases else [],
        "count": count,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": "https://ilsanintel0602-collab.github.io",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("ok") and isinstance(data.get("aliases"), list):
            return data["aliases"]
        print(f"  [Worker err] {name}: {data.get('error', 'unknown')}")
        return []
    except Exception as e:
        print(f"  [Worker err] {name}: {e}")
        return []


def call_gemini_direct(api_key, name, category, existing_aliases):
    """Gemini API 직접 호출 (API 키 필요)"""
    prompt = PROMPT_TEMPLATE.format(
        name=name,
        category=category,
        existing_aliases=", ".join(existing_aliases[:5]) if existing_aliases else "없음",
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 512,
            "temperature": 0.7,
        },
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 응답 정리 시도
            m = re.search(r"\[.*?\]", text, re.DOTALL)
            if m:
                try: return json.loads(m.group(0))
                except: pass
            return []
    except Exception as e:
        print(f"  [ERR] {name}: {e}")
        return []


def validate_aliases(new_aliases, name, category, all_known):
    """증강된 alias 검증 (오염 차단)"""
    out = []
    for a in new_aliases:
        if not isinstance(a, str): continue
        a = a.strip()
        if len(a) < 2: continue  # 너무 짧음
        if len(a) > 30: continue  # 너무 김
        if a in all_known: continue  # 이미 있음
        if a == name: continue
        # 카테고리 충돌 검사 (단순 — 다른 카테고리 명확 단어 차단)
        BAD_CROSS = {
            "plastic": ["종이", "유리", "캔", "음식", "밥"],
            "paper": ["페트병", "플라스틱", "캔", "유리"],
            "food": ["플라스틱", "유리", "캔", "전자"],
            "battery": ["옷", "책", "음식", "유리병"],
        }
        bad = BAD_CROSS.get(category, [])
        if any(b in a for b in bad):
            continue
        out.append(a)
    return out


def main():
    args = sys.argv[1:]
    api_key = None
    dry_run = "--dry" in args
    limit = None
    direct = "--direct" in args  # 직접 Gemini 호출 (테스트용, 키 필요)

    for i, a in enumerate(args):
        if a == "--api-key" and i + 1 < len(args):
            api_key = args[i + 1]
        elif a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    # 기본: Worker /augment (키 노출 0)
    # --direct 옵션일 때만 API 키 필요
    if direct:
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(__doc__)
            print("\n[ERR] --direct 모드는 --api-key 또는 환경변수 GEMINI_API_KEY 필요")
            print("⚠️  키 노출 위험: 일반 사용자는 --direct 빼고 실행하세요.")
            return
        print(f"⚠️  --direct 모드 — Gemini API 직접 호출 (키 사용)\n")
    else:
        print(f"✓ Worker 모드 — {WORKER_URL}/augment (키 노출 0)\n")

    # 백업
    BAK = NAT + ".backup_pre_augment.json"
    if not dry_run and not os.path.exists(BAK):
        shutil.copy(NAT, BAK)

    with open(NAT, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]

    # 전체 알려진 단어 (오염 검사용)
    all_known = set()
    for k, v in items.items():
        all_known.add(k)
        n = v.get("name")
        if n: all_known.add(n.strip())
        for a in (v.get("aliases") or []):
            all_known.add(a.strip())
    print(f"기존 known terms: {len(all_known)}")
    print(f"items: {len(items)}")
    print(f"DRY={dry_run}, limit={limit}\n")

    target_items = list(items.items())
    if limit:
        target_items = target_items[:limit]

    total_added = 0
    for i, (key, item) in enumerate(target_items, 1):
        name = item.get("name", key)
        category = item.get("category", "general")
        existing = item.get("aliases") or []

        if category not in VALID_CATEGORIES:
            continue

        print(f"[{i}/{len(target_items)}] {name} ({category}) — 현재 {len(existing)} aliases")

        # Gemini 호출 (Worker 기본, --direct만 직접)
        if direct:
            new_aliases = call_gemini_direct(api_key, name, category, existing)
        else:
            new_aliases = call_worker(name, category, existing)
        if not new_aliases:
            time.sleep(0.5)
            continue

        # 검증
        valid = validate_aliases(new_aliases, name, category, all_known)
        if not valid:
            print(f"  생성 {len(new_aliases)} → 검증 통과 0")
            continue

        # 추가
        if not dry_run:
            for v_alias in valid:
                existing.append(v_alias)
                all_known.add(v_alias)
            item["aliases"] = sorted(set(existing))

        total_added += len(valid)
        print(f"  + {len(valid)}개 추가: {valid[:5]}{'...' if len(valid) > 5 else ''}")

        # rate limit (Gemini API)
        time.sleep(0.3)

    # 저장
    if not dry_run:
        with open(NAT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n저장 완료. 추가된 alias: {total_added}건")
    else:
        print(f"\n[dry-run] 추가될 alias: {total_added}건 (저장 안 함)")


if __name__ == "__main__":
    main()
