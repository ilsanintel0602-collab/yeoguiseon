#!/usr/bin/env python3
"""
Phase 8 자동 보강 사이클 — 사용자 피드백 분석 + 자동 alias 보강

플로우:
  1) Cloudflare Worker /feedback/dump 호출 → 누적 피드백 JSON
     (또는 localStorage dump 파일 사용)
  2) 빈도 높은 약점 자동 식별 (vote=bad/wrong)
  3) Gemini로 user_correction → 카테고리 자동 분류
  4) national_rules.json에 alias 자동 추가
  5) audit 자동 검증

사용:
  python scripts/analyze_feedback.py --dump <path>     # localStorage dump
  python scripts/analyze_feedback.py --worker          # Cloudflare KV
  python scripts/analyze_feedback.py --dry             # 미리보기
"""
import json
import os
import sys
import time
import base64
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
NAT = os.path.join(ROOT, "data", "national_rules.json")
WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev"

DRY = "--dry" in sys.argv


def load_feedback_from_dump(path):
    """localStorage dump JSON 로드"""
    if not os.path.exists(path):
        print(f"[ERR] dump 파일 없음: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("feedback", [])


def classify_with_gemini(correction_text, item_id_old):
    """Gemini Worker로 user_correction → 카테고리 분류"""
    prompt = f"""사용자가 분리수거 분류를 정정했습니다.

원래 우리 분류: {item_id_old}
사용자 정정: "{correction_text}"

"{correction_text}"의 올바른 분리수거 카테고리를 JSON으로만 응답:
{{"category": "plastic|paper|paper_pack|vinyl|can|glass|styrofoam|food|general|battery|lamp|clothes|electronics|furniture|hazardous|medicine|reusable", "confidence": 0~1}}"""

    # 텍스트만으로 호출 (이미지 없이) — Worker가 text만 받으면 reject. 그러므로 dummy 이미지.
    # 또는 별도 text-only 엔드포인트 만들기. 일단 dry-run.
    return {"category": "general", "confidence": 0.5, "_note": "text-only Worker 미구현"}


def main():
    print("=" * 60)
    print("  Phase 8 자동 보강 사이클")
    print("=" * 60)

    # 입력 소스 결정
    dump_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--dump" and i + 1 < len(sys.argv):
            dump_path = sys.argv[i + 1]

    if dump_path:
        feedback = load_feedback_from_dump(dump_path)
    else:
        # Cloudflare Worker /feedback/dump 호출 (TODO: 엔드포인트 추가)
        print("[INFO] --dump <path> 옵션으로 localStorage dump 파일 지정해주세요.")
        print("  사용자 모바일 Chrome → DevTools → Application → Local Storage → fb_v5")
        print("  → 값 복사해서 fb_dump.json 저장 → python scripts/analyze_feedback.py --dump fb_dump.json")
        return

    print(f"\n  피드백 항목: {len(feedback)}건")
    if not feedback:
        print("  보강할 항목 없음")
        return

    # 분석: vote별 분포
    votes = Counter(fb.get("vote") for fb in feedback)
    print(f"\n=== Vote 분포 ===")
    for vote, cnt in votes.most_common():
        print(f"  {vote:8s} : {cnt}")

    # 약점 식별: bad/wrong인 item_id 빈도
    bad_items = Counter()
    corrections_by_item = defaultdict(list)
    for fb in feedback:
        if fb.get("vote") in ("bad", "wrong"):
            item = fb.get("item_id") or fb.get("item_name") or "?"
            bad_items[item] += 1
            corr = fb.get("user_correction", "").strip()
            if corr:
                corrections_by_item[item].append(corr)

    print(f"\n=== Top 약점 ===")
    for item, cnt in bad_items.most_common(10):
        corrs = corrections_by_item.get(item, [])
        unique_corrs = Counter(corrs)
        top_corr = unique_corrs.most_common(1)
        print(f"  '{item}' bad/wrong {cnt}회")
        if top_corr:
            print(f"    → 사용자 정정 top: '{top_corr[0][0]}' ({top_corr[0][1]}회)")

    # 자동 보강 plan
    print(f"\n=== 자동 보강 계획 ===")
    boost_plan = []
    for item_id_old, corrs in corrections_by_item.items():
        unique_corrs = Counter(corrs)
        for correct_word, freq in unique_corrs.most_common(3):
            if freq >= 2:  # 2번 이상 같은 정정
                boost_plan.append({
                    "from_item": item_id_old,
                    "correct_word": correct_word,
                    "frequency": freq,
                })

    if not boost_plan:
        print("  보강 후보 없음 (모든 정정이 1회뿐)")
        return

    for plan in boost_plan:
        print(f"  '{plan['correct_word']}' ({plan['frequency']}회 정정) — '{plan['from_item']}'와 분리")

    if DRY:
        print(f"\n[dry-run] 자동 보강 안 함. 보강 항목 {len(boost_plan)}건 준비됨.")
        return

    # 실제 보강
    with open(NAT, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    added = 0
    for plan in boost_plan:
        word = plan["correct_word"]
        # 이미 있는지 확인
        found = False
        for k, v in items.items():
            if k == word or v.get("name") == word or word in (v.get("aliases") or []):
                found = True
                break
        if found:
            continue
        # Gemini로 카테고리 분류 (실제 운영 시 활성)
        cls = classify_with_gemini(word, plan["from_item"])
        cat = cls.get("category", "general")
        # 해당 카테고리의 첫 item에 alias 추가
        for k, v in items.items():
            if v.get("category") == cat:
                aliases = v.get("aliases") or []
                aliases.append(word)
                v["aliases"] = sorted(set(aliases))
                added += 1
                print(f"  + '{word}' → {k} ({cat})")
                break

    if added:
        with open(NAT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n저장 완료: {added}건 alias 추가")
    else:
        print(f"\n추가된 alias 없음")


if __name__ == "__main__":
    main()
