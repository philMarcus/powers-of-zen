#!/usr/bin/env bash
# Overnight render queue (~6h): all journeys in turbo with counter v2, then
# DreamShaper for everything lacking a current DS version, flagship first.
# No set -e: one failed render must not kill the night.
cd "$(dirname "$0")/.."

TURBO="cosmic_scales tide_of_life mineral_heart night_bloom cartographer dollhouse food_chain iris_observatory black_hole antenna_ball snowfall skyfog midnight_kitchen"
DS="cosmic_scales skyfog midnight_kitchen black_hole iris_observatory food_chain antenna_ball dollhouse tide_of_life"

for j in $TURBO; do
  echo "=== turbo $j ==="
  python3 engine/dive.py "journeys/$j.json" || echo "!!! FAILED turbo $j"
done
for j in $DS; do
  echo "=== ds $j ==="
  python3 engine/dive.py "journeys/$j.json" --model ds || echo "!!! FAILED ds $j"
done
echo "=== overnight complete ==="
