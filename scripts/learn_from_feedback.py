#!/usr/bin/env python3
"""
Phase F: 사용자 피드백 학습 루프
================================================================

Worker /feedback/dump → 잘못된 매칭 케이스 추출 → alias 보강 제안

사용:
    export FEEDBACK_DUMP_KEY=<your-key>
    python scripts/learn_from_feedback.py

흐름:
1. Worker /feedback/dump 호출 (KV 누적 피드백 전체)
2. vote='bad'·'wrong' + user_correction 있는 케이스 추출
3. 잘못된 item_id → 사용자 correction 매핑 후보 리스트
4. docs/feedback_learning/YYYY-MM-DD.md 저장
5. 사용자 검토 후 alias 적용 (자동 적용 X — 안전)

원칙:
- 자동 alias 추가 절대 X (사용자 동의 후만)
- 출처 + 빈도수 표시
- 같은 잘못 3회 이상 = 우선 검토
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from collections import defaultdict, Counter
from datetime import datetime

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev"


def fetch_feedback():
    key = os.environ.get("FEEDBACK_DUMP_KEY")
    if not key:
        print("❌ FEEDBACK_DUMP_KEY 환경변수 필요")
        print("   set FEEDBACK_DUMP_KEY=<your-key>   (Windows)")
        print("   export FEEDBACK_DUMP_KEY=<your-key>  (Mac/Linux)")
        return None
    url = f"{WORKER_URL}/feedback/dump?key={urllib.parse.quote(key)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "yeoguiseon-learning/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ /feedback/dump 호출 실패: {e}")
        return None


def main():
    print("=== Phase F: 피드백 학습 루프 ===\n")

    data = fetch_feedback()
    if not data:
        return 1
    items = data.get("items", [])
    print(f"전체 피드백: {len(items)}건\n")

    # 잘못된 매칭 추출
    bad_cases = []
    for fb in items:
        if fb.get("vote") in ("bad", "wrong") and fb.get("item_id"):
            bad_cases.append({
                "item_id": fb["item_id"],
                "item_name": fb.get("item_name", ""),
                "category": fb.get("category", ""),
                "correction": fb.get("user_correction", ""),
                "region": fb.get("region", ""),
                "ts": fb.get("ts", ""),
            })

    print(f"잘못된 매칭 (bad/wrong): {len(bad_cases)}건")
    if not bad_cases:
        print("✓ 학습할 케이스 없음")
        return 0

    # item_id별 카운트
    item_counter = Counter(c["item_id"] for c in bad_cases)
    print(f"\n=== 잘못 매칭 item TOP 10 ===")
    for iid, cnt in item_counter.most_common(10):
        print(f"  {cnt}회: {iid}")

    # 동일 (item_id, correction) 묶음 — 3회 이상이면 alias 후보
    pair_counter = Counter((c["item_id"], c["correction"]) for c in bad_cases if c["correction"])
    suggestions = []
    for (iid, corr), cnt in pair_counter.most_common(30):
        if cnt >= 1:
            suggestions.append({
                "wrong_id": iid,
                "user_says": corr,
                "count": cnt,
                "priority": "high" if cnt >= 3 else "medium" if cnt >= 2 else "low",
            })

    print(f"\n=== 알리아스 보강 후보 ===")
    for s in suggestions[:20]:
        print(f"  [{s['priority']}] {s['count']}회: '{s['wrong_id']}' → '{s['user_says']}'")

    # 저장
    out_dir = os.path.join(ROOT, "docs", "feedback_learning")
    os.makedirs(out_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(out_dir, f"{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# 피드백 학습 보고서 — {today}\n\n")
        f.write(f"- 전체 피드백: {len(items)}\n")
        f.write(f"- 잘못된 매칭: {len(bad_cases)}\n\n")
        f.write(f"## 알리아스 보강 후보\n\n")
        for s in suggestions:
            f.write(f"- [{s['priority']}] {s['count']}회 — `{s['wrong_id']}` 가 실제로 `{s['user_says']}`\n")
        f.write(f"\n## 적용 방법 (사용자 동의 후)\n\n")
        f.write(f"1. 후보 검토 — 같은 물건의 다른 이름인가? 다른 물건인가?\n")
        f.write(f"2. 같은 물건이면 — NATIONAL.items[정확_id].aliases에 사용자 단어 추가\n")
        f.write(f"3. 다른 물건이면 — 새 item 추가 또는 모호 분기 UI 후보\n")
        f.write(f"4. 적용 후 benchmark_db.py 실행 — 정확도 변화 확인\n")

    print(f"\n저장: {out_path}")
    print("\n✓ 학습 보고서 작성 완료. 사용자 검토 후 alias 수동 적용.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
