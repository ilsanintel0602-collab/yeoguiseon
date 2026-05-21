# Phase B1 — Colab 노트북 셀 교체용 패치
> **목적**: 이전 세션에서 실패한 AI Hub 인증을 2025년 공식 `-aihubapikey` 방식으로 교체
> **대상 노트북**: `scripts/train_yolo_colab.ipynb`
> **작성일**: 2026-05-19
> **출처**: https://aihub.or.kr/devsport/apishell/list.do (공식 가이드)

## 무엇이 바뀌었나
- ❌ 이전 (실패): `AIHUB_ID` / `AIHUB_PW` 환경변수 → aihubshell이 무시
- ✅ 변경: `-aihubapikey '발급받은-API-키'` 인자 직접 전달
- 모드도 정확화:
  - `-mode l` = 파일 목록 (list)
  - `-mode d` = 데이터셋 전체 다운로드
  - `-mode pd` = 부분 다운로드 (파일키 지정)

---

## 🔧 교체 셀 #1 — cell-5 인증 (전체 덮어쓰기)

```python
# AI Hub Shell 다운로드 (최신 버전, 기존 셀의 wget URL은 동일하게 사용 가능)
!wget -q https://api.aihub.or.kr/api/aihubshell.do -O /usr/local/bin/aihubshell
!chmod +x /usr/local/bin/aihubshell

# 인증: 2025년부터는 API 키 방식 (ID/PW 방식 deprecated)
from getpass import getpass

AIHUB_API_KEY = getpass('AI Hub API 키 입력 (aihub.or.kr 마이페이지 발급): ').strip()

# 환경변수로도 저장 (다음 셀에서 편의용)
import os
os.environ['AIHUB_API_KEY'] = AIHUB_API_KEY

# 검증: -help 출력 (네트워크/실행 권한 확인)
!aihubshell -help 2>&1 | head -20

print('\n✅ aihubshell 설치 완료. 다음 셀에서 -aihubapikey 인자로 사용.')
```

---

## 🔧 교체 셀 #2 — cell-7 파일 목록 조회 (전체 덮어쓰기)

```python
# AI Hub 데이터셋 #71385 (재활용선별장 인공지능 데이터) 파일 목록 조회
# 출력에서 어플리케이션 A2(품목별 이미지) + A4(라벨링)의 filekey 확인 후 다음 셀에서 사용
!aihubshell -mode l -datasetkey 71385 -aihubapikey "$AIHUB_API_KEY"
```

**확인 포인트**:
- 출력에 `[파일명 | 용량 | filekey]` 형식 행이 보여야 OK
- "Authentication failed" / "Invalid API key" 같은 메시지면 키 잘못 입력 → 다시
- 출력에서 `재활용선별장_A2_*` (이미지)와 `재활용선별장_A4_*` (라벨) 행의 filekey 메모

---

## 🔧 교체 셀 #3 — cell-8 부분 다운로드 (전체 덮어쓰기)

```python
# A2 (어플리케이션 이미지) + A4 (라벨링) 부분 다운로드
# ★ 아래 FILEKEYS는 위 셀 출력에서 실제 값으로 교체해야 함
import os

DATA_DIR = '/content/aihub_data'
os.makedirs(DATA_DIR, exist_ok=True)
os.chdir(DATA_DIR)

# 예: A2 첫 part 1개 + A4 첫 part 1개 (총 ~11GB 예상)
# 실제 filekey는 cell-7 출력에서 복사해 아래 리스트에 추가
FILEKEYS_TO_DOWNLOAD = [
    # 'XXXXXX',  # A2 part 1 filekey 여기에
    # 'YYYYYY',  # A4 part 1 filekey 여기에
]

# 디스크 여유 확인
!df -h /content

for fk in FILEKEYS_TO_DOWNLOAD:
    print(f'\n=== 다운로드 시작: filekey={fk} ===')
    # -mode pd = partial download (파일키 지정)
    !aihubshell -mode pd -datasetkey 71385 -filekey {fk} -aihubapikey "$AIHUB_API_KEY"

# 다운로드 확인
!ls -la /content/aihub_data/
!du -sh /content/aihub_data/
```

**진행 팁**:
- Colab 무료 디스크 ~80GB 한도 → 11GB 정도면 안전
- 다운로드 중 끊기면 같은 셀 재실행 (이어받기 지원 가정)
- 다운로드 완료 후 압축 해제: 보통 `.tar` 또는 `.zip` → `tar -xf` / `unzip`

---

## 🆘 인증 실패 시 디버그 순서

1. **키 형식 확인**: `1234ABCD-EFGH-1234-ABCD-1234567890AB` 형태 (UUID 유사). 따옴표 안 함부로 추가/제거.
2. **키 유효성**: aihub.or.kr 마이페이지 → API 키 재발급 가능
3. **데이터셋 신청 상태**: #71385가 "승인" 상태여야 다운로드 가능. "신청 중"이면 거부됨.
4. **aihubshell 버전**: `aihubshell -help` 출력 첫 줄에 버전. 2024 이후 버전이어야 `-aihubapikey` 지원.
5. **재시도**: 동일 명령 1-2회 재실행 (서버 일시 오류 가능)

---

## ➡️ 인증 성공 후 다음 단계 (자동)

`cell-7` 성공 (파일 목록 출력) → 사용자가 filekey 알려줌 → `cell-8` 다운로드 → `cell-10~16` 전처리 + 학습 (기존 셀 그대로 진행) → Phase B 진행.

학습 자체는 3~5일 자동, Colab Pro 권장 (무료는 12h 끊김 위험).
