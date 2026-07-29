"""Grammar compiler: world-card journeys -> phases + per-frame schedules.

Two build modes:

BUILD-IN (classic): registers authored LARGE -> SMALL. Each frame crops the
center and re-diffuses; the model invents interior detail. Beats per register:
arrival / travel / plunge, targets named via `next_target`.

BUILD-OUT: registers authored SMALL -> LARGE. Each frame shrinks the whole
image toward the center and the model paints only the newly exposed border —
the environment. The current world is physically inherited (no double-object
ghosts). Cards use `afar` (how this world looks when small in the distance)
instead of `next_target`; the last card may carry `loop_hint` describing how
its world morphs toward the first card's world (circular seam).

Journeys are CIRCULAR either way: in build-in the last card's next_target names
the first world; in build-out the last card's loop_hint does.

Per-card keys (both modes): exp (may be float), interior, palette?, sec?,
cameo? {sprite, pos, size}. Build-in adds next_target; build-out adds afar
(and loop_hint on the last card).
"""
import math

# ---- build-in templates -----------------------------------------------------
TEMPLATE_ARRIVAL = ("{target} now filling the entire view up close, its surface "
                    "spreading open into {interior}, {style}")
TEMPLATE_TRAVEL = ("traveling through {interior}, vast {interior} in every direction, "
                   "one single tiny {target}, barely visible, alone very far away in "
                   "the distance ahead, {style}")
TEMPLATE_PLUNGE = ("plunging toward {target}, the only one, growing huge ahead, "
                   "walls of {interior} rushing past the edges of the frame, "
                   "{style}")
TEMPLATE_FINAL = ("deep inside {interior}, endless intricate glowing detail in every "
                  "direction, {style}")

# ---- build-out templates ----------------------------------------------------
TEMPLATE_EMERGE = ("{afar} shrinking away into the distance below, its surroundings "
                   "opening up into {interior}, {style}")
TEMPLATE_RECEDE = ("{interior}, stretching endlessly in every direction, "
                   "{style}")
TEMPLATE_LOOPHINT = ("{interior} in every direction, the whole scene slowly "
                     "becoming {loop_hint}, {style}")


def _p(text, reg):
    pal = reg.get("palette")
    return f"{text}, {pal} colors" if pal else text


def compile_journey(spec, fps, build="in"):
    fmt = spec.get("format", {})
    sec = fmt.get("sec_per_scale", fmt.get("sec_per_decade", 2.4))
    travel_denoise = fmt.get("travel_denoise", 0.55 if build == "out" else 0.40)
    style = spec.get("style_suffix", "")
    regs = spec["registers"]

    phases, zoom, denoise, exponent, cameos = [], [], [], [], []
    arrivals = set()
    prev_exp = regs[0]["exp"]
    for k, reg in enumerate(regs):
        nxt = regs[k + 1] if k + 1 < len(regs) else None
        F = max(12, round(reg.get("sec", sec) * fps))
        reg_start = len(zoom)

        if build == "out":
            fa = round(F * 0.30) if k > 0 else 0
            if fa:
                arrivals.add(len(phases))
                phases.append({"prompt": _p(TEMPLATE_EMERGE.format(
                    afar=regs[k - 1]["afar"], interior=reg["interior"],
                    style=style), reg), "frames": fa})
            if not nxt and reg.get("loop_hint"):
                fr = round((F - fa) * 0.45)
                phases.append({"prompt": _p(TEMPLATE_RECEDE.format(
                    interior=reg["interior"], style=style), reg), "frames": fr})
                phases.append({"prompt": _p(TEMPLATE_LOOPHINT.format(
                    interior=reg["interior"], loop_hint=reg["loop_hint"],
                    style=style), reg), "frames": F - fa - fr})
            else:
                phases.append({"prompt": _p(TEMPLATE_RECEDE.format(
                    interior=reg["interior"], style=style), reg),
                    "frames": F - fa})
        else:
            fa = round(F * 0.25) if k > 0 else 0
            if fa:
                arrivals.add(len(phases))
                phases.append({"prompt": _p(TEMPLATE_ARRIVAL.format(
                    target=regs[k - 1]["next_target"], interior=reg["interior"],
                    style=style), reg), "frames": fa})
            if reg.get("next_target"):
                # SELF-SIMILAR LOOP: the last register loops back to the FIRST world, so it must
                # plunge toward that world described EXACTLY as frame 0 shows it (same subject, same
                # framing) — otherwise first/last render as two different images and the loop seam
                # has a big gap to bridge. Derive the loop target from regs[0] (its `loop_target`
                # if given, else its `interior`) rather than a separately-authored next_target that
                # drifts. Non-last registers use their own next_target as before.
                target = reg["next_target"]
                if k == len(regs) - 1:
                    target = regs[0].get("loop_target") or regs[0]["interior"]
                ft = round(F * (0.35 if fa else 0.55))
                phases.append({"prompt": _p(TEMPLATE_TRAVEL.format(
                    interior=reg["interior"], target=target,
                    style=style), reg), "frames": ft})
                phases.append({"prompt": _p(TEMPLATE_PLUNGE.format(
                    interior=reg["interior"], target=target,
                    style=style), reg), "frames": F - fa - ft})
            else:
                phases.append({"prompt": _p(TEMPLATE_FINAL.format(
                    interior=reg["interior"], style=style), reg),
                    "frames": F - fa})

        # arrive -> look -> plunge zoom curve; per-register product is exactly x10
        w = [0.30 + 0.70 * math.sin(math.pi * (j + 0.5) / F) ** 2 for j in range(F)]
        s = sum(w)
        zs = [math.exp(math.log(10) * wj / s) for wj in w]
        zoom += zs
        denoise += [travel_denoise] * F

        # counter stays PINNED to this register's declared exp, descending with
        # the actual visual zoom; handoffs get a fast odometer spin during the
        # arrival beat — honest about skipped scales, including wraps
        cum = 0.0
        for j in range(F):
            if fa and j < fa:
                t = (j + 0.5) / fa
                exponent.append(prev_exp + (reg["exp"] - prev_exp) * t)
            else:
                cum += math.log10(zs[j])
                exponent.append(reg["exp"] - cum)
        prev_exp = exponent[-1]

        if reg.get("cameo"):
            cameos.append({"start": reg_start + fa, "end": reg_start + F,
                           **reg["cameo"]})

    loop = None
    if fmt.get("exact_loop") and build != "out":
        F_last = max(12, round(regs[-1].get("sec", sec) * fps))
        L = min(round(2.0 * fps), F_last - 2)
        total = len(zoom)
        # seam: over the last L frames ramp denoise DOWN so the tail stops repainting and
        # settles onto frame 0's structure (which the last frame is hard-copied to). Lower
        # target (0.12) = harder convergence = softer loop cut. Pairs with authoring the
        # last register's next_target to name the FIRST world so the tail morphs into it.
        for j in range(L):
            t = (j + 1) / L
            denoise[total - L + j] = travel_denoise + (0.12 - travel_denoise) * t
        loop = {"frames": L, "s0": 0.10}
    return phases, zoom, denoise, exponent, loop, cameos, arrivals
