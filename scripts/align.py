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


# Which beat of the bar we PREFER the morph to land on when two beats score alike.
# Phil's rule (2026-09-10): beat 1 and beat 3 are the strong beats; 2 and 4 are weak.
# The prior only breaks near-ties — a decisively louder beat still wins on its own merits.
BEAT_PRIOR = {0: 1.00, 2: 0.98, 1: 0.93, 3: 0.93}
# how far off the beat grid (in beats) the free maximum may sit before we correct it
OFFGRID_TOL = 0.15


def _fold(vals, grid, period):
    """Sum a curve sampled on `grid` into one `period`-long profile (n bins)."""
    n = max(4, int(round(period / (grid[1] - grid[0]))))
    prof = np.zeros(n)
    for v, g in zip(vals, grid):
        prof[int((g % period) / period * n) % n] += v
    return prof


def _downbeat_phase(env, esr, bar_track, beats):
    """Where the track's OWN bar starts, from its envelope alone — independent of where the
    morphs sit, so it can honestly say WHICH beat a morph lands on."""
    T = len(env) / esr
    grid = np.arange(0.0, bar_track, 0.01)
    scores = []
    for ph in grid:
        idx = ((np.arange(ph, T, bar_track)) * esr).astype(int)
        idx = idx[(idx >= 0) & (idx < len(env))]
        scores.append(float(env[idx].sum()) / max(1, len(idx)))
    return float(grid[int(np.argmax(scores))])


def meter_fit(env, esr, bar, lo_s=0.30, hi_s=7.0, ref=None):
    """Does the track PHRASE in the video's bar, or in some other grouping?

    Phil, 2026-09-10: the picture's morph is reliably periodic — "every video has a good
    periodic visual beat" — so when a track feels like it lands in a different place each
    time, the track is what disagrees. `lock` cannot see this: a dense onset envelope always
    has energy near every morph, so a track can score a high lock while its FELT phrase
    walks around the morph grid. `kick` cannot see it either — it samples the autocorrelation
    at the assumed bar lag and never asks what the dominant grouping actually is.

    Measured cause on saguaro_vigil's choir_of_dust-b (kick 0.42, the take Phil says does not
    mesh): its beat is correct at 0.747s (80bpm, 4 to the bar) but its strongest LONG grouping
    is 2.251s and 4.501s — it phrases in THREES. Morphs come every 4 beats, so the downbeat
    and the morph only coincide every 12 beats and drift in between. Meanwhile the bar lag
    itself is only its 5th strongest period (ac 0.27), which measure_bar's +-10% window
    happily picked as if it were the tempo.

    Returns (fit, bar_ac, clash_ac): fit = bar_ac / clash_ac, where clash_ac is the strongest
    periodicity that neither divides nor multiplies the bar. fit >= 1 means the bar is the
    track's own strongest structure; below 1 a rival grouping is stronger.

    `ref` (2026-09-19 — the sargasso_windrow false alarm): the period to judge the track
    AGAINST. On an UNSTRETCHED track that must be the track's own MEASURED bar, not the
    video's nominal bar. ACE-Step lands within a percent or two of the requested tempo and
    the aligner stretches the difference away, but autocorrelation peaks are only a few
    hundredths of a second wide: sampled at the nominal 2.333s, a perfectly phrased 4/4
    track whose own bar is 2.283s read bar_ac 0.02 (its real peak is 0.75), and its TRUE
    multiples (3 bars = 6.859s) failed the commensurability test against 2.333 and were
    counted as rivals. Every good track was labelled "phrases off the bar" (fit ~0.1), and
    the ranking penalty then pushed strong-beat takes below beatless wildcards. Measured on
    the finished videos, those same tracks sat within 10-40 ms of all 11 morphs."""
    e = env - env.mean()
    a = np.correlate(e, e, mode="full")[len(e) - 1:]
    a = a / (a[0] + 1e-9)
    lo, hi = int(lo_s * esr), min(int(hi_s * esr), len(a) - 1)
    if hi <= lo + 2:
        return 1.0, 0.0, 0.0
    ref = float(ref) if ref else float(bar)
    kb = min(int(round(ref * esr)), len(a) - 1)
    wb = max(1, int(round(0.012 * ref * esr)))          # +-1.2%: sit ON the peak, not beside it
    bar_ac = float(a[max(0, kb - wb):kb + wb + 1].max())
    clash = 0.0
    for k in range(lo + 1, hi - 1):
        if not (a[k] > a[k - 1] and a[k] >= a[k + 1]):
            continue
        per = k / esr
        r1, r2 = ref / per, per / ref          # bar is n beats of it, or it is n bars long
        if min(abs(r1 - round(r1)), abs(r2 - round(r2))) < 0.06:
            continue                            # commensurate — not a rival
        clash = max(clash, float(a[k]))
    fit = bar_ac / clash if clash > 0.02 else (2.0 if bar_ac > 0 else 1.0)
    return fit, bar_ac, clash


