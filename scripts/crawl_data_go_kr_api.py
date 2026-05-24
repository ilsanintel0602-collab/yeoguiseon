#!/usr/bin/env python3
"""
data.go.kr REST API 자동 크롤러 (GitHub Actions용)
=====================================================

CSV 수동 다운로드 폐기, API 키로 자동 호출.

사용:
  python crawl_data_go_kr_api.py --area medicine --output data/medicine_bins.json
  python crawl_data_go_kr_api.py --area clothes --output data/clothes_bins.json
  ...

환경변수: DATA_GO_KR_API_KEY (GitHub Secrets에 등록)

영역별 endpoint:
  - medicine: 폐의약품 수거함 (15012005 류)
  - clothes:  의류수거함
  - iot:      무인회수기
  - lamp:     폐형광등 수거함
  - battery:  폐건전지 수거함

(주: 실제 endpoint URL은 data.go.kr에서 영역별 신청 시 받은 URL 사용)
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

# 영역별 API endpoint + 메타
AREA_CONFIG = {
    "medicine": {
        "label": "폐의약품 수거함",
        "icon": "💊",
        "endpoint": "https://api.data.go.kr/openapi/tn_pubr_public_lung_medicine_api",
        "show_when_category": ["medicine"],
        "var_name": "MEDICINE_BINS",
    },
    "clothes": {
        "label": "의류수거함",
        "icon": "👕",
        "endpoint": "https://api.data.go.kr/openapi/tn_pubr_public_clothing_collect_bins_api",
        "show_when_category": ["clothes"],
        "var_name": "CLOTHES_BINS",
    },
    "lamp_battery": {
        "label": "폐형광등·폐건전지 수거함",
        "icon": "💡🔋",
        "endpoint": "https://api.data.go.kr/openapi/tn_pubr_public_waste_lamp_battery_collection_box_api",
        "show_when_category": ["lamp", "battery"],
        "var_name": "LAMP_BATTERY_BINS",
    },
    "furniture_fee": {
        "label": "대형폐기물 수거 수수료",
        "icon": "🛋",
        "endpoint": "https://api.data.go.kr/openapi/tn_pubr_public_lar_was_fee_api",
        "show_when_category": ["furniture"],
        "var_name": "FURNITURE_FEE",
    },
}


def fetch_api(endpoint, api_key, page=1, per_page=1000):
    """data.go.kr OpenAPI 호출 — User-Agent + 재시도 (Windows WinError 10054 대응)"""
    import time
    params = {
        "serviceKey": api_key,
        "pageNo": page,
        "numOfRows": per_page,
        "type": "json",
    }
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) YeoguiseonCrawler/1.0",
        "Connection": "close",
    }
    for retry in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            wait = 2 ** retry  # 1s, 2s, 4s
            if retry < 2:
                print(f"  [재시도 {retry+1}/3] {e} — {wait}초 후 재시도")
                time.sleep(wait)
                continue
            print(f"[ERR] API 호출 실패 (3회 시도): {e}")
            return None


def normalize_item(raw_item, area_type):
    """표준 데이터셋 행을 우리 포맷으로 변환 (data.go.kr 실제 필드명 검증 완료 2026-05-24)"""
    return {
        "sggCode":  raw_item.get("insttCode") or raw_item.get("sigunguCode") or raw_item.get("SIGUN_CD"),
        "sidoName": raw_item.get("ctpvNm") or raw_item.get("ctprvnNm") or raw_item.get("SIDO_NM"),
        "sggName":  raw_item.get("sggNm") or raw_item.get("insttNm") or raw_item.get("signguNm") or raw_item.get("SGG_NM"),
        "name":     raw_item.get("instlPlcNm") or raw_item.get("instlPlace") or raw_item.get("fcltyNm") or raw_item.get("NAME"),
        "address":  raw_item.get("lctnRoadNm") or raw_item.get("lctnLotnoAddr") or raw_item.get("rdnmadr") or raw_item.get("lnmadr") or raw_item.get("ADDR"),
        "lat":      raw_item.get("lat") or raw_item.get("latitude") or raw_item.get("LAT"),
        "lng":      raw_item.get("lot") or raw_item.get("longitude") or raw_item.get("LON") or raw_item.get("LNG"),
        "phone":    raw_item.get("mngInstTelno") or raw_item.get("phoneNumber") or raw_item.get("TEL"),
        "managedBy": raw_item.get("mngInstNm") or raw_item.get("managedBy"),
    }


def main():
    args = sys.argv[1:]
    area = None
    output = None
    for i, a in enumerate(args):
        if a == "--area" and i + 1 < len(args): area = args[i + 1]
        elif a == "--output" and i + 1 < len(args): output = args[i + 1]

    if not area or area not in AREA_CONFIG:
        print(f"--area 필요: {list(AREA_CONFIG.keys())}")
        return 1

    api_key = os.environ.get("DATA_GO_KR_API_KEY")
    if not api_key:
        print("[ERR] DATA_GO_KR_API_KEY 환경변수 필요")
        print("로컬: set DATA_GO_KR_API_KEY=...")
        print("GitHub Actions: Settings → Secrets → DATA_GO_KR_API_KEY")
        return 1

    cfg = AREA_CONFIG[area]
    print(f"\n=== {cfg['icon']} {cfg['label']} API 크롤링 ===")
    print(f"  endpoint: {cfg['endpoint']}")

    if not cfg["endpoint"]:
        print(f"[SKIP] endpoint 미설정 — 환경변수 ENDPOINT_{area.upper()} 또는 SECRETS에 추가 필요")
        return 0

    all_items = []
    page = 1
    while True:
        data = fetch_api(cfg["endpoint"], api_key, page=page)
        if not data: break

        # data.go.kr OpenAPI 표준 응답 구조 (response.body.items)
        body = (data.get("response", {}).get("body") or data.get("body") or {})
        items = body.get("items") or body.get("data") or []
        if isinstance(items, dict):
            items = items.get("item", [])
        if not items:
            break

        for raw in items:
            normalized = normalize_item(raw, area)
            if normalized.get("name") and normalized.get("address"):
                all_items.append(normalized)

        total = int(body.get("totalCount", 0) or 0)
        if len(all_items) >= total:
            break
        page += 1
        # data.go.kr 부하 회피 — 페이지 간 1초 대기
        import time
        time.sleep(1)

    # 시군구별 그룹화
    from collections import defaultdict
    by_sgg = defaultdict(list)
    for it in all_items:
        key = it.get("sggCode") or it.get("sggName") or "unknown"
        by_sgg[key].append(it)

    output_data = {
        "$schema": f"여기선 v6 - {cfg['label']} (data.go.kr API 자동 크롤링)",
        "version": "auto",
        "lastUpdated": datetime.now().isoformat(),
        "source": "행정안전부 공공데이터포털 (data.go.kr OpenAPI)",
        "area_type": area,
        "label": cfg["label"],
        "icon": cfg["icon"],
        "show_when_category": cfg["show_when_category"],
        "totalBins": len(all_items),
        "sggCount": len(by_sgg),
        "data": dict(by_sgg),
    }

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n저장: {output}")
    print(f"수거함 {len(all_items)}건, {len(by_sgg)} 시군구")
    return 0


if __name__ == "__main__":
    sys.exit(main())
