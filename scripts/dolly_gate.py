#!/usr/bin/env python3
"""dolly_gate — mechanical checks on a finished dolly_lab run (DEPTH 2.0 gate).

Phil judges the LOOK (12fps looped clip); this script judges what a script can:
  1. SMEAR: sharpness (Laplacian variance) at card starts vs card ends, per arm — the
     residual must not degrade structure faster than re-diffusion re-anchors it (the
     orbit-v1 failure mode). PASS = each parallax arm's end-of-card sharpness stays
     within ~15% of baseline's.
  2. PARALLAX ACTIVE: build/parallax.jsonl rows exist with sane med/k, and the depth
     source switches scaffold <-> da where expected.
  3. DIVERGENCE: mean |frame difference| between each arm and baseline over time — the
     arms SHOULD diverge (parallax changes what the model paints); a flat-zero curve
     means the residual silently no-opped.

Usage: python3 scripts/dolly_gate.py            # reads output/dolly_lab/<journey>_runs.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "output" / "dolly_lab"


def lap_var(img):
    a = np.asarray(img.convert("L"), np.float32)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)
    from numpy.lib.stride_tricks import sliding_window_view
    w = sliding_window_view(a, (3, 3))
    return float(((w * k).sum(axis=(2, 3)) ** 2).mean())


def main():
    recs = sorted(LAB.glob("*_runs.json"))
    if not recs:
        sys.exit("no dolly_lab runs recorded")
    rec = json.loads(recs[-1].read_text())
    runs, frames = rec["runs"], rec["frames"]
    arms = list(runs)
    card = 24  # squid_lantern fpb6 dur4
    checks = [1] + [c * card - 2 for c in range(1, frames // card + 1) if c * card - 2 < frames]

    print(f"journey {rec['journey']}, {frames} frames/arm\n")
    print("1) SHARPNESS (Laplacian var) at card starts/ends:")
    print(f"   {'frame':>6} " + " ".join(f"{a:>10}" for a in arms))
    sharp = {}
    for i in checks:
        row = []
        for a in arms:
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            v = lap_var(Image.open(p)) if p.exists() else float("nan")
            sharp[(a, i)] = v
            row.append(v)
        print(f"   {i:>6} " + " ".join(f"{v:>10.0f}" for v in row))
    base = arms[0]
    worst = 0.0
    for a in arms[1:]:
        for i in checks:
            r = sharp[(a, i)] / max(1e-6, sharp[(base, i)])
            worst = max(worst, 1 - r)
    print(f"   worst sharpness deficit vs baseline: {100 * worst:.1f}%  "
          f"({'PASS' if worst < 0.15 else 'CHECK THE CLIP'})")

    print("\n2) PARALLAX LOG per arm:")
    for a in arms:
        pl_ = Path(runs[a]) / "build" / "parallax.jsonl"
        rows = [json.loads(x) for x in pl_.read_text().splitlines()] if pl_.exists() else []
        srcs = {}
        for r in rows:
            srcs[r.get("src")] = srcs.get(r.get("src"), 0) + 1
        meds = [r["med"] for r in rows]
        print(f"   {a:5}: {len(rows)} rows, srcs {srcs}, med range "
              f"{min(meds):.2f}..{max(meds):.2f}" if rows else f"   {a:5}: (no rows — gain 0)")

    print("\n3) DIVERGENCE from baseline (mean |diff|, 0-255):")
    picks = [8, frames // 4, frames // 2, 3 * frames // 4, frames - 4]
    print(f"   {'frame':>6} " + " ".join(f"{a:>10}" for a in arms[1:]))
    for i in picks:
        b = Path(runs[base]) / "build" / "frames" / f"{i:05d}.png"
        if not b.exists():
            continue
        ab = np.asarray(Image.open(b), np.float32)
        row = []
        for a in arms[1:]:
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            row.append(float(np.abs(np.asarray(Image.open(p), np.float32) - ab).mean())
                       if p.exists() else float("nan"))
        print(f"   {i:>6} " + " ".join(f"{v:>10.1f}" for v in row))


if __name__ == "__main__":
    main()
