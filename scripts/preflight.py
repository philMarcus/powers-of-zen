#!/usr/bin/env python3
"""Pre-flight a journey before spending an hour of GPU on it.

Checks, in order of how much they cost when wrong:
  * frame 0's FULL prompt (scene + target + style suffix + brand tail) for figure bait
  * render_start present, and NOT putting the seam card first or last
  * frame count / duration tier
  * uniform bars, counter on
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grammar  # noqa: E402
import pipeline as pl  # noqa: E402
import style as _style  # noqa: E402

BAIT = re.compile(r"\b(halos?|auras?|nimbus|crowns?|robes?|veils?|shrouds?|mantles?|wings?|"
                  r"embrace|torso|limbs?|lobes?|grandeur|regal|majestic|goddess|angels?|"
                  r"portraits?|figures?|mannequins?|dress-?form)\b", re.I)
NAME_ONLY = re.compile(r"\b(quark|hadron|boson|gluon|fermion|superposition|probability cloud|"
                       r"spacetime foam|wavefunction)\b", re.I)

for name in sys.argv[1:]:
    p = pl.journey_path(name)
    if not p:
        print(f"{name}: NO journey file"); continue
    spec = json.loads(p.read_text(encoding="utf-8"))
    sfx, model, _ = _style.resolve(spec, None)
    spec["style_suffix"] = sfx
    out = grammar.compile_journey(spec, 12, "in")
    phases, frames = out[0], out[1]
    total = len(frames)
    regs = spec["registers"]
    durs = sorted({r.get("dur") for r in regs})
    seam_idx = [i for i, r in enumerate(regs) if r.get("kind") == "seam"]
    start = spec.get("render_start")
    order = [r["name"] for r in regs]
    rot = order.index(start) if start in order else 0
    rotated = order[rot:] + order[:rot]
    seam_names = [regs[i]["name"] for i in seam_idx]
    first_last = [rotated[0], rotated[-1]]
    p0 = phases[0]["prompt"]

    print(f"\n=== {name} ===")
    print(f"  cards {len(regs)} · {total} frames · {total/12:.1f}s · style {spec.get('style')} [{model}]")
    print(f"  dur {durs} {'UNIFORM' if len(durs) == 1 else '!! MIXED BARS'}"
          f" · counter {spec.get('format', {}).get('counter')}")
    print(f"  render_start={start!r} -> order starts {rotated[0]!r}, ends {rotated[-1]!r}")
    bad_seam = [s for s in seam_names if s in first_last]
    print(f"  seams {seam_names} {'!! SEAM AT AN END: ' + str(bad_seam) if bad_seam else 'ok'}")
    bait = sorted(set(w.lower() for w in BAIT.findall(p0)))
    nameonly = sorted(set(w.lower() for w in NAME_ONLY.findall(p0)))
    print(f"  frame-0 bait   : {bait or 'none'}")
    print(f"  frame-0 name-only physics: {nameonly or 'none'}")
    cam = pl.cameo_realm_check(spec)
    print(f"  cameo realm    : {'!! ' + ' | '.join(cam) if cam else 'ok'}")
    print(f"  frame-0 prompt : {p0[:150]}")
