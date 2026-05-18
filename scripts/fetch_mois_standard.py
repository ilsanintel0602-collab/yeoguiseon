#!/usr/bin/env python3
"""
행정안전부 공공데이터포털 표준데이터 정기 동기화
- 전국종량제봉투가격표준데이터 (#15025538)
- 전국재활용센터표준데이터 (#15021108)
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

DATASETS = {
    "bag_prices": {
        "publicDataPk": "15025538",
        "svcTableNm": "tn_pubr_public_pyspmtbi_prce_svc",
        "raw_path": os.path.join(DATA_DIR, "raw_bag_prices_mois.json"),
    },
    "recycle_centers": {
        "publicDataPk": "15021108",
        "svcTableNm": "tn_pubr_public_ruse_cnter_svc",
        "raw_path": os.path.join(DATA_DIR, "raw_recycling_centers.json"),
    },
}


def fetch_standard(public_pk: str, svc_table: str, per_page: int = 10000):
    """data.go.kr 표준데이터 직접 다운로드 URL 호출"""
    base = "https://www.data.go.kr/download/standard.json"
    params = {
        "publicDataPk": public_pk,
        "svcTableNm": svc_table,
        "perPage": per_page,
        "page": 1,
    }
    r = requests.get(base, params=params, timeout=30, headers={
        "User-Agent": "yeoguiseon-sync/1.0",
        "Accept": "application/json",
    })
    r.raise_for_status()
    return r.json()


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 저장: {path} ({os.path.getsize(path)/1024:.0f} KB)", flush=True)


def main():
    failed = []
    for name, cfg in DATASETS.items():
        print(f"\n📥 {name} 다운로드 중...", flush=True)
        try:
            data = fetch_standard(cfg["publicDataPk"], cfg["svcTableNm"])
            # data.go.kr 응답 포맷이 두 가지 — list 또는 {records: [...]}
            if isinstance(data, dict) and "records" in data:
                count = len(data["records"])
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 0
            print(f"  ✅ {count}개 레코드", flush=True)
            save_json(data, cfg["raw_path"])
        except Exception as e:
            print(f"  ❌ {name} 실패: {e}", flush=True)
            failed.append(name)
        time.sleep(2)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
