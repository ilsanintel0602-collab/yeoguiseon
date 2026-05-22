#!/usr/bin/env python3
"""
bins JSON → D1 SQL 변환

크롤된 5개 영역 JSON 파일(medicine·clothes·iot·lamp·battery)을
D1 bins 테이블 INSERT SQL로 변환.

사용:
  python scripts/bins_to_sql.py
  → data/migrations/bins_initial.sql 생성

그 후:
  wrangler d1 execute yeoguiseon-db --remote --file=data/migrations/bins_initial.sql
"""
import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))

AREA_FILES = {
    "medicine": "data/medicine_bins.json",
    "clothes":  "data/clothes_bins.json",
    "iot":      "data/iot_bins.json",
    "lamp":     "data/lamp_bins.json",
    "battery":  "data/battery_bins.json",
}


def sql_str(s):
    if s is None or s == "":
        return "NULL"
    s = str(s).replace("'", "''").replace("\n", " ").strip()
    return f"'{s}'"


def sql_num(v):
    if v is None or v == "":
        return "NULL"
    try:
        return str(float(v))
    except (ValueError, TypeError):
        return "NULL"


def extract_bins(data):
    """JSON 데이터에서 bin 리스트 추출 (구조 다양성 대응)"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "bins", "list", "data", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def normalize_bin(raw, area_type):
    """다양한 컬럼명 → 표준 키로 정규화"""
    name = raw.get("name") or raw.get("시설명") or raw.get("명칭") or raw.get("FCLT_NM") or raw.get("fcltyNm")
    address = raw.get("address") or raw.get("주소") or raw.get("도로명주소") or raw.get("RN_ADDR") or raw.get("rnAddr")
    lat = raw.get("lat") or raw.get("위도") or raw.get("LAT") or raw.get("latitude")
    lng = raw.get("lng") or raw.get("lon") or raw.get("경도") or raw.get("LNG") or raw.get("longitude")
    phone = raw.get("phone") or raw.get("전화번호") or raw.get("TEL") or raw.get("tel")
    sgg_code = raw.get("sggCode") or raw.get("시군구코드") or raw.get("SIGUN_CD") or raw.get("sigunguCd")

    return {
        "area_type": area_type,
        "region_code": sgg_code,
        "name": name,
        "address": address,
        "lat": lat,
        "lng": lng,
        "phone": phone,
    }


def main():
    out = [
        "-- Phase A1-2: bins (수거함 위치) D1 입력",
        f"-- 생성: {datetime.now().isoformat()}",
        "-- 5개 영역: medicine·clothes·iot·lamp·battery",
        "",
        "-- 기존 데이터 정리 (재실행 시 안전)",
        "DELETE FROM bins;",
        "",
    ]

    total = 0
    summary = {}

    for area, rel_path in AREA_FILES.items():
        full_path = os.path.join(ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"  [SKIP] {rel_path} 없음 (먼저 crawl 스크립트 실행)")
            summary[area] = 0
            continue

        try:
            with open(full_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [ERR] {rel_path} 로드 실패: {e}")
            summary[area] = 0
            continue

        bins = extract_bins(data)
        out.append(f"-- {area} ({len(bins)} bins)")
        added = 0
        for raw in bins:
            n = normalize_bin(raw, area)
            if not n["name"] and not n["address"]:
                continue  # 이름·주소 둘 다 없으면 skip
            out.append(
                f"INSERT INTO bins (area_type, region_code, name, address, lat, lng, phone) "
                f"VALUES ({sql_str(n['area_type'])}, {sql_str(n['region_code'])}, "
                f"{sql_str(n['name'])}, {sql_str(n['address'])}, "
                f"{sql_num(n['lat'])}, {sql_num(n['lng'])}, {sql_str(n['phone'])});"
            )
            added += 1
        out.append("")
        summary[area] = added
        total += added
        print(f"  {area}: {added}개 INSERT")

    output_path = os.path.join(ROOT, "data", "migrations")
    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, "bins_initial.sql")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"\n✓ 생성: {out_file}")
    print(f"  총 {total}개 bin INSERT")
    print(f"  영역: {summary}")
    print(f"\n다음 단계 (사용자 PC):")
    print(f"  wrangler d1 execute yeoguiseon-db --remote --file=data/migrations/bins_initial.sql")


if __name__ == "__main__":
    main()
