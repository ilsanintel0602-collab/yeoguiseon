# 다음 세션 즉시 읽기 — 2026-05-25 v5.46 push 완료

## 🚨 사용자가 지금 멈춰 있는 곳

**1단계 완료**: ✅ `auto_push.bat` 실행 → GitHub push 성공 (commit `aff42c44`). Cloudflare Pages 자동 배포 진행 중.

**2단계 대기**: 🟡 사용자가 `deploy_worker.bat` 더블클릭만 하면 됨.
- 위치: `E:\Cowork 작업\yeoguiseon-v4\deploy_worker.bat`
- 이전에 `crawl_all.bat`을 잘못 클릭함 — 정확한 파일 안내 필요
- 처음이면 Cloudflare 브라우저 로그인 (`ilsanintel0602@gmail.com`)

**3단계 대기**: 🟡 사용자 모바일 시연 검증 (PWA 새로고침 → v5.46 확인 → 6가지 시나리오)

## v5.46 누적 자산 (2026-05-25 최종)

- **app.html v5.46** (157KB, push 완료)
- **sw.js v5.46** (캐시 무효화)
- **Worker v1.9.13** (deploy 대기, Post-AI 가드레일 — `reusable`·`bulky` 임의 분류 차단)
- **items 776** (777→776, 한·영문 duplicate 5건 병합, '스프레' 잘림 정정)
- **categories 19** (tier A 14 환경부 / B 5 행정·시·구청)
- **ambiguous_map 13 키워드** (컵·박스·봉지·병·그릇·접시·용기·포장재·도시락·팩·접착제·라이스컨테이너·포장지)
- **OCR keywords 60** (+83 매칭 단어 라면·과자·우유·즉석밥·세제·약·캔·카페·스티로폼·의류·건전지·전구·영수증)
- **brand_db 135** (한국 식음료 26 추가)
- **region_exceptions 261** (cityGuide 235 + _inherits 28 — 전국 100% 안내)
- **재활용센터 fallback 118 시군구** (행안부 53% 누락 보완)
- **벤치마크 97.7/100** (환각 100%, 충돌 3건 진짜 모호만)

## v5.46 신규 정정 (v5.45 → v5.46)

### 데이터 정직성
1. `reusable` 카테고리 폐기 — 환경부 표준 외 임의 분류
2. `bulky` 카테고리 폐기 — `furniture`와 중복
3. categories에 tier A/B + source 메타 추가
4. reusable_cup·tumbler steps 정직 단순화 — "재사용 결정은 사용자가"
5. '스프레' 잘린 item → aerosol_can 19 aliases 병합
6. EN_KO_FALLBACK['reusable_cup'] = '재사용 컵' → '유리·머그·스테인리스 컵'

