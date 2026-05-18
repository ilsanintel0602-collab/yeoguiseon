# 🆚 RecycleAi 벤치마크 (경쟁자 분석)

> 사용자가 2026-05-15 (금) 받아서 직접 테스트한 앱
> 우리(여기선)의 비교 대상이자 능가 목표

## 기본 정보

| 항목 | 값 |
|---|---|
| 이름 | RecycleAi |
| 개발자 | mrsure1 |
| GitHub | https://github.com/mrsure1/RecycleAi |
| APK 다운로드 | https://github.com/mrsure1/TrashAi/releases/download/v1.0.0/app-debug.apk |
| 버전 | v1.0.0 (2026-05-15 출시) |
| 라이선스 | 미공개 (Public 저장소) |
| 같은 강의/교육 출신? | 가능성 높음 (같은 problem.md 구조, CLAUDE.md 존재) |

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 메인 언어 | Kotlin 67.4% |
| 백엔드 | Python 21.1% |
| DB | PostgreSQL (PLpgSQL 2.1%) |
| 빌드 | Gradle (Android Studio) |
| 플랫폼 | Android 네이티브 |
| AI 모델 | Custom YOLO (TFLite 추정, 분리수거 전용 학습) |

## 폴더 구조

```
RecycleAi/
├── .claude/         (Claude 협업 흔적)
├── app/             (Android 앱 모듈)
├── data/            (분리수거 데이터)
├── docs/            (문서)
├── gradle/          (빌드)
├── scripts/         (Python 크롤러 등)
├── ui/              (UI 컴포넌트)
├── CLAUDE.md        (Claude 작업 기록)
├── PRD.md           (제품 요구사항)
├── problem.md       (페르소나 - 우리와 동일)
├── build.gradle.kts
├── gradle.properties
├── requirements.txt
└── settings.gradle.kts
```

## 사용자 실측 결과 (2026-05-17 테스트)

### RecycleAi 동작 (스크린샷 기반)
1. 앱 실행
2. 카메라 켜자마자 **실시간 박스 표시** (5개 객체 박스)
3. 박스 탭 → "AI가 분석 중... (이미지 42KB)" 1~2초
4. **"혹시 이 품목인가요?"** 후보 UI:
   - 플라스틱
   - 플라스틱 노끈
   - 플라스틱 도마
   - 플라스틱 서랍장
   - PCR 플라스틱
   - 쌀통(플라스틱 재질)
5. 사용자가 정답 선택 → 최종 분류

### 여기선 v3 동작 (같은 사진)
1. 사진 촬영 (수동, 실시간 X)
2. AI 분석 5초
3. 결과: **"재활용 무관" (일반쓰레기)** — 오답!
4. 신뢰도 59% (낮음)
5. "일반 가이드" 배지

**결론: RecycleAi 압승**

## 핵심 강점 비교

| 항목 | RecycleAi | 여기선 v3 |
|---|---|---|
| **정확도** | ⭐⭐⭐⭐⭐ (한국 제품 인식) | ⭐⭐ (COCO-SSD 한계) |
| **속도** | ⭐⭐⭐⭐⭐ (네이티브 NPU) | ⭐⭐⭐ (TF.js WebGL) |
| **실시간 박스** | ✅ | ❌ |
| **후보 UI** | ✅ ("혹시 이것?") | ❌ |
| **API 키** | 불필요 | 옵션 (LLM 폴백) |
| **iOS** | ❌ | ✅ |
| **설치** | APK | URL (PWA) |
| **앱스토어** | ❌ | ❌ (둘 다) |
| **지역 데이터** | 미확인 | 250 시군구 ✅ |
| **지역 비교 카드** | 미확인 | ✅ |
| **운영비** | 0원 | 0원 |
| **푸시 알림** | (네이티브 가능) | iOS 제한 |
| **개발 복잡도** | 높음 (Kotlin+Python+DB) | 낮음 (단일 HTML) |
| **배포 속도** | 느림 (APK 재배포) | 빠름 (파일 수정만) |

## 우리가 능가해야 할 것 (우선순위)

### 1순위: 정확도
- **현재:** COCO-SSD = 한국 제품 못 알아봄
- **목표:** Custom YOLO + OCR + 브랜드 DB = RecycleAi 수준

### 2순위: 실시간 카메라 박스
- **현재:** 사진 찍은 후만 분석
- **목표:** 카메라 켜면 즉시 박스 (RecycleAi 패턴)

### 3순위: 후보 선택 UI
- **현재:** 결과 하나만 표시
- **목표:** Top 5 후보 + 사용자 선택

## 우리가 이미 더 좋은 것 (지키기)

1. ✅ **iOS+Android+PC 모두 지원** (RecycleAi는 Android만)
2. ✅ **설치 불필요** (URL 공유 가능)
3. ✅ **전국 250 시군구 데이터**
4. ✅ **지역별 비교 카드** (강남↔일산)
5. ✅ **다크 모드** + **PWA 홈 화면 설치**
6. ✅ **빠른 배포·업데이트**

## 전략 결론

**v4 핵심 미션:**
> **RecycleAi의 정확도 + 우리의 플랫폼 우위 = 진짜 일등 앱**

핵심:
- 정확도 (Custom YOLO + OCR + 브랜드 DB)
- 실시간 박스 (UX)
- 후보 UI (UX)
- 우리만의 강점 유지 (iOS, 지역, PWA)

## 협조 vs 경쟁

- 같은 강의/교육 출신일 가능성 ↑
- 둘 다 학습 프로젝트일 수 있음
- 분리수거는 공공의 이익 → 경쟁보다 보완 가능
- 향후: 데이터 공유, 코드 참고 등 협업 가능성

## 참고 링크

- RecycleAi 저장소: https://github.com/mrsure1/RecycleAi
- 한국 AI Hub (생활폐기물 데이터): https://aihub.or.kr/
- Roboflow Universe (TACO 등): https://universe.roboflow.com/
- Tesseract.js (한국어 OCR): https://github.com/naptha/tesseract.js
