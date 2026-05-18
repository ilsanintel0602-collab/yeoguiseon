---
name: handoff
description: 여기선 프로젝트 작업을 다음 세션에 인수인계하거나 이어받습니다. HANDOFF.md, PROJECT_STATUS.md, RECYCLEAI_BENCHMARK.md, v4_ROADMAP.md를 자동으로 읽고 작업 컨텍스트를 빠르게 복원합니다.
---

# 여기선 인수인계 스킬

다음 세션 시작 시 또는 작업 중간에 컨텍스트를 빠르게 복원/저장.

## 언제 사용?

- 새 세션 시작했을 때 ("여기선 작업 이어서")
- 다른 작업자가 이어받을 때
- 중간 점검·정리할 때
- 작업 끝낼 때 (다음 세션을 위해 상태 저장)

## 처리 단계

### 1단계: 핵심 문서 4개 자동 읽기

다음 4개 문서를 순서대로 Read:
1. `E:\Cowork 작업\yeoguiseon-v3\docs\HANDOFF.md` (전체 인수인계)
2. `E:\Cowork 작업\yeoguiseon-v3\docs\PROJECT_STATUS.md` (현재 상태)
3. `E:\Cowork 작업\yeoguiseon-v3\docs\RECYCLEAI_BENCHMARK.md` (경쟁사)
4. `E:\Cowork 작업\yeoguiseon-v3\docs\v4_ROADMAP.md` (다음 작업)

### 2단계: 사용자에게 현재 상태 보고

```
📋 여기선 프로젝트 인수인계 완료

✅ 현재 버전: v3.0 (전국 250 시군구)
⚠️ 알려진 문제: 정확도 (COCO-SSD가 한국 제품 못 알아봄)
🎯 다음 미션: v4 (API 없이 RecycleAi 능가)

다음 작업 후보:
1. Phase A1: OCR 통합 (1일, 즉시 효과)
2. Phase A2: 브랜드 DB 100개 (1~2일)
3. Phase A3: 후보 선택 UI (1~2일)
4. Phase B1: Custom YOLO 학습 (2주, 본질적)

오늘 무엇을 할까요?
```

### 3단계: 사용자 답변 받고 작업 진행

- 작업은 자동 모드 (90+ 점수 + 일관성 유지)
- 매 Phase마다 자동 평가
- 90 미만이면 자동 보강

### 4단계: 작업 종료 시 인수인계 갱신

작업 끝나면 다음 문서 자동 갱신:
- `PROJECT_STATUS.md` 진행 상황 추가
- `HANDOFF.md` 마지막 업데이트 시각 갱신
- 새 학습이나 실수 발견 시 "누적 학습" 섹션에 추가

## 안전 가드레일

- ❌ 사용자 승인 없이 v3 핵심 데이터 (national_rules.json, regions_meta.json) 수정 금지
- ❌ 강남/일산 예외 룰 임의 변경 금지 (사용자 검증한 것)
- ✅ 새 기능은 새 폴더 (v4/) 생성 권장
- ✅ Cowork bash 동기화 문제 대비 → Write 도구 우선 사용
- ✅ 한글 경로 인코딩 주의 → BAT 파일 ASCII만

## 출력 형식

작업 시작 시:
```
✅ 4개 문서 읽음
📊 현재 상태 요약: [한 줄]
🎯 다음 작업 후보 3개: [목록]
⚠️ 주의사항: [있다면]

오늘 어떤 작업할까요?
```

작업 종료 시:
```
✅ 완료한 작업: [요약]
📊 점수: [N/100]
📝 PROJECT_STATUS.md 갱신됨
🔜 다음 세션 추천: [구체 작업]
```

## 예시 사용

**새 세션 시작:**
```
사용자: "여기선 작업 이어서 해요"
스킬 실행: handoff
→ 4개 문서 읽음
→ 현재 상태 보고
→ 사용자가 작업 선택
→ 진행
```

**기존 세션 마무리:**
```
사용자: "오늘 작업 마무리하고 다음 세션 준비"
스킬 실행: handoff (종료 모드)
→ PROJECT_STATUS.md 갱신
→ HANDOFF.md 시각 업데이트
→ 다음 세션용 첫 메시지 템플릿 출력
```
