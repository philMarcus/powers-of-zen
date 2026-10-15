#!/bin/bash
# queue the plate-style full video after the pickup-2 beat arm; PICKUP = 2 if its mean flip lands within -1.5..+1 f,
# else 3 (the measured better-than-today value); FIELDS=0 (the fog fix gives the dark ground).
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
while tmux has-session -t =beatq2 2>/dev/null; do sleep 20; done
M=$(grep -E "^pickup 2: mean flip" $L | tail -n 1 | sed -E 's/.*mean flip ([-+0-9.]+) f.*/\1/')
P=3
if [ -n "$M" ] && python3 -c "import sys; m=float('$M'); sys.exit(0 if -1.5 <= m <= 1.0 else 1)"; then P=2; fi
echo "[full] $(date +%H:%M:%S) pickup-2 mean flip = ${M:-n/a} f -> PICKUP=$P for the full video" | tee -a $L
FIELDS=0 PICKUP=$P bash scratchpad/orange/paint_full.sh
