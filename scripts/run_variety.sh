#!/usr/bin/env bash
# Render the 10-journey diversity batch (build-out per journey format)
set -e
cd "$(dirname "$0")/.."
for j in tide_of_life mineral_heart night_bloom cartographer dollhouse food_chain iris_observatory black_hole antenna_ball snowfall; do
  echo "=== $j ==="
  python3 engine/dive.py "journeys/$j.json"
done
echo "=== variety batch complete ==="
