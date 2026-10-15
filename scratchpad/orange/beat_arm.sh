#!/bin/bash
# BEAT ARM (2026-10-15, Phil: staged handoffs flip before the beat): valdes_blow cards 4-6 (handoffs 4->5 unstaged->
# stage at frame 160, 5->6 stage->stage at 192) with --stage-preroll-pickup 3 vs v2's own frames (today's pre-roll).
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
while tmux has-session -t =paintm2 2>/dev/null; do sleep 20; done
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
T=beat_pickup; DL=scratchpad/orange/beat_arm_$T.log
echo "[beat] $(date +%H:%M:%S) start arm $T: valdes_blow --from-card 4 --frames 224 --stage-preroll-pickup 3" | tee -a $L
python3 engine/dive.py journeys/valdes_blow.json --seed 1234 $NIGHTLY --tag $T --from-card 4 --src-version v2 --frames 224 --no-loop --stage-preroll-pickup 3 > $DL 2>&1
echo "[beat] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
grep -E "nest:|STAGE |Traceback|error:" $DL | tail -n 4 | cut -c1-200 | tee -a $L
V=$(ls -d output/valdes_blow_platelive_$T/v* | sort -V | tail -n 1)
python3 scratchpad/orange/beat_measure.py output/valdes_blow/v2/build/frames 32 160,192 "today   " 2>&1 | tee -a $L
python3 scratchpad/orange/beat_measure.py $V/build/frames 32 160,192 "pickup 3" 2>&1 | tee -a $L
echo "[beat] $(date +%H:%M:%S) beat arm done" | tee -a $L
