---
name: audience-stats
description: Snapshot and analyze Powers of Zen audience performance — followers, views, likes-per-view per video, and which variables (tier, style, palette, music, engine) move engagement. Use when asked how videos are performing, what's working, to take a stats snapshot, or to re-test a style/format hypothesis against data.
---

# Audience stats — snapshot, analyze, interpret

The METRIC is **likes/view** (age-independent; views only accumulate). Follower growth is the
GOAL metric, read from the snapshot series. Never rank videos by raw views — reach is the
algorithm's choice, not content quality.

## 1. Snapshot (data collection)
```bash
python3 scripts/ig_stats.py            # appends one row per reel to outbox/ig_stats.jsonl
```
- Needs zen Chrome up (`scripts/start_chrome_zen.sh`, CDP :9222). The tool opens its OWN tab
  and closes it — the poster's platform tabs are untouched.
- Likes/comments come from a trusted-CDP hover over each reels-grid tile (Phil's method — the
  overlay is CSS :hover, synthetic JS events do NOT trigger it); page visits only as fallback.
- Follower count rides along on every row → follower-over-time and per-post deltas come free.
- Snapshot cadence: daily is plenty. More often adds noise, not signal.

## 2. Analyze
```bash
python3 scripts/ig_analyze.py --features
```
Groups by tier/style/scale-span/engine/cut/music-mood, and `--features` measures each posted
video's frames (luminance, saturation, contrast, dark-fraction; cached in
outbox/video_features.json) and correlates each with like%.

## 3. Interpretation doctrine (apply as tests — this is where analyses go wrong)
- **Exclude reach outliers from contrasts.** like% FALLS with reach (pushed reels hit colder
  audiences) — one viral reel dominates any pooled bucket it lands in. The script excludes
  views > 1000 and lists them separately; read them as their own reach story.
- **Pooled rate + 95% CI, or don't claim it.** A single video at ~150 views carries ±1.3pp of
  binomial noise — per-video like% differences under ~2pp are meaningless. Call a group
  contrast real only when the CIs separate; otherwise report it as directional.
- **Check confounds before crediting a variable.** Style, tier, palette and subject travel
  together (e.g. candy_gloss journeys were also pale AND sphere-subject). Say which variables
  co-move; prefer the one with the mechanism.
- **Correlation strengths at n≈30 are direction, not law.** |r| ≥ 0.3 with a mechanism =
  actionable; below that, wait for more snapshots.
- **Two metrics, two stories.** likes/view = content quality; views/reach = algorithm +
  follower conversion. Don't mix conclusions across them.

## 4. Where findings go
- Actionable style/composition findings → `journeys/VARIATIONS.md` "PERFORMANCE NOTES" (the
  refill coordinator reads it) and the journey-composer skill if it changes an authoring test.
- Deck retirements: set `retired` on the entry in `styles/deck.json` + drop it from the
  composer skill's list (keep the entry itself — legacy renders reference it).
- Big shifts (tier_share, templates) → dashboard Settings / `outbox/journeys.json`, and note
  the change + the evidence in CLAUDE.md's current-state.

## Current standing findings (2026-08-13 baseline, n=31 reels, 33 followers)
Dark+saturated beats pale high-key (lum −0.33 / sat +0.24 / dark-frac +0.28); L > S > M by
tier (L 3.29±0.68 vs M 1.66±0.69); candy_gloss retired at 0.93% pooled; full-scale span shows
NO effect (don't mandate it); cut (divein/zoomout) shows no effect; engine-2 ≈ engine-1 on
like% so far. Re-test all of these as snapshots accumulate — they are baselines, not laws.
