---
name: dive-video
description: Produce a Zoomer dive video (Powers-of-Ten-style AI zoom short) from a world-card journey file, using the local ComfyUI + feedback-zoom engine. Use when asked to make, render, or iterate on a dive/zoom video, or to add a journey.
---

# Producing a Zoomer dive video

## What this produces
A 9:16 looping short (~12s at defaults) that dives through scale registers
(×10 per register, arrive→look→plunge pacing), with an odometer scale counter
(10ⁿ m) and an exact loop (last frame = first frame). Output lands in
`output/<name>/`: `<name>.mp4` (final), `<name>_zoomout.mp4` (reversed cut —
the small-to-large direction), `<name>_raw.mp4`, and `frames/`.

## Prerequisites
- ComfyUI must be running on the Windows side: `/mnt/c/Users/Phil/start_comfyui.sh`
  (tmux session `comfy`). API health check: `curl -s localhost:8188/system_stats`.
- Run everything from the project root `/mnt/c/Users/Phil/zoomer`.

## Commands
```bash
python3 engine/dive.py journeys/<journey>.json            # render (turbo default)
python3 engine/dive.py journeys/<j>.json --model ds       # DreamShaperXL flavor
python3 engine/dive.py journeys/<j>.json --frames 10 --no-video   # smoke test
python3 scripts/mascot_concepts.py [character_key ...]    # mascot concept art
```
A 144-frame turbo render takes ~8 min; ds ~3× slower. Run full renders in the
background. Never run two GPU jobs concurrently — ComfyUI interleaves them and
both slow down.

## Journey files (world cards — the ONLY thing that varies per video)
Registers are listed in dive order, LARGE → SMALL. Each card:
```json
{ "name": "city", "exp": 3,
  "interior": "what it looks like while traveling through this world",
  "next_target": "the next (smaller) world as first seen from afar" }
```
The last register omits `next_target`. Prompts are compiled from these cards
through fixed grammar templates in `engine/grammar.py` — never write raw prompts
in journeys, and never edit the templates for a single video (they are the
format's signature; tuning them changes ALL future videos).

Top-level keys: `name`, `style_suffix` (Layer-2 style tokens),
`format` (`sec_per_decade` default 3.0, `travel_denoise` default 0.40,
`exact_loop` true/false), `settings` (engine overrides, e.g. `"reverse": true`).

## Scale ladder + mascot cast (canonical; loose science is fine, it's an
attention project, not a science project)
| exp (10ⁿ m) | register | mascot |
|---|---|---|
| -15 | quark | Clark |
| -10 | atom | Adam |
| -8 | molecule/DNA | Tina |
| -5 | cell | Belle |
| -3 | small creature | Lee |
| 0 | human scale (objects only, no faces) | Newman (proposed) |
| 1 | flora/tree | Dora |
| 3 | city | Kitty |
| 5 | landmass/terrain | Lorraine |
| 7 | planet | Janet |
| 11 | star/solar system | Lamar |
| 21 | galaxy | Maxie |
| 26 | cosmos | Amos |

Rules (revised 2026-07-23):
- **Journeys are CIRCULAR.** The last register's `next_target` names the first
  register's world seen from afar — the seam is authored, never patched. With
  `exact_loop` the last frame IS the first frame. The seam pair can be ANY two
  scales (continent→nucleus is fine) — write the blend deliberately.
- The full ladder is one format among many. Slices are fine; fractional scales
  are fine (`exp` may be a float; registers ⅓–½ a decade apart are allowed —
  fish-eats-fish chains, dollhouse recursion). Weight time with per-card `sec`.
  The human/city/creature zone is the variety-rich band — linger there.
- Per-card keys: `exp`, `palette`, `interior`, `next_target`, optional `sec`,
  optional `cameo` {sprite, pos, size}.
- Don't name the same creature/object in two nearby registers — it will render
  at both scales (the double-lantern/double-fly ghost).
- Creature scenes fantastical, never gory. No human faces (negative prompt).
  Mascot names never shown on screen.
- `journeys/VARIATIONS.md` is the differentiation library — per-register
  variant looks and seam pairings. Draw from it; add to it.

## Iron rules
- NEVER overwrite a previous render or mascot round. Renders write to
  `output/<name>/vN/`; mascot rounds to `output/mascots/rN/`. If a tool would
  overwrite, version instead.

## Quality gate before showing Phil
Spot-check frames (e.g. 40%, 70%, 95% of the way through) for: feedback collapse
(image emptying out), palette drift (one color colonizing everything), and loop
integrity (last raw frame should equal frame 0 when `exact_loop`). If a video
must be sent as a file, files >30MiB fail to send — re-encode a preview:
`ffmpeg -i in.mp4 -crf 26 preview.mp4` (masters stay crf 18 for posting).

## Where things live
`PLAN.md` = plan of record (three-layer format doctrine, marketing doctrine,
phases). `engine/dive.py` = renderer; `engine/grammar.py` = compiler (Layer 1).
`journeys/` = world cards (Layer 3). `output/mascots/` = cast art.
`scripts/run_batch.sh` = multi-journey batches.
