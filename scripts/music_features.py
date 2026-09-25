#!/usr/bin/env python3
"""MUSIC FEATURES (2026-09-25, Phil: "make sure we have instrumentation for each video's music").
One record per video that has a chosen track: what the deck SAID (lane, rhythm feel, instrument
family, mood words) and what the audio IS (measured with numpy from the chosen take — brightness,
low-end share, dynamics, onset density, actual pulse period). Cached in outbox/music_features.json
keyed by journey + track path + mtime; `python3 scripts/music_features.py` refreshes it,
`--print` tabulates. scripts/dataset.py joins these into the analysis table."""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402
from score import FFMPEG, win  # noqa: E402

OUT = ROOT / "outbox" / "music_features.json"
DECK = json.loads((ROOT / "styles" / "music_deck.json").read_text(encoding="utf-8"))
SR = 22050

# instrument FAMILIES: a coarser grouping of the ten lanes so ~80 videos give each class some
# support (the lane itself is kept as the fine label). Assigned from the deck's own words.
FAMILY = {
    "glass_chapel": "bells_glass", "choir_of_dust": "bells_glass", "music_box": "bells_glass",
    "wooden_orbit": "mallets_plucked", "night_market": "mallets_plucked",
    "deep_archive": "pads_drone", "analog_dawn": "pads_drone", "tide_organ": "pads_drone",
    "ember_pulse": "pads_drone",
    "aurora_strings": "strings",
}
INSTRUMENT_WORDS = ["bell", "choir", "pad", "marimba", "kalimba", "bass", "drone", "hang drum",
                    "koto", "synth", "mallet", "glass harmonica", "music box", "celesta", "organ",
                    "string", "harp", "808", "chime", "shimmer", "pluck", "swell"]


def decode(track):
    """flac -> mono float32 at SR via ffmpeg (a temp wav; the project's wave-based loaders)."""
    tmp = ROOT / "output" / "music" / "_feat_tmp.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", win(ROOT / track), "-ac", "1",
                    "-ar", str(SR), "-f", "wav", win(tmp)], check=True)
    w = wave.open(str(tmp), "rb")
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    w.close()
    tmp.unlink(missing_ok=True)
    return a


def audio_features(x, hop=512, nfft=2048):
    n = 1 + (len(x) - nfft) // hop
    wdw = np.hanning(nfft).astype(np.float32)
    frames = np.stack([x[i * hop:i * hop + nfft] * wdw for i in range(n)])
    mag = np.abs(np.fft.rfft(frames, axis=1)) + 1e-9
    freqs = np.fft.rfftfreq(nfft, 1.0 / SR)
    power = mag ** 2
    tot = power.sum(axis=1)
    centroid = (power * freqs).sum(axis=1) / tot
    cum = np.cumsum(power, axis=1) / tot[:, None]
    rolloff = freqs[np.argmax(cum >= 0.85, axis=1)]
    low = power[:, freqs < 150].sum(axis=1) / tot
    high = power[:, freqs > 4000].sum(axis=1) / tot
    rms = np.sqrt((frames ** 2).mean(axis=1))
    flux = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
    flux = flux / (flux.max() + 1e-9)
    esr = SR / hop
    # onsets = flux peaks above a moving median (a simple, robust picker)
    k = int(esr * 0.5) | 1
    med = np.array([np.median(flux[max(0, i - k):i + k + 1]) for i in range(len(flux))])
    peaks = [i for i in range(1, len(flux) - 1)
             if flux[i] > flux[i - 1] and flux[i] >= flux[i + 1] and flux[i] > med[i] + 0.08]
    dur = len(x) / SR
    # dominant pulse period from the onset-envelope autocorrelation, 0.3-1.5 s
    f = flux - flux.mean()
    ac = np.correlate(f, f, "full")[len(f) - 1:]
    ac = ac / (ac[0] + 1e-9)
    lo, hi = int(0.3 * esr), int(1.5 * esr)
    pulse_s = float((np.argmax(ac[lo:hi]) + lo) / esr)
    pulse_strength = float(ac[lo:hi].max())
    # spectral flatness (noisiness vs tonality)
    flat = np.exp(np.log(mag).mean(axis=1)) / mag.mean(axis=1)
    return {
        "dur_s": round(dur, 1),
        "brightness_hz": round(float(centroid.mean())),          # spectral centroid
        "rolloff85_hz": round(float(np.median(rolloff))),
        "low_share": round(float(low.mean()), 3),               # energy below 150 Hz
        "high_share": round(float(high.mean()), 4),             # energy above 4 kHz
        "loudness_rms": round(float(rms.mean()), 4),
        "dynamics": round(float(rms.std() / (rms.mean() + 1e-9)), 3),   # coefficient of variation
        "onsets_per_s": round(len(peaks) / dur, 2),
        "pulse_s": pulse_s, "pulse_bpm": round(60.0 / pulse_s, 1),
        "pulse_strength": round(pulse_strength, 3),
        "flatness": round(float(flat.mean()), 4),
    }


