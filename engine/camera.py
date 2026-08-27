#!/usr/bin/env python3
"""ENGINE 3 Phase D — the per-card CAMERA VOCABULARY (built 2026-08-27, PLAN "Phase D").

A journey register may carry a `camera` field; this module compiles those into a
per-frame schedule dive.py consumes, and validates plans against the iron law.
The COMPOSER stays blind to camera — plans are written by scripts/cinematographer.py
(rule-based v1) or by hand in a lab spec. No camera field = today's engine exactly.

Schema (per register):
    "camera": "spiral"                          # shorthand, default rate
    "camera": {"move": "spiral", "rate": 0.4}   # full form

MOVES (v1 — each proven mechanism only):
  roll     rate = extra deg/frame on top of format's rotate_per_frame (signed).
           Exact for tracker + cameo (track.propagate handles rotation), no depth needed.
  spiral   rate = orbit deg/frame at envelope peak. Revolution about the TRACKED object
           when the card's tracker is locked (pivot rides the aim; the object holds, the
           world sweeps past), else about the median plane at frame center. THE dive
           composite: circling while the ×10 zoom keeps running (iron law intact).
  orbit    same mechanism, always center/median pivot — for field cards with no target.
  vertigo  rate = dolly v/frame: near-field perspective stretch against the running zoom
           (median plane anchored). Rare spice.
  tilt     rate = pitch deg/frame: horizon rises/falls (reserved for the `landing` hero
           move; small values only in v1).

THE ENVELOPE (musical + loop-safe by construction): every move's rate is zero during the
card's arrival morph, smoothsteps up over one beat, holds, and smoothsteps back to zero
over the card's last beat. Rates are zero at every card boundary, so motion is continuous
across cards, seams stay clean, and the loop closes without a validator having to sum
angles — the lap card copies card 0, which the rules keep camera-free.

Iron-law caps (validated mechanisms only — see PLAN "ENGINE 3"):
  spiral/orbit <= 0.5 deg/frame  (orbit-v3 gate: 15 deg held crisp at this class of step)
  roll         <= 0.6 deg/frame  (engine's own 0.15 is proven; 4x is the ceiling)
  vertigo      <= 0.015 /frame
  tilt         <= 0.5 deg/frame
Depth moves (spiral/orbit/vertigo/tilt) need parallax_gain > 0 (they ride the same fused
residual warp + depth field as DEPTH 2.0); roll works regardless.
"""
import math

import grammar

CAPS = {"roll": 0.6, "spiral": 0.5, "orbit": 0.5, "vertigo": 0.015, "tilt": 0.5}
DEFAULT_RATE = {"roll": 0.35, "spiral": 0.35, "orbit": 0.30, "vertigo": 0.008,
                "tilt": 0.25}
DEPTH_MOVES = {"spiral", "orbit", "vertigo", "tilt"}


def _parse(reg):
    """The register's camera plan -> {'move', 'rate'} or None. Raises ValueError on junk."""
    c = reg.get("camera")
    if not c:
        return None
    if isinstance(c, str):
        c = {"move": c}
    if not isinstance(c, dict):
        raise ValueError(f"camera must be a string or object, got {type(c).__name__}")
    move = c.get("move")
    if move in (None, "none", "drift"):
        return None
    if move not in CAPS:
        raise ValueError(f"unknown camera move {move!r} (know: {sorted(CAPS)})")
    rate = float(c.get("rate", DEFAULT_RATE[move]))
    if abs(rate) > CAPS[move]:
        raise ValueError(f"{move} rate {rate} over the cap {CAPS[move]}")
    return {"move": move, "rate": rate}


def _render_order(spec):
    """Registers rotated to render_start — the same rotation grammar/dive use."""
    regs = spec["registers"]
    rs = spec.get("render_start")
    names = [r.get("name") for r in regs]
    if rs in names:
        k = names.index(rs)
        regs = regs[k:] + regs[:k]
    return regs