def best_phase(env, esr, morphs, f, period_m=None, beats=None, quantize=True):
    """Choose the phase w0 that sits the track's accents on the morphs.

    Two stages (2026-09-10). A FREE 0.01s sweep finds the raw energy maximum, exactly as
    before — but on a sparse or busy envelope that maximum can land BETWEEN beats: audited
    across the catalog, 9 of 61 shipped videos had their morph sitting off the beat grid,
    4 of them almost exactly halfway between two beats (termite_citadel 0.495 of a beat
    off, chalkboard_infinities 0.442). So we then QUANTIZE: fold the score curve at the
    beat period to find the beat grid, evaluate the `beats` phases that put a real beat on
    the morph, and take the best — with BEAT_PRIOR breaking near-ties toward the strong
    beats. Each candidate is refined +/-0.2 beat so a pushed or laid-back accent is still
    hit exactly; the guarantee is only that we never settle between beats.

    Returns (w0, lock, bar, info) where info names the beat of the bar we landed on."""
    bar = float(np.median(np.diff(morphs)))
    m = np.asarray(morphs)

    def score(w0):
        t = (m + w0) * f
        if period_m:
            t = np.mod(t, period_m)
        idx = (t * esr).astype(int)
        idx = idx[(idx >= 0) & (idx < len(env))]
        return float(env[idx].sum())

    grid = np.arange(0.0, bar, 0.01)
    scores = np.array([score(w) for w in grid])
    mean = float(scores.mean()) or 1e-9
    w0_free = float(grid[int(np.argmax(scores))])
    info = {"quantized": False, "beats": None, "beat_no": None, "free_off": None,
            "gain": 1.0}
    if not quantize:
        return w0_free, float(scores.max()) / mean, bar, info

    # METER: 4/4 by construction — the format puts one morph on one bar and the deck's
    # bar is 4 beats — so default to 4 and only accept 3 when a waltz take makes the
    # 3-grid decisively peakier. (Guessing by raw peakiness alone called 4 of 6 audited
    # 4/4 tracks "3": a 4/4 envelope folded at bar/3 still peaks.)
    if beats is None:
        def peak(b):
            pr = _fold(scores, grid, bar / b)
            return float(pr.max() / (pr.mean() + 1e-9))
        beats = 3 if peak(3) > peak(4) * 1.20 else 4
    beat_w = bar / beats
    phi = float(np.argmax(_fold(scores, grid, beat_w))) /         max(4, int(round(beat_w / 0.01))) * beat_w

    best = None
    bar_track, dbp = bar * f, None
    try:
        dbp = _downbeat_phase(env, esr, bar_track, beats)
    except Exception:
        dbp = None
    for k in range(beats):
        c = (phi + k * beat_w) % bar
        # refine onto the actual accent without leaving this beat
        loc = [(score(c + d), (c + d) % bar)
               for d in np.arange(-0.2 * beat_w, 0.2 * beat_w + 1e-9, 0.01)]
        sc, w = max(loc)
        beat_no = 0
        if dbp is not None:                    # which beat of the bar is this, musically?
            t0 = (m[0] + w) * f
            beat_no = int(round((((t0 - dbp) % bar_track) / (bar_track / beats)))) % beats
        cand = (sc * BEAT_PRIOR.get(beat_no, 0.93), sc, w, beat_no)
        if best is None or cand[0] > best[0]:
            best = cand
    _, sc, w0, beat_no = best
    d = ((w0_free - w0) % beat_w) / beat_w
    free_off = min(d, 1 - d)
    # CONSERVATIVE ADOPTION: the free maximum is already sitting on a beat for the large
    # majority (46 of 61 audited videos land within 0.05 of a beat), and forcing those onto
    # the grid only ever costs energy. Quantize ONLY when the free choice is genuinely
    # adrift — that is the failure Phil hears, and it leaves every healthy video identical.
    if free_off < OFFGRID_TOL:
        info.update(beats=beats, beat_no=beat_no + 1, free_off=round(free_off, 3))
        return w0_free, float(scores.max()) / mean, bar, info
    info.update(quantized=True, beats=beats, beat_no=beat_no + 1,
                free_off=round(free_off, 3), gain=round(sc / (scores.max() or 1e-9), 3))
    return float(w0), sc / mean, bar, info


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
    # judge the phrasing against the track's OWN bar (this envelope is not stretched yet)
    fit, bar_ac, clash_ac = meter_fit(env, esr, bar, ref=(m_bar if conf >= 0.10 else None))
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
    w0, lock, _, ph = best_phase(env_phase, esr, morphs, f,
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
          f"beat {ph['beat_no']}/{ph['beats']} | fit {fit:.2f} "
          f"(bar {bar_ac:.2f} vs rival {clash_ac:.2f}) | "
          f"seamless loop @ {dur:.2f}s (music tiled x{guard+1}, xf {XF:.2f}s)")
    return {"w0": w0, "stretch": f, "lock": lock, "m_bar": m_bar, "bar_conf": conf,
            "kick": round(kick, 3), "beat_no": ph["beat_no"], "beats": ph["beats"],
            "free_off": ph["free_off"], "fit": round(fit, 2),
            "bar_ac": round(bar_ac, 3), "clash_ac": round(clash_ac, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("track")
    ap.add_argument("--out", required=True)
    ap.add_argument("--journey"); ap.add_argument("--cut")
    a = ap.parse_args()
    align(a.video, a.track, a.out, journey=a.journey, cut=a.cut)


if __name__ == "__main__":
    main()
