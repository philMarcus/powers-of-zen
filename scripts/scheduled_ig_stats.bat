@echo off
REM Powers of Zen - scheduled IG stats snapshot (12:00 + 00:00 tasks; Phil 2026-08-22:
REM count likes/views more often than the 19h post cadence, not only after posts).
REM ig_stats.py self-heals Chrome, skips if a poster run is in flight, and locks
REM against overlapping scrapes. Launched HIDDEN via hidden_task.vbs (focus rules in
REM SCHEDULER.md). NOTE Task Scheduler cwd = System32 -> the WSL call must cd first.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/ig_stats.py >> outbox/ig_stats_task.log 2>&1"
