#!/usr/bin/env python3
"""Align a MODEL-GENERATED track to a video's morphs — NO hand-written overlay.

Phil's direction (2026-07-28): don't synthesize a lead; let the music model write the
music and WE make it land. The track is generated tempo-locked (a morph interval = one
bar); this finds the (tempo, phase) that best sits the track's OWN accents on the morphs —
strong beat on the morph (the downbeat), the pickup/anacrusis landing just before it from
the previous bar — then applies a tiny stretch + window so it locks across all 11.

Morph grid comes from score.schedule_morphs (exact, from the render schedule). Alignment
uses the track's onset-strength envelope vs the morph grid — so it works with whatever the
model generates, no semantic beat-tracking.

Usage:
  python3 scripts/align.py production/night_bloom_ds_divein.mp4 output/music/track.flac \
          --out review/music/aligned.mp4
"""
import argparse
import sys
import shutil
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import (win, video_duration, schedule_morphs, parse_journey_cut,  # noqa: E402
                   FFMPEG, SR, TMP, _run)


def load_mono(path):
    w = wave.open(str(path), 'rb'); n = w.getnframes(); ch = w.getnchannels()
    raw = w.readframes(n); w.close()
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return a.reshape(-1, ch).mean(axis=1) if ch > 1 else a


def onset_env(x, hop=512, nfft=1024):
    """Spectral-flux onset envelope (rising spectral energy = a note/beat attack)."""
    n = 1 + (len(x) - nfft) // hop
    wdw = np.hanning(nfft).astype(np.float32)
    frames = np.stack([x[i * hop:i * hop + nfft] * wdw for i in range(n)])
    mag = np.abs(np.fft.rfft(frames, axis=1))
    flux = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
    env = np.concatenate([[0.0], flux])
    return env / (env.max() + 1e-9), SR / hop


def best_align(env, esr, morphs, stretches):
    """Search (stretch f, window-start w0) maximizing the track's onset energy summed at
    the morph times. Returns (w0, f, lock) where lock = peak/mean (how sharply it locks)."""
    bar = float(np.median(np.diff(morphs)))
    m = np.asarray(morphs)
    scores = []
    best = None
    for f in stretches:
        for w0 in np.arange(0.0, bar, 0.01):
            idx = ((m + w0) * f * esr).astype(int)
            idx = idx[(idx >= 0) & (idx < len(env))]
            sc = float(env[idx].sum())
            scores.append(sc)
            if best is None or sc > best[0]:
                best = (sc, w0, f)
    mean = (sum(scores) / len(scores)) or 1e-9
    return best[1], best[2], best[0] / mean, bar


def align(video, track, out, journey=None, cut=None, shift_sec=None,
          stretches=(0.985, 0.99, 0.995, 1.0, 1.005, 1.01, 1.015)):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    dur = video_duration(video)
    if journey is None or cut is None:
        journey, cut = parse_journey_cut(video)
    morphs = schedule_morphs(journey, cut, dur, shift_sec=shift_sec)

    # 1) STRIP the generator's leading/trailing silence — ACE-Step ends the piece early (~28s) and
    # pads the rest with silence, so the raw track is mostly-music + a silent tail. We want only the
    # music, then we build our OWN full-length loop from it.
    m = TMP / "_m.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(track),
          "-af", ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05:"
                  "stop_periods=-1:stop_threshold=-45dB:stop_silence=0.30:detection=peak,"
                  "aformat=sample_rates=%d" % SR),
          "-ac", "1", win(m)])

    # 2) tempo (micro-stretch) + phase from the track's own onsets vs the morph grid
    env, esr = onset_env(load_mono(m))
    w0, f, lock, bar = best_align(env, esr, morphs, stretches)
    ms = TMP / "_ms.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(m), "-filter:a",
          f"atempo={f:.5f}", win(ms)])

    XF = min(0.5, 0.3 * bar)          # wrap/tile crossfade (on-beat, keeps the pulse through joins)

    # 3) build a CONTINUOUS music bed at least dur+XF long. If the music is shorter than the video
    # (cosmic: ~28s music vs 31.3s video) we tile it, crossfading each join so the pulse carries.
    R = TMP / "_R.wav"; shutil.copy(ms, R)
    guard = 0
    while video_duration(R) < dur + XF + 0.05 and guard < 30:
        nxt = TMP / "_R2.wav"
        _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(R), "-i", win(ms),
              "-filter_complex", f"[0][1]acrossfade=d={XF:.3f}:c1=tri:c2=tri", win(nxt)])
        nxt.replace(R); guard += 1

    # 4) make a SEAMLESS loop of exactly `dur`: crossfade the body's tail into its own head, so the
    # end meets the start (the video's loop point) without a cut or a fade-to-silence.
    loop = TMP / "_loop.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(R), "-filter_complex",
          f"[0:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[body];"
          f"[0:a]atrim=0:{XF:.3f},asetpts=PTS-STARTPTS[head];"
          f"[body][head]acrossfade=d={XF:.3f}:c1=tri:c2=tri[a]", "-map", "[a]", win(loop)])

    # 5) phase-rotate the loop so its accents sit on the morphs (circular — a seamless loop can be
    # rotated and stays seamless AND full-length; no trimming, so no silence and nothing is lost).
    rot = TMP / "_rot.wav"
    if 0.02 < w0 < dur - 0.02:
        _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(loop), "-filter_complex",
              f"[0:a]atrim=start={w0:.3f},asetpts=PTS-STARTPTS[a1];"
              f"[0:a]atrim=end={w0:.3f},asetpts=PTS-STARTPTS[a2];"
              f"[a1][a2]concat=n=2:v=0:a=1[a]", "-map", "[a]", win(rot)])
    else:
        shutil.copy(loop, rot)

    # 6) loudnorm + mux over the video (audio is exactly dur; keep ALL video frames, no -shortest)
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(video), "-i", win(rot),
          "-filter_complex", f"[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,"
          f"atrim=end={dur:.3f},asetpts=PTS-STARTPTS[a]",
          "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", win(out)])
    for t in (m, ms, R, loop, rot):
        t.unlink(missing_ok=True)
    print(f"  aligned -> {out}\n    bar {bar:.3f}s | stretch {f:.4f} | phase {w0:.3f}s | "
          f"lock {lock:.2f}x | seamless loop @ {dur:.2f}s (music tiled x{guard+1}, xf {XF:.2f}s)")
    return {"w0": w0, "stretch": f, "lock": lock}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("track")
    ap.add_argument("--out", required=True)
    ap.add_argument("--journey"); ap.add_argument("--cut")
    a = ap.parse_args()
    align(a.video, a.track, a.out, journey=a.journey, cut=a.cut)


if __name__ == "__main__":
    main()
