#!/usr/bin/env python3
"""
D1 마이그레이션 — 정적 JSON → D1 SQL INSERT 문 생성
사용자 액션: 1회 (wrangler d1 execute 명령)

사용:
  python scripts/d1_migrate.py
  → data/migrations/v7_initial.sql 생성

그 후 (사용자 PC, wrangler 설치 후):
  npx wrangler d1 execute yeoguiseon-db --file=data/migrations/v7_initial.sql
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))


def sql_str(s):
    if s is None: return "NULL"
    s = str(s).replace("'", "''").replace("\n", " ").strip()
    return f"'{s}'"


def sql_json(obj):
    if obj is None: return "NULL"
    return f"'{json.dumps(obj, ensure_ascii=False).replace(chr(39), chr(39)+chr(39))}'"


def sql_int(v):
    if v is None: return "NULL"
    return str(int(v))


def sql_bool(b):
    return "1" if b else "0"


def main():
    out = [
        "-- 여기선 v7.0 D1 initial migration",
        "-- 정적 JSON → D1 (auto-generated)",
        "-- 주의: D1은 SQL BEGIN/COMMIT 거부 (JS API만 허용) → 트랜잭션 문 제외",
        "",
    ]

    # 1. items + aliases
    with open(os.path.join(ROOT, "data", "national_rules.json"), encoding="utf-8") as f:
        nat = json.load(f)
    items = nat.get("items", {})

    out.append(f"-- Items ({len(items)}) + Aliases")
    item_count = 0
    alias_count = 0
    for key, v in items.items():
        item_count += 1
        out.append(
            f"INSERT OR REPLACE INTO items (id, name, category, note, steps, confidence, source_url, source_name, source_grade, feature, caution, last_verified, region_variation, official_classification) "
            f"VALUES ({sql_str(key)}, {sql_str(v.get('name', key))}, {sql_str(v.get('category', 'general'))}, "
            f"{sql_str(v.get('note', ''))}, {sql_json(v.get('steps', []))}, {sql_str(v.get('confidence', 'medium'))}, "
            f"{sql_str(v.get('sourceUrl') or v.get('source'))}, {sql_str(v.get('sourceName'))}, {sql_str(v.get('sourceGrade'))}, "
            f"{sql_str(v.get('feature'))}, {sql_str(v.get('caution'))}, {sql_str(v.get('lastVerified'))}, "
            f"{sql_bool(v.get('regionVariation', False))}, {sql_json(v.get('official_classification'))});"
        )
        for a in (v.get("aliases") or []):
            alias = str(a).strip()
            if not alias: continue
            alias_count += 1
            out.append(
                f"INSERT INTO aliases (item_id, alias, alias_lower, source) "
                f"VALUES ({sql_str(key)}, {sql_str(alias)}, {sql_str(alias.lower())}, 'rule');"
            )

    out.append("")
    out.append(f"-- Regions + Exceptions")

    # 2. regions (from regions_meta.json + region_exceptions.json)
    with open(os.path.join(ROOT, "data", "regions_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    with open(os.path.join(ROOT, "data", "region_exceptions.json"), encoding="utf-8") as f:
        exc = json.load(f)

    level2 = meta.get("level2", {})
    exceptions = exc.get("exceptions", {})

    region_count = 0
    for code, info in level2.items():
        if not (code.isdigit() and len(code) == 5): continue
        region_count += 1
        bb = info.get("boundingBox", {})
        ex_info = exceptions.get(code, {})
        city_guide = ex_info.get("cityGuide")
        inherits = ex_info.get("_inherits")
        out.append(
            f"INSERT OR REPLACE INTO regions (code, name, short_name, parent_code, type, lat_min, lat_max, lng_min, lng_max, phone, official_url, inherits_from, city_guide) "
            f"VALUES ({sql_str(code)}, {sql_str(info.get('name'))}, {sql_str(info.get('shortName'))}, "
            f"{sql_str(info.get('parent'))}, {sql_str(info.get('type'))}, "
            f"{bb.get('minLat') or 'NULL'}, {bb.get('maxLat') or 'NULL'}, "
            f"{bb.get('minLng') or 'NULL'}, {bb.get('maxLng') or 'NULL'}, "
            f"{sql_str(info.get('phone'))}, {sql_str(info.get('officialUrl'))}, "
            f"{sql_str(inherits)}, {sql_json(city_guide)});"
        )

    # 3. region_exceptions (FK 보장: item_id가 items에 있는 것만)
    valid_item_ids = set(items.keys())
    exc_count = 0
    exc_skipped = 0
    for code, ex_info in exceptions.items():
        if not (code.isdigit() and len(code) == 5): continue
        for item_id, rule in (ex_info.get("exceptions") or {}).items():
            if not isinstance(rule, dict): continue
            if item_id not in valid_item_ids:
                exc_skipped += 1
                continue  # FK 위반 방지
            exc_count += 1
            out.append(
                f"INSERT OR REPLACE INTO region_exceptions (region_code, item_id, category, note, steps, confidence, source_url, source_grade) "
                f"VALUES ({sql_str(code)}, {sql_str(item_id)}, {sql_str(rule.get('category'))}, "
                f"{sql_str(rule.get('note'))}, {sql_json(rule.get('steps', []))}, "
                f"{sql_str(rule.get('confidence'))}, {sql_str(rule.get('source'))}, {sql_str(rule.get('sourceGrade'))});"
            )
    if exc_skipped:
        out.append(f"-- [경고] FK 위반으로 skip된 region_exceptions: {exc_skipped}건 (item_id가 items 테이블에 없음)")

    out.append("")
    out.append(f"-- Version record")
    out.append(
        f"INSERT INTO data_versions (version, area, change_count, note) "
        f"VALUES ('v7.0-initial', 'all', {item_count + alias_count + region_count + exc_count}, "
        f"'D1 initial migration from JSON');"
    )
    out.append("")

    output_path = os.path.join(ROOT, "data", "migrations")
    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, "v7_initial.sql")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"✓ 생성: {out_file}")
    print(f"  items: {item_count}")
    print(f"  aliases: {alias_count}")
    print(f"  regions: {region_count}")
    print(f"  region_exceptions: {exc_count}")
    print(f"\n다음 단계 (사용자 PC):")
    print(f"  1. npm install -g wrangler")
    print(f"  2. wrangler login")
    print(f"  3. wrangler d1 create yeoguiseon-db")
    print(f"  4. wrangler d1 execute yeoguiseon-db --file=data/migrations/v7_initial.sql")


if __name__ == "__main__":
    main()
