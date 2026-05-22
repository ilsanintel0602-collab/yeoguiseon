@echo off
chcp 65001 > nul
cd /d "%~dp0\.."
echo.
echo === Phase B4: 사용자 피드백 자동 학습 사이클 ===
echo.

if not exist .feedback_key.txt (
    echo [!] .feedback_key.txt 없음. 첫 사용 셋업:
    echo     1. Cloudflare Workers > yeoguiseon-proxy > Settings
    echo     2. Variables and Secrets > Add > Type: Secret
    echo     3. Name: FEEDBACK_DUMP_KEY, Value: 임의 긴 문자열
    echo     4. 같은 키를 프로젝트 루트 .feedback_key.txt에 저장
    echo.
    echo Skipping. 베타 사용자 생기면 다시 실행.
    pause
    exit /b 0
)

set /p DUMP_KEY=<.feedback_key.txt

echo [1/4] Worker dump...
python scripts\analyze_feedback.py --worker --key "%DUMP_KEY%" --dry

echo [2/4] 약점 분석...
python scripts\analyze_feedback.py --worker --key "%DUMP_KEY%"

echo [3/4] augment...
python scripts\augment_aliases_v2.py --feedback

echo [4/4] quick_check...
python scripts\quick_check.py
if errorlevel 1 (
    echo [!] 검증 실패
    pause
    exit /b 1
)

echo.
set /p PUSH=push (Y/N):
if /i "%PUSH%"=="Y" call scripts\auto_push.bat

pause
