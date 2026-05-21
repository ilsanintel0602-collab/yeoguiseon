@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === audit_v2 (8 stage, 99 pass line) ===
echo.
python scripts\audit_v2.py
echo.
echo === audit_v2 done ===
echo Press any key to close...
pause >nul
