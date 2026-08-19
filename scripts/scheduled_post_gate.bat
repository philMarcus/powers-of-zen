@echo off
REM Powers of Zen - posting gate entry point. One silent line: post_gate.py decides
REM whether a post fires (cadence clock in journeys.json); poster.py self-heals Chrome
REM itself, so nothing else belongs here. Launched HIDDEN via hidden_post_gate.vbs
REM (2026-08-19: a console .bat fired hourly by Task Scheduler stole focus every hour).
REM NOTE Task Scheduler cwd = System32 -> the WSL call must cd first.
wsl.exe bash -lc "cd /mnt/c/Users/Phil/zoomer && python3 scripts/post_gate.py >> outbox/post_gate.log 2>&1"
