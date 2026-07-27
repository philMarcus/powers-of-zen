#!/usr/bin/env bash
# Launch the Powers of Zen dashboard via WINDOWS streamlit (reads the same C: files
# as the WSL poster/scheduler). tmux session 'zendash'.
SESSION=zendash
STREAMLIT="/mnt/c/Users/Phil/AppData/Local/Python/pythoncore-3.14-64/Scripts/streamlit.exe"
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION"
  tmux send-keys -t "$SESSION" "'$STREAMLIT' run 'C:\\Users\\Phil\\zoomer\\dashboard\\app.py' --server.headless true" Enter
fi
echo "dashboard: http://localhost:8501  (tmux attach -t $SESSION)"
