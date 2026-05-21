@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo ===============================================
echo   data-steward Full Audit (10 stages)
echo ===============================================
echo.
python scripts\data_audit_full.py
echo.
echo ===============================================
echo   done. report shown above.
echo ===============================================
echo Press any key to close...
pause >nul
