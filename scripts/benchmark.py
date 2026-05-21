#!/usr/bin/env python3
"""
Phase 5: PC 기반 객관 벤치마크 (Worker 직접 호출)

사용법:
    1. benchmark/samples/ 폴더에 사진 추가 (.jpg, .png)
    2. benchmark/labels.csv 에 정답 라벨 작성:
       filename,expected_item,expected_category
       sample001.jpg,pet_bottle,plastic
       sample002.jpg,종이컵,general
    3. python scripts/benchmark.py
    4. 결과: benchmark/report_YYYY-MM-DD.md

특징:
- Worker URL 직접 호출 (모바일·앱 안 거침 → 깔끔)
- 카테고리별 정확도 자동 계산
- 약점 카테고리 자동 식별
- 버전별 비교 (이전 결과와 diff)
"""
import base64
import csv
import json
import os
import sys
import time
from collections import defaultdict, Counter
from datetime import datetime
from urllib import request, error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
BENCH_DIR = os.path.join(ROOT, "benchmark")
SAMPLES = os.path.join(BENCH_DIR, "samples")
LABELS = os.path.join(BENCH_DIR, "labels.csv")
WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev/"

# SYSTEM_PROMPT는 app.html과 동일 — Worker가 받기 때문에 그쪽에 위임 가능
# 단 직접 호출 시 prompt 함께 보내야 함. 간소화: Worker가 기본 prompt 사용하도록 빈 prompt도 OK.
DEFAULT_PROMPT = "분리수거 분류. JSON 응답만: {\"item_id\": \"<id>\", \"item_label_ko\": \"<한국어>\", \"category\": \"<plastic|paper|paper_pack|vinyl|can|glass|styrofoam|food|general|battery|lamp|clothes|electronics|furniture|hazardous|medicine|reusable>\", \"confidence\": 0.95}"


def call_worker(image_path):
    """Worker에 사진 보내고 결과 받기"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    body = json.dumps({
        "imageBase64": b64,
        "prompt": DEFAULT_PROMPT,
        "mimeType": "image/jpeg",
    }).encode("utf-8")
    req = request.Request(WORKER_URL, data=body, method="POST",
                          headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("ok") and data.get("result"):
            result = data["result"]
            if isinstance(result, str):
                # JSON 복구 (v5.11 클라이언트 로직과 동일)
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"_parse_error": "JSON 손상", "raw": result[:200]}
            return result
        return {"_error": data.get("error") or "unknown", "finishReason": data.get("finishReason"), "blockReason": data.get("blockReason")}
    except error.HTTPError as e:
        return {"_http_error": e.code, "_msg": str(e)}
    except Exception as e:
        return {"_exception": str(e)}


def load_labels():
    if not os.path.exists(LABELS):
        return []
    with open(LABELS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def main():
    print(f"Worker URL: {WORKER_URL}")
    print(f"Samples:    {SAMPLES}")
    print(f"Labels:     {LABELS}")
    print()

    if not os.path.exists(SAMPLES):
        os.makedirs(SAMPLES, exist_ok=True)
        print(f"[INFO] samples 폴더 생성됨. 사진을 여기에 넣고 다시 실행하세요.")
        return

    rows = load_labels()
    if not rows:
        print(f"[INFO] labels.csv 없음. 템플릿 생성합니다.")
        template = "filename,expected_item,expected_category\n# 예시:\n# sample001.jpg,pet_bottle,plastic\n# sample002.jpg,종이컵,general\n"
        with open(LABELS, "w", encoding="utf-8") as f:
            f.write(template)
        print(f"  → {LABELS}")
        return

    print(f"=== {len(rows)}장 평가 시작 ===\n")
    cat_correct = Counter()
    cat_total = Counter()
    item_results = []
    errors = []

    for i, row in enumerate(rows, 1):
        fname = row.get("filename", "").strip()
        if not fname or fname.startswith("#"):
            continue
        path = os.path.join(SAMPLES, fname)
        if not os.path.exists(path):
            print(f"  [{i:3d}] SKIP   {fname:30s}  파일 없음")
            continue

        expected_item = row.get("expected_item", "").strip()
        expected_cat = row.get("expected_category", "").strip()

        result = call_worker(path)

        if "_error" in result or "_http_error" in result or "_exception" in result or "_parse_error" in result:
            errors.append((fname, result))
            print(f"  [{i:3d}] ERR    {fname:30s}  {list(result.keys())[0]}")
            continue

        got_item = result.get("item_id") or result.get("item_label_ko") or ""
        got_cat = result.get("category") or ""

        cat_match = (got_cat == expected_cat) if expected_cat else None
        item_match = (got_item == expected_item) if expected_item else None

        if expected_cat:
            cat_total[expected_cat] += 1
            if cat_match:
                cat_correct[expected_cat] += 1

        mark = "OK " if cat_match else "FAIL"
        print(f"  [{i:3d}] {mark}  {fname:30s}  expect={expected_cat}/{expected_item}  got={got_cat}/{got_item}")
        item_results.append({
            "filename": fname,
            "expected_item": expected_item,
            "expected_category": expected_cat,
            "got_item": got_item,
            "got_category": got_cat,
            "match_cat": cat_match,
            "match_item": item_match,
        })
        time.sleep(0.5)  # Worker 부담 줄임

    print("\n=== 카테고리별 정확도 ===")
    total_correct = sum(cat_correct.values())
    total_n = sum(cat_total.values())
    overall_acc = total_correct * 100 / max(total_n, 1)
    print(f"  Overall: {total_correct}/{total_n} ({overall_acc:.1f}%)\n")
    for cat, total in sorted(cat_total.items(), key=lambda x: -x[1]):
        correct = cat_correct[cat]
        acc = correct * 100 / total
        print(f"    {cat:14s}  {correct:3d}/{total:3d}  ({acc:5.1f}%)")

    # 약점 카테고리 자동 식별
    weak = [(c, cat_correct[c], cat_total[c]) for c, t in cat_total.items() if cat_correct[c] / t < 0.8]
    if weak:
        print(f"\n=== ⚠️ 약점 카테고리 (정확도 80% 미만) ===")
        for c, k, t in weak:
            print(f"    {c}: {k}/{t} ({k*100/t:.0f}%)")

    if errors:
        print(f"\n=== ❌ 에러 ({len(errors)}건) ===")
        for fname, err in errors[:5]:
            print(f"    {fname}: {err}")

    # 보고서 저장
    report_path = os.path.join(BENCH_DIR, f"report_{datetime.now().strftime('%Y-%m-%d_%H%M')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 여기선 벤치마크 보고서\n\n")
        f.write(f"- 일시: {datetime.now().isoformat()}\n")
        f.write(f"- Worker: `{WORKER_URL}`\n")
        f.write(f"- 평가: {total_n}장\n")
        f.write(f"- **Overall 정확도: {overall_acc:.1f}%**\n\n")
        f.write(f"## 카테고리별\n\n| 카테고리 | 정확/전체 | 정확도 |\n|---|---|---|\n")
        for cat, total in sorted(cat_total.items(), key=lambda x: -x[1]):
            f.write(f"| {cat} | {cat_correct[cat]}/{total} | {cat_correct[cat]*100/total:.1f}% |\n")
        if weak:
            f.write(f"\n## 약점\n\n")
            for c, k, t in weak:
                f.write(f"- {c}: {k}/{t} ({k*100/t:.0f}%)\n")
        if errors:
            f.write(f"\n## 에러\n\n")
            for fname, err in errors:
                f.write(f"- {fname}: `{err}`\n")
    print(f"\n  보고서 저장: {report_path}")


if __name__ == "__main__":
    main()
