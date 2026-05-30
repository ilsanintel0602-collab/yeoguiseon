#!/usr/bin/env python3
"""
v6.30 본질 자동 정정 — disposal_path 일괄 추가
환경부 표준 기반: 명확한 종량제봉투 분기 items에 disposal_path: 'general_waste' 자동 추가
수거함 흐름 보호: steps에 '수거함' 있으면 제외 (의류수거함·전용수거함 등 재활용 흐름)
사용자 본질 명령 [feedback_self_check]: "끝까지 추적"
"""
import json, os, sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PATH = os.path.join(ROOT, 'data', 'national_rules.json')

with open(PATH, encoding='utf-8') as f:
    nat = json.load(f)
items = nat.get('items', {})

fixed = []
skipped_collection_box = []
for k, v in items.items():
    if v.get('disposal_path') == 'general_waste':
        continue
    cat = v.get('category')
    if cat in ('general', 'general_noncombustible'):
        continue
    steps = v.get('steps') or []
    if not steps:
        continue
    first_step = str(steps[0]).strip()
    all_steps = ' '.join(str(s) for s in steps)
    note_feature = (v.get('note') or '') + ' ' + (v.get('feature') or '')
    # 수거함 흐름 보호 — 의류수거함·전용수거함·폐의약품수거함 등 재활용 흐름
    if '수거함' in all_steps:
        skipped_collection_box.append(k)
        continue
    # 명확 조건 1: 첫 단계가 종량제봉투 (가장 강력)
    is_first_general = '종량제봉투' in first_step
    # 명확 조건 2: 재활용 불가/어려움 명시 + steps에 종량제봉투
    is_explicit_general = (
        ('재활용 불가' in note_feature) or
        ('재활용이 어렵' in note_feature) or
        ('재활용 공정 달라' in note_feature)
    ) and ('종량제봉투' in all_steps)
    if is_first_general or is_explicit_general:
        v['disposal_path'] = 'general_waste'
        fixed.append(f"{k}: '{v.get('name')}' ({cat})")

# Python fsync 표준 — truncation 사고 영구 차단 [feedback_edit_korean_truncation]
with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(nat, f, ensure_ascii=False, indent=2)
    f.flush()
    os.fsync(f.fileno())

print(f"\n[OK] disposal_path 자동 추가: {len(fixed)}건")
print(f"[INFO] 수거함 흐름 보호로 제외: {len(skipped_collection_box)}건")
print()
for line in fixed[:15]:
    print(f"  + {line}")
if len(fixed) > 15:
    print(f"  ... 외 {len(fixed) - 15}건")
print(f"\n파일 저장 완료: {PATH}")
print(f"\n다음: scripts/quick_check.bat 실행 → ❌ 0건 확인 후 push.bat")
