#!/usr/bin/env python3
"""
URL alive 검사 — region_urls.json·region_exceptions.json의 외부 URL 200 응답 확인.

사용:
  python scripts/check_urls_alive.py        # 전체 검사
  python scripts/check_urls_alive.py --fix  # 죽은 URL 자동 표시 (status='dead')

저장:
  docs/url_health/YYYY-MM-DD.md (보고서)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
TIMEOUT = 5  # 5초
HEADERS = {
    "User-Agent": "Mozilla/5.0 (yeoguiseon URL alive check)",
}


def check_url(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return url, resp.getcode(), None
    except Exception as e:
        # HEAD가 안 되면 GET 시도
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return url, resp.getcode(), None
        except Exception as e2:
            return url, 0, str(e2)[:80]


def main():
    # 모든 외부 URL 수집
    urls = set()
    region_urls = json.load(open(os.path.join(ROOT, "data", "region_urls.json"), encoding="utf-8"))
    for code, info in region_urls.get("regions", {}).items():
        for key in ("officialUrl", "wasteUrl", "bulkWasteUrl", "cleanUrl"):
            v = info.get(key)
            if v and v.startswith("http"):
                urls.add(v)

    region_ex = json.load(open(os.path.join(ROOT, "data", "region_exceptions.json"), encoding="utf-8"))
    for code, info in region_ex.get("exceptions", {}).items():
        cg = info.get("cityGuide") or {}
        for key in ("officialUrl", "bulkyWasteUrl"):
            v = cg.get(key)
            if v and v.startswith("http"):
                urls.add(v)

    print(f"검사 대상: {len(urls)} URL\n")

    # 병렬 검사 (10 스레드)
    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(check_url, u): u for u in urls}
        for i, future in enumerate(as_completed(futures), 1):
            url, status, err = future.result()
            results.append({"url": url, "status": status, "err": err})
            mark = "✓" if status == 200 else ("⚠" if 200 < status < 400 else "❌")
            print(f"  [{i}/{len(urls)}] {mark} {status} {url[:80]}")

    # 분류
    alive = [r for r in results if r["status"] == 200]
    redirect = [r for r in results if 300 <= r["status"] < 400]
    dead = [r for r in results if r["status"] == 0 or r["status"] >= 400]

    print(f"\n=== 결과 ===")
    print(f"  ✓ alive (200): {len(alive)}")
    print(f"  ⚠ redirect (3xx): {len(redirect)}")
    print(f"  ❌ dead: {len(dead)}")

    # 보고서 저장
    out_dir = os.path.join(ROOT, "docs", "url_health")
    os.makedirs(out_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_path = os.path.join(out_dir, f"{today}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# URL alive 검사 — {today}\n\n")
        f.write(f"- 전체: {len(urls)}\n")
        f.write(f"- ✓ alive: {len(alive)}\n")
        f.write(f"- ⚠ redirect: {len(redirect)}\n")
        f.write(f"- ❌ dead: {len(dead)}\n\n")
        if dead:
            f.write(f"## ❌ Dead URLs ({len(dead)})\n\n")
            for r in dead:
                f.write(f"- [{r['status']}] {r['url']}\n")
                if r['err']:
                    f.write(f"  - error: {r['err']}\n")
    print(f"\n저장: {out_path}")

    return 0 if len(dead) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
