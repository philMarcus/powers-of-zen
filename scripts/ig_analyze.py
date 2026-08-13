#!/usr/bin/env python3
"""Analyze the IG snapshots in outbox/ig_stats.jsonl — which variables move likes/view.

Method (codified 2026-08-13, see the audience-stats skill):
  * newest snapshot row per reel; likes/view is THE metric (age-independent, unlike views)
  * reels with views > --outlier (default 1000) are EXCLUDED from group contrasts and shown
    separately: like-rate falls with reach (colder audiences), so one pushed reel dominates
    and distorts any bucket it lands in
  * groups are compared by POOLED rate (sum likes / sum views) with a 95% binomial CI, with
    the unweighted per-video mean alongside; call a contrast real only when CIs separate
  * --features adds MEASURED video features (luminance, saturation, contrast, dark fraction
    — sampled frames via ffmpeg, cached in outbox/video_features.json) and correlates each
    with like%%.

Usage:
  python3 scripts/ig_analyze.py               # group contrasts
  python3 scripts/ig_analyze.py --features    # + video-feature correlations
"""
import argparse
import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
from score import win, FFMPEG  # noqa: E402

ROOT = pl.ROOT
STATS = ROOT / "outbox" / "ig_stats.jsonl"
FEATS = ROOT / "outbox" / "video_features.json"
W, H, MAXF = 160, 284, 24


def load_rows():
    snap = {}
    for line in STATS.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        snap[r["code"]] = r                      # newest wins (file is append-ordered)
    return [r for r in snap.values() if r.get("views") and r.get("likes") is not None]


def journey_meta(j):
    p = pl.journey_path(j) if j else None
    if not p:
        return {}
    spec = json.loads(p.read_text(encoding="utf-8"))
    regs = spec.get("registers") or []
    exps = [r.get("exp") for r in regs if isinstance(r.get("exp"), (int, float))]
    cards = len(regs) or None
    return {"cards": cards, "style": spec.get("style"),
            "engine": "e2" if (regs and "scene" in regs[0]) else "e1",
            "tier": None if not cards else
                    ("S" if cards <= 5 else "M" if cards <= 8 else "L"),
            "cosmic": bool(exps) and max(exps) >= 11,
            "subatomic": bool(exps) and min(exps) <= -8,
            "full": bool(exps) and max(exps) >= 11 and min(exps) <= -8}


def video_features(j, entry):
    """Sampled-frame luminance/saturation/contrast/dark-fraction, cached by file+mtime."""
    f = entry.get("file")
    if not f or not (ROOT / f).exists():
        return None
    path = ROOT / f
    cache = json.loads(FEATS.read_text(encoding="utf-8")) if FEATS.exists() else {}
    key = f"{j}:{path.stat().st_mtime_ns}"
    if cache.get(j, {}).get("key") == key:
        return cache[j]
    raw = ROOT / "output" / "music" / "_feat.raw"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", win(path),
                    "-vf", f"fps=1,scale={W}:{H}", "-frames:v", str(MAXF),
                    "-pix_fmt", "rgb24", "-f", "rawvideo", win(raw)], check=True)
    buf = np.frombuffer(raw.read_bytes(), dtype=np.uint8)
    raw.unlink(missing_ok=True)
    n = len(buf) // (W * H * 3)
    if not n:
        return None
    px = buf[: n * W * H * 3].reshape(n, H, W, 3).astype(np.float32) / 255.0
    lum = 0.2126 * px[..., 0] + 0.7152 * px[..., 1] + 0.0722 * px[..., 2]
    mx, mn = px.max(axis=-1), px.min(axis=-1)
    sat = np.where(mx > 0.03, (mx - mn) / (mx + 1e-6), 0.0)
    feat = {"key": key, "frames": int(n),
            "lum": round(float(lum.mean()), 4),           # overall brightness 0..1
            "sat": round(float(sat.mean()), 4),           # colorfulness 0..1
            "contrast": round(float(lum.std()), 4),       # tonal range
            "dark_frac": round(float((lum < 0.25).mean()), 4)}   # how much deep shadow
    cache[j] = feat
    FEATS.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return feat


def pooled(rs):
    L = sum(r["likes"] for r in rs)
    V = sum(r["views"] for r in rs)
    p = L / V if V else 0.0
    se = math.sqrt(p * (1 - p) / V) if V else 0.0
    um = statistics.mean(100.0 * r["likes"] / r["views"] for r in rs) if rs else 0.0
    return 100 * p, 100 * 1.96 * se, um, len(rs)


def show_group(title, rows, keyfn):
    print(f"\n== {title} ==")
    g = defaultdict(list)
    for r in rows:
        g[keyfn(r)].append(r)
    for k in sorted(g, key=lambda k: -pooled(g[k])[0]):
        p, ci, um, n = pooled(g[k])
        print(f"  {str(k):16} pooled {p:5.2f}% ±{ci:.2f} | mean {um:4.2f}% (n={n})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", action="store_true")
    ap.add_argument("--outlier", type=int, default=1000)
    a = ap.parse_args()

    rows = load_rows()
    d = pl.load()
    vids = d["videos"] if isinstance(d, dict) else d
    if isinstance(vids, dict):
        vids = list(vids.values())
    pv = {v["journey"]: v for v in vids}
    for r in rows:
        r.update(journey_meta(r.get("journey")))
        v = pv.get(r.get("journey"), {})
        r["cut"] = v.get("cut", "?")
        r["mood"] = (v.get("music") or {}).get("chosen")

    out = [r for r in rows if r["views"] > a.outlier]
    core = [r for r in rows if r["views"] <= a.outlier]
    p, ci, um, n = pooled(rows)
    print(f"ALL {n} reels: pooled {p:.2f}% ±{ci:.2f} | followers "
          f"{rows[-1].get('followers', '?')}")
    if out:
        print("reach outliers (excluded from contrasts): "
              + ", ".join(f"{r.get('journey')}({r['views']}v {100*r['likes']/r['views']:.1f}%)"
                          for r in out))

    known = [r for r in core if r.get("journey")]
    show_group("tier", known, lambda r: r.get("tier") or "?")
    show_group("style", known, lambda r: r.get("style") or "(legacy)")
    show_group("full scale", known, lambda r: r.get("full"))
    show_group("engine", known, lambda r: r.get("engine", "?"))
    show_group("cut", known, lambda r: r["cut"])
    show_group("music mood", known, lambda r: r["mood"] or "?")

    if a.features:
        print("\n== video features vs like% (measured frames) ==")
        feats = []
        for r in known:
            ft = video_features(r["journey"], pv.get(r["journey"], {}))
            if ft:
                feats.append((r, ft))
        for name in ("lum", "sat", "contrast", "dark_frac"):
            xs = np.array([ft[name] for _, ft in feats])
            ys = np.array([100.0 * r["likes"] / r["views"] for r, _ in feats])
            c = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 2 else float("nan")
            print(f"  corr(like%, {name:9}) = {c:+.2f}   (n={len(xs)})")
        print(f"\n  {'journey':24} {'like%':>6} {'lum':>6} {'sat':>6} {'contr':>6} {'dark%':>6}")
        for r, ft in sorted(feats, key=lambda t: -(t[0]["likes"] / t[0]["views"])):
            print(f"  {r['journey']:24} {100*r['likes']/r['views']:5.1f}% "
                  f"{ft['lum']:6.3f} {ft['sat']:6.3f} {ft['contrast']:6.3f} "
                  f"{ft['dark_frac']:6.3f}")


if __name__ == "__main__":
    main()
