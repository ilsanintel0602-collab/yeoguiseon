@echo off
title yeoguiseon v4 Worker deploy
cd /d "%~dp0"
echo.
echo === Cloudflare Worker v1.9.14 deploy ===
echo Target: yeoguiseon-proxy.ilsanintel0602.workers.dev
echo Folder: %CD%
echo.
echo Running: npx wrangler deploy
echo (Login may open in browser on first run -- use ilsanintel0602@gmail.com)
echo.
call npx wrangler deploy
echo.
echo === Done. Press any key to close. ===
pause
