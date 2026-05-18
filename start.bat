@echo off
setlocal

set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

where python >nul 2>nul
if not errorlevel 1 ( set "PY=python" & goto run )
where py >nul 2>nul
if not errorlevel 1 ( set "PY=py" & goto run )

echo [ERROR] Python not installed.
echo Install: https://www.python.org/
pause
exit /b 1

:run
echo.
echo ======================================
echo   Yeoguiseon v4.0 Server (Port 8004)
echo ======================================
echo.
echo Folder: %DIR%
echo.
echo OPEN IN BROWSER:
echo.
echo    http://localhost:8004/
echo.
echo (v4 uses port 8004 to avoid v1/v2/v3 conflict)
echo Stop: Ctrl+C
echo ======================================
echo.

%PY% -m http.server 8004 --directory "%DIR%"
endlocal
