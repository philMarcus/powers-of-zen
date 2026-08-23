@echo off
REM Powers of Zen - scheduled IG stats snapshot (12:00 + 00:00 tasks; Phil 2026-08-22:
REM count likes/views more often than the 19h post cadence, not only after posts).
REM Runs BOTH scrapers: ig_stats (reels grid: views/likes/comments/followers) then
REM ig_insights (Business Suite: reach/shares/saves/follows/watch time). Each
REM self-heals Chrome, skips if a poster is in flight, and locks against overlap.
REM Launched HIDDEN via hidden_task.vbs (focus rules in SCHEDULER.md).
REM NOTE Task Scheduler cwd = System32 -> the WSL call must cd first.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/ig_stats.py >> outbox/ig_stats_task.log 2>&1"
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/ig_insights.py >> outbox/ig_stats_task.log 2>&1"