WORD_FAMILY = [  # instrument words -> family, for takes made before the deck (no lane)
    (("marimba", "kalimba", "koto", "hang drum", "pluck", "guitar", "mallet"), "mallets_plucked"),
    (("bell", "glass", "celesta", "music box", "chime", "tine"), "bells_glass"),
    (("string", "harp", "bowed", "cello", "violin"), "strings"),
    (("pad", "drone", "organ", "synth", "choir"), "pads_drone"),
]


def deck_features(cand):
    """Lane / rhythm feel / instrument family for EVERY naming era: deck takes carry `lane`
    and a mood with '· <rhythm>' appended; wildcards ('-wild') and pulse top-ups
    ('pulse1-<lane>') keep the real lane in `lane`; pre-deck takes ('tender', 'warm') have
    no lane — their family comes from the instrument words in their own prompt."""
    text = ((cand.get("mood") or "") + " " + (cand.get("tags") or "")).lower()
    lane = cand.get("lane") or (cand["id"].split("-")[0] if cand["id"].split("-")[0] in DECK["lanes"] else "")
    # rhythm: the mood suffix, else the deck sentence quoted in the tags, else the id suffix
    rhythm = ""
    mood = cand.get("mood") or ""
    if "·" in mood:
        rhythm = mood.split("·")[-1].split("(")[0].strip()
    if rhythm not in DECK["rhythms"]:
        rhythm = next((r for r, sent in DECK["rhythms"].items() if sent.lower()[:60] in text), "")
    if rhythm not in DECK["rhythms"]:
        suf = cand["id"].split("-", 1)[1] if "-" in cand["id"] else ""
        rhythm = suf if suf in DECK["rhythms"] else "unspecified"
    instr = DECK["lanes"].get(lane, {}).get("instr", "")
    words = sorted({w for w in INSTRUMENT_WORDS if w in (instr + " " + text)})
    family = FAMILY.get(lane)
    if not family:
        family = next((fam for ws, fam in WORD_FAMILY if any(w in text for w in ws)), "other")
    return {"lane": lane or "pre_deck", "deck_era": bool(lane), "rhythm": rhythm, "family": family,
            "instr_text": instr or mood.split("·")[0].strip(), "instruments": words,
            "mood": DECK["lanes"].get(lane, {}).get("mood", mood.split("·")[0].strip()),
            "kick": cand.get("kick"), "lock": cand.get("lock"), "fit": cand.get("fit"),
            "bar_conf": cand.get("bar_conf"), "seed": cand.get("seed")}


def main():
    p = pl.load()
    cache = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    done = 0
    for v in p["videos"]:
        m = v.get("music") or {}
        cid = m.get("chosen")
        if not cid:
            continue
        cand = next((c for c in m.get("candidates", []) if c["id"] == cid), None)
        if not cand:
            continue
        track = cand.get("track") or f"output/music/{v['journey']}_{cid}.flac"
        path = ROOT / track
        if not path.exists():
            continue
        key = f"{cid}:{path.stat().st_mtime_ns}"
        if cache.get(v["journey"], {}).get("key") == key:
            continue
        feat = {"key": key, "journey": v["journey"], "chosen": cid, "bpm": m.get("bpm"),
                "bar_s": m.get("bar"), "key_sig": m.get("key"),
                "mode": ("minor" if "minor" in (m.get("key") or "") else "major")}
        feat.update(deck_features(cand))
        try:
            feat.update(audio_features(decode(track)))
        except Exception as e:
            feat["audio_error"] = str(e)[:120]
        cache[v["journey"]] = feat
        done += 1
        print(f"  {v['journey']:22s} {cid:28s} {feat.get('family','?'):15s} "
              f"bright {feat.get('brightness_hz','?')} Hz  low {feat.get('low_share','?')}  "
              f"onsets/s {feat.get('onsets_per_s','?')}  pulse {feat.get('pulse_bpm','?')} bpm", flush=True)
    OUT.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    print(f"music_features: {done} new, {len(cache)} total -> {OUT}")
    if "--print" in sys.argv:
        import collections
        print(collections.Counter(f["family"] for f in cache.values()))
        print(collections.Counter(f["rhythm"] for f in cache.values()))


if __name__ == "__main__":
    main()
