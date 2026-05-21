@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === boost v3 (8 missing + sourceUrl 90%% target) ===
echo.
python scripts\boost_aliases_v3.py
echo.
echo --- audit after boost v3 ---
python scripts\audit_data.py
echo.
echo === done ===
echo Press any key to close...
pause >nul
