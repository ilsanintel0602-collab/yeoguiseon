#!/usr/bin/env python3
"""
행안부 추가 데이터 크롤링 — 대형폐기물 신고 표준 + 시군구 분리수거 표준

기존 scripts/fetch_mois_standard.py 확장.
정기 동기화 가능 (cron 또는 수동).

활용 목표:
1. **대형폐기물 신고 데이터**: 시군구별 신고 시스템 URL/전화/수수료
   → 앱에서 "지금 신고하기" 버튼 안내
2. **분리수거 표준 코드**: 시군구별 룰 보강 (현재 일산동구만 상세)
   → 226 시군구 전국 확장 데이터

출처: 공공데이터포털 (data.go.kr)
API 키: 사용자가 발급한 행안부 API 키 (환경변수 MOIS_API_KEY 또는 .env)
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# 추가로 크롤링할 행안부 표준데이터 후보 (data.go.kr에서 publicDataPk 확인 필요)
DATASETS = {
    # 1. 대형폐기물 처리 정보 (시군구별 신고 시스템)
    "bulky_waste_service": {
        "publicDataPk": "15013108",  # 추정 — 실제 PK는 data.go.kr에서 검색 필요
        "svcTableNm": "tn_pubr_public_bulky_wast_svc",
        "raw_path": os.path.join(DATA_DIR, "raw_bulky_waste_mois.json"),
        "description": "시군구별 대형폐기물 신고 시스템 URL/전화/수수료",
    },
    # 2. 폐기물처리시설 정보 (재활용센터 + 소각장 + 매립장)
    "waste_facility": {
        "publicDataPk": "15021108",  # 이미 활용 중 → 확장
        "svcTableNm": "tn_pubr_public_wast_disp_fclty_svc",
        "raw_path": os.path.join(DATA_DIR, "raw_waste_facilities.json"),
        "description": "전국 폐기물처리시설 위치/연락처/운영시간",
    },
    # 3. 시군구 분리수거 표준 코드 (확장 시 사용)
    # NOTE: data.go.kr에 정식 데이터셋이 있는지 확인 필요. 환경부 자료가 더 정확할 수도.
}


def fetch_dataset(public_pk: str, svc_table: str, per_page: int = 10000):
    """data.go.kr 표준데이터 직접 다운로드 URL 호출 (인증 불필요)."""
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
    print(f"💾 저장: {path} ({os.path.getsize(path)/1024:.1f} KB)")


def main():
    print("=" * 60)
    print("행안부 추가 데이터 크롤링 (대형폐기물 + 폐기물 시설)")
    print(f"실행: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = {}
    for name, cfg in DATASETS.items():
        print(f"\n📥 {name} ({cfg['description']})")
        try:
            t0 = time.time()
            data = fetch_dataset(cfg["publicDataPk"], cfg["svcTableNm"])
            save_json(data, cfg["raw_path"])
            results[name] = {
                "ok": True,
                "count": len(data) if isinstance(data, list) else len(data.get("body", [])),
                "elapsed_sec": time.time() - t0,
            }
        except Exception as e:
            print(f"❌ 실패: {e}")
            results[name] = {"ok": False, "error": str(e)}

    print("\n" + "=" * 60)
    print("결과 요약:")
    for name, r in results.items():
        status = "✅" if r["ok"] else "❌"
        detail = f"{r.get('count', 0)}건 ({r.get('elapsed_sec', 0):.1f}초)" if r["ok"] else r.get("error", "")
        print(f"  {status} {name}: {detail}")
    print("=" * 60)

    # 다음 단계 안내
    print("\n다음 단계:")
    print("  1. raw_*.json 파일이 정상 생성됐는지 확인")
    print("  2. scripts/normalize_and_merge.py 로 NATIONAL_RULES와 통합 가능")
    print("  3. 통합 후 app.html에서 결과 화면에 대형폐기물 신고 버튼 추가")


if __name__ == "__main__":
    main()
