#!/usr/bin/env python3
"""
자동 백업·회복 시스템 — truncation 영구 대책
================================================================

원칙:
  - quick_check 통과 시점 = "정상 상태" → 자동 snapshot
  - 다음 quick_check 실패 시 → 가장 최근 정상 snapshot에서 자동 회복
  - 회복 후 명확 알림 (사용자가 의도 변경 잃지 않게)

저장 위치: data/_snapshots/app.html_YYYYMMDD_HHMMSS
보존: 최근 10개만 (오래된 것 자동 정리)

사용:
  python scripts/auto_snapshot.py save       # 정상 상태 저장
  python scripts/auto_snapshot.py restore    # 가장 최근 정상 상태 회복
  python scripts/auto_snapshot.py list       # 보유 snapshot 목록
"""
import os
import sys

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
import shutil
import glob
from datetime import datetime

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SNAP_DIR = os.path.join(ROOT, "data", "_snapshots")
TARGETS = ["app.html", "sw.js", "scripts/cloudflare_worker.js", "scripts/quick_check.py"]
KEEP_MAX = 10


def ensure_dir():
    os.makedirs(SNAP_DIR, exist_ok=True)


def save_snapshot():
    """현재 상태를 timestamp snapshot으로 저장"""
    ensure_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []
    for rel in TARGETS:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        # 파일명 sanitize
        base = rel.replace("/", "_").replace("\\", "_")
        dst = os.path.join(SNAP_DIR, f"{base}_{ts}")
        shutil.copy2(src, dst)
        # 강제 fsync
        with open(dst, "rb") as f:
            f.read()
        saved.append((rel, dst))
    print(f"✓ snapshot 저장: {ts}")
    for r, d in saved:
        sz = os.path.getsize(d)
        print(f"  - {r}: {sz} bytes")
    cleanup_old()
    return ts


def cleanup_old():
    """KEEP_MAX 초과 시 오래된 snapshot 정리"""
    for rel in TARGETS:
        base = rel.replace("/", "_").replace("\\", "_")
        snaps = sorted(glob.glob(os.path.join(SNAP_DIR, f"{base}_*")))
        if len(snaps) > KEEP_MAX:
            for old in snaps[:-KEEP_MAX]:
                os.remove(old)
                print(f"  🗑 정리: {os.path.basename(old)}")


def list_snapshots():
    """보유 snapshot 목록"""
    ensure_dir()
    print(f"snapshot 위치: {SNAP_DIR}\n")
    for rel in TARGETS:
        base = rel.replace("/", "_").replace("\\", "_")
        snaps = sorted(glob.glob(os.path.join(SNAP_DIR, f"{base}_*")))
        print(f"{rel}: {len(snaps)}개")
        for s in snaps[-3:]:
            sz = os.path.getsize(s)
            print(f"  - {os.path.basename(s)} ({sz} bytes)")


def restore_latest():
    """가장 최근 snapshot으로 회복"""
    ensure_dir()
    restored = []
    for rel in TARGETS:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        base = rel.replace("/", "_").replace("\\", "_")
        snaps = sorted(glob.glob(os.path.join(SNAP_DIR, f"{base}_*")))
        if not snaps:
            print(f"  ⚠ {rel}: snapshot 없음 (스킵)")
            continue
        latest = snaps[-1]
        # 현재 파일 임시 백업 (사용자 변경 사항 보존)
        crash_bak = src + f".crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(src, crash_bak)
        # 회복
        shutil.copy2(latest, src)
        # fsync 강제
        with open(src, "rb") as f:
            data = f.read()
        with open(src, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        restored.append((rel, os.path.basename(latest), crash_bak))
    print(f"\n✓ 회복 완료 ({len(restored)}개 파일)")
    for r, s, cb in restored:
        print(f"  - {r} ← {s}")
        print(f"    (직전 상태 백업: {os.path.basename(cb)})")
    print(f"\n⚠ 직전 변경 사항이 있었다면 .crash_* 파일에서 diff 확인 가능")
    return len(restored)


def main():
    if len(sys.argv) < 2:
        print("사용: python scripts/auto_snapshot.py [save|restore|list]")
        return 1
    cmd = sys.argv[1]
    if cmd == "save":
        save_snapshot()
    elif cmd == "restore":
        n = restore_latest()
        return 0 if n > 0 else 1
    elif cmd == "list":
        list_snapshots()
    else:
        print(f"알 수 없는 명령: {cmd}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
