# scripts/fetch_mois_extended.py 사용 가이드

> **목표**: 기존 fetch_mois_standard.py 확장. 대형폐기물 신고 정보 + 폐기물 시설 데이터 추가 크롤링.
> **출처**: 행안부 공공데이터포털 (data.go.kr)
> **사용 시점**: v5.6.7 검증 후, 정확도 보강 위한 데이터 확장 단계

---

## 현재 상태

**자동 작성됨**: `scripts/fetch_mois_extended.py` (132줄)

**확인 필요**:
- 추정된 `publicDataPk` 값들이 실제로 존재하는지 검증 필요
- 후보:
  - `15013108` → 대형폐기물 처리 정보 (추정)
  - `15021108` → 폐기물처리시설 (이미 fetch_mois_standard.py에서 활용 중, 중복 확인 필요)

---

## PK 확인 방법 (5분, 사용자 직접)

1. 브라우저에서 https://www.data.go.kr 열기 (ilsanintel0602 계정으로 로그인 권장)
2. 우측 상단 검색창에서 검색:
   - **"대형폐기물"** 또는 **"생활폐기물 신고"** 입력
3. 결과 목록에서 **"표준데이터"** 마크가 있는 항목 클릭
4. URL 확인: `https://www.data.go.kr/data/XXXXXXXX/standard.do` → **XXXXXXXX**가 publicDataPk
5. 페이지 안에 **"오픈 API"** 또는 **"파일데이터"** 정보 확인:
   - "서비스명" 또는 "테이블명" = `svcTableNm` 값 (예: `tn_pubr_public_xxx_svc`)

찾은 PK + svcTableNm을 채팅에 보내주세요. 제가 scripts/fetch_mois_extended.py의 `DATASETS` 객체를 정확한 값으로 업데이트해드릴게요.

---

## 실행 방법 (PK 확정 후)

### 방법 1 — 사용자 PC에서 직접 실행

```cmd
cd "E:\Cowork 작업\yeoguiseon-v4"
python scripts\fetch_mois_extended.py
```

- 결과: `data/raw_bulky_waste_mois.json`, `data/raw_waste_facilities.json` 생성
- 시간: 약 1~3분 (네트워크 따라)
- 인증 불필요 (data.go.kr 표준데이터는 공개)

### 방법 2 — Colab에서 실행

```python
# Colab에서 행안부 스크립트 실행
import urllib.request
url = "https://raw.githubusercontent.com/ilsanintel0602-collab/yeoguiseon/main/scripts/fetch_mois_extended.py"
script = urllib.request.urlopen(url).read().decode("utf-8")
exec(script)
```

> Colab은 미국 IP라 차단될 수 있음. 사용자 PC가 안전.

---

## 다음 단계 (데이터 받은 후)

1. **정규화**: `scripts/normalize_and_merge.py` 활용 또는 새 스크립트로 NATIONAL_RULES와 통합
2. **분리수거 안내 보강**:
   - 결과 화면에 "**우리 동네 대형폐기물 신고하기**" 버튼 추가 (자동 링크)
   - 카테고리가 `furniture`일 때 자동 표시
3. **재활용 센터 시간/연락처 표시**:
   - 가까운 센터 정보 (data/recycle_centers.json와 보강)

---

## 우선순위 평가

| 데이터 | 효과 | 시급도 | 작업량 |
|---|---|---|---|
| 대형폐기물 신고 | "지금 신고하기" 버튼 활성화 — UX 큰 개선 | ⭐⭐⭐ | 1~2시간 |
| 폐기물 시설 정보 | 사용자가 "어디 버려요" 질문 답 | ⭐⭐ | 2~3시간 |
| 시군구 분리수거 표준 | 226개 시군구 룰 확장 (현재 일산동구만 상세) | ⭐⭐⭐ | 5~10시간 |

→ **벤치마크가 안정화된 후** 데이터 확장. 지금은 v5.6.7 검증 우선.
