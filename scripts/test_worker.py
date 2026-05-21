#!/usr/bin/env python3
"""Worker /augment 진단 도구 — 응답 전체 그대로 출력"""
import json
import urllib.request

WORKER_URL = "https://yeoguiseon-proxy.ilsanintel0602.workers.dev/augment"

payload = json.dumps({
    "item_name": "노트북",
    "category": "electronics",
    "existing_aliases": ["laptop"],
    "count": 6,
}).encode("utf-8")

req = urllib.request.Request(
    WORKER_URL, data=payload, method="POST",
    headers={
        "Content-Type": "application/json",
        "Origin": "https://ilsanintel0602-collab.github.io",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) yeoguiseon-test/1.0",
        "Accept": "application/json",
    },
)

print("=== Worker /augment 진단 ===")
print(f"URL: {WORKER_URL}")
print(f"Item: 노트북 (electronics)")
print()

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        status = resp.status
    print(f"HTTP 상태: {status}")
    print()
    print("=== 응답 원본 (raw) ===")
    print(raw[:2000])
    print()
    try:
        data = json.loads(raw)
        print("=== 파싱된 응답 키 ===")
        print(list(data.keys()))
        print()
        if "parseHow" in data:
            print(f"✅ v1.7.1 활성 — parseHow={data.get('parseHow')}")
            print(f"raw_preview: {data.get('raw_preview', '?')[:200]}")
        else:
            print("❌ v1.7.1 미활성 — parseHow 없음. Cloudflare 재배포 필요.")
        print()
        aliases = data.get("aliases", [])
        print(f"aliases ({len(aliases)}개):")
        for a in aliases:
            print(f"  - {a}")
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e}")
except urllib.error.HTTPError as e:
    print(f"HTTP 에러: {e.code} {e.reason}")
    print(e.read().decode("utf-8", errors="replace")[:500])
except Exception as e:
    print(f"기타 오류: {type(e).__name__}: {e}")
