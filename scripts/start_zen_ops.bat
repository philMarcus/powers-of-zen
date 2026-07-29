@echo off
REM Powers of Zen — one-click ops launcher (desktop shortcut points here).
REM Ensures the PowersOfZen Chrome (CDP :9222) is up AND the Streamlit dashboard is up,
REM then opens the dashboard in the browser. Idempotent — safe to run when already running.
title Powers of Zen - ops launcher
echo Starting Chrome (CDP :9222) and the dashboard...
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && bash scripts/start_chrome_zen.sh && bash scripts/start_dashboard.sh"
echo Waiting for the dashboard to come up...
timeout /t 8 /nobreak >nul
start "" http://localhost:8501
echo Done. Dashboard: http://localhost:8501   (this window can be closed)
timeout /t 4 /nobreak >nul
