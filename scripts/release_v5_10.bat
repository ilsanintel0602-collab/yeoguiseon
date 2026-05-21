@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo ===============================================
echo   v5.10 release: refine + audit + push
echo ===============================================
echo.

echo --- Step 1: refine_v5_10.py ---
python scripts\refine_v5_10.py
if errorlevel 1 (
    echo [ERROR] refine failed. Stop.
    pause
    exit /b 1
)
echo.

echo --- Step 2: data_audit_full.py ---
python scripts\data_audit_full.py
echo.

echo --- Step 3: push (auto_push.bat) ---
call scripts\auto_push.bat
echo.

echo ===============================================
echo   v5.10 release done
echo ===============================================
pause
