@echo off
REM Powers of Zen — scheduled post. Run by Windows Task Scheduler at 08:00 and 18:00.
REM Ensures the PowersOfZen Chrome (CDP) is up, then posts the next QUEUED video.
REM No Claude involved — poster.py is standalone (reads pipeline.json, writes telemetry).
wsl.exe bash -lc "bash scripts/start_chrome_zen.sh"
timeout /t 20 /nobreak >nul
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/poster.py >> outbox/scheduler.log 2>&1"
