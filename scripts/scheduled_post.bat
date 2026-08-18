@echo off
REM Powers of Zen - posting entry point. DELEGATES to the cadence gate (post_gate.py):
REM the dashboard's post_every_hours/post_next clock decides whether a post fires.
REM All posting tasks run this; the gate makes double-posting impossible.
REM NOTE Task Scheduler runs with cwd=System32 -> every WSL call must cd first
REM (2026-08-18: relative paths silently broke every hourly run; Last Result 1, empty log).
REM NOTE 'timeout' needs console stdin and dies under Task Scheduler -> ping-sleep.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && bash scripts/start_chrome_zen.sh >> outbox/post_gate.log 2>&1"
ping -n 21 127.0.0.1 >nul
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/post_gate.py >> outbox/post_gate.log 2>&1"
