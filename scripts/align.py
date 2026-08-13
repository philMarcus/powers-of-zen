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


def onset_env(x, hop=512, nfft=1024, lo=None, hi=None):
    """Spectral-flux onset envelope (rising spectral energy = a note/beat attack).
    lo/hi select an FFT bin range — lo=1, hi=6 (~47-280Hz) isolates DEEP percussion:
    a soft kick carries far less broadband flux than a bright bell, so full-band flux
    mis-ranks the accents the listener feels as the beat."""
    n = 1 + (len(x) - nfft) // hop
    if n < 2:                      # near-silent take: edge-strip ate everything
        return np.zeros(2, np.float32), SR / hop
    wdw = np.hanning(nfft).astype(np.float32)
    frames = np.stack([x[i * hop:i * hop + nfft] * wdw for i in range(n)])
    mag = np.abs(np.fft.rfft(frames, axis=1))
    if lo is not None or hi is not None:
        mag = mag[:, (lo or 0):hi]
    flux = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
    env = np.concatenate([[0.0], flux])
    return env / (env.max() + 1e-9), SR / hop


def measure_bar(env, esr, bar):
    """The track's OWN bar length, from the onset envelope's autocorrelation near the video
    bar. The music was generated tempo-locked to ~bar, so the true period is within a few %;
    measuring it beats searching a stretch grid — a 2-D (stretch, phase) search overfits a
    sparse envelope (it can catch a handful of loud onsets on a wrong tempo and beat the
    honest fit), and a wrong stretch accumulates ~0.1s of drift by the far end of the video.
    Returns (m_bar, confidence 0..1); confidence low -> caller falls back to f=1."""
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    ac /= (ac[0] + 1e-9)
    lo, hi = int(bar * 0.90 * esr), int(bar * 1.10 * esr) + 1
    if hi >= len(ac):
        return bar, 0.0
    k = lo + int(np.argmax(ac[lo:hi]))
    return k / esr, float(ac[k])


def best_phase(env, esr, morphs, f, period_m=None):
    """Search the phase w0 only (stretch is derived, not fitted): maximize onset energy at
    the morph times mapped into the track (mod the tile period, so morphs beyond one tile
    still count — they play tiled content at the same grid phase)."""
    bar = float(np.median(np.diff(morphs)))
    m = np.asarray(morphs)
    scores, best = [], None
    for w0 in np.arange(0.0, bar, 0.01):
        t = (m + w0) * f
        if period_m:
            t = np.mod(t, period_m)
        idx = (t * esr).astype(int)
        idx = idx[(idx >= 0) & (idx < len(env))]
        sc = float(env[idx].sum())
        scores.append(sc)
        if best is None or sc > best[0]:
            best = (sc, w0)
    mean = (sum(scores) / len(scores)) or 1e-9
    return best[1], best[0] / mean, bar


