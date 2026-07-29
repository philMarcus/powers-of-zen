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

    twav = TMP / "_align_track.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(track), "-ar", str(SR),
          "-ac", "1", win(twav)])
    env, esr = onset_env(load_mono(twav))
    w0, f, lock, bar = best_align(env, esr, morphs, stretches)
    twav.unlink(missing_ok=True)

    fo = max(0.0, dur - 0.5)
    af = (f"atempo={f:.5f},atrim=start={w0:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS,"
          f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.12,afade=t=out:st={fo:.3f}:d=0.5")
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(video), "-i", win(track),
          "-filter_complex", f"[1:a]{af}[a]", "-map", "0:v:0", "-map", "[a]",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", win(out)])
    print(f"  aligned -> {out}\n    bar {bar:.3f}s | stretch {f:.4f} | window {w0:.3f}s | "
          f"lock {lock:.2f}x (higher = the track's accents sit on the morphs more sharply)")
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
