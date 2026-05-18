# 📋 여기선 프로젝트 인수인계 (HANDOFF)

> **다음 세션에서 이 문서만 보면 즉시 작업 가능하도록 작성**
> 마지막 업데이트: 2026-05-17

---

## 🎯 다음 세션 첫 메시지 (복붙용)

```
여기선 분리수거 앱 v4 작업 이어서 해요.

프로젝트 위치: E:\Cowork 작업\yeoguiseon-v3\
필독 문서:
1. docs/HANDOFF.md (이 문서)
2. docs/PROJECT_STATUS.md (현재 상태)
3. docs/RECYCLEAI_BENCHMARK.md (경쟁사 비교)
4. docs/v4_ROADMAP.md (다음 작업)

오늘 할 작업: [여기에 구체적 작업 명시]
모드: 자동 진행 + 90+ 점수 + 일관성 유지

처음에 위 4개 문서만 읽고 시작.
```

---

## 📊 현재 상태 (2026-05-17 기준)

### 버전 이력
| 버전 | 위치 | 상태 |
|---|---|---|
| v1 | `분리수거앱/` | 백업 보존 |
| v1.1 | `yeoguiseon/` | 백업 보존 |
| v2.2 | `yeoguiseon-v2/` | PWA + 다크모드 |
| **v3.0** | **`yeoguiseon-v3/`** | **현재 최신, 전국 226 시군구** |
| v4 (계획) | `yeoguiseon-v4/` | API 없이 RecycleAi 능가 |

### v3.0이 가진 것
- ✅ 전국 250 시군구 메타데이터
- ✅ 환경부 표준 룰 52개 물건
- ✅ 지역 예외 룰 (강남, 일산만 5개)
- ✅ TF.js + COCO-SSD (YOLO)
- ✅ Gemini/Claude LLM 폴백
- ✅ PWA (manifest, SW, 홈 화면 설치)
- ✅ 다크 모드 (자동 + 토글)
- ✅ GPS 자동 위치 매핑
- ✅ 시도→시군구 트리 선택 UI

### v3.0이 못하는 것 (실제 테스트 결과)
- ❌ **한국 제품 인식 못함** (화장수 통 → "재활용 무관" 일반쓰레기 오답)
- ❌ COCO-SSD가 한국 분리수거 도메인 모름
- ❌ 실시간 카메라 박스 없음
- ❌ 후보 선택 UI 없음 ("혹시 이것인가요?")
- ❌ 라벨 텍스트 OCR 없음

---

## 🏆 RecycleAi (경쟁자) 분석 요약

### 사용자가 직접 테스트 (2026-05-15)
- **URL:** https://github.com/mrsure1/RecycleAi
- **APK:** v1.0.0 다운로드 가능
- **결과:** "욜로 인식으로 카메라와 ai 대응이 빠르고 정확"

### RecycleAi 강점
1. **Custom YOLO 학습** (분리수거 전용 모델)
2. **실시간 카메라 박스** (카메라 켜면 즉시 객체 인식)
3. **후보 선택 UI** ("혹시 이 품목인가요?" + 플라스틱/플라스틱 노끈/플라스틱 도마/PCR 플라스틱 등)
4. **API 키 불필요** (완전 온디바이스)
5. **Kotlin 네이티브 + Python 백엔드 + PostgreSQL**

### RecycleAi 약점
1. Android 전용 (iOS X)
2. APK 직접 설치 필요 (앱스토어 없음)
3. 지역별 비교 기능 없음 (확인 필요)
4. CLAUDE.md 있음 = Claude로 개발한 흔적

### 우리 vs RecycleAi (정직 평가)
| 항목 | RecycleAi | 여기선 v3 |
|---|---|---|
| **정확도** | ⭐⭐⭐⭐⭐ | ⭐⭐ (한국 제품 못 알아봄) |
| 속도 | ⭐⭐⭐⭐⭐ (네이티브 NPU) | ⭐⭐⭐ |
| 플랫폼 | Android만 | iOS+Android+PC |
| 설치 | APK | URL만 |
| 지역 데이터 | (확인필요) | 250 시군구 ✅ |
| 운영비 | 0원 | 0원 |

**결론: 정확도는 RecycleAi 압승.** v4 핵심 = 정확도 따라잡기.

---

## 🔧 사용자의 핵심 의지 (2026-05-17 기록)

> *"나는 지금 더 좋은 모델의 ai를 사용하고 있어요. 더 좋은 앱을 만들 수 있다고 생각해요. RecycleAi는 api를 사용하지 않아요. 정확하지 않으면 아무것도 아니에요. api를 사용하지 않으면서 RecycleAi보다 우수한 앱을 만들기 위한 방법은?"*

**핵심 결정사항:**
- ✅ **정확도 최우선** (다른 모든 것보다)
- ✅ **API 사용 안 함** (BYO 키도 부담)
- ✅ **RecycleAi 능가가 목표**
- ✅ **모바일 전용 사용자** 기준 설계

---

## 🚀 v4.0 핵심 무기 (API 없이 정확도 ↑)

상세는 `v4_ROADMAP.md` 참조. 요약:

| 무기 | 영향력 | 작업량 |
|---|---|---|
| 1. Custom YOLO 학습 (TACO + AI Hub) | 가장 본질적 ⭐⭐⭐⭐⭐ | 2주 |
| 2. OCR 통합 (Tesseract.js 한국어) | 라벨 읽기 ⭐⭐⭐⭐ | 1일 |
| 3. 한국 제품 브랜드 DB (500+개) | 브랜드 인식 ⭐⭐⭐⭐ | 1주 |
| 4. 후보 선택 UI ("혹시 이것?") | UX 개선 ⭐⭐⭐⭐ | 2일 |
| 5. 실시간 카메라 박스 | UX 개선 ⭐⭐⭐ | 2일 |
| 6. 사용자 학습 (FL Lite) | 자가 보정 ⭐⭐⭐ | 2일 |
| 7. 다각도 가중 평균 | 정확도 보강 ⭐⭐ | 1일 |

