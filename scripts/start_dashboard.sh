#!/usr/bin/env bash
# Launch (or RESTART) the Powers of Zen dashboard via WINDOWS streamlit (reads the same C: files
# as the WSL poster/scheduler). tmux session 'zendash'. Running this always gives a FRESH process
# so code changes are picked up — Streamlit re-runs app.py on its own, but it does NOT re-import
# modules like scripts/pipeline.py, so a full restart is required after editing them.
SESSION=zendash
STREAMLIT="/mnt/c/Users/Phil/AppData/Local/Python/pythoncore-3.14-64/Scripts/streamlit.exe"
TASKKILL="/mnt/c/Windows/System32/taskkill.exe"

tmux kill-session -t "$SESSION" 2>/dev/null      # drop the old tmux pane (legacy host)
"$TASKKILL" /F /IM streamlit.exe /T >/dev/null 2>&1 || true   # kill the Windows streamlit tree
sleep 1
# 2026-09-18: launch as its OWN hidden Windows process, not inside a tmux pane. A Windows
# process started from a WSL terminal shares that terminal's console: when the terminal
# window was closed (06:45 that morning) the console CLOSE event killed the dashboard AND
# ComfyUI ("forrtl: error (200): program aborting due to window-CLOSE event"). Start-Process
# gives it a console of its own; output goes to outbox/dashboard.log / dashboard.err.log.
PS="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
"$PS" -NoProfile -Command "Start-Process -FilePath 'C:\Users\Phil\AppData\Local\Python\pythoncore-3.14-64\Scripts\streamlit.exe' -ArgumentList 'run','C:\Users\Phil\zoomer\dashboard\app.py','--server.headless','true' -WorkingDirectory 'C:\Users\Phil\zoomer' -WindowStyle Hidden -RedirectStandardOutput 'C:\Users\Phil\zoomer\outbox\dashboard.log' -RedirectStandardError 'C:\Users\Phil\zoomer\outbox\dashboard.err.log'" >/dev/null 2>&1 &
echo "dashboard (fresh restart): http://localhost:8501  (log: outbox/dashboard.log)"
