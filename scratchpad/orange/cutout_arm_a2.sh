#!/bin/bash
# re-run of arm A (cut-out HERO ONLY) on the corrected mask code, after the main chain (tmux cutout) ends.
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/cutout_arms.log
while tmux has-session -t =cutout 2>/dev/null; do sleep 20; done   # exact-name match (10-13 lesson)
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
T=cutout_a2; DL=scratchpad/orange/cutout_arm_$T.log
echo "[cutout] $(date +%H:%M:%S) start arm $T: valdes_blow hero-only re-run" | tee -a $L
python3 engine/dive.py journeys/valdes_blow.json --seed 1234 $NIGHTLY --tag $T --from-card 6 --src-version v1 --frames 288 --no-loop --stage-echo-cutout 0 > $DL 2>&1
echo "[cutout] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
grep -E "stage-echo|nest:|-> output|Traceback|Error" $DL | tail -n 10 | cut -c1-220 | tee -a $L
echo "[cutout] $(date +%H:%M:%S) a2 done" | tee -a $L
