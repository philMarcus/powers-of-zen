#!/usr/bin/env bash
# Waits for the running fix_batch to fully finish, then renders skyfog + antenna_ball
# in DS, deposits to review/, and phase-shifts ONLY the ds files (turbo already shifted).
cd "$(dirname "$0")/.."
absent=0
while [ $absent -lt 2 ]; do
  if pgrep -f "engine/dive.py" >/dev/null || pgrep -f "scripts/phase_shift.py" >/dev/null; then
    absent=0
  else
    absent=$((absent+1))
  fi
  sleep 30
done
echo "=== fix_batch done; rendering skyfog + antenna_ball DS ==="
render() {
  local j=$1
  echo "=== render ${j}_ds ==="
  python3 engine/dive.py "journeys/$j.json" --model ds || { echo "!!! FAILED ${j}_ds"; return; }
  local v=$(ls -d "output/${j}_ds"/v* 2>/dev/null | sort -V | tail -1)
  cp "$v/${j}_ds.mp4" "review/${j}_ds.mp4" 2>/dev/null
  cp "$v/${j}_ds_divein.mp4" "review_divein/${j}_ds_divein.mp4" 2>/dev/null
}
render skyfog
render antenna_ball
python3 - << 'PY'
import sys; sys.path.insert(0,'scripts'); import phase_shift as ps
from pathlib import Path
for j in ['skyfog','antenna_ball']:
    for f, cut in ((f'review/{j}_ds.mp4','zoomout'), (f'review_divein/{j}_ds_divein.mp4','divein')):
        p = Path(f)
        if p.exists(): ps.shift(p, ps.cut_time(j, cut)); print(f"shifted {f}")
PY
echo "=== skyfog + antenna_ball DS COMPLETE ==="
