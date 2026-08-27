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
  start_chrome_zen.sh, mascot_concepts.py. REPAIR family (2026-08-02, see the
  **video-repair** skill for the decision tree): replace_opening.py (bad opening card),
  replace_tail.py (bad loop seam), make_candidate.py (preview/--install a repair for a
  video already in production — measured rotation + its own audio), seam_tail_ab.py
  (mechanism A/B lab).
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
  coordinator → Opus composers → audit → auto-queue; tier per brief = Monte Carlo draw
  weighted by tier_share) → 01:30 night_batch renders the queue head IN ORDER, as many
  as fit render_budget_min, captions, drops in Video Review → Phil approves
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
auto-picks from the journey queue in `outbox/journeys.json`: QUEUE ORDER, as many as fit
render_budget_min (tier templates RETIRED 2026-08-26 — they overrode Phil's queue order;
a too-big journey is skipped for the next, the first pick always lands), per journey
dive → queue_review → caption with REAL exit-code checks (a dead render marks the journey
render_failed and moves on; queue_review before caption because it CREATES the entry
captions write into). Skips the night on backpressure (≥ max_ready_videos ready to post)
or render_paused.
`scripts/journey_refill.py` (00:00 task) tops the queue toward journey_queue_target
(≤ refill_max_per_night/run): tiers are assigned BY THE SCRIPT — a Monte Carlo draw
weighted by tier_share (the queue converges to the target mix with no predictable
rotation; since the batch drains in order, queued mix = rendered mix), then ONE headless
claude call — coordinator on Fable reads
VARIATIONS.md + the catalog (extends VARIATIONS.md if mined out), writes briefs to
outbox/refill_briefs_<date>.md, spawns parallel Opus composers running the journey-composer
skill — and the SCRIPT audits (audit_starts + real compile) and auto-queues only passers.
Estimates: frames = 28×cards; render sec ≈ 17.9×frames − 606 (fit on 6 renders, ≤2.5% err).
Manage everything from the dashboard's 🗺 Journeys tab (queue/reorder/reject, tonight's
picks preview) and ⚙ Settings tab (all knobs incl. platform pauses). Times: SCHEDULER.md.

