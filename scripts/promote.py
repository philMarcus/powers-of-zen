#!/usr/bin/env python3
"""Promote a video to production — the STANDARD step when Phil marks a video ready.

Moves the CHOSEN model's cuts (zoom-out + dive-in) out of review/ into production/,
and the OTHER model's counterpart cuts out of review/ into production_alternates/.
Everything not chosen and not the alternate stays in review/. Missing files are skipped.

Usage:  python3 scripts/promote.py <journey> <turbo|ds>
Example: python3 scripts/promote.py iris_observatory ds
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _suf(model):
    return "" if model == "turbo" else "_ds"


def _mv(rel_src, dstdir):
    s = ROOT / rel_src
    if s.exists():
        (ROOT / dstdir).mkdir(exist_ok=True)
        shutil.move(str(s), str(ROOT / dstdir / s.name))
        print(f"  moved {rel_src} -> {dstdir}/")
    else:
        print(f"  (skip missing {rel_src})")


def promote(journey, chosen):
    alt = "ds" if chosen == "turbo" else "turbo"
    cs, asf = _suf(chosen), _suf(alt)
    print(f"promote {journey} (chosen={chosen}, alt={alt})")
    _mv(f"review/{journey}{cs}.mp4", "production")
    _mv(f"review_divein/{journey}{cs}_divein.mp4", "production")
    _mv(f"review/{journey}{asf}.mp4", "production_alternates")
    _mv(f"review_divein/{journey}{asf}_divein.mp4", "production_alternates")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("turbo", "ds"):
        print(__doc__)
        sys.exit(1)
    promote(sys.argv[1], sys.argv[2])