### UI 정직성 (사용자 직접 노출)
7. 결과 카드 카테고리 옆 tier 배지: ✅ 환경부 공식 / 🏛 시·구청 행정 (지자체별 차이)
8. 단일/다량 표 다크모드 가시성 (헤더 #dbeafe + 텍스트 #1f2937)
9. Gemini SYSTEM_PROMPT "임의 카테고리 금지" 강화

## 사용자 본질 명령 (절대 룰)

> "임의 X, 환경부·시·구청 공식만"

- Tier A 카테고리 (14개) = 환경부 분리배출 표시·자원순환·폐의약품 등 공식
- Tier B 카테고리 (5개) = 시·구청 행정 (지자체별 차이) — 라벨 명시 필수
- Gemini 출력 임의 분류 자동 차단 (Worker VALID_CATS)

## 시연 검증 시나리오 (사용자 push 후)

| 검색 | 기대 |
|---|---|
| 폐가전 노트북 | 박스-in-박스 X + 단일/다량 표 명확 + "전국 폐가전 예약 1599-0903" |
| 머그잔 | "재질로 분류, 재사용은 사용자 결정" + 🏛 시·구청 행정 배지 |
| 신라면·코카콜라 | ✅ 환경부 공식 배지 |
| 거주지 → 수원/전주 | 본청 cityGuide fallback 정상 |
| "박스"·"컵" 검색 | 모호 분기 UI ("어떤 박스?") |
| 살충제 사진 | "에어로졸 캔 (스프레이)" 잘림 X |

## 사고 기록 (자동 회복 시스템 정착)

**truncation 20회 발생, 20회 자동 회복**. 사용자 모바일 영향 0.
- 회복 방법: snapshot 차이 추출 + Python fsync
- crash 백업 보존: `.crash_truncated_v45*`, `.crash_truncated_v46_*` (분석용)
- snapshot 폴더: `data/_snapshots/` (16개 시점 보관)
- quick_check.py 4중 검사 (truncation·IIFE·init·JS syntax + 벤치 ≥80)
- auto_snapshot.py save/restore/list

**핵심 룰**: Edit 도구 한국어 50+줄 블록 = truncation 위험. Python fsync 회피. snapshot 차이 추출법으로 1분 이내 복구.

## 시연 후 옵션 (시연 결과 받기 전까지 진행 가능)

1. **MediaPipe Object Detection 사전 조사** — 카메라 자동 인식 점프 (시연 호소 "느림·실패" 대응)
2. **app.html 모듈 분할 설계** — truncation 영구 종결 (20회 누적)
3. **사진 벤치마크 가동** — pass@1 정량 측정 (사용자 사진 수집)
4. **시·구청 본문 추가 정독** — cityGuide 풍부화 (web fetch 제약 있음)

## 인계 명령어 (다음 세션 시작 시 즉시)

```bash
# 1. 현재 상태 확인
cd "E:\Cowork 작업\yeoguiseon-v4"
python scripts/quick_check.py  # 통과해야 함

# 2. 최신 push 확인
git log --oneline -5

# 3. snapshot 확인
ls data/_snapshots/ | tail -10
```

## 메모리 (자동 로드)

- `user_profile.md` — 경숙, 일산동구, 작업 계정 `ilsanintel0602@gmail.com`
- `feedback_workmode.md` — 자동 진행, 정확도 최우선, 임의 중단 X
- `project_v4_status.md` — v5.46 push 완료, 97.7/100, 전국 100%, truncation 20회
- `feedback_edit_korean_truncation.md` — snapshot 차이 추출 회복법 (20회 검증)
- `feedback_self_check.md` — push 전 검증 룰
- `feedback_region_codes.md` — 시군구 코드 매핑
- `feedback_css_stacking.md` — 모달 input 차단 함정
- `feedback_hidden_features.md` — UX 발견 경로
- `reference_data_sources.md` — 행안부·환경부 + AI Hub 차단
- `project_d1_infrastructure.md` — D1 라이브 미사용

## 컴퓨터 환경

- Windows + 한글 폴더 경로 (`E:\Cowork 작업\yeoguiseon-v4`)
- `.ps1` 더블클릭 X (메모장 열림) → `.bat` wrapper 사용
- `.bat`에 `chcp 65001`은 한글 경로 깨뜨림 — PowerShell wrap이 안전
- CMD CP949 인코딩 함정 → Python `PYTHONIOENCODING=utf-8` + `sys.stdout.reconfigure`

## 사용자가 시연하면 받을 수 있는 피드백 패턴

이전 시연 패턴 (v5.39~v5.45):
- 임의 결정 정직성 의문 (v5.46에서 reusable·tier 라벨로 정정)
- 박스-in-박스, 두 안내 같은곳 (v5.45 정정)
- 전화번호 라벨 부족 (v5.45 "전국 폐가전 예약" 등 정정)
- 단일/다량 표 빈칸 (v5.46 다크모드 색상 정정)
- 카메라 인식 느림 (v5.45 customBox crop 추가, MediaPipe는 미래 옵션)

새 시연 결과 → 즉시 정정 → push → 사이클 반복.
