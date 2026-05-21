---
name: pre-deploy-check
description: 여기선 PWA의 app.html·sw.js·Worker 코드 변경 후 GitHub commit 직전에 자동 검증. 프롬프트 길이·버전 동기화·평문 키·인터페이스 계약·JSON valid를 한 번에 검사해서 모바일 배포 후 발견되는 실수를 사전에 차단합니다.
---

# 배포 전 검증 스킬

`app.html`, `sw.js`, `scripts/cloudflare_worker.js`, `data/*.json` 수정 후 GitHub commit하기 전에 6가지를 자동 검사. 미달 시 commit 차단 + 정확한 조치 안내.

## 언제 사용?

- **자동 트리거**: app.html / sw.js / cloudflare_worker.js 를 Edit/Write 한 직후
- **수동 호출**: 사용자가 "commit해도 돼?" 또는 "배포 전 검증해줘" 요청 시
- **Phase 전환 직전**: v5.6.x → v5.7 등 메이저 변경 후

## 왜 만들어졌나 (실수 이력)

- **2026-05-20 (v5.6.2)**: SYSTEM_PROMPT를 어려운 케이스 7종 추가하면서 2600자로 늘림 → Worker `MAX_PROMPT_CHARS=2000` 거부 → 모바일에서 "prompt too long" 에러 → COCO-SSD 폴백 → "AL" 오분류. **사용자 모바일에서 발견될 때까지 못 잡음.**
- 이 스킬이 있었으면 commit 전에 차단됐을 것.

## 검사 항목 (6개, 모두 통과해야 deploy OK)

### ✅ 검사 1 — SYSTEM_PROMPT 길이 ≤ Worker MAX_PROMPT_CHARS

```bash
# Worker 한도 추출
MAX=$(grep -oP 'MAX_PROMPT_CHARS\s*=\s*\K\d+' scripts/cloudflare_worker.js)

# SYSTEM_PROMPT 길이 측정 (Python)
python3 -c "
import re
with open('app.html', encoding='utf-8') as f:
    txt = f.read()
m = re.search(r'const SYSTEM_PROMPT = \`(.*?)\`;', txt, re.DOTALL)
print(len(m.group(1)) if m else 'NOT_FOUND')
"
```

| 결과 | 판정 |
|---|---|
| length ≤ MAX × 0.9 | ✅ 통과 (10% 여유) |
| MAX × 0.9 < length ≤ MAX | ⚠️ 경고 (여유 < 10%, 다음 추가 시 위험) |
| length > MAX | ❌ **차단** — 압축 후 재실행 |

### ✅ 검사 2 — sw.js VERSION ↔ app.html 라벨 동기화

```bash
# sw.js의 VERSION
SW_VER=$(grep -oP "VERSION\s*=\s*'\K[^']+" sw.js)

# app.html의 표시 라벨 (2곳: <title>, <span class="version">)
TITLE_VER=$(grep -oP '<title>여기선 \K[^ ]+' app.html)
BRAND_VER=$(grep -oP '<span class="version">\K[^<]+' app.html)
```

3개 모두 일치해야 통과. 하나라도 다르면 ❌ — 라벨 한 곳만 빼먹는 실수 차단.

### ✅ 검사 3 — 평문 API 키 검색

```bash
grep -nE 'AIzaSy[A-Za-z0-9_-]{30,}|AQ\.[A-Za-z0-9_-]{40,}|sk-[A-Za-z0-9]{30,}' \
  app.html sw.js js/*.js scripts/cloudflare_worker.js 2>/dev/null
```

- 매치 0건 → ✅ 통과
- 매치 발견 → ❌ **차단** — GitHub secret scanning 알림 재발 위험. suffix 방식으로 변경 후 재실행.

### ✅ 검사 4 — categoryHint enum 일관성

SYSTEM_PROMPT의 `category_hint` 허용값 ↔ matchRule의 includes() 배열이 같은지 확인.

```bash
# SYSTEM_PROMPT의 enum 추출 (응답 형식 줄에서)
python3 -c "
import re
with open('app.html', encoding='utf-8') as f:
    txt = f.read()
prompt_enum = set(re.findall(r'category_hint[\"\\']:\\s*[\"\\']([^\"\\']+)', txt)[0].split('|'))
matcher_enum = set(re.findall(r\"\\['([\\w,\\s\\']+?)'\\]\\.includes\\(categoryHint\\)\", txt)[0].replace(\"'\",'').replace(' ','').split(','))
diff_a = prompt_enum - matcher_enum
diff_b = matcher_enum - prompt_enum
print('prompt에만:', diff_a)
print('matcher에만:', diff_b)
print('OK' if not (diff_a | diff_b) else 'MISMATCH')
"
```

