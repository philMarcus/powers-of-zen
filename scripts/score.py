#!/usr/bin/env python3
"""Phase-dynamic scorer — lock a music bed's swells + sub-bass hits to a video's morphs.

THE THEORY (why this is easy for us and matches every time):
  We *generate* the video, so the morph rhythm is not something to detect — it's a
  known quantity. The picture rushes/transforms in the middle of every register and
  hovers at the boundaries (engine/grammar.py's zoom curve). That per-frame motion is
  the music's intensity automation. So we:
    1. read a motion-energy curve straight from the pixels (universal: works on any
       already-cut / phase-shifted / looped video), then
    2. use it as a gain envelope on the bed (swell on the rush, breathe on the hover)
       and drop a sub-bass IMPACT + a bright SHIMMER on each motion peak (the morph).
  Because the control curve is derived from the same motion the eye sees, the hits
  land on the morphs by construction — no beat-matching, no luck. For fresh renders we
  can instead emit the exact curve from the zoom schedule (schedule_curve(), TODO) for
  zero-detection perfection; the pixel path here is the model-agnostic bootstrap.

Usage:
  python3 scripts/score.py production/night_bloom_ds_divein.mp4 \
          output/music/night_bloom_ambient_s55.flac \
          --out review/music/night_bloom_synced_s55.mp4
"""
import argparse
import audioop
import math
import struct
import subprocess
import time
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FFBIN = ("/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/"
         "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin")
FFMPEG = f"{FFBIN}/ffmpeg.exe"
FFPROBE = f"{FFBIN}/ffprobe.exe"
SR = 48000
TMP = ROOT / "output" / "music"


def win(path):
    rel = Path(path).resolve().relative_to(ROOT)
    return "C:\\Users\\Phil\\zoomer\\" + str(rel).replace("/", "\\")


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr[-2000:])


def video_duration(path):
    # Windows ffprobe.exe occasionally returns an empty/partial read under load; retry
    # and reject implausibly small values so a flaky probe can't truncate the whole mux.
    last = ""
    for _ in range(5):
        out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nk=1:nw=1", win(path)],
                             capture_output=True, text=True).stdout.strip()
        last = out
        try:
            v = float(out)
            if v > 1.0:
                return v
        except ValueError:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"ffprobe gave no valid duration for {path!r} (last: {last!r})")


def schedule_morphs(journey, cut, final_dur, fps=12):
    """TRUE morph times (s) in the final video, derived from the zoom schedule — no
    detection. Registers each span F frames; the world changes at every register
    boundary. phase_shift.py cyclically rotates the loop to open at START_REGISTER, so
    we invert that rotation to place the boundaries in final-video time. This is the
    'we authored it, so we know' path — exact, every time."""
    import json as _json
    spec = _json.loads((ROOT / "journeys" / f"{journey}.json").read_text())
    fmt = spec.get("format", {}); sec = fmt.get("sec_per_scale", fmt.get("sec_per_decade", 2.4))
    regs = spec["registers"]
    starts, idx = [], 0
    for r in regs:
        starts.append(idx); idx += max(12, round(r.get("sec", sec) * fps))
    total = idx
    # replicate phase_shift.cut_time for the rotation offset
    from phase_shift import START_REGISTER
    target = START_REGISTER.get(journey)
    cut_frame = 0
    for k, r in enumerate(regs):
        F = max(12, round(r.get("sec", sec) * fps))
        if r.get("name") == target:
            fa = round(F * 0.25) if k > 0 else 0
            raw = starts[k] + fa + round((F - fa) * 0.4)
            cut_frame = raw if cut == "divein" else (total - raw)
    order = starts if cut == "divein" else [(total - s) % total for s in starts]
    times = sorted(((b - cut_frame) % total) / total * final_dur for b in order)
    return times


