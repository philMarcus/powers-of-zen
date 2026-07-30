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

# the anacrusis + anti-sparse instruction, in musical language (the model obeys this).
# Phil (2026-07-28) prefers STRONG beats — they read as a clearer match to the video — so
# the downbeat is emphatic (still no drums; a firm bass/mallet note, not a soft swell).
ANACRUSIS = ("a quiet pickup note leads in and then a strong clear note lands firmly on the "
             "downbeat of every bar, a steady prominent recurring pulse, never sparse, ")
# distinct moods so the 5 candidates are genuinely different tracks
MOODS = [
    ("warm", "warm analog pads with a soft round mallet on the beat"),
    ("glassy", "crystalline glassy bell tones and airy shimmer pads"),
    ("deep", "deep warm sub bass and dark oceanic pads"),
    ("tender", "tender nostalgic marimba and soft dreamy pads"),
    ("choir", "soft choir-like pad and gentle glass harmonica"),
]
BASE = ("chill hypnotic ambient evoking {theme}, {mood}, {anac}spacious moody reverb, slow, "
        "oddly satisfying, no drums, no snare, no hihat, instrumental")
SEED0 = {"warm": 500, "glassy": 501, "deep": 502, "tender": 503, "choir": 504}


def bpm_for(journey, cut, shift_sec=None):
    dur = video_duration(str(ROOT / _video(journey)))
    morphs = schedule_morphs(journey, cut, dur, shift_sec=shift_sec)
    bar = float(np.median(np.diff(morphs)))
    return int(round(240.0 / bar)), bar


def _video(journey):
    d = pl.load(); v = pl.get(d, journey)
    # align against the silent master if present (never the already-music'd posting file)
    silent = Path(v["file"]).with_name(Path(v["file"]).stem + "_silent.mp4")
    return str(silent) if (ROOT / silent).exists() else v["file"]


def generate(journey, n=5):
    d = pl.load(); v = pl.get(d, journey)
    if not v:
        print(f"no pipeline entry for {journey}"); return
    cut = v["cut"]; key = KEYS.get(journey, "D minor")
    spec = json.loads((ROOT / "journeys" / f"{journey}.json").read_text())
    # theme source of truth = the journey file's music_theme (editable in the dashboard);
    # fall back to the built-in map, then a generic cosmic default.
    theme = spec.get("music_theme") or THEMES.get(journey) or DEFAULT_THEME
    key = spec.get("music_key") or key
    shift_sec = v.get("start_t")          # dashboard-marked start frame (phase-shift, seconds)
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
    print(f"{journey} ({cut}): bar {bar:.3f}s -> {bpm} bpm, key {key}; generating {n}")
    cands = []
    for mood, desc in MOODS[:n]:
        seed = SEED0[mood]
        tags = BASE.format(theme=theme, mood=desc, anac=ANACRUSIS)
        track = ROOT / "output" / "music" / f"{journey}_{mood}.flac"
        music.generate(journey=journey, tags=tags, bpm=bpm, key=key, duration=track_dur,
                       seed=seed, out=str(track))
        aligned = outdir / f"{mood}.mp4"
        info = al.align(video, str(track), str(aligned), journey=journey, cut=cut, shift_sec=shift_sec)
        cands.append({"id": mood, "mood": desc, "track": str(track.relative_to(ROOT)),
                      "aligned": str(aligned.relative_to(ROOT)), "seed": seed,
                      "lock": round(info["lock"], 2), "tags": tags})
        print(f"  [{mood}] lock {info['lock']:.2f}x -> {aligned.relative_to(ROOT)}")
    v["music"] = {"bpm": bpm, "bar": round(bar, 3), "key": key, "stage": "review",
                  "chosen": None, "candidates": cands,
                  "for_model": v["model"], "for_cut": cut}  # so a model/cut switch flags stale music
    pl.save(d)
    pl.telem("music_gen", journey=journey, detail=f"{len(cands)} candidates")
    print(f"recorded {len(cands)} candidates; audition in the dashboard Music panel")


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
    a = ap.parse_args()
    if a.choose:
        choose(a.journey, a.choose)
    else:
        generate(a.journey, n=a.n)


if __name__ == "__main__":
    main()
