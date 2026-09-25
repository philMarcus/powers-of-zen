# Powers of Zen — audience data science plan (2026-09-25)

Goal (Phil): find the variables that most move engagement, prove one of them with a clean A/B that
lifts likes, and make the whole thing a portfolio piece (data science + AI engineering). Be honest
about what ~80 posts can and cannot tell us.

## 1. The data (built today — `python3 scripts/dataset.py` → outbox/dataset.csv)
One row per posted video (84 today, 76 columns). Sources joined:
- **what was posted**: outbox/pipeline.json — posting time, cut, cameo, caption length/hashtags/spot hook,
  engine settings (parallax gain, planet plate + entrance) for the 38 newest.
- **what the journey is**: journeys/*.json — cards, tier, scale span (exp max/min), cosmic/subatomic/
  full-scale, planet card, seams, tempo (fpb → bpm), style deck, cameo card scale, water/creature words.
- **what the frames look like**: outbox/video_features.json — luminance, saturation, contrast, dark fraction.
- **what the music is** (NEW, scripts/music_features.py → outbox/music_features.json): the deck's lane,
  rhythm feel (downbeat / heartbeat / third_answer / halftime), instrument FAMILY (bells_glass ·
  mallets_plucked · pads_drone · strings — coarse enough to have support at n≈80), instrument words,
  key/mode, bpm, the ranking metrics (kick / lock / fit), and MEASURED audio from the chosen take:
  spectral brightness, 85% roll-off, low-end share (<150 Hz), high share (>4 kHz), loudness, dynamics,
  onsets per second, dominant pulse period + strength, spectral flatness. Every naming era parsed
  (deck takes, wildcards, pulse top-ups, pre-deck 'tender'/'warm' takes).
- **outcomes**: IG views/likes/comments — latest AND at fixed exposure ages (first snapshot ≥48 h and
  ≥7 d after posting; 12:00/00:00 snapshots exist since 08-22, so 48 h values cover 48 of 84);
  followers at post time (the audience size the video was shown to); Business Suite reach / shares /
  saves / follows / watch time (66 videos); YouTube views (79).
Gaps: TikTok is paused (no data); pre-08-22 videos have only after-post snapshots; 8 posts carry the
new planet plate (all in the last 8 days).

## 2. What the data says today (scratchpad/eda.py — exploratory, NOT causal)
- **The level-up is real but half of it is the audience.** Median likes at 7 d: 4 (Jul) → 6.5 → 7 →
  30 (last two weeks); median views 162 → 1068; followers 33 → 127. Likes scale with
  followers_at_post^0.72 (p=0.004). Everything below is measured on the follower-ADJUSTED residual
  (what a video did beyond what the audience size predicts; +0.69 = 2×).
- **Signals with support**: scale span (ρ=+0.29, p=0.013), card count / length (ρ≈+0.28, p≈0.02),
  full-scale journeys ×1.39 vs ×0.76, long tier ×1.32 vs short ×0.74 / medium ×0.66, journeys with a
  planet card ×1.42 vs ×0.80 (CI ±0.38 — and planet cards live in long full-scale journeys, so these
  three are one signal until modelled together), creature scenes ×1.20 vs ×0.81, posting hour
  (ρ=+0.23, p=0.057, later = better).
- **Music, honestly**: bells_glass ×1.52 (n=18, CI ±0.49 → not significant), pads_drone ×0.90,
  mallets ×0.90, strings ×0.83 (n=7); rhythm feels all within ±0.15 of each other with CIs of ±0.5-0.8;
  major key ×0.54 but n=5; none of the measured audio features correlates beyond |ρ|=0.18. At n=69
  the music question is OPEN — which is exactly why it needs the experiment in §4, not more slicing.
- **Predictability**: ridge regression on 30 standardized features, 5-fold CV R² = 0.03 vs 0.00 for
  followers alone. A decision tree / random forest on this n would memorize noise; we will report
  importances only with bootstrap CIs, and never as "the" answer.
- The last 12 posts: 11 of 12 over 10 likes (Phil's count checks out); best 48 h: natron_skein 49,
  cicada_chorus 50 (plate), mantis_drumline 42, haboob_oasis 41 at 28 h (on track to top them).

## 3. Observational analysis (the portfolio's "what we learned" chapter)
Primary outcome: log likes at 7 d (fallback: latest for videos older than 7 d), adjusted for
followers at post; secondary: like-rate (lower dispersion, sd 0.55 vs 0.92), shares+saves, follows,
YouTube views (a separate lottery — corr +0.04 with IG).
1. **Regularized multivariable model** (ridge / lasso, one-hot for style·lane·family·rhythm·cameo,
   followers + posting-era as covariates) with **bootstrap** coefficient intervals — separates
   planet/full-scale/length from each other and from the era they arrived in.
2. **Gradient boosting + permutation importance, repeated CV** — a nonlinear cross-check; report the
   importance distribution across bootstrap resamples, partial-dependence for the top 5.
3. **Hierarchical Bayesian shrinkage** for the many-level categoricals (12 styles, 10 lanes, 13 cameos,
   n≈5 each): partial pooling gives honest per-level estimates instead of n=5 outliers.
4. **Time-series view**: engagement vs posting date with follower growth; rolling 10-post median;
   change-point at the 08-13 rethink and the 09-18 planet plate.
5. **Survival/decay of a post**: likes(t) curves from the snapshot series — when is a post "done"?
   (Defines the right outcome age; today's 7 d is a guess.)
Deliverable: `analysis/report.py` regenerates figures + a Markdown report from dataset.csv, so the
report is always reproducible from raw logs (portfolio requirement).

## 4. The experiment (the "we proved it" chapter)
Power, from our own dispersion (α=0.05, power 0.8, one post per 19 h):
| outcome | detect ×1.3 | ×1.5 | ×2.0 |
|---|---|---|---|
| likes at 7 d (sd 0.92) | 196/arm · 10 months | 83/arm · 4.4 months | 29/arm · 6.5 weeks |
| like-rate (sd 0.55) | 71/arm · 3.8 months | 31/arm · 7 weeks | 12/arm · 2.5 weeks |
So: test ONE variable at a time, use like-rate (or qscore) as the primary outcome, randomize at
posting time, pre-register the rule, and analyze sequentially with a stopping boundary.
Candidate #1 — **music instrument family** (Phil's question; assignable WITHOUT changing the video;
pregen already gives 2.5 families per set and 64 of 121 sets contain both bells_glass and pads_drone):
at approve time a coin flip picks the arm and the dashboard proposes the best take of that family;
Phil may override (recorded → intent-to-treat + per-protocol). Two design decisions for Phil:
(a) arms: bells_glass vs pads_drone (the two ends of the observational spread), and (b) pregen
guarantees at least one strong take of each arm's family (a small change to candidate_plan).
Candidate #2 — **posting hour** (free to randomize; the data hints later = better).
Candidate #3 — **planet card present** (randomize queue order over planet/no-planet journeys;
the biggest observational effect, but confounded with length — the A/B settles it).
Run #1 now, #2 in parallel (orthogonal, doubles the value of every post), #3 after.

## 5. Dashboard ("📈 Insights" tab, Windows python: pandas + sklearn + altair are installed)
- Trend: likes / views / like-rate per post over time with follower growth; era markers.
- Forest plot: follower-adjusted effect per group (planet, tier, music family, rhythm, style, cameo,
  weekday) with 95% CIs — the honest version of "what matters".
- Importance: bootstrap distribution of permutation importances (box plot), top 12.
- Music panel: family × rhythm grid of like-rate; audio-feature scatter (brightness, low-end) vs like-rate.
- Experiment panel: active test, arms, n per arm, running lift + CI, posts-to-decision, stop rule state.
- Rebuild: dataset.py runs after every stats snapshot (12:00 / 00:00 / post) so the tab is live.

## 6. Portfolio framing (both careers)
Data science: a documented pipeline from raw scrapes → tidy dataset → adjusted analysis → powered,
pre-registered experiment → decision; every number regenerable. AI engineering: the same repo is the
production system that generated the content (agents, engine, scheduler, posting harness) — the
analysis closes the loop back into the generator (what we learn changes what the composer writes).

## Status
DONE today: music instrumentation + audio features; dataset builder; first EDA; power analysis;
review-queue backpressure (max_review_videos = 20). NEXT (in order): analysis/report.py (§3 1-2 +
figures) → Insights tab → A/B #1 assignment in the approve flow + pregen family guarantee → run.
