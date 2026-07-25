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
- Ollama on Windows host, reachable from WSL at `http://192.168.68.1:11434` (~15 models incl. deepseek-r1, qwen3.6:27b).
- ComfyUI: Windows install at `/mnt/c/Users/Phil/ComfyUI`, started via
  `/mnt/c/Users/Phil/start_comfyui.sh` (tmux session `comfy`); **API reachable from WSL at
  `http://localhost:8188`** (v0.22.0, Windows box has 64GB RAM). Checkpoints available:
  `FLUX1\flux1-schnell-fp8.safetensors`, `SDXL-TURBO\sd_xl_turbo_1.0_fp16.safetensors`,
  `dreamshaperXL.safetensors`. No video/zoom custom nodes yet (hand-rolled feedback loop
  via API may not need them).
- GPU: RTX 3080 10GB — SDXL-Turbo feedback zoom comfortably; Wan 2.2 5B FP8 / LTX-2 NVFP8 feasible.

## Open questions (park until relevant)

- Channel name/brand (needed at account creation, Phase 1).
- Which zoom-engine node wins (FL_InfiniteZoom vs Deforum-for-ComfyUI vs hand-rolled
  img2img feedback loop — the hand-rolled option gives most control over prompt schedules).
- Best loop-seam trick for feedback zooms (end-world morphs back into start-world).
- Whether TikTok Content Posting API approval is worth pursuing at volume.
