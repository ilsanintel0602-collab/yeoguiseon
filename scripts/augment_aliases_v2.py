#!/usr/bin/env python3
"""
augment_aliases v2 — 안전한 데이터 증강 (중간 저장 + 이어가기)
================================================================

v1 대비 개선:
- 매 25개 처리마다 자동 저장 (national_rules.json 갱신)
- 진행 상황 별도 기록 (augment_progress.json) — 다음 실행 시 자동 이어감
- Ctrl+C 또는 핫스팟 끊김 시 손실 최소화 (최대 25개)
- 이미 alias가 충분한 아이템은 자동 건너뛰기 (--skip-rich)

사용 (배치 모드):
  augment_v2.bat 더블클릭 (전체)
  python scripts/augment_aliases_v2.py --limit 100 (100개만 추가)
  python scripts/augment_aliases_v2.py --skip-rich 5 (5개 이상 가진 건 건너뛰기)

진행 파일: data/.augment_progress.json (gitignore 권장)
"""
import json
import os
import sys
import time
import shutil
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
NAT = os.path.join(ROOT, "data", "national_rules.json")
PROGRESS = os.path.join(ROOT, "data", ".augment_progress.json")
WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev/augment"
SAVE_EVERY = 25  # 25개마다 자동 저장

VALID_CATEGORIES = {
    "plastic", "paper", "paper_pack", "vinyl", "can", "glass", "styrofoam",
    "food", "general", "battery", "lamp", "clothes", "electronics",
    "furniture", "hazardous", "medicine", "reusable",
}


def call_worker(name, category, existing, count=12):
    payload = json.dumps({
        "item_name": name, "category": category,
        "existing_aliases": existing[:5], "count": count,
    }).encode("utf-8")
    req = urllib.request.Request(
        WORKER_URL, data=payload, method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": "https://ilsanintel0602-collab.github.io",
            "User-Agent": "Mozilla/5.0 yeoguiseon-augment/2.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("ok") and isinstance(data.get("aliases"), list):
            return data["aliases"]
        return []
    except Exception as e:
        print(f"  [err] {name}: {e}")
        return []


def validate(new_list, name, category, existing, all_known):
    out = []
    seen = set()
    BAD_CROSS = {
        "plastic": ["종이", "유리", "캔", "음식", "밥"],
        "paper": ["페트병", "플라스틱", "캔", "유리"],
        "food": ["플라스틱", "유리", "캔", "전자"],
        "battery": ["옷", "책", "음식", "유리병"],
    }
    bad = BAD_CROSS.get(category, [])
    for a in new_list:
        if not isinstance(a, str): continue
        a = a.strip()
        if not (2 <= len(a) <= 30): continue
        if a in existing or a == name: continue
        if a.lower() in all_known: continue
        if a in seen: continue
        if any(b in a for b in bad): continue
        seen.add(a)
        out.append(a)
    return out


def load_progress():
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"completed_keys": [], "total_added": 0, "last_index": 0}


def save_progress(prog):
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)


def save_data(data):
    with open(NAT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    args = sys.argv[1:]
    limit = None
    skip_rich = None
    reset = "--reset" in args
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        elif a == "--skip-rich" and i + 1 < len(args):
            skip_rich = int(args[i + 1])

    # 백업
    BAK = NAT + ".backup_pre_augment_v2.json"
    if not os.path.exists(BAK):
        shutil.copy(NAT, BAK)
        print(f"백업 생성: {BAK}")

    # 진행 상황 로드
    progress = {"completed_keys": [], "total_added": 0, "last_index": 0} if reset else load_progress()
    completed = set(progress["completed_keys"])

    with open(NAT, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]

    all_known = set()
    for k, v in items.items():
        all_known.add(k.lower())
        n = v.get("name")
        if n: all_known.add(n.strip().lower())
        for a in (v.get("aliases") or []):
            all_known.add(a.strip().lower())

    target_items = list(items.items())
    if limit:
        target_items = target_items[:limit]

    print(f"\nWorker: {WORKER_URL}")
    print(f"전체 items: {len(items)} / 처리 대상: {len(target_items)}")
    print(f"이미 완료: {len(completed)}건 (건너뜀)")
    print(f"자동 저장: {SAVE_EVERY}개마다")
    print(f"이어가기: {'OFF (reset)' if reset else 'ON'}\n")

    total_added = progress["total_added"]
    batch_added = 0
    processed_in_session = 0

    try:
        for i, (key, item) in enumerate(target_items, 1):
            if key in completed:
                continue

            name = item.get("name", key)
            category = item.get("category", "general")
            existing = item.get("aliases") or []

            if category not in VALID_CATEGORIES:
                completed.add(key)
                continue

            if skip_rich is not None and len(existing) >= skip_rich:
                completed.add(key)
                continue

            print(f"[{i}/{len(target_items)}] {name} ({category}) — 현재 {len(existing)} aliases")
            new_aliases = call_worker(name, category, existing)
            valid = validate(new_aliases, name, category, existing, all_known)

            if valid:
                for v in valid:
                    existing.append(v)
                    all_known.add(v.lower())
                item["aliases"] = sorted(set(existing))
                total_added += len(valid)
                batch_added += len(valid)
                print(f"  + {len(valid)}개: {valid[:5]}{'...' if len(valid) > 5 else ''}")
            elif new_aliases:
                print(f"  생성 {len(new_aliases)} → 검증 통과 0")
            else:
                print(f"  [빈 응답] (재시도 후보)")

            completed.add(key)
            processed_in_session += 1

            # 25개마다 자동 저장 (안전망)
            if processed_in_session % SAVE_EVERY == 0:
                save_data(data)
                progress["completed_keys"] = list(completed)
                progress["total_added"] = total_added
                progress["last_index"] = i
                save_progress(progress)
                print(f"  ✓ 자동 저장 (누적 +{total_added}, 배치 +{batch_added})\n")
                batch_added = 0

            time.sleep(0.3)

        # 끝까지 완료
        save_data(data)
        progress["completed_keys"] = list(completed)
        progress["total_added"] = total_added
        save_progress(progress)
        print(f"\n✓ 모두 완료. 추가 alias: {total_added}건")

    except KeyboardInterrupt:
        # Ctrl+C — 안전 저장
        print("\n\n⚠️  중단 감지 — 안전 저장 진행 중...")
        save_data(data)
        progress["completed_keys"] = list(completed)
        progress["total_added"] = total_added
        save_progress(progress)
        print(f"✓ 저장 완료. 누적 +{total_added}건")
        print(f"  다음 실행 시 자동 이어감 (이미 완료: {len(completed)}건 건너뛰기)")


if __name__ == "__main__":
    main()
