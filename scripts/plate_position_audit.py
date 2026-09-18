#!/usr/bin/env python3
"""PLANET-CARD POSITION AUDIT (2026-09-17, Phil: "make sure the planet card is in such a position
that it's not screwed up by being too close to the beginning").

The PLANET PLATE (engine/plate.py) spans the planet card AND the next card. It cannot act when the
planet card is the render_start card (its delivered copy is the loop LAP, which the loop tail owns
— PLAN "PLANET DESCENT", finding 4) or the LAST card (its successor is the lap, inside the tail).
27 of 53 planet cards sat at render_start. This audit picks a new `render_start` for those
journeys so that ALL of these hold at once — nothing already settled is undone:

  * the planet card (plate.is_plate_card) lands at render-order index 1 .. n-2;
  * the seam card is neither first nor last (audit_starts' SEAM FIRST / SEAM LAST);
  * the new frame-0 card passes audit_starts' start test (no single hard-edged subject outside
    space), and cosmic/subatomic realms are preferred over everything else (the doctrine's
    outer space > subatomic > everyday), field-of-view wording next;
  * a journey whose current start already satisfies all of this is left alone.

Only journeys with NO live/production video are touched (a rendered video keeps its start; the
new start applies to future renders). Dry run by default; --apply rewrites `render_start` in place
(utf-8, atomic) and reports. Verify afterwards with scripts/audit_starts.py + preflight.

    python3 scripts/plate_position_audit.py            # report
    python3 scripts/plate_position_audit.py --apply    # rewrite render_start where needed
    python3 scripts/plate_position_audit.py --only cork_dehesa prairie_town
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "engine"))
import pipeline as pl  # noqa: E402
import plate  # noqa: E402
from audit_starts import SINGLE, FIELD, FAR  # noqa: E402

UNTOUCHABLE = {"live", "queued", "music", "production", "posting", "posted"}   # video states
MIN_SCORE = 2.0      # rotate only onto a cosmic/subatomic start (FAR realm); see below


def plate_cards(regs):
    n = len(regs)
    return [i for i, r in enumerate(regs) if plate.is_plate_card(r, regs[(i + 1) % n])]


def evaluate(regs, k):
    """Score the rotation starting at card k; None = violates a hard rule."""
    n = len(regs)
    rot = regs[k:] + regs[:k]
    seams = [i for i, r in enumerate(rot) if r.get("kind") == "seam"]
    if 0 in seams or (n - 1) in seams:
        return None, "seam at an end"
    pcs = plate_cards(rot)
    if any(p == 0 or p >= n - 1 for p in pcs):
        return None, "planet card at an end"
    scene = rot[0].get("scene") or ""
    exp0 = rot[0].get("exp")
    # FAR = the wording says so OR the card's exponent does: the engine itself treats
    # exp >= 6.5 / <= -6 as far from human scale (grammar SPACE_EXP_HI/LO -> the spaceless
    # establish + landscape negatives), whatever words the composer used (2026-09-18:
    # vernal_clutch's nucleosome card is molecular by exp but names no FAR-regex word).
    far = bool(FAR.search(scene)) or (isinstance(exp0, (int, float))
                                      and (exp0 >= 6.5 or exp0 <= -6.0))
    single = SINGLE.findall(scene)
    if single and not far:
        return None, "single hard-edged subject: " + single[0]
    score = 0.0
    if far:
        score += 2.0
    if FIELD.search(scene):
        score += 1.0
    exp = rot[0].get("exp")
    if isinstance(exp, (int, float)):
        if exp >= 6.5:
            score += 0.6          # outer space first
        elif exp <= -6.0:
            score += 0.3          # subatomic second
    # never start ON a planet-class card (the plate's frame-0 path is untested) — covered by the
    # planet-at-an-end rule; and prefer not to start on the card right after the seam? no: that
    # is the classic cosmic start (e.g. cobalt's globular_cluster) — allowed.
    return score, "ok"


def main():
    apply = "--apply" in sys.argv
    only = set()
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1:])
    pdata = pl.load()
    jd = pl.jload()
    rows = []
    for p in sorted((ROOT / "journeys").glob("*.json")):
        name = p.stem
        if only and name not in only:
            continue
        spec = json.loads(p.read_text(encoding="utf-8"))
        regs = spec.get("registers") or []
        if not regs or "scene" not in regs[0]:
            continue
        n = len(regs)
        if not plate_cards(regs):
            continue
        names = [r["name"] for r in regs]
        cur = spec.get("render_start")
        k0 = names.index(cur) if cur in names else 0
        cur_score, cur_why = evaluate(regs, k0)
        video = pl.get(pdata, name)
        vstate = video.get("state") if video else None
        touchable = vstate not in UNTOUCHABLE
        if cur_score is not None:
            rows.append((name, cur, cur, "keeps", vstate, f"{cur_score:.1f} {cur_why}"))
            continue
        best = None
        for k in range(n):
            sc, why = evaluate(regs, k)
            if sc is None:
                continue
            if best is None or sc > best[0]:
                best = (sc, k, why)
        if best is None:
            rows.append((name, cur, None, "NO VALID START", vstate, cur_why))
            continue
        new = names[best[1]]
        if best[0] < MIN_SCORE:
            # the only legal starts left are everyday wide shots — rotating would trade a
            # cosmic/subatomic start for a postcard-prone one (Phil: never undo the start
            # doctrine). Leave the start alone; this journey needs AUTHORING (a cosmic or
            # subatomic card that can start, or the planet card moved) before the plate
            # can act on it.
            rows.append((name, cur, new, "NEEDS AUTHORING (best start is everyday)", vstate,
                         f"{best[0]:.1f} (was: {cur_why})"))
            continue
        action = "rotate" if touchable else "would rotate (video " + str(vstate) + ")"
        rows.append((name, cur, new, action, vstate, f"{best[0]:.1f} (was: {cur_why})"))
        if apply and touchable:
            # the video must still OPEN where the composer put it: remember the old start as
            # play_start — dive's assembly rotates the delivered loop back to it (2026-09-18,
            # Phil: the scale must decrease monotonically and then loop back to the biggest)
            spec.setdefault("play_start", cur or names[0])
            spec["render_start"] = new
            txt = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".tmp_", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(txt)
            os.replace(tmp, p)
    w = max(len(r[0]) for r in rows) if rows else 10
    print(f"{'journey':{w}s}  {'current start':22s} {'new start':22s} {'action':28s} video   score/why")
    for r in rows:
        print(f"{r[0]:{w}s}  {str(r[1]):22s} {str(r[2]):22s} {r[3]:28s} {str(r[4]):7s} {r[5]}")
    n_rot = sum(1 for r in rows if r[3] == "rotate")
    print(f"\n{len(rows)} journeys with a planet-class card; {n_rot} to rotate"
          + (" — APPLIED" if apply else " (dry run; --apply to write)"))


if __name__ == "__main__":
    main()
