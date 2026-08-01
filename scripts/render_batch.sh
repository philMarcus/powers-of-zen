#!/usr/bin/env bash
# ENGINE-2 RENDER BATCH — one LONG, one MEDIUM, one SHORT, newest engine settings.
#
#   bash scripts/render_batch.sh
#
# Per journey: render -> caption (local VLM) -> ingest to the REVIEW queue.
# Sequential: ONE GPU job at a time (ComfyUI interleaves concurrent jobs and both crawl).
# No `set -e` — one failure must not kill the rest of the batch.
#
# Everything engine-side is already the default (uniform bars, engine-1 zoom curve, on-beat
# morphs with the anacrusis, seam = more FRAMES not more force, rule-of-thirds composition,
# depth-CN 0.45, DreamShaper, honest 10^n counter, style brand tail). No flags needed.
# `render_start` is set per journey in its JSON so frame 0 lands in an abstract realm.
#
# SAFE TO RUN AFTER A REBOOT: waits for ComfyUI, and waits for the GPU to be free first, so it
# won't fight a game. Resumable: a journey whose render already completed is skipped.
cd "$(dirname "$0")/.."
LOG="outbox/render_batch_$(date +%m%d_%H%M).log"
: > "$LOG"
say(){ echo "=== $(date +%H:%M:%S) $* ===" | tee -a "$LOG"; }
step(){ say "$*"; "$@" >> "$LOG" 2>&1 || echo "!!! FAILED: $*" | tee -a "$LOG"; }

# journey : tier (frames)  — render_start lives in each journey JSON
JOURNEYS=(butterfly_meridian quantum_orrery lather_atlas)

say "batch start — long butterfly_meridian (280f/23.3s), medium quantum_orrery (196f/16.3s), short lather_atlas (140f/11.7s)"

# --- ComfyUI up (it does NOT survive a reboot) --------------------------------
if ! curl -s --max-time 3 http://localhost:8188/system_stats >/dev/null 2>&1; then
  say "starting ComfyUI"
  bash /mnt/c/Users/Phil/start_comfyui.sh >> "$LOG" 2>&1
fi
for i in $(seq 1 60); do
  curl -s --max-time 3 http://localhost:8188/system_stats >/dev/null 2>&1 && break
  sleep 5
done
if ! curl -s --max-time 3 http://localhost:8188/system_stats >/dev/null 2>&1; then
  say "ABORT: ComfyUI never came up (start it by hand: bash /mnt/c/Users/Phil/start_comfyui.sh)"; exit 1
fi
say "ComfyUI ready"

# --- don't fight a game: wait for the GPU to go quiet -------------------------
for i in $(seq 1 240); do            # up to ~2h of waiting, checked every 30s
  python3 -c "import sys;sys.path.insert(0,'scripts');import pipeline as pl;sys.exit(0 if pl.gpu_busy() else 1)" || break
  [ "$i" = 1 ] && say "GPU busy (game or another render?) — waiting for it to free up"
  sleep 30
done
say "GPU free — rendering"

for j in "${JOURNEYS[@]}"; do
  say "--- $j ---"
  # skip if a complete render already exists (resumable batch)
  if python3 - "$j" <<'PY' >/dev/null 2>&1
import json, sys
sys.path.insert(0, "engine"); sys.path.insert(0, "scripts")
import grammar, style as _style
from pathlib import Path
j = sys.argv[1]
spec = json.loads(Path(f"journeys/{j}.json").read_text())
sfx, _m, _n = _style.resolve(spec, None); spec["style_suffix"] = sfx
total = len(grammar.compile_journey(spec, 12, "in")[1])
base = Path("output") / j
ok = any(len(list((d / "build" / "frames").glob("*.png"))) >= total
         for d in base.glob("v[0-9]*")) if base.exists() else False
sys.exit(0 if ok else 1)
PY
  then
    say "$j: complete render already exists — skipping render"
  else
    step python3 engine/dive.py "journeys/$j.json"
  fi
  # QUEUE FIRST, then caption. queue_review.py is what CREATES the pipeline.json entry, and
  # caption.py silently discards its work when there's no entry to write into — captioning
  # first left butterfly_meridian and lather_atlas in Review with no caption at all, while
  # both logs showed "5 caption+title pairs" as if it had worked.
  step python3 scripts/queue_review.py "$j" ds
  step python3 scripts/caption.py "$j"
  say "$j done -> REVIEW"
done

say "BATCH COMPLETE — 3 videos in Video Review (captioned). Next: mark a start frame, Approve -> Music."
echo "log: $LOG"
