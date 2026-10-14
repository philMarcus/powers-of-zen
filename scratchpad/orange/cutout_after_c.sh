#!/bin/bash
# end the arm chain after C (D relief-only baseline and A2 hero-only are redundant with the full render), so the
# full-video chain (tmux cutoutfull, waits on =cutout and =cutouta2) starts ~70 min sooner.
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/cutout_arms.log
while ! grep -q "arm cutout_c rc=" $L 2>/dev/null; do sleep 10; done
sleep 3
tmux kill-session -t =cutout 2>/dev/null
sleep 2
for p in $(pgrep -f "tag cutout_d"); do kill $p 2>/dev/null; done
curl -s -m 10 -X POST http://localhost:8188/interrupt -o /dev/null
curl -s -m 10 -X POST http://localhost:8188/queue -H 'Content-Type: application/json' -d '{"clear": true}' -o /dev/null
echo "[cutout] $(date +%H:%M:%S) chain ended after C (D and A2 skipped: redundant with the full render)" | tee -a $L
