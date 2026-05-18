# 배포 가이드

여기선 앱을 인터넷에 올려서 누구나 접속할 수 있게 만드는 방법.

## 옵션 1: Vercel (가장 쉬움, 추천)

### 준비
- GitHub 계정 (https://github.com)
- Vercel 계정 (https://vercel.com — GitHub 로그인 가능)

### 단계
1. **GitHub 저장소 만들기**
   - https://github.com/new
   - 이름: `yeoguiseon` (또는 원하는 이름)
   - Public 선택
   - "Create repository"

2. **파일 업로드**
   - 만든 저장소 → "uploading an existing file" 클릭
   - `app.html`, `index.html`, `regions.json`, `README.md` 끌어다 놓기
   - "Commit changes"

3. **Vercel 연결**
   - https://vercel.com/new
   - GitHub 저장소 선택 → Import
   - Framework Preset: "Other" 선택
   - "Deploy" 클릭

4. **완료!**
   - 약 30초 후 https://yeoguiseon.vercel.app 같은 URL 생성
   - 폰에서도 접속 가능
   - HTTPS 자동

### 업데이트
GitHub 저장소에 파일 수정 → 자동으로 Vercel 재배포

## 옵션 2: Netlify (드래그앤드롭)

### 단계
1. https://app.netlify.com/drop 접속
2. `yeoguiseon` 폴더를 드래그앤드롭
3. 자동 배포, URL 생성

## 옵션 3: GitHub Pages

### 단계
1. GitHub 저장소 만들기 (위와 동일)
2. 파일 업로드
3. Settings → Pages → Source: `main` 브랜치 선택
4. 약 1분 후 `https://USERNAME.github.io/yeoguiseon/` 접속 가능

## 모바일에서 PWA로 설치

### Android (Chrome)
1. 모바일 Chrome에서 URL 접속
2. 메뉴(⋮) → "홈 화면에 추가"

### iOS (Safari)
1. Safari에서 URL 접속
2. 공유 → "홈 화면에 추가"

## 도메인 연결 (선택)

Vercel/Netlify에서 사용자 도메인 연결 가능:
- 도메인 구매 (가비아, 카페24 등에서 .com 약 15,000원/년)
- DNS 설정 (Vercel/Netlify 안내 따라)

## 비용

- **무료**: Vercel, Netlify, GitHub Pages 모두 개인 사용 무료
- **도메인**: 연 15,000원~30,000원 (선택)
- **AI API**: 사용자가 직접 발급 (BYO 키)

## 보안 주의사항

- API 키는 코드에 직접 넣지 마세요 (사용자 입력 방식 유지)
- 깃에 .env 등 비밀 파일 푸시 금지
- HTTPS 자동 적용되므로 추가 설정 불필요
