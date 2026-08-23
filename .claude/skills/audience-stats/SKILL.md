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
- Snapshots run automatically THREE ways (Phil 2026-08-22 — count more often than the 19h
  post cadence): after every post (poster.py, passing `--force`), and at 12:00 + 00:00 via
  the `PowersOfZen-igstats` Task Scheduler job (two triggers, hidden runner —
  scripts/SCHEDULER.md; log: outbox/ig_stats_task.log). Each saved snapshot emits an
  `ig_stats` telemetry event.
- ig_stats.py self-heals a down Chrome (same start_chrome_zen.sh contract as the poster),
  locks against overlapping scrapes, and SKIPS if a poster/gate run is in flight (`--force`
  overrides — the poster's own end-of-run snapshot uses it). It opens its OWN tab and closes
  it — the poster's platform tabs are untouched.
- Likes/comments come from a trusted-CDP hover over each reels-grid tile (Phil's method — the
  overlay is CSS :hover, synthetic JS events do NOT trigger it); page visits only as fallback.
  Tiles are tagged INCREMENTALLY while scrolling (2026-08-22): IG virtualizes the grid, and a
  tag-after-scrolling pass lost the newest reels when the grid top unmounted (coverage was
  21–28 of 43; now 36+). The hover pass re-finds each tile by shortcode + absolute page-Y.
  Rows that learned nothing (no view count) are dropped at save — a viewless row would
  shadow the reel's last good snapshot in the analyzer's newest-wins join.
- Follower count rides along on every row → follower-over-time and per-post deltas come free.
- The dashboard Live tab reads the latest snapshot on every rerun: header = followers + last
  scrape time, a **Top 5 by qscore** strip (same fit as ig_analyze, pure-python OLS —
  no numpy on Windows), then per-video views/likes/comments.

## 1b. Deep metrics — outbox/ig_insights.jsonl (Meta Business Suite, since 2026-08-22)
`scripts/ig_insights.py` scrapes the Business Suite content table (linked via "Continue
with Instagram" — no Facebook account; if the session dies it telems `ig_insights_login`
and the link is redone by hand once): per-post **reach, shares (= reposts — Phil's key
metric), saves, follows-from-post, watch time, average play time**, alongside
views/likes/comments. Runs with every ig_stats invocation (post + 12:00 + 00:00). Rows
join to journeys by caption match. Interpretation notes: shares+saves are STRONG intent
signals (rarer than likes); follows-per-view is the conversion the account actually
grows by; avg-play-time on low-view old posts can read implausibly high (a few looping
sessions dominate) — trust it on posts with 300+ views.

## 2. Analyze
```bash
python3 scripts/ig_analyze.py --features
```
Groups by tier/style/scale-span/engine/**posted era**/**parallax gain** (the DEPTH 2.0
random per-video gain draw, from the pipeline entry's engine_params — pre-parallax videos
group as "off"; Phil picks the winner from this as posts accumulate)/cut/music-mood, and
`--features`
measures each posted video's frames (luminance, saturation, contrast, dark-fraction; cached
in outbox/video_features.json) and correlates each with like%. The posted-era buckets
(jul–08-04 / 08-05–08-13 / 08-14+ rethink) track whether the 08-13 rethink package moved the
numbers — era, engine, and music deck co-move by construction, so era contrasts measure the
package, never one variable.

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

## Current standing findings — 2026-08-22 (n=43 reels, 59 followers)
THE RETHINK PACKAGE VALIDATED: posts since 08-14 (new-doctrine journeys + music deck +
resolve engine, n=10) — median views 506 vs ~165 for both earlier eras, pushed >300 60% vs
14–29%, >1000 40% vs 0–12% (the only earlier >1000s were remix re-posts), pooled like
2.59% ±0.33 vs ~1.95%, mean qscore 1.32x — better engagement on much colder pushed traffic,
and the era posts are the youngest (least accumulation time), so the gap is understated.
Followers 34→59 in 9 days (~2× prior growth rate). Era 2 (08-05–08-13, the queue Phil
"wasn't in love with") was the catalog's weakest stretch (1.08x, 0 pushes >1000) — the
queue-reset call was right in hindsight. Standouts: sundew_snare 3.05x (choir_of_dust lane),
squid_lantern 2982 views (biggest organic reach), desert_rosette 1.50x at 1373. reef_pop
0.35x (n=2, both era-2 — confounded, watch before retiring). Tier L 1.36x > S 1.02x > M
0.92x confirms the 08-13 tier finding on more data.

## Prior findings — 2026-08-13 baseline (n=31 reels, 33 followers) — kept for the paper trail
Dark+saturated beats pale high-key and STRENGTHENS under qscore (sat +0.34 / lum −0.33 /
dark-frac +0.29); tier by qscore: L 1.36x > M 0.98x > S 0.92x (longs EARN pushes; shorts'
decent like% never converts to reach); candy_gloss retired (0.22x sugar_nebula = catalog
worst); cut (divein/zoomout) no effect; engine-2 ≈ engine-1 on mean qscore (1.18x vs 1.12x)
but e2 owns both tails — the palette variables dominate the engine variable; cave_of_numbers
reads ~1.0x once comments + earned reach count. TWO-AXIS LAW (2026-08-13, Phil's discarded-
measure catch): LIKES reward dark/saturated/nameable; REACH (pushes >300 views) rewards SCALE
SPAN — full-scale 44% pushed vs 10% narrow, cosmic 33% vs 7% — so full-scale is reinstated
for L-tier composition even though its like% shows no effect. REMIX natural experiment: the
two reach outliers are refined re-posts of earlier journeys whose originals got ~180 views
(same content, 10x reach on the second roll) — re-posting proven winners re-rolls the reach
dice; a deliberate remix-slot test is the standing proposal. Re-test all of these as
snapshots accumulate — they are baselines, not laws.
