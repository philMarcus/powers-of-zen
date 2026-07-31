#!/usr/bin/env bash
# Launch the PowersOfZen Chrome profile with CDP on :9222 — idempotent, and opens the
# 3 platform tabs so the poster always has them (self-heals too, but this avoids churn).
if curl -s --max-time 3 http://localhost:9222/json/version >/dev/null 2>&1; then
  echo "PowersOfZen Chrome already up (CDP :9222)"; exit 0
fi
CHROME="/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
# Anti-throttle flags: keep the automated tabs LIVE when the display sleeps overnight (off after
# 45min on AC). Without these, Chrome throttles background timers and backgrounds the renderer when
# its window is occluded, so at the 08:00 run the page looks ready but clicks/JS don't register —
# the recurring morning failure. Standard fix for "works with the display on, fails with it off".
nohup "$CHROME" \
  --user-data-dir="C:\\Users\\Phil\\zoomer\\chrome_zen" \
  --remote-debugging-port=9222 --remote-allow-origins='*' \
  --no-first-run --window-size=1200,900 \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --disable-background-timer-throttling \
  "https://www.tiktok.com/tiktokstudio/upload" \
  "https://studio.youtube.com" \
  "https://www.instagram.com/" "$@" > /dev/null 2>&1 &
echo "PowersOfZen Chrome launching (CDP :9222, 3 platform tabs)"
