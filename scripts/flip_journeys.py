#!/usr/bin/env python3
"""One-time converter: flip build-out journeys (SMALL->LARGE, afar/loop_hint)
into build-in journeys (LARGE->SMALL, next_target, circular).

The reversed cycle starts at the old last register, so start scales stay varied.
Each card's next_target is the next-smaller card's old `afar` (same semantic:
'this world seen small'). The last card wraps to the first (circular).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402

NAMES = ["tide_of_life", "mineral_heart", "night_bloom", "cartographer",
         "dollhouse", "food_chain", "iris_observatory", "black_hole",
         "antenna_ball", "snowfall"]

for n in NAMES:
    p = pl.journey_path(n)
    spec = json.loads(p.read_text())
    regs = spec["registers"]
    if not regs[0].get("afar"):
        print(f"{n}: already build-in, skipping")
        continue
    rev = list(reversed(regs))
    flipped = []
    for i, r in enumerate(rev):
        nxt = rev[(i + 1) % len(rev)]
        card = {k: v for k, v in r.items() if k not in ("afar", "loop_hint")}
        card["next_target"] = nxt["afar"]
        flipped.append(card)
    spec["registers"] = flipped
    fmt = spec.get("format", {})
    fmt.pop("build", None)
    fmt["exact_loop"] = True
    spec["format"] = fmt
    p.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"{n}: flipped to build-in, starts at "
          f"{flipped[0]['name']} (exp {flipped[0]['exp']})")
