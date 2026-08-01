#!/usr/bin/env python3
"""Audit render_start across every journey.

A journey is OK when its rendered card 0 is an ABSTRACT/textural realm and the SEAM card
lands neither first nor last. Reports what each journey would actually render first.
"""
import json
import re
import sys
from pathlib import Path

# Words that mark a card as a LITERAL, human-scale, context-bearing place — the kind that
# frame 0 (the only txt2img frame) fills in with invented surroundings.
LITERAL = re.compile(
    r"\b(room|hall|studio|workshop|atelier|kitchen|shop|stall|street|corner|sidewalk|"
    r"terrace|desk|table|bench|park|garden|orchard|apiary|laboratory|lab|cellar|attic|"
    r"library|market|temple|house|cottage|hamlet|village|town|city|stairs|doorway|"
    r"window|shelf|floor|wall of the|living room|lecture)\b", re.I)

rows = []
for p in sorted(Path("journeys").glob("*.json")):
    spec = json.loads(p.read_text(encoding="utf-8"))
    regs = spec.get("registers") or []
    if not regs or "scene" not in regs[0]:
        rows.append((p.stem, "LEGACY", "-", "-", "-", ""))
        continue
    names = [r["name"] for r in regs]
    start = spec.get("render_start")
    i = names.index(start) if start in names else 0
    rot = names[i:] + names[:i]
    seams = [r["name"] for r in regs if r.get("kind") == "seam"]
    first_scene = regs[names.index(rot[0])]["scene"]
    lit = sorted(set(w.lower() for w in LITERAL.findall(first_scene)))
    problems = []
    if not start:
        problems.append("NO render_start")
    if set(seams) & {rot[0]}:
        problems.append("SEAM FIRST")
    if set(seams) & {rot[-1]}:
        problems.append("SEAM LAST")
    if lit:
        problems.append("literal:" + ",".join(lit[:3]))
    rows.append((p.stem, spec.get("style") or "-", start or "-", rot[0],
                 " ".join(seams), "; ".join(problems)))

bad = [r for r in rows if r[5] and r[1] != "LEGACY"]
for n, st, start, first, seams, prob in rows:
    if st == "LEGACY":
        continue
    tag = "!!" if prob else "ok"
    print(f"{tag} {n:24} start={start:16} renders first: {first:16} {prob}")
print(f"\nnew-schema journeys: {sum(1 for r in rows if r[1] != 'LEGACY')} | "
      f"needing attention: {len(bad)} | legacy skipped: {sum(1 for r in rows if r[1] == 'LEGACY')}")
