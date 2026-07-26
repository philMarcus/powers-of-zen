#!/usr/bin/env bash
# Launch the dedicated PowersOfZen Chrome profile (Windows Chrome) with the CDP
# debug port open on 9222 so agents can drive it from WSL. Separate
# user-data-dir = fully isolated from Phil's personal browsing.
CHROME="/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
nohup "$CHROME" \
  --user-data-dir="C:\\Users\\Phil\\zoomer\\chrome_zen" \
  --remote-debugging-port=9222 \
  --remote-allow-origins='*' \
  --no-first-run \
  --window-size=1200,900 \
  "$@" > /dev/null 2>&1 &
echo "PowersOfZen Chrome launching (CDP on :9222)"