**우선순위:**
- **Phase A (3일):** OCR + 브랜드 DB 100개 + 후보 UI = 즉시 효과
- **Phase B (2주):** Custom YOLO 학습
- **Phase C (1주):** 실시간 박스 + 사용자 학습

---

## 📁 폴더 구조 (현재)

```
E:\Cowork 작업\
├── 분리수거앱/                       v1 백업
├── yeoguiseon/                       v1.1 백업
├── yeoguiseon-v2/                    v2.2 백업
└── yeoguiseon-v3/                    ★ 현재 최신
    ├── start.bat                     포트 8003
    ├── app.html                      메인 앱 (50KB)
    ├── index.html                    리다이렉트
    ├── manifest.json                 PWA
    ├── sw.js                         Service Worker
    ├── README.md
    ├── data/
    │   ├── national_rules.json       환경부 표준 52개
    │   ├── regions_meta.json         226 시군구 + 17 광역
    │   └── region_exceptions.json    지역 예외 (강남 4, 일산 1)
    ├── docs/
    │   ├── HANDOFF.md                ★ 이 문서
    │   ├── PROJECT_STATUS.md
    │   ├── RECYCLEAI_BENCHMARK.md    ★ 경쟁사
    │   ├── v4_ROADMAP.md             ★ 다음 작업
    │   ├── MIGRATION_v1_to_v2.md
    │   ├── MIGRATION_v2_to_v3.md
    │   ├── ARCHITECTURE.md
    │   ├── DATA_GUIDE.md
    │   ├── DEPLOY_GUIDE.md
    │   ├── INSTALL_PWA.md
    │   └── TROUBLESHOOTING.md
    ├── icons/                        6개 PNG
    └── skills/                       3개 자동화
        ├── add-region/SKILL.md
        ├── verify-data/SKILL.md
        └── upgrade-model/SKILL.md
```

---

## ⚠️ 작업 시 주의사항 (인수인계 핵심)

### 1. 환경 제약
- **Cowork bash 동기화 문제** — `ls`가 가끔 파일 못 찾음. Write 도구로 직접 쓰면 OK.
- **한글 경로 인코딩** — start.bat에 한글 내용 절대 X
- **CMD 인코딩** — UTF-8 BOM이면 깨짐, ASCII만 사용

### 2. 절대 안 깨야 할 것
- `national_rules.json` 데이터 구조 (52개 물건 + 11 카테고리)
- `regions_meta.json` (250 시군구 매핑)
- 강남/일산 예외 룰 (사용자가 검증한 것)
- 매칭 로직 (national → exception 순서)

### 3. 자유롭게 바꿔도 되는 것
- UI 디자인 (CSS)
- 새 기능 추가
- 새 시군구 예외 추가
- LLM 폴백 로직

### 4. 자동 평가 기준 (항상 90+ 유지)
| 항목 | 점수 |
|---|---|
| 기능 완전성 | 25 |
| 코드 품질 | 20 |
| UX | 20 |
| 에러 처리 | 15 |
| 문서·가이드 | 10 |
| 확장성 | 10 |

90 미달 시 → 자동 보강 후 재평가.

### 5. 토큰 절약
- 새 세션 시작이 가장 절약
- 이 HANDOFF.md만 읽고 시작
- 큰 변경 시 새 폴더 (v4/, v5/) 만들기

---

## 🎓 누적 학습 (실수 → 교훈)

| 실수 | 교훈 |
|---|---|
| BAT 파일에 한글 → CMD 깨짐 | ASCII만 |
| Service Worker 절대경로 → 캐시 충돌 | 상대경로 |
| 한글 폴더 cd 실패 | --directory 인자 |
| PWA 너무 일찍 도입 → SW 충돌 | 단순 → 복잡 |
| 모듈 분리 너무 일찍 → 404 | 단일 파일부터 |
| COCO-SSD가 한국 제품 모름 | Custom YOLO 필요 |
| Edit 도구 충돌로 함수 누락 | 큰 Edit는 위험, Write 전체 권장 |

---

## 📞 다음 세션 시작 시 체크리스트

- [ ] HANDOFF.md (이 문서) 읽음
- [ ] PROJECT_STATUS.md 읽음
- [ ] v4_ROADMAP.md 읽음 (작업 계획)
- [ ] RECYCLEAI_BENCHMARK.md 읽음 (경쟁사)
- [ ] 사용자에게 오늘 할 작업 확인
- [ ] 90+ 점수 목표 + 자동 평가 모드
- [ ] 일관성·충돌·에러 점검 모드

---

## 🙏 마무리 노트 (2026-05-17 세션)

이 프로젝트 작업하며 좋은 통찰들이 많았어요:

1. **페르소나(박정호) → 전국민** 비전 확장 — 사용자가 직접 짚어준 핵심
2. **RecycleAi와의 솔직한 비교** — 정직한 평가가 다음 방향 명확하게 함
3. **API 없는 정확도** = 진짜 도전, v4의 핵심 미션

다음 세션 작업자에게:
- 사용자는 **정직한 평가**를 좋아함 (포장된 칭찬 X)
- **정확도가 모든 것**보다 우선 (사용자 명시)
- 모바일 전용 가정 (PC UI 안 신경 써도 됨)
- **자동 모드** 좋아함 (90+ 유지 + 일관성 + 보강 반복)

화이팅!