- `MISMATCH` → ⚠️ 경고: 한 쪽에만 있는 카테고리는 폴백으로 빠짐. paper_pack·reusable·general 등 핵심 카테고리는 양쪽 동기화 필수.

### ✅ 검사 5 — JSON 파일 유효성

```bash
for f in data/*.json data/rules/*.json data/regions/*.json; do
  [ -f "$f" ] && python3 -m json.tool "$f" > /dev/null 2>&1 || echo "❌ INVALID: $f"
done
```

- 모두 valid → ✅
- 하나라도 깨짐 → ❌ **차단** (잘못된 JSON은 PWA에서 그냥 빈 화면)

### ✅ 검사 6 — DEPRECATED_KEY_SUFFIXES 형식

```bash
grep -A 10 'DEPRECATED_KEY_SUFFIXES' app.html | grep -oE "'[^']+'" | while read s; do
  # 따옴표 제거 + 길이 측정
  raw="${s//\'/}"
  len=${#raw}
  if [ "$len" -lt 6 ] || [ "$len" -gt 12 ]; then
    echo "⚠️ suffix 길이 의심: $s (len=$len)"
  fi
  # 평문 키 패턴 안 들어있는지
  if echo "$raw" | grep -qE '^(AIzaSy|AQ\.|sk-)'; then
    echo "❌ 평문 키 prefix 발견: $s"
  fi
done
```

## 검증 통과 후 출력 (사용자에게)

```
🔍 pre-deploy-check 결과 (v5.6.3)
====================================
✅ SYSTEM_PROMPT 길이: 1847 / 2000 chars (8% 여유)
✅ 버전 동기화: sw.js v5.6.3 == title v5.6.3 == brand v5.6.3
✅ 평문 키 검사: 매치 0건
✅ categoryHint enum: 양쪽 17개 일치
✅ JSON 파일: 12개 모두 valid
✅ DEPRECATED_KEY_SUFFIXES: 3개 (8자, prefix 안전)

🚀 commit 진행 OK. 추천 메시지:
   "v5.6.3 보안 + 정확도 (프롬프트 길이 수정)"
```

## 검증 실패 시 출력

```
🚫 pre-deploy-check 차단 (v5.6.2)
====================================
❌ SYSTEM_PROMPT 길이: 2587 / 2000 chars (29% 초과)
   → Worker가 거부합니다. 다음 중 하나:
   1. 프롬프트 압축 (어려운 케이스를 표 → 키워드 형식으로)
   2. Worker MAX_PROMPT_CHARS 늘리고 재배포 (사용자 작업 필요)

권장: 1번 (사용자 작업 X). 압축 패치 진행할까요?
```

## 처리 단계 (스킬 실행 흐름)

1. **변경 파일 식별**: `git status` 또는 최근 mtime 기반
2. **각 검사 병렬 실행** (1-6번, bash 한 번에)
3. **결과 종합**: 모두 ✅면 통과, 하나라도 ❌면 차단
4. **차단 시**: 정확한 조치 + 자동 수정 옵션 제시
5. **통과 시**: commit 메시지 추천 + 다음 단계 안내

## 안전 가드레일

- ❌ 검사 자체로 파일 수정하지 말 것 (read-only)
- ❌ 사용자 승인 없이 commit 진행하지 말 것
- ✅ 검사 실패 시 정확한 줄 번호·근거 제시
- ✅ "Worker 한도가 너무 빡빡함" 같은 메타 판단은 사용자에게 위임 (스킬이 임의로 한도 변경 X)
- ✅ 검사 결과는 PROJECT_STATUS.md에 짧게 기록 (날짜·버전·통과 여부)

## 예시 사용

**상황**: 정확도 패치 작업 중. SYSTEM_PROMPT에 어려운 케이스 7종 추가했음.

**자동 트리거**:
```
[Edit app.html: SYSTEM_PROMPT 영역]
→ pre-deploy-check 자동 실행
→ 검사 1 실패: 2600 chars > 2000
→ "commit 차단. 압축 패치 진행할까요?" 안내
→ 사용자: "응"
→ 압축 후 재검증 → 1847 chars ✅
→ commit 진행
```

**결과**: 모바일 배포 후 발견되던 실수가 commit 전에 차단됨.

## 확장 아이디어 (나중에)

- **검사 7**: WORKER_URL이 유효한지 fetch (HEAD 요청)
- **검사 8**: 새 item_id가 NATIONAL.items에 매핑되는지
- **검사 9**: A/B 비교 (이전 버전 vs 새 버전의 토큰 사용량 변화)
- **검사 10**: data/ 폴더 모든 룰에 source_url 존재하는지

이 항목들은 사용자 운영 패턴 보고 결정.
