---
name: phase-progression
description: 여기선 v6 작업의 표준 진행 절차. 각 Phase 시작·진행·종결의 단계별 점검, 95점 자동 진행, 충돌·에러 방지 규칙. Phase 작업을 시작하거나 종결할 때 항상 이 절차를 따른다.
---

# Phase Progression 표준 절차

## 핵심 원칙

1. **95점 합격선** — 각 Phase는 95점 이상 도달 시 자동 다음 Phase 진행 (사용자 별도 결정 없이)
2. **일관성** — 이전 Phase에서 확립한 enum·스키마·키 명명을 절대 변경하지 않음
3. **자동 백업** — 데이터 수정 전 반드시 `.backup_pre_<phase>_<step>.json` 생성
4. **에러 방지** — JSON valid 검증, schema 준수, dry-run 우선
5. **롤백 가능** — 모든 단계는 백업으로 되돌릴 수 있어야 함

## Phase 시작 절차 (Stage A — 진입)

1. **자산 점검**: 해당 Phase 관련 기존 파일 모두 확인 (data/, scripts/, docs/)
2. **현 커버리지 측정**: 시작 시점의 점수 측정 (얼마나 부족한지)
3. **기준 확인**: `docs/PHASE_CRITERIA.md`의 해당 Phase 합격선 재확인
4. **충돌 점검**: 기존 카테고리 enum, 스키마, 키 명명과 충돌 없는지
5. **백업 생성**: 작업 전 자동 백업 (`*.backup_pre_phaseN.json`)

## Phase 진행 절차 (Stage B — 실행)

1. **dry-run 우선**: 큰 변경 전에 미리보기 출력 (--dry 옵션)
2. **단계별 검증**: 각 단계 후 JSON valid + schema 통과 확인
3. **로그 기록**: 작업 내역을 `docs/HANDOFF_*.md`에 누적
4. **에러 시 롤백**: 백업으로 즉시 복구

## Phase 종결 절차 (Stage C — 합격 검증 + 다음 진행)

1. **자체 점검 실행**: 해당 Phase의 점검 스크립트 자동 실행
2. **95점 도달 확인**:
   - **≥ 95** → ✅ 자동 다음 Phase 진행 (사용자 알림만)
   - **90 ≤ x < 95** → ⚠️ 약점 자동 보강 시도 (최대 2회), 그 후에도 미달 시 사용자에게 보고
   - **< 90** → ❌ 사용자에게 약점 보고 + 결정 요청
3. **메모리 갱신**: `project_v4_status.md`에 Phase 종결 표시
4. **HANDOFF 누적**: 작업 내역 + 다음 Phase 진입 알림

## 충돌 방지 절대 규칙

- **카테고리 enum 17개 고정**: `plastic, paper, paper_pack, vinyl, can, glass, styrofoam, food, general, battery, lamp, clothes, electronics, furniture, hazardous, medicine, reusable` — 절대 추가/변경 안 함
- **app.html SYSTEM_PROMPT의 enum과 일치 필수**: 데이터 카테고리는 항상 app.html과 동기화
- **sourceUrl 필수**: 새 item 추가 시 환경부 또는 지자체 공식 URL 반드시 부여
- **백업 보존**: `.backup_*.json`은 절대 삭제 안 함 (audit 비교용)
- **버전 일관성**: app.html title/brand/version + sw.js VERSION 항상 동기 갱신

## 에러 방지 체크리스트

- [ ] JSON valid 확인 (`json.load` 성공)
- [ ] 필수 필드 (name/category/steps) 완비
- [ ] category가 enum 17개 안에 있는지
- [ ] sourceUrl 부착 여부
- [ ] 중복 키 없는지
- [ ] alias 오염 없는지 (cross-category 검사)
- [ ] 한글 인코딩 (UTF-8 BOM 없음)

## Phase 자동 진행 예시

```
Phase 2 시작 → 자산 점검 → 작업 진행 → 자체 점검
  ├── 점수 97 → ✅ 자동 Phase 3 진행
  ├── 점수 92 → ⚠️ 약점 자동 보강 시도 → 재점검 → 96 → ✅ 진행
  └── 점수 85 → ❌ 사용자에게 보고 + 결정 요청
```

## 산출물 명명 규칙

- 스크립트: `scripts/phase{N}_<purpose>.py`
- 점검: `scripts/audit_phase{N}.py`
- 데이터 백업: `data/<file>.backup_pre_phase{N}.json`
- 문서: `docs/PHASE{N}_*.md`
- 보고: `audit_phase{N}_report.md`
