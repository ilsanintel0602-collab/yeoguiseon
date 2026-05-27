#!/usr/bin/env python3
"""
사진 자동 수집 — Wikimedia Commons API (CC BY-SA) 활용.
benchmark/samples/ 에 자동 다운로드 + labels.csv 자동 생성.

사용:
    python scripts/collect_samples.py            # 기본 30장 수집
    python scripts/collect_samples.py --count 50 # 50장 수집
    python scripts/collect_samples.py --dry-run  # URL만 출력
    python scripts/collect_samples.py --resume   # 기존 파일 skip

라이센스: Wikimedia Commons (CC BY-SA, 출처 표기 시 무료 사용)
"""
import argparse
import csv
import json
import os
import sys
import time
from urllib import request, parse, error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
BENCH_DIR = os.path.join(ROOT, "benchmark")
SAMPLES = os.path.join(BENCH_DIR, "samples")
LABELS = os.path.join(BENCH_DIR, "labels.csv")

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

# 카테고리 -> (검색 키워드, 예상 item, 우리 카테고리 enum) 매핑
# 의미 있는 30장 (한국 분리수거 자주 검색되는 케이스 위주)
TARGETS = [
    # 페트·플라스틱
    ("pet_clear_bottle",  "PET clear bottle water",       "투명 페트병",    "pet_clear"),
    ("plastic_color",     "plastic bottle colored",        "유색 플라스틱병", "plastic"),
    ("shampoo_bottle",    "shampoo bottle plastic",        "샴푸통",         "plastic"),
    ("plastic_container", "plastic container food",        "플라스틱 용기",   "plastic"),
    # 종이류
    ("newspaper",         "newspaper stack",               "신문지",         "paper"),
    ("cardboard_box",     "cardboard box brown",           "종이박스",       "paper"),
    ("magazine",          "magazine pile",                 "잡지",           "paper"),
    # 종이팩
    ("milk_carton",       "milk carton tetrapak",          "우유팩",         "paper_pack"),
    ("juice_carton",      "juice carton aseptic",          "주스팩",         "paper_pack"),
    # 캔·금속
    ("aluminum_can",      "aluminum can drink",            "음료캔",         "can"),
    ("food_can",          "tin can food",                  "통조림캔",       "can"),
    ("spray_can",         "aerosol spray can",             "에어로졸 캔",    "can"),
    # 유리
    ("glass_bottle",      "glass bottle clear",            "유리병",         "glass"),
    ("wine_bottle",       "wine bottle empty",             "와인병",         "glass"),
    # 비닐
    ("plastic_bag",       "plastic bag shopping",          "비닐봉지",       "vinyl"),
    ("snack_bag",         "chip bag empty",                "과자봉지",       "vinyl"),
    ("ramen_packet",      "instant noodle packet",         "라면봉지",       "vinyl"),
    # 스티로폼
    ("styrofoam_box",     "styrofoam box white",           "스티로폼 박스",  "styrofoam"),
    ("styrofoam_tray",    "styrofoam tray food",           "스티로폼 트레이","styrofoam"),
    # 의류
    ("old_clothes",       "old clothes pile donate",       "헌옷",           "clothes"),
    # 건전지·전구
    ("battery_AA",        "AA battery alkaline",           "건전지",         "battery"),
    ("fluorescent_lamp",  "fluorescent lamp tube",         "형광등",         "lamp"),
    ("led_bulb",          "LED light bulb",                "LED 전구",       "lamp"),
    # 전자
    ("smartphone",        "smartphone old broken",         "폐휴대폰",       "electronics"),
    ("laptop",            "laptop computer used",          "노트북",         "electronics"),
    # 위험
    ("butane_gas",        "butane gas canister",           "부탄가스",       "hazardous"),
    ("paint_can",         "paint can metal",               "페인트 캔",      "hazardous"),
    # 일반·기타
    ("ceramic_dish",      "ceramic dish broken",           "도자기",         "general_noncombustible"),
    ("diaper",            "diaper disposable",             "기저귀",         "general"),
    ("furniture_chair",   "wooden chair old",              "헌 의자",        "furniture"),
]


