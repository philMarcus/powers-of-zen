# Powers of Zen — project orientation (read this first)

This file is the durable "read me first" for anyone (Claude or Phil) picking the project
up in a fresh session. Nothing important should live only in a conversation. Deep detail
lives in `PLAN.md`; this file is the map and the mental models.

## What this is
An agent-assisted pipeline that produces and posts **"Powers of Ten"-style continuous-zoom
short videos** — seamless looping dives through morphing worlds across every scale of the
universe (city → cosmos → quantum → back). Brand: **Powers of Zen**, on TikTok, YouTube
Shorts, Instagram (all @powersofzen / powers.of.zen). Goal: followers. It's an ATTENTION
project, not a science project — loose science as awe-garnish, visuals maximized.
Everything runs LOCAL and FREE on Phil's RTX 3080 (no paid APIs).

## The mental models we've settled on (the "why", learned the hard way)
- **Three-layer format** (see PLAN.md): FORMAT (fixed signature — zoom/denoise schedules,
  10ⁿ counter, exact loop) / STYLE (checkpoint + palette deck) / JOURNEY (infinitely
  varied world-cards). Journeys are SLOT FILLERS compiled through fixed grammar templates,
  never raw prompts — this is what keeps infinite variety on-brand.
- **Build-IN, not build-out.** The engine dives inward (crop-and-reimagine); build-out
  (shrink+outpaint) was tested and REJECTED by Phil as "awful". Journeys authored
  LARGE→SMALL with next_target chains, CIRCULAR (last card targets first world).
- **Zoom, not morph.** ×10 per register, arrive→look→plunge pacing, targets named once,
  denoise low enough that structures persist. The whole engine exists to fight morph-feel.
- **Two seams, don't conflate:** the LOOP point (last frame = first, unavoidably at a cut)
  vs the EXOTIC WRAP (quark→cosmos). Phase-shift playback so both land mid-video and the
  opening is a stable macro-realm frame (scripts/phase_shift.py).
- **The cost lesson:** rendering is cheap (GPU work is OUTSIDE model context); browser
  posting is expensive (screenshots ACCUMULATE in context, cost compounds quadratically).
  Put work where it's cheap; keep images out of the accumulating context; delegate vision
  to subagents/local models. This drives the whole agent architecture (PLAN.md).

## Where things live
- `PLAN.md` — plan of record: all decisions, the end-to-end architecture, doctrines.
- `engine/dive.py` — the renderer (ComfyUI API feedback-zoom, counter, loop, cameos).
- `engine/grammar.py` — compiles world-card journeys → prompts + per-frame schedules.
- `journeys/*.json` — the world-card journeys (Layer 3). `journeys/VARIATIONS.md` — the
  differentiation library the Journey Composer draws from (Phil edits it directly).
- `scripts/` — phase_shift.py (intentional openings), zen_browser.py (CDP driver),
  start_chrome_zen.sh, overnight.sh (render batches), mascot_concepts.py.
- `output/<journey>/vN/` — renders (NEVER overwritten; finals at root, build/ = intermediates).
- `output/mascots/canon/` — the chosen mascot cast (hidden Waldo-style cameos, one per video).
- `review/` + `review_divein/` — phase-shifted cuts still IN REVIEW (zoom-out / dive-in).
- `production/` — chosen-model cuts of videos MARKED READY (queue.json points here).
  `production_alternates/` — the other-model counterpart. Promote via
  `scripts/promote.py <journey> <turbo|ds>` (the standard "approve" step).
- `outbox/pipeline.json` — SINGLE SOURCE OF TRUTH (every video's model/cut/caption/state/
  platforms). `outbox/telemetry.jsonl` — event log. `scripts/pipeline.py` — shared lib.
  (outbox/queue.json is legacy, superseded by pipeline.json.)
- `dashboard/app.py` — Streamlit ops dashboard (Queue/Review/Live/Failed/Telemetry,
  editable captions). Run via Windows streamlit → localhost:8501 (scripts/start_dashboard.sh).
- `scripts/poster.py` — the posting harness (CDP + local VLM checks). `scripts/scheduled_post.bat`
  + `scripts/SCHEDULER.md` — Windows Task Scheduler auto-poster (08:00/18:00, no Claude).
- DAILY LOOP: approve a video in the dashboard (review→queued) → Task Scheduler runs
  poster.py → posts to all 3 → pipeline marks live + telemetry. Claude only writes captions.
- Every video gets a scale-matched mascot cameo (size ≥0.12, full-cast rotation) → the
  find-the-character caption. Music is a QUALITY priority: phase-dynamic (intensify on
  plunge, chill on hover), moving toward local MusiConGen — see PLAN.md.
- `.claude/skills/dive-video/` — how to make a video. `.claude/skills/zen-post/` — how to
  post one (the playbook the future local harness will execute).

## How to work on this
- Skills: invoke `/dive-video` to make/iterate a video, `/zen-post` to post (currently the
  playbook; being ported to a local harness). Follow the skill files — they encode hard-won
  authoring rules (no double-objects, creature chains don't nest, empty human interiors,
  vary cameos, never open on the exotic seam, etc.).
- ComfyUI must be up (`/mnt/c/Users/Phil/start_comfyui.sh`, API at localhost:8188). Ollama
  at 192.168.68.1:11434. ffmpeg is the Windows winget build (path in PLAN.md / engine).
- ALWAYS run python from the project root (module imports assume it). Use absolute paths.
- Commit source (not output/, review*, chrome_zen/ — all gitignored).

## Current state (update this line as it changes)
2026-07-28: MUSIC SYSTEM built + shipping. Custom AI music via ComfyUI-native ACE-Step 1.5
(engine/music.py) + phase-dynamic scorer/aligner (scripts/score.py, scripts/align.py) +
music-review stage (scripts/music_gen.py + dashboard 🎵 Music panel). METHOD: the model
writes the music; we tempo-lock generation to the morph grid (bar = morph interval) and
align the track's OWN accents to the morphs; prompts are anacrusis-forward + scene-themed
per journey (journeys/*.json `music_theme`, editable in the dashboard). night_bloom shipped
with music. Chosen: night_bloom (304 overlay), alexandria/food_chain=deep, snowfall=choir.
POSTER hardened tonight: YouTube opens via Create→"Upload videos" (/upload bounces to the
content list), YouTube title-retry, TikTok WAITS for the music copyright check (never click
"Post now" on the incomplete-check modal — it kills the post), Instagram Next/Share/Done use
SYNTHESIZED mouse clicks (el.click is ignored by IG's React). ALWAYS verify a post against
the live page — "posted" strings lie (repeated TikTok false-positives tonight).
OPEN ISSUES: (1) TikTok DROPS with-music posts — publishes then vanishes, even posting by
hand; likely custom audio on a new account. Test a silent post / use a TikTok-licensed sound.
(2) THE SEAM IS UNSOLVED — the loop cut is still ugly. The "fix" so far (grammar loop-tail
denoise 0.18→0.12 + authoring loop pairs to name the first world) does NOT fix it: the last
frame is a hard COPY of frame 0 (dive.py), so mismatched worlds hard-cut. NEXT: build a real
seam mechanism with ControlNet — prototype on ISOLATED seam generations (just the last→first
transition frames, not whole videos, iterate fast), THEN wire into engine/dive.py's loop tail.
Six journeys authored tonight (cosmic_scales_remix, circuit_city, stormglass + reworked
antenna_ball/skyfog/mineral_heart); only cosmic_scales_remix & circuit_city turbo rendered
(RAW, un-phase-shifted → seams at the ends). Full detail in PLAN.md.
