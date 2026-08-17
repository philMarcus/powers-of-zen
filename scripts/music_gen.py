#!/usr/bin/env python3
"""Music-review stage: turn an approved video into 4-5 aligned candidate tracks to audition.

The METHOD (proven 2026-07-28): the MODEL writes the music; we only pick the tempo and
slide it into phase. For a journey whose cut is locked, we:
  1. derive tempo from the morph grid (one bar = one morph interval),
  2. generate N tracks, each tempo-locked and prompted IN MUSICAL LANGUAGE for the
     anacrusis (quiet pickup -> strong downbeat on EVERY bar, a steady recurring pulse —
     never sparse, that was the failure mode), chill, no drums,
  3. auto-align each (scripts/align.py) so its own accents sit on the morphs,
  4. record them as candidates in pipeline.json for the dashboard Music panel.

Phil auditions, tweaks, approves one -> choose() promotes it into the posting slot.

Usage:
  python3 scripts/music_gen.py night_bloom            # generate candidates
  python3 scripts/music_gen.py night_bloom --n 5
  python3 scripts/music_gen.py night_bloom --choose warm   # promote a candidate
"""
import argparse
import json
import math
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402
import align as al  # noqa: E402
from score import schedule_morphs, win, FFMPEG, video_duration  # noqa: E402
import engine.music as music  # noqa: E402

# per-journey musical key (lead/melody sits in this) — default D minor (night_bloom lane)
KEYS = {"night_bloom": "D minor"}

# per-journey SCENE theme — so the model scores the actual world (underwater / cosmic /
# library / winter …), not a generic pad. This is the dominant vibe of the whole dive.
THEMES = {
    "night_bloom": "a glowing bioluminescent night garden, nocturnal, dreamy, alive with soft light",
    "alexandria": "an ancient library of scrolls, ink and knowledge, scholarly, timeless, mysterious",
    "food_chain": "a teeming underwater pond ecosystem, aquatic, murky green, alive with tiny creatures",
    "iris_observatory": "a cosmic observatory peering through a great eye, celestial, vast, contemplative",
    "cartographer": "old star charts and voyages, exploratory, starlit, adventurous, wondrous",
    "dollhouse": "a miniature dollhouse world, music-box, cozy and domestic, tiny and tender",
    "snowfall": "quiet snowfall over a sleeping village, frozen crystalline stillness, hushed and wintry",
}
DEFAULT_THEME = "a hypnotic journey across every scale of the universe, cosmic and wondrous"

# MUSIC DECK (2026-08-13, Phil-approved design): curated instrumentation LANES + rhythm
# feels + a fixed brand tail live in styles/music_deck.json — the sound analog of the visual
# style deck. A journey names its lane (`music_lane`, composer-assigned); journeys without
# one get a stable hash pick so the whole catalog spreads across the deck. Candidates:
# N_GEN variants (own lane, rhythm alternates, wildcard lanes, seed jitter — occasionally a
# 3/4 waltz reframing, sparingly per Phil) auto-ranked down to N_KEEP by lock x bar-clarity.
DECK = json.loads((ROOT / "styles" / "music_deck.json").read_text(encoding="utf-8"))
N_GEN, N_KEEP = 8, 5
# rhythm FIRST (tag order carries weight) and percussion by POSITIVE EXCLUSIVITY — the old
# "no snare, no hi-hat" tail summoned the very instruments it named (2026-08-13, Phil heard
# snares/woodblocks across the tempo-test candidates), and ACE's negative conditioning is a
# ConditioningZeroOut at cfg 1.0 so prose bans carried zero guidance.
TAGS = ("{rhythm}, chill hypnotic ambient evoking {theme}, {instr}, spacious moody reverb, "
        "oddly satisfying, cinematic, instrumental, no vocals")


def _lane_names():
    return sorted(DECK["lanes"])


def lane_for(journey, spec):
    lane = spec.get("music_lane")
    if lane in DECK["lanes"]:
        return lane
    names = _lane_names()
    return names[zlib.crc32(journey.encode()) % len(names)]


def build_tags(theme, lane_name, rhythm_key=None):
    lane = DECK["lanes"][lane_name]
    rhythm = DECK["rhythms"][rhythm_key or lane["rhythm"]]
    return TAGS.format(theme=theme, instr=lane["instr"], rhythm=rhythm)


