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
2026-07-29: THE SEAM IS SOLVED (see PLAN.md "THE SEAM"). Two parts: (A) grammar.py now
auto-derives the last register's loop target from `regs[0]` (loop_target|interior), so the
last frame plunges toward the first world in the SAME words frame 0 uses → first/last render
alike → tiny loop gap (fixed food_chain's "golden cove" that didn't mention the heron). (B)
scripts/repair_seam.py regenerates only the last ~L frames: natural dive (keep zooming) →
palette-match toward frame 0 → gap-SCALED generated morph (light depth-CN, no static blend) →
NO hard-copy of frame 0 (the old `img=frame0.copy()` made 3 identical frames = a loop FREEZE);
optional --cut-tail. Non-destructive (fresh vN, keeps build/frames_orig_seam/), reuses saved
frames (engine is a feedback chain: resume at the seam, no full re-render). Music-safe: morph
grid unchanged → re-align reproduces the lock (food_chain deep = 11.54× before+after), no
frames added. Approved on cosmic (v11) and food_chain. NEXT: fold repair_seam's mechanism into
engine/dive.py's exact_loop tail so every render ends this way, then re-render the self-similar
journeys. POSTER (2026-07-29): now VERIFIES every post against the live page before claiming
success — TikTok checks the content list, IG reads the reel caption (kills the false-positive
"live"); waits for both TikTok checks then a single Post; AI-label clicks the real switch +
verifies; YouTube title read-back retry; IG selects Original (phone 9:16) crop by CONTAINMENT
(default was square). TikTok PAUSED (meta.paused_platforms) — new-account posts publish then
vanish even silent/by-hand (likely under-review/spam flag); scheduler posts YT+IG only. alexandria
live on YT+IG. DASHBOARD refactored: Video Review → 🎵 Music → Production stage flow; Live/Failed
are per-platform (a video can be in both); videos loop. Desktop shortcut: scripts/start_zen_ops.bat.
2026-07-29 (later): seam-repaired PRODUCTION videos via scripts/reseam_production.py — replaces
ONLY the seam frames, keeps start point + music + cut + model. Ran on all 4 (iris/dollhouse/
cartographer/snowfall); Phil KEPT iris + cartographer (clear improvement) and REVERTED dollhouse +
snowfall (their original seams read better — dollhouse/snowfall have the far-world clamp gap 68/73
→ morph 0.82, harder to bridge). Originals in _seam_backup/. KEY TRAP: those production files were phase-shifted to open on a macro frame, but
phase_shift.py's START_REGISTER config has since DRIFTED, so recomputing cut_time() moves the
opening. reseam_production.py MEASURES the actual frame-rotation of the current production vs its
render (residual~0 confirms clean rotation), applies that EXACT integer-frame rotation (trim=
start_frame, NOT seconds — seconds rounds off by a frame and desyncs the copied audio) to the
repaired render, and re-muxes the production's OWN audio. Verified seam-localized (byte-identical
outside the ~24-frame seam) + same opening frame. Backups in _seam_backup/ (gitignored).
DASHBOARD fixes: picking a caption radio now auto-updates the caption+YT fields (session_state, no
refresh); YouTube TITLE = the caption body (the descriptive line before the mascot question) — a
truncation, not a separate write (caption.py drops yt_title generation); removed the dead
"scheduled" timestamp field. GPU FLAG fix: pipeline.gpu_busy() now reads nvidia-smi utilization
(>=30%) instead of matching process names — the old pgrep matched watcher/caption command lines
that merely mentioned dive.py, so the flag never cleared after a render.
2026-07-30: POSTER COLD-BROWSER FIX. The 08:00 scheduled posts kept failing at YT title + IG crop
while EVENING (18:00) posts worked — because every success was a WARM browser I'd been driving, and
the 08:00 run hits a cold/idle session. Flag contexts proved it: YouTube showed the Studio DASHBOARD
with onboarding nags ("Dismiss"/"Skip navigation"/"Catch me up"), Create->Upload no-oped behind them,
and the old flow FALSE-PASSED on a stale '#textbox'[0] element (title then NO_FOCUSed). IG reached
Crop but measured an unrendered <video>. Fix (scripts/poster.py): _yt_dismiss_nags (specific nag
texts only, never the uploads dialog), _yt_open_upload (confirms the REAL uploads dialog opened +
retries), dialog-scoped title selector (dropped the false-passing fallback); IG _ig_dismiss + wait
for the crop <video> to load before the Original check. LESSON (feedback): validate automation in the
conditions it actually runs in — a cold browser via killing+relaunching zen Chrome and a --dry-run —
NOT a warm browser I've been using. Claiming "fixed" off a warm test is why it didn't take twice.
2026-07-30 (afternoon): ENGINE 2.0 — object-zoom targeting (see PLAN.md "ENGINE 2.0" + "FORMAT
2.0"). Problem: the feedback engine center-zooms into whatever fills the frame, so DISCRETE
objects (planets, animals) fly by and the background morphs into the next world — not a real zoom.
BUILT + validated today: (1) Florence-2 detector (ComfyUI-Florence2/Kijai) → engine/detect.py
(referring_expression_segmentation + a SHORT visual phrase → object box, fractional). (2) POC
(scripts/zoom_probe.py): detect→aim cx,cy→depth-CN makes the planet CENTER + GROW (3%→55%) while
staying ALIVE (regenerated every frame, not pasted) — Phil's two guardrails. (3) Integrated:
grammar emits a per-frame `approach` schedule from a register's `target_phrase`; dive.build_workflow
gained depth-CN; the loop detects+aims+CN on approach beats (arrival-morph/counter/seam/music
untouched). First full render = stormglass with targeting on the star register only (planet) —
proves the mechanism; other levels still old-morph. NEXT (Phil's steer, NOT built): FORMAT 2.0 —
targeting on EVERY object level + distinguish ZOOM-IN (contained object, takes time, targeted) from
SEAM/MORPH-BIT (the semantic jump, e.g. atom→cosmos / antenna-tip→planet — instant morph ON THE
BEAT, no zoom time; the large exp-jump already marks these). Require logical object-containment in
journeys + the journey generator; richer scene/interior descriptions. Update dive-video SKILL when
results are good. OPEN: fold seam into dive.py + re-render journeys; TikTok waits (weekend).
2026-07-31: BIG SESSION — full detail in PLAN.md ("TRACKER v3", "POINT-TRACK", "STYLE is Layer 2").
(1) STYLE DECK built (Layer 2): styles/deck.json (curated word-only shiny looks, no realism words) +
engine/style.py + dive.py --style; journeys now set `style`=a deck NAME, composer never writes the look.
journey-composer SKILL fixed (no reflection/interior over-description; STYLE section). skyfog +
antenna_ball rewritten (Sonnet) to the fixed skill. (2) COUNTER bug fixed: format.counter was read from
cfg not the format block → skyfog's counter:false was ignored (nonsense 10^n overlay). (3) TRACKING is
now THE priority (the point of engine-2 = fix engine-1's illogical zoom). v6 point-track = smooth but
tracks a POSITION not an object (picks center every run; misses the lighthouse). SEMANTIC DETECTION
VALIDATED + committed: engine/detect.locate() (both Florence tasks + large-ft) finds the dark planet /
galaxy / lighthouse that brightness/NCC/point-picker cannot. NEXT SESSION (fable) builds TRACKER v3:
unified two-stage (point-picker emergence → detect.locate object, handoff=first lock, PROPAGATE the lock
through the zoom geometry so flickery boxes never lurch), detect ~every 4th frame NOT every frame
(Florence ~tripled frame time; slow ok, not >1min/frame — the old bug was LOGIC not cadence), steer
toward an edge-locked object before it escapes. TEST BED = night_bloom (rewrite to new schema first).
Keep engine-vs-journey variables SEPARATE (skyfog is a bad journey — useless test bed). (4) POSTER: root
cause of the 3-morning failures found = the DISPLAY sleeps (45min) and Chrome throttled the occluded tabs
(frozen timers/renderer) so 08:00 clicks didn't register; 6pm (display on) worked. Fix = anti-throttle
flags in start_chrome_zen.sh (--disable-backgrounding-occluded-windows / --disable-renderer-backgrounding
/ --disable-background-timer-throttling); also IG dismiss the "Turn on Notifications" nag on the crop
screen + YT confirm the Create dropdown opened before clicking Upload. NOT marked fixed — watching 6pm
tonight + 8am tomorrow (system sleep is Never; task fires on time; it was Chrome throttling, not the
machine). cartographer posted manually (warm). LESSON saved to memory: I ship my first plausible cause
as the diagnosis — hold ≥2 hypotheses, get ground truth, reproduce before claiming.
