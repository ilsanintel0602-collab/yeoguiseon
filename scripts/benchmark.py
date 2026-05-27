#!/usr/bin/env python3
"""
사진 벤치마크 — Gemini AI 정확도 정량 측정.
사용: python scripts/benchmark.py [--mock] [--limit N] [--threshold P] [--verbose]
"""
import argparse, base64, csv, glob, json, os, random, sys, time
from collections import defaultdict, Counter
from datetime import datetime
from urllib import request, error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
BENCH_DIR = os.path.join(ROOT, "benchmark")
SAMPLES = os.path.join(BENCH_DIR, "samples")
LABELS = os.path.join(BENCH_DIR, "labels.csv")
WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev/"

CATEGORIES = [
    "paper", "paper_pack", "pet_clear", "plastic", "vinyl",
    "styrofoam", "glass", "can", "clothes", "battery", "lamp", "electronics",
    "food", "general", "general_noncombustible", "general_or_bulky",
    "furniture", "hazardous", "medicine"
]
DEFAULT_PROMPT = (
    '한국 분리수거 분류. JSON 응답만: '
    '{"item_id": "<id>", "item_label_ko": "<한국어>", '
    '"category": "<' + "|".join(CATEGORIES) + '>", '
    '"confidence": 0.95, "danger": false}'
)


def call_worker(image_path):
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
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"_parse_error": "JSON 손상", "raw": result[:200]}
            return result
        return {"_error": data.get("error") or "unknown",
                "finishReason": data.get("finishReason"),
                "blockReason": data.get("blockReason")}
    except error.HTTPError as e:
        return {"_http_error": e.code, "_msg": str(e)}
    except Exception as e:
        return {"_exception": str(e)}


def mock_worker(expected_item, expected_cat):
    """mock 모드 — 90% 정답, 10% 오답"""
    if random.random() < 0.9:
        return {"item_id": expected_item, "item_label_ko": expected_item,
                "category": expected_cat, "confidence": 0.92, "danger": False}
    wrong_cat = random.choice([c for c in CATEGORIES if c != expected_cat])
    return {"item_id": "wrong_" + expected_item, "item_label_ko": "오답",
            "category": wrong_cat, "confidence": 0.65, "danger": False}