def validate(spec):
    """-> list of problem strings (empty = ok). The iron-law / proven-mechanism checks:
    caps, no camera on the render-start card (it is the establish frame AND the loop
    lap/tail card), none on seam cards (they dwell then morph), depth moves kept off
    cameo cards (sprite paste propagation is exact only for zoom+roll)."""
    probs = []
    order = _render_order(spec)
    for k, reg in enumerate(order):
        name = reg.get("name", f"card{k}")
        try:
            plan = _parse(reg)
        except ValueError as e:
            probs.append(f"{name}: {e}")
            continue
        if not plan:
            continue
        if k == 0:
            probs.append(f"{name}: camera on the RENDER-START card — it is the establish "
                         f"frame and the loop lap/tail re-renders it; keep it camera-free")
        if reg.get("kind") == "seam":
            probs.append(f"{name}: camera on a SEAM card — seams dwell then morph; "
                         f"no moves there")
        if reg.get("cameo") and plan["move"] in DEPTH_MOVES:
            probs.append(f"{name}: depth move {plan['move']!r} on a CAMEO card — the "
                         f"sprite's propagation is exact only for zoom+roll; use roll "
                         f"or nothing")
    return probs


def schedule(spec, fps):
    """Per-frame camera schedule for the FULL compiled render (lap included):
    a list of {'move', 'roll'|'orbit'|'dolly'|'tilt': per-frame amount, 'pivot'} or None
    per frame. Envelope: 0 across the arrival, one-beat smoothstep up, hold, one-beat
    smoothstep down to 0 at card end. The lap card copies card 0's plan (the rules keep
    card 0 camera-free, so lap + tail stay clean)."""
    fmt = spec.get("format", {})
    fpb = fmt.get("frames_per_beat", 7)
    order = _render_order(spec)
    cfr = [grammar._frames(r, fmt, fps) for r in order]
    lap = fmt.get("exact_loop") and fmt.get("loop_lap", True)
    if lap:
        # mirror grammar's lap: card 0 again + card 1's arrival replay (fa frames)
        order = order + [order[0]]
        cfr = cfr + [cfr[0]]
        lap_fa = max(2, round(cfr[1 % len(cfr)] * 0.25))
    out = []
    for k, (reg, F) in enumerate(zip(order, cfr)):
        try:
            plan = _parse(reg)
        except ValueError:
            plan = None                               # validate() reports; render ignores
        # HARD exclusions enforced here too (not just in validate): the render-start card
        # (k==0), the lap card (a copy of it), seam cards, and depth moves on cameo cards
        # must never move even if a spec slips past validation.
        if plan and (k == 0 or (lap and k == len(order) - 1)
                     or reg.get("kind") == "seam"
                     or (reg.get("cameo") and plan["move"] in DEPTH_MOVES)):
            plan = None
        fa = 0 if k == 0 else max(2, round(F * 0.25))
        ramp = min(fpb, max(1, (F - fa) // 3))
        for j in range(F):
            if not plan:
                out.append(None)
                continue
            if j < fa:
                env = 0.0
            elif j < fa + ramp:
                t = (j - fa + 1) / ramp
                env = t * t * (3 - 2 * t)
            elif j >= F - ramp:
                t = (F - j) / ramp
                env = t * t * (3 - 2 * t)
            else:
                env = 1.0
            if env <= 0.0:
                out.append(None)
                continue
            move, rate = plan["move"], plan["rate"] * env
            if move == "roll":
                fr = {"move": move, "roll": rate}
            elif move in ("spiral", "orbit"):
                fr = {"move": move, "orbit": rate,
                      "pivot": "target" if move == "spiral" else "center"}
            elif move == "vertigo":
                fr = {"move": move, "dolly": rate}
            else:                                     # tilt
                fr = {"move": move, "tilt": rate}
            out.append(fr)
    if lap:
        out += [None] * lap_fa                        # card 1's arrival replay: no camera
    return out


def plan_summary(spec):
    """One line per card with a camera plan (for run.json + logs)."""
    lines = []
    for reg in _render_order(spec):
        try:
            plan = _parse(reg)
        except ValueError as e:
            lines.append(f"{reg.get('name')}: INVALID ({e})")
            continue
        if plan:
            lines.append(f"{reg.get('name')}: {plan['move']} {plan['rate']:g}")
    return lines
