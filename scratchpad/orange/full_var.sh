#!/bin/bash
# STAGE VARIETY full A/Bs (2026-10-10): thousand_moons_var + macaw_lick_var at seed 1234 with the
# production flags + --stage-variety, ingested to Review next to their v1 baselines, plus
# side-by-side cuts review/compare/<j>_VAR.mp4 (today | variety).
cd /mnt/c/Users/Phil/zoomer
for J in thousand_moons macaw_lick; do
  echo "[var] $(date +%H:%M:%S) full ${J}_var"
  bash scratchpad/orange/full_ab.sh ${J}_var 1234 --palette-anchor 0.5 --stage-auto --stage-preroll 16 --stage-variety
  echo "[var] $(date +%H:%M:%S) ${J}_var chain rc=$?"
  if [ -f review_divein/${J}_var_ds_divein.mp4 ] && [ -f review_divein/${J}_ds_divein.mp4 ]; then
    mkdir -p review/compare
    bash scratchpad/orange/sbs2.sh review_divein/${J}_ds_divein.mp4 review_divein/${J}_var_ds_divein.mp4 review/compare/${J}_VAR.mp4 today variety
    echo "[var] $(date +%H:%M:%S) side-by-side -> review/compare/${J}_VAR.mp4"
  fi
done
echo "[var] done"
