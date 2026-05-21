@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === audit start ===
python scripts\audit_data.py
echo === audit done ===
echo.
echo Press any key to close...
pause >nul
