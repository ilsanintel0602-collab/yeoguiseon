#!/usr/bin/env python3
"""
행안부 공공데이터포털 표준 데이터셋 일반 크롤러

Phase 4 보강 영역 (시도 권장 순):
  - 폐의약품 수거함: data.go.kr 검색 "폐의약품" → publicDataPk 확정 후 사용
  - 의류수거함:     data.go.kr 검색 "의류수거함" 또는 "헌옷"
  - 무인회수기:     data.go.kr 검색 "무인회수기" 또는 "IoT 페트병"
  - 폐형광등:       data.go.kr 검색 "폐형광등 수거함"
  - 폐건전지:       data.go.kr 검색 "폐건전지 수거함"

사용 (사용자 PC에서):
    1. data.go.kr 접속 → 위 키워드 검색
    2. 표준 데이터셋 페이지 URL에서 publicDataPk 추출
       예: https://www.data.go.kr/data/15012005/standard.do → pk=15012005
    3. CSV 다운로드 → scripts/raw_data/<영역>.csv 저장
    4. python scripts/crawl_data_go_kr.py --csv scripts/raw_data/medicine.csv \
            --output data/medicine_bins.json \
            --type medicine
    5. data 디렉토리에 변환된 JSON 저장됨

CSV 컬럼 자동 매핑 (행안부 표준 헬퍼):
  - 시군구코드/sgg_code/SIGUN_CD → sggCode
  - 시설명/명칭/시설명/NAME → name
  - 주소/도로명주소/ADDR → address
  - 위도/lat/LAT → lat
  - 경도/lng/lon/LON → lng
  - 전화번호/연락처/TEL → phone
"""
import csv
import json
import os
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_DIR = os.path.join(ROOT, "data")

# 행안부 표준 데이터의 일반 컬럼 매핑 (자동 추측)
COLUMN_MAP = {
    "sggCode": ["시군구코드", "SIGUN_CD", "SGG_CD", "sgg_code", "sigungu_cd"],
    "sidoName": ["시도명", "SIDO_NM", "sido_name"],
    "sggName":  ["시군구명", "SIGUN_NM", "SGG_NM", "sgg_name"],
    "name":     ["시설명", "명칭", "NAME", "FCLT_NM", "fcltyNm", "지점명"],
    "address":  ["주소", "도로명주소", "지번주소", "RN_ADDR", "LOC_PLC", "ADDR"],
    "lat":      ["위도", "lat", "LAT", "Y", "yLat"],
    "lng":      ["경도", "lng", "lon", "LON", "X", "xLng"],
    "phone":    ["전화번호", "연락처", "TEL", "TEL_NO", "phoneNumber"],
    "hours":    ["운영시간", "OPR_TM", "운영"],
    "etc":      ["비고", "ETC", "REMARK"],
}

# 영역별 메타 (한국어 라벨, 카테고리, app.html 통합용)
AREA_META = {
    "medicine": {
        "label": "폐의약품 수거함",
        "icon": "💊",
        "show_when_category": ["medicine"],
        "var_name": "MEDICINE_BINS",
    },
    "clothes": {
        "label": "의류수거함",
        "icon": "👕",
        "show_when_category": ["clothes"],
        "var_name": "CLOTHES_BINS",
    },
    "iot": {
        "label": "무인회수기 (IoT 페트병)",
        "icon": "🤖",
        "show_when_category": ["plastic"],
        "var_name": "IOT_BINS",
    },
    "lamp": {
        "label": "폐형광등 수거함",
        "icon": "💡",
        "show_when_category": ["lamp"],
        "var_name": "LAMP_BINS",
    },
    "battery": {
        "label": "폐건전지 수거함",
        "icon": "🔋",
        "show_when_category": ["battery"],
        "var_name": "BATTERY_BINS",
    },
}


def normalize_column(header_row):
    """CSV 헤더를 표준 키로 매핑"""
    mapping = {}
    for idx, col in enumerate(header_row):
        col_clean = col.strip()
        for std, candidates in COLUMN_MAP.items():
            if col_clean in candidates or col_clean.lower() in [c.lower() for c in candidates]:
                mapping[idx] = std
                break
    return mapping


def parse_csv(path):
    """CSV → 표준 dict 리스트"""
    out = []
    # 한국어 CSV는 EUC-KR 또는 UTF-8-SIG 가능성
    for encoding in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            with open(path, encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                header = next(reader)
                col_map = normalize_column(header)
                print(f"  인코딩: {encoding}, 컬럼 매핑: {len(col_map)}/{len(header)}개")
                for row in reader:
                    if not row: continue
                    item = {}
                    for idx, std in col_map.items():
                        if idx < len(row):
                            item[std] = row[idx].strip()
                    if item.get("name") and item.get("address"):
                        out.append(item)
                break
        except UnicodeDecodeError:
            continue
    return out


def main():
    args = sys.argv[1:]
    csv_path = None
    output = None
    area_type = "medicine"

    for i, a in enumerate(args):
        if a == "--csv" and i + 1 < len(args): csv_path = args[i + 1]
        elif a == "--output" and i + 1 < len(args): output = args[i + 1]
        elif a == "--type" and i + 1 < len(args): area_type = args[i + 1]

    if not csv_path:
        print(__doc__)
        return

    if not os.path.exists(csv_path):
        print(f"[ERR] CSV 파일 없음: {csv_path}")
        return

    if not output:
        output = os.path.join(DATA_DIR, f"{area_type}_bins.json")

    if area_type not in AREA_META:
        print(f"[ERR] --type 지정 필요: {list(AREA_META.keys())}")
        return

    meta = AREA_META[area_type]
    print(f"\n=== {meta['icon']} {meta['label']} 크롤러 ===")
    print(f"  입력: {csv_path}")
    print(f"  출력: {output}")
    print()

    rows = parse_csv(csv_path)
    print(f"\n파싱 완료: {len(rows)}건")

    # 시군구별 그룹화
    by_sgg = defaultdict(list)
    for r in rows:
        sgg = r.get("sggCode") or r.get("sggName") or "unknown"
        by_sgg[sgg].append(r)

    print(f"시군구 분포: {len(by_sgg)}개")

    output_data = {
        "$schema": f"여기선 v6 - {meta['label']} (행안부 공공데이터포털)",
        "version": "1.0.0",
        "lastUpdated": __import__("datetime").datetime.now().isoformat(),
        "source": "행정안전부 공공데이터포털 (data.go.kr)",
        "area_type": area_type,
        "label": meta["label"],
        "icon": meta["icon"],
        "show_when_category": meta["show_when_category"],
        "totalBins": len(rows),
        "data": dict(by_sgg),
    }

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output}")
    print(f"\n=== 다음 단계 ===")
    print(f"1. app.html에 fetch 추가: fetch('./data/{os.path.basename(output)}')")
    print(f"2. 전역 변수 추가: let {meta['var_name']} = null;")
    print(f"3. renderResult 카드에서 카테고리 {meta['show_when_category']} 시 표시")
    print(f"4. DATA_INVENTORY.md 갱신")


if __name__ == "__main__":
    main()
