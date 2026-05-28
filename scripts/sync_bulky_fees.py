#!/usr/bin/env python3
"""
대형폐기물 수거 수수료 자동 동기화 (행안부 표준데이터 #1)
============================================================
목적: 매트리스·소파·책상·장롱 등 대형폐기물 카테고리에 시군구별 정확 수수료 표시.

데이터 출처: 행정안전부 "전국대형폐기물수거수수료정보표준데이터"
출력: data/bulky_fees.json — {sgg_code: {item_name: price, ...}}
사용:
  python scripts/sync_bulky_fees.py --dry-run --key API_KEY
  python scripts/sync_bulky_fees.py --key API_KEY

안전망:
  - 매 실행 백업 (bulky_fees.json.bak.YYYYMMDD_HHMMSS)
  - --dry-run 옵션
  - 신규 시군구 추가 가능 (대형폐기물은 신규 정합성 OK)
  - 가격 0 이하 자동 차단
  - fsync 강제 저장
"""
import argparse
import json
import os
import sys
import shutil
import ssl
import time
from datetime import datetime
from urllib import request, parse, error

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT_PATH = os.path.join(ROOT, "data", "bulky_fees.json")
DEFAULT_API_URL = "https://api.data.go.kr/openapi/tn_pubr_public_bulky_waste_fee_api"


def _make_ssl_context():
    """SSL context — TLS 1.2 강제, 호환성 ↑ (data.go.kr 일부 시군구 서버 호환 문제 회피)"""
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT@SECLEVEL=1")  # 일부 구식 cipher 허용
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def fetch_api(api_url, api_key, page=1, per_page=100, retry=3):
    """행안부 API 호출 (SSL 강화 + 재시도 3회 + Mozilla UA)"""
    params = {
        "serviceKey": api_key,
        "type": "json",
        "pageNo": str(page),
        "numOfRows": str(per_page),
    }
    url = api_url + "?" + parse.urlencode(params)
    # Mozilla UA (Python UA 차단 회피)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Connection": "keep-alive",
    }
    ssl_ctx = _make_ssl_context()
    last_err = None
    for attempt in range(1, retry + 1):
        try:
            req = request.Request(url, headers=headers)
            with request.urlopen(req, timeout=30, context=ssl_ctx) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                # 응답이 XML인 경우 JSON 강제 (type=json 무시 서버 대응)
                if raw.strip().startswith("<"):
                    print(f"  ⚠️ XML 응답 (재시도 {attempt}/{retry})")
                    last_err = "XML 응답"
                    time.sleep(1)
                    continue
                return json.loads(raw)
        except error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e}"
            print(f"  ⚠️ {last_err} (재시도 {attempt}/{retry})")
            if e.code in (401, 403):
                # 인증 오류는 재시도 무의미
                print(f"  ❌ 인증 실패 — 키 확인 필요")
                return None
        except Exception as e:
            last_err = str(e)
            print(f"  ⚠️ {last_err} (재시도 {attempt}/{retry})")
        time.sleep(2)
    print(f"  ❌ fetch 최종 실패: {last_err}")
    return None


def fetch_all(api_url, api_key):
    """페이지네이션 전체 fetch"""
    all_items = []
    page = 1
    while page <= 200:  # 안전 상한
        d = fetch_api(api_url, api_key, page=page)
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


def normalize_items(api_items):
    """API 응답 → {sgg_code: {item_name: price}} 구조로 정규화.
    행안부 API 필드 (추정): signguCd, opetnInsttNm, lrgWastesNm, dsuseFeeAmt
    """
    out = {}
    seen_fields = set()
    for ai in api_items[:3]:
        seen_fields.update(ai.keys())
    print(f"  [샘플] API 필드: {sorted(seen_fields)[:10]}")

    for ai in api_items:
        # 시군구 코드 (다양한 필드명 시도)
        sgg = str(ai.get("signguCd") or ai.get("sigunguCd") or ai.get("signguCode") or "").strip()
        if not sgg or len(sgg) < 5:
            continue
        # 품목명
        item = (
            ai.get("lrgWastesNm") or ai.get("lrgWasteNm")
            or ai.get("itemNm") or ai.get("wasteNm") or ""
        ).strip()
        if not item:
            continue
        # 수수료
        try:
            fee = int(float(ai.get("dsuseFeeAmt") or ai.get("feeAmt") or ai.get("price") or 0))
        except (ValueError, TypeError):
            continue
        if fee <= 0:
            continue
        # 시청 이름
        sgg_name = (
            ai.get("ctprvnNm", "") + " " + ai.get("signguNm", "")
        ).strip()
        out.setdefault(sgg, {"name": sgg_name, "fees": {}})
        out[sgg]["fees"][item] = fee
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DATA_GO_KR_API_KEY"))
    ap.add_argument("--url", default=DEFAULT_API_URL,
                    help="API URL (활용신청 페이지에서 확인)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("=" * 50)
    print("🛋 대형폐기물 수수료 자동 동기화")
    print("=" * 50)
    print(f"  API URL: {args.url}")

    if not args.key:
        print("  ❌ API 키 필요")
        print("  발급: data.go.kr → 활용신청 페이지 → 인증키 (Decoding)")
        return 1

    print("\n[1/3] API fetch...")
    items = fetch_all(args.url, args.key)
    print(f"  ✅ {len(items)}건 수신" if items else f"  ❌ 0건 — API URL/키 확인 필요")
    if not items:
        return 1

    print("\n[2/3] 정규화...")
    normalized = normalize_items(items)
    sgg_count = len(normalized)
    fee_count = sum(len(v.get("fees", {})) for v in normalized.values())
    print(f"  ✅ {sgg_count} 시군구 / {fee_count} 수수료 항목")

    # 샘플 출력
    print("\n  [샘플] 처음 3 시군구:")
    for i, (sgg, info) in enumerate(list(normalized.items())[:3]):
        sample_items = list(info.get("fees", {}).items())[:3]
        print(f"    {sgg} {info.get('name', '')}: {dict(sample_items)}")

    if args.dry_run:
        print("\n[3/3] DRY RUN — 저장 X")
        return 0

    # 백업 (기존 파일 있으면)
    if os.path.exists(OUT_PATH):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = OUT_PATH + f".bak.{ts}"
        shutil.copy2(OUT_PATH, bak)
        print(f"\n[3/3] 백업: {os.path.basename(bak)}")
    else:
        print("\n[3/3] 신규 파일 생성")

    final = {
        "$schema": "전국대형폐기물수거수수료 (행안부 표준데이터)",
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "source": "행정안전부 표준데이터",
        "sourceUrl": "https://www.data.go.kr/data/15049435/standard.do",
        "sgguCount": sgg_count,
        "feeCount": fee_count,
        "data": normalized,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    print(f"  ✅ 저장: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
