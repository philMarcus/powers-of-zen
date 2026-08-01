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
+ storybook grandeur is a dense region of its training set.

HOW IT DETECTS (the first attempt was wrong — measure before trusting a detector)
--------------------------------------------------------------------------------
First attempt asked detect.locate("person") and gated on box SIZE. That FAILED validation:
of five figure-free frame-0s, three "found" a person at 43-78% of frame, and the real goddess
(84%) was indistinguishable from them by size. Cause: locate() uses grounding/segmentation,
which are "point at X" tasks — ask for something absent and Florence returns a near-full-width
blob. detect.py's FULLSPAN filter only drops boxes >=0.9 in BOTH dims, and these were ~1.00
wide by 0.72-0.89 tall.

Presence/absence needs a "describe what's here" task. detect.caption() returns Florence's own
description, and on the same six frames it separated them perfectly — the goddess captioned as
"A woman with long red hair is standing ... a golden crown on her head", while the clean frames
captioned as vases, stars, shiny balls, moss and lanterns.

This also matches the doctrine better than an area threshold did: a caption names what the
image is ABOUT, so a featured individual gets named while the distant anonymous figures that
the journey-composer SKILL explicitly allows as texture do not.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Deliberately tight. Every word here aborts a render, so a false trigger is expensive:
#  - no "knight"/"statue"/"model": chess_empires has knight PIECES, jade_automata carved panels
#  - no bare "figure": chess pieces and figurines get called figures
#  - no "face": captions say "the face of the cliff"
# Word boundaries matter: "man" must not fire on "many balls on the table" (lather_atlas).
PERSON = re.compile(
    r"\b(person|persons|people|man|men|woman|women|girl|girls|boy|boys|child|children|"
    r"human|humans|lady|ladies|guy|guys|someone|somebody|goddess|angel|angels|"
    r"warrior|priestess|monk|nun)\b", re.I)


def find(pil, model=None, **_ignored):
    """The figure words in this frame's caption, or None.

    Returns (matched_words, caption). Never raises — a detector failure must not kill a
    render, so it reports "no figure" and lets the render continue.
    """
    import detect          # lazy: detect imports dive, which imports this module (same
                           # circular-import dance track.py does). By call time dive is loaded.
    try:
        if model:
            detect.MODEL = model
        cap = detect.caption(pil)
    except Exception:
        return None
    if not cap:
        return None
    hits = sorted({w.lower() for w in PERSON.findall(cap)})
    return (hits, cap.strip()) if hits else None


def describe(hit):
    words, cap = hit
    return f"{'/'.join(words)} — Florence: \"{cap[:150]}\""
