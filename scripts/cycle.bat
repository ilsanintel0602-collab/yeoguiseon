@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo ===============================================
echo   audit + boost cycle (target 99/100)
echo ===============================================
echo.

echo --- Round 1: initial audit_v2 ---
python scripts\audit_v2.py
echo.

echo --- Boost v4 (Stage 5 + Stage 7 auto-fix) ---
python scripts\boost_v4.py
echo.

echo --- Round 2: audit_v2 after boost ---
python scripts\audit_v2.py
echo.

echo ===============================================
echo   cycle done. See score above.
echo ===============================================
echo Press any key to close...
pause >nul
