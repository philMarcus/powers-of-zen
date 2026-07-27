#!/usr/bin/env bash
# Regenerate ONLY the fix batch (mineral_heart, cartographer, skyfog, antenna_ball) —
# all with visible cameos. Release-approved videos are NOT touched. No set -e.
cd "$(dirname "$0")/.."
render() {
  local j=$1 model=$2 suffix="" margs=""
  if [ "$model" = "ds" ]; then suffix="_ds"; margs="--model ds"; fi
  echo "=== render $j$suffix ==="
  python3 engine/dive.py "journeys/$j.json" $margs || { echo "!!! FAILED $j$suffix"; return; }
  local v=$(ls -d "output/$j$suffix"/v* 2>/dev/null | sort -V | tail -1)
  cp "$v/$j$suffix.mp4" "review/$j$suffix.mp4" 2>/dev/null
  cp "$v/$j${suffix}_divein.mp4" "review_divein/$j${suffix}_divein.mp4" 2>/dev/null
  echo ">>> $j$suffix deposited to review"
}
render skyfog turbo
render antenna_ball turbo
render mineral_heart ds
render cartographer ds
render mineral_heart turbo
render cartographer turbo
echo "=== phase-shifting ==="
python3 scripts/phase_shift.py skyfog antenna_ball mineral_heart cartographer
echo "=== FIX BATCH COMPLETE ==="
