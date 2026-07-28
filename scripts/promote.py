#!/usr/bin/env python3
"""Place a video's files by the folder rule (2026-07-27):
  production/            = ONLY the postable file (chosen model + chosen cut)
  production_alternates/ = the other 3 variants (other model both cuts + other cut
                           of chosen model)

The chosen model+cut come from pipeline.json (derived from each video's `file`).
Files are gathered from wherever they currently are (review*, production*).

Usage:
  python3 scripts/promote.py <journey>   # reorg one video per pipeline.json
  python3 scripts/promote.py --all       # reorg every video in pipeline.json
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl

ROOT = pl.ROOT
SEARCH = ["production", "production_alternates", "review", "review_divein"]


def variant_basename(journey, model, cut):
    return journey + ("_ds" if model == "ds" else "") + ("_divein" if cut == "divein" else "") + ".mp4"


def _variants(journey):
    """The 4 variant (basename, model, cut) for a journey."""
    return [(variant_basename(journey, m, c), m, c)
            for m in ("turbo", "ds") for c in ("zoomout", "divein")]


def switch(journey, model, cut):
    """Change a video's chosen model+cut: update pipeline (file/model/cut) and move the
    newly-chosen variant into production/ (old one to alternates). Used by the dashboard."""
    d = pl.load()
    v = pl.get(d, journey)
    if not v:
        print(f"no pipeline entry for {journey}"); return
    v["model"], v["cut"] = model, cut
    v["file"] = "production/" + variant_basename(journey, model, cut)
    pl.save(d)
    reorg(journey, model, cut)
    pl.telem("switch", journey=journey, detail=f"{model}/{cut}")


def _find(basename):
    for d in SEARCH:
        p = ROOT / d / basename
        if p.exists():
            return p
    return None


def reorg(journey, chosen_model, chosen_cut):
    (ROOT / "production").mkdir(exist_ok=True)
    (ROOT / "production_alternates").mkdir(exist_ok=True)
    moved = []
    for basename, model, cut in _variants(journey):
        src = _find(basename)
        if not src:
            continue
        dest_dir = "production" if (model == chosen_model and cut == chosen_cut) else "production_alternates"
        dest = ROOT / dest_dir / basename
        if src.resolve() != dest.resolve():
            shutil.move(str(src), str(dest))
            moved.append(f"{basename} -> {dest_dir}")
    print(f"{journey} (chosen {chosen_model}/{chosen_cut}): " + (", ".join(moved) or "already placed"))
    return moved


def main():
    data = pl.load()
    if sys.argv[1:] == ["--all"]:
        for v in data["videos"]:
            reorg(v["journey"], v["model"], v["cut"])
    elif len(sys.argv) == 2:
        v = pl.get(data, sys.argv[1])
        if not v:
            print(f"no pipeline entry for {sys.argv[1]}"); sys.exit(1)
        reorg(v["journey"], v["model"], v["cut"])
    else:
        print(__doc__); sys.exit(1)
    pl.telem("promote", detail=sys.argv[1])


if __name__ == "__main__":
    main()
