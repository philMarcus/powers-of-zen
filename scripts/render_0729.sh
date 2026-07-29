#!/usr/bin/env bash
# Render batch 2026-07-29 — the self-similar journeys through the NEW engine (grammar self-
# similar loop + dive.py seam mechanism). Sequential (one GPU job at a time). DS FIRST so Phil
# can stop after the DS pass if needed; turbo for the new ones after. Each finished render is
# ingested into the REVIEW queue (no music). No set -e: one failure must not kill the batch.
cd "$(dirname "$0")/.."
LOG=outbox/render_0729.log
: > "$LOG"
step(){ echo "=== $(date +%H:%M:%S) $* ===" | tee -a "$LOG"; "$@" >> "$LOG" 2>&1 || echo "!!! FAILED: $*" | tee -a "$LOG"; }

# ComfyUI must be up
bash /mnt/c/Users/Phil/start_comfyui.sh >> "$LOG" 2>&1
for i in $(seq 1 30); do curl -s --max-time 3 http://localhost:8188/system_stats >/dev/null 2>&1 && break; sleep 5; done

# 1) circuit_city: seam-repair the EXISTING turbo render (don't re-render it), then queue
step python3 scripts/repair_seam.py circuit_city --model turbo
step python3 scripts/queue_review.py circuit_city turbo

# 2) DS renders (all six) through the new engine, queue each as it lands
for j in cosmic_scales_remix circuit_city stormglass antenna_ball skyfog mineral_heart; do
  step python3 engine/dive.py "journeys/$j.json" --model ds
  step python3 scripts/queue_review.py "$j" ds
done

# 3) turbo renders for the four NEW journeys (cosmic + circuit already have turbo)
for j in stormglass antenna_ball skyfog mineral_heart; do
  step python3 engine/dive.py "journeys/$j.json" --model turbo
  step python3 scripts/queue_review.py "$j" turbo
done

echo "=== render batch COMPLETE $(date) ===" | tee -a "$LOG"
