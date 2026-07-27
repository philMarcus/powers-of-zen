#!/usr/bin/env bash
# Launch the Powers of Zen dashboard (Streamlit) in tmux session 'zendash'.
SESSION=zendash
cd "$(dirname "$0")/.."
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -c "$(pwd)"
  tmux send-keys -t "$SESSION" "streamlit run dashboard/app.py --server.headless true" Enter
fi
echo "dashboard: http://localhost:8501  (tmux attach -t $SESSION)"
