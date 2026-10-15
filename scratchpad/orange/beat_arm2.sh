#!/bin/bash
# BEAT ARM 2: pickup 2 frames + a smaller window (0.22 W) — pickup 3 / 0.28 W moved the flip from -7 to -4.5 f (the
# frames: the window opens at -3..-2); the unstaged morph's pickup is 2 frames. Frames 128..203 cover both handoffs
# (160, 192) + the 11 frames the measure needs. Runs after tmux paintm1b.
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
while tmux has-session -t =paintm1b 2>/dev/null; do sleep 20; done
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
T=beat_pickup2; DL=scratchpad/orange/beat_arm_$T.log
echo "[beat] $(date +%H:%M:%S) start arm $T: valdes_blow --from-card 4 --frames 204 --stage-preroll-pickup 2 --stage-preroll-window 0.22" | tee -a $L
python3 engine/dive.py journeys/valdes_blow.json --seed 1234 $NIGHTLY --tag $T --from-card 4 --src-version v2 --frames 204 --no-loop --stage-preroll-pickup 2 --stage-preroll-window 0.22 > $DL 2>&1
echo "[beat] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
grep -E "Traceback|error:" $DL | tail -n 2 | tee -a $L
V=$(ls -d output/valdes_blow_platelive_$T/v* | sort -V | tail -n 1)
python3 scratchpad/orange/beat_measure.py $V/build/frames 32 160,192 "pickup 2" 2>&1 | tee -a $L
echo "[beat] $(date +%H:%M:%S) beat2 done" | tee -a $L
