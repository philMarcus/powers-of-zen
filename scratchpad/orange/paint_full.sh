#!/bin/bash
# valdes_blow v3 = THE PLATE-STYLE full video (2026-10-15; the M2 recipe: today's leash + repaint, the AI's element
# pictures on the kit's spheres at 0.9, identity 0.5, bold scale, a dark ground) on all four staged cards, from card 5
# of v1 (cards 0-4 byte-identical to the nightly render). FIELDS=1 paints the authored far-field lines blurred/dimmed
# behind the elements; FIELDS=0 relies on the (now near-black) fog. Re-points the Review entry at v3 (v2 stays on
# disk), builds the side-by-side review/compare/valdes_blow_PAINT.mp4 (v1 nightly | v3 painted) and drops it in the Lab.
cd /mnt/c/Users/Phil/zoomer
L=scratchpad/orange/paint_arms.log
J=valdes_blow
DL=scratchpad/orange/paint_full.log
: "${FIELDS:=1}"
NIGHTLY="--plate live --plate-cn 0 --plate-void-gate --plate-intro mix --palette-anchor 0.5 --stage-auto --stage-preroll 16 \
  --stage-nest --stage-variety --stage-echo-relief 0.35 --stage-echo-relief-gain 4 --stage-echo-ambient 0.10 --stage-fog-phrase \
  --stage-preroll-pickup ${PICKUP:-0}"
EL5="skin cell, a plump amber polygon with a round olive nucleus, threaded with tangerine keratin strands"
FL5="stacked layers of overlapping keratin plates fading into a profound ink-black ground"
EL6="ribosome bead, a plump two-lobed tangerine bead, a larger lobe capped by a lesser one, glossy"
FL6="a violet cytoplasm haze thinning into ink-black depth"
EL7="sulfur atom, a tight tangerine glowing core wrapped in a broader amber haze and a thin ultramarine outer veil"
FL7="dim knots of neighbouring electron fog at the margins of an ink-black void, tangerine and ultramarine"
EL8="spark, a tiny blazing tangerine-white mote with a short bright tail"
FL8="faint loose curling violet tracks about an ink-black void"
ARGS=(journeys/$J.json --seed 1234 $NIGHTLY --from-card 5 --src-version v1
      --stage-paint --stage-paint-scale bold --stage-paint-tex 0.9 --stage-paint-id 0.5
      --stage-element "5=$EL5" --stage-element "6=$EL6" --stage-element "7=$EL7" --stage-element "8=$EL8")
if [ "$FIELDS" = "1" ]; then
  ARGS+=(--stage-field "5=$FL5" --stage-field "6=$FL6" --stage-field "7=$FL7" --stage-field "8=$FL8"
         --stage-paint-field-blur 14 --stage-paint-field-dim 0.45)
fi
echo "[full] $(date +%H:%M:%S) start $J v3 --from-card 5 --src-version v1 (M2 recipe, fields=$FIELDS, pickup=${PICKUP:-0})" | tee -a $L
# the element/field lines carry spaces: a bash ARRAY keeps each one a single argument (the 06:22 lesson)
python3 engine/dive.py "${ARGS[@]}" > $DL 2>&1
RC=$?; echo "[full] $(date +%H:%M:%S) dive rc=$RC" | tee -a $L
grep -E "stage-paint|nest:|-> output|Traceback|error:" $DL | tail -n 12 | cut -c1-200 | tee -a $L
if [ $RC -ne 0 ]; then echo "[full] done (failed)" | tee -a $L; exit $RC; fi
V=$(ls -d output/$J/v* | sort -V | tail -n 1)
echo "[full] run dir $V" | tee -a $L
python3 scripts/queue_review.py $J ds --src $V >> $DL 2>&1; echo "[full] queue_review rc=$?" | tee -a $L
if [ -f review/compare/${J}_v1_divein.mp4 ] && [ -f review_divein/${J}_ds_divein.mp4 ]; then
  bash scratchpad/orange/sbs2.sh review/compare/${J}_v1_divein.mp4 review_divein/${J}_ds_divein.mp4 review/compare/${J}_PAINT.mp4 "nightly" "painted" | tee -a $L
  python3 scripts/lab_drop.py review/compare/${J}_PAINT.mp4 --title "valdes_blow full video — nightly v1 | painted v3 (M2 recipe)" --note "Staged cards k5 skin cells, k6 ribosome beads, k7 sulfur lattice, k8 sparks; 32 frames per card from frame 160. v3 is also the Review entry."
fi
echo "[full] $(date +%H:%M:%S) done" | tee -a $L