def align(video, track, out, journey=None, cut=None, shift_sec=None):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    dur = video_duration(video)
    if journey is None or cut is None:
        journey, cut = parse_journey_cut(video)
    morphs = schedule_morphs(journey, cut, dur, shift_sec=shift_sec)
    bar = float(np.median(np.diff(morphs)))

    # 1) STRIP the generator's leading/trailing silence — EDGES ONLY. ACE-Step ends the piece
    # early and pads the rest with silence; we drop that. stop_periods=-1 (the old form) also
    # excised INTERIOR silences >=0.3s, chopping seconds out of quiet tracks (tide_glass's
    # choir lost 3.26s) — after which no single (stretch, phase) can lock the broken grid.
    m = TMP / "_m.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(track),
          "-af", ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05:"
                  "detection=peak,areverse,"
                  "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05:"
                  "detection=peak,areverse,"
                  "aformat=sample_rates=%d" % SR),
          "-ac", "1", win(m)])

    # 2) tempo: MEASURE the track's own bar and derive the exact stretch that maps it onto the
    # video bar (f = m_bar / bar; atempo=f makes the stretched bar == video bar). Phase is then
    # the only searched dimension.
    xm = load_mono(m)
    if len(xm) < SR * 1.5:
        raise RuntimeError(f"track unusable: {len(xm)/SR:.2f}s of audio after silence strip")
    env, esr = onset_env(xm)
    env_low, _ = onset_env(xm, lo=1, hi=6)     # deep-percussion band (~47-280Hz)
    m_bar, conf = measure_bar(env, esr, bar)
    f = (m_bar / bar) if conf >= 0.10 else 1.0
    f = min(max(f, 0.97), 1.03)
    # PHASE is kick-weighted (2026-08-13): full-band flux locked bright bells to the morph
    # and parked the felt beat half a bar off (salt_mirror). The deep band leads; full band
    # breaks ties for tracks with no low percussion at all.
    env_phase = 0.65 * env_low + 0.35 * env
    # deep-pulse PRESENCE: does the low band recur at the track's own bar? (music_gen ranks
    # candidates by this so kickless takes can't reach the audition top-5)
    e = env_low - env_low.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    ac = ac / (ac[0] + 1e-9)
    kick_lag = int(round(m_bar * esr))
    kick = float(ac[kick_lag]) if 0 < kick_lag < len(ac) else 0.0
    ms = TMP / "_ms.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(m), "-filter:a",
          f"atempo={f:.5f}", win(ms)])

    XF = min(0.5, 0.3 * bar)          # wrap/tile crossfade (keeps the pulse through joins)

    # 3) build a CONTINUOUS music bed at least dur+XF long. If the music is shorter than the video
    # (cosmic: ~28s music vs 31.3s video) we tile it, crossfading each join so the pulse carries.
    # Each tile is trimmed to an INTEGER number of bars (+XF join overlap): with acrossfade the
    # next tile's time-origin sits at prevLen-XF, so a tile period of exactly k*bar keeps every
    # tile at the SAME beat-grid phase. An arbitrary-length tile shifted the grid at every join —
    # everything past the first tile played off-beat, and the lock score (computed on one tile's
    # envelope) never saw it.
    need_tiles = video_duration(ms) < dur + XF + 0.05
    k = int((video_duration(ms) - XF) // bar) if need_tiles else 0
    # phase search AFTER the tiling geometry is known: morphs past one tile fold onto the tile
    # period (same content, same grid phase), so every morph in the video scores.
    w0, lock, _ = best_phase(env_phase, esr, morphs, f,
                             period_m=(k * bar * f) if (need_tiles and k >= 1) else None)
    if need_tiles and k >= 1:
        msb = TMP / "_msb.wav"
        _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(ms), "-af",
              f"atrim=0:{k * bar + XF:.3f}", win(msb)])
        msb.replace(ms)
    R = TMP / "_R.wav"; shutil.copy(ms, R)
    guard = 0
    while video_duration(R) < dur + XF + 0.05 and guard < 30:
        nxt = TMP / "_R2.wav"
        _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(R), "-i", win(ms),
              "-filter_complex", f"[0][1]acrossfade=d={XF:.3f}:c1=tri:c2=tri", win(nxt)])
        nxt.replace(R); guard += 1

    # 4) make a SEAMLESS loop of exactly `dur`. Body = R[XF : XF+dur]; its tail crossfades into
    # R[0:XF] — the material that LEADS INTO the body's start — so the last sample flows straight
    # into the first (end ~ R[XF-e] -> start = R[XF]): the wrap is sample-continuous. Since dur is
    # an integer number of bars, the crossfade pairs R[dur+t] with R[t] — one whole loop apart,
    # IDENTICAL grid phase. (The old body=R[0:dur] form ended on R[XF] while starting at R[0]:
    # every loop replayed the head — a half-second stutter that rotation then parked ~w0 before
    # the video's end. Verified on a position-coded synthetic before fixing.)
    loop = TMP / "_loop.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(R), "-filter_complex",
          f"[0:a]atrim={XF:.3f}:{dur + XF:.3f},asetpts=PTS-STARTPTS[body];"
          f"[0:a]atrim=0:{XF:.3f},asetpts=PTS-STARTPTS[head];"
          f"[body][head]acrossfade=d={XF:.3f}:c1=tri:c2=tri[a]", "-map", "[a]", win(loop)])

    # 5) phase-rotate the loop so its accents sit on the morphs (circular — a seamless loop can be
    # rotated and stays seamless AND full-length). The loop's content starts at R[XF], i.e. it is
    # already XF ahead of the envelope best_align searched, so rotate by w0-XF (mod dur) to land
    # the same phase w0 promised.
    w0_eff = (w0 - XF) % dur
    rot = TMP / "_rot.wav"
    if 0.02 < w0_eff < dur - 0.02:
        _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(loop), "-filter_complex",
              f"[0:a]atrim=start={w0_eff:.3f},asetpts=PTS-STARTPTS[a1];"
              f"[0:a]atrim=end={w0_eff:.3f},asetpts=PTS-STARTPTS[a2];"
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
    print(f"  aligned -> {out}\n    bar {bar:.3f}s | music bar {m_bar:.3f}s (conf {conf:.2f}) -> "
          f"stretch {f:.4f} | phase {w0:.3f}s | lock {lock:.2f}x | kick {kick:.2f} | "
          f"seamless loop @ {dur:.2f}s (music tiled x{guard+1}, xf {XF:.2f}s)")
    return {"w0": w0, "stretch": f, "lock": lock, "m_bar": m_bar, "bar_conf": conf,
            "kick": round(kick, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("track")
    ap.add_argument("--out", required=True)
    ap.add_argument("--journey"); ap.add_argument("--cut")
    a = ap.parse_args()
    align(a.video, a.track, a.out, journey=a.journey, cut=a.cut)


if __name__ == "__main__":
    main()
