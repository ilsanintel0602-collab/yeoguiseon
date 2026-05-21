@echo off
REM yeoguiseon v4 - GitHub auto push wrapper (ASCII-only for CMD compat)
chcp 65001 > nul
cd /d "%~dp0\.."
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0auto_push.ps1"
echo.
echo Press any key to close...
pause > nul
