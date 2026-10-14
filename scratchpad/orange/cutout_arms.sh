#!/bin/bash
# ECHO CUT-OUT arms (2026-10-14; Phil: "let's try the other two, cut-out shapes first"): the plunge-target
# element becomes a cut-out of the donor swatch (silhouette + DepthAnything depth), on top of the nightly's
# echo texture (relief + half-lit) and fog fix.
#   A  valdes_blow cards 6-8 (whale on tubes, callosity on lattice, coiled protein chain on tracks): hero only
#   B  same, hero + half the other spheres
#   C  lepidolite_halo_var card 6 (lilac mica crystal on lattice; 7-8 are round donors = unchanged): hero + 0.5
#   D  valdes_blow cards 6-8 with the nightly's flags only (relief + half-lit) = the baseline for the strip
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/cutout_arms.log
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
run() {
  local T=$1 J=$2; shift 2
  local DL=scratchpad/orange/cutout_arm_$T.log
  echo "[cutout] $(date +%H:%M:%S) start arm $T: $J $*" | tee -a $L
  python3 engine/dive.py $J --seed 1234 $NIGHTLY --tag $T "$@" > $DL 2>&1
  echo "[cutout] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
  grep -E "stage-echo|nest:|-> output|Traceback|Error" $DL | tail -n 10 | cut -c1-220 | tee -a $L
}
run cutout_a journeys/valdes_blow.json --from-card 6 --src-version v1 --frames 288 --no-loop --stage-echo-cutout 0
run cutout_b journeys/valdes_blow.json --from-card 6 --src-version v1 --frames 288 --no-loop --stage-echo-cutout 0.5
run cutout_c journeys/lab/lepidolite_halo_var.json --from-card 6 --src-version v3 --frames 224 --no-loop --stage-echo-cutout 0.5
run cutout_d journeys/valdes_blow.json --from-card 6 --src-version v1 --frames 288 --no-loop
echo "[cutout] $(date +%H:%M:%S) all arms done" | tee -a $L
