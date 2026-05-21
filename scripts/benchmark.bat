@echo off
cd /d "%~dp0"
cd ..
echo.
echo === benchmark run ===
echo.
python "scripts\benchmark.py"
echo.
echo === done ===
pause
