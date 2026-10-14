#!/bin/bash
# re-run of the painted LATTICE arm with the field fix (the fog had covered the painted field), after tmux paint ends
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
while tmux has-session -t =paint 2>/dev/null; do sleep 20; done
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase"
EL7="sulfur atom, a tight tangerine glowing core wrapped in a broader amber haze and a thin ultramarine outer veil"
FL7="dim knots of neighbouring electron fog at the margins of an ink-black void, tangerine and ultramarine"
T=paint_l1b; DL=scratchpad/orange/paint_arm_$T.log
echo "[paint] $(date +%H:%M:%S) start arm $T: lattice paint WITH the painted field" | tee -a $L
python3 engine/dive.py journeys/valdes_blow.json --seed 1234 $NIGHTLY --tag $T --from-card 7 --src-version v2 --frames 256 --no-loop \
  --stage-paint --stage-element "7=$EL7" --stage-field "7=$FL7" > $DL 2>&1
echo "[paint] $(date +%H:%M:%S) arm $T rc=$?" | tee -a $L
grep -E "stage-paint|STAGE |Traceback|Error" $DL | tail -n 4 | cut -c1-220 | tee -a $L
sed -i "s#latest(f'{Z}/output/valdes_blow_platelive_paint_l1')#latest(f'{Z}/output/valdes_blow_platelive_paint_l1b')#" scratchpad/orange/paint_strip.py
python3 scratchpad/orange/paint_strip.py 2>&1 | tail -n 8 | tee -a $L
echo "[paint] $(date +%H:%M:%S) l1b done" | tee -a $L
