# 사용자 피드백 학습 루프 — 사용자 매뉴얼

## 목적
사용자가 결과 카드에서 "다른 거에요" 누르면 Worker /feedback에 기록 → 주간 학습 사이클로 잘못된 매칭 보강.

## 1회 셋업 (Cloudflare KV 키)

1. Cloudflare 대시보드 → Workers → `yeoguiseon-proxy` → Settings → Variables and Secrets
2. **Add Variable**:
   - Type: **Secret**
   - Name: `FEEDBACK_DUMP_KEY`
   - Value: 임의 긴 문자열 (예: `xK9mP3qR7vW2zL8tH5jN4cF6yB1aD0sE`)
3. Save → Deploy
4. PC 워크폴더 루트 (`E:\Cowork 작업\yeoguiseon-v4`)에 **`.feedback_key.txt`** 파일 생성, 위 값 저장
5. `.gitignore`에 `.feedback_key.txt` 추가 (이미 있을 수 있음 — 확인)

## 주간 학습 실행 (베타 사용자 누적 후)

```cmd
cd "E:\Cowork 작업\yeoguiseon-v4"
scripts\learn_cycle.bat
```

또는 직접:
```cmd
set FEEDBACK_DUMP_KEY=xK9mP3qR7vW2zL8tH5jN4cF6yB1aD0sE
python scripts\learn_from_feedback.py
```

## 결과 확인

- `docs/feedback_learning/YYYY-MM-DD.md` 보고서 자동 생성
- 잘못 매칭된 케이스 + alias 보강 후보 정리

## 안전 원칙

- **자동 alias 적용 X** — 사용자가 보고서 검토 후 수동 적용
- 같은 잘못 3회+ = 우선 보강
- 적용 후 `python scripts\benchmark_db.py`로 정확도 변화 확인

## 자동화 (GitHub Actions)

- `.github/workflows/benchmark_weekly.yml` = 매주 일요일 21:00 UTC 자동 실행
- PAT workflow 권한 + FEEDBACK_DUMP_KEY GitHub Secrets 등록 필요

## 점검 흐름

```
사용자 결과 카드 → "다른 거에요" 클릭
   ↓
Worker /feedback (POST) → KV `fb:` 저장
   ↓
주간 cron → /feedback/dump → analyze_feedback.py
   ↓
docs/feedback_learning/*.md (보고서)
   ↓
사용자 검토 → NATIONAL.items alias 보강
   ↓
benchmark_db.py 재실행 → 정확도 변화 확인
```
