#!/usr/bin/env python3
"""Lone-figure detection — the guard that stops us rendering an hour of the wrong video.

WHY THIS EXISTS (2026-07-31, quantum_orrery v1)
-----------------------------------------------
Frame 0 is the ONLY txt2img frame in a dive. Every other frame is img2img at denoise ~0.5
anchored on its predecessor, so the checkpoint's own prior gets full authority exactly once
— and whatever it puts there is then carried through the entire video by the feedback chain.
One bad frame = one wasted hour.

quantum_orrery's frame-0 prompt was

    "three glowing quark cores bound close inside one luminous shell, gold-white lobes ...
     a crimson halo around the trio ... warm gilded light ... storybook grandeur ...
     jewel-bright accents"

and DreamShaper XL — a FANTASY-CHARACTER-ART fine-tune — rendered a haloed goddess. It was
not ignoring the prompt: "quark core" has no visual referent, and halo + gilded + jewel-bright
+ storybook grandeur is a dense region of its training set. The global negative at the time
("human face, portrait, close-up person") targeted CLOSE-UPS and did nothing about a
full-body standing figure.

Doctrine (journey-composer SKILL): distant anonymous crowds / tiny figures AT SCALE are fine
texture; a featured individual is not. So this gates on SIZE, not mere presence.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Two phrasings, not one: Florence's two tasks catch different cases, and "person" alone
# misses stylized/painted figures that "a woman" finds (most SDXL character drift is female).
QUERIES = ("person", "a woman")

# Fraction of the frame a figure must occupy to count. Tiny background figures are ALLOWED
# by doctrine; the quantum_orrery goddess covered most of the frame.
MIN_AREA = 0.05


def find(pil, queries=QUERIES, min_area=MIN_AREA, model=None):
    """Largest human figure in this frame as (query, box), or None.

    `box` is detect.locate's fractional dict (cx, cy, w, h, area). Never raises — a detector
    failure must not kill a render, so it reports "no figure" and lets the render continue.
    """
    import detect          # lazy: detect imports dive, which imports this module (same
                           # circular-import dance track.py does). By call time dive is loaded.
    best = None
    for q in queries:
        try:
            b = detect.locate(pil, q, model=model) if model else detect.locate(pil, q)
        except Exception:
            continue
        if b and b["area"] >= min_area and (best is None or b["area"] > best[1]["area"]):
            best = (q, b)
    return best


def describe(hit):
    q, b = hit
    return (f"{q} @ ({b['cx']:.2f},{b['cy']:.2f}) "
            f"{b['w']:.2f}x{b['h']:.2f} = {b['area'] * 100:.0f}% of frame")
