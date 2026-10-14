#!/bin/bash
# valdes_blow v2 = THE ECHO CUT-OUT full video for Phil (2026-10-14): --from-card 6 of v1 (cards 0-5 byte-identical
# to the nightly render in Review), the nightly's flags (echo texture relief + half-lit, nesting, fog phrase) plus the
# cut-out HERO on the three echo cards (whale on tubes k6, callosity on lattice k7, coiled protein chain on tracks k8).
# Re-points the Review entry at v2 (caption + music candidates kept; v1 stays on disk), builds the side-by-side
# review/compare/valdes_blow_CUTOUT.mp4 (v1 words-only echo | v2 cut-out) and a strip. Waits for the arm chains.
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/cutout_arms.log
J=valdes_blow
DL=scratchpad/orange/cutout_full.log
: "${CUT_FLAGS:=--stage-echo-cutout 0}"
while tmux has-session -t =cutout 2>/dev/null || tmux has-session -t =cutouta2 2>/dev/null; do sleep 20; done
cp -n review_divein/${J}_ds_divein.mp4 review/compare/${J}_v1_divein.mp4 2>/dev/null
echo "[full] $(date +%H:%M:%S) start $J --from-card 6 --src-version v1 ($CUT_FLAGS + nightly flags)" | tee -a $L
python3 engine/dive.py journeys/$J.json --seed 1234 --plate live --plate-cn 0 --plate-void-gate --plate-intro mix \
  --palette-anchor 0.5 --stage-auto --stage-preroll 16 --stage-nest --stage-variety \
  --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase \
  $CUT_FLAGS --from-card 6 --src-version v1 > $DL 2>&1
RC=$?; echo "[full] $(date +%H:%M:%S) dive rc=$RC" | tee -a $L
grep -E "nest:|stage-echo|-> output|Traceback|Error" $DL | tail -n 16 | cut -c1-220 | tee -a $L
if [ $RC -ne 0 ]; then echo "[full] $(date +%H:%M:%S) done (failed)" | tee -a $L; exit $RC; fi
V=$(ls -d output/$J/v* | sort -V | tail -n 1)
echo "[full] run dir $V" | tee -a $L
python3 scripts/queue_review.py $J ds --src $V >> $DL 2>&1; echo "[full] queue_review rc=$?" | tee -a $L
if [ -f review/compare/${J}_v1_divein.mp4 ] && [ -f review_divein/${J}_ds_divein.mp4 ]; then
  bash scratchpad/orange/sbs2.sh review/compare/${J}_v1_divein.mp4 review_divein/${J}_ds_divein.mp4 \
       review/compare/${J}_CUTOUT.mp4 "echo words" "cut-out echo" | tee -a $L
fi
python3 scratchpad/orange/cutout_strip.py scratchpad/orange/cutout_full_strip.png 2>&1 | tail -n 6 | tee -a $L
echo "[full] $(date +%H:%M:%S) done" | tee -a $L