def motion_curve(video, fps=24, w=48, h=85, min_gap=1.5):
    """Return (env[0..1] at fps, fps, [accent_times_s]) from pixel motion energy."""
    raw = TMP / "_motion.raw"
    TMP.mkdir(parents=True, exist_ok=True)
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(video),
          "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", win(raw)])
    buf = array('B'); buf.frombytes(raw.read_bytes()); raw.unlink()
    fsz = w * h; n = len(buf) // fsz
    mot = [0.0]
    for i in range(1, n):
        a, b, s = i * fsz, (i - 1) * fsz, 0
        for p in range(fsz):
            d = buf[a + p] - buf[b + p]; s += d if d >= 0 else -d
        mot.append(s / fsz)
    sm = [sum(mot[max(0, i - 3):i + 4]) / len(mot[max(0, i - 3):i + 4]) for i in range(n)]
    lo, hi = min(sm), max(sm)
    e = [(v - lo) / (hi - lo + 1e-9) for v in sm]
    mean = sum(e) / n
    peaks = [i for i in range(2, n - 2) if e[i] == max(e[i - 2:i + 3]) and e[i] > mean]
    acc = []
    for i in peaks:
        if acc and (i - acc[-1]) / fps < min_gap:
            if e[i] > e[acc[-1]]: acc[-1] = i
        else:
            acc.append(i)
    return e, fps, [i / fps for i in acc]


def parse_journey_cut(video):
    parts = Path(video).stem.split("_")
    cut = "divein"
    if parts[-1] in ("divein", "zoomout"):
        cut = parts[-1]; parts = parts[:-1]
    if parts and parts[-1] in ("ds", "turbo"):
        parts = parts[:-1]
    return "_".join(parts), cut


def morph_env(t, morphs, floor, peak, rise, fall, offset):
    """Musical swell: the bed crescendos INTO each morph and eases after — no foreign
    synth, just the track breathing. Raised-cosine so it's smooth (no clicks)."""
    val = floor
    for m in morphs:
        c = m + offset
        if c - rise <= t < c:
            b = 0.5 - 0.5 * math.cos(math.pi * (t - (c - rise)) / rise)
        elif c <= t <= c + fall:
            b = 0.5 + 0.5 * math.cos(math.pi * (t - c) / fall)
        else:
            b = 0.0
        if b > 0:
            val = max(val, floor + (peak - floor) * b)
    return val


import re  # noqa: E402


