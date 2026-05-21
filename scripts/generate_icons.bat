@echo off
cd /d "%~dp0"
cd ..
echo.
echo === icon generation ===
echo.

python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Installing Pillow...
    python -m pip install --user Pillow
    echo.
)

echo Generating icons...
python "scripts\generate_icons.py"
echo.

echo === done ===
pause
