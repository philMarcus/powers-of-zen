#!/bin/bash
# PLATE-STYLE MICRO STAGE A/B (2026-10-14, Phil: "let's try that one... Try the AB you mentioned"): a lattice card
# (valdes_blow k7 sulfur_atom) and a nucleus card (lepidolite_halo_var k8 halo_nucleus), same seed, today's stage
# (the nightly's flags) vs --stage-paint (the AI draws the element from an authored line, every sphere wears it,
# the far field is painted behind, the repaint capped at the plate's trust).
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
EL7="sulfur atom, a tight tangerine glowing core wrapped in a broader amber haze and a thin ultramarine outer veil"
FL7="dim knots of neighbouring electron fog at the margins of an ink-black void, tangerine and ultramarine"
EL8="nucleon, a glowing amber-gold glass sphere packed tight against its neighbours"
FL8="an enormous faint lilac fog in pine-black deep space, two loose quartz-silver spheres adrift far out"
run() {
  local T=$1 J=$2; shift 2
  local DL=scratchpad/orange/paint_arm_$T.log
  echo "[paint] $(date +%H:%M:%S) start arm $T: $J $*" | tee -a $L
  python3 engine/dive.py $J --seed 1234 $NIGHTLY --tag $T "$@" > $DL 2>&1
  echo "[paint] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
  grep -E "stage-paint|stage-echo|STAGE |-> output|Traceback|Error" $DL | tail -n 8 | cut -c1-220 | tee -a $L
}
run paint_l0 journeys/valdes_blow.json --from-card 7 --src-version v2 --frames 256 --no-loop
run paint_l1 journeys/valdes_blow.json --from-card 7 --src-version v2 --frames 256 --no-loop --stage-paint --stage-element "7=$EL7" --stage-field "7=$FL7"
run paint_n0 journeys/lab/lepidolite_halo_var.json --from-card 8 --src-version v3 --frames 288 --no-loop
run paint_n1 journeys/lab/lepidolite_halo_var.json --from-card 8 --src-version v3 --frames 288 --no-loop --stage-paint --stage-element "8=$EL8" --stage-field "8=$FL8"
echo "[paint] $(date +%H:%M:%S) all arms done" | tee -a $L
python3 scratchpad/orange/paint_strip.py 2>&1 | tail -n 8 | tee -a $L
