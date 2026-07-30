#!/usr/bin/env bash
# Launch (or RESTART) the Powers of Zen dashboard via WINDOWS streamlit (reads the same C: files
# as the WSL poster/scheduler). tmux session 'zendash'. Running this always gives a FRESH process
# so code changes are picked up — Streamlit re-runs app.py on its own, but it does NOT re-import
# modules like scripts/pipeline.py, so a full restart is required after editing them.
SESSION=zendash
STREAMLIT="/mnt/c/Users/Phil/AppData/Local/Python/pythoncore-3.14-64/Scripts/streamlit.exe"
TASKKILL="/mnt/c/Windows/System32/taskkill.exe"

tmux kill-session -t "$SESSION" 2>/dev/null      # drop the old tmux pane
"$TASKKILL" /F /IM streamlit.exe /T >/dev/null 2>&1 || true   # kill the Windows streamlit tree
sleep 1
tmux new-session -d -s "$SESSION"
tmux send-keys -t "$SESSION" "'$STREAMLIT' run 'C:\\Users\\Phil\\zoomer\\dashboard\\app.py' --server.headless true" Enter
echo "dashboard (fresh restart): http://localhost:8501  (tmux attach -t $SESSION)"