def note_freq(name):
    pc = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
          "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    m = re.match(r"([A-G][b#]?)(-?\d)", name)
    midi = (int(m.group(2)) + 1) * 12 + pc[m.group(1)]
    return 440.0 * 2 ** ((midi - 69) / 12)


# D natural-minor scale across two octaves; the lead draws melody + pickups from this.
SCALE = ["D3", "E3", "F3", "G3", "A3", "Bb3", "C4", "D4", "E4", "F4", "G4", "A4",
         "Bb4", "C5", "D5", "E5", "F5"]
SCALE_F = [note_freq(n) for n in SCALE]
# a gentle D-minor line kept in a warm mid-low register (no bright high notes), resolving
# home to D. Not tracking the scale of the zoom — just pretty and atmospheric.
ACCENT_LINE = [7, 4, 9, 7, 11, 9, 7, 4, 5, 4, 7]
# motif around each accent: (bar_fraction, scale_steps_below_accent, gain, ring_s). Musical
# time (bar = morph interval). Sparse + soft: a single soft pickup, a moderate long-ringing
# accent ON the morph, a quiet tail — meant to be felt, not to announce itself.
MOTIF = [(-0.125, 2, 0.26, 0.5), (0.0, 0, 0.60, 1.9), (0.25, 3, 0.18, 1.1)]
# rotate soft voices so the lead isn't one mechanical instrument striking every morph.
# each: (partials [(harmonic, amp)], attack_s, decay_frac, detune)
VOICES = [
    ([(0.5, 0.28), (1, 1.0), (2, 0.18), (3, 0.04)], 0.09, 0.74, 1.004),  # warm pad + sub
    ([(1, 1.0), (2, 0.40), (3, 0.09)], 0.06, 0.60, 1.006),               # rounder mallet
    ([(0.5, 0.38), (1, 1.0), (2, 0.10)], 0.13, 0.82, 1.003),             # dark + slow
]


def synth_pad(freq, dur, gain, voice):
    """Soft warm ambient voice (additive, gentle rolloff, no click). `voice` picks the
    timbre — sub-weighted pad, rounder mallet, or dark slow — so morphs don't all sound
    identical. Warmer + darker than a bell; meant to sit under the surface."""
    parts, atk, decf, det = voice
    N = int(SR * dur); out = [0.0] * N
    tp = 2 * math.pi
    dec = dur * decf
    for k in range(N):
        t = k / SR
        env = min(1.0, t / atk) * math.exp(-t / dec)
        s = 0.0
        for h, a in parts:
            s += a * (math.sin(tp * freq * h * t) + 0.5 * math.sin(tp * freq * h * det * t))
        out[k] = gain * env * s / 2.8
    return out


def reverb_taps(x):
    """Cheap ambient air: a few attenuated delayed copies — glues the pad, adds space."""
    y = list(x)
    for delay, g in [(0.09, 0.30), (0.15, 0.22), (0.23, 0.15), (0.33, 0.09)]:
        d = int(delay * SR)
        for n in range(d, len(x)):
            y[n] += g * x[n - d]
    return y


def lead_mask(n, pattern):
    """Which morphs get a lead note; the rest are carried by just the bed's subtle swell,
    so the lead can lay out and let the atmosphere breathe (Phil likes that)."""
    if pattern == "alt":
        return [i % 2 == 0 for i in range(n)]
    if pattern == "sparse":
        return [i % 3 == 0 for i in range(n)]
    if pattern == "decay":            # dense early, thins out toward the end
        h = (n + 1) // 2
        return [(i < h) or (i % 2 == 0) for i in range(n)]
    if pattern == "swell":            # early laid-back, fuller later
        h = n // 2
        return [(i >= h) or (i % 2 == 0) for i in range(n)]
    return [True] * n                 # "all"


def score(video, bed, out, journey=None, cut=None, floor=0.86, peak=1.0,
          rise=0.7, fall=1.0, offset=0.0, lead=True, lead_gain=0.5, pattern="all"):
    """offset is MUSICAL — a fraction of the morph interval ('bar'); 0 = dead on the morph
    (Phil's pick), 1/16 = a sixteenth behind. Not clock seconds, so it holds at any tempo.
    `pattern` chooses which morphs the lead plays (see lead_mask)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    dur = video_duration(video)
    if journey is None or cut is None:
        journey, cut = parse_journey_cut(video)
    try:
        morphs = schedule_morphs(journey, cut, dur); src = "schedule"
    except Exception as ex:
        _, _, morphs = motion_curve(video); src = f"motion (schedule failed: {ex})"
    # tempo comes from the morph grid itself: the interval between morphs is one "bar".
    gaps = sorted(morphs[i + 1] - morphs[i] for i in range(len(morphs) - 1))
    bar = gaps[len(gaps) // 2] if gaps else 2.4          # median morph interval (s)
    off_s = offset * bar                                  # musical offset -> seconds
    bpm = 240.0 / bar                                     # bar = 4 beats

    bedwav = TMP / "_bed.wav"
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(bed), "-ar", str(SR), "-ac", "2",
          win(bedwav)])
    w = wave.open(str(bedwav), 'rb'); nfr = w.getnframes(); raw = w.readframes(nfr); w.close()
    need = int(dur * SR)
    if nfr < need:
        raw += b'\x00' * ((need - nfr) * 4)
    raw = raw[:need * 4]

    # musical morph-swell envelope on the bed, per 10ms block (audioop.mul is C-fast)
    block = int(SR * 0.01) * 4
    scaled = bytearray(); pos = 0
    while pos < len(raw):
        chunk = raw[pos:pos + block]
        g = morph_env((pos // 4) / SR, morphs, floor, peak, rise, fall, off_s)  # noqa
        scaled += audioop.mul(chunk, 2, g)
        pos += block
    master = bytearray(scaled[:len(raw)])

    # dominant lead: a soft-pad MELODIC MOTIF whose accent note lands ON each morph. The
    # motif has pickups + a tail, so it's musical (not an obvious ding), but its strongest,
    # longest note is placed to the sample on the morph — the attack is the sync.
    if lead:
        ns = len(master) // 4
        buf = [0.0] * ns
        mask = lead_mask(len(morphs), pattern)
        for i, m in enumerate(morphs):
            if not mask[i]:
                continue
            ai = ACCENT_LINE[i % len(ACCENT_LINE)]
            voice = VOICES[i % len(VOICES)]
            vg = [1.0, 0.85, 0.92][i % 3]                   # gentle per-morph level variation
            for rel, below, g, ndur in MOTIF:
                si = max(0, min(len(SCALE_F) - 1, ai - below))
                note = synth_pad(SCALE_F[si], ndur, g * vg, voice)
                start = int((m + off_s + rel * bar) * SR)   # bar-fraction -> seconds
                for k, v in enumerate(note):
                    idx = start + k
                    if 0 <= idx < ns:
                        buf[idx] += v
        buf = reverb_taps(buf)
        lead_b = bytearray(ns * 4)
        for n in range(ns):
            s = int(max(-1.0, min(1.0, buf[n] * lead_gain)) * 32767)
            struct.pack_into('<hh', lead_b, n * 4, s, s)
        master = bytearray(audioop.add(bytes(master), bytes(lead_b), 2))

    scored = TMP / "_scored.wav"
    ww = wave.open(str(scored), 'wb')
    ww.setnchannels(2); ww.setsampwidth(2); ww.setframerate(SR)
    ww.writeframes(bytes(master)); ww.close()

    fo = max(0.0, dur - 0.5)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.12,"
          f"afade=t=out:st={fo:.3f}:d=0.5")
    _run([FFMPEG, "-y", "-loglevel", "error", "-i", win(video), "-i", win(scored),
          "-filter_complex", f"[1:a]{af}[a]", "-map", "0:v:0", "-map", "[a]",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", win(out)])
    bedwav.unlink(missing_ok=True); scored.unlink(missing_ok=True)
    print(f"  scored -> {out}\n    {dur:.1f}s | {len(morphs)} morphs ({src}) | "
          f"bar {bar:.2f}s ({bpm:.0f}bpm) | offset {offset:.4g} bar = {off_s*1000:.0f}ms @ "
          f"{[round(a, 1) for a in morphs]}")
    return str(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("bed")
    ap.add_argument("--out", required=True)
    ap.add_argument("--journey"); ap.add_argument("--cut")
    ap.add_argument("--floor", type=float, default=0.82)
    ap.add_argument("--peak", type=float, default=1.0)
    ap.add_argument("--rise", type=float, default=0.7)
    ap.add_argument("--fall", type=float, default=1.0)
    ap.add_argument("--offset", type=float, default=0.0,
                    help="musical offset as fraction of a bar (0 = dead on, 1/16 sixteenth)")
    ap.add_argument("--pattern", default="all",
                    help="lead pattern: all | alt | sparse | decay | swell")
    ap.add_argument("--no-lead", dest="lead", action="store_false")
    ap.add_argument("--lead-gain", type=float, default=0.5)
    a = ap.parse_args()
    score(a.video, a.bed, a.out, journey=a.journey, cut=a.cut, floor=a.floor,
          peak=a.peak, rise=a.rise, fall=a.fall, offset=a.offset, lead=a.lead,
          lead_gain=a.lead_gain, pattern=a.pattern)


if __name__ == "__main__":
    main()