def search_wikimedia(keyword, limit=3):
    """Wikimedia Commons API: 이미지 검색 -> 파일 제목 리스트"""
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f"{keyword} filetype:bitmap",
        "srnamespace": "6",  # File namespace
        "srlimit": str(limit),
    }
    url = WIKIMEDIA_API + "?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "yeoguiseon-benchmark/1.0 (https://github.com/ilsanintel0602-collab/yeoguiseon)"})
    try:
        with request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("query", {}).get("search", [])
        return [r["title"] for r in results]
    except Exception as e:
        print(f"  [WARN] search 실패 ({keyword}): {e}")
        return []


def get_image_url(file_title):
    """Wikimedia 파일 제목 -> 실제 이미지 URL"""
    params = {
        "action": "query",
        "format": "json",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": "640",  # 640px thumbnail
    }
    url = WIKIMEDIA_API + "?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "yeoguiseon-benchmark/1.0"})
    try:
        with request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        for p in pages.values():
            ii = p.get("imageinfo", [])
            if ii:
                # thumburl 우선 (640px), 없으면 원본 url
                return ii[0].get("thumburl") or ii[0].get("url")
    except Exception as e:
        print(f"  [WARN] imageinfo 실패 ({file_title}): {e}")
    return None


def download(url, dest):
    """이미지 다운로드"""
    req = request.Request(url, headers={"User-Agent": "yeoguiseon-benchmark/1.0"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return len(data)
    except Exception as e:
        print(f"  [ERR] 다운로드 실패: {e}")
        return 0


def main():
    ap = argparse.ArgumentParser(description="Wikimedia Commons 사진 자동 수집")
    ap.add_argument("--count", type=int, default=30, help="수집 개수 (default 30)")
    ap.add_argument("--dry-run", action="store_true", help="URL만 출력, 다운로드 안 함")
    ap.add_argument("--resume", action="store_true", help="기존 파일 skip")
    ap.add_argument("--per-keyword", type=int, default=1, help="키워드당 사진 개수 (default 1)")
    args = ap.parse_args()

    os.makedirs(SAMPLES, exist_ok=True)
    targets = TARGETS[:args.count]
    print(f"=== Wikimedia Commons 자동 수집 ===")
    print(f"  대상: {len(targets)}개 (각 키워드 상위 {args.per_keyword}장)")
    print(f"  저장: {SAMPLES}")
    print(f"  모드: {'DRY-RUN' if args.dry_run else 'DOWNLOAD'}")
    print()

    collected = []  # (filename, expected_item, expected_category)
    for idx, (slug, keyword, item_ko, cat) in enumerate(targets, 1):
        fname = f"{slug}.jpg"
        dest = os.path.join(SAMPLES, fname)
        if args.resume and os.path.exists(dest):
            print(f"  [{idx:2d}] SKIP {fname} (이미 존재)")
            collected.append((fname, item_ko, cat))
            continue

        print(f"  [{idx:2d}] [{cat:24s}] '{keyword}'")
        titles = search_wikimedia(keyword, args.per_keyword * 2)
        if not titles:
            print(f"        검색 결과 없음, skip")
            continue

        # 첫 번째 적합 결과 시도
        success = False
        for title in titles[:args.per_keyword * 2]:
            img_url = get_image_url(title)
            if not img_url:
                continue
            print(f"        -> {title}")
            print(f"           URL: {img_url[:80]}...")
            if args.dry_run:
                collected.append((fname, item_ko, cat))
                success = True
                break
            size = download(img_url, dest)
            if size > 1000:  # 1KB 이상이면 성공
                print(f"           saved: {size:,} bytes")
                collected.append((fname, item_ko, cat))
                success = True
                break
            elif os.path.exists(dest):
                os.remove(dest)
        if not success:
            print(f"        다운로드 실패, skip")

        time.sleep(0.5)  # API rate limit

    print(f"\n=== 수집 완료: {len(collected)}/{len(targets)}장 ===")

    # labels.csv 자동 생성 (백업 후 새로 작성)
    if collected and not args.dry_run:
        if os.path.exists(LABELS):
            backup = LABELS + ".bak"
            import shutil
            shutil.copy(LABELS, backup)
            print(f"  기존 labels.csv 백업: {backup}")
        with open(LABELS, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["filename", "expected_item", "expected_category"])
            writer.writerow(["# 자동 생성 by collect_samples.py", "", ""])
            writer.writerow(["# 출처: Wikimedia Commons (CC BY-SA)", "", ""])
            writer.writerow([f"# 라벨이 부정확하면 수동 정정 후 python scripts/benchmark.py 실행", "", ""])
            for row in collected:
                writer.writerow(row)
        print(f"  labels.csv 생성: {LABELS}")

    print()
    print("다음 단계:")
    print("  1. benchmark/samples/ 확인 (라벨 부정확하면 정정)")
    print("  2. python scripts/benchmark.py --verbose  (실측)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
