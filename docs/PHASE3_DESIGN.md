# Phase 3 설계 — 사용자 피드백 시스템

> 목표: 모바일에서 발견된 약점을 자동 누적 → 매주 자동 보강 사이클

---

## 핵심 원칙

1. **사용자 동의 우선**: 옵트인 (기본 OFF)
2. **PII 자동 차단**: 얼굴·번호판 자동 블러
3. **익명화**: 사용자 식별 정보 절대 저장 안 함
4. **투명성**: 어떤 데이터가 누적되는지 사용자에게 명확

---

## 시스템 구조

```
[모바일 사용자]
     ↓ "이 결과 도움 됐어요?" 또는 "분류 잘못됐어요"
     ↓ 동의 후 익명화 전송
[app.html] 
     ↓ POST /feedback
[Cloudflare Worker]
     ↓ 두 가지 저장 옵션
     ├─ Worker KV (즉시 저장)
     └─ GitHub Issue (자동 생성, PAT 필요)
     
[개발자(경숙)]
     ↓ 매주 누적 확인
     ↓ 약점 패턴 발견 → boost_v5.py 자동 생성
[데이터 보강 사이클]
     ↓ Phase 1 audit + Phase 2 audit 재실행
     ↓ 점수 측정 → 자연스러운 95+ 도달
```

---

## 피드백 데이터 스키마

```json
{
  "id": "<uuid_v4>",
  "timestamp": "2026-05-21T10:30:00Z",
  "version": "v5.8.1",
  "region": "11680",  // 강남구
  "feedback_type": "wrong" | "unknown" | "good",
  "ai_result": {
    "item_id": "pet_bottle",
    "category": "plastic",
    "confidence": 0.92,
    "source": "llm" | "yolo" | "fallback"
  },
  "user_correction": "유리병",  // 사용자가 알려준 정답 (선택)
  "image_hash": "<sha256>",  // 사진 자체는 저장 안 함, 해시만
  "context": {
    "live_detections": ["bottle 92%", "vase 30%"],
    "skipped_fallback": false
  }
}
```

**저장 안 함**:
- ❌ 사진 원본 (해시만)
- ❌ 사용자 위치 정확치 (region 코드만)
- ❌ 사용자 식별자 (랜덤 uuid만)
- ❌ IP / 디바이스 정보

---

## 모바일 UI 흐름

### 결과 카드 하단에 추가
```
✨ Gemini AI 분석     [플라스틱]
페트병 (투명)
신뢰도: 높음 (92%)

[ 배출 방법 ... ]

─────────────────────────────
🤔 이 안내, 도움 됐어요?
  [ 👍 정확해요 ]  [ 👎 다른 거에요 ]

(눌렀을 때만)
사용자 동의: "익명으로 데이터 보내기" ☐
[ 보내기 ]  [ 취소 ]
```

### 사용자 동의 (옵트인)
첫 피드백 시 한 번만:
- "여기선 앱 개선을 위해 어떤 데이터를 익명으로 모을 수 있어요"
- 명시: 사진 저장 안 함, 위치 정확치 안 보냄, 식별자 없음
- 동의 후에만 활성화

---

## Cloudflare Worker 엔드포인트 (신규)

```javascript
// scripts/cloudflare_worker.js에 추가

if (path === '/feedback' && req.method === 'POST') {
  const data = await req.json();
  
  // PII 검증 (필드 검사)
  if (data.user_email || data.user_phone || data.ip) {
    return new Response(JSON.stringify({error: 'PII detected'}), {status: 400});
  }
  
  // Worker KV에 저장 (또는 GitHub Issue 생성)
  const id = crypto.randomUUID();
  await env.FEEDBACK_KV.put(id, JSON.stringify({...data, id}));
  
  return new Response(JSON.stringify({ok: true, id}), {status: 200});
}
```

---

## GitHub Issue 자동 생성 (선택)

PAT 필요. 옵션:
- **Worker secrets에 PAT 저장** (안전)
- 매 피드백마다 Issue 생성 (또는 매주 누적 Issue)
- Issue 라벨: `feedback:wrong`, `feedback:unknown`, `feedback:good`

```javascript
async function createGitHubIssue(feedback) {
  await fetch('https://api.github.com/repos/ilsanintel0602-collab/yeoguiseon/issues', {
    method: 'POST',
    headers: {
      'Authorization': `token ${env.GITHUB_PAT}`,
      'Accept': 'application/vnd.github+json'
    },
    body: JSON.stringify({
      title: `[feedback:${feedback.feedback_type}] ${feedback.ai_result.item_id}`,
      body: JSON.stringify(feedback, null, 2),
      labels: [`feedback:${feedback.feedback_type}`, `region:${feedback.region}`]
    })
  });
}
```

---

## 매주 누적 → 보강 사이클

### 스크립트: `scripts/analyze_feedback.py` (PC 실행)

1. Cloudflare Worker KV에서 피드백 dump (또는 GitHub Issues API)
2. 카테고리·지역별 약점 패턴 분석
3. 가장 빈도 높은 잘못된 분류 식별
4. boost_v5.py 자동 생성 (aliases 추가, RegionVariation 보강)
5. audit_phase1 + audit_phase2 재실행
6. 점수 도약 확인

```
pip install python-dateutil
python scripts/analyze_feedback.py
# 출력:
#  지난 1주: 152건 피드백
#  Top 약점:
#    1. "압력솥" → 알 수 없음 (12건, 강남구·송파구)
#    2. "캠핑용 가스버너" → 잘못된 분류 (8건)
#  자동 boost_v5_proposed.py 생성됨
#  적용하려면: python scripts/boost_v5_proposed.py
```

---

## Phase 3 합격선 (95점)

| 항목 | 배점 | 측정 |
|---|---|---|
| 모바일 피드백 UI 작동 | 25 | 결과 카드 하단 버튼 + 옵트인 동의 흐름 |
| Worker 피드백 엔드포인트 | 20 | /feedback POST 정상 + KV 저장 |
| PII 자동 차단 | 20 | 사진 해시만, 사용자 식별자 없음 검증 |
| 분석 스크립트 작동 | 15 | analyze_feedback.py 출력 정상 |
| 매주 자동 보강 안내 | 10 | boost_v5_proposed.py 자동 생성 |
| 사용자 옵트인 동의 흐름 | 10 | 첫 사용 시 명시적 동의 |
| **합계** | **100** | **합격선 95** |

---

## 구현 순서

1. **scripts/cloudflare_worker.js** — /feedback 엔드포인트 추가 (코드만, 배포는 사용자 결정)
2. **app.html** — 결과 카드 하단에 피드백 버튼 + 옵트인 흐름 추가
3. **scripts/analyze_feedback.py** — 누적 분석 + boost 자동 생성 스크립트
4. **docs/USER_PRIVACY.md** — 사용자에게 보이는 개인정보 정책

## Push 시점

Phase 3 **코드는 작성**하지만 **push는 사용자가 결정**. 다음 push 시점에 모두 함께 활성화.

---

## 의의

Phase 1·2는 "수집 가능한 공식 데이터" 수준. Phase 3은 **"실제 사용 사례에서 발견되는 약점"**을 누적하는 시스템. 시간이 지나면 모든 시군구의 진짜 차이가 데이터로 들어옴. **점진적 진화** 구조로 정확도 지속 향상.
