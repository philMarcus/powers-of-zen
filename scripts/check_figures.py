#!/usr/bin/env python3
"""Scan rendered frames for lone human figures.

    python3 scripts/check_figures.py output/quantum_orrery/v1          # sample a render
    python3 scripts/check_figures.py output/*/v*  --frames 0           # frame-0 audit, many runs
    python3 scripts/check_figures.py output/night_bloom/v10 --every 20 # sweep a whole render

Exit status 1 if any figure was found, so it can gate a batch. GPU-serial: it shares ComfyUI
with the renderer, so DON'T run it against a live render (it starves the sampler — that is what
turned a 14s/frame dive into 36s/frame while this tool was being built).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
from PIL import Image  # noqa: E402

import figure  # noqa: E402


def frames_of(run):
    d = Path(run)
    d = d / "build" / "frames" if (d / "build" / "frames").is_dir() else d
    return sorted(d.glob("*.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="render dirs (output/<journey>/vN)")
    ap.add_argument("--frames", type=int, nargs="*", help="specific frame indices (default: sweep)")
    ap.add_argument("--every", type=int, default=28, help="sweep cadence when --frames absent")
    args = ap.parse_args()

    bad = 0
    for run in args.runs:
        fs = frames_of(run)
        if not fs:
            print(f"{run}: no frames")
            continue
        picks = ([fs[i] for i in args.frames if i < len(fs)] if args.frames is not None
                 else fs[::max(1, args.every)])
        hits = []
        for f in picks:
            hit = figure.find(Image.open(f).convert("RGB"))
            if hit:
                hits.append((f.stem, figure.describe(hit)))
        tag = "FIGURE" if hits else "clean "
        print(f"[{tag}] {run}  ({len(picks)} frames checked)")
        for stem, desc in hits:
            print(f"          frame {stem}: {desc}")
        bad += bool(hits)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
