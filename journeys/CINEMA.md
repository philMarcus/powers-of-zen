# CINEMA.md — the camera doctrine (ENGINE 3 Phase D, first cut 2026-08-27)

The camera vocabulary lives OUTSIDE journey authoring: composers never write `camera`
fields (the composer skill stays blind to them); scripts/cinematographer.py assigns
plans after a journey is finished, and engine/camera.py compiles + enforces them.
This file is the doctrine both obey.

## The iron law (from PLAN "ENGINE 3" — every move obeys all four)
1. The scale-zoom never stops and never changes rate. Moves are ADDITIVE residuals on
   top of the scheduled ×10-per-card dive.
2. Moves are musical events: rates are zero during a card's arrival morph, smoothstep up
   over one beat, hold, and smoothstep back to zero over the card's last beat (the
   envelope in engine/camera.py — inflections land on beats by construction).
3. The loop must close. The envelope's zero-rate card boundaries + a camera-free
   render-start card (it is also the loop lap/tail card) close the loop structurally —
   no angle bookkeeping needed.
4. Every frame stays freshly generated: moves are per-frame warps on the fed-back frame,
   healed by re-diffusion (the parallax-residual mechanism, gate-passed 2026-08-22).

## The vocabulary (v1 — proven mechanisms only)
| move    | what it does                                          | cap (per frame) |
|---------|-------------------------------------------------------|-----------------|
| roll    | extra rotation beyond the format's 0.15°/frame        | 0.6°            |
| spiral  | revolution about the TRACKED object while diving in   | 0.5°            |
| orbit   | revolution about the median plane (field cards)       | 0.5°            |
| vertigo | near-field perspective stretch against the zoom       | 0.015           |
| tilt    | pitch — horizon rises (the `landing` component)       | 0.5°            |

Depth moves (everything but roll) ride the SAME fused residual warp + depth field as
DEPTH 2.0's parallax (one resample per frame, engine/warp.camera_residual) and need
parallax_gain > 0. Orbit-class frames get a denoise floor (cfg camera_den_floor, 0.48)
— the orbit-v3 gate showed re-synthesis must outpace resample loss or the warp smears.

## Where moves may NOT go (validator-enforced, engine-enforced)
- the render-start card (it is the establish frame AND the loop lap/tail re-renders it)
- seam cards (they dwell, then the NEXT arrival morphs — moves would blur the event)
- the card arriving FROM a seam (its morph IS the event)
- cameo cards: depth moves never (sprite paste propagation is exact only for
  zoom+roll); v1's cinematographer skips them entirely

## The rule floor (cinematographer v1, deterministic)
Moves are spice, not sauce. Per journey: at most one spiral (first eligible target
card), one orbit (first eligible field card), two rolls (alternating sign, phase seeded
by the journey name). Everything else stays on plain drift. An LLM taste pass (v2) may
later override the floor, never the caps or exclusions.

## Hero moves (Phase 4 — designed, NOT built; labs gate them)
- `landing` (planet → landscape): approach under slight orbit → tilt ramps the horizon
  into frame → fast low terrain SKIM (strong parallax) → normal card into one feature.
  Needs: tilt at rate over multiple cards + scaffold surface mode agreement + prompt
  attitude ramps. Gate: landing_lab.
- `threshold` (exterior → interior): tracker aims at an aperture's dark opening; the
  crossing lands ON a beat (dolly surge + prompt flip + light change) into a new
  `chamber` scaffold mode. Gate: threshold_lab.

## Labs (12fps SLOW LOOPED clips, one variable per arm — Phil's standing format)
scripts/camera_lab.py renders same-seed arms of a journey with hand-written camera
plans in derived specs (output/camera_lab/specs/ — the catalog is never touched).
