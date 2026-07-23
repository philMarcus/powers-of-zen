#!/usr/bin/env bash
# Render the diversity batch through one model preset: run_batch.sh turbo|ds
set -e
cd "$(dirname "$0")/.."
for j in molten_clockwork stained_glass_ocean origami_bloom neon_mycelium ice_and_ember; do
  echo "=== $j ($1) ==="
  python3 engine/dive.py "journeys/$j.json" --model "$1"
done
echo "=== batch $1 complete ==="
