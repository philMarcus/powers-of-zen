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
