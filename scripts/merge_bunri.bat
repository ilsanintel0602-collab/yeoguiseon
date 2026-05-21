@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === merge bunribaechul 730 ===
echo.
echo Step 1: dry-run (preview, no save)
echo ---------------------------------
python scripts\merge_bunribaechul.py --dry
echo.
echo.
choice /M "Above looks correct. Run real merge with save?"
if errorlevel 2 (
    echo Skipped real merge. Backup not created.
    goto done
)
echo.
echo Step 2: real merge (save + backup)
echo ---------------------------------
python scripts\merge_bunribaechul.py
echo.
echo Step 3: audit after merge
echo ---------------------------------
python scripts\audit_data.py
:done
echo.
echo === all done ===
echo Press any key to close...
pause >nul
