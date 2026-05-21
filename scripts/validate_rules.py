"""
여기선 v4 — 룰 데이터 검증 스크립트
- JSON 스키마 검증
- source_url 100% 존재 확인
- 3-way 정합성 (national ↔ regional ↔ local) 충돌 검출
- 출처 신뢰도 등급 합리성 검사
사용법: python scripts/validate_rules.py
종료코드: 0 = OK, 1 = 검증 실패
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft7Validator
except ImportError:
    print("[!] jsonschema 미설치. pip install jsonschema --break-system-packages")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "data" / "schema"
RULES_DIR = ROOT / "data" / "rules"
REGIONS_FILE = ROOT / "data" / "regions" / "regions.json"

RULE_FILES = [
    ("national",   RULES_DIR / "national.json"),
    ("gyeonggi",   RULES_DIR / "regional_41_gyeonggi.json"),
    ("goyang",     RULES_DIR / "local_41280_goyang.json"),
    ("ilsandong",  RULES_DIR / "district_41281_ilsandong.json"),
]

VALID_SCOPE_LEVELS = ["national", "regional", "local", "district"]


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_schema(rules: list[dict], schema: dict, label: str) -> list[str]:
    errors: list[str] = []
    validator = Draft7Validator(schema)
    for i, rule in enumerate(rules):
        for err in validator.iter_errors(rule):
            errors.append(f"[{label}#{i} id={rule.get('id','?')}] {err.message} (path: {list(err.path)})")
    return errors


def check_source_urls(rules: list[dict], label: str) -> list[str]:
    errors = []
    for i, rule in enumerate(rules):
        url = rule.get("source_url", "").strip()
        if not url:
            errors.append(f"[{label}#{i} id={rule.get('id','?')}] source_url 비어있음 — 입력 금지 원칙 위반")
        elif not (url.startswith("http://") or url.startswith("https://")):
            errors.append(f"[{label}#{i} id={rule.get('id','?')}] source_url 형식 오류: {url}")
    return errors


def detect_conflicts(all_rules: dict[str, list[dict]]) -> list[str]:
    """
    같은 item에 대해 다른 method.short를 가진 룰이 여러 계층에 존재할 때 충돌로 간주.
    override 명시된 경우는 제외.
    """
    conflicts = []
    by_item: dict[str, list[tuple[str, dict]]] = {}
    for label, rules in all_rules.items():
        for rule in rules:
            item_key = rule.get("item", "").strip().lower()
            if not item_key:
                continue
            by_item.setdefault(item_key, []).append((label, rule))

    for item_key, entries in by_item.items():
        if len(entries) < 2:
            continue
        methods = {(e[1].get("method", {}).get("short") or "").strip() for e in entries}
        if len(methods) <= 1:
            continue
        # override 체인 확인
        ids = {e[1]["id"] for e in entries}
        overridden = set()
        for _, rule in entries:
            for ov in rule.get("overrides", []):
                overridden.add(ov)
        unresolved = ids - overridden
        if len(unresolved) > 1:
            conflicts.append(
                f"[CONFLICT] item='{item_key}' — 다른 method 존재: "
                + " | ".join(f"{lbl}:{r['id']}" for lbl, r in entries)
            )
    return conflicts


def check_source_tier_consistency(rules: list[dict], expected_min_tier: str, label: str) -> list[str]:
    tier_order = [
        "official_gov_national",
        "official_gov_regional",
        "official_gov_local",
        "official_industry",
        "secondary",
    ]
    warnings = []
    for rule in rules:
        tier = rule.get("source_tier", "")
        if tier == "secondary":
            warnings.append(f"[{label} id={rule.get('id','?')}] 출처가 secondary — 단독 근거 사용 금지 (보조용만)")
    return warnings


def main() -> int:
    print("=== 여기선 v4 룰 검증 ===")

    if not (SCHEMA_DIR / "rule.schema.json").exists():
        print("[FATAL] rule.schema.json 없음")
        return 1
    rule_schema = load_json(SCHEMA_DIR / "rule.schema.json")

    all_errors: list[str] = []
    all_warnings: list[str] = []
    all_rules: dict[str, list[dict]] = {}
    total_count = 0

    for label, path in RULE_FILES:
        if not path.exists():
            all_errors.append(f"[{label}] 파일 없음: {path}")
            continue
        rules = load_json(path)
        if not isinstance(rules, list):
            all_errors.append(f"[{label}] 최상위가 배열이 아님")
            continue
        all_rules[label] = rules
        total_count += len(rules)
        all_errors.extend(validate_schema(rules, rule_schema, label))
        all_errors.extend(check_source_urls(rules, label))
        all_warnings.extend(check_source_tier_consistency(rules, "official_gov_local", label))

    all_warnings.extend(detect_conflicts(all_rules))

    print(f"\n총 룰 수: {total_count}")
    print(f"오류: {len(all_errors)}")
    print(f"경고: {len(all_warnings)}")

    if all_errors:
        print("\n--- 오류 ---")
        for e in all_errors:
            print(" -", e)
    if all_warnings:
        print("\n--- 경고/충돌 ---")
        for w in all_warnings:
            print(" -", w)

    return 0 if not all_errors else 1


if __name__ == "__main__":
    sys.exit(main())
