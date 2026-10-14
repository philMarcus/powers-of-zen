#!/bin/bash
# NUCLEUS A/B re-run: lepidolite_halo_var's cards are 36 frames (card 8 = 288..323); the first run's --frames 288
# ended at the card's first frame and rendered nothing.
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
EL8="nucleon, a glowing amber-gold glass sphere packed tight against its neighbours"
FL8="an enormous faint lilac fog in pine-black deep space, two loose quartz-silver spheres adrift far out"
run() {
  local T=$1 J=$2; shift 2
  local DL=scratchpad/orange/paint_arm_$T.log
  echo "[paint] $(date +%H:%M:%S) start arm $T: $J $*" | tee -a $L
  python3 engine/dive.py $J --seed 1234 $NIGHTLY --tag $T "$@" > $DL 2>&1
  echo "[paint] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
  grep -E "stage-paint|STAGE nucleus|Traceback|Error" $DL | tail -n 4 | cut -c1-220 | tee -a $L
}
run paint_n0 journeys/lab/lepidolite_halo_var.json --from-card 8 --src-version v3 --frames 324 --no-loop
run paint_n1 journeys/lab/lepidolite_halo_var.json --from-card 8 --src-version v3 --frames 324 --no-loop --stage-paint --stage-element "8=$EL8" --stage-field "8=$FL8"
echo "[paint] $(date +%H:%M:%S) nucleus arms done" | tee -a $L
python3 scratchpad/orange/paint_strip.py 2>&1 | tail -n 8 | tee -a $L
echo "[paint] $(date +%H:%M:%S) nucleus strip done" | tee -a $L
