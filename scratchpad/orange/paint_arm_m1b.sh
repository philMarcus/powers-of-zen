#!/bin/bash
# M1 re-run with the fog fix (a palette "on ink-black" now gives a near-black fog; M1's wash was the tangerine fog)
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
while tmux has-session -t =beatq 2>/dev/null || tmux has-session -t =paintm2 2>/dev/null; do sleep 20; done
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
EL7="sulfur atom, a tight tangerine glowing core wrapped in a broader amber haze and a thin ultramarine outer veil"
run() {
  local T=$1; shift; local DL=scratchpad/orange/paint_arm_$T.log
  echo "[paint] $(date +%H:%M:%S) start arm $T: $*" | tee -a $L
  python3 engine/dive.py --seed 1234 $NIGHTLY --tag $T "$@" > $DL 2>&1
  echo "[paint] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
  grep -E "stage-paint|Traceback|error:" $DL | tail -n 2 | cut -c1-200 | tee -a $L
}
run paint_l0c journeys/valdes_blow.json --from-card 7 --src-version v2 --frames 256 --no-loop
run paint_m1b journeys/valdes_blow.json --from-card 7 --src-version v2 --frames 256 --no-loop --stage-paint --stage-paint-scale bold --stage-element "7=$EL7" --stage-paint-tex 0.9 --stage-paint-id 0.5
echo "[paint] $(date +%H:%M:%S) m1b done" | tee -a $L
