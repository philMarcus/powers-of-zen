---
name: dive-video
description: Produce a Zoomer dive video (Powers-of-Ten-style AI zoom short) from a world-card journey file, using the local ComfyUI + feedback-zoom engine. Use when asked to make, render, or iterate on a dive/zoom video, or to add a journey.
---

# Producing a Zoomer dive video (ENGINE 2)

## What this produces
A 9:16 looping short that dives continuously through scale registers (×10 per card), with the
10ⁿ odometer counter and an exact loop. Length comes from card count × tempo — seconds ≈
cards × fpb/3 (fpb 6–9, see journey-composer TEMPO). Output: `output/<journey>/vN/`
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
python3 engine/dive.py journeys/<j>.json --from-card K [--seed S] [--src-version vN]
    # PARTIAL re-render: copy cards 0..K-1's frames from an existing render into a FRESH vN
    # (source untouched) and regenerate from card K on — new seed and/or edited later cards.
    # Card = journey register (boundaries only). Refuses the loop tail (use repair_seam) and
    # cameo-window interiors. Dashboard path: review card → ↻ from-card box + Reject → re-queue.
python3 engine/dive.py journeys/<j>.json --no-resolve   # A/B: disable resolve-on-approach depth scaffolds (DEFAULT ON)
# active journeys live flat in journeys/; legacy schemas in journeys/engine1|engine0
# (resolve names in python via pipeline.journey_path(), never a hand-built path)
python3 scripts/caption.py <j>                            # 5 caption options (local VLM)
python3 scripts/queue_review.py <j> ds [--src output/<j>/vN]     # -> Video Review
python3 scripts/night_batch.py [j ...]     # batch: auto-picks from the journey queue (no args)
                                           # or renders exactly these; per journey render ->
                                           # queue_review -> caption. render_batch.sh wraps it.
                                           # A 01:30 Task Scheduler job runs it nightly — check
                                           # the queue in the dashboard's Journeys tab before
                                           # rendering by hand (scripts/SCHEDULER.md). After all
                                           # renders, one music-pregen pass runs over the newly
                                           # rendered journeys.
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
- `--no-resolve` — disable resolve-on-approach depth scaffolds (they are DEFAULT ON).
- `--parallax <gain>` — DEPTH 2.0 depth-differential parallax on the fed-back frame
  (PLAN "PARALLAX ERA"). **DEFAULT 1.0 = Phil's final verdict 2026-08-23** ("more freedom
  and diversity in the shifts between cards, more depth-filled world — no downside");
  `--parallax 0` = the off A/B. `--resolve-persist` (parked — measured ~no-op at current
  card lengths) keeps arrival scaffolds as the parallax depth source until card end.
  `--micro` = Phase C musical micro camera moves, DEFAULT OFF — Phil judges its
  with/without A/B separately; never flip these defaults without his verdict recorded here.

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
7. **Frame 0 renders WIDE** (2026-08-02): the only txt2img frame uses grammar's T_ESTABLISH
   (scene panoramic, NO target) + anti-close-up negatives — the schedule's travel prompt names
   the card target, which in txt2img composes a product-shot close-up (seed-held ablations).
8. **IPA loop homing** (2026-08-02): the exact-loop tail conditions generation on frame 0's
   IMAGE (IP-Adapter ramp) + depth-CN landing alignment + a small FIXED blend — the world
   converges on home while every frame stays freshly rendered and diving. `--classic-tail`
   restores the old gap-scaled pixel morph for A/B.
9. **RESOLVE-ON-APPROACH depth scaffolds — default ON** (engine/scaffold.py; windows
   auto-derived per card, journey `resolve` field overrides/opts out). Since 2026-08-17 they
   carry scaffold v3 (per-instance looming + painter's-algorithm occlusion) plus a
   depth-of-field clause appended to resolve-window prompts; palette-gloom and depth-aware
   detail_boost were deliberately HELD by Phil.

## Repairing an existing render (don't full re-render for a fixable defect)
See the **video-repair** skill: `replace_opening.py` (bad opening card — scene kept, arc
through card 1's arrival), `replace_tail.py` (bad loop seam only), `make_candidate.py`
(preview/install a repair for a video already in production, same start + same music).

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

## Mascot cast (ONE cameo per video, REALM-matched: |card.exp − mascot.exp| ≤ 3, hard-failed by audit_starts; size ≥0.12; cast rotation only breaks ties among passers)
| exp | register | mascot (display name) |   | exp | register | mascot (display name) |
|---|---|---|---|---|---|---|
| -15 | quark | clark (Clark the Quark) |  | 1 | flora/tree | dora (Dora the Flora) |
| -10 | atom | adam (Adam the Atom) |    | 3 | city | kitty (Kitty the City) |
| -8 | molecule/DNA | tina (Tina the DNA) | | 5 | landmass | lorraine (Lorraine the Terrane) |
| -5 | cell | belle (Belle the Cell) |    | 7 | planet | janet (Janet the Planet) |
| -3 | small creature | lee (Lee the Flea) | | 11 | star | lamar (Lamar the Star) |
| 0 | human scale | newman (Dwight the Light) | | 21 | galaxy | aleksey (Alexis the Galaxy) |
|  |  |  | | 26 | cosmos | amos (Cosmo) |

The lowercase key is the IDENTIFIER — sprite filename (`output/mascots/canon/<key>.png`), the
journey's `cameo.sprite`, `pipeline.MASCOT_EXP`, the pipeline entry's `cameo` field. The name in
parentheses is the DISPLAY name and is what every user-facing string says (captions, the spot
question, hashtags, the dashboard) — `pipeline.MASCOT_DISPLAY` is the single source. Note two
display first names differ from their key on purpose: `newman` → Dwight, `aleksey` → Alexis.
Never rename a file or a JSON field to match a display name.
A cameo may sit on any card EXCEPT one whose frames fall inside the loop tail (the last
L = round(24 × fpb/7) frames — 21–31 across the catalog — morph home and would smear it).
Card 0 is fine — the engine pastes from frame 1.

## After a render
`queue_review.py` then `caption.py` — THAT order. `queue_review.py` creates the pipeline.json
entry; `caption.py` silently throws its output away if there is no entry to write into (it still
prints "5 caption+title pairs", so the log looks fine). Then in
the dashboard: mark a start frame → **Approve → Music** (phase-shifts, then REALIGNS the
overnight pregen candidates in seconds — `music_gen --realign`; full generation only if no
pregen exists) → choose a track → Production → the hourly post_gate fires on the
post_every_hours (19h) cadence, holding the window when nothing is queued (scripts/SCHEDULER.md).

## Debugging
- `build/track.jsonl` + `track_lab.py overlay` show exactly what the camera aimed at and why.
- `run.json` records which checkpoint really produced a render. The run dir has NO `_ds` suffix
  when the style deck picks the model — that is not a turbo render.
- ComfyUI's `Model SDXL` log line is the ARCHITECTURE, not the checkpoint (DreamShaper XL is an
  SDXL fine-tune). To prove what ran, read `run.json` or ComfyUI `/history`.
