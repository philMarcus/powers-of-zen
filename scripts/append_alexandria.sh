#!/usr/bin/env bash
# Waits for the main overnight queue to drain, then renders alexandria
# in turbo and DreamShaper (added mid-night at Phil's request).
cd "$(dirname "$0")/.."
while true; do
  if ! pgrep -f "engine/dive.py" > /dev/null; then
    sleep 90
    pgrep -f "engine/dive.py" > /dev/null || break
  fi
  sleep 120
done
echo "=== queue drained, rendering alexandria ==="
python3 engine/dive.py journeys/alexandria.json || echo "!!! FAILED turbo alexandria"
python3 engine/dive.py journeys/alexandria.json --model ds || echo "!!! FAILED ds alexandria"
echo "=== alexandria complete ==="
