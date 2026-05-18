# 문제 해결 가이드

## 서버 시작 문제

### start.bat 더블클릭 시 창이 바로 꺼져요
**원인**: Python 미설치 또는 PATH에 없음
**해결**:
1. https://www.python.org/downloads/ 에서 Python 3 설치
2. 설치 마법사에서 **"Add Python to PATH"** 옵션 반드시 체크
3. 설치 후 PC 재부팅
4. 명령 프롬프트에서 `python --version` 확인

### "포트 8001이 이미 사용 중" 에러
**해결**:
```bash
# 명령 프롬프트(관리자)에서
netstat -ano | findstr :8001
# PID 확인 후
taskkill /F /PID <PID>
```

## 브라우저 문제

### http://localhost:8001/ 접속 안 됨
**확인**:
- start.bat 명령창이 계속 열려있는가? (닫으면 서버 종료)
- 주소 정확한가? (`/app/` 같은 거 빼고 `/` 만)
- 방화벽이 막고 있지 않은가?

### "Unsafe attempt to load URL" 에러
**원인**: HTML 파일을 직접 더블클릭으로 열었을 때
**해결**: 반드시 서버 통해 http://localhost:8001/ 로 접속

### 카메라 권한이 안 떠요
**해결**:
1. 주소창 좌측 자물쇠 아이콘 클릭
2. 카메라 권한 → "허용"
3. 페이지 새로고침

### 화면이 깨져 보여요
**해결**: Ctrl+Shift+R (강제 새로고침으로 캐시 무시)

## API 키 문제

### "API 키가 올바르지 않습니다"
**확인**:
- 설정 → API 키와 제공자(Google/Claude)가 일치하는가?
- 키 앞뒤 공백 없는가?
- Gemini 키: AIzaSy로 시작
- Claude 키: sk-ant-로 시작

### "AI 사용량 한도 초과" (429 에러)
**해결**:
- Gemini 무료 한도: 분당 15회, 일일 1500회 (2025 기준)
- 잠시 후 (분당 한도면 1분) 다시 시도
- 자주 발생하면 Claude로 전환 또는 유료 플랜

### 분석 결과가 이상해요
**원인**: 사진이 흐리거나 여러 물건이 보일 때
**해결**:
- 가이드 박스 안에 물건 한 개만
- 충분한 조명
- 라벨이 잘 보이게 촬영

## 데이터 문제

### 우리 동네 지역이 없어요
**해결**: 현재는 강남구와 일산서구만 지원
- "정보 틀려요" 버튼으로 요청 가능
- regions.json에 추가 후 PR 환영 (향후)

### "정보 틀려요" 누르면 어디로 가요?
**현재**: mailto: 링크로 이메일 작성 화면 열림
**향후**: Google Form 또는 신고 대시보드 연동 예정

## 모바일 문제

### 폰에서 안 열려요
**확인**:
- PC와 폰이 같은 와이파이?
- PC 방화벽이 8001 포트 허용?
- 폰 브라우저 URL이 `http://192.168.x.x:8001` 형식?

PC IP 확인:
```
# 명령 프롬프트
ipconfig
# "IPv4 주소" 찾기
```

### iOS에서 카메라가 안 켜져요
**확인**:
- iOS 14.5+ 인가? (이전 버전은 PWA 카메라 제한)
- Safari 사용 (Chrome iOS는 일부 제한)
- HTTPS 환경인가? (Vercel 배포 후)

### 홈 화면 추가 후 카메라가 안 됨
**해결**: HTTPS 환경에서만 PWA 카메라 동작
→ 로컬 서버 대신 Vercel 배포 권장 (DEPLOY_GUIDE.md 참조)

## 기타

### 모든 데이터 초기화하고 싶어요
**방법**:
1. 앱 설정 → "모든 데이터 삭제" 버튼
2. 또는 브라우저 F12 → Application → Storage → Clear site data

### 캐시가 너무 많이 쌓였어요
**해결**: 자동 관리됨 (최대 20개, FIFO)
강제 청소: 위의 "모든 데이터 초기화" 또는 콘솔에서
```javascript
Object.keys(localStorage).filter(k => k.startsWith('yeoguiseon.cache')).forEach(k => localStorage.removeItem(k))
```

### 코드 수정하고 싶어요
- `app.html` 한 파일에 모든 코드 있음
- 수정 후 브라우저 강제 새로고침 (Ctrl+Shift+R)
- 백업: `app.html.backup` 으로 복사 후 작업
