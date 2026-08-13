---
name: audience-stats
description: Snapshot and analyze Powers of Zen audience performance — followers, views, likes-per-view per video, and which variables (tier, style, palette, music, engine) move engagement. Use when asked how videos are performing, what's working, to take a stats snapshot, or to re-test a style/format hypothesis against data.
---

# Audience stats — snapshot, analyze, interpret

The PRIMARY metric is **qscore** (Phil's insight, 2026-08-13): actual engagement (likes +
3×comments) divided by the catalog's own fitted scaling law `a·views^b`. IG distributes in
stages — early views hit warm audience, pushed batches are colder — so like-rate mechanically
DECAYS with reach (fitted: 2.7% at 150 views → 1.4% at 2000, b≈0.7). Raw likes/view therefore
punishes exactly the videos that EARNED a push; views are a success signal, not just a
confound. qscore = 1 is catalog-typical at that reach, ≥1.5 strong, ≤0.7 weak; the exponent
re-fits from the data every run (`--alpha` overrides: 0 = pure like-rate, 1 = raw likes).
Keep pooled like-rate + CI for significance calls. Follower growth is the GOAL metric, read
from the snapshot series.

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
- **Rank by qscore, claim significance by CI.** qscore absorbs reach (no outlier exclusion
  needed); the binomial CI machinery only exists for like-rate, so group contrasts are
  "real" only when pooled like-rate CIs separate OR a qscore gap persists across snapshots.
- **Low-view rows are jumpy under qscore.** At <100 views one comment swings the score
  (the +0.5 smoothing and 3× comment weight are large relative to tiny counts) — read
  sub-100-view qscores as provisional.
- **Pooled rate + 95% CI, or don't claim it.** A single video at ~150 views carries ±1.3pp of
  binomial noise — per-video like% differences under ~2pp are meaningless.
- **Check confounds before crediting a variable.** Style, tier, palette and subject travel
  together (e.g. candy_gloss journeys were also pale AND sphere-subject). Say which variables
  co-move; prefer the one with the mechanism.
- **Correlation strengths at n≈30 are direction, not law.** |r| ≥ 0.3 with a mechanism =
  actionable; below that, wait for more snapshots.
- **A push without likes may be a RETENTION push.** Reels distribution weights watch-time/
  loops as much as likes; a video whose views keep climbing while likes stall is holding
  viewers, not failing (cave_of_numbers pattern). The snapshot SERIES separates the two:
  like-velocity early vs view growth late.

## 4. Where findings go
- Actionable style/composition findings → `journeys/VARIATIONS.md` "PERFORMANCE NOTES" (the
  refill coordinator reads it) and the journey-composer skill if it changes an authoring test.
- Deck retirements: set `retired` on the entry in `styles/deck.json` + drop it from the
  composer skill's list (keep the entry itself — legacy renders reference it).
- Big shifts (tier_share, templates) → dashboard Settings / `outbox/journeys.json`, and note
  the change + the evidence in CLAUDE.md's current-state.

## Current standing findings (2026-08-13 baseline, n=31 reels, 33 followers)
Dark+saturated beats pale high-key and STRENGTHENS under qscore (sat +0.34 / lum −0.33 /
dark-frac +0.29); tier by qscore: L 1.36x > M 0.98x > S 0.92x (longs EARN pushes; shorts'
decent like% never converts to reach); candy_gloss retired (0.22x sugar_nebula = catalog
worst); full-scale span shows NO effect (don't mandate it); cut (divein/zoomout) no effect;
engine-2 ≈ engine-1 on like% so far; cave_of_numbers reads ~1.0x once comments + earned reach
count (the old like%-only read undersold it). Re-test all of these as snapshots accumulate —
they are baselines, not laws.
