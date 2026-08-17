@echo off
REM Powers of Zen — posting entry point. Since 2026-08-17 this DELEGATES to the cadence
REM GATE (post_gate.py): the dashboard's post_every_hours/post_next clock decides whether
REM a post actually fires. The legacy 08:00/18:00 tasks and the hourly PowersOfZen-postgate
REM task all run this safely — the gate makes double-posting impossible.
wsl.exe bash -lc "bash scripts/start_chrome_zen.sh"
timeout /t 20 /nobreak >nul
wsl.exe bash -lc "python3 scripts/post_gate.py >> outbox/post_gate.log 2>&1"
