#!/usr/bin/env python3
"""
v6.14 #3: 행안부 봉투 가격 자동 동기화 — 단계 B (자동 갱신 + 백업 + 변경 로그)

단계 A (기존 sync_bag_prices.py): 비교·알림만
단계 B (이 스크립트): 자동 적용 + 백업 + JSONL 변경 로그

안전망:
  - 매 실행 백업 (bag_prices.json.bak.YYYYMMDD_HHMMSS)
  - --dry-run 옵션 (검토만)
  - 신규 시군구 절대 미추가 (안전 — 기존 261개만 갱신)
  - 변경량 10% 초과 시 경고 + 확인 필요
  - JSONL 변경 로그 (data/sync_log_bag_prices.jsonl)

사용:
  python scripts/sync_bag_prices_v2.py --dry-run        # 검토만
  python scripts/sync_bag_prices_v2.py                  # 자동 적용 (백업 + 로그)
  python scripts/sync_bag_prices_v2.py --key API_KEY    # API 키 직접 지정

환경변수: DATA_GO_KR_API_KEY
"""
import argparse
import json
import os
import sys
import shutil
from datetime import datetime
from urllib import request, parse, error

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BAG_PATH = os.path.join(ROOT, "data", "bag_prices.json")
LOG_PATH = os.path.join(ROOT, "data", "sync_log_bag_prices.jsonl")
API_URL = "https://api.data.go.kr/openapi/tn_pubr_public_traswste_polybag_api"

MAX_CHANGE_PCT = 10.0  # 안전망: 10% 초과 변경이면 경고


def log(msg, kind="info"):
    sym = {"info": "•", "ok": "✅", "warn": "⚠️", "err": "❌"}.get(kind, "•")
    print(f"  {sym} {msg}")


def fetch_api(api_key, page=1, per_page=100):
    params = {
        "serviceKey": api_key,
        "type": "json",
        "pageNo": str(page),
        "numOfRows": str(per_page),
    }
    url = API_URL + "?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "yeoguiseon-sync-v2/1.0"})
    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        log(f"HTTP {e.code}: {e}", "err")
        return None
    except Exception as e:
        log(f"fetch 실패: {e}", "err")
        return None


def fetch_all(api_key):
    all_items = []
    page = 1
    while page <= 100:
        d = fetch_api(api_key, page=page)
        if not d:
            break
        try:
            items = d.get("response", {}).get("body", {}).get("items", []) or []
            if isinstance(items, dict):
                items = items.get("item", []) or []
        except Exception:
            items = []
        if not items:
            break
        all_items.extend(items)
        total = int(d.get("response", {}).get("body", {}).get("totalCount", 0) or 0)
        if len(all_items) >= total:
            break
        page += 1
    return all_items


def make_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = BAG_PATH + f".bak.{ts}"
    shutil.copy2(BAG_PATH, bak)
    return bak


def append_log(entries):
    """JSONL 변경 로그 추가 (1줄 1변경)"""
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def compute_changes(api_items, local):
    """API와 로컬 비교 — 적용 가능한 변경 목록 반환 (신규 시군구는 무시)"""
    local_data = local.get("data", {})
    changes = []
    for ai in api_items:
        # 코드 매칭 (api 필드는 sigunguCd 또는 비슷)
        sgg = str(ai.get("signguCd") or ai.get("sigunguCd") or "")
        if not sgg or sgg not in local_data:
            continue  # 신규 시군구 안전 무시
        kind = str(ai.get("clType") or "")
        vol = str(ai.get("clVol") or "")
        try:
            new_price = int(float(ai.get("clPc") or 0))
        except (ValueError, TypeError):
            continue
        if new_price <= 0:
            continue
        local_info = local_data[sgg]
        bags = local_info.get("bags", [])
        for b in bags:
            if str(b.get("종류")) == kind:
                prices = b.get("prices", {})
                if vol in prices and int(prices[vol]) != new_price:
                    changes.append({
                        "sgg_code": sgg,
                        "sgg_name": local_info.get("name"),
                        "kind": kind,
                        "volume": vol,
                        "old": int(prices[vol]),
                        "new": new_price,
                    })
                break
    return changes


def apply_changes(local, changes):
    """안전 적용: prices만 갱신 (구조 변경 X)"""
    local_data = local.get("data", {})
    applied = 0
    for ch in changes:
        info = local_data.get(ch["sgg_code"])
        if not info:
            continue
        for b in info.get("bags", []):
            if str(b.get("종류")) == ch["kind"]:
                if ch["volume"] in b.get("prices", {}):
                    b["prices"][ch["volume"]] = ch["new"]
                    applied += 1
                break
    return applied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DATA_GO_KR_API_KEY"))
    ap.add_argument("--dry-run", action="store_true", help="검토만, 파일 변경 X")
    ap.add_argument("--force", action="store_true", help="10% 초과 변경도 강제 적용")
    args = ap.parse_args()

    print("=" * 50)
    print("📦 봉투 가격 자동 동기화 단계 B (v6.14)")
    print("=" * 50)

    if not args.key:
        log("API 키 필요 (DATA_GO_KR_API_KEY 환경변수 또는 --key)", "err")
        log("발급: https://www.data.go.kr → '종량제봉투정보표준데이터' 활용신청", "info")
        return 1

    print("\n[1/4] 행안부 API fetch...")
    items = fetch_all(args.key)
    log(f"{len(items)}건 수신", "ok" if items else "err")
    if not items:
        return 1

    print("\n[2/4] 로컬 비교...")
    with open(BAG_PATH, "r", encoding="utf-8") as f:
        local = json.load(f)
    changes = compute_changes(items, local)
    log(f"변경 감지 {len(changes)}건", "ok" if changes else "info")

    if not changes:
        log("모두 일치 — 갱신 불필요", "ok")
        return 0

    # 안전망: 변경량 검증
    total_bags = sum(
        len(info.get("bags", []))
        for info in local.get("data", {}).values()
    )
    change_pct = (len(changes) / total_bags * 100) if total_bags else 0
    log(f"변경 비율: {change_pct:.1f}% (전체 {total_bags}건 중)", "info")

    if change_pct > MAX_CHANGE_PCT and not args.force:
        log(f"⚠️ 변경 비율 {MAX_CHANGE_PCT}% 초과 — --force 없이는 적용 X", "warn")
        log("  의심 케이스: API 형식 변경·잘못된 fetch·sample 케이스 ↑", "warn")
        return 2

    print("\n[3/4] 변경 미리보기 (처음 10건):")
    for ch in changes[:10]:
        print(f"    - {ch['sgg_name']} / {ch['kind']} {ch['volume']}: {ch['old']}원 → {ch['new']}원")
    if len(changes) > 10:
        print(f"    ... 외 {len(changes) - 10}건")

    if args.dry_run:
        print("\n[4/4] DRY RUN — 파일 변경 X")
        return 0

    print("\n[4/4] 자동 적용...")
    # 백업
    bak = make_backup()
    log(f"백업 {os.path.basename(bak)}", "ok")
    # 적용
    applied = apply_changes(local, changes)
    log(f"적용 {applied}건", "ok")
    # 저장 + fsync
    local["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")
    with open(BAG_PATH, "w", encoding="utf-8") as f:
        json.dump(local, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    # 로그 추가 (JSONL)
    ts = datetime.now().isoformat()
    log_entries = [{**ch, "ts": ts} for ch in changes]
    append_log(log_entries)
    log(f"로그 추가 {LOG_PATH}", "ok")
    log(f"✅ 동기화 완료 — bag_prices.json 갱신됨", "ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
