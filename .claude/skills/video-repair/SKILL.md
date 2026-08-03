---
name: video-repair
description: Repair an EXISTING dive render without a full re-render — replace a bad opening card, replace an ugly loop-seam tail, or produce/install a repaired candidate for a video already in production (phase-shifted + music). Use when asked to fix a video's opening, seam, loop, or ending, or to reseam/re-home a render.
---

# Repairing an existing dive video (IPA homing toolkit, built 2026-08-02)

Full re-renders cost ~an hour and lose an approved video's good body. These tools regenerate
only the broken stretch, resuming the feedback chain from saved frames (the engine's only heavy
state is the previous frame; everything else is a pure function of the frame index). All are
non-destructive: output lands in a fresh `output/<name>/vN/` with `run.json` provenance, and
frame count + bar grid are NEVER changed, so music alignment survives.

## Decision tree

1. **The whole video is wrong** (bad world lock-in from frame 0, wrong style, tracker chaos)
   → full re-render via the dashboard reject verdicts (Video Review card → Reject → re-queue).
2. **Opening card is bad, rest is good** (close-up/table-top frame 0 the loop can't come home to)
   → `python3 scripts/replace_opening.py <journey> [--model M] [--src-version vN]`
   The card-0 SCENE is kept — it is passed through mid-dive (it only failed as a cold txt2img
   start). Regenerates old tail + card-0 slots + card 1's arrival as ONE continuous arc.
3. **Opening is fine, loop seam is bad** (render predates the IPA tail, or the wrap reads ugly)
   → `python3 scripts/replace_tail.py <journey> [--model M] [--src-version vN]`
   Regenerates only the last L (24) frames, schedule-faithful, IPA-homing onto frame 0.
4. **Where does the result go?**
   - Video still in REVIEW → add `--queue-review` to either tool (upserts the review file;
     captions are preserved).
   - Video in PRODUCTION / queued-to-post (phase-shifted, music baked) → NO `--queue-review`
     (it would reset pipeline state to review). Instead:
     `python3 scripts/make_candidate.py <journey>` → watch
     `output/candidates/<journey>_candidate.mp4` (same start point, same music — the tool
     MEASURES the production's frame rotation empirically and re-attaches its audio stream) →
     on approval `python3 scripts/make_candidate.py <journey> --install` (backs up to
     `_seam_backup/`, swaps production + the chosen music candidate's aligned copy).
5. **Cutting cards out / mid-video splice** (Level 2) → not yet built; when it is, it reuses
   the same bridge primitive (resume chain → schedule-faithful slots → IPA/CN landing on a
   kept frame). Whole-card cuts remove exactly one bar, keeping the music grid.
6. **Investigating which mechanism looks best** → `python3 scripts/seam_tail_ab.py <journey>
   --methods orig,ipa,ipacn,blendcn` (labeled side-by-side in `output/seam_lab/<name>/`);
   two arbitrary frames → `scripts/seam_lab.py`.

## Rhythm doctrine (each is a TEST to apply to any new splice mechanism)

- **The flip lands ON the bar.** Does any homing (IPA/CN/pixel blend) converge toward a
  junction image BEFORE a bar line? Then the world-change happens off the beat and the actual
  downbeat has nothing to flip. Confine homing to the arrival window after the boundary.
- **Never freeze a plunge.** Does depth-CN or a static-image blend act during a card's plunge
  slots? That visibly decelerates the dive at its maximum-energy moment. Homing belongs in
  arrival/landing frames only; the loop tail is the one exception (its deceleration lands on
  card 0's slow arrive phase across the wrap, which reads as the engine's own breathing).
- **No kept frame may follow a regenerated one across a morph boundary** unless the morph
  itself is regenerated. A kept arrival that morphed out of REPLACED footage pivots to a
  trajectory "from nowhere" (this is why replace_opening regenerates card 1's arrival and
  lands PAST it).
- **Splices are schedule-faithful.** Regenerated slots must use the compiled schedule's own
  prompts/crossfades (`dive.phase_info`) and dive.py's denoise cadence (arrival/transition
  boosts, seam windows, 2-frame anacrusis). `seam_tail_ab.regen_tail` does this — keep it
  bit-matched to dive.py's main loop when either changes.

## Gotchas

- **Pin `--src-version`** to the intended original render. "Newest complete" may be a previous
  repair (its kept frames are byte-copies so results match, but provenance gets murky).
- **Engine-1 sources**: today's grammar must compile to EXACTLY the saved frame count
  (check `len(compile) == frames on disk`) or the slots don't line up — abort if not.
- **Cameos**: replace_opening refuses a cameo in the regenerated slots (move it in the journey
  first); for replace_tail, check the cameo window does not overlap the tail (last 24 frames).
- The native engine already does IPA homing on every NEW render (dive.py exact-loop tail;
  `--classic-tail` restores the old gap-scaled morph for A/B) and renders frame 0 wide
  (T_ESTABLISH + anti-close-up negatives). These tools exist for renders made before that,
  and for surgical fixes that keep an approved body.
- Legacy tools `repair_seam.py` + `reseam_production.py` are superseded by replace_tail +
  make_candidate `--install` (same measurement/swap contract); keep them for reference.
