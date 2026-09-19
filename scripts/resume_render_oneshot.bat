@echo off
wsl.exe bash -lc "python3 scripts/resume_render_oneshot.py >> outbox/render_resume.log 2>&1"
