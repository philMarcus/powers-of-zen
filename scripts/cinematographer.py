#!/usr/bin/env python3
"""CINEMATOGRAPHER v1 — rule-based camera assignment (ENGINE 3 Phase D, 2026-08-27).

A SEPARATE role from the journey composer (PLAN "ENGINE 3"): the composer stays blind to
camera; this pass reads a FINISHED journey and writes its `camera` plan deterministically.
v1 is the rule FLOOR — auditable, reproducible, no model in the loop (an LLM taste pass
is the planned v2, mirroring the refill's composers). Doctrine: journeys/CINEMA.md.

THE RULES (moves are spice, not sauce — most cards stay on plain drift):
  never moved : the render-start card (establish + loop lap/tail), seam cards, the card
                arriving FROM a seam (its morph IS the event), cameo cards (sprite
                propagation is exact only for zoom+roll — v1 skips them entirely)
  spiral      : the first eligible card WITH a target (the tracker gives the revolve a
                subject — "circling the thing we're diving toward"), rate 0.4
  orbit       : the first eligible FIELD card (no target) after that, rate 0.3
  roll        : up to two more eligible cards, rate 0.3, sign alternating (starting sign
                from the journey name's crc32, so different journeys phase differently
                but a re-run reproduces)
  at most 2 depth moves + 2 rolls per journey — the floor keeps the brand calm.

NOT wired into the nightly pipeline: a journey only gains camera when this tool is run
on it explicitly (Phil judges the lab clips first).

Usage:
  python3 scripts/cinematographer.py <journey> [<journey> ...]   # print the plan
  python3 scripts/cinematographer.py <journey> --write           # persist into the JSON
"""
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import camera as _camera  # noqa: E402
import pipeline as pl  # noqa: E402

SPIRAL_RATE, ORBIT_RATE, ROLL_RATE = 0.4, 0.3, 0.3
DEPTH_BUDGET, ROLL_BUDGET = 2, 2


def plan(spec):
    """-> {register_name: camera_dict} for the eligible cards (render order applied)."""
    regs = spec["registers"]
    rs = spec.get("render_start")
    names = [r.get("name") for r in regs]
    order = regs[names.index(rs):] + regs[:names.index(rs)] if rs in names else regs
    out = {}
    depth_left, roll_left = DEPTH_BUDGET, ROLL_BUDGET
    have_spiral = have_orbit = False
    sign = 1 if zlib.crc32(spec.get("name", "").encode()) & 1 else -1
    prev_kind = None
    for k, reg in enumerate(order):
        kind = reg.get("kind")
        eligible = (k > 0 and kind != "seam" and prev_kind != "seam"
                    and not reg.get("cameo") and not reg.get("camera"))
        prev_kind = kind
        if not eligible:
            continue
        has_target = bool(reg.get("target_phrase") or reg.get("target"))
        if has_target and depth_left and not have_spiral:
            out[reg["name"]] = {"move": "spiral", "rate": SPIRAL_RATE}
            have_spiral = True
            depth_left -= 1
        elif not has_target and depth_left and not have_orbit:
            out[reg["name"]] = {"move": "orbit", "rate": ORBIT_RATE}
            have_orbit = True
            depth_left -= 1
        elif roll_left:
            out[reg["name"]] = {"move": "roll", "rate": sign * ROLL_RATE}
            sign = -sign
            roll_left -= 1
    return out


def main():
    write = "--write" in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not names:
        sys.exit(__doc__)
    for name in names:
        p = pl.journey_path(name)
        if not p:
            print(f"{name}: NO journey file")
            continue
        spec = json.loads(p.read_text(encoding="utf-8"))
        assigned = plan(spec)
        print(f"\n=== {name} ===")
        if not assigned:
            print("  (no eligible cards — every card is start/seam/post-seam/cameo "
                  "or already has a camera plan)")
            continue
        for reg in spec["registers"]:
            c = assigned.get(reg["name"]) or reg.get("camera")
            tag = f"{c['move']} {c['rate']:g}" if isinstance(c, dict) else (c or "-")
            print(f"  {reg['name']:24s} {tag}")
        # apply + validate BEFORE any write; refuse to persist a plan that fails
        for reg in spec["registers"]:
            if reg["name"] in assigned:
                reg["camera"] = assigned[reg["name"]]
        probs = _camera.validate(spec)
        if probs:
            print("  !! validation: " + " | ".join(probs) + " — NOT writing")
            continue
        if write:
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
            tmp.replace(p)
            print(f"  wrote camera plan to {p.relative_to(ROOT)}")
        else:
            print("  (dry run — pass --write to persist)")


if __name__ == "__main__":
    main()