def load_labels():
    if not os.path.exists(LABELS):
        return []
    with open(LABELS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def find_previous_overall():
    pattern = os.path.join(BENCH_DIR, "report_*.md")
    files = sorted(glob.glob(pattern))
    if not files:
        return None, None
    prev_path = files[-1]
    try:
        with open(prev_path, encoding="utf-8") as f:
            for line in f:
                if "pass@1" in line:
                    import re
                    m = re.search(r"(\d+\.\d+)%", line)
                    if m:
                        return float(m.group(1)), os.path.basename(prev_path)
    except Exception:
        pass
    return None, None


def main():
    ap = argparse.ArgumentParser(description="여기선 사진 벤치마크")
    ap.add_argument("--mock", action="store_true", help="사진 없이 dry-run")
    ap.add_argument("--limit", type=int, default=0, help="처음 N장만 평가")
    ap.add_argument("--threshold", type=float, default=80.0,
                    help="pass@1 < P%% 면 exit 1 (default 80)")
    ap.add_argument("--verbose", action="store_true", help="상세 출력")
    args = ap.parse_args()

    mode_label = "MOCK (dry-run)" if args.mock else "LIVE Worker"
    print(f"Worker URL: {WORKER_URL}")
    print(f"Samples:    {SAMPLES}")
    print(f"Labels:     {LABELS}")
    print(f"Mode:       {mode_label}")
    print(f"Threshold:  pass@1 >= {args.threshold}%")
    print()

    if not os.path.exists(SAMPLES):
        os.makedirs(SAMPLES, exist_ok=True)

    rows = load_labels()
    valid_rows = [r for r in rows if r.get("filename", "").strip()
                  and not r.get("filename", "").strip().startswith("#")]
    if not valid_rows:
        print("[INFO] 유효한 라벨 행 없음. benchmark/labels.csv 에 행을 추가하세요.")
        if args.mock:
            print("[MOCK] 가상 라벨 5건으로 진행")
            valid_rows = [
                {"filename": "mock_pet.jpg", "expected_item": "페트병", "expected_category": "pet_clear"},
                {"filename": "mock_paper.jpg", "expected_item": "신문지", "expected_category": "paper"},
                {"filename": "mock_can.jpg", "expected_item": "캔", "expected_category": "can"},
                {"filename": "mock_vinyl.jpg", "expected_item": "비닐", "expected_category": "vinyl"},
                {"filename": "mock_general.jpg", "expected_item": "일반쓰레기", "expected_category": "general"},
            ]
        else:
            return 0

    if args.limit > 0:
        valid_rows = valid_rows[:args.limit]

    print(f"=== {len(valid_rows)}장 평가 시작 ===\n")

    cat_correct = Counter()
    cat_total = Counter()
    item_correct = 0
    total_evaluated = 0
    confusion = defaultdict(Counter)
    errors = []

    for i, row in enumerate(valid_rows, 1):
        fname = row.get("filename", "").strip()
        path = os.path.join(SAMPLES, fname)
        expected_item = row.get("expected_item", "").strip()
        expected_cat = row.get("expected_category", "").strip()

        if args.mock:
            result = mock_worker(expected_item, expected_cat)
        else:
            if not os.path.exists(path):
                if args.verbose:
                    print(f"  [{i:3d}] SKIP   {fname:30s}  파일 없음")
                continue
            result = call_worker(path)

        if any(k.startswith("_") for k in result.keys()):
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
            confusion[expected_cat][got_cat] += 1

        if cat_match and item_match:
            item_correct += 1
        total_evaluated += 1

        mark = "OK " if cat_match else "FAIL"
        if args.verbose or not cat_match:
            print(f"  [{i:3d}] {mark}  {fname:30s}  expect={expected_cat}/{expected_item}  got={got_cat}/{got_item}")
        if not args.mock:
            time.sleep(0.5)

    print(f"\n=== 결과 요약 ===")
    total_correct = sum(cat_correct.values())
    total_n = sum(cat_total.values())
    overall_acc = total_correct * 100 / max(total_n, 1)
    pass_at_1 = item_correct * 100 / max(total_evaluated, 1)

    print(f"  카테고리 정확도: {total_correct}/{total_n} ({overall_acc:.1f}%)")
    print(f"  pass@1 (item+cat): {item_correct}/{total_evaluated} ({pass_at_1:.1f}%)")
    print(f"  에러: {len(errors)}건")

    print(f"\n=== 카테고리별 ===")
    for cat, total in sorted(cat_total.items(), key=lambda x: -x[1]):
        correct = cat_correct[cat]
        acc = correct * 100 / total
        bar = "#" * int(acc / 10) + "." * (10 - int(acc / 10))
        print(f"  {cat:24s}  {correct:3d}/{total:3d}  ({acc:5.1f}%)  {bar}")

    if confusion and any(len(v) > 1 for v in confusion.values()):
        print(f"\n=== 혼동 행렬 (오류 패턴) ===")
        for exp_cat in sorted(confusion):
            row = confusion[exp_cat]
            if len(row) <= 1:
                continue
            total = sum(row.values())
            print(f"  {exp_cat} (총 {total}건):")
            for got_cat, n in sorted(row.items(), key=lambda x: -x[1]):
                if got_cat == exp_cat:
                    continue
                pct = n * 100 / total
                print(f"    -> {got_cat}: {n}건 ({pct:.0f}%)")

    weak = [(c, cat_correct[c], cat_total[c]) for c, t in cat_total.items()
            if cat_correct[c] / t < 0.8]
    if weak:
        print(f"\n=== [WARN] 약점 카테고리 (정확도 80% 미만) ===")
        for c, k, t in weak:
            print(f"    {c}: {k}/{t} ({k*100/t:.0f}%)")

    prev_overall, prev_name = find_previous_overall()
    diff_msg = ""
    if prev_overall is not None:
        diff = pass_at_1 - prev_overall
        sign = "+" if diff >= 0 else ""
        diff_msg = f" (이전 {prev_overall:.1f}% -> {sign}{diff:.1f}%)"
        print(f"\n=== 회귀 감지 ===")
        print(f"  이전: {prev_overall:.1f}% ({prev_name})")
        print(f"  현재: {pass_at_1:.1f}%")
        if diff < -5.0:
            print(f"  [REGRESSION] {diff:.1f}% 하락")
        elif diff > 1.0:
            print(f"  [IMPROVE] +{diff:.1f}%")
        else:
            print(f"  [STABLE] {diff:+.1f}%")

    if errors:
        print(f"\n=== 에러 ({len(errors)}건) ===")
        for fname, err in errors[:5]:
            print(f"    {fname}: {err}")

    suffix = "_mock" if args.mock else ""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_path = os.path.join(BENCH_DIR, f"report_{ts}{suffix}.md")
    mode_str = "MOCK" if args.mock else "LIVE"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 여기선 사진 벤치마크 보고서\n\n")
        f.write(f"- 일시: {datetime.now().isoformat()}\n")
        f.write(f"- Mode: {mode_str}\n")
        f.write(f"- Worker: `{WORKER_URL}`\n")
        f.write(f"- 평가: {total_n}장\n")
        f.write(f"- 에러: {len(errors)}건\n\n")
        f.write(f"## 점수\n\n")
        f.write(f"- **Overall 정확도: {overall_acc:.1f}%**{diff_msg}\n")
        f.write(f"- **pass@1 (item+cat): {pass_at_1:.1f}%**\n\n")
        f.write(f"## 카테고리별\n\n| 카테고리 | 정확/전체 | 정확도 |\n|---|---|---|\n")
        for cat, total in sorted(cat_total.items(), key=lambda x: -x[1]):
            f.write(f"| {cat} | {cat_correct[cat]}/{total} | {cat_correct[cat]*100/total:.1f}% |\n")
        if confusion and any(len(v) > 1 for v in confusion.values()):
            f.write(f"\n## 혼동 행렬\n\n")
            for exp_cat in sorted(confusion):
                row = confusion[exp_cat]
                if len(row) <= 1:
                    continue
                f.write(f"### {exp_cat}\n\n")
                for got_cat, n in sorted(row.items(), key=lambda x: -x[1]):
                    mark = "OK" if got_cat == exp_cat else "X"
                    f.write(f"- {mark} -> {got_cat}: {n}건\n")
                f.write("\n")
        if weak:
            f.write(f"\n## 약점 카테고리\n\n")
            for c, k, t in weak:
                f.write(f"- {c}: {k}/{t} ({k*100/t:.0f}%)\n")
        if errors:
            f.write(f"\n## 에러\n\n")
            for fname, err in errors:
                f.write(f"- {fname}: `{err}`\n")
    print(f"\n  보고서 저장: {report_path}")

    if total_evaluated > 0 and pass_at_1 < args.threshold:
        print(f"\n[FAIL] pass@1 {pass_at_1:.1f}% < threshold {args.threshold}% — 회귀 차단")
        return 1
    print(f"\n[PASS] pass@1 {pass_at_1:.1f}% >= threshold {args.threshold}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
