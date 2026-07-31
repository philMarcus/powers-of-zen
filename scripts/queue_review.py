#!/usr/bin/env python3
"""Ingest a finished dive render into the REVIEW queue.

Copies both cuts of the newest COMPLETE render into review/ (zoom-out) and review_divein/
(dive-in) under promote-compatible names, and upserts a pipeline.json entry with state=review
(no music, blank caption — Phil reviews, picks cut/model, approves → Music).

Usage:  python3 scripts/queue_review.py <journey> <ds|turbo>
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402
import promote  # noqa: E402
from engine import grammar  # noqa: E402


def newest_complete(name, total, bases=None):
    """Newest vN with a complete frame set. `bases` = output subdirs to search, newest wins.
    Since the style deck picks the model, renders now land in output/<journey>/ with NO
    _<model> suffix (the suffix only appears when --model was passed), so callers pass both."""
    best = None
    for b in (bases or [name]):
        base = ROOT / "output" / b
        if not base.exists():
            continue
        for d in sorted([p for p in base.glob("v[0-9]*") if p.name[1:].isdigit()],
                        key=lambda p: int(p.name[1:])):
            if len(list((d / "build" / "frames").glob("*.png"))) >= total:
                best = d
    return best


def cameo_of(spec):
    for r in spec["registers"]:
        if r.get("cameo"):
            return Path(r["cameo"]["sprite"]).stem
    return None


def main():
    journey, model = sys.argv[1], sys.argv[2]
    # --src <run dir>: ingest a specific render (e.g. one rendered under a different journey
    # name, or any vN that isn't the newest). Otherwise search both naming conventions.
    src_arg = None
    if "--src" in sys.argv:
        src_arg = ROOT / sys.argv[sys.argv.index("--src") + 1]
    spec = json.loads((ROOT / "journeys" / f"{journey}.json").read_text())
    _, z, *_ = grammar.compile_journey(spec, 12)
    total = len(z)
    name = f"{journey}_{model}"
    src = src_arg or newest_complete(name, total, bases=[name, journey])
    if not src or not src.exists():
        print(f"no complete render for {name} (need {total} frames)")
        sys.exit(1)
    # the render's mp4s are named after the render dir's journey, not necessarily `journey`
    stem = next((p.stem for p in src.glob("*.mp4") if not p.stem.endswith("_divein")
                 and not p.stem.endswith("_review")), name)
    name = stem
    (ROOT / "review").mkdir(exist_ok=True)
    (ROOT / "review_divein").mkdir(exist_ok=True)
    pairs = [(src / f"{name}.mp4", ROOT / "review" / promote.variant_basename(journey, model, "zoomout")),
             (src / f"{name}_divein.mp4", ROOT / "review_divein" / promote.variant_basename(journey, model, "divein"))]
    for s, d in pairs:
        if s.exists():
            shutil.copy(str(s), str(d))
            print(f"  copied {s.name} -> {d.relative_to(ROOT)}")
        else:
            print(f"  WARN missing cut: {s.relative_to(ROOT)}")
    divein_rel = str((ROOT / "review_divein" / promote.variant_basename(journey, model, "divein")).relative_to(ROOT))
    dd = pl.load()
    v = pl.get(dd, journey)
    if v:
        already = v.get("state") == "review" and v.get("file")
        v["state"] = "review"
        v["cameo"] = cameo_of(spec)
        if not already:   # keep the first-ingested model/cut as the displayed default
            v.update({"model": model, "cut": "divein", "file": divein_rel})
    else:
        dd["videos"].append({
            "journey": journey, "model": model, "cut": "divein", "file": divein_rel,
            "title": "", "caption": "", "yt_title": "", "yt_desc": "",
            "cameo": cameo_of(spec), "state": "review", "scheduled": None,
            "platforms": pl.blank_platforms(), "created": pl._now()[:10]})
    pl.save(dd)
    pl.telem("review", journey=journey, detail=f"{model}/divein (src {src.name})")
    print(f"{journey}: queued to REVIEW ({model}/divein) from {src.name}")


if __name__ == "__main__":
    main()
