#!/bin/bash
# MIDDLE-GROUND arms (2026-10-15, Phil: "go ahead, run that test"): stage-style STRUCTURE (today's depth leash kept),
# plate-style SURFACES (the gem-orb element pictures on the kit's elements), on the sulfur lattice (valdes_blow k7),
# same seed, bold element scale. Baseline rows: paint_l0 (today, drawn scale) + M0 (today's stage at bold scale).
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
EL7="sulfur atom, a tight tangerine glowing core wrapped in a broader amber haze and a thin ultramarine outer veil"
FL7="dim knots of neighbouring electron fog at the margins of an ink-black void, tangerine and ultramarine"
BASE="journeys/valdes_blow.json --from-card 7 --src-version v2 --frames 256 --no-loop"
PAINT="--stage-paint --stage-paint-scale bold"
run() {
  local T=$1; shift
  local DL=scratchpad/orange/paint_arm_$T.log
  echo "[paint] $(date +%H:%M:%S) start arm $T: $*" | tee -a $L
  python3 engine/dive.py --seed 1234 $NIGHTLY --tag $T "$@" > $DL 2>&1
  echo "[paint] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
  grep -E "stage-paint|STAGE lattice|Traceback|Error" $DL | tail -n 3 | cut -c1-240 | tee -a $L
}
run paint_l0b $BASE
run paint_m0 $BASE $PAINT --stage-element "7=$EL7" --stage-paint-tex 0.0
run paint_m1 $BASE $PAINT --stage-element "7=$EL7" --stage-paint-tex 0.9 --stage-paint-id 0.5
run paint_m2 $BASE $PAINT --stage-element "7=$EL7" --stage-paint-tex 0.9 --stage-paint-id 0.5 --stage-field "7=$FL7" --stage-paint-field-blur 14 --stage-paint-field-dim 0.45
run paint_m3 $BASE $PAINT --stage-element "7=$EL7" --stage-paint-tex 0.5 --stage-paint-id 0.40 --stage-paint-den 0.40 --stage-paint-den-arrival 0.45
run paint_m4 $BASE $PAINT --stage-element "7=$EL7" --stage-paint-tex 0.9 --stage-paint-id 0.5 --stage-paint-den 0.30 --stage-paint-den-arrival 0.32
echo "[paint] $(date +%H:%M:%S) middle arms done" | tee -a $L
python3 scratchpad/orange/paint_mid_strip.py 2>&1 | tail -n 10 | tee -a $L
echo "[paint] $(date +%H:%M:%S) middle strip done" | tee -a $L
