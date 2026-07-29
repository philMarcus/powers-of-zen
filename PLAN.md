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
City Kitty, Planet Janet, Star Lamar, Galaxy Maxie, Cosmos Amos. One hidden
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
Halted 2026-07-27 (was burning premium budget + would post unapproved). Resumes only
once the LOCAL harness exists AND posts are Phil-approved. Cold-start underperformance
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
- Live: posted + 3 platform links (view-count slot, filled later if safe)
- Journeys pending: (once composer exists) drafts to skim/edit/approve pre-render
- Telemetry: recent activity, failed posts, failed renders, flags

**Scheduler — WINDOWS-SIDE (Phil's choice 2026-07-27; his autonomy was a Windows script,
more stable than WSL cron/daemon which idles out). Windows Task Scheduler runs a script at
08:00/18:00 that (a) ensures Chrome-zen is up, (b) calls `wsl … python3 scripts/poster.py`.
COST-CRITICAL: NO Claude in the loop — poster.py is standalone (reads pipeline.json, posts
next approved, writes telemetry), always-on cost = electricity only. Claude appears ONLY for
caption-writing + journey composition. Task Scheduler also wakes WSL (solves idle-shutdown)
and survives reboots. Phase-2 hook: if queue low → ping composer.

**Folder rule (corrected):** production/ = ONLY the exact postable file (chosen cut of chosen
model) for queued/live videos. production_alternates/ = other model (both cuts) + the OTHER
cut of the chosen model. Fix promote.py to take cut direction (currently over-includes both
cuts of chosen model).

**View counts:** HOLD (scraping is fiddly + mild ban-risk on new accounts). Revisit at volume.

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
