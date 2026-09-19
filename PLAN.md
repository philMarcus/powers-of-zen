# Zoomer — plan of record

Started 2026-07-22, re-scoped same day. Goal: an agent team that produces and posts
**hypnotic AI zoom-trip shorts** — endless dives through morphing worlds (neurons →
galaxies → eyes → coral → fractal cities) — and maximizes followers. This is an
attention project, not a science project; scale-of-the-universe ideas are flavor, not
curriculum. This file is the source of truth for decisions; update as they change.

## Decisions

| Decision | Choice |
|---|---|
| Budget | Strictly $0 — everything local on the RTX 3080 (10GB) |
| Product | 9:16 vertical, 7–15s to start, maximally AI visual feast, seamless loop wherever possible |
| Signature move | The continuous zoom/dive — every video unmistakably "the zoom account"; worlds vary endlessly |
| Science | Very loose — awe-bait garnish in captions/labels, never a lecture. Artistic > accurate. |
| Audio | Trending sounds from platform libraries, chosen per-post; zoom accelerations & transitions beat-synced |
| Platform | TikTok primary (manual phone posting), cross-post to YouTube Shorts + Instagram Reels |
| Operation | Interactive only — Phil approves every video. Autonomy added in phases. |

## Production approach: local AI video, two engines

1. **Deforum-style feedback zoom (workhorse)** — each frame is a zoomed crop of the
   previous frame re-diffused with time-scheduled prompts, so the world continuously
   morphs as you dive. Unlimited length, genre-defining psychedelic aesthetic, fast with
   the SDXL-Turbo already installed. ComfyUI nodes exist for this (FL_InfiniteZoom /
   Deforum-for-ComfyUI — evaluate both).
2. **Real video models (hero shots)** — now fit 10GB: Wan 2.2 TI2V-5B at FP8 (~8GB),
   Wan 2.2 14B via GGUF (480p), LTX-2 with NVFP8 (2x speed / −40% VRAM on RTX 30).
   Used for smooth cinematic moments interleaved with zoom segments.
3. **Assembly/post** — ffmpeg: concat segments, beat-sync cut timing to the chosen
   audio, loop seam, optional label garnish. Audio added at post time when the platform
   supplies the trending sound.

Pipeline: `journey concept → world/morph sequence → prompt schedule → ComfyUI renders
(zoom engine + hero shots) → assembly/beat-sync → outbox (mp4 + caption + hashtags) →
Phil reviews → post`

## Marketing doctrine (v1 — Marketing agent revises with data)

- Loop so it rewatches before the viewer notices; completion/rewatch drive TikTok ranking.
- Open mid-dive at max intensity — hook in the first 0.5s, never an establishing shot.
- 7–15s until analytics justify longer.
- Ride trending sounds; sync motion to beats.
- One signature move + endless world variety = follows, not just views.
- Awe-bait captions ("what a thought looks like at 10 scales") frame the trip for free.
- Post cadence target once live: 1–2/day; consistency beats bursts.

## Scale ladder (canonical registers — journeys traverse these, skips allowed)

quantum foam → molecules/chemistry → cells/microbes → flora (plants/fungi/forests) →
**creatures** (fantastical animals, food-chain drama — fleas-on-the-dog, fish-eats-fish,
always unreal and cool, never gory) → **human-object scale** (made things: instruments,
markets, workshops, relics — objects and interiors, no faces) → city/landscape →
planet (landmasses/oceans from orbit) → solar system → galaxy → cosmic web.
Quantum foam ↔ cosmic web look alike (networks) — the natural loop seam.
Engine dives inward (large→small); the `reverse` setting emits the same footage backwards
for the zoom-out direction. One render = two videos.

## Variety engine (design agreed 2026-07-22; build after core pipeline is polished)

Novelty must be systematic, not vibes. The World Builder (local LLM, e.g. qwen3.6:27b via
Ollama) composes each journey from combinatorial ingredient tables:

- **Substrate**: coral, circuitry, stained glass, magma, silk, bone, origami, clockwork,
  ice, fungal mycelium, woven light, ceramic, rust, paper, neon glass…
- **Structure motif** (the mathematical play): fractal recursion, voronoi cells, hyperbolic
  tiling, branching networks, spirals/phyllotaxis, foam/bubble packing, knots, lattices,
  strange attractors…
- **Palette + mood**: jewel tones / bioluminescent dark / pastel dream / molten / monochrome
  with one accent…

