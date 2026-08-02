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
- `journeys/*.json` — the ACTIVE engine-2 catalog (Layer 3). Superseded schemas live in
  `journeys/engine1/` (world-card interior/style_suffix) and `journeys/engine0/` (phases —
  won't compile). Resolve names via `pipeline.journey_path()` — never build the path by
  hand. `journeys/VARIATIONS.md` — the differentiation library the Journey Composer (and
  the midnight refill's coordinator) draws from.
- `outbox/journeys.json` — journey REGISTRY: the render queue + pipeline settings
  (budget/backpressure/tier mix/pauses). Stores only DECISIONS (queued/rejected/
  render_failed); everything else derives from pipeline.json + output/ so nothing drifts.
- `scripts/` — night_batch.py (the nightly renderer), journey_refill.py (midnight
  composer), phase_shift.py (intentional openings), zen_browser.py (CDP driver),
  start_chrome_zen.sh, mascot_concepts.py.
- `output/<journey>/vN/` — renders (NEVER overwritten; finals at root, build/ = intermediates).
- `output/mascots/canon/` — the chosen mascot cast (hidden Waldo-style cameos, one per video).
- `review/` + `review_divein/` — phase-shifted cuts still IN REVIEW (zoom-out / dive-in).
- `production/` — chosen-model cuts of videos MARKED READY (queue.json points here).
  `production_alternates/` — the other-model counterpart. Promote via
  `scripts/promote.py <journey> <turbo|ds>` (the standard "approve" step).
- `outbox/pipeline.json` — SINGLE SOURCE OF TRUTH (every video's model/cut/caption/state/
  platforms). `outbox/telemetry.jsonl` — event log. `scripts/pipeline.py` — shared lib.
  (outbox/queue.json is legacy, superseded by pipeline.json.)
- `dashboard/app.py` — Streamlit ops dashboard (Video Review/Music/Production/Journeys/
  Live/Failed/Telemetry/Settings). Run via Windows streamlit → localhost:8501
  (scripts/start_dashboard.sh). NOTE it runs on WINDOWS python: no engine/ imports there,
  utf-8 on every spec read.
- `scripts/poster.py` — the posting harness (CDP + local VLM checks). `scripts/SCHEDULER.md`
  — the four Task Scheduler jobs (refill 00:00 · render 01:30 · posts 08:00/18:00, no Claude
  except inside journey_refill's one headless call).
- DAILY LOOP (closed 2026-08-01): 00:00 refill tops the journey queue (headless Fable
  coordinator → Opus composers → audit → auto-queue) → 01:30 night_batch renders a tier
  template (L+M+S / 2L+M / 2L+S) worth ≤4h, captions, drops in Video Review → Phil approves
  in the dashboard (review→music→queued) → posts at 08:00/18:00 → live. Backpressure: the
  batch skips once max_ready_videos (20) are approved-and-waiting; then the queue stops
  draining and the refill stops too.
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

## ENGINE-2 IS SETTLED (2026-07-31 evening) — read PLAN.md "ENGINE-2 SETTLED" before changing any of this
Phil's verdicts, now implemented: depth ControlNet **stays 0.45** (his A/B call — it keeps the
dive coherent on ONE object; don't re-litigate); composition eases to a **frozen rule-of-thirds
anchor, never center** (measured holding ~0.22 off-center vs v10's 0.05 slide); **uniform bars
per scale**; morph = engine-1 intensity with SEAMS GETTING MORE FRAMES not more force, plus a
2-frame anacrusis into every downbeat; seam cards **keep zooming**; `render_start` rotates the
circular chain so frame 0 lands in an ABSTRACT realm; **"fills the view" banned** in scenes;
DreamShaper is the house default (we never left it — "Model SDXL" in the ComfyUI log is the
architecture, and 17 legacy styleless journeys would silently have gone turbo, now fixed).

## THE NIGHTLY PIPELINE (built 2026-08-01) — journeys flow themselves now
`scripts/night_batch.py` (01:30 task; `render_batch.sh` is a thin wrapper for manual runs)
auto-picks from the journey queue in `outbox/journeys.json`: first satisfiable tier template
(LMS → LLM → LLS, editable) within render_budget_min, per journey dive → queue_review →
caption with REAL exit-code checks (a dead render marks the journey render_failed and moves
on; queue_review before caption because it CREATES the entry captions write into). Skips
the night on backpressure (≥ max_ready_videos ready to post) or render_paused.
`scripts/journey_refill.py` (00:00 task) tops the queue toward journey_queue_target
(≤ refill_max_per_night/run): tiers are assigned BY THE SCRIPT from tier_share deficits
(alternates 2L2M1S / 2L1M2S), then ONE headless claude call — coordinator on Fable reads
VARIATIONS.md + the catalog (extends VARIATIONS.md if mined out), writes briefs to
outbox/refill_briefs_<date>.md, spawns parallel Opus composers running the journey-composer
skill — and the SCRIPT audits (audit_starts + real compile) and auto-queues only passers.
Estimates: frames = 28×cards; render sec ≈ 17.9×frames − 606 (fit on 6 renders, ≤2.5% err).
Manage everything from the dashboard's 🗺 Journeys tab (queue/reorder/reject, tonight's
picks preview) and ⚙ Settings tab (all knobs incl. platform pauses). Times: SCHEDULER.md.

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
2026-07-31 (later): TRACKER v3 BUILT (see PLAN "TRACKER v3 — BUILT"). Root cause of v6's
position-not-object tracking found: it propagated its track with the UNCLAMPED aim while
zoom_transform's crop clamp (±2.2%/frame at z=1.045) bounded the real motion — pure divergence.
engine/track.py = exact propagation (selftest ≤1px, incl. rotation + clamp) + two-stage Tracker
(point emergence → detect.locate lock; near-heading hits correct gently, redirects need 2 agreeing
observations, degenerate >0.8 boxes dropped, escape → re-pick). dive.py: tracker owns approach aim,
always-on build/track.jsonl debug log, --plain A/B flag, cameo propagation fixed to the same exact
math. scripts/track_lab.py: selftest/bench/sweep/overlay. Gates calibrated from sweeps on
night_bloom v4 frames (misses normal; garbage rarely agrees twice; FP locks land on salient objects
= benign in a generative loop). night_bloom.json rewritten to the new schema (8 bars, liquid_light,
1 seam) as the test bed; ~20s/frame with cadence-4 large-ft + depth-CN. Full render night_bloom/v6
+ overlay for review vs engine-1 v4. NEXT: Phil reviews v6 (logical zoom? pretty?); --plain A/B for
the depth-CN look; fold seam into dive.py; update dive-video SKILL when approved.
2026-07-31 (evening): HARD-CUT + PACING + MUSIC fixes (PLAN "SEAM-MORPH + PACING + MUSIC-GRID
FIXES"). Phil flagged 3 consecutive frames = 3 unrelated worlds: the seam card ran at 0.72 base
+ 0.18 arrival boost = 0.85 denoise for 14 frames (near-txt2img each frame). Fixed: seam cards
travel at 0.40; the on-beat seam morph now lives at the NEXT card's arrival (grammar returns
seam_arrivals; dive ramps denoise 0.70 peak ON the downbeat → 0.40 across the prompt crossfade).
Zoom floor 1.028 (fmt.zoom_floor) kills the long-card stall. Music side (checked per Phil):
schedule_morphs was still sec-based → phantom grid for dur journeys (now uses grammar._frames);
bpm_for median-bar broke on mixed durs (now bar = format grid: 103bpm/2.33s). night_bloom v6 =
old-seam "before"; v7 with fixes = "after". antenna_ball's review cut has the same seam defect.
2026-07-31 (night): v7 VERDICT — SEAM FIXED (frames 41-44 one continuous world vs v6's three
hard-cut rolls; the forest dissolves coherently into the galaxy over the morph window — gradual
+ gorgeous; if Phil wants it snappier, raise fmt.seam_denoise 0.70→~0.78). First GENUINE
semantic lock in production (f207: the firefly, object-shaped box, gates refused all 8 garbage
candidates, zero bad redirects — the v6 corner-sliver lock class is dead). Phil approved the
v6 object-zoom logic ("looks really good... more logical"). CENTER-SNAP fix committed AFTER v7
launched (approach_lock_ease 0.3→0.05 = near-fixed-point zoom; ease formula at 0 makes the
object the zoom's fixed point — grows in place, no viewpoint shift): v7 still snaps; NEXT
render shows the natural aim. CATALOG: 21 new-schema journeys now — batch 1 (10× 8-bar
standards, distinct palette/math/space/seam identities) + batch 2 (5 shorts 16 beats ~9.3s
realm-local micro loops; 5 mediums 24-28 beats ~14-16s with non-cosmic "space": chalk realm,
glowworm ceiling, CRT-static Ising, sea-foam, bubble-chamber). PACING+MORPH DOCTRINE SETTLED
(Phil, evening): (a) UNIFORM BARS PER SCALE — every card in a journey has the SAME dur (4, or 8
journey-wide), never mixed; mixed durs made engine-1's arrive-look-plunge curve vary in period
card-to-card = the "uneven within each scale" feel. Curve itself is engine-1's, unchanged (the
interim zoom_floor experiment is retired); length tiers now come from CARD COUNT (5 cards ~12s,
7 ~16s, 11 ~26s). All 22 journeys retimed to dur 4 — bonus: the music grid is now perfectly
regular (every morph interval 2.333s @103bpm) so alignment locks far cleaner. (b) MORPH =
engine-1 INTENSITY EVERYWHERE (0.58); a SEAM differs only by MORE FRAMES (seam_morph_frames 12
vs the normal 6-frame crossfade), never a harder per-frame change ("more frames rather than a
bigger change within a frame looks better"). fmt.seam_denoise retired. (c) ANACRUSIS ON EVERY
MORPH: the last ~sixteenth (2 frames @7fpb) before each boundary rises toward the boost so the
old world shimmers on the pickup and the flip peaks ON the downbeat — mirrors the music's
pickup-into-strong-beat. (d) TARGET = PLAIN OBJECT (see skill): never location/context, never
another object's name — the plunge prompt repeats it every frame so named context steals the
dive (night_bloom's "flower in the lantern light" chased lanterns). 126 targets rewritten.
(e) COUNTER back ON (17 journeys): skyfog's nonsense counter was a flag-read BUG, not a wrap
problem — the engine's odometer pins to the register and spins at handoffs, honest across
seams; the fix had been over-generalized into "false unless monotonic" and darkened the whole
catalog. false only where a realm is fictional (chalkboard/orrery/cave/static_bloom).
(f) SEAM CARDS NEVER STOP ZOOMING — grammar gave them x1.4 total vs x10 (1.006-1.019/frame);
the uniform-bar retime stretched that over 28 frames = a 2.3s STALL right before the biggest
morph (Phil spotted it in v9 frames). "Don't target during a seam" was right; "don't zoom"
never was. Now x10 like every card. (g) MODEL: we never switched off DreamShaper (all engine-2
renders loaded dreamshaperXL; every deck entry recommends ds) — the confusion was the run dir
losing its _ds suffix once the deck picks the model. But 17 LEGACY journeys have no `style`,
so the deck recommended nothing and cfg kept DEFAULTS' TURBO ckpt: a silent turbo render for
any legacy re-render without --model. Fallback is now "ds" routed through MODEL_PRESETS (gets
dpmpp_sde/karras too); startup logs "MODEL ds (...)" and each run writes run.json.
V10 = THE REFERENCE RENDER (2026-07-31, output/night_bloom/v10, 308f/11 bars/25.7s): seam now
a genuine structural morph (forest's branching gold filaments PERSIST across the jump and
resolve into the cosmic web + galaxies — the best morph the engine has made, and it only reads
that way because the camera keeps diving into it); normal morphs land ON the beat with the
pickup frame visibly leading; loop closure near-perfect (f307 ~= f0); counter on screen (613
frames, 41 decade pulses); tracker 44 misses / 6 refused candidates / 2 lock-redirects / 1
lock, zero lurches; fixed-point aim CONFIRMED (tracked point sits mean 0.100 / max 0.334 off
center and STAYS there — aim-vs-track mean 0.086, i.e. the object grows in place instead of
snapping to center). Composer SKILL: length tiers +
simile ban + diffuse-linger ban + cameo-window note; VARIATIONS.md: math-pattern/space-
personality/palette-family/micro-realm/non-cosmic-seam libraries. Engine: cameo init-once
window (card-0 cameos used to silently never paste — dollhouse's is missing), grammar._frames
floors at one beat (dur-1 cards no longer break the grid). Review queue: antenna_ball+skyfog →
new "rejected" state; stormglass alone in review. NEXT: Phil reviews v7 + the seam snappiness
knob; render the new catalog (shorts are cheap: 112f ≈ 35min); dive-video SKILL update once
engine-2 is approved; fold repair_seam into dive.py's tail (still open).
2026-07-31 (late night): BATCH RUN + FOUR REAL BUGS. Ran scripts/render_batch.sh. Only
butterfly_meridian survived; the other two died on "workflow did not finish in 300s".
(1) VRAM STARVATION (root cause of both deaths): the batch captions BETWEEN renders, and
caption.py's Ollama call left mistral-small3.2:24b resident holding 7.59 GB on a 10 GB card.
The next render's SDXL+ControlNet+CLIP+DepthAnything+Florence then didn't fit, ComfyUI switched
to per-step CPU<->GPU weight swapping (1.5 s/it -> 33 s/it) and the job finished at 310s with
nobody listening. Fix: caption.py passes keep_alive=0 (VRAM 9893 -> 1228 MiB); dive.run_workflow
timeout 300 -> 900s, detect._wait 180 -> 300s. NOTE pl.gpu_busy() reads UTILIZATION, not memory,
so an idle-but-resident model doesn't register — the batch happily started the next render.
(2) LONE FIGURE (Phil: "I don't wanna have lone figures showing up in these"). quantum_orrery
rendered a haloed goddess for the whole video. Frame 0 is the ONLY txt2img frame, so the
checkpoint's prior owns it and the feedback chain then locks it in — one bad frame = one wasted
hour. Its frame-0 prompt was "quark cores bound inside one luminous shell ... a crimson halo
around the trio ... warm gilded light ... storybook grandeur ... jewel-bright accents": nothing
is a person and every word is character-art bait. Fixes: engine/figure.py frame-0 gate (re-roll
seed 4x, then ABORT with a prompt-level diagnosis; --allow-figures overrides; warns every 28th
frame); widened the global negative (it was all CLOSE-UP terms, useless vs a full-body figure);
dropped "storybook grandeur" from gilded_relic; rewrote the hadron card. DOCTRINE (Phil): do NOT
require concrete objects on render_start — that drags brass/glass into cosmic realms. Instead,
name-only physics (quark/hadron/boson/field) are WORDS WITH NO IMAGE: the composer must write
the PICTURE at compose time. Also: figures intrude by VOCABULARY (halo/crown/robe/regalia +
gilded/jewel/grandeur), not just by setting — "empty, no one present" was on every interior card
and the goddess appeared on the abstract PARTICLE card.
(3) THE FIRST FIGURE DETECTOR WAS WRONG — validate before trusting. detect.locate("person") +
an area threshold flagged 3 of 5 KNOWN-CLEAN frame-0s (43-78% of frame) and the real goddess
(84%) was indistinguishable by size; it would have aborted almost every render. Cause: grounding
and referring-expression segmentation are "point at X" tasks — ask for something absent and
Florence returns a near-full-width blob (FULLSPAN drops only >=0.9 in BOTH dims; these were 1.00
x 0.72-0.89, mask area == bbox area = solid rectangles). Presence needs a "describe what's here"
task: detect.caption() (more_detailed_caption, text out via PreviewAny since ComfyUI only
surfaces OUTPUT nodes) separated the same 6 frames PERFECTLY — goddess "A woman with long red
hair is standing ... a golden crown", vs "a glass vase", "an abstract image", "many shiny balls",
"a forest", "lights hanging from the ceiling". 1 TP / 5 clean / 0 FP. Word list deliberately
tight (no "knight" — chess PIECES; no bare "figure"; no "face"; word boundaries so "man" can't
fire on "many"). Audit: scripts/check_figures.py.
(4) CAPTION ORDER WAS BACKWARDS. queue_review.py CREATES the pipeline.json entry; caption.py
silently discards everything when there's no entry (`if v:`) while still printing "5 caption+
title pairs". So the batch's caption-then-queue order left butterfly_meridian and lather_atlas
in Review with NO caption despite clean-looking logs. render_batch.sh + dive-video SKILL now
queue FIRST; caption.py says "GENERATED BUT DISCARDED" instead of faking success.
STYLE DECK: 7 new colourful/trendy entries (neon_drift, candy_gloss, ultraviolet, aurora_silk,
infrared_bloom, lacquer_pop, reef_pop) = 13 total; catalog spread from 8/5/4/3/2/2 to max 3 each
(a ONE-OFF spread at Phil's request, NOT a permanent cap). Colours named as COLOURS ("hot pink"
not "coral") so they can't paint literal objects. DASHBOARD: fixed a UnicodeDecodeError that
blanked the bottom of every tab — Windows streamlit read UTF-8 journey specs as cp1252, mojibaked
the em-dashes, wrote them back, then choked on byte 0x9d; the crash on queued video #5 hid #6
(frost_window) while the header metric still counted it. Also normalized 7 Windows-backslash
paths in pipeline.json (poster.py runs under WSL).
STATE: butterfly_meridian + lather_atlas in REVIEW (captioned). quantum_orrery NOT rendered —
re-render it to exercise the figure gate. render_batch.sh is fixed but UNRUN since the fixes.
2026-08-01: RENDER_START DOCTRINE CORRECTED (twice) + batch 2 in review. Batch 2 rendered clean
after the VRAM fix: quantum_orrery (196f), loom_of_nights (308f), jade_automata (280f),
pollen_court (140f) — all 4 captioned and in Video Review alongside butterfly_meridian,
lather_atlas, stormglass (7 total). The figure gate passed frame 0 first try on quantum_orrery
(no goddess, no seed re-rolls) after the hadron rewrite + deck fix.
PHIL'S REVIEW: the one real complaint was the STARTING FRAME. Starts that worked (butterfly's
nebula, jade's filament starburst) were easy for the loop to return to; starts that failed
(pollen's single grain, orrery's metal-object-on-a-table, loom's knot of cord) blend home badly
at the end of the video. TWO WRONG RULES, both mine, both now dead: (a) "start in an ABSTRACT
realm" — abstract and wide are INDEPENDENT axes; "a single pollen grain" is abstract AND an
extreme macro. (b) "start on the largest exp" — Phil: "the size of objects doesn't correspond to
wideness of shot... a close-up of a neutron star is a very large object, high exp, but it's a
close-up, whereas a wide shot of a meadow is a much smaller scale object." Cards ALTERNATE
between wide and target shots at every scale, so exp can never select framing. Never re-derive
either rule.
THE RULE (settled, in the composer SKILL): frame 0 must be EASY TO MORPH INTO, because it is both
the only txt2img frame and the LOOP-HOME target. Qualifies: many things across a field of view,
OR a single SOFT-EDGED diffuse form — astronomical subjects qualify ALONE (no hard silhouette, so
the returning dive can land anywhere on one). Fails: a hard-edged recognizable object as the
subject. Preference: outer space > subatomic (describe as diffuse light/depth, never by naming
particles — a thinly-described subatomic card is what let DreamShaper substitute a metal object)
> a recognizable everyday place. Seam must not rotate to first or last: with seam at index s of
n, i must be neither s nor s+1. All 24 new-schema journeys now have a start; verify with
`python3 scripts/audit_starts.py` (hard-fails a lone subject only OUTSIDE space) or
`scripts/preflight.py <journey>` (one journey: frames, bars, counter, seam, frame-0 bait scan).
SKILL-WRITING LESSON (Phil): do NOT put worked examples in the skills — "the more examples you
have of what to do... they just get copied throughout, the samier our videos are gonna be." State
rules as tests to apply, not models to imitate. The render_start and figure sections were rewritten
this way; keep it that way.
STILL OPEN: pollen_court/frost_window/velvet_atlas/copper_rain/static_bloom are closed terrestrial
journeys with NO space or subatomic card — they start on their widest establishing shot; giving
them a cosmic card is journey authoring, not a start pick. night_bloom + remix keep moss_cells
(approved/queued; `nebula` recorded in-journey as the better start on any re-render). None of
these 24 starts has been RENDERED yet except the 4 above — the doctrine is untested at scale.
Also still open from before: fold repair_seam into dive.py's tail; TikTok paused.
2026-08-01 (afternoon): JOURNEYS ENTERED THE PIPELINE (see "THE NIGHTLY PIPELINE" above).
Catalog split: 17 engine-1 → journeys/engine1/, 9 engine-0 → journeys/engine0/; active
engine-2 stays flat; every resolver now goes through pipeline.journey_path() (caption,
music_gen, score, phase_shift, repair_seam, queue_review, flip_journeys, preflight —
preflight also ROOT-anchored — and dashboard _spec_path). outbox/journeys.json = journey
registry (decisions only: queued/rejected/render_failed + settings; everything else
derived). pipeline.py grew journey_path/journey_names, jload/jsave/jqueue/jmove/jstate,
tier_of (S≤5 cards, M 6–8, L≥9), journey_frames (real compile), est_render_sec
(17.9×f−606+42, ≤2.5% err vs the 6 measured renders), pick_tonight (tier templates),
refill_tiers (deficit-vs-share; alternates 2L2M1S/2L1M2S exactly), + "music" added to
STATES. night_batch.py + journey_refill.py + scheduled_render.bat/scheduled_refill.bat
REGISTERED in Task Scheduler (00:00/01:30, verified Ready; wsl bash -lc env resolves
claude + python3). Dashboard: 🗺 Journeys tab (queue/reorder/unqueue/reject/re-queue-
with-force, render-failed + rejected + legacy sections, audit badges, tonight-preview
using the same pick_tonight) and ⚙ Settings tab (all journeys.json knobs + platform
pauses). Dashboard computes frames spec-side (matches real compile 24/24) — no engine
imports on Windows python. promote.switch made crash-consistent (files move BEFORE the
pipeline pointer updates; refuses a variant with no file — the jade_automata scare was
almost certainly a hot-reload race from live app.py edits, its entry was untouched).
FIRST NIGHT IS A WATCH NIGHT: queue is seeded EMPTY — Phil queues from the tab (or lets
the 00:00 refill compose 5); check outbox/refill.log + night_batch log + Video Review
in the morning per the validate-in-real-runtime-conditions lesson.
2026-08-01 (later): REVIEW VERDICTS + LEVEL-1 PARTIAL RE-RENDER + A NASTY RACE KILLED.
Dashboard: Journeys tab moved first; Video Review cards grew three reject verdicts (Reject →
front/back of render queue = video rejected + journey re-queued force; Reject journey = both
dead) with a 🎲 new-seed checkbox (default on; uncheck = same seed through an engine change)
and an ↻ from-card box. dive.py --seed (base override) and --from-card K [--src-version]:
repair_seam's pattern generalized — copy cards 0..K-1's frames into a FRESH vN, restart the
feedback chain at the card boundary (anchor rotation counted from the approach schedule,
prefix cameos marked done, loop-tail + mid-cameo-window boundaries refused), regenerate on.
CARD = REGISTER, not a compiled phase (grammar splits registers ~3 phases — first cut indexed
phases, wrong boundaries). run.json now records card_frames + from_card/prefix_src. VALIDATED
on loom_of_nights v2: 280 prefix frames byte-identical to v1, 28 regenerated (seed 777),
full assembly clean, 7 min total. night_batch honors entry.from_card/new_seed.
THE RACE (Phil caught it live): music_gen/caption/poster all held a pipeline.json snapshot
across minutes of slow work and saved it whole at the end — a video rejected during a music
gen silently reverted to review. All three now RE-READ fresh before writing and merge only
their own fields. LESSON: any writer that sleeps between load and save clobbers concurrent
edits; pipeline.json has no locking — merge-into-fresh is the contract.
PLANNED NEXT (Phil's order): Level 3 = IP-Adapter seam (ipadapter_plus + SDXL vit-h models
ALREADY INSTALLED in ComfyUI; prototype in seam_lab on the dollhouse/snowfall hard cases,
ramp weight into the tail, then fold into dive.py) → then Level 2 (cut cards + stitch)
becomes nearly trivial. The current review videos' bad FIRST frames need full re-renders
(the reject verdicts handle that), not from-card.
2026-08-01 (session close): BATCH TRIGGERED LIVE via `schtasks /Run PowersOfZen-render` at
15:19 — the real scheduled chain (.bat → wsl → night_batch) picked LMS: glass_apiary +
quantum_orrery(re-render, fresh seed, figure-gate exercise) + copper_rain, ~2.6h. Watch
outbox/night_batch.log; results land captioned in Video Review. The 01:30 task tonight
picks the NEXT template from the remaining ~10-deep queue; midnight refill will top it up
(queue 13/20 → composes 5). NEXT SESSION: Level 3 = IP-Adapter seam in seam_lab (models
installed; hard cases dollhouse/snowfall), then Level 2 splice — see PLANNED NEXT above.
2026-08-02: OPENING-SHOT DIAGNOSIS (no fixes applied — Phil wants discussion first) + IPA SEAM
VALIDATED. All 5 new renders (glass_apiary, quantum_orrery re-render, copper_rain, sugar_nebula,
velvet_atlas) opened on CLOSE-UPS despite the render_start doctrine. Root causes, CONFIRMED by
seed-held frame-0 ablation probes (scratchpad probe/, strips sent to Phil):
(1) ENGINE: card 0 skips its arrival phase, so frame 0 — the only txt2img frame — renders the
T_TRAVEL prompt "moving through {scene}, {TARGET}, {style}": the card's plain-object target is
IN the txt2img prompt, and SDXL composes a product shot around the most concrete noun (removing
just the target flipped quantum_orrery from crystal-on-a-table to a wide starfield vista).
(2) STYLE: the deck's gloss vocabulary + brand tail (specular highlights/jewel-bright/candy
gloss) is macro-product-shot prior; sugar_nebula stayed macro even without the target, went
wide-ish with explicit wide language, fully wide only without the gloss words. The "twins"
(glass_apiary/sugar_nebula colorful-balls openings) = both candy_gloss + both SPHERE targets +
both nebula scenes — same checkpoint attractor, journeys not actually similar.
(3) Nothing anywhere says WIDE: scene bans frame language, so the 9:16 portrait canvas prior
(product shots/portraits) wins by default. Also: 3 of the 5 (copper_rain, velvet_atlas, and
aborted static_bloom) were on the KNOWN closed-terrestrial no-qualifying-start list — the
doctrine never covered them. static_bloom's figure abort: "behind a fine black MASK" — a
WEARABLE summons a wearer (all 4 seeds: "a woman wearing a green and black mask"); ablation
confirmed the same class on velvet_atlas (target removed → a woman IN the coat, despite "empty,
no one present" + full negative). Candidate fixes FOR DISCUSSION: engine-side frame-0 ESTABLISH
template (wide language, no target — probe C validated), frame-0-only close-up negatives,
wearables added to the composer bait list, authored wide cards for the closed-terrestrial five.
IPA SEAM (Level 3) VALIDATED in the lab: seam_lab.add_ipadapter (ipadapter_plus, PLUS preset,
plus_sdxl_vit-h + CLIP-ViT-H) + NEW scripts/seam_tail_ab.py — regenerates a render's REAL loop
tail per method (orig/blendcn/ipa/ipacn), non-destructive, output/seam_lab/<name>/ with labeled
side-by-side seam_AB.mp4. Ran dollhouse_ds + snowfall_turbo (the blendcn-reverted hard cases,
gaps 64/73) + copper_rain (live engine-2). VERDICT from stills: ipacn (IPA weight 0.95·t^1.5 +
depth-CN 0.2→0.8 over the last 12 + FIXED small blend ≤0.35 last 6, palette ramp, full zoom
throughout) lands compositionally ON frame 0 in all three (dollhouse: same purple corner house/
street curve; snowfall: spire in place; copper_rain: the exact staircase) with every frame alive
— while blendcn hit the 0.82 fading-photo morph on all three (the regime Phil reverted in July).
ipa alone = right world, wrong framing (one zoom-level off) — IPA carries the world home, CN
aligns the landing. ~14-17s/frame, IPA adds ~nothing after the first-frame CLIP encode. Phil is
judging the seam_AB clips in MOTION. NEXT (pending Phil): fold ipacn into dive.py's exact_loop
tail (--classic-tail for A/B); Level 2 splice = the same bridge primitive aimed at ANY target
frame — whole-CARD cuts keep the music grid (28f = 1 bar), and a bad opening card could be cut
with the tail homing onto card 1 instead.
2026-08-02 (afternoon): PHIL'S VERDICTS IMPLEMENTED. Opening fixes a+b+d are IN: (a) frame 0 now
renders grammar.T_ESTABLISH ("a vast wide panoramic view of {scene}, seen from far away" — scene
only, NO target; grammar.establish_prompt() standalone so no tuple churn) — the schedule's travel
prompt with its target is used from frame 1 on; (b) FRAME0_NEG_EXTRA anti-close-up negatives
(close-up/macro/product shot/tabletop/still life/shallow DoF/bokeh) on the txt2img call + the
figure-gate re-rolls only; (d) composer SKILL gained the WEARABLE-summons-a-wearer rule (mask/
veil/cloak/hood/gown/coat/crown... rename by physical function or make emptiness structural);
static_bloom's "fine black mask" -> "set in a fine black grille", preflight-pass, left
render_failed for Phil to re-queue from the Journeys tab. IPA TAIL FOLDED INTO dive.py (Phil:
"head and shoulders above the rest... every video should have it"): build_workflow grew
ipa_image/ipa_weight/neg_extra (IPAdapterUnifiedLoader PLUS preset -> IPAdapterAdvanced patches
the sampler model); the exact-loop tail now runs the ipacn schedule (IPA 0.95*t^1.5 ease-in-out,
depth-CN from frame 0 ramping 0.2->0.8 over morph_frames, fixed <=0.35 blend last 6, palette pull
unchanged; frame-0 upload cached in loop["_home_ref"]); the old gap-scaled 0.82 morph lives
behind --classic-tail. VALIDATED: copper_rain --from-card 4 -> v3 (throwaway, 541s) landed on
frame 0's staircase; NOTE v3 is now copper_rain's newest complete vN (queue_review without --src
would pick it; review deliberately points at v2). COPPER_RAIN v2 = the EXACT lab ipacn tail
spliced onto v1's body (no GPU), assembled with counter, re-queued to Video Review with captions
kept — Phil judges the full-video seam there; run.json records the splice. REPLACE_OPENING built,
NOT run (Phil's hold): scripts/replace_opening.py regenerates the old-tail + old-card-0 slots as
ONE continuous L+C0 (~52-frame) homing arc — resume feedback at the last kept frame, keep the
scheduled zoom, prompt-crossfade last-card T_FINAL -> card-1 T_MORPH, IPA/CN/blend home onto the
FIRST KEPT FRAME (card 1's start = the new loop point), counter re-derived only on the arc (spin
from last kept exp to first kept exp), every kept frame byte-identical, bar grid untouched;
refuses cameos sitting in the regenerated slots; --dry-run/--queue-review. Dry-runs verified on
pollen_court (drop 'park', home onto bench_slat), loom_of_nights (drop 'galaxy'), quantum_orrery
(drop 'hadron'). Tonight's batch renders with establish-frame-0 + IPA tail automatically — the
first doctrine-complete renders land in Video Review tomorrow morning.