def candidate_plan(journey, spec, bar):
    """(id, lane, rhythm_key, bpm_override, seed) x N_GEN. Deterministic per journey (its
    own seeds — the old fixed 500..504 made every journey's 'warm' the same take)."""
    h = zlib.crc32(journey.encode())
    s0 = 500 + h % 40000
    own = lane_for(journey, spec)
    names = [n for n in _lane_names() if n != own]
    wild = [names[(h // 7 + i * 3) % len(names)] for i in range(3)]
    own_r = DECK["lanes"][own]["rhythm"]
    alt_r = {"downbeat": "third_answer", "third_answer": "downbeat",
             "halftime": "heartbeat", "heartbeat": "halftime"}[own_r]
    plan = [
        (own, own, None, None),
        (f"{own}-b", own, None, None),                      # seed jitter, same recipe
        (f"{own}-{alt_r}", own, alt_r, None),
        (f"{wild[0]}-wild", wild[0], None, None),
        (f"{wild[1]}-wild", wild[1], None, None),
        (f"{own}-halftime", own, "halftime", None),
        (f"{wild[2]}-wild", wild[2], None, None),
    ]
    if h % 4 == 0:      # the occasional 3/4 spice (sparingly — Phil 2026-08-13)
        plan.append((f"waltz-{own}", own, "downbeat", int(round(3 * 60.0 / bar))))
    else:               # filler: a rhythm the plan doesn't already cover for this lane
        fill = next(r for r in ("heartbeat", "third_answer", "downbeat")
                    if r not in (own_r, alt_r, "halftime"))
        plan.append((f"{own}-{fill}", own, fill, None))
    return [(cid, ln, rk, bpm, s0 + 37 * i) for i, (cid, ln, rk, bpm) in enumerate(plan)]


def bpm_for(journey, cut, shift_sec=None):
    import json as _json
    spec = _json.loads(pl.journey_path(journey).read_text(encoding="utf-8"))
    fmt = spec.get("format", {})
    if any(r.get("dur") is not None for r in spec["registers"]):
        # dur-in-BEATS schema: the bar is DEFINED by the format grid (beats_per_bar ×
        # frames_per_beat at the 12fps raw rate). Median morph spacing is wrong here —
        # sub-bar cards (dur 2 = half a bar, morphs on beats 1 AND 3 by design) drag the
        # median to a phantom 1.75s "bar" that matches nothing musical.
        bar = fmt.get("beats_per_bar", 4) * fmt.get("frames_per_beat", 7) / 12.0
        return int(round(240.0 / bar)), bar
    dur = video_duration(str(ROOT / _video(journey)))
    morphs = schedule_morphs(journey, cut, dur, shift_sec=shift_sec)
    bar = float(np.median(np.diff(morphs)))
    return int(round(240.0 / bar)), bar


def _video(journey):
    d = pl.load(); v = pl.get(d, journey)
    # align against the silent master if present (never the already-music'd posting file)
    silent = Path(v["file"]).with_name(Path(v["file"]).stem + "_silent.mp4")
    return str(silent) if (ROOT / silent).exists() else v["file"]


def generate(journey, n=N_KEEP, shift=True, target="music"):
    """target="music": the normal Phil-facing candidates (aligned to the marked start).
    target="music_pregen": the overnight PRE-GENERATION (Phil 2026-08-17 — no waiting at
    approve time): same tracks, ranked against the UNSHIFTED cut; approve_to_music later
    just re-aligns the keepers to the chosen start (seconds of ffmpeg, no GPU)."""
    d = pl.load(); v = pl.get(d, journey)
    if not v:
        print(f"no pipeline entry for {journey}"); return
    cut = v["cut"]; key = KEYS.get(journey, "D minor")
    spec = json.loads(pl.journey_path(journey).read_text(encoding="utf-8"))
    # theme source of truth = the journey file's music_theme (editable in the dashboard);
    # fall back to the built-in map, then a generic cosmic default.
    theme = spec.get("music_theme") or THEMES.get(journey) or DEFAULT_THEME
    key = spec.get("music_key") or key
    shift_sec = v.get("start_t") if shift else None   # marked start (phase-shift, seconds)
    bpm, bar = bpm_for(journey, cut, shift_sec=shift_sec)
    video = _video(journey)
    # Track length isn't critical anymore: align.py strips the generator's silent tail and builds
    # its OWN seamless full-length loop (tiling if the music is shorter than the video). We just ask
    # for a bit more than the video so there's a full, settled take of music to loop from. (ACE-Step
    # tends to cap its actual music at ~28s regardless — the aligner's tiling covers longer videos.)
    vdur = video_duration(str(ROOT / video) if not Path(video).is_absolute() else video)
    track_dur = int(math.ceil(vdur)) + 3
    outdir = ROOT / "review" / "music" / "candidates" / journey
    outdir.mkdir(parents=True, exist_ok=True)
    plan = candidate_plan(journey, spec, bar)
    print(f"{journey} ({cut}): bar {bar:.3f}s -> {bpm} bpm, key {key}; lane "
          f"{lane_for(journey, spec)}; generating {len(plan)}, keeping {n}")
    cands = []
    for cid, lane_name, rk, bpm_o, seed in plan:
        tags = build_tags(theme, lane_name, rk)
        if cid.startswith("waltz"):
            tags = "a gently lilting waltz in 3/4 time, " + tags
        use_bpm = bpm_o or bpm
        track = ROOT / "output" / "music" / f"{journey}_{cid}.flac"
        try:
            music.generate(journey=journey, tags=tags, bpm=use_bpm, key=key,
                           duration=track_dur, seed=seed, out=str(track))
            aligned = outdir / f"{cid}.mp4"
            info = al.align(video, str(track), str(aligned), journey=journey, cut=cut,
                            shift_sec=shift_sec)
        except Exception as e:
            print(f"  [{cid}] SKIPPED — {e}")
            continue
        # rank = lock x bar-clarity x DEEP-PULSE presence (Phil 2026-08-13: the felt deep
        # beat must be near-ever-present; a kickless take gets crushed by the x0.25 floor
        # and can't reach the audition top-5)
        score = (info["lock"] * (0.5 + max(0.0, info.get("bar_conf", 0.0)))
                 * (0.25 + max(0.0, info.get("kick", 0.0))))
        lane = DECK["lanes"][lane_name]
        cands.append({"id": cid, "lane": lane_name,
                      "mood": f"{lane['mood']} · {rk or lane['rhythm']}"
                              + (f" · {use_bpm}bpm 3/4" if bpm_o else ""),
                      "track": str(track.relative_to(ROOT)),
                      "aligned": str(aligned.relative_to(ROOT)), "seed": seed,
                      "lock": round(info["lock"], 2),
                      "bar_conf": round(info.get("bar_conf", 0.0), 2),
                      "kick": round(info.get("kick", 0.0), 2),
                      "score": round(score, 2), "tags": tags})
        print(f"  [{cid}] lock {info['lock']:.2f}x conf {info.get('bar_conf', 0):.2f} "
              f"kick {info.get('kick', 0):.2f} score {score:.2f} -> {aligned.relative_to(ROOT)}")

    # DEEP-PULSE TOP-UP (2026-08-13): ACE obeys the percussion spec stochastically (~1 in 3
    # takes has no kick regardless of phrasing — measured). If the plan didn't yield enough
    # pulsed candidates, roll extra downbeat takes so the audition set always carries the
    # felt beat Phil asked for.
    extra_seed = max(c["seed"] for c in cands) + 101
    tries = 0
    while sum(1 for c in cands if c.get("kick", 0) >= 0.25) < n and tries < 3:
        cid = f"pulse{tries + 1}-{lane_for(journey, spec)}"
        tags = build_tags(theme, lane_for(journey, spec), "downbeat")
        track = ROOT / "output" / "music" / f"{journey}_{cid}.flac"
        try:
            music.generate(journey=journey, tags=tags, bpm=bpm, key=key, duration=track_dur,
                           seed=extra_seed, out=str(track))
            aligned = outdir / f"{cid}.mp4"
            info = al.align(video, str(track), str(aligned), journey=journey, cut=cut,
                            shift_sec=shift_sec)
        except Exception as e:
            print(f"  [{cid}] SKIPPED — {e}")
            extra_seed += 101
            tries += 1
            continue
        score = (info["lock"] * (0.5 + max(0.0, info.get("bar_conf", 0.0)))
                 * (0.25 + max(0.0, info.get("kick", 0.0))))
        lane = DECK["lanes"][lane_for(journey, spec)]
        cands.append({"id": cid, "lane": lane_for(journey, spec),
                      "mood": f"{lane['mood']} · downbeat (pulse top-up)",
                      "track": str(track.relative_to(ROOT)),
                      "aligned": str(aligned.relative_to(ROOT)), "seed": extra_seed,
                      "lock": round(info["lock"], 2),
                      "bar_conf": round(info.get("bar_conf", 0.0), 2),
                      "kick": round(info.get("kick", 0.0), 2),
                      "score": round(score, 2), "tags": tags})
        print(f"  [{cid}] kick {info.get('kick', 0):.2f} (top-up {tries + 1})")
        extra_seed += 101
        tries += 1

    # keep the top n with SPREAD (max 2 per lane so the audition is never five near-twins)
    keep = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if len(keep) < n and sum(1 for k in keep if k["lane"] == c["lane"]) < 2:
            keep.append(c)
    for c in sorted(cands, key=lambda c: -c["score"]):
        if len(keep) >= n:
            break
        if c not in keep:
            keep.append(c)
    for c in cands:                       # de-clutter the audition dir
        if c not in keep:
            (ROOT / c["aligned"]).unlink(missing_ok=True)
    cands = keep
    print(f"kept: {', '.join(c['id'] for c in cands)}")
    # RE-READ before writing. This function runs for MINUTES (5 generations + aligns) while
    # the dashboard keeps editing pipeline.json; saving the snapshot loaded before the work
    # clobbers every edit made meanwhile (2026-08-01: a video rejected during lather_atlas's
    # music gen silently came back to review). Long-running writers merge their OWN fields
    # into a fresh copy — never save a stale whole-file snapshot.
    model0 = v["model"]                    # what the tracks were BUILT for (staleness check)
    d = pl.load(); v = pl.get(d, journey)
    if not v:
        print(f"{journey} vanished from pipeline.json during generation — not recorded"); return
    v[target] = {"bpm": bpm, "bar": round(bar, 3), "key": key,
                 "stage": "pregen" if target == "music_pregen" else "review",
                 "chosen": None, "candidates": cands,
                 "for_model": model0, "for_cut": cut}  # a model/cut switch flags stale music
    pl.save(d)
    pl.telem("music_gen" if target == "music" else "music_pregen",
             journey=journey, detail=f"{len(cands)} candidates")
    music.free_vram()      # ACE-Step holds ~9 GB after a run; release it for whatever's next
    print(f"recorded {len(cands)} candidates; audition in the dashboard Music panel")


def realign(journey):
    """Fast path at approve time: the overnight pregen already made + ranked the tracks;
    re-align those keepers to the CURRENT file + marked start (ffmpeg only, no GPU) and
    promote them into v["music"] for audition."""
    d = pl.load(); v = pl.get(d, journey)
    pg = (v or {}).get("music_pregen")
    if not v or not pg or not pg.get("candidates"):
        print(f"no pregen for {journey} — falling back to full generation")
        return generate(journey)
    shift_sec = v.get("start_t")
    video = _video(journey)
    outdir = ROOT / "review" / "music" / "candidates" / journey
    outdir.mkdir(parents=True, exist_ok=True)
    cands = []
    for c in pg["candidates"]:
        track = ROOT / c["track"]
        if not track.exists():
            print(f"  [{c['id']}] track missing — skipped"); continue
        aligned = outdir / f"{c['id']}.mp4"
        try:
            info = al.align(video, str(track), str(aligned), journey=journey,
                            cut=v["cut"], shift_sec=shift_sec)
        except Exception as e:
            print(f"  [{c['id']}] realign failed: {e}"); continue
        cc = dict(c)
        cc.update({"aligned": str(aligned.relative_to(ROOT)),
                   "lock": round(info["lock"], 2),
                   "kick": round(info.get("kick", 0.0), 2),
                   "bar_conf": round(info.get("bar_conf", 0.0), 2)})
        cands.append(cc)
        print(f"  [{c['id']}] realigned (lock {info['lock']:.2f}x kick "
              f"{info.get('kick', 0):.2f})")
    d = pl.load(); v = pl.get(d, journey)
    if not v:
        return
    v["music"] = {"bpm": pg["bpm"], "bar": pg["bar"], "key": pg["key"], "stage": "review",
                  "chosen": None, "candidates": cands,
                  "for_model": v["model"], "for_cut": v["cut"]}
    pl.save(d)
    pl.telem("music_realign", journey=journey, detail=f"{len(cands)} candidates")
    print(f"realigned {len(cands)} pregen candidates to the marked start")


def choose(journey, cand_id):
    """Promote a candidate into the posting slot (mux its aligned full-res over the file)."""
    d = pl.load(); v = pl.get(d, journey)
    m = v.get("music", {})
    cand = next((c for c in m.get("candidates", []) if c["id"] == cand_id), None)
    if not cand:
        print(f"no candidate {cand_id} for {journey}"); return
    src = ROOT / cand["aligned"]; dst = ROOT / v["file"]
    silent = dst.with_name(dst.stem + "_silent.mp4")
    if not silent.exists():           # preserve the silent master once
        subprocess.run(["cp", str(dst), str(silent)], check=True)
    subprocess.run(["cp", str(src), str(dst)], check=True)
    m["chosen"] = cand_id; m["stage"] = "done"
    pl.save(d)
    pl.telem("music_choose", journey=journey, detail=cand_id)
    print(f"{journey}: promoted '{cand_id}' (lock {cand['lock']}x) into {v['file']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--choose", help="candidate id to promote into the posting slot")
    ap.add_argument("--pregen", action="store_true",
                    help="overnight pre-generation (unshifted cut, stored in music_pregen)")
    ap.add_argument("--realign", action="store_true",
                    help="fast approve path: re-align pregen keepers to the marked start")
    a = ap.parse_args()
    if a.choose:
        choose(a.journey, a.choose)
    elif a.pregen:
        generate(a.journey, n=a.n, shift=False, target="music_pregen")
    elif a.realign:
        realign(a.journey)
    else:
        generate(a.journey, n=a.n)


if __name__ == "__main__":
    main()