A journey = scale ladder × (substrate, motif, palette) rolls per register, composed by the
LLM into dense prompts ("a city built of stained-glass mycelium," "a galaxy that is a
strange attractor of molten silk"). Every used combo is logged (journeys/log.jsonl) so we
never repeat; the Marketing agent later reweights sampling toward what wins followers.
Seeds and checkpoint choice add further free variation.

## Format architecture (agreed 2026-07-23 — supersedes raw-prompt journeys)

Verdict on diversity batch: cool but reads as MORPH, not ZOOM. Causes: only ~2× zoom per
register (needs ×10), denoise so high nothing survives to be approached, wallpaper
prompts with no target object, constant zoom speed. Fix = three-layer structure:

- **Layer 1 FORMAT (fixed, tuned centrally)**: zoom physics with arrive→look→plunge speed
  curve; pacing knob (sec per decade, default 3); phase grammar templates
  (approach/arrival/interior); denoise schedule (~0.35–0.42 travel, ~0.6 transitions);
  odometer scale counter (10ⁿ m, rolls on decade crossings with a pulse — later
  beat-synced); exact loop (frame-0 composited into final register, growing until
  last frame IS first frame). Lives in format.json + engine.
- **Layer 2 STYLE (small curated deck)**: checkpoint + style tokens + IPAdapter reference
  images from library/style_refs/ (best frames get promoted back into the library —
  flywheel). Turbo is default workhorse (composed cities better than DS + 3× faster);
  DS is an occasional flavor.
- **Layer 3 JOURNEY (infinitely varied, agent-written)**: ladder slice + one world card
  per register — SLOT FILLERS not prose: {register, target, interior, seed_of_next}.
  Engine compiles cards through grammar templates into prompts. World Builder can only
  vary what slots expose — cannot break format.

**Mascots** (Phil's idea, merged with counter): fixed cast, rhyming names, one per
register — draft: Quark Clark, Atom Adam, Cell Adele, Flea Lee, Market Margaret,
City Kitty, Planet Janet, Star Lamar, Galaxy Aleksey, Cosmos Amos. One hidden
Waldo-style cameo per video (sprite composited into fed-back frame at low denoise —
consistent identity, restyled per world). Find-the-mascot = comment/rewatch bait.

**ControlNet-depth**: radial depth template each frame (center=far) to force a
persistent tunnel composition — structural anti-morph. IPAdapter + ControlNet aux +
Ultimate Upscale already installed in ComfyUI.

Build sequence: (1) anti-morph package + 4-decade proof cell→creature→city→landmass;
(2) mascots + style library; (3) ControlNet depth + checkpoint shopping on Civitai.
Videos reviewed by Phil between builds.

## A/B pair-testing doctrine (Phil, 2026-07-23 — build capacity now, use once popular)

Videos are produced in PAIRS differing in exactly one variable (model, palette, pacing,
narration, loop style…). Posted as a pair, their performance delta is a data point for
the Marketing agent. Requires enough baseline reach to be meaningful — don't gate early
posting on it, but keep the pipeline pair-capable (same journey, one knob flipped —
`--model turbo|ds` is already the first example).

Model notes (researched 2026-07-23): dreamshaperXL.safetensors = DreamShaper XL
Turbo/Lightning-class (Feb 2024): needs DPM++ SDE + Karras, cfg 2, 4–8 effective steps;
also usable non-turbo (cfg 6, 20–40 steps, DPM++ 2M SDE Karras) for max polish at 3×
cost. Community consensus: DreamShaper XL is the go-to for fantasy/concept art (our
genre); candidates to audition later: Juggernaut XL Ragnarok (all-around),
ZavyChromaXL (fantasy-artistic).

## Launch plan — POWERS OF ZEN (named 2026-07-24; @powersofzen verified free on YT, no
search footprint on TikTok/IG)

Platform reality (researched 2026-07-24): ALL three official APIs gate public posting
behind audits — TikTok Content Posting API posts SELF_ONLY until audit (~1-2 wks);
YouTube Data API uploads locked PRIVATE for unverified projects until audit; Instagram
Graph API needs Business acct + FB Page + app review (2-4 wks). Therefore:

- **Phase 1 posting = Claude-driven Chrome automation** (Phil pre-approved): Windows
  Chrome with a dedicated "PowersOfZen" profile (logged into all 3), launched with
  --remote-debugging-port; WSL drives it via CDP (playwright). Human-ish cadence,
  1 post/day/platform to start. MUST tick each platform's AI-generated-content
  disclosure. Manual phone fallback if bot-detection bites.
- **In parallel**: submit TikTok + YouTube API audits (privacy policy page + demo
  video needed) so posting graduates to clean APIs later.

Account-day checklist (needs Phil present for phone/2FA):
1. Create powersofzen@gmail.com — identity anchor for everything.
2. YouTube channel "Powers of Zen", handle @powersofzen.
3. TikTok @powersofzen; Instagram @powersofzen (set Creator/Business for analytics).
4. Shared branding: avatar + banner (candidate: Amos orb or a "10ᶻ" mark), bio
   (candidate: "the universe at every size — hit ▶ and breathe"), cross-links.
5. Chrome profile setup + start_chrome_debug.sh (tmux pattern like ComfyUI).
6. Build outbox/ + posting driver + per-platform caption/hashtag generator; first
   post = full ladder (thesis-statement video).

PRODUCTION LIST (locked 2026-07-26): EXCELLENT — cosmic_scales TURBO, iris_observatory DS,
night_bloom DS, alexandria DS, black_hole TURBO. VERY GOOD — midnight_kitchen DS,
tide_of_life DS, food_chain DS, dollhouse DS, snowfall TURBO. Ten ready.

RENDER QUEUE (fixes staged, render later — no rendering tonight per Phil):
1. mineral_heart --model ds  (star_forge de-flaked: round molten sun — Phil prefers DS,
   turbo "too generic"; blocked on this fix)
2. cartographer --model ds   (study/desk declared empty — DS painted a scholar into the
   final seconds; turbo not as good)
3. skyfog (rewritten: point targets per register, kettle-spout steam, single lighthouse
   mention) — both models
4. antenna_ball (reworked: 6 registers, ball→planet gag now the mid-video wrap via
   lacquer-bead planet) — both models
Also noted: cosmic_scales DS flora reads as Christmas tree + odd seam (moot — turbo chosen);
vary cameo mascots across videos (Belle is in everything so far).

POSTING DOCTRINE (Phil, 2026-07-26): dive-in is the preferred viewing cut. Post
pattern: dive-in, dive-in, zoom-out, repeat (every 3rd post = zoom-out; Phil may
flag which videos suit zoom-out). Order: alternate EXCELLENT with VERY GOOD until
excellents run out, then continue with very-goods. First batch = 10-12 posts,
finalized only after Phil rules on the five re-renders (full_ladder, cartographer,
mineral_heart, night_bloom, snowfall). Then: account setup (TikTok, YT Shorts, IG).

Pre-launch polish decision: masters are 576×1024; consider 2x upscale to 1152×2048
at assembly (cheap ffmpeg lanczos, or Ultimate Upscale pass) since platforms prefer
1080×1920. Mascot find-the-sprite contest: deferred (Phil), sprites stay subtle.

## Agent team (built incrementally, reusing autonomy_dev patterns)

- **Creative Director** — owns intensity, pacing, hooks; picks each video's journey concept.
- **World Builder** — invents the dive: which worlds, what order, what morphs into what;
  sprinkles loose-science awe where it heightens the trip.
- **Production** — runs the pipeline; LLM only for prompt-schedule crafting, rest is code.
- **Marketing Director** — captions/hashtags/sound selection/posting time; consumes
  analytics, feeds learnings back.
- **QC Agent** — phase 3; trained on Phil's accept/reject decisions.

## Phases

- **Phase 0 — pipeline proof** *(current)*: one mesmerizing 10–15s looping dive, end-to-end
  by hand. Milestones: (a) ComfyUI up + zoom-engine nodes installed and evaluated;
  (b) first feedback-zoom test clip; (c) prompt-scheduled morph journey with loop seam +
  audio, Phil reviews.
- **Phase 1 — production line**: agent roles wrapped around the pipeline; concept-in →
  outbox-out; accounts created; first posts (manual). Try Wan 2.2 / LTX-2 hero shots.
- **Phase 2 — feedback loop**: analytics (YouTube API free; TikTok manual/CSV); Marketing
  agent makes evidence-based calls (length, hooks, sounds, cadence, narration A/B).
- **Phase 3 — autonomy**: QC agent, scheduled runs, auto-post to YouTube; Phil spot-checks.
  Expand formats beyond the zoom if data warrants.

## Environment facts (verified 2026-07-22)

- Project home: `/mnt/c/Users/Phil/zoomer` (moved from /root/zoomer same day).
- WSL2, node v22.22.2, python 3.12 (requests ✓, PIL ✗ — not yet installed).
- ffmpeg: Windows-side via winget, callable from WSL:
  `/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe`
- Ollama on Windows host, reachable from WSL at localhost:11434 (was 192.168.68.1; WSL host IP drifts — poster.py auto-detects) (~15 models incl. deepseek-r1, qwen3.6:27b).
- ComfyUI: Windows install at `/mnt/c/Users/Phil/ComfyUI`, started via
  `/mnt/c/Users/Phil/start_comfyui.sh` (tmux session `comfy`); **API reachable from WSL at
  `http://localhost:8188`** (v0.22.0, Windows box has 64GB RAM). Checkpoints available:
  `FLUX1\flux1-schnell-fp8.safetensors`, `SDXL-TURBO\sd_xl_turbo_1.0_fp16.safetensors`,
  `dreamshaperXL.safetensors`. No video/zoom custom nodes yet (hand-rolled feedback loop
  via API may not need them).
- GPU: RTX 3080 10GB — SDXL-Turbo feedback zoom comfortably; Wan 2.2 5B FP8 / LTX-2 NVFP8 feasible.

## END-TO-END ARCHITECTURE (designed 2026-07-27, post-launch) — the plan of record

### The cost lesson (why the tiering below exists)
Making a video is CHEAP: the expensive work (GPU rendering) happens OUTSIDE any model's
context — Claude issues a few shell commands and sits idle. Posting via browser is
EXPENSIVE: the expensive work (reading screenshots to decide clicks) happens INSIDE
the model context, and screenshots (~1.5–2k tokens each) ACCUMULATE — every turn
re-sends all prior screenshots, so cost compounds ~quadratically. One 3-platform
hand-driven posting run ≈ burned Phil's whole Fable session (2026-07-27). Rule that
falls out: **put work where it's cheap; keep images out of the accumulating context.**

Corollary (Phil's catch): a Haiku SUBAGENT reading a screenshot returns only ~10 words
of text to the main context — the image stays in the subagent's context and never
accumulates. That alone would cut posting cost ~20x even before going local. Use
subagent-delegated vision any time screenshots would otherwise pile up.

### Three tiers — put work where it's cheap
- **Frontier model (Opus/Fable) — rare, creative, judgment:** journey composition
  (the novelty engine — worth the cost), title writing, reading analytics for strategy,
  rescuing the harness when a site changes its flow. A few calls/week.
- **Local model (Ollama VLM) — frequent, mechanical, verifiable:** the posting harness's
  sanity checks, QC of rendered frames (collapse / face-intrusion / counter-present),
  best-effort view-count reading. Runs constantly, costs only electricity. PREFER DOM/
  text assertions (free, instant, no model) over vision — the VLM is a fallback sanity
  layer called only a handful of times per post, so even ~10 tok/s is fine.
- **No model at all — pure code:** render pipeline (already), scheduling, queue/state
  files, dashboard. Most of the system. Free + deterministic.

### Local VLM candidates (researched 2026-07-27; RTX 3080 10GB; pull when building harness)
Checks are simple ("upload finished?", "which dialog?", "green check present?") and — key —
Qwen3-VL is GUI-AWARE (trained to recognize UI elements + button functions), so it fits
posting checks perfectly. Current line is **Qwen3-VL** (NOT 2.5 — I was behind), Apache-2.0,
Ollama-native, sizes 2B/4B/8B/30B/32B/235B, 256K context.
- **PRIMARY: Qwen3-VL-4B** — best accuracy-per-VRAM; wins clearly on document/UI reading,
  fits 10GB with room to spare, fast enough. `ollama pull qwen3-vl:4b`.
- **FALLBACK for pure yes/no: Moondream2** (~2B) — tiny/fast for "is X present" glances.
- **If we want max OCR muscle:** Qwen3-VL-8B or MiniCPM-V 4.5 (8B) — both fit quantized
  on 10GB (Phil runs ~20B quantized fine), slower but strongest at dense text.
- InternVL3.5 is the overall benchmark leader but bigger/heavier than we need here.
Minimize calls: DOM/text assertions first (free), VLM only for genuine visual checks.
Download+validate a couple (4B + Moondream) when we build; ~10–20 min of pulls.

### The pipeline (format-agnostic — only the renderer is zoom-specific)
`compose → render → QC → review → post → measure`. Each stage reads/writes ONE state
store (pipeline.json or SQLite) so nothing hides in a script. When we branch to other
video styles later, only the renderer changes; the spine is reused.

1. **Journey Composer** (frontier, occasional) — generates candidate journeys from
   VARIATIONS.md into "pending review".
2. **Journey review** (Phil, optional via dashboard) — skim/edit/approve/reject, or
   wave through. Phil may also hand-write journeys.
3. **Renderer** (code + GPU) — approved journeys → turbo+ds, phase-shifted, both cuts.
4. **QC** (local VLM) — frame checks; flags questionable videos for Phil.
5. **Phil review** (dashboard) — approve videos into the post queue (approval gate).
6. **Poster** (LOCAL harness) — posts approved videos on schedule via the zen-post
   playbook. Fail-loud: after each step assert expected next state; on failure,
   screenshot + halt THAT platform + raise a dashboard flag + continue others.
7. **Analytics** (local/code) — YouTube via free Data API (clean); TikTok/IG via
   periodic page-scrape (best-effort). Feeds dashboard.

### Dashboard (Streamlit — like autonomy_dev's; local, free, reads the state store)
Four panels: journeys pending review · videos pending Phil's review · post queue
(approved+scheduled, with okayed caption) · posted (with 3-platform view counts).

### CAPTION DOCTRINE (Phil, 2026-07-27)
Caption = the TITLE line only (NO separate marketing prose — the old multi-sentence
captions were rejected as "awful"). Minimal hashtags (Phil dislikes them, tolerates a
few). NOTHING posts without Phil's approval — queue.json has `approved: false` per post;
Phil flips to true (or approves a range) before the harness posts.

### AUTO-POST STATUS
RESUMED — the hourly post_gate posts on a 19h cadence (see scripts/SCHEDULER.md).
(Originally halted 2026-07-27 — was burning premium budget + would post unapproved —
until the LOCAL harness existed AND posts were Phil-approved.) Cold-start underperformance
of first posts is normal, not a content verdict. Seeding to r/oddlysatisfying /
r/interestingasfuck can prime reach.

### CAPTION DOCTRINE (updated 2026-07-27 — ban RETRACTED)
Captions are welcome (TikTok viewers expect them); Phil doesn't have to love them but they
stay. Descriptive title-style line, not multi-sentence marketing prose. ALWAYS include
**#fyp** (added to all queued; note: its algorithmic effect is largely myth — TikTok keys
off relevant/specific tags, not #fyp — but it's harmless, free, and some users browse it,
so no reason to omit). Composer DRAFTS the caption at journey-compose time (knows the
concept); Phil FINALIZES/approves it at video review (after seeing the render). Approval
gate (`approved:false->true`) still required before any post.

### AUDIO / MUSIC (priority RAISED 2026-07-27 — Phil: it's part of video QUALITY, not just discovery)
Silent videos underperform; a sound is both a discovery lever AND core to how the video
FEELS. Music must match the journey's rhythm — and not just BPM but INTENSITY OVER TIME
matched to the arrive→look→plunge grammar: build/intensify through the PLUNGE, ease/chill
during the HOVER (arrival + look beats). We're unusually well-suited because our timing is
fully parametric (sec_per_scale) and the engine already emits per-phase beats + decade
PULSE events — so we can hand the music generator our exact per-phase timeline and get
dynamics that rise and fall WITH the dive. Tiers:
1. **Trending sound at post time** (near-zero work): quick discovery win, loose match.
   Fine as a stopgap the moment posting is automated.
2. **Beat-locked track** (moderate): track at known BPM, snap register transitions +
   counter-pulses to beats (librosa).
3. **PHASE-DYNAMIC local generation** (the real target — Phil wants to move here fast):
   generate a track conditioned on our per-phase intensity timeline. **MusiConGen**
   (MusicGen + BPM/chord conditioning) is the local $0 fit; LoopGen/VampNet give LOOPABLE
   audio (matches our looping videos); Google Lyria via API is the hosted alt. Feed the
   generator the arrive/look/plunge segment map so intensity tracks the zoom.
Recommendation: tier-1 stopgap when posting goes live, but move to tier 3 SOON — it's a
quality feature, not a nice-to-have. Slots in after the posting harness + dashboard.

### PRODUCTION FOLDER WORKFLOW (standard, 2026-07-27)
When Phil marks a video ready for production, run `python3 scripts/promote.py <journey>
<turbo|ds>`. It MOVES the chosen model's cuts (zoom-out + dive-in) from review/ into
`production/`, and the OTHER model's counterpart cuts into `production_alternates/`.
Result: review/ holds only in-progress/unreviewed videos; production/ is the postable
set (queue.json `file` points here); production_alternates/ keeps the alt-model version
in case we want to A/B or swap. Both folders gitignored. Newly rendered videos still land
in review/ first (fix_batch.sh etc.), promoted only after Phil's OK. The 10-video launch
set is already promoted.

### CAMEO DOCTRINE — STANDARD GOING FORWARD (2026-07-27)
EVERY new video gets a mascot cameo, scale-matched to a register, size ≥0.12 so it's
actually visible (smaller = invisible = pointless). Full-cast rotation: don't reuse a
mascot until the cast is exhausted. Video WITH a visible cameo → find-the-character
caption ("find <Name>, comment the timestamp", future contest hook); video without →
normal descriptive caption. Do NOT regenerate already-released videos just to add a cameo.
May need tuning after this round (size/position/denoise so the face survives) — getting it
consistent matters even if not perfect immediately.

### Build order
(1) local posting harness — stops the bleeding, pure code (cheap to build even though
using Claude to post isn't). (2) pipeline state store + Streamlit dashboard + approval
flow. (3) Journey Composer (frontier) filling the pending-review queue. (4) local QC +
view-count collection. Keep stages format-agnostic for future video styles.

## OPERATING SYSTEM — dashboard + data model + scheduler (designed 2026-07-27)

**Source of truth = two files (everything reads/writes these):**
- `pipeline.json` — state of every video: {journey, model, cut(divein|zoomout), file,
  title, caption(editable), yt_title, yt_desc, state, per-platform results+URLs, ts}.
  state ∈ rendered → pending_review → approved/queued → live → failed. Evolves today's
  outbox/queue.json. Dashboard writes it, scheduler picks from it, poster.py updates it.
- `telemetry.jsonl` — append-only events {ts, event(post|post_fail|render|render_fail|flag),
  journey, platform, detail}. Dashboard activity/failures feed. (flags.jsonl folds in here.)

**Dashboard (Streamlit, local, free — like autonomy_dev's):** panels —
- Queue: preview · cut · model · title · EDITABLE caption (writes to pipeline.json) · sched time
- Review: rendered videos awaiting Phil's yes → approve moves to Queue
- Live: posted + 3 platform links (view-count slot now FILLED — views/likes/comments shown
  per video)
- Journeys pending: (once composer exists) drafts to skim/edit/approve pre-render
- Telemetry: recent activity, failed posts, failed renders, flags

**Scheduler — WINDOWS-SIDE (Phil's choice 2026-07-27; his autonomy was a Windows script,
more stable than WSL cron/daemon which idles out). Posting: the hourly PowersOfZen-postgate
task fires `scripts/post_gate.py` (the legacy 8am/6pm tasks delegate to the same gate) —
scripts/SCHEDULER.md is the authority on the tasks.
COST-CRITICAL: NO Claude in the loop — poster.py is standalone (reads pipeline.json, posts
next approved, writes telemetry), always-on cost = electricity only. Claude appears ONLY for
caption-writing + journey composition. Task Scheduler also wakes WSL (solves idle-shutdown)
and survives reboots. Phase-2 hook: if queue low → ping composer.

**Folder rule (corrected):** production/ = ONLY the exact postable file (chosen cut of chosen
model) for queued/live videos. production_alternates/ = other model (both cuts) + the OTHER
cut of the chosen model. Fix promote.py to take cut direction (currently over-includes both
cuts of chosen model).

**View counts:** SHIPPED 2026-08-13 — ig_stats.py trusted-CDP hover scrape, auto-runs after
every post. EXTENDED 2026-08-22: also scheduled 12:00 + 00:00 (PowersOfZen-igstats task —
Phil: don't wait 19h between counts); unattended-hardened (Chrome self-heal, locks,
skip-while-posting); grid-virtualization coverage fix (tag-while-scrolling, 36/43 reels vs
21–28 before); dashboard Live tab = followers header + top-5-by-qscore strip + per-video
counts. Era analysis in ig_analyze ("posted era" group): the 08-14+ rethink package
validated on reach, engagement, and follower growth — numbers in the audience-stats skill.

**Harness polish:** click Done/Close after each post so Phil lands back on the videos list.

**Build order:** (1) promote.py cut-fix + harness Done-click (small). (2) pipeline.json +
telemetry.jsonl data model (fold in queue.json/flags.jsonl). (3) Streamlit dashboard w/
editable captions. (4) local scheduler (cron → poster.py). (5) later: composer, view counts.

## Open questions (park until relevant)

- Local VLM selection + accuracy validation (does it reliably read the post-flow UIs?).
- Trending-audio workflow (added at post time; which platform, how chosen).
- Whether TikTok/YouTube API audits are worth pursuing at volume (would replace the
  browser harness with clean APIs for those two).
- 2x upscale decision (576×1024 masters → 1152×2048; platforms prefer 1080×1920).

---

## 2026-07-28 session — music system, poster hardening, seam still unsolved

### Music system (BUILT, shipping)
Three-layer method, "the model writes the music, we only place it":
- **Generate** (`engine/music.py`): ComfyUI-native **ACE-Step 1.5 turbo** (2B-class, fits the
  10GB 3080; UNETLoader → ModelSamplingAuraFlow shift=3 → KSampler steps=8/cfg=1 euler/simple,
  DualCLIPLoader type="ace" qwen_0.6b+1.7b, VAELoader ace_1.5_vae). ~10-20s/track. Stable Audio
  Open also downloaded but ACE-Step is the pick.
- **Tempo-lock + align** (`scripts/align.py`): generate at bpm so one bar = one morph interval,
  then shift/micro-stretch the finished track so its OWN onset accents sit on the morphs. No
  overlay. "lock" score = peak/mean (7x+ good). Morph grid from `score.schedule_morphs` (exact,
  inverts the phase_shift rotation — no detection). Anacrusis-forward prompt (weak pickup →
  strong downbeat on every bar, "never sparse"). `scripts/score.py` = the older overlay
  (synthesized soft-pad anacrusis lead) — now the FALLBACK.
- **Music-review stage** (`scripts/music_gen.py` + dashboard 🎵 Music panel): per journey,
  derive bpm, generate 5 mood-varied candidates (warm/glassy/deep/tender/choir) with the
  journey's `music_theme` (scene vibe — underwater/cosmic/library/wintry) baked in, align each,
  record under pipeline `v["music"]`. Phil auditions → Choose promotes it into the posting slot.
  `music_theme`/`music_key` live in each journey JSON, editable in Review + Music panels; Music
  panel has a 🔄 Regenerate button. DOCTRINE (Phil): sync matters more than model; mandate the
  anacrusis (it's a RULE, not per-video composition); Phil prefers STRONG beats (clearer match);
  don't track lead pitch to the zoom scale.

### Poster hardened (all real fixes tonight; validated live)
- **YouTube**: `/upload` bounces to the Studio content list for this channel → open the upload
  dialog via **Create → "Upload videos"**. Title field can exist before it's editable → retry
  set_text. night_bloom now live on YT.
- **TikTok**: videos with music trigger a **"Music copyright check"**; clicking Post while it
  runs pops "check incomplete — Post now stops the check", and clicking Post now silently drops
  the post. FIX: WAIT for the check (cancel the modal, retry) — never stop it.
- **Instagram**: `el.click()` is ignored by IG's React for Next/Share/Done → `_ig_click` now
  does a SYNTHESIZED press/release at the button center. (This is why captions weren't saving.)
- **DISCIPLINE**: the poster's "posted" return is NOT proof — verify against the live page
  (studio list / public profile). TikTok gave repeated false-positives tonight.

### OPEN — TikTok drops with-music posts
night_bloom publishes to TikTok (publish dialog shows) then **vanishes** — not in studio, not
on the public profile, no removal notice. Reproduced posting BY HAND → it's TikTok-side, not
the poster. Likely custom AI audio on a brand-new account (1 follower). Next: post one SILENT
version as a clean test (sticks → it's the music → use a TikTok-licensed sound for TikTok,
keep custom music for IG/YouTube — ties to the trending-sound idea in journeys/VARIATIONS.md).

### THE SEAM IS UNSOLVED — next up: ControlNet (Phil's long-standing idea)
The ugly loop cut is NOT fixed. Current state: dive.py sets the last frame = a hard COPY of
frame 0; grammar ramps the loop-tail denoise down (0.18→0.12 as of tonight) and journeys are
authored so the last register's `next_target` names the first world — but mismatched worlds
still HARD-CUT. A denoise nudge + authoring is not a mechanism.
**PLAN:** build a real seam mechanism with **ControlNet** so the closing frames genuinely morph
INTO frame 0 (e.g. condition the last L frames toward the frame-0 image via ControlNet, or a
true generated crossfade). **Prototype on ISOLATED seam generations first** — take a near-end
frame + frame 0 and generate just the ~L transition frames, iterate fast, DON'T render whole
videos each attempt. Once the transition looks seamless, wire it into dive.py's exact_loop tail.
Only then re-render journeys. (Six journeys are authored + waiting; cosmic_scales_remix &
circuit_city turbo rendered raw with ugly seams — throwaway until the seam works.)

---

## THE SEAM — SOLVED (2026-07-29). Plan of record; don't lose this.

The loop seam (last frame → frame 0 wrap) is now handled by a repeatable mechanism, plus a
structural authoring fix so future videos barely need it. Two pieces:

### A. Structural fix — self-similar loop target (engine/grammar.py)
Root cause of ugly seams: the first world was described TWICE with different words — frame 0
from `regs[0].interior`, the last frame from a hand-authored last-register `next_target` that
DRIFTED (food_chain's last target was "a golden cove" — no heron; frame 0 was heron shallows).
Two descriptions → two different images → a big gap at the loop.
FIX: the last register now AUTO-derives its loop target from `regs[0]` (`loop_target` if set,
else `interior`). So the last frame plunges toward the first world in the *same words* frame 0
uses → first/last render alike → tiny seam gap. Authoring rule (also in the dive-video skill):
make `regs[0].interior` a strong establishing description, pin a consistent viewpoint, and the
last register must genuinely CONTAIN the first world (heron stands in the landscape we dive into).

### B. End-of-video mechanism (scripts/repair_seam.py; to be folded into dive.py's loop tail)
Over the last L (~24) frames, in order:
  1. NATURAL DIVE — keep zooming with the last-register prompt (the world grows, alive; frame 0
     is NEVER fed back through the zoom, so it can't scale into a frozen photo).
  2. PALETTE-MATCH — ramp each frame's palette toward frame 0's channel stats (the missing
     last→first color blend; fixed food_chain's green-garden vs warm-brass clash).
  3. MORPH (last `morph_frames`, default 12) — gradual pixel-blend toward frame 0, **auto-scaled
     to the measured gap** (tiny for a same-room return → gentle, zoom-preserving like cosmic;
     strong to bridge a far world like food_chain). Morph frames are also GENERATED with a light
     depth-ControlNet toward frame 0 so they stay alive/distinct, not a static blend.
  4. NO HARD-COPY of frame 0 at the end. dive.py's old `img = frame0.copy()` created 3 near-
     identical frames (morph≈F0, copy=F0, head=F0) = a FREEZE at the loop. The last frame is now
     a generated ≈frame 0; the wrap is one normal dive step.
  5. Optional `--cut-tail N` — last N morph frames keep zooming (moving cut to frame 0) instead
     of converging to a static frame 0, for cases where the still-frame-0 "appears static" reads
     badly. (Tradeoff: a small cut instead of a hold; for a big-gap render it can over-zoom.)

### What we tried and REJECTED (so we don't repeat it)
- PASTE / loop_composite (grow a shrunk frame 0 in the center): keeps zoom but "zoom into a
  frozen photo" — Phil rejected.
- Full-frame cross-fade to static frame 0: content converges but the ZOOM STOPS (frame becomes a
  still) — the "velocity take-up" hitch.
- IRIS (aperture-open frame 0 at native scale): opens on a frozen image; and it hid the zoom.
- Natural dive + slow aperture: aperture revealed the EXACT frame 0 over a different-palette dive
  → jarring, and no visible zoom.
The winner is the natural-dive + palette + gap-scaled generated morph (no hard copy). Approved on
cosmic (v11) and food_chain (v3/v4).

### The fundamental limit (why "perfect" needs authoring, not just repair)
A pure zoom-IN cannot smoothly arrive at a WIDER establishing frame 0 — the motion would have to
reverse. Converging to a static frame 0 always leaves either a tiny static moment or a small cut.
The real cure is CONTENT self-similarity (Droste: the deepest point IS frame 0's world at the next
scale) — that's what section A pushes toward. Repair bridges the residual; authoring shrinks it.

### Frames, music, tooling
- KEEP the generation frames: `output/<name>/vN/build/frames/` (repair reuses them; the engine is
  a feedback chain whose only heavy state is the previous frame — seed/zoom/denoise/drift are
  deterministic functions of the frame index, so we can resume at the seam and regenerate only ~L
  frames, no full re-render).
- repair_seam is NON-DESTRUCTIVE: source vN untouched; repair lands in a fresh vN with the original
  seam frames kept in `build/frames_orig_seam/`; emits before/after `seam_preview_*` loop clips.
- MUSIC is safe: the repair only touches the last ~L frames; the morph GRID (register boundaries
  the music locks to) is unchanged, so re-aligning the chosen track reproduces the same lock
  (verified food_chain "deep" = 11.54× before and after, stretch 1.0000). NO frames are added, so
  the music grid is never disturbed.
- NEXT: fold mechanism B into engine/dive.py's exact_loop tail (replace the loop_composite/hard-
  copy tail) so every new render ends this way; then re-render the self-similar journeys.

---

## KNOWN ISSUE — "object zoom" (space→planet transitions) (noted 2026-07-29)

**Symptom (Phil):** going from space to a planetary surface, instead of zooming INTO one planet
that swells until we see its landscapes and descend into one — planets FLASH BY, the swirly
space background MORPHS into a landscape, and the planets shrink/dissolve. Most pronounced at
space→planet; a softer version happens at any "zoom into a small discrete object" boundary.

**Root cause:** the feedback engine zooms into whatever fills the frame CENTER and regenerates
it — great for ENVIRONMENTS (interior fills the frame, cropping reveals more of it), broken for a
DISCRETE OBJECT that is small and must grow. Two compounding failures:
  1. The object doesn't persist/grow. TEMPLATE_TRAVEL ("one single tiny {target} ... very far
     away ... vast {interior} in every direction") makes the model REPAINT a fresh tiny planet
     every frame; the center-crop enlarges the prior frame but the model re-invents new tiny
     planets (and drift can slide the crop off it) → many planets flashing by, none swelling.
     High travel denoise worsens the re-invention.
  2. Sphere→surface is a PERSPECTIVE change, not an optical zoom. Orbital sphere vs standing on
     terrain can't be reached by cropping the center — it's a representational morph, so the last
     step always reads as "space morphs into landscape."

**Difficulty: moderate.** Not trivially solved (a truly filmic orbital descent is hard for a
regenerating feedback chain), but levers should move it from "wrong" to "good." Try later, in
order of expected payoff (all cheap, iterate-and-see like the seam):
  1. GRAMMAR — for "zoom into a discrete celestial/object target," swap the travel wording:
     ONE object DEAD CENTER, swelling to fill the view; drop "tiny / very far away / in every
     direction"; add "the only one, no other planets, its curved edge growing past the frame."
     (Possibly a per-register flag like "approach":"object" selecting an object-approach template.)
  2. ENGINE — during object-approach beats, KILL drift (pin the crop center on the object) and
     LOWER denoise (so the crop-zoom GROWS the existing planet instead of repainting new ones).
  3. GRAMMAR — add a DESCENT beat for celestial→surface: sphere fills view → curved horizon
     flattens → descend through atmosphere/clouds → surface rushes up. Gives a continuous path
     through the perspective wall instead of one abrupt morph.
  4. AUTHORING — where possible prefer true environment-zooms; when a planet is needed, arrive
     already low over its terrain (surface as the filling "interior") rather than from orbit.
Recommendation: 1+2 first (centered/persistent/low-denoise growth — likely the biggest win),
then 3 for the perspective wall. Do NOT touch grammar.py/dive.py mid-batch (a live render
re-imports per process; edits would make the batch inconsistent).

---

## ENGINE 2.0 — object-zoom targeting (design locked with Phil 2026-07-30)

The core goal: make it read as ONE CONTINUOUS ZOOM into a specific object, not a morph into
whatever's center. Design agreed (still planning; prototype-first before any build):

**Root mechanism to fix:** the engine always zooms toward a FIXED center (`cx,cy=0.5`+drift) and
re-diffuses at constant denoise — so for a discrete object (planet, one animal, geode) it marches
into the background and re-hallucinates it into the next world. Works for environments, fails for
objects. The fix adds a *targeting brain* to hardware we ALREADY have: `zoom_transform` already
takes `cx,cy` (zoom toward any point) and `build_workflow` already supports `SetLatentNoiseMask`.

**The loop:** establish wide varied scene (many objects) → LOCATE the target object (box/mask) →
pan-zoom toward ITS center over the plunge beats → hold its identity with a light ControlNet while
still fully regenerating every frame → arrive at its surface → recurse (find the next sub-target).
The mask does triple duty: direction, persistence, arrival-detection (mask fills frame = arrived).

**Phil's two guardrails (critical):**
- KEEP MORPH-ON-THE-BEAT. The cool thing is the morph landing on the beat, NOT the zoom (velocity
  changes are too subtle with our soft beats). So: keep the INTENTIONAL morph at the arrival beat
  (already the arrival_denoise_boost + prompt-blend at register boundaries, on the beat, music-
  locked) and kill only the ACCIDENTAL morph (center-into-background between beats). Sensible zoom
  while approaching → morph pops on the arrival beat. Do NOT go all the way to pure static zoom.
- NEVER STATIC / PASTED. The seam-repair pasted frame-0 and froze — do NOT repeat that at every
  scale. The engine already regenerates every frame (img2img); KEEP that. Persistence = a light
  ControlNet (depth/soft-edge) from the previous frame as a STRUCTURAL WHISPER that holds the
  object's identity/layout while pixels are fully re-diffused each frame (alive, not frozen). CN
  strength is a knob to back off if it ever looks static. Prototype must prove BOTH: object grows
  (not flies by) AND stays alive frame-to-frame.

**Decisions:** DETECT the target (not compose) — fits "busy varied scene, zoom into one of many";
detect a FEW times per register (not per frame; cheap). The "semantic seam" (the one weird warp
every journey has — not always quark→cosmos; e.g. cellular→planetary) is NOT special-cased — it's
just another register transition the journey-writer blends creatively, with its own on-beat morph.

**Journeys: NO rewrite needed.** The existing `next_target` already names what we zoom into → the
compiler derives the detector query from it. Only optional addition: a "which one" selector
(e.g. `target_pick: "the largest"`) for ambiguous scenes. Old journeys keep working.

**Prereq / open:** NO detector installed yet (ComfyUI has no GroundingDINO/SAM/Florence nodes; no
local torch/cv2; Ollama gateway was down at check time). First real step = get a detector on the
3080 — recommend **Florence-2** (one small model does open-vocab detection + phrase-grounding,
great on a 3080, has a ComfyUI node) or GroundingDINO+SAM. Then the POC: box "the planet" on real
stormglass frames + a short targeted-zoom-with-CN clip → eyeball grows-and-stays-alive.

PARKED for later (Phil): moving/dynamic worlds (motion IN the environment); dynamic camera (turn
corners, whip around a planet — the old big sinusoid was jarring; a tasteful version later).

### Engine-2.0 BUILD STATUS (2026-07-30)
DONE today: (1) Florence-2 detector installed (ComfyUI-Florence2, Kijai) — engine/detect.py
localizes the target via referring_expression_segmentation + a SHORT visual phrase → clean object
mask → connected-component boxes (fractional). Long/abstract phrases degenerate to full-frame;
"the round banded planet" nails it. (2) POC validated (scripts/zoom_probe.py): on stormglass
frame 233 the planet CENTERS (0.24,0.34→0.50,0.50) and GROWS (area 0.03→0.55) staying alive
(fully regenerated) — both guardrails met. (3) Integrated into engine: grammar emits a per-frame
`approach` schedule from a register's `target_phrase`; dive.build_workflow gained depth-CN
(ctrl_image/cn_strength); the loop detects+aims cx,cy+depth-CN on approach frames. CN 0.45,
detect every approach frame. First full render: stormglass with target_phrase ONLY on the star
register (planet) — proves the mechanism in-engine; other levels still do old center-morph.

### FORMAT 2.0 — zoom-vs-seam + logical containment (Phil, 2026-07-30) — NOT BUILT, design notes
Reading all 20 journeys revealed the core structural gap (half the problem is journey/format, not
the engine). Two things:

1. **Every transition is one of TWO kinds, and the format doesn't distinguish them — that's the
   timing bug.**
   - **ZOOM-IN** (into a CONTAINED object): small exp step (~2-4/register, the ×10). e.g. scroll→
     glyph, cell→protein, ladybug→antenna-tip. TAKES TIME — a targeted approach (gets target_phrase).
   - **SEAM / MORPH-BIT** (the semantic jump where a thing BECOMES a far-scale world): a LARGE exp
     jump. e.g. atom(-10)→planet(7) [+17], quark(-15)→cosmos(26) [+41], antenna-tip(-2.6)→planet(7)
     [+9.6], ice-lattice(-8)→peaks(4.5). This should be INSTANT — a morph ON THE BEAT, NO zoom time
     (you can't optically zoom an atom into the cosmos). Currently it gets a full register of slow
     zoom → the "weird timing" + "background opens into the next level" morph.
   KEY: the exp DISCONTINUITY already encodes which is which (big jump = seam). So we can derive it,
   but better to make it EXPLICIT per transition (`kind: zoom|seam`). Ties to beat-alignment: seams
   = the morph-on-beat (instant), zooms = the sustained approach (integer bars).

2. **Logical containment must be REQUIRED, not hoped for.** Fable wrote most journeys as genuine
   object-in-object chains (alexandria/cartographer/cosmic_scales/tide_of_life are good: library→
   scroll→glyph→ink→fibers→molecule→atom→[SEAM]→planet→delta→city→library, ONE clean seam each).
   But nothing enforced it, so: (a) targeting isn't applied → multiple objects at a level (the
   antenna_ball "multiple ladybugs" — its concept is right: meadow→ladybug→antenna TIP→[SEAM: tip
   BECOMES planet]→descend clouds→canopy→meadow); (b) some next_targets are vague on WHERE the
   object is (need the short target_phrase); (c) seams unmarked → slow-zoomed.

**Format 2.0 (to design):** per register — the ZOOM target (a contained object) with a rich SCENE
description + a short `target_phrase` for detection; an explicit `kind` (zoom vs seam) so seams are
instant on-beat morphs; a richer description of what the interior BECOMES at the next scale.
Journey GENERATOR (the two-mode one — theme-driven + describe-it-yourself) must ENFORCE the
containment chain and mark seams. This + universal targeting is the full object-zoom fix; today's
engine work is the mechanism, this is the intentionality. The authoring doctrine is now written
up as .claude/skills/journey-composer/SKILL.md (draft, iterated with Phil 2026-07-30) — the schema
(rich `scene` + rich emerging `target` + tight `target_phrase`; `kind` zoom|seam; `dur` in BEATS
power-of-two 0.5|1|2|4; optional `target_pick`), the containment law, prominent-point emergence
(engine selects one-among-many + commits), and the diversity rules. NO backward-compat: we rewrite
journeys to the new skill (old field names interior/next_target/sec retired; live videos stay as
already rendered). VARIATIONS.md needs a BIG expansion (generator fuel).

**PACING = power-of-two beats (Phil 2026-07-30).** `dur` in beats, power-of-two only (0.5|1|2|4) so
every morph lands on the beat and the STRONG downbeat ("bum-bum", led by the anacrusis we keep from
engine 1) carries the main morphs. Whiz fast scales at 1 beat each (4 fill a bar); linger at 2-4.
Seam = instant on-beat morph, dur 1. This is the disciplined version of the beat-alignment note.

**RHYTHM-DRIVEN COMPOSITION + beat-synced FX (Phil 2026-07-30, big future feature).** Because these
are rhythmic, compose the RHYTHM FIRST, then build BOTH video and audio to it. On NON-morph beats,
hit on-screen FLARES/EFFECTS synced to the drum/rhythm (drum hit → a flare or effect pops on a
thing on screen). Meshing video FX to the beat is a major cool-factor lever. Likely needs music-gen
changes to control rhythm + accents/effects. Keep the anacrusis + strong morph beats throughout.

---

## Journey generator — the last pipeline piece (Phil's notes 2026-07-30, build later/parallel)

Two capabilities wanted:
1. LOCALLY-GENERATED journeys (gemma/mistral etc.) — from scratch OR from a big DIVERSE THEME list
   (academia → pop culture → food → geography → culture → …). Diversity of journeys is the key.
2. Phil DESCRIBES a journey in natural language → translated into the JSON format (registers,
   interiors, next_targets, exponents CALCULATED, beat-aligned durations — see below).

**Beat-aligned durations (FORMAT CHANGE — ties engine+grammar+music together).** Today per-register
`sec` is arbitrary DECIMAL seconds → morphs land OFF beat, so the music can't lock cleanly (the
seamless-loop work relies on the video being an integer number of bars; it's currently integer
only by luck because all registers share one `sec`). Fix: express register duration in BARS/beats,
integer-quantized, so EVERY morph lands on a downbeat (beat 1 / beat 3 / …). This enables varied
pacing WITHOUT going off-beat: a "linger" scale = more bars (2, 4); "pass through fast / don't
pause" = fewer bars, or traverse several scales within a bar-aligned span. Always stay on beat —
that's the rule. Change the format if needed. (This is the structural version of "video = exact
integer bars" we discovered during the music-loop fix.)

---

## Dashboard start-frame + cover-frame marking (2026-07-29)

Video Review has a **start frame** marker (enter the seconds you paused the looping preview at,
🔎 preview to confirm, ✅ set → stored as `start_t`). On **Approve → Music** the video is
PHASE-SHIFTED to open at `start_t` (phase_shift.shift, in place, keeping a `*_preshift.mp4` so it
is re-derivable) BEFORE music is generated — and music_gen/align/score.schedule_morphs now take a
`shift_sec` so the track aligns to the shifted arrangement (the music may still micro-shift up to
a bar within that). Production has a **cover frame** marker (`cover_t`) — same mechanism, no
re-shift (video is locked by then).

TODO (poster, later): the poster currently lets YouTube/IG use the DEFAULT first frame as the
cover/thumbnail. Update poster.py to select the frame at `cover_t` as the cover image on each
platform (extract that frame, upload it as the custom thumbnail / cover) instead of the default.

---

## Captions, hashtags, GPU-gating, and pipeline polish (2026-07-29)

**Captioning is now formalized** (was: Claude wrote captions by hand at pipeline-entry time).
`scripts/caption.py` uses a LOCAL model (Ollama `mistral-small3.2:24b`, :11434) on the journey's
worlds to write FIVE caption options. The YouTube TITLE is NOT written separately — it's the
caption BODY (the descriptive line before the mascot question), i.e. a truncation of the caption
(that's how Phil has done it by hand). [TEXT-ONLY: qwen3-vl:4b was a reasoning model that returned
empty JSON; image-grounding via a working VLM (e.g. moondream) is a TODO]
so a video already HAS a caption by the time it's in Video Review. Model-agnostic (same caption
for DS/turbo; prefers DS frames). Dashboard Video Review shows the 5 options (picking one auto-fills
the caption + YT-title fields, no refresh) + a ✍ Generate button. `caption.py --all` captions
every review video missing one.
  - HASHTAGS: always-on brand tags (programmatic, appended): #powersofzen #oddlysatisfying
    #zoomer. **#fyp is DROPPED.** The model adds 3–4 JOURNEY-SPECIFIC tags per video. Tune the
    brand set in caption.py BRAND_TAGS.
  - Caption is GPU-heavy (VLM) → gated on `pipeline.gpu_busy()`; runs after the render batch.

**GPU gating** (`pipeline.gpu_busy()`): true while the GPU is actually under load — reads
nvidia-smi utilization (>=30%), works from Windows via wsl.exe. (Earlier it matched process
command lines via pgrep, but that falsely tripped on watcher/caption scripts whose command lines
merely mentioned dive.py, so the flag never cleared after a render; utilization is the true
signal and also catches the user's Steam game.) Music auto-gen on Approve→Music is skipped
when busy (Music tab shows a "GPU busy" note + Generate button). Same gate guards captioning.
TODO: also gate any future local-LLM journey-writing on it; the user's Steam game is the same
concern (a render pins the GPU — that's the frame-rate-drop question).

**Music on approve:** Approve→Music phase-shifts to the marked start frame (score/align/music_gen
take shift_sec) then auto-generates music IF the GPU is free, else waits for the Generate button.

**Render-batch integration TODO:** add a final `python3 scripts/caption.py --all` step to the
render batch (render_0729.sh) so captions are written automatically once rendering finishes and
the GPU frees up. (Don't edit a batch script while it's running.)

**Maybe later:** (a) INTELLIGENT default start frame — have a model pick a good opening frame
(stable macro-realm, mid-travel, on a beat) instead of Phil marking it by hand; give it candidate
frames and let it choose. (b) Possibly DROP turbo and render DS-only (caption/music are the same
either way) — leaning that way; decide after seeing the DS batch.

**CONFIRMED in a real render (stormglass DS, 2026-07-29):** star→gas-giant transition. No planet
renders during the star's travel/plunge beats (frames 220–230 are just corona); at the register
BOUNDARY (~frame 234) a planet flashes in, and frames 238–250 show MULTIPLE round bodies (ringed
planet + blue giant) coexisting while the background morphs to orange atmosphere — never one gas
giant swelling. So the object is not established during the approach; it pops in at the arrival
beat, and the model invents extra bodies. Confirms fix direction: object-approach template
(ONE centered body, swelling, "the only one, no other planets") + kill drift + lower denoise, so
the crop-zoom grows the SAME planet from far→full instead of re-inventing it at the boundary.

## STYLE is Layer 2 — pull it OUT of the journey composer (Phil 2026-07-30)
Engine-2.0 journeys (meadow/ladybug/lighthouse) drifted PHOTOREALISTIC because the composer
invents `style_suffix` per journey and reskins toward realism. Phil wants the shiny, AI-polished
DreamShaper eye-candy look the engine-1 cosmic videos had ("food for the masses"). Fix: the journey
composer should write CONTENT only (scenes/targets/pacing) and leave the LOOK to a separate, curated
STYLE step — a small deck of deliberate "shiny AI eye-candy" style presets (style_suffix + palette +
checkpoint) applied on top of a style-agnostic journey. Keeps the brand look consistent + intentional
(per the FORMAT/STYLE/JOURNEY three-layer model) instead of drifting to whatever a lighthouse "should"
look like. BUILT 2026-07-30: styles/deck.json (curated word-only looks: cosmic_gloss / crystalline /
liquid_light / gilded_relic / stormlight / enchanted_wild — all shiny/rendered, NO realism words) +
engine/style.py (resolves a journey's `style` NAME -> style_suffix + recommended checkpoint) +
dive.py `--style` override (A/B look-tests). The composer now sets `style` = a deck NAME (bounded
choice, no realism drift); it NEVER writes free-text style_suffix (legacy free-text still honored).
FUTURE (Phil): if words alone aren't enough, tack on LoRA/IPAdapter style models at render time — a
later lever, deck stays word-only for now.

## Journey-authoring rule (Phil 2026-07-30): don't over-describe the object / its reflections
Describing what's REFLECTED in or INSIDE a shiny/transparent object makes the model zoom into the
reflection/contents instead of the object (raindrop "with the meadow mirrored on it" -> we get the
meadow; sphere "reflecting the sky" -> the sky; over-detailed interior -> we chase that detail). And
a colour word that names another object ("rose dust") gets painted as that object (a rose flower).
Name the object plainly; the engine fills surface/reflection detail. Now in the journey-composer SKILL.

## POINT-TRACK targeting (2026-07-30) — Florence out of the hot loop
Engine-2.0 v5 (skyfog) tracking was bad. Re-ran Florence on the saved frames (scripts were ad-hoc;
engine now should save a debug overlay — TODO): on real rendered scenes Florence MISSES most frames
(storm-eye 0/21, fog 0/21, water-bead 1/6, planet/lighthouse mostly miss — diffuse/atmospheric things
and region-phrases have no outline to segment) and the few hits are garbage (edge slivers, top-of-frame
horizon strips, a 0.49 half-frame jump). The camera was really flown by the point-picker fallback, and
the LURCHES were the sporadic bad Florence hits reseating the aim + "arrived->snap-to-center" firing
whenever detection dropped. Phil's call: track a POINT, not an outline. dive.py now: commit ONE point
per approach run (points.pick_point; Florence optional off-by-default seed via approach_detect, filtered
by clean_box), then FOLLOW it through the KNOWN zoom geometry — zoom_transform re-centers on the aim, so
each frame we pick the aim that eases the tracked point toward center by LOCK_EASE(=0.3) of its offset
through z, and advance the tracked point analytically. Smooth geometric convergence (0.30->0.01 over ~9
frames, no jumps), faster (no per-frame masks). Dropped the width-planned-zoom (needed detection);
scheduled x10 arrive-look-plunge does the filling. Also fixed: format.counter was ignored (read from cfg
not format) so skyfog/antenna_ball's counter:false silently rendered a nonsense 10^n overlay. TODO: save
a per-frame aim/point debug overlay so we can SEE tracking without re-deriving it; revisit fill-on-beat.

## TRACKER v3 — the plan to BUILD next (2026-07-31, for the fresh session)
The whole reason engine-2 exists: fix the ILLOGICAL zoom of the (pretty) engine-1 videos — zoom into
the RIGHT object. Object tracking is THE priority ("the whole game" — Phil). Status of the attempts:
- v5 (per-frame Florence base + referring_expression_segmentation, reseat aim to box center): lurched.
  Florence missed most frames on muddy scenes; sporadic garbage hits yanked the aim.
- v6 (point-track: pick ONE contrast point/run, ease to center, hold; NO Florence): smooth, no lurch —
  BUT the picker picks near-CENTER every run (post-arrival the salient thing is already centered), so
  it tracks a POSITION not an OBJECT. It misses the lighthouse, doesn't stay on a specific drop. Proved
  by replaying the aim over v6 frames (scripts pattern: reconstruct aim offline, overlay on frames).
- Brightness/NCC probes: fail — the intended object isn't reliably the brightest (a DARK planet on a
  BRIGHT nebula → brightness tracks the background) and it GROWS as we zoom (template can't match).

VALIDATED FOUNDATION (committed): `engine/detect.locate(pil, query)` — semantic detection WORKS when
the object is present + big enough. Runs BOTH Florence tasks (caption_to_phrase_grounding got the
lighthouse; referring_expression_segmentation got the galaxy; both got the dark planet) on
Florence-2-large-ft, returns the best CLEAN box (clean_box filter). This is the OBJECT-phase detector.

THE DESIGN TO BUILD — unified two-stage, one loop (keep Phil's two-stage, rethink the handoff):
- Each detection beat, run detect.locate for the named target_phrase.
- OBJECT phase: when it locks, aim at it and FOLLOW it by PROPAGATING the lock through the KNOWN zoom
  geometry between detections (zoom_transform re-centers on the aim; a locked point maps to a known new
  spot each frame) — so a flickery/missed box never reseats/yanks the camera (v5's bug). New detections
  only GENTLY correct the aim.
- POINT phase: before the first lock (object still a sub-detectable speck), aim at the emergence point
  (points.pick_point / center) and keep zooming gently while locate() keeps trying.
- HANDOFF = first confident lock; geometry makes it seamless (no hard mode switch).
- EDGE CASE (Phil): if the object locks NEAR a screen edge, that's fine — but STEER toward it before it
  escapes the frame (don't let it drift off before we recentre).

TIMING (Phil's clarification, get this right):
- "Real-time" only meant the TECH exists (real-time video object tracking is solved) — NOT that we must
  detect every frame. We generate offline; we can be SLOW, just not VERY slow (>~1 min/frame = too slow).
- Florence per-frame ~TRIPLED frame-gen time before → do NOT detect every frame. ~every 4th frame
  (old REDETECT=4) is fine — we don't zoom fast enough to lose the object between beats. The thing that
  HURT before was the tracking LOGIC (reseat lurch / wrong config / center-picking), NOT the cadence.
- detect.locate = 2 tasks on large-ft = heavier than one base call; watch frame time and TUNE: cadence
  (~every 4 frames), maybe base-ft or grounding-only for speed, geometry-propagate on the in-between
  frames. Measure, don't guess.

TEST BED: night_bloom (a known-cool engine-1 journey, live, distinct objects: spore/spark/galaxy/
planet/lantern/flower/firefly). MUST be rewritten to the new schema first (scene/target/target_phrase/
kind/dur + a style-deck name) — schema+grammar+pacing all changed 2026-07-30, so its old render can't be
reproduced and it has no target_phrase. Develop the tracker against existing frames (frame-agnostic),
then render night_bloom-new WITH tracking and compare to the engine-1 version (did we make the zoom
LOGICAL while keeping the prettiness?). Keep engine-vs-journey variables SEPARATE (don't confound —
skyfog is a bad journey AND bad engine test; that's why it was useless as a test bed).

ALSO OPEN (separate from tracking, do NOT confound): (a) depth-ControlNet is a suspect for the ugly
"land/mountain" look — engine-1 had NONE and looked better; it may carve mountainous relief into cosmic
scenes (f95). A `--plain` flag (render any journey as pure feedback zoom, no CN/track) would A/B it.
(b) Pacing: the arrive-look-plunge curve decelerates to near-zero mid-scale, so long dives SLOW into
boring diffuse scenes (yellow fog); engine-1 was steadier — revisit the curve / don't give diffuse
scales a 2-bar linger. (c) STYLE: skyfog/antenna_ball drifted photoreal → fixed via the style deck; the
back half went orange-mono under stormlight (revisit). Journey fixes go into the COMPOSER, not one-offs.

### TRACKER v3 — BUILT (2026-07-31)

**The v6 root cause, found by reading the math:** v6 advanced its tracked point with the aim it
ASKED for, but `zoom_transform` silently clamps the crop window to the frame. At z=1.045 the crop
can only recenter by ±(1−1/z)/2 ≈ **±2.2% of the frame per frame**, while the ease formula assumed
up to ±35% — the `[0.15,0.85]` aim clamp never binds; the CROP clamp always does. So the internal
track marched to center on paper while the real object stayed put (or escaped) — "tracks a
position, not an object" was propagation divergence, compounding every frame. Rotation
(0.15°/frame) was ignored too. The cameo world-attach used the same broken advance (now also fixed).

**What was built:**
- `engine/track.py` — `crop_center`/`rotate_pt`/`propagate` mirror the real transform EXACTLY
  (selftest vs a rendered dot: worst 1.04px across zoom/rotation/clamped-aim cases —
  `python3 scripts/track_lab.py selftest`). `dive.zoom_transform` now derives its crop from the
  same `crop_center`, so assumed and actual transforms can never drift again.
- `Tracker` (one per approach run): POINT phase = committed `points.pick_point` emergence aim;
  `detect.locate` tries every `track_cadence`(=4) frames; OBJECT phase after the first confident
  lock. GATING (the anti-lurch core): a detection near the current heading (≤ max(0.15, size/2))
  confirms it — first hit snaps the lock, later hits correct GENTLY (gain 0.5); a detection FAR
  from the heading redirects only after TWO consecutive observations agree (≤0.18, both
  geometry-propagated); degenerate boxes (max side >0.8 — near-full-width centered strips that
  would false-agree) are dropped; a pending candidate expires after 3 missed beats; size ≥0.55 →
  stop detecting (object fills frame); track walks off-frame → re-pick emergence point.
  Camera smoothness is STRUCTURAL: real recenter speed is bounded by crop authority no matter
  what the gates decide — a redirect is just a few frames of max-authority steering.
- `engine/dive.py` — tracker owns the aim on approach frames; writes `build/track.jsonl` EVERY
  frame (mode drift/track/tail, z, aim, track state, detection events; row i = the frame the
  tracker OBSERVED, i.e. the fed frame) — the always-on debug record the v5/v6 postmortems
  lacked; `--plain` renders pure feedback zoom (no track, no depth-CN) for A/B; new DEFAULTS
  `track_cadence` 4, `track_model` Florence-2-large-ft.
- `scripts/track_lab.py` — `selftest` / `bench` / `sweep` (locate over saved frames → jsonl) /
  `overlay` (draw track.jsonl over frames → mp4 with aim ring, track cross, locked box, raw
  detection, pending X).

**Calibration data (sweeps over night_bloom v4 frames, the engine-1 morph-mush hard case):**
hit rates 0–80% by phrase — misses are the NORM, the tracker must (and does) ride geometry
through them; consecutive-beat garbage rarely agrees (median jump 0.2–0.7) so the 2-observation
gate stays closed through it; hallucinated boxes for ABSENT phrases occasionally DO agree
(ladybug pair at 0.025 — grounded onto the big flower), i.e. FP redirects land on stable SALIENT
objects — benign-to-good in a generative loop (we steer toward the most target-like thing and
the prompt paints the target there; the lock is self-fulfilling). Degenerate wide boxes
(1.00x0.62, centered) motivated the >0.8 cut. `locate()` ≈2.4s on empty scenes, ≈10s on
object-rich frames (mostly beam-search token time).

**Timing (measured, DS + depth-CN + cadence-4 large-ft):** ~20s/frame (engine-1 was ~6; the
depth-CN chain is most of the delta, detection ≈2.5s amortized). 224-frame render ≈ 75 min. Fine
per the "slow ok, not >1min/frame" bound; drop to base-ft or cadence 6 if it ever matters.

**Test bed:** `journeys/night_bloom.json` REWRITTEN to the new schema (8 bars/32 beats/224
frames, liquid_light deck, one seam quantum_sparks→galaxy mid-list, explicit `kind` everywhere —
galaxy→nebula is Δ8 and must not auto-seam — card-0 `loop_target`, lamar cameo, counter false).
Smoke (30f): point-commit → miss-riding → max-authority convergence verified against the log
(hand-checked propagate vs logged track to 4 decimals). Full tracked render: output/night_bloom/v6.
NOTE (journey, not engine): DreamShaper renders card 0 as an enchanted moss FOREST, not a moss-leaf
cell interior — gorgeous but off-script; composer-side fix if it matters.

### ENGINE-2 SETTLED (2026-07-31 evening) — Phil's verdicts, all in the engine now
- **DEPTH ControlNet STAYS at 0.45.** A/B rendered on frost_window (`--cn 0` vs default, same
  journey/seed/model/composition — `output/frost_window_cn0/v1` vs `output/frost_window/v1`).
  Claude read the CN as over-sculpting; PHIL'S CALL, and he's right: with the CN the dive
  stays coherently on ONE piece of the fern; without it the zoom wanders. Do not re-litigate.
  (`--cn STRENGTH` exists for future A/Bs; `--plain` also kills tracking, so it is NOT the
  CN test.)
- **COMPOSITION: never toward center.** v10 measured every run sliding 0.15 -> 0.05 off-center;
  the aim eased toward CENTER and the offset is multiplied EVERY frame, so even ease=0.05 ate
  76% of the composition per card. Now: ease toward the run's FROZEN rule-of-thirds ANCHOR
  (`points.nearest_third`), rate 0.03, anchor rotating diagonally per scale
  (`points.THIRDS_ORDER`), redirects gated to the first 10 frames so the heading never swings
  mid-bar. MEASURED on frost_window: runs hold 0.206->0.226, 0.210->0.226, 0.226->0.223, mean
  0.220 (v10: 0.100). Phil: "the center issue looks a lot better."
- **`render_start` (new).** Frame 0 is the only txt2img frame and a LITERAL scene is hardest to
  establish cold — frost_window opened as "a white fern on a desk in a room". Journeys are
  circular, so `render_start: "<register>"` rotates the chain to begin at an ABSTRACT/pattern
  realm (lattice, foam, field of lights). Independent of the playback opening (phase_shift).
  grammar WARNS if the rotation lands the seam card first/last (last = the loop-home branch
  swallows the seam entirely — it silently vanishes).
- **"fills the view" is BANNED in `scene`.** It compiled to broken prose ("moving through X
  fills the view") AND, as a render start, gave the model a close-up with no world so it
  invented one (the fern-on-a-desk). 49 scenes across the catalog carried it — the skill's own
  schema example taught it. Scenes now describe the WORLD with the subject as a feature in it;
  the ENGINE decides frame fill.
- **Captions:** BRAND_TAGS now also always append #animation #art #aiart #chillbeats.
- night_bloom v10 (the reference render) is queued as `night_bloom_remix`; frost_window (CN)
  queued too. queue_review.py fixed — it still expected `output/<journey>_<model>/`, which the
  style-deck-picks-model change broke, so NO new render could be ingested.

### SESSION CLOSE 2026-07-31 — state of play
**Fixed late in the session (all committed):**
- CAPTIONS WERE DEAD for the whole engine-2 catalog: `journey_worlds()` read `r['interior']`
  but new journeys use `scene` → KeyError → the dashboard's Generate button silently did
  nothing. Now reads scene|interior and takes style words from the deck. Verified end-to-end.
- DASHBOARD CAPTION EDITS didn't stick. Root cause: a KEYED `st.radio` IGNORES `index` on
  rerun and restores its own stored selection, so the sync-on-read block wrote the stale option
  over every hand edit — Save was undone by its own `st.rerun()`. Fix: apply picks ONLY in an
  `on_change` callback (fires just on a real click); Save clears the radio when the text isn't
  an option. Regenerating no longer overwrites an existing caption.
- MUSIC verified end-to-end on the new engine WITH a moved start frame: 103bpm from the format
  grid, key from the journey, 5 aligned candidates (lock 7.7–18.3×), seamless loop. The
  `render_start` rotation does NOT disturb the morph grid — but only because bars are uniform.
- STYLE: deck gained `brand_tail` (glittering specular highlights, iridescent sparkle, vivid
  complementary colour contrast, jewel-bright accents), appended to every style — Phil found
  cave_of_numbers monochromatic orange/yellow. Light/surface words only; "gemstone" as a NOUN
  would paint literal gems into meadows. NOTE: this fights deliberately-monochrome journeys
  (chess_empires "monochrome + one emerald", ink_dynasty sumi-e) — add a per-style opt-out if
  those look wrong.
- dive-video SKILL rewritten for engine 2 (was still documenting engine-1 schema + turbo).

**QUEUED FOR PHIL:** `bash scripts/render_batch.sh` — butterfly_meridian (long) /
quantum_orrery (medium) / lather_atlas (short), each render → caption → REVIEW. Waits for
ComfyUI + a free GPU, resumable, failure-tolerant.

**Review queue right now:** stormglass (engine-1 holdover), night_bloom_remix (the v10
reference render), frost_window, cave_of_numbers.

**OPEN / next session:** (a) the 4 fictional-realm counters (chalkboard_infinities,
quantum_orrery, cave_of_numbers, static_bloom) are still `counter:false` — Phil may want the
odometer everywhere for the charm; (b) cave_of_numbers' middle palettes are three stone cards
in a row (journey-side monochrome, separate from the style tail); (c) fold repair_seam into
dive.py's exact_loop tail (open since 07-29); (d) TikTok still paused (meta.paused_platforms);
(e) VARIATIONS.md could use the trending-sound journey idea.

**OPEN after this:** (a) review v6 vs the engine-1 v4 — did the zoom become LOGICAL while keeping
the prettiness (the whole point); (b) --plain A/B for the depth-CN look suspicion; (c) fold the
seam repair into dive.py's exact_loop tail (still open from 07-29); (d) update the dive-video
SKILL once results are approved.

### SEAM-MORPH + PACING + MUSIC-GRID FIXES (2026-07-31, Phil's hard-cut complaint)

**The hard cuts Phil flagged (ComfyUI 24805-7 = night_bloom v6 dive frames 41-43) — diagnosed
with ground truth:** the FORMAT 2.0 seam implementation ran the ENTIRE seam card at
`seam_denoise` 0.72, and dive stacked the +0.18 arrival boost → **0.85 effective for 4 frames,
then 0.78/0.72 for 10 more**. At 0.85 only ~15% of the frame survives → consecutive frames are
near-fresh txt2img rolls (citrus-cells → literal insect → jungle). Engine-1's ceiling was 0.58
for 6 prompt-blended frames — that's the cool dissolve. The design was also INVERTED: the dwell
got chaos while the actual on-beat seam morph got only 0.58. (antenna_ball's review cut has the
same defect — recheck it.)

**Fix (music-intent-aligned — the strong downbeat carries the morph, anacrusis leads in):**
- grammar: every card's schedule is `travel_denoise`; seam cards no longer special. New
  `seam_arrivals` return (9th) marks arrival phases that FOLLOW a seam card.
- dive: on a seam arrival's transition frames, denoise = `fmt.seam_denoise`(default 0.70) PEAK
  on the downbeat frame (k=0, where align.py sits the track's strong beat) ramping to travel
  across the prompt crossfade: 0.70→0.65→0.60→0.55→0.50→0.45→0.40. One coherent on-beat
  world-flip, engine-1 character at seam strength. Frame counts unchanged → morph grid unchanged.
- journey text: "like fireflies in fog" simile in the quantum realm summoned a literal INSECT
  mid-seam (the composer rule about similes naming objects — violated by my own card); de-simile'd.

**ZOOM FLOOR (Phil's other timing complaint — long scales stall):** grammar's sin² curve let
card-edge rates fall to ~1.02/frame (dur-8 cards worse). Now `zoom_floor`(fmt, default 1.028)
guarantees a perceptible dive rate; only the budget ABOVE the floor is shaped by the sin² swell;
per-card product (and the fill-lands-on-the-beat property) unchanged. A below-budget card (seam
dwell ×1.4) becomes a steady glide (1.024 uniform).

**MUSIC-GRID BUGS found while checking the musical intent (both silent, both new-schema-only):**
1. `score.schedule_morphs` still derived frame counts from legacy `sec` — a dur-based journey
   got a phantom 29f/card grid proportionally scaled onto the real video: EVERY morph time
   wrong, alignment locking to nothing. Now imports `grammar._frames` (single source of truth,
   same doctrine as zoom_transform/track sharing crop_center). Verified: night_bloom intervals
   now 2.33s/1.17s = exact 4-beat and 2-beat cards.
2. `music_gen.bpm_for` used MEDIAN morph interval as the bar — mixed dur journeys (2+2 half-bar
   groups are BY DESIGN) → phantom 1.75s bar / 137bpm. For dur journeys the bar is now DEFINED
   by the format grid (beats_per_bar × frames_per_beat / 12fps → 2.333s, 103bpm); legacy
   journeys keep the median path.

night_bloom v6 (rendering during the fix) has the OLD seam — keep as the before; v7 = the after.

**v6 FULL-RENDER TRACKER AUDIT (224 frames, 152 approach, 43 detection beats):** 34 honest
misses / 8 refused candidates / 1 lock — and the one lock was BAD: on the white-flower run two
consecutive corner-garbage detections (a 5:1 sliver at the frame corner) agreed within 0.18 and
squeaked a lock-redirect through; the camera stayed bounded (crop authority) but aimed cornerward
for ~7 frames. Gate tightened from the data: a box accepted as lock/redirect must be
object-shaped (aspect ≤ 3.5) and steerable-to (center outside the outer 10% margin). ZERO true
locks overall — night_bloom's worlds are mostly emergent (the target materializes AT the arrival
morph, not during approach), so the point-phase + arrival-morph pipeline carried the whole video
— and did it well (the dark-planet card arrived dead-center and filled the frame: the LOGICAL
zoom, no detector needed). Locks are an opportunistic bonus on discrete-object cards, not the
backbone; that matches Phil's morph-on-the-beat guardrail. The one structural miss: the
lantern-garden card drifted to flat paper-cut style ("paper lanterns" content words) and Florence
finds little on flat art — style-vs-detection interplay to watch.

# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE 3 — THE CAMERA (planned 2026-08-15, Phil's brief; the plan of record)
# STATUS 2026-08-17: PAUSED at Phase 2 by Phil — "get our world looking 3-D and parallax
# looking nice before adding camera moves." The orbit gate's technical finding stands
# (warps survive re-diffusion only when re-synthesis outpaces resample loss — v3: denoise
# floor 0.52 + post-warp unsharp held 15° crisp), but the result did not read as orbital
# motion to Phil (content re-interpretation at higher denoise; parallax not legible;
# labs must ship 12fps looped clips). Phase 1.5 (depth realism in scaffolds) is the
# active work; resume here after depth reads 3-D.
# STATUS 2026-08-22: superseded as a standalone plan — this section resumes as Phase D of
# "DEPTH 2.0 — PARALLAX ERA" (end of this file), Phil-approved 2026-08-22.
# ═══════════════════════════════════════════════════════════════════════════════

## Why (the residual problem)
Engine 1 gave us the zoom. Engine 2 gave us targeting and (via resolve-on-approach)
populated realms. What remains — Phil, 2026-08-15, after reviewing the first resolve-era
renders — is TWO-DIMENSIONALITY ("big and little things in a 2-D plane; I can't even tell
if the parallax is working") and two realm jumps the engine still cannot perform:
**planet → landscape** (we never descend and land; space morphs into terrain) and
**exterior → interior** (we never pass through a window/door into a room). Camera motion
is the fix class, and it generalizes what the engine already does: crop-and-reimagine is
the special case "zoom" of warp-and-reimagine.

## THE IRON LAW (constraints every move obeys)
1. **The scale-zoom never stops and never changes rate.** ×10 per card at the schedule's
   log-rate is the metronome. Camera moves are ADDITIVE on top; forward/lateral SPEED may
   vary (rush, settle) but the scale axis is constant.
2. **Moves are musical events.** A move begins/ends/inflects ON beats, eases across bars,
   peaks with the anacrusis into downbeats — same grid as morphs and music.
3. **The loop must close.** Net camera state over the video ≈ identity (orbit angles sum
   to ~0 mod 360, tilt returns home, or the seam absorbs the residual) — a new validator
   class alongside seam/start rules.
4. **Every frame stays freshly generated.** Warps feed the diffusion; nothing is pasted.

## Architecture: three layers that must agree
1. **WARP layer (new — engine/warp.py).** Per-frame transform of the fed-back frame using
   its own depth map (DepthAnything, already computed every frame): depth-parallax
   translation (truck/pedestal), depth-rotate (true ORBIT — the camera revolves, near
   pixels sweep opposite far, re-diffusion invents newly revealed sides), homography pitch
   (TILT), dolly (forward translation with perspective change — distinct from zoom).
   Disocclusion handling: the warp emits a stretched-region mask → locally boosted denoise
   via the existing mask_image channel (partial inpaint), so revealed geometry is invented,
   not smeared. Depth is temporally EMA-smoothed to kill estimator shimmer.
2. **SCAFFOLD layer (exists).** During resolve windows the procedural scaffold performs the
   IDENTICAL move (it is geometry we project) so conditioning and warp always agree.
   PHASE-1 FIX (Phil's log instinct): instance depths become LOG-UNIFORM across ~1.5
   decades with size/brightness spanning the full range, plus 2-3 discrete parallax planes
   with distinct velocities — motion must separate the planes or the field reads flat.
3. **SEMANTIC layer (exists).** Prompt attitude ramps (REALMS POV tags) synchronized with
   the warp: the words, the scaffold and the warp all describe the same camera.

## The move vocabulary (per-card `camera` field, validated like everything else)
Primitives: `roll(rate)` · `truck(dx,dy)` · `orbit(deg_per_bar)` · `tilt(from,to)` ·
`dolly(v)` · `settle` (ease to hover). Composites:
- **`spiral`** — orbit + the ever-running zoom: circling a star/nucleus while closing in.
- **`vertigo`** — dolly OUT while the zoom runs: scale constant, perspective stretches
  (legal under the iron law — the classic shot, used as rare spice on hover beats).
- **`landing`** — THE planet fix, a choreography spanning 2-3 cards:
  (a) APPROACH: planet grows under slight orbit (tracker owns aim);
  (b) PITCH-OVER: as the surface scale is crossed, tilt ramps from face-on to oblique —
      the horizon rises INTO frame (scaffold flips to surface mode with a high horizon;
      prompt ramps "from directly above" → "low over");
  (c) SKIM: fast forward speed low over terrain — strong parallax, surface instances
      rushing past beneath, zoom still constant — with a TERRAIN MENU per journey
      (canyon / forest / city / lake / dune / glacier, from REALMS landscape band);
  (d) hand back to a normal card diving into one terrain feature.
- **`threshold`** — the interior fix: an APERTURE (window/door/arch) is the card's target;
  the tracker aims at its dark opening; the crossing lands ON a beat (brief dolly surge +
  exterior→interior prompt flip + light-regime change); a new scaffold mode **`chamber`**
  (one-point-perspective room: wall/ceiling gradients + furnishing instances) receives the
  camera inside. Unlocks the human-scale interior play (room → animal/object/mineral
  within) Phil wants — used when a journey has built structures, never mandatory.
Cinema menu to grow over time: push-in, crane reveal, orbital reveal, fly-through,
rack-focus (a cheap post-layer defocus ramp), whip-tilt on seams.

## The CINEMATOGRAPHER (a separate role — never the composer)
The journey composer stays blind to camera. A distinct pass reads the finished journey
(cards, exps, scenes, POV tags) + REALMS + a new CINEMA.md doctrine and writes the
`camera` plan: v1 is RULE-BASED and deterministic (planet→landscape adjacency ⇒ landing;
aperture nouns in scene ⇒ threshold candidate; single central [amb] subject ⇒ spiral;
wide surface ⇒ skim/tilt; default ⇒ drift + roll), auditable and testable like every
schedule; v2 adds an LLM cinematographer for taste on top of the rule floor (headless
opus pass in the refill, mirroring composers). A validator enforces the iron law + loop
closure before render.

## Build sequence (each phase gated by a lab A/B, the pattern that works)
- **Phase 1 — depth realism in scaffolds** (day): log-uniform depth, full-range layering,
  parallax planes. Gate: do resolve windows stop reading flat? **DONE — scaffold v3 shipped
  2026-08-17** (per-instance looming via `_advance()`, painter's-algorithm occlusion, depth
  prompt clause in resolve windows); fixes #2 (palette gloom) and #3 (depth-aware
  detail_boost) explicitly HELD by Phil.
- **Phase 2 — warp core** (the heart): engine/warp.py primitives + disocclusion-mask
  denoise + depth EMA; extend track.py's exact propagation so tracker aim and cameo
  positions ride ANY warp (it already does zoom+roll). Gate: orbit_lab — re-render one
  card of an existing video with a 20-40° orbital sweep; does re-diffusion heal it at
  travel denoise?
- **Phase 3 — vocabulary + cinematographer v1**: camera schedules compiled like
  zoom/denoise (grammar emits per-frame camera params; dive consumes); rule-based
  assignment; loop-closure validator; preflight/audit checks.
- **Phase 4 — the hero moves**: landing_lab (pitch-over + skim on a planet→landscape
  boundary; terrain menu) and threshold_lab (compose one test journey with a window card;
  chamber scaffold; crossing on the beat). Each ships only after its lab wins.
- **Phase 5 — polish + adoption**: vertigo/rack-focus/settle spice, CINEMA.md doctrine,
  LLM cinematographer, refill integration, catalog-wide adoption; IG data then judges
  (does motion move qscore/reach?).

## Risks and their mitigations
Depth-estimate noise → EMA smoothing + small per-frame steps (≤0.5°/frame orbit).
Warp drift accumulation → camera state resets at card boundaries (moves are per-card).
Cameo/counter interplay → cameo paste coordinates transformed through the same warp math
(track.py generalization); counter is post-assembly, unaffected. Disocclusion smears →
mask-boosted denoise; if insufficient, scaffold-assisted infill during resolve windows.
Motion sickness / brand drift → moves are spice, not sauce: the cinematographer's rule
floor keeps most cards on drift+roll; heroes appear where the journey earns them.

# ═══════════════════════════════════════════════════════════════════════════════
# DEPTH 2.0 — PARALLAX ERA (approved by Phil 2026-08-22; supersedes Phase-1.5
# pictorial-depth work as the active depth effort; ENGINE 3 resumes as its Phase D)
# ═══════════════════════════════════════════════════════════════════════════════

## The diagnosis (why depth stayed thorny — settled with Phil 2026-08-22)
Motion parallax is the DOMINANT human depth cue, and the core transform deletes it:
zoom_transform is a uniform crop+upscale — every pixel expands at the same rate, which is
the optical signature of approaching a FLAT FRONTAL PLANE. However 3-D a still looks, it
MOVES like wallpaper, and the brain trusts motion over the picture. This explains all of it:
- Pictorial fixes (scaffold v3 looming, depth prompts) improved stills, but stills animated
  with flat-plane motion still read flat; scaffold looming lives only in the CN conditioning
  during resolve windows while the fed-back IMAGE moves uniformly — at travel denoise 0.40
  the image wins.
- coral_synapse read 3-D at the opening then flattened mid-dive: one dominant structure
  against background gives silhouette-occlusion depth and uniform zoom passably imitates
  approaching ONE object; when the frame fills with a FIELD of instances, uniform zoom =
  enlarging patterned wallpaper. Flatness bites exactly in the seas.
- The taste conflict dissolves: the pictorial cues Phil rejected (gloom fade, far-field
  desat, depth blur — his verdicts STAND) are unnecessary for motion depth. Everything stays
  sharp/dark/saturated; depth comes from HOW IT MOVES. The "COD feel" = parallax + occlusion
  changes at full sharpness, exactly how a game renders.

## Phase A — parallax dolly (the centerpiece)
Compose the schedule-exact zoom with a small DEPTH-DIFFERENTIAL residual: near pixels get
extra expansion, far pixels less, normalized so the reference plane (the TRACKED object's
depth when locked, else median depth) stays EXACTLY on the scheduled zoom — counter, bars,
morphs, loop math untouched; iron law intact. warp.dolly already implements the
displacement; the work:
1. Fuse crop-zoom + dolly residual into ONE resample (no added generation loss — we already
   resample every frame; orbit failed on LARGE lateral warps, this residual is a few px/frame
   at the edges, same order as existing resampling).
2. Per-frame depth source: the scaffold's OWN depth inside resolve windows (clean, and
   conditioning + warp finally AGREE — the orbit-v2 lesson); DepthAnything at cadence
   ~every 3-4 frames with EMA + quantized into planes elsewhere (the noisy-depth lesson).
3. disocclusion_denoise where the warp reveals geometry.
4. `parallax_gain` knob, 0 = today's engine — the A/B axis and the safe retreat.

## Phase B — persistent seas
Scaffolds currently exist only at realm arrivals. Extend the population field through the
WHOLE CARD for many-instance scenes: instances keep flowing, looming, occluding, exiting at
the edges for the full travel, feeding both CN and the warp's depth. "Moving through a sea
of things", not "a sea appears, then wallpaper".

## Phase C — musical micro camera motion (Phil: MUST have a clean off-switch)
Flatness is worst during LOOK bars (zoom slows, parallax stops). Add sinusoidal lateral
truck during arrive/look bars (drifts out and back — integrates to zero within the card, so
loop closure is safe by construction) + a dolly-gain surge on plunge downbeats. Camera
motion as musical phrasing. Phil can't yet envision it → build behind a SINGLE default-off
flag (`camera_micro`) so every render can run with/without; he judges the A/B when we
get there.

## Phase D — vocabulary + cinematographer (= ENGINE 3 resumed, gated on A-C verdicts)
Orbit for showcase cards (v3 gate result stands), `landing` planet-descent and `threshold`
window-transfer hero moves, roll/yaw/revolution kept distinct, rule-based cinematographer
v1 assigning moves from journey POV tags.

### Phase D BUILT (2026-08-27 — doctrine in journeys/CINEMA.md, labs pending Phil)
- engine/camera.py: per-register `camera` field ({move, rate} or shorthand string) →
  per-frame schedule. Envelope = zero across the arrival morph, one-beat smoothstep up,
  hold, one-beat smoothstep down to zero at card end — rates are zero at every card
  boundary, so moves inflect on beats and THE LOOP CLOSES STRUCTURALLY (no angle
  bookkeeping; the lap card copies the camera-free render-start card). Hard exclusions
  enforced in schedule() itself (not just validate()): render-start/lap card, seam
  cards, depth moves on cameo cards.
- Vocabulary v1 (proven mechanisms only): roll (extra deg/frame through the exact
  rotation propagation — track.step takes per-frame rot), spiral (orbit about the
  TRACKED object — pivot rides the aim, pivot depth sampled from the object's own
  patch; the world revolves around the thing we're diving toward), orbit (median-plane
  pivot for field cards), vertigo (near-field dolly against the zoom), tilt (pitch —
  the `landing` component). Caps: orbit-class 0.5°/frame (the orbit-v3 gate figure),
  roll 0.6, vertigo 0.015, tilt 0.5.
- warp.camera_residual: parallax + micro-lat + orbit + dolly + tilt FUSED INTO ONE
  REMAP (the Phase-A one-resample lesson). Camera-free frames keep calling
  parallax_residual — byte-identical production path (VERIFIED 2026-08-27: fresh base
  arm v12 vs pre-Phase-D v9, frames 0-71 byte-equal, first diff exactly at the frame-72
  tail boundary where tail code legitimately evolved since 08-22). Orbit/tilt frames
  get a denoise floor (cfg camera_den_floor 0.48; orbit-v3: re-synthesis must outpace
  resample loss). Depth moves taper across the loop tail exactly like the parallax.
- scripts/cinematographer.py: rule-based v1, a SEPARATE role from the composer
  (composer stays camera-blind). Floor: ≤1 spiral (first eligible target card),
  ≤1 orbit (first eligible field card), ≤2 rolls alternating sign (phase seeded by
  name-crc32), everything else drift; never on start/seam/post-seam/cameo cards.
  NOT wired into the nightly — a journey gains camera only when the tool is run on it.
- scripts/camera_lab.py: same-seed A/B harness over DERIVED specs
  (output/camera_lab/specs/ — catalog untouched); preflight prints a camera line.
- Phase C verdict arm shipped alongside: dolly_lab a10m (gain 1.0 + --micro) vs a10.

### Phase D lab log (2026-08-27, same day — three findings before the clean run)
1. SCAFFOLD SEED BUG (fixed): resolve scaffolds seeded from the RUN name, so every
   renamed A/B arm (lab specs, --plain/--cn suffixes) drew a DIFFERENT instance field —
   the first camera A/B diverged at the window pre-roll, before the camera acted. Fix:
   seed from the journey identity (spec.scaffold_name override for derived lab specs;
   nightly renders byte-unchanged). Verified: arms then byte-identical to frame 34,
   first divergence exactly at the frame-35 orbit onset.
2. DEN FLOOR RE-CREATED THE ORBIT-V3 REJECTION (fixed): camera_den_floor 0.48 made the
   cam arm re-INTERPRET content instead of revolving it — literal steel launch towers
   hallucinated from abyssal's "gas towers" scene wording. Same failure Phil rejected
   on orbit-v3 ("the raised denoise CHANGED the content"). Floor now defaults 0 —
   vocabulary-rate moves displace ~1px/frame, parallax-order, healed at travel denoise.
   Also: plane-quantized depth makes orbit shear piecewise-constant (girder-bait edges)
   — displacement fields now use a Gaussian-smoothed depth (warp.camera_residual
   `smooth`); the parallax SCALE term keeps the raw proven planes.
3. PROMPT BAIT CONTAMINATES CAMERA LABS (test-bed rule): even with both fixes, abyssal's
   card-2 ARRIVAL morph (den 0.58, prompt "...among the gas towers") coin-flipped to
   literal towers on the cam arm's diverged feed — BEFORE spiral ramped in. A camera lab
   journey must have bait-free wording on and around the move cards. Round 4 = the clean
   bed: cherenkov_cistern (storm_world=spiral 0.4, mountain_country=orbit 0.35).
   abyssal rounds kept on disk as the failure-class record
   (output/abyssal_chandelier_cam*/).

### PHIL'S VERDICT (2026-08-27 evening) — vocabulary PARKED; the noise-floor law
Phil on both A/Bs: no perceptible motion, "just two videos that diverge slightly in
content." He is right, and the reason is quantitative: at rates that don't destroy
content, orbit displaces ~0.8px/frame — under the engine's own frame-churn floor (the
zoom's radial flow is ~26px/frame at the edges; the parallax differential that DOES
read is ~6-12px/frame; re-diffusion repaints small structure every few frames
regardless). Above that rate, re-diffusion smears or re-interprets (the tower class).
IMAGE-SPACE WARP RESIDUALS AT SAFE RATES ARE BELOW THE PERCEPTUAL NOISE FLOOR — orbit
has now failed to read 4 times (orbit_lab v1-v3, camera_lab). SECOND LESSON, method:
in a feedback engine a 1px perturbation cascades into different content within ~10
frames, so same-seed side-by-side A/Bs CANNOT isolate motion perception — judge single
clips only. Phase D plumbing stays committed and INERT (no catalog journey carries a
camera field; verified byte-identical off-path). Camera motion returns only via
mechanisms that ride channels the engine is strong in (conditioning/scaffold-driven,
or the zoom channel itself) — after PERSISTENCE.

# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE — THE ACTIVE FRONT (Phil's call 2026-08-27 evening)
# ═══════════════════════════════════════════════════════════════════════════════

## The shared root (forensics 2026-08-27, both cases on file in scratchpad strips)
Re-diffusion pulls every frame's composition back toward the checkpoint's prior;
nothing open-loop anchors instance EXISTENCE or scheduled SCALE outside resolve
arrival windows. Two production symptoms, same disease:
- HUMMINGBIRDS (ruby_furnace daybreak_garden, v6 f72-96): the scene's population
  ("ranks of trumpet flowers, several hummingbirds") never establishes — the card is
  vine-leaf wallpaper; birds materialize ad hoc only when the plunge prompt names the
  target, hopping position and size frame to frame. Root: the cameo rule capped the
  card's scaffold window at 6 of 24 frames; nothing held instances after it.
- PLANETS (cobalt_rookery ice_world, v6 f50-77): the "world seen from orbit" lives as
  a small marble ON an orange ground plane and grows only 12%->25% across a x10-zoom
  card — THE PRIOR EATS THE ZOOM (re-diffusion re-normalizes the object to
  prior-preferred size every frame). At the boundary the dominant background becomes
  the landscape and the never-entered planet is re-read as decoration and slides off.
  (Counter-example that proves the rule: cherenkov's storm_world lands cleanly because
  its plunge FILLED the frame with surface texture before the boundary.)

## Two mechanisms BUILT 2026-08-27 evening (lab flags, default OFF; commit da23d94)
- --persist-cn: the resolve scaffold stays the CN through the card's TRAVEL (window to
  one beat before card end; the plunge stays the tracker's), CAMEO CARDS INCLUDED.
- --hero-cn: single-target cards get a synthetic depth SPHERE at the tracker's live
  position whose size follows the schedule exactly — seeded at 1.05/(product of
  remaining zooms) so the target FILLS the frame at the boundary; detected size adopted
  upward, never shrunk. The containment contract enforced through the CN.

## First lab results (single-clip format; clips in output/persist_lab/, Phil judging)
- ruby garden + persist-cn (v7 vs v6 ref, same copied prefix): the flower population
  now ESTABLISHES and holds through the card — the wallpaper failure is gone. Open:
  no distinct hummingbirds appear, and the dive plunges into the CAMEO sprite (which
  also persists now; the tracker likely locked it — the known sprite-takeover class,
  aggravated). Cameo/tracker interaction is the next fix before adoption.
- cobalt planet + hero-cn (v7 vs v6 ref): the forced structure grows on schedule from
  small to frame-filling and the boundary descends INTO it — the slide-off failure is
  gone, first time on this card. Open: it reads as a giant ringed caldera ON the
  ground, not a globe in space — the world-in-space reading is lost at the card's
  ARRIVAL (upstream of hero-cn): the previous card's texture feeds forward as
  "ground" and the arrival morph keeps it. Candidate next steps: space-establish
  language + negatives on planet-card arrivals mid-chain (the T_ESTABLISH_SPACE idea
  applied to arrivals, not just frame 0), or a sea/space scaffold mode behind the hero.

## SECOND ROUND (2026-08-29, Phil's verdicts on round 1 + these tests)
Phil accepted round 1 as PROGRESS, not solved. His three reads, and what round 2 found:
- PERSIST is real but it is ONE object, not a SEA. On ruby garden he saw one hummingbird
  whose PART morphs back into a whole bird on the plunge (the fixed-point dive regrowing
  the target from a fragment). His ask, verbatim: "making sure seas of things persist."
  TEST (waterbear tun_cells, a sea-mode card, --persist-cn, from-card 3, v2 f72-95):
  SAME SHAPE as ruby. f72-76 = a genuine DENSE FIELD of many cells (establishment FIXED,
  second case now — the wallpaper failure is gone for flowers AND cells); f80-84 the zoom
  has FUNNELLED INTO ONE cell filling the frame; f88+ we are on its surface. So persist-cn
  fixes the LOOK phase (real crowd, not wallpaper) but the PLUNGE still collapses to one
  BY DESIGN — every card's arrive->look->plunge dives into a single target. "A sea that
  persists the WHOLE card" is in direct tension with "zoom into one object per card."
  REFRAME (the productive split): Phil's real want (hummingbirds) is DIVE-THROUGH-A-CROWD,
  not a static sea — move through a dense field, near instances passing (parallax), toward
  ONE among many, instead of a lone object we funnel to. Levers, both untested:
    (a) scaffold extend=True during the plunge so the field stays dense (far instances keep
        arriving as near ones exit — the Phase-B log-uniform drain fix; persist-cn currently
        does NOT set extend, so the sea thins as we advance);
    (b) a PLUNGE-prompt variant that keeps naming the POPULATION ("through a dense field of
        X toward one"), not only the single target (T_PLUNGE names one target every frame).
  Clip: output/persist_lab/sea_persist_waterbear.mp4 (card 3, 12fps x3).
- PLANET (cobalt): "those holes aren't planets — I want a sphere in the void, an interesting
  void." HERO v2 built (commit 16da4aa): (1) ROUND-TARGET GATE — hero fires only on
  planet/world/moon/sun/sphere/orb/egg/... (round 1 forced a globe onto card 1's "steep rock
  headland" and got a ringed caldera — Phil's "holes"); (2) VOID OF SPECKS replaces the flat
  far plane (the flat plane over a busy fed-back background was half the on-the-ground read);
  (3) globe-in-void PROMPT ("a single round globe hanging alone in the black void of space")
  + NEG (crater/hole/pit/ring/cell/landscape/horizon) while the globe is still an object.
  TEST bed = cobalt CARD 0 (cluster_sun -> "a blue planet" in a crowded star cluster = his
  "sphere in the void"). Clips: planet static + planet 90-deg orbit (see below).
- CAMERA was FAR too timid (Phil: single degrees are nothing; he wants ~90 deg around a
  planet as it grows a third->80% of frame). The one place a BIG image-space warp can beat
  the noise floor is HERE: the hero depth-CN pins the sphere silhouette and a void of specks
  has nothing to re-interpret. warp.hero_orbit (commit 16da4aa) revolves the sphere interior
  + pans the starfield DEG across the approach, tied to the hero. THE AGGRESSIVE BET; a
  smear shows plainly in the single clip. --hero-orbit DEG (lab flag, default 0).

## --frames SMOKE-TEST TRAP (found + fixed 2026-08-29, commit pending)
in_loop_tail = i >= total - loop["frames"]; with --frames truncating total, the loop-homing
tail is sized off the TRUNCATED total, so it EATS the approach (cobalt --frames 40: tracker
flipped to "tail" at frame 7, the whole planet approach became loop-homing). --frames already
disables counter + lap_cut; it now also disables the loop tail via the new --no-loop flag
(approach labs pass it). ANY past --frames+--from-card lab clip whose last loop["frames"]
frames looked like homing was hitting this — re-cut from the pre-tail frames.

## Next steps (pending Phil's verdicts on the clips)
1. Sprite/tracker interaction under persist-cn (veto locks inside the cameo's
   propagated box; or suppress cameo on persist cards).
2. Bird-species establishment: scaffold holds WHERE instances are; the species comes
   from prompt weighting — try naming the population in the travel prompt (grammar
   currently names only the target).
3. Planet-arrival space treatment (above) + hero-cn on more planet cards.
4. Adoption path when clips convince: persist-cn for populated cards + hero-cn for
   planet-class targets as per-card `resolve`/`hero` fields the composer can set —
   never a blanket default without A/B'd renders.

## Labs and gates (variable-isolated, 12fps SLOW LOOPED clips — Phil's standing format)
- dolly_lab: one populated-field card (the class that flattens), same seed, four arms —
  baseline / gain 0.5 / gain 1.0 / gain 1.0 + persistent scaffold. GATE: near instances
  visibly overtake far and exit fast at the edges; no structure smear by card end; no
  added morph-feel.
- drift_lab: winning arm + hover-drift. GATE: look bars feel inhabited, not paused.
- Full-journey A/B at the SAME SEED as an existing render (coral_synapse — the video Phil
  cited) for his motion verdict BEFORE the nightly batch adopts anything.

## Deliberately NOT doing
No gloom fade, no far-field desaturation, no depth blur (taste verdicts stand — motion
depth makes them unnecessary); no change to bars, tempo, seams, targeting, or the loop
contract. Camera-move vocabulary stays gated behind the dolly foundation.

## STATUS 2026-08-22 (same day): A-C BUILT, dolly_lab GATE PASSED, coral A/B rendering
Lab (output/dolly_lab/, squid_lantern first 4 cards × 4 same-seed arms, 96f each):
- MECHANICAL GATE PASSED (scripts/dolly_gate.py): parallax active frames 1+ (DA cadence +
  scaffold windows as designed; persist arm 76/94 scaffold-sourced), arms diverge from
  baseline (~15 by f8 → ~52 mid-render, stable not exploding), consecutive-frame crops at
  gain 1.0 CRISP — zero directional smear (the gate's "51.7% sharpness deficit" was content
  divergence: smooth near-domes score lower Laplacian variance than baseline's busy
  eye-wall; metric caveat noted in dolly_gate.py).
- THE BIG FINDING: the residual doesn't just move pixels — it STEERS WHAT THE MODEL PAINTS.
  Parallax arms grow genuine foreground-over-background composition (looming domes, layered
  scalloped edges, oblique surface views) exactly where baseline stays frontal wallpaper.
  The motion cue biases the feedback chain toward depth-composed content: pictorial depth
  emerges FROM motion depth, for free.
- Lab-frame caveats for viewers: last ~21 frames of each arm are a fake loop tail (a
  --frames cut lands the tail mid-card; parallax tapers there by design). Phil's clip =
  output/dolly_lab/squid_lantern_dolly_AB_loop.mp4 (+_small delivery copy).
Full-journey A/B: coral_synapse v3 (seed 1234 = same as v1/v2), --parallax 1.0
--resolve-persist, launched 2026-08-22 ~14:30. Phil judges the motion; adoption decision
(nightly --parallax default + gain choice + whether persist ships) waits on that verdict.
Phase C (--micro) built but UNJUDGED — needs its own with/without A/B when Phil wants it.

## PHIL'S FIRST LAB VERDICT (2026-08-22 evening) + follow-ups
- All three parallax arms > baseline. **GAIN 0.5 read the most 3-D** (his callout: a squid
  resolving into a sphere ~4s in with visible parallax, and the ball-field just after).
  The two 1.0 arms didn't look much different from each other; a bit better than baseline.
  Side-by-side was hard to judge → labs now ALSO ship a one-after-another SEQUENTIAL cut
  (dolly_lab --sequence-only; label card before each arm) — add to the 12fps-looped rule.
- **PERSIST IS ~A NO-OP AT THESE CARD LENGTHS (measured, mechanism understood):** the CN
  window already spans w0=S−6 .. S+fa+10 ≈ 22 of a 24-frame card, so --resolve-persist
  extends the depth source by ~2 frames/card (~5 on 28f cards). a05 vs a05p frames are
  byte-IDENTICAL until the first SEA window (f48), and diverge there mostly because the
  corridor traffic-extras change the scaffold's draw — a content variant, not visible
  "persistence". Phil called it ("not sure persistency is doing much") before the numbers
  did. Persist would only matter on long-dur cards or with deliberately shorter CN windows
  — park it; don't ship it as a default on current catalogs.
- WHY 0.5 > 1.0 (hypotheses on file, coral v4 tests): (1) displacement-survival sweet spot
  — re-diffusion re-paints toward coherence, a gentle warp survives as MOTION while a
  strong one is absorbed as content change; (2) trackability — at 1.0 near content exits
  too fast to register relative motion; (3) in scaffold windows the CN already animates
  looming, a strong warp double-pushes and the model repaints the conflict away.
  CANDIDATE REFINEMENT (untested): scale gain by depth source — lower inside CN windows,
  higher on DA travel frames.
- Delivered: coral v3 (gain 1.0+persist) A/B loop + assembled cut; squid a05p arm;
  sequential cuts. coral v4 (gain 0.5 + persist, seed 1234) RENDERED + DELIVERED
  (v2-vs-v4 AB loop, assembled v4, sequential v2→v4→v3 — all in build/ of v4).
  VERDICT (same evening, revised after the v3-vs-v4 side-by-side): Phil leans HIGHER —
  1.0 gives more depth, its only cost is occasionally-abrupt motion; 0.8-0.9 maybe ideal.
  **GAIN IS NOW A RANDOM PER-VIDEO VARIABLE**: DEFAULTS["parallax_gain"] = "random" → each
  render draws from {0.5..1.0 by tenths}, DETERMINISTIC from crc32("name#seed") (same-seed
  re-render reproduces its gain; '#' salt chosen for even spread over the first requeue),
  logged in run.json AND carried by queue_review into the pipeline entry
  (engine_params.parallax_gain) so ig_analyze's new "parallax gain" group can contrast
  them as posts accumulate. persist NOT shipped (parked); coral v5 0.7+persist rendered as
  standby. THE REQUEUE (2026-08-22 night): all 15 review-stage videos (pre-parallax) →
  rejected, journeys re-queued at FRONT same-seed; music/production stages untouched.
  TONIGHT: one-off PowersOfZen-render-once task at 00:00 (delete after: schtasks /Delete
  /TN "PowersOfZen-render-once" /F), budget 430 + LLLLSS template prepended for the extra
  videos — RESTORE budget 340 + drop LLLLSS when the requeue backlog drains (Settings tab).
  Verified pick: whale_fall(0.8) coral(0.8) lantern_mangrove(0.7) cobalt(0.9)
  magnetite_choir(1.0) wild_yeast(0.5) ≈ 419min.

## SEAMS — DIAGNOSED AND FIXED 2026-08-23 (Phil's extra-card idea; supersedes the ipacn-
## parameter hypothesis below)
FORENSICS: every piece of the 08-02 seam machinery was intact and WORKING — the IPA tail
landed perfectly on frame 0. The disease was frame 0 itself: the only frame in the video
not born from the feedback chain. "A vast wide panoramic view … seen from far away" is
postcard language — on cosmic render_starts DreamShaper composed LAND-UNDER-SKY (whale-
fall's 10^14 nursery = desert rocks + flowers under the Milky Way), and the tail dutifully
returned the whole video to it. It read WORSE lately because (a) parallax made mid-dive
frames more coherent (wider gap to the postcard) and (b) the rethink doctrine favors
cosmic starts (max postcard damage). BOTH FIXES SHIPPED (commit aedd70a, details there):
1. LOOP LAP (Phil's idea, default ON, --classic-loop A/B): one extra card — card 0's
   schedule again, arrived mid-dive — home onto card 1's feedback-born start, cut the
   txt2img warm-up card. Still exactly N bars; music/morph grid untouched; seam-card-last
   no longer swallowed; +1 card ≈ +10% render. Validated on wild_yeast v3 (loop closes in
   the same visual universe; seam A/B sent to Phil).
2. SCALE-AWARE ESTABLISH: T_ESTABLISH_SPACE + landscape negatives for render_starts at
   exp ≥ 6.5 or ≤ −6 (pastiche: cobalt sun-wheel-in-space vs galaxy-over-clouds; ruby
   space-portal vs lava-canyon; lantern orbital ocean-world vs aurora-over-lake).
RETROFIT (no full re-renders — Phil): review+production videos get `--from-card N-1
--src-version vX --parallax <source gain>` (zoom schedules byte-identical through card
N-2, only last-card prompts + tail + lap regenerate ≈ 15 min each). Pre-parallax sources
(caddis v1, termite v2) retrofit at --parallax 0 to match their bodies.

## AUDIENCE DATA WISHLIST (Phil 2026-08-22): reposts/saves/shares per reel — **SHIPPED same night**
Phil converted the account to professional. IG web STILL exposed no insights UI (no View
insights, professional_dashboard 404) — but Meta Business Suite accepts "Continue with
Instagram" login (no Facebook account needed): linked the zen Chrome session, and
business.facebook.com/latest/insights/content serves a full per-post table (views, reach,
interactions, likes, comments, SHARES, SAVES, link clicks, follows, watch time, avg play
time). scripts/ig_insights.py scrapes it (incremental collect while scrolling — the table
virtualizes like the reels grid; viewless remount-copies dropped at save) →
outbox/ig_insights.jsonl; runs after every post + 12:00/00:00 (scheduled_ig_stats.bat).
Session-expiry telems ig_insights_login (relink by hand once). FIRST SCRAPE HEADLINES
(n=44): shares+saves leaders are ALL rethink-era (sundew 12sh/12sv, desert_rosette
12sh/9sv, squid 7sh/10sv+14 follows, geode 5sh/10sv); mineral_heart converts follows at
8/577 views; avg-play-time on low-view old posts reads implausibly high (looping-session
artifact — trust ≥300 views).

# ═══════════════════════════════════════════════════════════════════════════════
# PLANET DESCENT — THE PLATE PLAN (2026-09-17; Phil: "plan before building")
# ═══════════════════════════════════════════════════════════════════════════════
Phil's problem statement: in nearly every video we go space → planet; planets have got
better at growing, but the SPACE BACKGROUND MORPHS INTO THE PLANETARY LANDSCAPE and the
planet fades or becomes a feature of that surface. Scope for now: top-down — arrive at a
spherical planet, zoom onto it, its surface becomes the next scene. No canyons/biomes yet.

## Ground truth (frame strips in scratchpad/strips/, 2026-09-17; read before re-deriving)
Eight planet approaches on disk: five plain mid-chain cards (saguaro_vigil, sargasso_windrow,
winter_murmuration, anvil_country, garnet_glass v1) and the three 08-31/09-01 hero-cn+persist-cn
test renders (gecko_rampart, natron_skein, lily_undercroft v2). Findings:
1. THE TRACKER HAS NEVER LOCKED A PLANET. Object-phase frames on the planet card = 0 in all
   eight (track.jsonl: miss/candidate only). natron v2's one lock was the SUN (size 0.71) and
   the plunge dove into it. Florence can't find "a blue planet" because there is none.
2. NO PLANET EVER FORMS. The "star/space" card is a texture field inherited from the previous
   card (spicule rays, foam, strata); at cfg 2.0 and travel denoise 0.40 the fed-back image
   owns the frame and a 4-token target inside a 60-token prompt cannot conjure an object that
   is not already in the pixels. Depth-CN from the feedback (approach_cn 0.45) then reinforces
   whatever texture is there. The arrival onto the surface is a texture→texture morph. This is
   why every WORD-side fix (globe clause, negatives, "one object dead centre") did nothing.
3. CAMEO TAKEOVER on 2 of 5 (saguaro f46-64, garnet f168-190): the mascot sprite grew into the
   dive. Which is also THE PROOF OF MECHANISM below — the one object that has ever persisted
   and grown through a planet card is the PASTED one.
4. THE RENDER_START HOLE (structural, never noticed): 27 of 53 planet cards are the
   render_start card. With the loop lap, that card's DELIVERED copy is the lap card, and the
   loop tail (L = 4 bars = 32 of its 35 frames) owns it: no tracker, no hero, IPA 0.22→0.95 +
   depth-CN 0.15→0.80 homing onto the trajectory of the WARM-UP copy (frames 3..34) — which is
   a cold txt2img establish of the star card (gecko: a river valley under the Milky Way). So
   for half the catalog the planet approach is, by construction, a conditioned crossfade
   toward a postcard, and the arrival re-play then morphs it into the surface. hero-cn is
   gated on `approaching` and could never have run there (gecko/natron v2: it fired only in
   the discarded warm-up copy).
5. THE HERO TEST WAS CONFOUNDED: persist-cn's resolve windows set approaching=False for the
   travel, so lily v2's planet card had a 2-frame approach (hero dir: 2 pngs). hero-cn + persist-cn
   on the same card cancel each other. Don't combine them again.

## What has been tried (by CHANNEL) and what has not
Tried: WORDS (T_TRAVEL object language, globe-in-void clause, HERO_NEG, T_ESTABLISH_SPACE);
STRUCTURE (depth-CN from the feedback; synthetic hero sphere + void-of-specks in the CN;
scaffold-as-CN through travel); WARPS (hero_orbit); TRACKING (v3, cadence, gates). All act on
the diffusion's steering; none puts the planet or the void INTO THE PIXELS the chain feeds on.
NOT tried: (a) supplying the pixels — a PLATE: a rendered sphere over a space plate composited
into the fed frame at the scheduled size every frame (the cameo mechanism, which provably
survives the zoom); (b) MASKED denoise — protect the void (SetLatentNoiseMask, the build-out
ring-mask plumbing already in build_workflow; DifferentialDiffusion for a graded mask) so the
space pixels are never re-diffused at 0.40 and CANNOT morph into landscape; (c) REGIONAL
prompts (ConditioningSetMask: void prompt outside the disc, surface prompt inside; IPAdapter
attn_mask for a regional reference); (d) bypassing the tracker on planet cards — we OWN the
sphere's position, so aim = its centre (fixed-point zoom), no Florence at all.
Nodes verified on disk 2026-09-17: SetLatentNoiseMask, DifferentialDiffusion, ConditioningSetMask,
ImageCompositeMasked, LatentCompositeMasked, GrowMask/FeatherMask, IPAdapterAdvanced attn_mask,
SAM3 (nodes_sam3.py), controlnet-inpaint-dreamer-sdxl (unused so far).

## The design — PLANET PLATE (a per-card mechanism for round targets, exp ≥ ~8 → next card 6-8)
1. PLATE, built once at the planet card's start:
   - SURFACE TEXTURE: one txt2img of the NEXT card's scene seen from directly above (that
     card already describes the world from orbit — cobalt's "a cobalt ocean world seen from
     orbit, sea ice broken into floes…"). Wrapped onto an orthographic sphere in numpy: lit
     from one side, limb darkening, thin atmosphere rim, slight barrel so the centre of the
     texture is what the zoom lands on.
   - VOID: the star card's own fed-back pixels (they are the space we want to keep) OR, when
     the card arrives as texture soup, a once-generated wide space plate (T_ESTABLISH_SPACE of
     the star card, no target). Under a pure zoom a starfield just spreads — no morph needed.
2. PER FRAME: sphere diameter s_j = s0·Πz (exact schedule; s0 = 1.05/Π remaining zooms, the
   hero formula) at a thirds anchor; aim = sphere centre (tracker OFF on plate cards). Disc
   interior = previous frame's disc interior propagated by the zoom (crop-and-reimagine INSIDE
   the disc, so its surface is alive and grows), blended toward the plate texture with a small
   decaying weight to keep identity. Composite → ONE img2img with a GRADED noise mask: ~0.45
   inside the disc, ~0.12 outside (shimmer only), feathered limb. Depth-CN = hero_depth dome
   (already built) so structure agrees with pixels. Optional regional prompts (inside: "the
   surface of {planet}, seen from orbit, curved limb"; outside: "black void of space, sparse
   stars").
3. HANDOFF: when the disc diameter ≥ ~1.15× frame the mask is full and the normal chain
   resumes; the boundary's arrival morph now starts from a frame that IS the planet's surface
   from above, so "the planet becomes the next scene" is the ordinary continuation. Top-down.
4. THE TAIL/LAP CASE: the plate runs inside the loop tail too (hero-cn did not). The plate is
   deterministic (journey-keyed seed), so the warm-up copy the tail homes onto is plate-rendered
   as well and the IPA reference trajectory AGREES with what the tail renders. Bonus: frame 0
   of a planet render_start becomes the plate composite, not a cold postcard.
5. CAMEOS never on a plate card (the takeover class) — composer rule + engine refusal.

## Lab before any adoption (Phil's standing format: single 12fps slow looped clips, judged alone)
Test beds, same seeds as the existing renders, --from-card + --no-loop: cobalt_rookery
cluster_sun→ice_world (his "sphere in an interesting void" case; render_start card, so ALSO
render it as the lap to exercise the tail) and saguaro_vigil star_spicules→desert_world
(mid-chain, cameo-takeover case). Arms, one variable each:
  A baseline (current engine) · B plate + global denoise 0.32 (the cameo mechanism, simplest)
  · C plate + graded mask (void 0.12 / disc 0.45) · D = C + regional prompts + hero dome CN.
GATE (measured, not eyeballed): sphere present from the card's first frame; disc radius per
frame tracks the schedule (measure it); void pixels stay void (edge density / luminance outside
the disc flat across the card); no planet-within-a-planet at handoff; limb reads as a limb; the
boundary lands on surface and the next card's arrival is clean. Failure modes to expect: a
mask-edge halo (feather + limb rim), a pasted/flat look (raise inside denoise), the disc read as
a hole/eye/cell (hero v1's caldera — regional prompt + dome CN are the counters).
Cost ≈ 30 frames/arm ≈ 8-10 min GPU/arm; the whole lab ≈ 1.5 h GPU. Nightly unaffected.

## Adoption path
Per-card `hero: "plate"` set by the composer (or auto for HERO_ROUND targets that descend to a
6-8 card) → full-journey A/B at the same seed → Phil's verdict → default for planet-class cards.
Until then: never run hero-cn and persist-cn together; audit_starts should WARN when the
render_start card's target is a round object (the lap/tail hole above) — Phil's call whether to
rotate those 27 starts to the preceding cosmic card now or wait for the plate to fix the tail.

## BUILT 2026-09-17 evening (Phil's go: "run the lab"; lab flags, default OFF, nightly byte-unchanged)
- engine/plate.py + dive.py `--plate {low,mask,region} [--plate-card K] [--plate-limb 1.15]
  [--plate-outside 0.27]`; build_workflow grew `diff_diffusion` (DifferentialDiffusion +
  SetLatentNoiseMask = per-pixel denoise) and `region` (ConditioningSetMask pair + Combine).
  Lab name suffix `_plate<mode>`; --from-card prefix still read from the unsuffixed source.
- scripts/plate_lab.py: arms A (source frames) / B low / C mask / D region, 12fps looped clips,
  SEQ cut, strip, measured gate (void edge/luminance outside the scheduled disc) →
  output/plate_lab/<journey>/. Test beds (Phil: nothing live/production): sargasso_windrow
  card 1 (star_comet_shoal → ocean_world) and garnet_glass card 5 (hourglass_binary →
  night_world), both in Review, both cameo-takeover cases in v1.
- SMOKE (6 frames, region arm): every node accepted; the diffusion KEEPS the composited disc as
  a sphere with a limb and the stars outside stay stars even at arrival denoise 0.58. Trap found
  + fixed: the size schedule must span the card's FULL compiled frames, not the --frames-
  truncated total (globe started at 1.77 instead of 0.23).
- FIRST FULL ARM (sargasso B/low, single-card plate, 13 min): A PLANET EXISTS FOR THE FIRST
  TIME — shaded sphere with limb, 0.24 → frame-filling on schedule, coast texture persisting,
  void staying space, no concentric-ring attractor. AND THE NEXT FAILURE, at the bar line: the
  next card is authored as the ORBIT VIEW ("seen from orbit ... stars beyond the rim"), so its
  arrival at 0.58 repainted the just-landed surface into space + a strip of blue marbles.
  FIX (v2, built same evening): THE PLATE SPANS THE BAR LINE — s_limb (1.15 x width, limb
  visible top/bottom in portrait = the orbit view) exactly at the boundary so the next card's
  arrival prompt MATCHES the picture, then the globe keeps growing through that arrival under
  the mask/composite until the frame lies inside the disc (`Plate.done`), and only then the
  next card's normal tracked approach takes over on the surface. sargasso geometry: size0
  0.115, bar line at f56 = 1.15, covered at f65 (9 frames into the next card), ~19 frames left
  for that card's own target. Resolve windows + cameos refused across the whole span.
- Lab v2 running from ~19:35: sargasso B/C/D then garnet C/D (~2.5 h GPU); clips in
  output/plate_lab/. Known open items for v3 if the clips ask for them: the void plate is
  zoomed by resampling each frame (stars soften over a card — a synthetic star overlay fixes
  it); the sphere reads dark (limb shading 0.22 ambient — lift if Phil wants it brighter);
  s_limb 1.15 makes the start 0.115 of the width (raise s_limb for a bigger first sighting);
  render_start planet cards (frame 0 = void plate + composite) untested; the loop-tail case
  (27/53 journeys) untested — plate is skipped inside the tail today.

## LAB RESULTS 2026-09-17 night (sargasso_windrow card 1 → ocean_world; garnet running)
Deliverables: output/plate_lab/sargasso_windrow/ — `*_SEQ_best.mp4` (A baseline → B → C → D one
after another, 12fps), `*_<arm>_best_loop.mp4` per arm, `*_strip_best.png`; the v2/v5 sets
are the earlier iterations. Run dirs: output/sargasso_windrow_plate{low,mask,region}/vN.
Iterations (each fixed one thing the frames showed):
- v1 single-card plate: planet exists + grows on schedule (FIRST TIME EVER); the NEXT card's
  orbit-view arrival repainted the landed surface → the plate now spans the bar line (v2).
- v2 spans the bar line: B clean end to end; C/D (mask arms, full denoise in the disc) locked
  into CONCENTRIC RINGS from ~frame 44; D also painted "a planet" INSIDE the disc from its own
  regional prompt and dove into that marble after the handoff. Globe read as a dark ball.
- v3/v4: revolution 1.5°/frame (texture + fed disc via warp.hero_orbit) — did NOT break the
  rings; two compounding darkeners found + fixed (per-frame limb-shade multiply; void plate
  blended over the whole frame incl. the disc); a 2:1 landscape texture canvas made SDXL paint
  a horizon seascape (v3) → square texture mirrored to 2:1 (v4).
- v5 (--plate-cn 0 on the mask arms): THE DOME CN WAS THE RING SOURCE — C has no rings with it
  off (the hero-cn "caldera" class: a radially symmetric depth signal under full denoise paints
  radially symmetric structure). What remains in C/D is WORDING: inside the disc C carries the
  star card's "comet heads sown through the black" (dotted skin); after the handoff the next
  card's "an ocean world seen from orbit" paints little worlds ONTO the surface at full
  denoise; D's "curving away to the limb of the world" re-creates a spiral at arrival denoise.
VERDICT (for Phil's clips): **B = plate + global denoise cap 0.32 + dome CN** is the working
configuration end to end — sphere with limb from 0.12 of the width, revolving top-down coast,
orbit view exactly on the bar line, the next card descends onto terrain with its own target.
Cost of B: the previous card's texture lingers in the void through the arrival (0.32 weakens
the arrival morph) and the globe's surface is calmer/flatter than full denoise would give.
NEXT if Phil approves the look: (1) card-after-a-plate REWORDING at compile time ("the surface
of {scene}, seen from straight above" in that card's arrival/travel/plunge) — the same
reinterpretation the texture uses; removes the object framing that C/D showed; (2) then retry
the mask arm with CN 0 + the rewording + a lower inside value (0.85) so the disc stays alive
without ringing; (3) a synthetic star overlay for the void (resampling softens the plate over a
card); (4) the loop-tail/lap case and render_start planet cards (frame 0 = plate) untested.

## GARNET + THE GATES (2026-09-17, 21:00–22:30) — second bed confirms B; two plate gates added
- garnet_glass card 5 (hourglass_binary → night_world), baseline = the mascot-face takeover.
  B (plate + cap 0.32, CN 0): green world with limb grows on schedule, orbit view on the bar
  line, hands off to night_world. C/D (mask arms, CN 0) STILL ring/iris → full denoise inside
  a fixed-point disc rings regardless of the CN; the dome CN made it worse on sargasso but is
  not the whole cause. VERDICT STANDS: B on both beds.
- TWO PLATE FAILURES, both txt2img priors, both now GATED (--plate-void-gate, Florence caption,
  seed re-roll x3, same defence as the frame-0 figure gate): (1) the VOID plate came back as a
  glass PENDANT ON A CHAIN ("A round pendant is hanging from a silver chain" — the jewelry
  prior; caught + re-rolled to a starfield); (2) the SURFACE plate came back as an AURORA OVER
  A SEA CLIFF (ground level, a horizon) → surface prompt is now "a satellite view looking
  straight down onto the surface of {scene}, a flat aerial map ... no sky, no horizon" +
  SURFACE_BAIT (sky/horizon/beach/cliffs/...) → v7's surface = the storm spiral + lamp-lit
  coast the card describes, top-down. VOID_NEG now also bans planet/moon/globe (the re-rolled
  void carried its own red moon + a blue limb).
- Deliverables sent to Phil: output/plate_lab/{sargasso_windrow,garnet_glass}/*_SEQ_best(_small)
  .mp4 + *_strip_best.png (A → B → C → D, 12fps). Run dirs: output/<journey>_plate<mode>/vN
  (sargasso B = platelow/v4; garnet B = platelow/v3 with both gates).
- ENGINE STATE: everything behind `--plate` (default OFF); nightly path byte-unchanged. The
  working recipe = `--plate low --plate-cn 0 --plate-void-gate` (spin 1.5°/f, limb 1.15,
  square-mirrored texture, no compounding blends). Sargasso B still used the dome CN at 0.45;
  garnet B used 0 — both fine in B, so CN 0 is the simpler default.
- NEXT (Phil's verdict first): (1) if the look is approved, wire B as the default for
  planet-class cards (`hero: "plate"` per card or auto via plate.is_plate_card) + make the
  gates default-on + a full-journey A/B at the same seed; (2) card-after-a-plate rewording
  ("the surface of {scene}, seen from straight above") so the next card stops painting worlds
  onto the surface at full denoise; (3) mask arm only if the alive-surface look is wanted:
  inside value ~0.85 + rewording; (4) loop-tail/lap case + render_start planet cards (frame 0
  = void plate + composite) untested; (5) synthetic star overlay for the void.

## WIRED INTO THE NIGHTLY (2026-09-17 ~23:00, Phil: "tonight's videos to use this new planet descent")
- journeys.json settings `plate_mode` (default "low"; dashboard ⚙ Settings "🪐 planet plate"
  low/off). night_batch passes `--plate <mode> --plate-cn 0 --plate-void-gate` to every render;
  journeys with no planet-class card print "no planet-class card in range" and render exactly as
  before. `dive --plan-only` prints the compiled plan (plates/cameos/resolve) without rendering.
- POSITION AUDIT (scripts/plate_position_audit.py): the plate spans the planet card + the next,
  so the planet card must sit at render-order index 1..n-2. The audit rotates `render_start`
  ONLY onto a cosmic/subatomic start (audit_starts FAR realm, score ≥ 2) with the seam mid-list
  and no single hard-edged subject — never onto an everyday wide shot (Phil: don't undo the
  start doctrine). APPLIED to 9 non-live journeys (anvil_country→ice_lattice, cherenkov_cistern→
  water_cages, cicada_chorus→chitin_ribbons, cork_dehesa→carbon_atom, gecko_rampart→shell_rings,
  kelp_dynamo→moon_swell, moon_jelly→dust_cocoon, prairie_town→hydrogen_haze, weddell_lightwell→
  spiral_galaxy); all 9 pass audit_starts + preflight (cicada: frame-0 bait note 'wing').
  NEEDS AUTHORING (planet card at the start, only everyday starts available — plate inert, they
  render as before): ammonite_spiral, girih_dome, hyperbolic_reef, lantern_canals,
  marigold_carousel, singing_dunes, skyfog, vernal_clutch (+ live ones untouched: glass_apiary,
  lantern_mangrove, natron_skein, sugar_nebula, butterfly_meridian, cinder_veil). Fix = give
  each a cosmic/subatomic card that can start, or move the planet card — composer work.
- CAMEO RULE: a cameo ON the planet card is refused (takeover class); a cameo on the NEXT card
  is DEFERRED to the first frame after the handoff (cork_dehesa's Janet). Cameo-on-planet-card
  journeys will render without a mascot — the composer skill should stop placing cameos on
  planet-class cards.
- TONIGHT (01:30): cork_dehesa (plate card 3 disk_galaxy→dusk_world, frames 96-159, bar line
  128, Janet deferred to ~137) + dugong_meadow (no planet card) + prairie_town (plate card 3
  dwarf_scatter→dusk_world). First full-length renders through the plate — the lab only ever
  rendered card spans with --no-loop. WATCH IN THE MORNING: outbox/night_batch.log for
  "plate void reads as an OBJECT"/"GROUND-LEVEL" re-rolls, plate.jsonl in the run dirs,
  the tail/lap interplay (plate frames inside the loop tail are skipped by design), and the
  captions (mascot present?). Budget note: plate frames cost ~+40% each (25 vs 18 s), ~+7 min
  per L journey — not in est_render_sec yet.
- UNCOMMITTED in the working tree: engine/plate.py (new), engine/dive.py, scripts/plate_lab.py
  (new), scripts/plate_position_audit.py (new), scripts/night_batch.py, scripts/pipeline.py,
  dashboard/app.py, 9 journeys' render_start, PLAN.md, CLAUDE.md.

## 2026-09-18 MORNING — the batch RAN, the ingest failed (lab suffix leak), recovered without re-rendering
The 01:30 batch rendered all three (cork_dehesa 5052s, dugong_meadow 4295s, prairie_town 4953s)
but queue_review reported "no complete render" for each and the batch marked them render_failed:
with --plate, dive.py suffixed the run name `_platelow` (the lab's separate-vN device), so the
renders landed in output/<journey>_platelow/v1 where neither queue_review nor has_complete_render
looks. FIX: the suffix now applies only to --frames lab runs. RECOVERY: the three run dirs were
moved to output/<journey>/v1 (mp4s + run.json name normalized, note in run.json), ingested with
queue_review + captioned, render_failed entries popped (state derives to rendered). All three are
in Video Review with engine_params.plate="low" (queue_review now carries plate/plate_cn/
plate_void_gate). FIRST FULL PLATE RENDERS LOOK RIGHT: cork_dehesa grows a banded world out of
the galaxy void to the orbit view on the bar line, hands off to dusk_world, Janet pastes right
after the handoff (deferred cameo works); prairie_town grows a dusty world out of the Milky Way
and lands on orange desert terrain. Both void/surface plates passed the gates first try.
LESSON: a lab-only naming device must be gated on a lab-only flag — the nightly runs the same
entry point. Verified this morning with --plan-only: run dir = output/<journey>/vN.

## 2026-09-18 — THE ARRIVAL: live void + absolute disc cap + GROW/ENTER introductions (Phil's review of the nightly plate renders)
PHIL: the descent "looks pretty cool" but the planet-in-the-void ARRIVES AS A FADE, not an
infinite zoom — jarring; and the globe must never "appear in the middle out of nowhere": it
should EXPAND FROM A POINT or COME IN FROM OFF THE FRAME, with variety. He wants to judge a
FULL video, not lab clips. DIAGNOSIS (arm B, by construction): the void plate was pixel-blended
(60% on the first frame, 25%/frame after = a fading photograph, the mechanism rejected for seams
in July); the whole span ran under the 0.32 cap, starving the arrival's live morph (normally
0.58 + prompt crossfade); the globe was pasted in one frame.
BUILT (mode `--plate live`, flags `--plate-intro {auto,grow,enter,plain}`):
- VOID HELD BY CONDITIONING: IP-Adapter toward the void plate, attention-masked to outside the
  disc (build_workflow `ipa_mask`), weight 0.25 → 0.60 across the arrival (the loop-tail homing
  idea). No void pixel blend in live mode. The void runs the schedule's own denoise incl. the
  arrival boost → the previous world re-imagines itself into the star scene while zooming.
- ABSOLUTE DISC CAP: graded mask inside = 0.30/den per frame (DifferentialDiffusion), outside
  1.0. LAB v8 proved a RELATIVE cap (0.8) fails: on the two arrival boosts the disc ran ~0.46
  effective → re-read as a lumpy rock, then a spiral lock. With the absolute cap the globe
  holds through both boosts (lab v9 enter: no rock, no rings).
- INTRODUCTIONS: size = s_limb·(Z_j/Z_card)^k (exactly s_limb at the bar line for any k).
  ENTER k=0.6: starts ~0.30 x width beyond a frame edge (right/left/top/bottom, journey-keyed
  hash), ease-out path to (0.56,0.46) by the bar line; the carried disc is TRANSLATED each
  frame (vacate disc + glow halo to the void plate, land the patch at the new spot) — LAB v9
  PASSED (globe rises into frame, live void, orbit view on the beat, clean handoff); a faint
  stripe "wake" under the moving globe → vacate radius widened 1.14R → 1.34R.
  GROW k=2.0 FAILED in lab v9: under a tenth of the width for 2/3 of the card, repainted over by
  the full-denoise void, then ~8 frames to reach the orbit view — never established (ghost
  sphere; bar line landed on a starry landscape). FIX (untested, lab v10 queued after the full
  render): k 1.5 (starts a visible dot ~0.036) + near-OPAQUE paste while size < 0.30.
  PLAIN k=1: the lab's arm B rate. `auto` = journey-keyed grow/enter variety.
- NIGHTLY PINNED to `--plate-intro plain` (settings key plate_intro, default plain) and
  plate_mode "low" until Phil has judged the full video — nothing untested ships overnight.
OPS: ComfyUI died 06:45 with "forrtl: error (200): program aborting due to window-CLOSE event"
— its console belonged to a terminal that got closed; every job rendering against it died
(live arm at 78/88). It now runs as its OWN minimized Windows process (PowerShell Start-Process),
and long jobs run in detached tmux sessions (plate_full, plate_grow2) so neither a closed
terminal nor a dead Claude session can kill them.
FULL-VIDEO TEST (Phil's ask): cherenkov_cistern (queued, never in production; planet card 5
flared_star → storm_world, frames 160-223, intro = ENTER FROM TOP), `--plate live --plate-cn 0
--plate-void-gate --plate-intro auto --seed 754920`, started 09:05, chain ingests to Video
Review + captions + consumes the registry entry (log output/plate_lab/full.log).

## 2026-09-18 (midday) — PHIL APPROVED THE LIVE DESCENT; play order fixed; fleet switched; extra batch running
PHIL on the cherenkov_cistern full video: "yes, i like it ... the fix is good and we should use it
in all future videos." His one issue: "the scale doesn't monotonically decrease and then loop back
to the biggest scale."
- CAUSE = OUR WORK, not the authoring: the position audit moved render_start (water_cages, 10^-8)
  so the plate could act, and the delivered video plays in RENDER order → the exotic wrap landed
  3 cards in. Authored order was right (10^12 ↓ 10^-15, wrap 0.9 → 16.5, loop into 12).
- FIX = PLAY ORDER ≠ RENDER ORDER: journey field `play_start` (the card the video OPENS on);
  dive.assemble(rot=) rotates the delivered loop so frame 0 = the first clean post-arrival frame
  of play_start (dive.play_rotation; uniform bars → a whole number of cards → music grid
  unchanged; the new wrap joins two consecutive chain frames; the render's own lap seam lands
  mid-video). `dive.py <journey> --reassemble vN` re-runs ONLY the assembly (no GPU).
  plate_position_audit now records play_start = the old render_start whenever it rotates; the 9
  already-rotated journeys got theirs. cherenkov_cistern v1 re-assembled (rot 128f = 4 cards),
  verified by sampled frames (opens 10^12 with the globe entering, ends on the 10^16.5 echo
  shells wrapping into the opening), re-ingested to Review, captions kept.
- AUDIT v2: a start card counts as FAR when the engine itself says so (exp ≥ 6.5 or ≤ −6 — the
  spaceless-establish rule), not only by wording → vernal_clutch + singing_dunes rotated too.
  Still NEEDS AUTHORING (only everyday alternative starts): ammonite_spiral, girih_dome,
  hyperbolic_reef, lantern_canals, marigold_carousel, skyfog (+ live: butterfly_meridian,
  cinder_veil, glass_apiary, sugar_nebula).
- FLEET: settings plate_mode="live", plate_intro="enter" (edge varies per journey: right/left/
  top/bottom). GROW is NOT in production: lab v10 (k 1.5 + opaque while small) establishes the
  globe but it is invisible for its first third in a busy void and gets re-read as a lumpy ball;
  v11 (opaque until 0.5 x width, grow only) runs automatically after the extra batch (tmux
  plate_grow3). Dashboard Settings: plate knob = live/low/off + "how the globe arrives".
- REVIEW PURGE (Phil: "any videos without the fix ... back in the rendering queue"): the 7 Review
  videos with a planet descent rendered the old way → video rejected, journey re-queued at the
  FRONT, force, SAME seed: cork_dehesa, sargasso_windrow, garnet_glass, gecko_rampart,
  cicada_chorus, anvil_country, vernal_clutch. LEFT IN REVIEW: the 6 with NO planet card
  (plasma_script, phage_landing, venus_basket, pika_larder, locust_sorghum, dugong_meadow) —
  the fix has nothing to act on, a re-render would be identical work — and cherenkov_cistern.
- EXTRA BATCH started 11:37 in tmux `extra_batch` (log outbox/extra_batch_0918.log): cork_dehesa
  + sargasso_windrow + garnet_glass, `--plate live --plate-cn 0 --plate-void-gate --plate-intro
  enter`, ~5.1h. Tonight's 01:30 batch continues down the queue (gecko_rampart, cicada_chorus,
  anvil_country, vernal_clutch next).

## 2026-09-18 (afternoon) — THE BORDER ROUND THE GLOBE (Phil: "a bit of a border ... some space between the void and the planet ... doesn't look great")
WHAT IT WAS (limb crops of the cherenkov full render): not the rim line — a dark EMPTY MOAT,
0.15-0.3 R wide, between the limb and the surrounding star field. CAUSE: the enter path's vacate
step cleared a disc 1.34 R wide back to the dark void plate on EVERY moving frame, overwriting the
live void around the globe; the wide rim glow (sigma 0.05R, alpha 0.85) was what had forced that
wide clear (the earlier "stripe wake").
FIX (engine/plate.py): THIN RIM (atmosphere line 0.012R at 0.35, outer glow sigma 0.012R at alpha
0.40, feather 0.012R); VACATE ONLY THE CRESCENT the globe actually left = old disc (its TRUE
previous radius x this frame's zoom, +5%) MINUS the new disc; the moved patch is cut at the old
radius (cutting it at the new radius pasted a sliver of old surroundings outside the limb each
frame = a stack of trailing arcs — caught in CPU simulation before any render used it, except
~10 min of a sargasso render that was killed and restarted); mask feathers 14/10px -> 6px.
VERIFIED ON CPU (entry path over a bright busy background + dark plate, with a stand-in for the
void's re-diffusion): ring just outside the limb 0.44/0.42 (leading/trailing) vs far field 0.49 —
was plate-black; no arcs. NOT yet seen through diffusion: first renders with it = the restarted
extra batch (13:57, tmux extra_batch, log outbox/extra_batch_0918b.log): sargasso_windrow +
garnet_glass + gecko_rampart + lissajous_stage. cork_dehesa rendered at 11:37 with the OLD wide
vacate (moat) and is in Review as v2; tmux `after_batch` regenerates it from its planet card on
(`--from-card 3`, same flags) as soon as the batch exits, re-ingests it, then runs the grow lab
v11 (k 1.5, opaque until 0.5 x width, thin rim). Log output/plate_lab/after_batch.log.
OPEN ITEMS FOR THE NEXT SESSION: (1) judge the border fix + grow v11 in the new renders;
(2) card-after-plate rewording (untested); (3) the 6 queued journeys that NEED AUTHORING (planet
card at the render start, only everyday alternative starts); (4) render_start planet cards /
loop-tail plate (frame-0 path exists, untested); (5) est_render_sec does not know the plate's
~+7 min per long journey; (6) grow introduction not in production (settings plate_intro=enter).

## 2026-09-18 (14:20) — THE TRAIL UNDER THE ENTERING GLOBE (Phil caught it live in the ComfyUI outputs)
The crescent-vacate fix removed the moat but exposed the SAME root cause in a new shape: the
vacated space was filled with the DARK VOID PLATE, and in sargasso's bright ray field the dark
slivers stacked up behind the rising globe as a ribbed dark column (DepthAnything even read it
as a solid stalk). RULE: a vacated region is filled with the LIVE VOID, never the plate —
mirror the fed frame across the old limb (pixel d inside the old edge takes the void pixel d
outside it, same radius); samples that clamp at the frame border and land back inside a disc
(an entering globe still overlaps its edge) take the mean of the true void instead (they had
replicated the globe's edge row into a stem); clear to 1.12 R_old so the old limb's edge line
goes too (a wider clear cannot carve a moat once the fill is live void). CPU worst-case sim (no
healing at all, bottom + right entries over a bright ray field): no column, no stem, no arcs.
Batch restarted a second time at 14:18 on this code (log outbox/extra_batch_0918c.log).

## 2026-09-18 (15:15) — ENTRY TRAIL: VERIFIED UNDER DIFFUSION (sargasso_windrow v2, frames 28-60)
Third iteration of the vacate step, and the one that holds: DIRECTIONAL fill (each vacated pixel
takes the void found by walking along the trailing direction to just past the old disc's edge),
soft 14px edge on the cleared region, EVEN entry pace with a soft landing. The mirror fill (v2)
had left a circular echo that the model painted as a glassy bubble under the rising globe; the
plate fill (v1) a dark ribbed column; the 1.34R clear (v0) a moat. In the real render the ray
field now runs right up to the limb on every side with no column, bubble, moat or arcs, and the
orbit view still lands on the bar line. RULES LEARNED: never put void-PLATE pixels into the live
frame; never leave a circular/symmetric patch for the model to read as an object; keep per-frame
globe motion small. The extra batch (third start 14:47, log outbox/extra_batch_0918d.log) and
every later render use this code (commit 45f45b4).

## 2026-09-19 — MUSIC: the "phrases off the bar" false alarm (Phil on sargasso_windrow: "none of them sit, or they don't have beat")
GROUND TRUTH FIRST (accent offsets on the finished aligned videos, all 11 morphs): ember_pulse-wild
-24..+2 ms (spread 7 ms, no drift); pulse1-deep_archive -45..+10 ms; deep_archive-heartbeat 9 of 11
within -14..-40 ms; the two wildcards scattered +-285 ms (genuinely beatless). So generation was
fine for 3 of 5 — the LABEL and the SELECTION were wrong:
1. align.meter_fit (mine, 09-10) sampled the autocorrelation at the video's NOMINAL bar on the
   UNSTRETCHED track, a line before measure_bar. ACE-Step lands 1-2% off the requested tempo (the
   stretch step exists for that) and ac peaks are hundredths of a second wide → a clean 4/4 take
   with a 2.283s bar read ~0 at 2.333s, and its true multiples (3 bars = 6.859s) failed the
   commensurability test and counted as RIVALS. Every strong-beat take got fit ~0.1. (The 09-10
   audit had scored fit on the ALIGNED audio, where the bar is exact — so it looked validated.)
   FIX: meter_fit(ref=measured bar), numerator = the peak within +-1.2% of it.
2. The rank penalty (scales with kick x misfit) then pushed strong-beat takes below beatless
   wildcards; AND the lane-spread rule (max 2 per lane) seated 0.17/0.14-score beatless takes
   ahead of 3.23/2.17-score own-lane ones. FIX: _keep_spread — a take may claim a spread seat
   only if it scores >= 35% of the best.
3. `music_gen.py <journey> --rerank` (NO GPU): re-judges EVERY raw take on disk (kept + discarded;
   raw flacs stay in output/music/) and keeps the best n. sargasso_windrow re-ranked: all five
   now have a beat (kick 0.38-0.79), four fit >= 1.09. The 10 other Review videos with pregen are
   being re-ranked in tmux `music_rerank` (log output/plate_lab/rerank_all.log).
ALSO 09-19: dashboard approve_to_music no longer gates the no-GPU realign on comfy_busy (that is
why Phil could not pick music during ~20h of renders); nightly rendering is NOT paused.

## 2026-09-19 — "HOW IT WORKS" TAB + GROW v12/v13 + vernal_clutch note
- OVERVIEW TAB (Phil: "a big visual, graphically organized overview of everything ... to show it
  off"): dashboard tab 9 "🧭 How it works" renders dashboard/overview.html, built by
  scripts/build_overview.py (self-contained: inline CSS + hand-authored SVG + 5 real frames as
  base64; follows light/dark; ~6900px tall at 1240 wide). Seven figures, one claim each: the daily
  loop · a journey as a circular chain (play start / render start / seam) · inside one card (zoom
  + denoise curves COMPUTED from the engine formulas) · the frame loop · the planet descent
  (real cherenkov frames) · closing the loop + play order · music alignment; then an index of
  ~45 technologies with purpose + file. Static by design for now: re-run the script to refresh
  counts/frames. Checked by headless-Edge screenshots in light and dark. GOTCHA learned: a CSS
  text-anchor rule beats the SVG attribute, so per-label alignment must be an inline style.
- vernal_clutch (Phil: "the planet stretched out horizontally and faded into space"): its planet
  card is `star_floor`; once the globe is wider than the portrait frame its limbs are gentle
  arcs and the "floor" reading flattened them into a horizon. GUARD: plate.GLOBE_NEG (horizon,
  floor, ground plane, landscape...) in the negative while the globe is an object. Composer
  note: avoid floor/plain/horizon words on the card that targets a planet.
- GROW: three fixes built (Phil's go): (1) point-of-light GLINT under 40px radius — a
  MAX-composite (additive light accumulated into a white bloom in CPU sim: every frame feeds the
  next); (2) MIN_CAP_PX 34: the protected low-denoise zone never shrinks below that radius;
  (3) identity hold >= 0.6 until 0.6 x width. LAB v12: glint fires (brilliant star at f32) but is
  inconsistent — at 0.30 effective denoise a point is re-read as one more glowing dot; globe then
  appears clean at ~97px. v13 (running): Plate.cap_now() = 0.12 while under GLINT_PX easing to
  0.30 by 2x, slightly larger/stronger glint. Production stays plate_intro=enter until a grow
  version passes.
- GROW v13 RESULT (2026-09-19, clip sent to Phil: output/plate_lab/sargasso_windrow/
  sargasso_windrow_plate_live_v13grow_loop.mp4): with cap_now() 0.12 in the point phase the globe
  no longer pops — a soft glow forms (f32-36), condenses into a translucent sphere (f38), a solid
  banded globe by f40, orbit view on the bar line, clean landing. STILL OPEN: (a) the first ~4
  frames show nothing (the arrival morph at full boost owns them; the point could start a beat
  later, after the arrival); (b) the glint reads as a soft glow, not a crisp star point; (c) the
  globe's look still drifts banded → cratered with a dark hollow on the unlit side (shading
  ambient / identity). Awaiting Phil's verdict before it joins `auto`; production stays `enter`.

## 2026-09-19 (afternoon) — GROW v14/v15 + UNIFIED ENTRANCES (Phil: "combine grow and enter tech so we can start anywhere in frame or come in from any direction with a small planet and grow it — key is most possible variety of entrances")
- GROW v14 (lab sargasso card 1, run sargasso_windrow_platelive/v8, clip ..._live_v14grow_loop.mp4):
  the point is now INTRODUCED AFTER THE ARRIVAL (Plate.small_start / hold = fa / introduced — the
  arrival morph at full boost owned the first frames and a point could not compete), crisp star
  glint, brighter night side while small (ambient 0.60 -> 0.38 by 0.8 x width), cap_now() 0.08-0.12
  in the point phase, k 1.75. RESULT: the sequence reads point (f36-39) -> small disc (f40) ->
  growing globe -> orbit view on the bar line -> clean landing (covered f62). TWO FLAWS, both
  diagnosed from the frames and fixed for v15:
  (a) THE POINT WAS DIM in the delivered frame though bright on the composite: a 1.7 px gaussian
      loses ~60% of its peak in one VAE round trip (8x latent) and the scene's own stars outshone
      it. v15 = flat-topped core (1.8 x a 2.6 px gaussian clipped at 1), whiter tint.
  (b) "THE DARK BITE OUT OF THE SPHERE" (reported in v12, v13 AND v14 as shading/identity drift —
      WRONG, it is the TEXTURE): sargasso's surface texture has a near-black river over 16.5% of
      its area (lum < 0.10), and black-on-black against the void reads as a missing chunk. Fix =
      plate.lift_darks() in set_assets: luminance under 0.28 compressed toward it (L=0 -> 0.18) in
      the pixel's own hue. Applies to EVERY plate (enter too) — a globe never carries void-black.
- UNIFIED ENTRANCES (built, CPU-simulated, lab running): plate.draw_entrance(key, w, h, s_limb,
  z_card, kind=None) describes EVERY arrival with four things — start (in frame, or beyond ANY
  point of the frame boundary via perimeter_point, not four edges), goal (a central region, never
  dead centre), k (growth law: 0.6 = already a globe, 1.0 = zoom rate, 1.75 = a point of light)
  and bow (sideways arc of the path, fraction of its length). Kinds: `enter` (k 0.6 from off-frame
  = the approved mechanism, now from any direction) · `grow` (k 1.75, swells IN PLACE at a drawn
  point, keeps the spiked star glint) · `travel` (k 1.10-1.45 = a SMALL disc that comes from
  off-frame, or crosses the frame, while it grows). Draw = deterministic crc32 of
  "journey:card:seed", weights 3 enter / 3 grow / 4 travel. Plate takes `entrance=`; aim()'s path
  now runs for any start != goal FROM THE INTRODUCTION FRAME to the bar line (even pace + soft
  landing, as approved for enter); legacy intro names (enter/grow/plain) are byte-for-byte the
  approved behaviour. dive: --plate-intro mix | travel | mix-enter | mix-grow, plus
  --plate-entrance-seed N for labs.
  MOVING POINTS: a travelling globe that still wears its glint gets a TIGHT halo and no spikes
  (Plate._mover_halo), and the vacate step clears R_old + 2 sigma behind it — otherwise every
  frame leaves a soft star behind (a string of pearls trailing the traveller).
  CPU worst-case sim (no diffusion, so leftovers stay visible): scratchpad entrance_sim.py —
  six draws all reach s_limb on the bar line, max path speed 22-29 px/frame (approved enter = 29).
- LAB RESULTS (sargasso card 1, live, --plate-intro mix --plate-entrance-seed N; clips in
  output/plate_lab/sargasso_windrow/ tagged v15_*; all sent to Phil):
  · v15_grow (seed 31, swells in place at (0.37, 0.57)): star point f35-38 now reads in the
    delivered frame, ghost disc f39, small planet f40, smooth growth, orbit view on the bar line,
    covered f62. The dark bite is GONE (the river reads as a blue sea). Grow is ready to join the
    rotation.
  · v15_travelA (seed 0, k 1.44, from beyond the left edge at 0.71 H, bow -0.16): the small disc
    enters at f38-40, grows while it crosses, orbit view on the bar line, covered f62. No pearl
    string, no stalk. NOTE a broad translucent band is born at the entry point before the globe
    shows (f35-36) and the model later textures it like the globe: it is the ENGINE's own habit —
    new large structure is always born at the zoom's fixed point, and during the hold the fixed
    point sits at the (off-frame) start. v15_grow has the same band behind its point. It reads as
    a nebula/ring behind the planet, not as a defect; if Phil dislikes it the lever is to keep the
    zoom's fixed point at the GOAL until the globe is big enough to cover it.
  · v15_travelB (seed 9, k 1.14, IN-FRAME start at the top, bowed) — FAILED, and the failure
    reshaped the design. The globe grew a barrel-shaped tail on its trailing side (f40-45) that
    became a glassy ghost sphere (f46-49). MECHANISM: a small fast globe vacates a crescent a
    quarter of its own radius thick every frame; the directional pull smears the pixels right
    behind the old limb across it, the model repaints the smear as MORE GLOBE (worst when the
    trailing limb is the dark side — no edge contrast), and once a tail exists the pull copies
    the tail, so it feeds itself. travelA survived only because its trailing limb was the lit one.
- RIDE THE FLOW (the fix, plate.Plate.aim for drawn entrances): in a zoom-in everything streams
  outward from the zoom's fixed point. Instead of making the globe the fixed point and TRANSLATING
  it against the void, put the fixed point where the stream itself carries the globe from where it
  is to where the path wants it: P = (z*old - des)/(z - 1), confined to the frame (= the crop
  clamp). Globe and void then move TOGETHER: no crescent, no fill, nothing to repaint. In-frame
  starts use FLOW PACE (path progress = (Zcum - 1)/(Zpath - 1)), which makes a straight path
  exactly one fixed P behind the start — residual translation 0.0 px on every frame (measured).
  Off-frame starts move against the stream until they are far enough inside: residual 17-24
  px/frame falls to 0 within 14-18 frames for top/bottom entries, and to ~10-12 for left/right
  ones (the stream is weak near the side it came from). The remainder is filled by
  Plate._void_copy: ONE translated copy of clean live void for the whole crescent (16 directions
  x 2 distances, in frame, clear of both discs, away from the trail), the pull as fallback when
  the globe is too big for a clean region to fit. The zoom's fixed point hands back to the globe
  at the bar line, when the globe already spans the frame. Legacy enter/grow/plain untouched.
  LAW WORTH KEEPING: in this engine nothing can ENTER the frame with the stream — entering is
  always against it; drifting outward from any in-frame point is free.
- v16 RESULTS + THE k < 1 LESSON:
  · v16_travelB (seed 9 in-frame start, flow-riding): CLEAN — a round planet on every frame, no
    tail, no ghost; it appears beside the galaxy and drifts down into place as it grows, the void
    moving with it; bar-line handoff and landing clean (covered f62). Clip sent to Phil.
  · v16_enterBottom (k 0.6, flow-riding) FAILED from the frame the residual reached zero: a
    STRIPED GLASS COLLAR round the globe. A globe that grows SLOWER than the zoom (k < 1) sheds a
    thin annulus of itself every frame (the crop magnifies the carried disc by z, the schedule
    wants z^k). The approved enter clears that annulus as a BY-PRODUCT of translating the globe;
    remove the translation and the annuli pile up. A radial pull to clear them drew a sunburst in
    CPU simulation. RULE: ride the flow ONLY where it is exact, k >= 1 (travel, grow). k < 1
    entrances keep the APPROVED aim + vacate unchanged; only their geometry is drawn — any
    perimeter point, a goal pulled toward the side they came from, and a 430 px PATH BUDGET (the
    portrait frame makes a top/bottom entry twice the approved 350 px; over budget, the globe
    starts partly in view inside the arrival morph), straight paths only.
- DRAW v2: travel = 50% in-frame drifts that start 7-17% inside ANY boundary point (with the
  stream's fixed point P = S - (G - S)/3 verified inside the frame) + 50% off-frame; spin drawn
  1-2 deg/frame in EITHER direction; light from the left, right or above. dive --plate-entrance
  '<json>' pins an exact entrance so a lab no longer depends on the draw. Round 3 labs (v17_*):
  enterBottom (seed 4), travelA (the old off-frame left draw, pinned), driftC (seed 3: in-frame
  from the lower right, spin reversed).
- v17 RESULTS (round 3, the design as shipped):
  · v17_enterBottom (k 0.6 from below, lit from above, approved mechanics, 430 px budget): clean
    rise, orbit view on the bar line, clean landing (covered f62), NO collar. In this busy void the
    model bends the filaments into concentric rings round the rising globe (f35-50, gone by the bar
    line) — the radial-symmetry habit of a stable object at the zoom's fixed point; reads as
    orbital rings. Flagged to Phil for his eye.
  · v17_travelA (pinned off-frame left, k 1.44, flow-riding + void-copy for the remainder): clean
    from entry to landing — round on every frame, no tail, and the v15 band at the entry point is
    gone too.
  · v17_driftC (seed 3: in-frame start lower right, k 1.33, spin -1.23, lit from the upper right):
    clean from the point of introduction to the landing (covered f64); reversed spin and the drawn
    light both work. Residual translation 0 px on every frame.
- STATE: all five kinds of arrival have a passing lab on sargasso card 1 — grow in place (v15_grow),
  in-frame drift (v16_travelB, v17_driftC), off-frame small traveller (v17_travelA), big globe from
  any edge (v17_enterBottom). Clips sent to Phil. PRODUCTION STAYS plate_intro="enter" until he
  approves; the switch is Settings → "how the globe arrives" → mix (night_batch passes the setting
  straight to --plate-intro). NOT YET TESTED: a full-length render through `mix`; a second test
  bed (all labs are one card of one journey); the est_render_sec plate term.
