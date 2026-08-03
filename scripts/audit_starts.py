#!/usr/bin/env python3
"""Audit render_start across every journey.

Frame 0 must be an ESTABLISHING SHOT: many things across a field of view, not one subject the
camera is aimed at (it is both the only txt2img frame and the loop-home target). This is
independent of scale — `exp` is the size of the object, not the width of the shot — so nothing
here reads exp. Also flags a missing start and a seam rotated to either end, and notes when the
start is not a cosmic/subatomic realm (those establish and re-blend most forgivingly).

    python3 scripts/audit_starts.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402  (cameo_realm_check)

# A scene built around ONE subject. These phrasings are decisive: even when the sentence goes on
# to mention neighbours, the frame is still a portrait of the named thing.
SINGLE = re.compile(
    r"(\ba single\b|\ba lone\b|\bone arm\b|\bthe inside of\b|\bthe surface of\b|"
    r"\bthe face of\b|\bthe head of\b|\bthe tip of\b|\bthe corona of\b|\bthe curved wall of\b|"
    r"\ba curled length of\b|\bup close\b|\bat full width\b)", re.I)

# Evidence the frame holds a spread of things / a place rather than a subject.
FIELD = re.compile(
    r"(\bfield of\b|\branks of\b|\brows of\b|\bbanks of\b|\bwebs? of\b|\bgrid of\b|\btiling of\b|"
    r"\bswarm of\b|\bcluster of\b|\bthousands\b|\bcountless\b|\bmany\b|\bdozens\b|\bpacked\b|"
    r"\bstrewn\b|\bscattered\b|\bin every direction\b|\bacross the\b|\bfrom high above\b|"
    r"\bseen wide\b|\bseen from across\b|\bat standing height\b|\bat eye level\b|\bfrom above\b|"
    r"\bspread through\b|\bthrough the void\b|\bcountry\b|\bsheets of\b|\bsets of\b|"
    r"\beither side\b|\bplains?\b|\bterraces\b|\bnodes\b|\bfrom straight above\b)", re.I)

# Realms that establish cleanly from nothing and blend forgivingly on the return.
FAR = re.compile(r"(\bnebula\b|\bgalax|\bcosmos\b|\bcosmic\b|\bstars?\b|\bstarlight\b|\bvoid\b|"
                 r"\bquantum\b|\batoms?\b|\bmolecul|\blattice\b|\bparticle\b|\bplasma\b|"
                 r"\bsubatomic\b|\bindigo dark\b|\bdeep space\b)", re.I)


def main():
    flagged = total = 0
    for p in sorted((Path(__file__).resolve().parent.parent / "journeys").glob("*.json")):
        spec = json.loads(p.read_text(encoding="utf-8"))
        regs = spec.get("registers") or []
        if not regs or "scene" not in regs[0]:
            continue                                   # legacy engine-1 schema
        total += 1
        names = [r["name"] for r in regs]
        start = spec.get("render_start")
        i = names.index(start) if start in names else 0
        rot = names[i:] + names[:i]
        seams = [r["name"] for r in regs if r.get("kind") == "seam"]
        scene = regs[i]["scene"]

        problems = []
        if not start:
            problems.append("NO render_start")
        if rot[0] in seams:
            problems.append("SEAM FIRST")
        if rot[-1] in seams:
            problems.append("SEAM LAST")
        # A lone subject only fails OUTSIDE space. Astronomical forms have no hard silhouette, so
        # a single nebula or galaxy morphs home as easily as a field does.
        hits = sorted(set(w.lower() for w in SINGLE.findall(scene)))
        if hits and not FAR.search(scene):
            problems.append("single hard-edged subject: " + ", ".join(hits[:2]))
        # the sprite must live in its realm — Amos does not visit beehives
        problems += pl.cameo_realm_check(spec)

        # Notes, not failures: these two are judgement calls a regex can only hint at. Requiring
        # field-of-view WORDS produced false alarms on scenes that are plainly wide but phrased
        # differently, and cosmic/subatomic is a preference the journey may legitimately lack.
        notes = []
        if not FAR.search(scene) and not FIELD.search(scene):
            notes.append("width unconfirmed — read it")   # space needs no width check
        if not FAR.search(scene):
            notes.append("not cosmic/subatomic")

        flagged += bool(problems)
        tail = "; ".join(problems) or ("· " + " · ".join(notes) if notes else "")
        print(f"{'!!' if problems else 'ok'} {p.stem:24} start={str(start):20}{tail}")
    print(f"\n{total} journeys · {flagged} need attention")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
