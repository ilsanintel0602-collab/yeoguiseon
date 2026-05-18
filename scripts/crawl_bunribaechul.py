#!/usr/bin/env python3
"""
분리배출.kr 주간 자동 크롤러
- 환경부 생활폐기물 분리배출 누리집의 730+ 품목 수집
- GitHub Actions에서 매주 월요일 새벽 3시(KST) 실행
- 변경 사항 있으면 자동 commit + push

사용:
    python scripts/crawl_bunribaechul.py            # 전체 크롤
    python scripts/crawl_bunribaechul.py --range 1 100   # 부분 (테스트)
    python scripts/crawl_bunribaechul.py --check     # 차이만 확인 (commit X)
"""
import requests
import json
import time
import re
import sys
import os
from datetime import datetime, timezone
from collections import Counter
from bs4 import BeautifulSoup

BASE = "https://www.xn--oy2b29bd3a601b.kr"
DETAIL_URL = f"{BASE}/front/dischargeMethod/dictionaryView.do?niIdx={{seq}}"
HEADERS = {
    "User-Agent": "yeoguiseon-crawler/1.0 (educational PWA; +https://github.com/ilsanintel0602-collab/yeoguiseon)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_RAW = os.path.join(DATA_DIR, "raw_bunribaechul_730.json")


def fetch_item(seq: int, session: requests.Session, retries: int = 2):
    """단일 품목 페이지 fetch + 파싱"""
    for attempt in range(retries + 1):
        try:
            r = session.get(DETAIL_URL.format(seq=seq), timeout=15)
            if r.status_code != 200:
                return None
            return parse_item(r.text, seq)
        except requests.RequestException as e:
            if attempt == retries:
                print(f"  ! seq={seq} 실패: {e}", flush=True)
                return None
            time.sleep(1)


def parse_item(html: str, seq: int):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("#mainContent, main, .container") or soup
    txt = main.get_text("\n", strip=False)
    lines = [s.strip() for s in txt.split("\n") if s.strip()]

    # 이름 (품목사전 다음 단어)
    name = None
    for i, l in enumerate(lines):
        if l == "품목사전" and i + 1 < len(lines):
            cand = lines[i + 1]
            if cand and cand != "품목사전" and len(cand) < 30 and "폐기물" not in cand:
                name = cand
                break

    # 분류체계
    classification = []
    if "폐기물 분류체계" in lines:
        ci = lines.index("폐기물 분류체계")
        for j in range(ci + 1, min(ci + 6, len(lines))):
            l = lines[j]
            if l in ("유사품목", "배출방법", "특징", "유의사항"):
                break
            if len(l) < 30:
                classification.append(l)

    # 유사품목
    similar = []
    if "유사품목" in lines:
        si = lines.index("유사품목")
        for j in range(si + 1, len(lines)):
            l = lines[j]
            if l in ("배출방법", "특징", "유의사항"):
                break
            if 0 < len(l) < 30:
                similar.append(l)

    # 배출방법
    dm = ""
    if "배출방법" in lines:
        di = lines.index("배출방법")
        for j in range(di + 1, len(lines)):
            l = lines[j]
            if l in ("특징", "유의사항"):
                break
            if len(l) > 3:
                dm += l + " "

    # 특징
    feat = ""
    if "특징" in lines:
        fi = lines.index("특징")
        for j in range(fi + 1, len(lines)):
            l = lines[j]
            if l in ("유의사항", "배출방법"):
                break
            if len(l) > 3:
                feat += l + " "

    # 유의사항
    cau = ""
    if "유의사항" in lines:
        ui = lines.index("유의사항")
        for j in range(ui + 1, len(lines)):
            l = lines[j]
            if l.startswith("※") or l.startswith("가까운") or "맨위로" in l:
                break
            if len(l) > 3:
                cau += l + " "

    # 이름이 없으면 배출방법 첫 문장에서 추출
    if not name and dm:
        first = re.sub(r"^[\s·\-•]+", "", dm).split(".")[0].strip()
        m = re.match(r"^([가-힣A-Za-z0-9()\s&]+?)(?:는|은|을|를|이|가)\s", first)
        if m:
            name = m.group(1).strip()

    if not name and not dm:
        return None  # 존재하지 않는 seq

    return {
        "seq": seq,
        "name": name,
        "classification": classification,
        "similar": similar,
        "dischargeMethod": dm.strip(),
        "feature": feat.strip(),
        "caution": cau.strip(),
        "sourceUrl": f"https://www.xn--oy2b29bd3a601b.kr/front/dischargeMethod/dictionaryView.do?niIdx={seq}",
    }


def crawl(start: int = 1, end: int = 800, delay: float = 0.3):
    """1~800 시퀀스 순회"""
    s = requests.Session()
    s.headers.update(HEADERS)
    results = []
    print(f"📥 크롤링 시작: seq {start} ~ {end}", flush=True)
    t0 = time.time()
    for seq in range(start, end + 1):
        item = fetch_item(seq, s)
        if item:
            results.append(item)
        if seq % 50 == 0:
            elapsed = time.time() - t0
            rate = seq / max(1, elapsed)
            print(f"  진행 {seq}/{end} ({len(results)}개 유효) — {elapsed:.0f}초, {rate:.1f}/s", flush=True)
        time.sleep(delay)
    print(f"✅ 크롤링 완료: {len(results)}개, {time.time() - t0:.0f}초", flush=True)
    return results


def save(results, output_path=OUTPUT_RAW):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = {
        "source": "https://분리배출.kr (한국폐기물협회·환경부)",
        "crawledAt": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "items": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 저장: {output_path} ({os.path.getsize(output_path)/1024:.0f} KB)", flush=True)


def diff_summary(old_path: str, new_data: dict) -> dict:
    """기존 vs 신규 데이터 변경 요약"""
    if not os.path.exists(old_path):
        return {"new": new_data["count"], "removed": 0, "changed": 0}
    with open(old_path, "r", encoding="utf-8") as f:
        old = json.load(f)
    old_by_seq = {i["seq"]: i for i in old.get("items", []) if i.get("seq")}
    new_by_seq = {i["seq"]: i for i in new_data["items"] if i.get("seq")}
    added = set(new_by_seq) - set(old_by_seq)
    removed = set(old_by_seq) - set(new_by_seq)
    changed = sum(
        1 for s in (set(old_by_seq) & set(new_by_seq))
        if old_by_seq[s].get("dischargeMethod") != new_by_seq[s].get("dischargeMethod")
    )
    return {"added": len(added), "removed": len(removed), "changed": changed}


def main():
    args = sys.argv[1:]
    start, end = 1, 800
    check_only = False
    if "--range" in args:
        i = args.index("--range")
        start, end = int(args[i + 1]), int(args[i + 2])
    if "--check" in args:
        check_only = True

    results = crawl(start, end)
    new_data = {
        "source": "https://분리배출.kr",
        "crawledAt": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "items": results,
    }

    diff = diff_summary(OUTPUT_RAW, new_data)
    print(f"\n📊 변경 요약: 추가 {diff.get('added', 0)} · 제거 {diff.get('removed', 0)} · 수정 {diff.get('changed', 0)}", flush=True)

    if check_only:
        sys.exit(0 if (diff.get("added", 0) + diff.get("removed", 0) + diff.get("changed", 0)) == 0 else 1)

    save(results)


if __name__ == "__main__":
    main()
