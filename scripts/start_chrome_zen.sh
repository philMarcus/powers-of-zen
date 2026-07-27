#!/usr/bin/env bash
# Launch the dedicated PowersOfZen Chrome profile with CDP on :9222 — idempotent
# (skips if already running, so the scheduler can call it safely).
if curl -s --max-time 3 http://localhost:9222/json/version >/dev/null 2>&1; then
  echo "PowersOfZen Chrome already up (CDP :9222)"; exit 0
fi
CHROME="/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
nohup "$CHROME" \
  --user-data-dir="C:\\Users\\Phil\\zoomer\\chrome_zen" \
  --remote-debugging-port=9222 --remote-allow-origins='*' \
  --no-first-run --window-size=1200,900 "$@" > /dev/null 2>&1 &
echo "PowersOfZen Chrome launching (CDP on :9222)"