## Current state (update this line as it changes)
2026-08-27 (CAMERA DAY — Phase C micro A/B rendered + ENGINE 3 PHASE D BUILT + first
camera labs; NOTHING queued — Phil judges tonight): (1) MICRO A/B ready:
output/dolly_lab/squid_micro_dolly_AB_loop.mp4 + _SEQ.mp4 (squid_lantern 4 cards, seed
1234, fresh base v12 vs micro v13; micro verified acting — hover drift to ±8.7px,
plunge surge k→1.5, downbeats at zero offset). (2) PHASE D BUILT (commits a348429 +
77ef13f; doctrine journeys/CINEMA.md): engine/camera.py compiles per-card `camera`
fields → per-frame schedule (beat-quantized envelope, rates zero at card boundaries →
loop closes structurally; exclusions enforced in schedule() itself: render-start/lap
card, seams, depth moves on cameo cards); warp.camera_residual fuses
parallax+micro+orbit+dolly+tilt into ONE remap; roll rides the exact propagation
(track.step per-frame rot); spiral pivots on the tracked object when locked (in all
lab runs it fell back to median/center — the tracker rarely locks inside move windows,
open v2 item: pivot on the committed emergence point). BYTE-IDENTITY PROVEN: no-camera
path unchanged (fresh v12 vs pre-Phase-D v9: frames 0-71 byte-equal, first diff at the
frame-72 tail boundary where tail code legitimately evolved). scripts/cinematographer.py
= rule-based v1 (spice-not-sauce floor), deliberately NOT wired into the nightly.
(3) CAMERA LAB round 4 = the deliverable: output/camera_lab/
cherenkov_cistern_camera_AB_loop.mp4 + _SEQ.mp4 (storm_world spiral 0.4 +
mountain_country orbit 0.35; arms byte-identical to the frame-40 move onset; both
moves stay on-world). THREE LAB LESSONS (PLAN "Phase D lab log"): scaffold seeds are
now JOURNEY-keyed (renamed A/B arms drew different instance fields — latent flaw for
every --plain/--cn A/B too); camera_den_floor 0.48 re-created orbit-v3's REJECTED
content-reinterpretation (steel towers from abyssal's "gas towers" wording) → defaults
0 + orbit shear uses smoothed depth; camera-lab journeys need bait-free wording on/
around move cards (abyssal's card-2 ARRIVAL coin-flipped to literal towers BEFORE the
move acted; output/abyssal_chandelier_cam* kept as the failure record). (4) PIPELINE
CLEAN: hardened poster's first scheduled flight perfect (wild_yeast 11:06 YT+IG,
trusted share path, caption carried natively, no wedge/reheal); queue-order pick's
first night rendered 5 to Review (3M+2S — bamboo_sea, observatory_dusk, bee_cathedral
re-captioned after an Ollama hiccup, fiddler_commons, voltaic_shoal); post_next
2026-08-28 06:00 (11:06+19h). NEXT: Phil's verdicts on micro + camera clips → rate/
move tuning + cinematographer adoption question; spiral pivot v2; then the hero moves
(landing_lab / threshold_lab).
2026-08-26 (LATER — CDP WEDGE HARDENED + TIER TEMPLATES RETIRED): (1) the poster's known
flakiness (IG platform tab's CDP websocket wedges silently → 200s hangs; a fresh process
always cured it) is CLOSED: zen_browser ws timeout 200→30s, Tab.cmd auto-reconnects +
retries ONCE on socket-level failures (never on CDP error replies — those stay
RuntimeError), choosefile got its own wedge retry (its raw recv loop bypasses cmd), and
poster.platform_tab now PINGS every tab before a flow gets it, rebuilding the tab
entirely (close + reopen, telem poster_tab_reheal) if even a fresh socket gets no
answer. Validated live: socket killed under a live IG tab → next eval reconnected and
answered. (2) NIGHTLY MIX (Phil's call — "we have a glut of longs"): nightly_templates
RETIRED everywhere (pipeline defaults, night_batch, dashboard, journeys.json key
removed); pick_tonight = QUEUE ORDER, as many as fit render_budget_min (too-big journey
skipped for the next, first pick always lands); refill_tiers = pure MONTE CARLO draw
weighted by tier_share (currently 0.45L/0.2M/0.35S, editable in Settings) — the queue
converges to the target mix with no predictable rotation, and since the batch drains in
order, queued mix = rendered mix. Dry-run verified: tonight = bee_cathedral +
observatory_dusk + bamboo_sea (M) + fiddler_commons + voltaic_shoal (S) = 5.2h — Phil's
front-of-queue mediums/shorts, no more template-forced longs.
2026-08-26 (THE CAPTION SAGA, RESOLVED — read this before touching poster.py): four IG
posts went out caption-less (caddis 08-24, peony 08-24, termite 08-25, lantern 08-26) —
Phil: "this is ruining my project." FINAL DIAGNOSIS (proven by controlled experiment,
vesper 16:3x: "share click path: trusted" + caption intact natively): a JS-synthesized
.click() on the composer's Share fires a BARE share that drops the registered caption;
the TRUSTED pointer sequence (hover→press→release — what a real user does) carries it.
The JS Share click was MY 08-24 change (made because coordinate clicks hit an overlay
container); every blank post followed it. Phil's plausibility check ("I find it hard to
believe IG is that broken") redirected the diagnosis after I wrongly blamed the platform.
THE POSTER NOW HAS THREE LAYERS: (1) _ig_share_click = trusted-first with reacted-check
+ JS fallback, path logged + telem ig_share_method; (2) _ig_set_caption = trusted
Input.insertText verified by IG's char counter (execCommand text renders but never
registers on the professional UI); (3) CAPTION SELF-HEAL = post detected by reel-code
DIFF (snapshot before posting), live caption checked, repaired via the EDIT dialog if
missing (trusted insertText + TRUSTED-COORDS Done — JS Done closes WITHOUT saving),
telem ig_caption_heal; a post cannot be recorded live without its caption verified on
the live page. ALL FOUR blank reels repaired in place (caddis by Phil, peony DccarGtgKjB
+ termite Dce_d_qOwVA + lantern DcgRKhzODHi by the repair flow) + marked live. KNOWN
FLAKINESS: the IG platform tab's CDP websocket occasionally wedges (200s hang →
"Connection timed out", hit 3× on 08-26; wait_for swallows+retries which can stall
long) — a FRESH process retry has always worked; a shorter ws timeout + reconnect-ping
in platform_tab is the open hardening item. POSTED TODAY: lantern (Post-now 08:58, YT+IG,
caption healed ~15min), vesper (16:00 YT via Post-now, IG 16:3x retry with caption
native; reel DchCOAOhmDn). Next gate window: virtual 2026-08-27 11:00 (no remap needed).
Queue: cobalt, ruby, meteorite, wild_yeast. NEXT FRONTS unchanged: --micro A/B, Phase D
camera vocabulary.
2026-08-24 (EVENING — TRAJECTORY HOMING APPROVED + FLEET-WIDE): Phil's morning catches
led to loop-tail v3: (1) v2 "home one step early" fixed the WRAP but the tail still
DECELERATED into a static target (asymptotic convergence reads as a stop); v3 =
TRAJECTORY HOMING — tail frame j targets original frame lap_cut−L+j (same position one
loop period earlier), inter-frame change stays one zoom step all the way in; final
target lap_cut−1 keeps the continuous wrap. Phil on cobalt: "looks good and smooth" →
re-lapped EVERYTHING: all 8 review videos (wild_yeast v7, lantern v7, cobalt v6,
magnetite v6, vesper/anemone/meteorite/peony v3s) re-ingested; production termite v5 +
ruby v6 installed at marked openings (diff 3.4/6.1) with companions refreshed; caddis
already live (untouched). ALSO: VRAM leak guard = dive POSTs /free before frame 0 (the
12:30 crawl: 8.9GB idle-resident after morning pregen → 55s/frame swap); budget restored
340 + LLLLSS dropped + one-off render task deleted (overnight batch had run 01:30→09:30
on the bumped settings). MORNING: IG post fixed twice more (crop button below the
scrolling dialog's fold; Share click hitting a non-delegating container — JS-first
clicks in _ig_select_original_crop + _ig_click); caddis posted + verified
(reel Dca_2VJRSs1); post_next 2026-08-25 02:00 (termite next, with the new seam).
Tonight's batch renders cherenkov/motmot/bourdon/pomegranate-era queue with the FULL
stack incl. trajectory homing. POSTING DEAD-ZONE REMAP (Phil's exact rule, in post_gate):
virtual window [01:00,03:30) → actually post 21:00 the NIGHT BEFORE; [03:30,07:00) →
09:00; the 19h clock ALWAYS advances from the VIRTUAL time (walk undistorted); never
posts 01-07 even after downtime. TONIGHT: virtual 08-25 02:00 → termite posts 08-24
21:00 (new seam), next virtual 08-25 21:00. NEXT FRONTS: --micro A/B, Phase D camera
vocabulary; Phil may fine-tune depth.
2026-08-23 (NIGHT CLOSE — round 3, Phil's two catches fixed): (1) "INTERMEDIATE IMAGE"
AT THE SEAM (cobalt's red rays) = the lap homed onto card 1's ARRIVAL START — a mid-morph
hybrid by construction. Fix = ARRIVAL RE-PLAY (grammar): the lap continues fa more frames
re-playing card 1's on-beat arrival morph mid-chain; cut/home = first CLEAN post-arrival
frame; delivered still exactly N bars (lap_cut = card0 + fa). All 7 retrofits re-run on
it: review wild_yeast/lantern/cobalt/magnetite v5s re-ingested; production caddis v3 +
termite v4 + ruby v5 rebuilt from Phil's marked rotations (R + lap-shift for zoomout,
R − for divein; openings verified 3-7 diff) + installed with prod's own audio; UNSHIFTED
COMPANIONS refreshed (orig_file targets now the new cuts — future re-marks shift the
right video). (2) MUSIC SEND-BACK BUG (Phil's report): Back-to-Review now reverts v.file
to the unshifted cut (marker time must match what's on screen); queue_review clears
orig_file/start_t on new-render ingest. RUBY ROOT CAUSE PROVEN: orig_file survived
reject→re-render→re-approve pointing at production/ruby_furnace_ds.mp4 dated AUG 17 (the
pre-rejection OLD-ENGINE render, tree archived to E:) — the 11:35 approve shifted THAT.
Both bugs now impossible. NOTE: lantern was approved to Music mid-day (start 8.7s) — the
re-ingest pulled it back to Review with the mark cleared (new safety rule); Phil re-enters
8.7. Orphaned production/lantern_mangrove_ds_shift.mp4 (16:58) is harmless. caddis posts
07:00 with the FINAL corrected seam.
2026-08-23 (EVENING CLOSE): HOMING CURVE v2 shipped after Phil's "still too abrupt" on the
first lap result — smoothstep IPA from a 0.22 floor (half strength by mid-tail; was
0.95·t^1.5 = converged in the last ~8 frames), depth-CN across the WHOLE tail 0.15→0.80,
tail = one full bar (fpb×4, ≈ the whole lap card). Knobs: home_ipa_floor/peak/shape,
home_cn_floor/peak. ALL 7 RETROFITS RE-RUN ON v2 + DONE: review wild_yeast/lantern/
cobalt/magnetite re-ingested (captions kept, music candidates still valid — bar grid
unchanged); production caddis+termite installed via make_candidate (now lap-aware:
from_card provenance + cut-direction lap shift — divein R−shift, zoomout R+shift, both
empirically verified; backups in _seam_backup/, chosen-music copies updated). RUBY
ANOMALY: its production video matched NO local render (flat rotation residual ~34;
caddis/termite/whale_fall all clean — one-file mystery, possibly a stale/archived source
in the 11:35 approve flow) — production REBUILT deterministically from v4 @ Phil's marked
3.15s + prod's own audio, old file in _seam_backup/. 3-way seam clip (no-lap / lap-v1 /
lap-v2) sent to Phil — his verdict on curve v2's strength pending; knobs are one-line if
he wants more. Tonight's 01:30 batch inherits lap + curve v2 + gain 1.0 + spaceless
establish. caddis posts 07:00 (IG only, YT live) WITH the new seam.
2026-08-23 (SEAM DAY — loop lap + scale-aware establish SHIPPED; gain 1.0 the rule): Phil's
morning verdicts: (1) parallax gain 1.0 EVERYWHERE going forward (more freedom/diversity in
card shifts + deeper world; DEFAULTS parallax_gain=1.0, random-gain exploration retired
after one night, its six renders keep drawn gains in engine_params; queued videos NOT
redone). (2) SEAMS diagnosed + fixed — see PLAN "SEAMS — DIAGNOSED AND FIXED": machinery
was fine, the loop HOME (txt2img frame 0 postcard) was the disease; LOOP LAP (Phil's
extra-card idea, default ON, --classic-loop A/B) + T_ESTABLISH_SPACE (exp ≥6.5/≤−6 +
landscape negs; threshold set by pastiche). Validated wild_yeast v3; retrofits via
--from-card N-1 (~15min each, --parallax matches source gain; pre-parallax sources get 0)
ran for lantern/cobalt/magnetite (auto re-ingested to review) + caddis/termite/ruby
(production — install decision via make_candidate pending). POSTING: the professional-
account conversion broke IG (new Create menu Post/Live/Ad — poster fixed + validated
live; whale_fall re-posted IG DcY5PRHxbtQ; caddis IG queued first for 08-24 07:00 window,
YT skip automatic). NOTE for tonight's batch: renders inherit lap + gain 1.0 + spaceless
establish automatically; budget still 430/LLLLSS (restore when backlog drains); delete
PowersOfZen-render-once task. NEXT: Phil judges retrofitted seams + lap-era renders;
then --micro A/B; then Phase D camera vocabulary.
2026-08-22 (PM — DEPTH 2.0 "PARALLAX ERA" BUILT + LAB-PASSED; read PLAN.md "DEPTH 2.0"):
Phil approved the motion-parallax plan (the settled diagnosis: uniform crop-zoom IS the
flat look — it deletes motion parallax, the dominant depth cue; pictorial fixes were
fighting that headwind, and the cues we could add collide with his sharp/saturated taste
— motion depth needs none of them). BUILT (commit ffd02e7): warp.parallax_residual (extra
scale z^(gain·(depth−med)) about the zoom's fixed point; median plane rides the schedule
exactly — tracker/cameo/counter untouched; --parallax 0 byte-identical to today, nightly
unaffected); depth = resolve scaffold in windows / DepthAnything cadence+EMA+planes
elsewhere; disocclusion denoise; loop-tail taper. Phase B --resolve-persist (scaffold
stays DEPTH source till card end; corridor-placed traffic extras keep the sea populated
— log-uniform drained 24%→0.4% by f80, now steady). Phase C --micro DEFAULT OFF (Phil:
clean off-switch, judge with/without later): hover bars parallax-only lateral drift (one
sinusoid per bar, downbeats at zero offset), plunge gain surge. dolly_lab GATE PASSED
(4 same-seed arms × squid_lantern 4 cards; scripts/dolly_gate.py): no smear at gain 1.0,
arms diverge stably, and the KEY finding — the residual steers the model to PAINT
foreground-over-background composition where baseline stays wallpaper (pictorial depth
emerges from motion depth). Clip+strip sent to Phil (output/dolly_lab/). EVENING ROUND 2 (Phil's first verdict: all
parallax arms > baseline, GAIN 0.5 reads most 3-D, persist "not doing much" — CONFIRMED
by measurement: CN windows already span ~22/24 frames so persist extends ~2 frames/card;
a05 vs a05p byte-identical until the sea window; park persist). Labs now also ship a
SEQUENTIAL one-after-another cut (dolly_lab --sequence-only — Phil: side-by-side ×4 is
hard to judge). DELIVERED: squid 4-arm + 0.5-focus sequentials; coral v3 (1.0+persist)
AB+assembled; coral v4 (0.5+persist, seed 1234) AB+assembled+sequential v2→v4→v3.
0.5>1.0 hypotheses + per-source-gain refinement candidate in PLAN. FINAL CALL (after the
v3-vs-v4 side-by-side — Phil: 1.0 = MORE depth, only sometimes abrupt; 0.8-0.9 maybe
ideal): **parallax_gain = "random"** — every render draws {0.5..1.0 by tenths},
deterministic crc32("name#seed") (same-seed reproduces; even spread verified), recorded
in run.json + pipeline entry engine_params + ig_analyze "parallax gain" group. persist
parked; micro default-off. REQUEUE: all 15 pre-parallax review videos rejected → journeys
re-queued FRONT same-seed (music termite_citadel + queued caddis_masonry untouched).
TONIGHT: one-off 00:00 render task (PowersOfZen-render-once — DELETE it after) + budget
430 + LLLLSS prepended (RESTORE 340 / drop LLLLSS once the backlog drains); verified pick
whale_fall(.8) lantern(.7) cobalt(.9) ruby_furnace(.9) magnetite(1.0) wild_yeast(.5)
≈ 6.8h. coral_synapse UNQUEUED (Phil: enough corals — v4=0.5/v5=0.7/v3=1.0 same-seed
already exist; when he picks a gain, ingest GPU-free via queue_review --src, note in its
registry entry).
NEXT FRONTS (Phil): (1) SEAMS still not good enough (suspect IPA params — see PLAN "NEXT
FRONT"); (2) DONE same night — reposts/saves/shares SHIPPED: Phil converted the account
to professional; IG web still had no insights UI, but META BUSINESS SUITE accepts
"Continue with Instagram" (no FB account) — linked the zen Chrome session, built
scripts/ig_insights.py (per-post reach/SHARES/SAVES/follows/watch-time from the content
table; virtualization-safe incremental collect; viewless remount-rows dropped) →
outbox/ig_insights.jsonl, runs after every post + 12:00/00:00 + telem ig_insights /
ig_insights_login (session-expiry = relink by hand). First scrape n=44: shares/saves
leaders ALL rethink-era (sundew 12/12, desert_rosette 12/9, squid 7sh/10sv/14 follows);
avg-play-time unreliable under ~300 views. Followers 62 (was 59 at 11:00).
2026-08-22 (MARKETING DAY — stats now flow themselves): (1) IG stats snapshots now run
12:00 + 00:00 via the PowersOfZen-igstats task (ONE task, two PowerShell-registered
triggers → hidden_task.vbs → scheduled_ig_stats.bat; log outbox/ig_stats_task.log) in
addition to the after-every-post scrape — Phil: don't wait 19h between counts. ig_stats.py
hardened for unattended runs: Chrome self-heal (poster's contract), flock against
overlapping scrapes, SKIPS when a poster/gate run is in flight (poster's own call passes
--force since the gate lock is held), telem ig_stats event, viewless rows dropped at save
(they'd shadow the reel's last good row in the analyzer's newest-wins join). SCRAPER
COVERAGE BUG FIXED: IG virtualizes the reels grid — tagging tiles AFTER scrolling to the
bottom captured only the still-mounted 21–28 of 43 tiles and one run lost the NEWEST 7
reels; tiles are now tagged incrementally while scrolling (shortcode + absolute page-Y,
hover pass re-finds by code), coverage 36/43 validated through the real task chain.
(2) Dashboard Live tab: header (followers · n reels · last-scrape time) + TOP 5 BY QSCORE
strip (same fit as ig_analyze, pure-python OLS — no numpy on Windows python) above the
per-video stats; ig_stats telemetry icon. (3) ig_analyze grew a "posted era" group
(jul–08-04 / 08-05–08-13 / 08-14+ rethink). THE VERDICT (full numbers in audience-stats
skill + VARIATIONS.md performance notes): the rethink package (new-doctrine journeys +
music deck + resolve engine, n=10 posts) = median views 506 vs ~165, pushed >1000 40% vs
0–12% (earlier >1000s were only remix re-posts), pooled like 2.59%±0.33 vs ~1.95%,
followers 34→59 in 9 days (~2× growth rate) — era/engine/music co-move, so this validates
the package, not one variable. sundew_snare = catalog-best 3.05x qscore; squid_lantern =
biggest organic reach (2982). NEXT (Phil, after context clear): DEPTH — Phase-1.5 pictorial
depth plan in the 2026-08-17 entries; squid_lantern v5 depth A/B still awaiting his verdict.
2026-08-19 (HARDENING DAY): dashboard music-pick crash fixed (music candidate_plan emitted
duplicate ids when the lane rhythm is heartbeat — alt slot == halftime slot, second take
overwrote the first's files; distinct rhythm + id-uniquify guard + index in the widget key;
3 existing dupes deduped). SCHEDULER DE-INTRUDED: all tasks now run WINDOWLESS via
scripts/hidden_task.vbs (a Task-Scheduler .bat pops a focus-stealing console; wscript
Run(...,0) hides it; legacy 8am/6pm bats hand off to the same runner) — repoint actions
with PowerShell Set-ScheduledTask, NEVER schtasks /Change (password-prompts + quote-mangles;
rules in SCHEDULER.md "HIDDEN EXECUTION"). FULL AUDIT SWEEP (2 subagents; 15 code findings
fixed, commit ee757f7): the big one — poster counted PAUSED platforms in the live check, so
every post since the TikTok pause landed state=failed (34 repaired to live; Live tab was
right, analytics/state were wrong). post_gate: flock (Post-now button + hourly task can't
double-post), poster timeout 90min, GROUND-TRUTH advance (19h window burns only when the
target video verifiably went live). Atomic tmp+os.replace on pipeline.json/journeys.json/
spec writes. night_batch: per-child timeouts (a wedged ComfyUI can't hold the lock across
nights), compile-failure retry-once, GPU wait = comfy_busy OR util≥60 (game) — dashboard
previews no longer burn budget. Refill retry deadline-bounded to 75min total (was hitting
01:30 exactly). music_gen: empty-candidates guard + free_vram on every exit + choose()
re-reads before save. caption: comfy_busy gate, journey_worlds in try, utf-8 atomic spec
write. poster: preconditions (missing file/empty caption → failed, never a blank post).
ALL SKILLS + PLAN.md DE-STALED (subagent, ~30 corrections): zen-post now reads
pipeline.json + documents the cadence gate; tempo math is cards×fpb/3 everywhere; composer
schema documents `resolve`; repair skill notes tools don't reproduce resolve windows;
PLAN.md auto-post RESUMED + Phase 1 depth DONE. OPS: 08-19 batch ran clean (4 depth-fix
videos in Review: meteorite_cradle/physarum_maze/caddis_masonry/wild_yeast); midnight
refill failed on EXPIRED OAUTH (Phil /login'd; headless auth re-verified — tonight runs);
ember_meadow posted 12:00, desert_rosette next 08-20 07:00. Queue 12 journeys. Phil still
to judge: squid_lantern v5 depth A/B (v1 vs v5 loop in output/squid_lantern/v5/build/).
2026-08-17 (LATE NIGHT — DEPTH FIXES #1+#4 BUILT + LIVE): Phil's picks implemented, #2
(palette gloom fade — Phil does NOT want it) and #3 (depth-aware detail_boost — "I like
sharp") HELD. #4 = scaffold v3 in engine/scaffold.py: (a) true per-instance LOOMING —
_advance() accumulates camera travel Σ(z−1)/z, each instance's distance shrinks by it, so
position expands about the aim by d0/d and radius grows as 1/d^0.72 as d falls (near
instances rocket past + exit at d≤0.16, far ones crawl — size/brightness/motion now
AGREE); (b) painter's-algorithm occlusion — items render far-first and _gauss_blob's hard
core (≤0.72r) OVERWRITES with a shaded dome, rim still max-blended (spheres in space, not
discs on a plane). Verified on-CPU: looming progression strip at
output/realm_refs/scaffold_demo/v3_loom_check.png. #1 = resolve-window prompts get a
depth clause in dive.py ("enormous soft-focus shapes drifting close past the camera,
countless tiny ones far beyond" — deliberately NO gloom/desat words). TEST RENDER DONE:
squid_lantern v5, seed 1234 = SAME as v1 for A/B (first attempt crashed at the first
surface window — the depth-less "ground" sentinel broke the painter sort; hotfixed, all
4 modes + 4 lattice variants now CPU-exercised). A/B sent to Phil: side-by-side loop at
output/squid_lantern/v5/build/depth_AB_loop.mp4 + frame strip depth_AB_strip.png — v5's
windows read as populated fields with real size gradation (f52: countless small cells at
varied depth where v1 had flat macro). Phil judges the MOTION. Tonight's 01:30 batch
(17 queued, 3/20 backpressure) inherits everything since --resolve is default-on. POSTING FIXED + FIRED: the missed-22:00
root cause was the hourly gate .bats having LF endings (written via bash heredoc — Task
Scheduler cmd needs CRLF) plus the 18:00 window burning on an empty queue; post_gate.py
now parses post_next leniently, HOLDS the window when nothing is queued, and after firing
advances now+19h ROUNDED TO NEAREST HOUR (Phil: always post on the hour). squid_lantern
posted tonight ~22:14 (IG reel DcKg2bhhBG0 verified), next post armed 2026-08-18 17:00.
DASHBOARD: 📤 Post now button in Production (opens the gate + fires post_gate.py — one
code path with the hourly task); Live tab now shows 👁 views ❤️ likes 💬 comments per
video from outbox/ig_stats.jsonl (join by reel shortcode from the IG url, fallback by
journey name; 3 newest posts show nothing until the next scrape runs post-post).
2026-08-17 (CLOSE — READ THIS FIRST IN THE MORNING): TOMORROW = DEPTH (Phase 1.5), clean
context. THE DIAGNOSIS (settled with Phil tonight — the "what we were missing"): we
treated depth as GEOMETRY while our own machinery strips the PICTORIAL depth cues that
make images read 3-D. Evidence: even the reef frame Phil called 3-D has depth ONLY from
occlusion — zero haze/defocus/light falloff, everything equally sharp+saturated at every
distance. The four suppressors: (1) style tail "ultra-detailed/jewel-bright/vivid
contrast" = uniform sharpness+saturation everywhere = flat-decorative by definition, and
the global dark+saturated doctrine forbids atmospheric desaturation of the far field;
(2) detail_boost uniformly re-sharpens/saturates EVERY feedback frame — any hazy distance
the model paints is erased within ~3 frames (anti-collapse == anti-depth); (3) no prompt
ever INVITES haze/soft distance (scene grammar is planar "a field of"); (4) scaffolds
animate WRONG: all instances scale by the same Z — real approach LOOMS (instance at
distance d grows d/(d−Δ)): we broadcast cardboard-cutouts-in-formation, which is why
parallax was never legible; blobs also max-composite with no occlusion edges (discs on a
plane, not spheres in space). Proof it's us not DreamShaper: reef/squid-school read 3-D
because those content classes' training priors carry occlusion+haze strongly enough to
survive our suppression. THE PLAN, in variable-isolating test order: (1) depth language
in resolve-window prompts (near soft-focus occluder passing close; far forms fading into
gloom/haze); (2) palette doctrine amended: saturation is a NEAR-FIELD property, far field
desaturates into gloom (consistent with likes data — dark_frac correlates POSITIVE);
(3) DEPTH-AWARE detail_boost — sharpen/saturate weighted by depth (scaffold depth in
windows, DepthAnything elsewhere), far field gentler + slight desat: the biggest single
mechanical change; (4) scaffold v3: true LOOMING (d/(d−Δ) per instance), painter's-
algorithm occlusion with hard near-edges over far, ambient fog gradient in the depth
signal, strict size-depth agreement. DELIVERABLE: one resolve window rendered 4 ways
(baseline/+prompts/+depth-boost/+looming) as a SLOW LOOPED 12fps A/B before any full
render. Camera moves stay PAUSED — motion-depth's cheap 90% (looming + per-plane
parallax) lives inside scaffolds, no image warps needed; landing/threshold resume after
pictorial depth works. Everything else is settled and running: captions now use rhyme names (generator
verified fresh: "Dora the Flora"; all 11 review/music videos' STORED captions migrated —
live videos keep their posted captions); all 11 review videos carry music pregen
candidates (approve = seconds); posting = 19h cadence gate (Settings-editable, fired
first at 18:00 today); C: at 86% after archiving 121.9G/96 trees to E:\zoomer_archive
(manifest in outbox/archive_manifest.jsonl; delete-class 6.4G flagged, untouched);
nightly refill+render run themselves (refill assigns tempos; batch pregens music).
2026-08-17 (later): ENGINE-3 CAMERA MOVES PAUSED (Phil's call — "get our world looking 3-D
and parallax looking nice BEFORE adding camera moves; not too many things at once"). Phil's
orbit-v3 verdict: not convinced — no legible orbital motion/parallax; the raised denoise
CHANGED the content (solid gem-rock ground instead of space-plasma holes) rather than
demonstrably revolving; also the lab A/B clips play too fast to judge ("about four
discernible frames") — FUTURE LAB CLIPS: 12fps real-time + looped, not 6fps once. The v3
technical gate result (resample-loss-vs-resynthesis balance) stands on file for when
engine 3 resumes. CURRENT FOCUS = DEPTH REALISM (Phase 1.5): size-depth consistency
(Phil keeps seeing small things IN FRONT of big things — instance size must agree with
depth value), legible parallax inside resolve windows, far-floor knob test — deliver as a
SLOW A/B on one window. DISK: C: at 98% (27G free); E: mounted empty (232G).
output/ = 125G of the ~145G project. scripts/archive.py built (policy in its docstring:
live/rejected/failed render trees + labs + orphans -> E:\zoomer_archive with copy-verify-
remove + manifest; active-stage trees, mascots, music stay; build/labeled+raw+interp in
kept trees = flagged delete-class, untouched pending Phil). Dry-run + the big move run
2026-08-17. MUSIC: pregen chain run for all 11 review videos (whale_fall validated the
realign fast path end-to-end: 5 candidates, seconds).
2026-08-17: ORBIT GATE PASSED (v3) + FOUR QUALITY-OF-LIFE SHIPS. Orbit v1 washed out (no
CN), v2 washed out (circular anchor: CN held the warped frame's own smear) — the REAL
mechanism was cumulative bilinear resample loss vs re-synthesis; v3 (denoise floor 0.52 in
the window + post-warp unsharp) holds 15° of true revolution crisp. Engine-3 Phase 2 gate
= PASSED; known lab artifact: palette drifts (lab lacks dive's color_match — integration
inherits it). Phil to judge parallax in motion. SHIPPED SAME DAY: (1) mascot RHYME NAMES
(pipeline.MASCOT_DISPLAY: Adam the Atom / Alexis the Galaxy / Cosmo / Belle the Cell /
Clark the Quark / Dora the Flora / Janet the Planet / Kitty the City / Lamar the Star /
Lee the Flea / Lorraine the Terrane / Dwight the Light / Tina the DNA) — captions + VLM +
dashboard use display names, internal keys/files unchanged; old stored captions keep old
names until regenerated. (2) MUSIC PREGEN: night_batch generates+ranks candidates per new
video after renders (one ACE load, unshifted cut, stored music_pregen); approve→Music now
runs music_gen --realign (seconds of ffmpeg) instead of minutes of generation. (3) POSTING
CADENCE GATE: hourly PowersOfZen-postgate task + legacy 8am/6pm tasks all delegate to
post_gate.py — fires when settings post_next arrives then advances by post_every_hours
(19h; dashboard-editable in Settings; missed windows never burst). First fire tonight
18:00. Legacy tasks are harmless but undeletable without elevation (commands in
SCHEDULER.md). (4) Dashboard: Live tab newest-first; cadence controls in Settings.
Phil's remaining depth verdict: coral marginal, still layered-2.5D — engine-3 camera
motion is the bet, orbit gate now open for Phase 3.
2026-08-15: ENGINE 3 PLANNED (see PLAN.md "ENGINE 3 — THE CAMERA" — the plan of record).
Phil's morning verdict on the resolve era: better but marginal; 2-D-ness persists ("big and
little things in a 2-D plane" — his log-depth instinct = Phase 1); the two missing realm
jumps are planet→landscape (no descend/land — the `landing` hero move: approach →
pitch-over → terrain SKIM with a varied-terrain menu) and exterior→interior (the
`threshold` hero move: aperture-targeted crossing ON a beat into a `chamber` scaffold).
IRON LAW: scale-zoom constant and never stops (forward/lateral speed may vary), moves are
musical events, the loop must close (net camera ≈ identity), every frame freshly generated.
Architecture: warp layer (depth-aware reprojection of the fed-back frame + disocclusion-
mask denoise) + scaffold layer (performs the identical move) + semantic layer (POV ramps).
CINEMATOGRAPHER = a separate role from the composer (rule-based v1, LLM v2). Phases gated
by labs: 1 scaffold depth realism → 2 warp core (orbit_lab gate) → 3 vocabulary +
cinematographer v1 → 4 landing_lab + threshold_lab → 5 polish/adoption. NEXT ACTION when
Phil gives go: Phase 1 (same-day) then orbit_lab.
2026-08-15 (later): PHASE 1 SHIPPED (log-uniform depth verified 63-87/octave, values
0.06-0.98, compressive falloff keeps far speckle; dive dumps scaffolds to build/resolve/);
coral_synapse rendered as the depth showcase (in Review). PHASE 2 BUILT (engine/warp.py
truck/orbit/tilt/dolly + depth-via-comfy + EMA + disocclusion boost; scripts/orbit_lab.py).
ORBIT GATE **FAILED in naive form** — 23° revolution washed the star into streaks by ~18°:
cumulative warp degraded structure faster than travel-denoise re-diffusion re-anchored it
(no subject hold, pivot not on the tracked object, noisy depth on abstract starfield).
V2 FIX LIST (ordered): anchor the pivot object with approach-CN during orbit; pivot at the
TRACKED subject; halve step to 0.5°/frame + fewer net degrees; blur/quantize depth into
planes pre-warp; pair orbit with a scaffold window (conditioning+warp agree); consider
warping the depth map forward as the CN signal. The gate worked as designed — stabilization
before vocabulary. Known Phase-1 knob if coral still reads flat: raise far-value floor
0.06→~0.18 (honesty vs compositional grip).
2026-08-14: RESOLVE-ON-APPROACH BUILT, INTEGRATED, AND PROVEN ON A FULL RENDER. Morning
triage: the overnight batch died when Phil took the machine mid-ember_meadow (5 of 7 done;
ember+bee re-queued at head, tonight template MS, budget 240); frame forensics on the new
renders found the era's core sameness mechanism — MID-DIVE, EVERY frame inherits close-up
texture, so wide/populated cards collapse into filament soup (abyssal vent_plain, ivory's
chessboard kingdom) while texture-realms and card-0 scenes deliver (squid school, enzyme
rotors); palette doctrine hit its numbers (all 4 in the winner pocket). Phil's microscope
grammar reframed the fix: a realm shift = the old texture RESOLVING into countless tiny
instances of the new realm (never a camera pull-back). BUILT: engine/scaffold.py (animated
procedural depth scaffolds — instances in world space projected through the render's own
zoom + drift, DEPTH-PARALLAX so near layers slide faster; modes sea/lattice/surface/web,
lattice variants cubic/hex/diamond/layered picked from the REAL mineral, web = connected
nearest-neighbour net; library doc in VARIATIONS.md); scripts/resolve_lab.py (schedule-
faithful A/B harness — vent_plain lab test WON decisively); dive.py --resolve (windows
auto-derived per card: mode by REALMS band, journey `resolve` field overrides/opts out,
seam arrivals + cameo paste windows + loop tail protected, tracker suppressed during
windows). FULL A/B RENDER: abyssal_chandelier v2 (same seed as v1, 9 windows) — frames
show populated colonies and instance-seas where v1 had noodle soup; Phil judging the
motion. NOT yet default: the nightly batch renders WITHOUT --resolve until Phil approves
the full video (then: pass --resolve in night_batch/render_one + make it the default).
CAMERA-MOTION PLAN (delivered, staged): Layer 1 = scaffold-space moves (parallax SHIPPED;
scaffold-orbit spiral-in + scaffold-tilt next, days); Layer 2 = image-space depth-warp of
the fed-back frame (true orbit/tilt/truck on real imagery, disocclusion healed by
re-diffusion — crop-and-reimagine generalized; prototype = orbit_lab, the ENGINE 3 gate);
then a per-card `camera` vocabulary (spiral/tilt/truck/roll/settle, moves land on beats,
composer assigns from REALMS POV tags). IG stats auto-snapshot ran with the 08:00 post.
OPEN: Phil's verdict on abyssal v2 → flip --resolve default + re-render the queue; remix
slot; library curation (offline, deferred); loom_of_nights cuts (stale).
2026-08-13 (FINAL, evening — READ THIS FIRST TOMORROW): THE REALMS RETHINK IS EXECUTED.
Phil's decision after seeing the library evidence: IPA REALM STEERING IS DEFERRED — the
engine is UNTOUCHED (loop-homing IPA stays; his worry: "the worst images in the video are
the ones that aren't generated from a previous image" — external conditioning risks the
feedback-chain coherence, and no library image yet beats our best in-video frames). Ship
the PROMPT-SIDE revolution first and watch. Library development continues OFFLINE (sea
doctrine in REALMS.md; depth-scaffold generation proven in output/realm_refs/sea_test —
"maybe the library just needs to be depth control"; two-dimensionality critique on file:
steeper near/far contrast + implied motion next iteration). Accordingly: ALL 26 queued
old-doctrine journeys retired to GRIST (registry notes; themes minable, specs dead) and
12 NEW-DOCTRINE journeys composed tonight by parallel opus composers (briefs in
outbox/rewrite_briefs_20260813.md, all 12 pass preflight+audit 0 flags): L = abyssal_chandelier,
ivory_gambit, whale_fall_republic, moth_orchard_night, geode_cosmos, lantern_mangrove,
coral_synapse · M = bee_cathedral, observatory_dusk · S = ember_meadow, squid_lantern,
magnetite_choir. Tempos spread fpb 6-9 (composers all defaulted to 8 — wave 2 got fpb
ASSIGNED in briefs; remember that for the refill: assign tempo in the brief or they
cluster). TONIGHT (Phil's ask: more videos): template LLLLSSM, budget 500min — 01:30
renders abyssal+ivory+whale_fall+moth_orchard+squid+ember+bee (~7.5h, done ~09:00);
render_paused=False; backpressure clear (2/20). RESTORE render_budget_min to 240 and
nightly_templates to ["LLS","LMS","LLM"] after tonight (or keep if Phil likes the volume).
POSTER now auto-runs ig_stats.py after every posting run (the tracker feeds itself,
starting 08:00 tomorrow). MUSIC is DONE per Phil ("good place"): kick-weighted phase,
kick-ranked candidates + pulse top-ups, positive-exclusivity tags; tempo tests deleted;
120bpm routine ceiling / 80 floor / 144+72 rare tails. TOMORROW'S LIKELY AGENDA: review
the 7 new-doctrine videos in the morning (the whole rethink's first real output), curate
output/realm_refs/ if continuing the library, restore batch settings, consider the
remix-slot experiment (jade_automata or butterfly_meridian re-render+post — reach test).
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
2026-08-02 (evening): REPLACE_OPENING REDESIGNED per Phil's clarification — NO SCENE SKIPPED.
Phil approved copper_rain v2's IPA seam in the full video, and corrected the opening tool's
design: card 0's scene is WANTED content (it failed only as a cold txt2img opening; "we can
assume the journey card contains something we want in the video"). The arc no longer bridges
last-world -> card 1 directly; it renders the ORIGINAL compiled schedule for the regenerated
slots via dive.phase_info (tail slots = their own loop-home prompts, which already plunge INTO
card 0's world; card-0 slots = card 0's own travel/plunge — the scene passes through mid-dive,
where the engine is strong), with: a wrap-around crossfade at slot 0 (phase 0's prev = the last
phase), a seam-class denoise morph at slot 0 (it IS a bar line) + 2-frame anacrusis on the last
tail slots, and ipacn homing confined to the last morph_frames (12) onto kept frame C0 — which
still half-shows card 0's world (card 1's arrival morphs OUT of it), so the landing gap is
small by construction. Original exponent schedule already correct for every slot (no counter
re-derivation). Dry-runs verified on pollen_court/loom_of_nights/quantum_orrery. AWAITING
Phil's go to run them (~52 frames ≈ 15 min GPU each, --queue-review lands them in Video Review).
2026-08-02 (late): REPAIR FAMILY MADE DURABLE + DOCUMENTED. New **video-repair SKILL** = the
user's guide (decision tree: full re-render vs replace_opening vs replace_tail vs
make_candidate; rhythm doctrine as tests — flip ON the bar, never freeze a plunge, no kept
frame after a regenerated one across a morph boundary, splices schedule-faithful; gotchas:
pin --src-version, engine-1 compile==saved-frames check, cameo windows, never queue_review a
production-stage video). Scratchpad drivers promoted: scripts/replace_tail.py (tail-only ipacn
splice, schedule-faithful, --queue-review for review-stage) + scripts/make_candidate.py
(production candidates: measured rotation + production's own audio -> output/candidates/;
--install = backup + swap production + chosen music aligned copy, reseam_production's
contract). dive-video SKILL cross-references. IN FLIGHT: frost_window tail candidate +
mineral_heart replace_opening (from ds/v5, engine-1, 60-slot arc) candidate — both for Phil's
review, production untouched. Earlier today Phil approved: copper_rain v2 seam, the four
v2-tool openings in review, sugar_nebula (moved to Music).
2026-08-02 (close): Phil APPROVED + INSTALLED both production repairs via make_candidate
--install: mineral_heart (full card-0 replacement, ds/v6) and frost_window (tail-only ipacn,
v2) — production files swapped in place (same start frame, same music; originals in
_seam_backup/), chosen "warm" music candidate copies updated, poster paths unchanged. Earlier
approvals today: copper_rain v2 seam, sugar_nebula tail (moved to Music), four v2-tool
openings in review. STILL OPEN: loom_of_nights card-cut list (first Level-2 splice);
static_bloom re-queue is Phil's call in the Journeys tab.
2026-08-03: CAMEO REALM-MATCH DOCTRINE (Phil: the sprite must match the register's exponent —
realm-match BEATS cast rotation). pipeline.py: MASCOT_EXP table + CAMEO_EXP_TOL=3 +
cameo_realm_check(); audit_starts hard-fails off-realm cameos (blocks refill auto-queue);
preflight prints a cameo-realm line; composer SKILL: pick the cameo CARD first, mascot NEAREST
its exp, rotation only among passers — extreme mascots travel rarely, that's correct. Root
cause of the drift: full-cast rotation pressure on a catalog whose cards cluster at exp -5..+3
put Amos(26)/Aleksey(21)/Clark(-15)/Adam(-10) on mid-scale cards (Amos in a beehive). ALL 34
active journeys fixed to 0 audit flags: 10 unrendered reassigned (nearest realm, variety ties),
11 rendered fixed FORWARD (existing videos/captions untouched; future re-renders get the right
mascot), chalkboard's cameo MOVED off the 10^16 chalk_realm (no mascot lives there) to
amphitheater_plan(2)/kitty. SPRITE->OBJECT INVESTIGATION (no action, Phil's call): mechanism
confirmed on tesla_garden v1 f164-176 — when the paste window ends (size>0.30), full denoise
regenerates the sprite pixels and the checkpoint absorbs them as scene vocabulary (Clark ->
neon filament wheel); the tracker then locked ON the ex-sprite (f166, it IS the salient round
object matching the target_phrase) and dove into it. Not new engine behavior — tracker-era
composition keeps objects near the thirds anchor IN FRAME (engine-1's drift slid sprites off
fast), so takeovers now happen on camera. Frequency knobs IF ever wanted: end the window
smaller than 0.30, fade the last 2-3 paste frames, or veto locks inside the cameo's propagated
box just after a window. Phil: fine as long as it's occasional.
2026-08-12: MUSIC-GEN OUTAGE + BATCH WEDGE + POSTER GAP — all diagnosed from logs, all fixed.
While Phil was away the pipeline ran itself fine (renders 08-03..08-08, posts through 08-10);
three independent failures then stacked up: (1) MUSIC KEYSCALE 400s: ComfyUI's ACE-Step
TextEncodeAceStepAudio1.5 keyscale is a FIXED 34-entry enum ("Eb major", "F# minor" — never
"E-flat"/"F-sharp"/modes); refill composers write music_key in prose, so resonance_hall
("E-flat major") died INSTANTLY at /prompt validation — and the dashboard's Popen sent
stdout/stderr to DEVNULL, so the video just sat in Music with no candidates. Fixed:
engine/music.normalize_key() (prose→enum, mode fallback dorian→minor etc., unknown→A minor,
prints remaps), run_workflow surfaces the 400 BODY (it contains node_errors), and the
dashboard logs every spawned gen to outbox/music_gen_<j>.log / caption_<j>.log — never
DEVNULL a Popen whose failure you'll need to see. jewel_oculus ("F-sharp minor") and
ochre_door ("D dorian") would have hit the same wall. (2) AUTO-GEN SKIPPED ON APPROVE:
approve_to_music gated on gpu_busy() = nvidia-smi utilization ≥30%, which false-positives on
the dashboard's OWN looping <video> previews (Chrome decodes on the GPU) — so approvals
silently skipped generation ("come back and click Generate"). Fixed: pl.comfy_busy() asks
ComfyUI's /queue for actual running/pending work (stdlib urllib — Windows dashboard has it);
approve + Music-tab warning use it; a skip now writes telem music_skip. gpu_busy() stays for
night_batch's game check. (3) VRAM NOT CLEARING: ACE-Step leaves ~9 GB resident after a gen
(SDXL ~7 GB after a render) — Phil was killing ComfyUI to play games, which left it DOWN at
01:30. music.free_vram() POSTs ComfyUI /free (unload_models+free_memory) at the end of every
music_gen run and night_batch end-of-batch; next job reloads in ~15s. (4) THE BATCH WEDGE:
night_batch.comfy_up() ran start_comfyui.sh, whose last line is `exec tmux attach` — in a
scheduled run that BLOCKS FOREVER; the 08-08 batch hung there holding the /tmp lock (ComfyUI
itself came up fine underneath — send-keys had fired), so 08-09+ nights exited "already
running" and the render queue froze at 20/20 while refill correctly no-opped. Fixed: comfy_up
now recreates the tmux session detached (kill-session; new-session -d; send-keys) and never
attaches. (5) THE AWRY POSTING NIGHT: 08-08 08:00 failed with "Chrome CDP not reachable" —
nobody relaunched zen Chrome after the reboot; zero flags, the poster refused cleanly. Fixed:
poster self-heals — CDP down → run start_chrome_zen.sh (idempotent, non-blocking), wait ≤60s
for :9222 + 15s for tabs, telem poster_chrome_selfheal, then proceed. CLEARED THE BACKLOG:
resonance_hall + tide_glass (the two stuck in Music since 08-09) each have 5 fresh aligned
candidates (locks up to 11.1x/9.8x) awaiting audition; VRAM confirmed freed after both runs.
8 videos sit in Video Review; posting queue is EMPTY until Phil approves. TONIGHT IS A WATCH
NIGHT for the batch fix (queue head: jewel_oculus + turing_springs + droplet_zoo); tomorrow
08:00 validates the poster self-heal only if Chrome is down again.
2026-08-13: TEMPO + MUSIC DECK + ANALYTICS + REALM FORMALISM (huge session; commits d990c5a..d344db7+).
(1) TEMPO IS A JOURNEY KNOB: bpm = 720/frames_per_beat at 12fps (fpb 5→144, 6→120, 7→103
default, 8→90, 10→72); musical geometry (transition/seam/anacrusis frames, loop tail) now
SCALES with fpb (dive.py cfg-time, grammar loop block — fpb 7 byte-identical); a fine retime
at the minterpolate stage gives the continuum between steps (designed, NOT built). A/B
renders in output/tempo_lab/ (copper_rain at fpb 5/6/10) sent to Phil — verdict pending,
composer-skill fpb rule deliberately HELD until Phil approves the look. Phil: 51bpm music
too slow, waltz = rare spice only. (2) MUSIC DECK LIVE: styles/music_deck.json (10 lanes ×
4 rhythm feels + brand tail + negatives; deep-downbeat doctrine); music_gen generates 8
(own lane + alternates + 3 wildcards + seed jitter + occasional 3/4), auto-ranks by lock ×
bar-clarity, keeps 5 with lane spread; per-journey seeds (old fixed 500-504 made every
journey's 'warm' identical). Validated on ammonite_spiral. Composer assigns music_lane.
(3) AUDIENCE ANALYTICS (audience-stats SKILL + scripts/ig_stats.py + ig_analyze.py):
ig_stats scrapes followers + per-reel views/likes/comments via TRUSTED CDP hover on the
reels grid (Phil's method; CSS :hover ignores synthetic JS events); ig_analyze fits the
catalog's own scaling law (engagement ≈ 0.14·views^0.68 — like-rate DECAYS with reach) and
ranks by QSCORE = engagement/expected (Phil's insight: views are EARNED; like%-only punishes
pushed videos). TWO-AXIS LAW: likes reward dark+saturated+nameable (sat +0.34, lum −0.33
measured on real frames — video_features.json); REACH rewards scale span (full-scale 44%
pushed vs 10%). Applied: candy_gloss RETIRED (glass_apiary→crystalline, sugar_nebula→
cosmic_gloss), pale-wash deprioritized, tier_share 0.55L/0.15M/0.30S + LLS-first templates,
full-scale reinstated for L-tier. REMIX finding: the two reach outliers are re-posts of
journeys whose originals got ~180 views (10×, confounded by account age — deliberate
remix-slot test proposed, Phil interested). (4) REALM FORMALISM: journeys/REALMS.md (per-band
archetypes + CONTINUATION RULE: living→cellular→molecular machinery, mineral→its real
lattice, made→its material; POV attitude tags [air]/[obl]/[eye]/[up]/[amb]; mineral list;
ecosystem menagerie); scripts/novelty_audit.py measures band coverage / broken continuation
(16 journeys) / motif monoculture / populated scenes (0/106!) and its --brief report is
EMBEDDED in the refill coordinator prompt — novelty is now data-driven. Composer skill:
realm tests. (5) LIBRARY PROBES (output/realm_refs/): DreamShaper BY NAME renders mesophyll/
mitochondria/tide-pool/every-mineral SPECTACULARLY (the catalog gap was never asking!) but
fakes molecular machines (ribosome→toy molecule, protein→jewelry) → IP-Adapter reference
steering needed ONLY for that corner. Donor pipeline proven: numpy raymarched gyroid +
Gray-Scott + Voronoi + REAL PDB renders (1BNA DNA, 4HHB hemoglobin via matplotlib, newly
installed) → img2img brand pass (hemoglobin+gyroid great, DNA donor needs thicker/brighter
geometry). NOTHING wired into the engine per Phil — libraries first. POV: near-term =
attitude ramps in scene wording across a card (codified); medium-term = depth-warp tilt
(DepthAnything maps exist; crop-and-reimagine generalizes to camera rotation) — lab
prototype proposed, not built. OPEN: remix-slot pick; loom_of_nights card-cut list (old).
2026-08-13 (close): PHIL'S VERDICTS + QUEUE RESET. Tempo: ALL three A/B clips approved
(fpb5/144 "not choppy — great"); FLOOR = 80bpm (fpb 9), 72 rare tail only; composer skill
tempo rule live (fpb by journey energy, total ≤~30s test). Tempo-test videos are in the
MUSIC TAB as copper_rain_fpb{5,6,10} (TEST-marked captions, registry-guarded so the batch
can never render them; each got 5 deck candidates on its own seeds — fpb5 drew
aurora_strings lanes at 146bpm-generated music, fpb10 drew music_box at 72) — Phil wants to
hear tempo+music together; delete specs+entries after the audition. QUEUE RESET (Phil: "not
in love with anything in the queue"): 8 review videos (gossamer_dawn heron_delta
chess_empires night_lido attic_drift jewel_oculus turing_springs droplet_zoo) → rejected,
their journeys re-queued force=True with note "REWRITE to REALMS/new standards before
re-render"; RENDER_PAUSED=TRUE until the rewrite lands. ammonite_spiral restored to Music
(Phil will publish with new-deck track). cinder_veil + salt_mirror in Music (Phil's picks).
THE AGREED ROADMAP: (1) build + curate the IPA reference library (realm_candidates.py
generated 24 archetypes × 3 seeds overnight → output/realm_refs/candidates/, Phil curates;
refs are ENV-phrased fields, not lone objects — Phil's seam-into concern; obj_ refs tagged
separately for target moments), (2) implement IP-Adapter realm steering in the engine +
test on ONE full-scale journey, (3) THEN mass-rewrite all queued journeys to REALMS
standards (composer subagents), (4) unpause renders. Mechanical tilt/rotation = "engine 3",
deliberately deferred until the realm era ships. Posting continues from Music/queued stock
meanwhile. Phil's
priorities: perfect music loop, tempo variety (investigate), strong deep beats + more usable
candidates. FOUR ALIGNER DEFECTS found, fixed, and VERIFIED (position-coded synthetic +
end-to-end mapping measurement — final audio at video time t is music-bed content at exactly
t+w0, corr ~1.0): (1) LOOP STUTTER: step 4 built the loop as body=R[0:dur] crossfaded into a
COPY of the head, so the file ended on R[XF] while starting at R[0] — every loop replayed
0.5s, and the phase rotation parked that stutter w0 (~0.5-2s) BEFORE the video's end. Phil's
"not always a nice perfect loop" = exactly this. Fix: body=R[XF:XF+dur] — the tail now fades
through the material leading INTO the start (wrap sample-continuous), and since dur = integer
bars the crossfade pairs content one whole loop apart = identical grid phase. (2) TILING:
joins at arbitrary track length shifted the beat grid at every join — all content past tile 1
played off-grid, invisibly (the lock score dropped morphs beyond one tile). Fix: tiles trimmed
to k*bar+XF so every tile restarts at grid phase 0; phase search folds all morphs onto the
tile period. (3) SILENCE STRIP excised INTERIOR silences >=0.3s (tide_glass choir lost 3.26s
mid-track) — a chopped grid can't be locked by any single (stretch, phase). Fix: edge-only
strip (areverse trick). (4) STRETCH SEARCH overfitted sparse envelopes (picked 0.99 where the
track implied 1.004; ~0.14s drift by video end). Fix: MEASURE the track's own bar
(autocorr near the video bar), derive stretch = m_bar/video_bar exactly, search phase only.
resonance_hall + tide_glass candidates regenerated on the fixed aligner (their pre-fix
versions were never auditioned). All LIVE videos carry the old stutter; nothing in production
queue does (it was empty). TEMPO FACTS (probed, output/music/probes/): we have shipped ONE
tempo ever — 103bpm on every dur-schema video (bpm = 240/bar, bar fixed at 2.333s by the
format). ACE-Step OBEYS the bpm tag 51-154 (measured onset periods = integer multiples of the
requested beat) but PHRASES IN 4-BEAT BARS, so usable framings are only those aligning music
bars with the morph interval: 103 (morph=1 bar), 77 (waltz — probe locked 3/4 exactly), 51
(half-time — downbeat every OTHER morph, which Phil pre-blessed); 129/154 clash with 4-beat
phrasing (bar-accent lands off the morph grid). RHYTHM VOCAB (probed): "a single deep 808
kick lands exactly on the downbeat of every bar" beat everything for bar-level pulse
(ac@bar 0.50, bar-period dominant); dense "four-on-the-floor sub kick" underperformed (0.17);
the current no-drums prose already phrases at half-bar/bar. Remaining lock imperfection is
MUSICAL, not mechanical: arpeggio-type textures have onsets on every 8th so no decisive
downbeat phase exists — fix upstream (deep-downbeat tags) + selection. PROPOSED (awaiting
Phil): candidate matrix varying rhythm x timbre x tempo{51,77,103} with per-journey seeds
(today every journey's 'warm' = seed 500 = same noise, a sameness generator); overgenerate
8-10, auto-rank by bar-clarity/lock/pulse-at-bar, present top 5; blanket 'no drums' replaced
by 'no snare/hi-hat/cymbals/woodblock' + explicit deep-kick language; MusiConGen stays the
phase-2 option if ACE rhythm obedience proves insufficient. FUTURE (Phil's list, not started):
IG likes-tracking + A/B framework; style diversity (kill candy/ceramic-tile looks, prefer
coherent full-scale space->subatomic journeys — those outperform).
