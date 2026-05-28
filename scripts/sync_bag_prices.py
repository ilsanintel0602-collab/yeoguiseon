#!/usr/bin/env python3
"""
v5.94 B: 행안부 봉투 가격 자동 동기화 (단계 A — 비교·알림 only)

행안부 표준데이터 (data.go.kr 15025538) 종량제봉투정보 → 우리 bag_prices.json 비교.
변경 감지 시 알림. 자동 갱신 X (사용자 검토 후 수동 적용).

사용: python scripts/sync_bag_prices.py [--key API_KEY]
환경변수: DATA_GO_KR_API_KEY (또는 --key 인자)

API 키 발급 방법:
1. https://www.data.go.kr 회원가입 (무료)
2. 데이터 검색: "종량제봉투정보표준데이터"
3. "활용신청" 클릭 → 인증키 즉시 발급
4. Decoding 키 복사 → 환경변수 또는 --key

API: https://api.data.go.kr/openapi/tn_pubr_public_traswste_polybag_api
"""
import argparse
import json
import os
import sys
from urllib import request, parse, error

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
BAG_PRICES_PATH = os.path.join(ROOT, "data", "bag_prices.json")
API_URL = "https://api.data.go.kr/openapi/tn_pubr_public_traswste_polybag_api"


def fetch_api(api_key, page=1, per_page=100):
    """행안부 API 호출"""
    params = {
        "serviceKey": api_key,
        "type": "json",
        "pageNo": str(page),
        "numOfRows": str(per_page),
    }
    url = API_URL + "?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "yeoguiseon-sync/1.0"})
    try:
        with request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data
    except error.HTTPError as e:
        print(f"[ERR] HTTP {e.code}: {e}")
        return None
    except Exception as e:
        print(f"[ERR] {e}")
        return None


def fetch_all(api_key):
    """전체 페이지 fetch (페이지네이션)"""
    all_items = []
    page = 1
    while True:
        data = fetch_api(api_key, page=page, per_page=100)
        if not data:
            break
        # 응답 구조 (예상): data["response"]["body"]["items"]
        items = []
        try:
            items = data.get("response", {}).get("body", {}).get("items", []) or []
            if isinstance(items, dict):
                items = items.get("item", []) or []
        except Exception:
            pass
        if not items:
            break
        all_items.extend(items)
        # 다음 페이지 여부
        total = data.get("response", {}).get("body", {}).get("totalCount", 0)
        if len(all_items) >= int(total or 0):
            break
        page += 1
        if page > 100:
            print("[WARN] 100 페이지 초과 — 중단")
            break
    return all_items


def compare_with_local(api_items):
    """행안부 데이터 vs 우리 bag_prices.json 비교"""
    with open(BAG_PRICES_PATH, "r", encoding="utf-8") as f:
        local = json.load(f)
    local_data = local.get("data", {})

    differences = []
    for api_item in api_items:
        # 행안부 필드 예상: 시군구코드·종류·용량·가격
        code = api_item.get("ctprvnNm", "") + api_item.get("signguCd", "")
        kind = api_item.get("clType", "")
        volume = api_item.get("clVol", "")
        price = api_item.get("clPc", "")
        # 우리 데이터에서 동일 시군구·종류·용량 찾기
        local_info = local_data.get(code, {})
        bags = local_info.get("bags", [])
        match = next((b for b in bags if str(b.get("종류")) == kind and str(b.get("용량")) == volume), None)
        if not match:
            differences.append(f"NEW: {code} {kind} {volume} {price}원")
        elif str(match.get("가격")) != str(price):
            differences.append(f"DIFF: {code} {kind} {volume} 로컬 {match.get('가격')}원 → API {price}원")

    return differences


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DATA_GO_KR_API_KEY"),
                    help="data.go.kr API 인증키 (Decoding)")
    args = ap.parse_args()

    if not args.key:
        print("[ERR] API 키 필요")
        print("발급: https://www.data.go.kr → '종량제봉투정보표준데이터' 활용신청")
        print("사용: python scripts/sync_bag_prices.py --key YOUR_KEY")
        print("또는: 환경변수 DATA_GO_KR_API_KEY 설정")
        return 1

    print("=== 행안부 봉투 가격 동기화 (단계 A — 비교만) ===")
    print(f"API: {API_URL}")
    print()

    print("[1/3] 행안부 API fetch...")
    items = fetch_all(args.key)
    print(f"  {len(items)}건 수신")

    if not items:
        print("[FAIL] API 응답 없음 — 키 확인 또는 sample API 응답 형식 점검 필요")
        return 1

    print()
    print("[2/3] 우리 데이터 비교...")
    diffs = compare_with_local(items)
    print(f"  변경 감지: {len(diffs)}건")

    print()
    print("[3/3] 결과:")
    if not diffs:
        print("  ✅ 모두 일치 — 갱신 필요 없음")
    else:
        print(f"  ⚠️ 변경 사항 {len(diffs)}건:")
        for d in diffs[:20]:
            print(f"    - {d}")
        if len(diffs) > 20:
            print(f"    ... 외 {len(diffs) - 20}건")
        print()
        print("  💡 단계 A: 비교·알림만. 자동 갱신은 다음 단계 B에서.")
        print("  📝 갱신 시 — 위 변경 사항 확인 후 bag_prices.json 수동 편집")

    return 0


if __name__ == "__main__":
    sys.exit(main())
