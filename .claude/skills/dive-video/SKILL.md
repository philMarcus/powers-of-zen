---
name: dive-video
description: Produce a Zoomer dive video (Powers-of-Ten-style AI zoom short) from a world-card journey file, using the local ComfyUI + feedback-zoom engine. Use when asked to make, render, or iterate on a dive/zoom video, or to add a journey.
---

# Producing a Zoomer dive video (ENGINE 2)

## What this produces
A 9:16 looping short that dives continuously through scale registers (×10 per card), with the
10ⁿ odometer counter and an exact loop. Length comes from CARD COUNT (every card is one bar):
5 cards ≈ 11.7s · 7 ≈ 16.3s · 10 ≈ 23.3s · 11 ≈ 25.7s. Output: `output/<journey>/vN/`
(never overwritten) with `<journey>.mp4` (primary, zoom-out), `<journey>_divein.mp4`,
`build/frames/`, `build/track.jsonl` (per-frame aim/track debug) and `run.json` (provenance:
model, checkpoint, style, seed).

## Prerequisites
- ComfyUI running: `bash /mnt/c/Users/Phil/start_comfyui.sh` (tmux `comfy`);
  health `curl -s localhost:8188/system_stats`. It does NOT survive a reboot.
- Ollama up for captions (localhost:11434, `mistral-small3.2:24b`).
- Run everything from `/mnt/c/Users/Phil/zoomer`. ONE GPU job at a time.

## Commands
```bash
python3 engine/dive.py journeys/<j>.json                  # render (DreamShaper by default)
python3 engine/dive.py journeys/<j>.json --frames 30 --no-video   # smoke test
python3 engine/dive.py journeys/<j>.json --resume         # continue newest vN after a crash
# active journeys live flat in journeys/; legacy schemas in journeys/engine1|engine0
# (resolve names in python via pipeline.journey_path(), never a hand-built path)
python3 scripts/caption.py <j>                            # 5 caption options (local VLM)
python3 scripts/queue_review.py <j> ds [--src output/<j>/vN]     # -> Video Review
python3 scripts/night_batch.py [j ...]     # batch: auto-picks from the journey queue (no args)
                                           # or renders exactly these; per journey render ->
                                           # queue_review -> caption. render_batch.sh wraps it.
                                           # A 01:30 Task Scheduler job runs it nightly — check
                                           # the queue in the dashboard's Journeys tab before
                                           # rendering by hand (SCHEDULER.md).
python3 scripts/track_lab.py overlay output/<j>/vN        # SEE the tracking (aim/lock overlay)
python3 scripts/track_lab.py selftest                     # propagation math vs zoom_transform
```
~17–20s/frame with tracking + depth-CN (196-frame medium ≈ 60 min). Renders are cheap in
CONTEXT (GPU work happens outside the model) — run them in the background and read the log.

## Flags for A/B only, not normal use
- `--cn 0` — drop the depth ControlNet, KEEP tracking. **The CN stays at 0.45** (Phil's call
  2026-07-31: with it the dive holds coherently on ONE object; without it the zoom wanders).
- `--plain` — no tracking AND no CN (engine-1-style pure feedback zoom). NOT the CN test.
- `--style <deck name>` look A/B · `--model turbo|ds` (ds is the house default).

## What the engine does (settled 2026-07-31 — don't re-derive or re-litigate)
1. **Uniform bars.** Every card in a journey shares one `dur` (4 = a bar). Mixed durations made
   the zoom curve vary in period card-to-card and read arrhythmic.
2. **Engine-1 zoom curve** on every card (arrive→look→plunge, sin²). Seam cards zoom at the
   SAME rate — the dive never stops.
3. **Morphs land on the beat.** Each boundary gets engine-1 intensity (0.40 travel + 0.18) with
   a 2-frame anacrusis pickup peaking ON the downbeat. A SEAM is that same intensity held for
   MORE FRAMES (12 vs 6) — never a harder per-frame change (that produced hard cuts).
4. **Composition, never centering.** `track.py` eases the object toward the run's FROZEN
   rule-of-thirds anchor (corner rotates per scale): objects hold ~0.22 off-center instead of
   sliding to the middle. Heading changes only at card boundaries (= on a beat).
5. **TRACKER v3.** Emergence point → `detect.locate` every 4th frame → gentle corrections;
   redirects need two agreeing observations and are gated to the first 10 frames. Misses are
   NORMAL — the known zoom geometry carries the dive between detections.
6. **Depth ControlNet 0.45** on approach frames holds the target's identity while pixels fully
   regenerate (not a paste).

## Journey files
The **journey-composer** skill is the authoring law. Schema in brief: per card `name`, `exp`,
`kind` (zoom|seam), `dur` (uniform), `palette`, rich static `scene`, PLAIN `target` (bare
object — no location, no other object's name), short `target_phrase`; top-level `style` (a deck
NAME), `format` {beats_per_bar, exact_loop, counter}, optional `render_start`.
Engine-critical rules:
- **`scene` never describes the frame** ("fills the view" is banned) — it describes the WORLD;
  the engine decides frame fill. A close-up scene rendered cold invents its own context (this
  is what made frost_window open as a fern on a desk).
- **`render_start`** rotates the circular card list so frame 0 — the only txt2img frame — lands
  in an ABSTRACT realm. Never let it put the seam card first or LAST (last silently destroys
  the seam via the loop-home branch; grammar warns).
- **counter ON by default** — the odometer pins to the current register and spins at handoffs,
  honest even across seams. `false` only where a realm is fictional and 10ⁿ m would be a lie.
- Journeys are CIRCULAR: the last card dives back into card 0's world, and the grammar
  auto-derives that loop target from `regs[0]` (`loop_target` if present, else its scene) — so
  never hand-author a last-card target for the loop.

## Mascot cast (ONE cameo per video, scale-matched, size ≥0.12, rotate the cast)
| exp | register | mascot |   | exp | register | mascot |
|---|---|---|---|---|---|---|
| -15 | quark | Clark |  | 1 | flora/tree | Dora |
| -10 | atom | Adam |    | 3 | city | Kitty |
| -8 | molecule/DNA | Tina | | 5 | landmass | Lorraine |
| -5 | cell | Belle |    | 7 | planet | Janet |
| -3 | small creature | Lee | | 11 | star | Lamar |
| 0 | human scale | Newman | | 21 | galaxy | Aleksey |
|  |  |  | | 26 | cosmos | Amos |
A cameo may sit on any card EXCEPT one whose frames fall inside the loop tail (the last ~24
frames morph home and would smear it). Card 0 is fine — the engine pastes from frame 1.

## After a render
`queue_review.py` then `caption.py` — THAT order. `queue_review.py` creates the pipeline.json
entry; `caption.py` silently throws its output away if there is no entry to write into (it still
prints "5 caption+title pairs", so the log looks fine). Then in
the dashboard: mark a start frame → **Approve → Music** (phase-shifts, then generates + aligns 5
candidates at the format's bpm) → choose a track → Production → the scheduler posts.

## Debugging
- `build/track.jsonl` + `track_lab.py overlay` show exactly what the camera aimed at and why.
- `run.json` records which checkpoint really produced a render. The run dir has NO `_ds` suffix
  when the style deck picks the model — that is not a turbo render.
- ComfyUI's `Model SDXL` log line is the ARCHITECTURE, not the checkpoint (DreamShaper XL is an
  SDXL fine-tune). To prove what ran, read `run.json` or ComfyUI `/history`.
