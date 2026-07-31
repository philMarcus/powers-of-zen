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

# ---- build-in (engine 2.0) templates ----------------------------------------
# THE object is EMERGING and GROWING — never "tiny / barely visible / far away" (that told the
# model to send it away; see journey-composer SKILL + PLAN "chicken-and-egg"). `target` text
# already carries the growing language, so we just place it.
T_ARRIVE = "{scene}, coming into full clear view up close, {style}"
T_TRAVEL = "moving through {scene}, {target}, {style}"
T_PLUNGE = ("diving straight into {target} as it swells to fill the entire view, the surrounding "
            "{scene} rushing past the edges of the frame, {style}")
T_FINAL = "deep inside {scene}, endless intricate detail in every direction, {style}"
# arrival right AFTER a seam: the whole view transforms into the new world (the on-beat morph)
T_MORPH = "the whole view transforming, resolving into {scene}, {style}"

SEAM_EXP_JUMP = 8.0   # |Δexp| this big to the next card = a semantic SEAM (instant morph, no zoom)

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


def _scene(reg):
    return reg.get("scene") or reg.get("interior") or ""


def _target(reg):
    return reg.get("target") or reg.get("next_target") or ""


def _frames(reg, fmt, fps):
    """Frame count for a card. New schema: `dur` in BEATS × frames_per_beat. Legacy: `sec`."""
    if reg.get("dur") is not None:
        # dur is in BEATS (a bar = 4). ~7 frames/beat -> a 1-bar scale = 28 frames = ~2.3s at 12fps
        # (matching the old ~2.4s/register), a 2-bar linger = 56. Keeps the video a sane length.
        # Floor = ONE BEAT (not 8): the old max(8,...) bumped a dur-1 seam card to 8 frames,
        # pushing every later morph 1 frame off the bar grid (found via sugar_nebula, 225≠224).
        fpb = fmt.get("frames_per_beat", 7)
        return max(fpb, round(reg["dur"] * fpb))
    sec = fmt.get("sec_per_scale", fmt.get("sec_per_decade", 2.4))
    return max(12, round(reg.get("sec", sec) * fps))


def compile_journey(spec, fps, build="in"):
    fmt = spec.get("format", {})
    travel_denoise = fmt.get("travel_denoise", 0.55 if build == "out" else 0.40)
    # (fmt.seam_denoise is read by dive.py as the seam-morph PEAK — no longer a schedule base)
    style = spec.get("style_suffix", "")
    regs = spec["registers"]

    phases, zoom, denoise, exponent, cameos = [], [], [], [], []
    approach = []          # per-frame: {phrase, pick} on object-approach beats, else None
    arrivals = set()
    seam_arrivals = set()  # arrival phases that follow a SEAM card: dive renders the on-beat morph there
    prev_exp = regs[0]["exp"]
    prev_kind = "zoom"
    for k, reg in enumerate(regs):
        nxt = regs[k + 1] if k + 1 < len(regs) else regs[0]   # loop back
        last = (k == len(regs) - 1)
        scene = _scene(reg)
        F = _frames(reg, fmt, fps)
        reg_start = len(zoom)

        # transition FROM this card: explicit `kind`, else auto-SEAM on a big exp jump to the next.
        kind = reg.get("kind")
        if kind is None:
            kind = "seam" if (not last and abs(nxt["exp"] - reg["exp"]) >= SEAM_EXP_JUMP) else "zoom"

        if build == "out":
            fa = round(F * 0.30) if k > 0 else 0
            if fa:
                arrivals.add(len(phases))
                phases.append({"prompt": _p(TEMPLATE_EMERGE.format(
                    afar=regs[k - 1]["afar"], interior=scene, style=style), reg), "frames": fa})
            if last and reg.get("loop_hint"):
                fr = round((F - fa) * 0.45)
                phases.append({"prompt": _p(TEMPLATE_RECEDE.format(interior=scene, style=style), reg), "frames": fr})
                phases.append({"prompt": _p(TEMPLATE_LOOPHINT.format(
                    interior=scene, loop_hint=reg["loop_hint"], style=style), reg), "frames": F - fa - fr})
            else:
                phases.append({"prompt": _p(TEMPLATE_RECEDE.format(interior=scene, style=style), reg), "frames": F - fa})
            card_zoom, card_appr, kind = 10.0, [None] * F, "zoom"
        else:
            # BUILD-IN (engine 2.0). The arrival beat is the on-beat MORPH into this scene, blending
            # from the previous scene (that blend IS the morph — strongest right after a SEAM, where
            # the previous scene's own text already says it's becoming this one). Skip only on card 0.
            fa = 0 if k == 0 else max(2, round(F * 0.25))
            if fa:
                arrivals.add(len(phases))
                if prev_kind == "seam":
                    seam_arrivals.add(len(phases))
                tmpl = T_MORPH if prev_kind == "seam" else T_ARRIVE
                phases.append({"prompt": _p(tmpl.format(scene=scene, style=style), reg), "frames": fa})
            body = F - fa
            if last:
                # loop home: plunge toward card-0's world (dive.py's loop tail morphs to frame 0). No
                # targeting here — the loop mechanism owns the tail.
                tgt = regs[0].get("loop_target") or _scene(regs[0])
                ft = max(1, round(body * 0.45))
                phases.append({"prompt": _p(T_TRAVEL.format(scene=scene, target=tgt, style=style), reg), "frames": ft})
                phases.append({"prompt": _p(T_PLUNGE.format(target=tgt, scene=scene, style=style), reg), "frames": body - ft})
                card_zoom, card_appr = 10.0, [None] * F
            elif kind == "seam":
                # SEAM: dwell in this scene; the MORPH is the next card's arrival beat (big prompt
                # jump + denoise boost). NO TARGETING (nothing to aim at) — but the DIVE NEVER
                # STOPS. This card zooms at the SAME rate as every other card: the old x1.4 was
                # a near-freeze (1.006-1.019/frame vs 1.039-1.135), and the uniform-bar retime
                # made it twice as slow and twice as long — a 2.3s stall right before the most
                # dramatic moment (Phil spotted it in the v9 frames). "Don't target" was correct;
                # "don't zoom" never was.
                phases.append({"prompt": _p(T_FINAL.format(scene=scene, style=style), reg), "frames": body})
                card_zoom, card_appr = 10.0, [None] * F
            else:
                # ZOOM: emerging targeted approach INTO the contained object.
                target = _target(reg)
                tp, pick = reg.get("target_phrase"), reg.get("target_pick", "salient")
                ft = max(1, round(body * 0.45))
                phases.append({"prompt": _p(T_TRAVEL.format(scene=scene, target=target, style=style), reg), "frames": ft})
                phases.append({"prompt": _p(T_PLUNGE.format(target=target, scene=scene, style=style), reg), "frames": body - ft})
                card_zoom = 10.0
                ap = {"phrase": tp, "pick": pick} if tp else None
                card_appr = [None] * fa + [ap] * body

        # arrive->look->plunge zoom curve; per-card PRODUCT = card_zoom (x10 zoom, ~x1.4 seam).
        # This is the EXACT engine-1 curve (Phil 2026-07-31: "engine one had the right idea —
        # we had a great curve"). The v7 "uneven within each scale" feel came from MIXED card
        # durations varying the curve's period/amplitude card-to-card, not from the curve —
        # fixed by the uniform-bars-per-scale rule (every card same dur -> same curve every
        # card, one consistent breathing period). The interim zoom-floor experiment is retired.
        w = [0.30 + 0.70 * math.sin(math.pi * (j + 0.5) / F) ** 2 for j in range(F)]
        s = sum(w) or 1.0
        zs = [math.exp(math.log(card_zoom) * wj / s) for wj in w]
        zoom += zs
        # denoise: EVERY card travels at travel_denoise — seam cards too. The old schedule ran
        # the whole seam card at seam_denoise 0.72 (+0.18 arrival boost = 0.85 capped): ~15%
        # frame survival for 14 straight frames = unrelated worlds on consecutive frames (hard
        # cuts, Phil 2026-07-31). The seam's world-flip is an ON-BEAT MORPH, rendered by dive.py
        # at the NEXT card's arrival (seam_arrivals below): peak denoise on the downbeat frame,
        # ramping out across the prompt crossfade — engine-1's dissolve character, seam-strength.
        denoise += [travel_denoise] * F
        approach += card_appr

        # counter exponent — descend with the actual visual zoom; arrival spins toward this card's exp
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
            cameos.append({"start": reg_start + fa, "end": reg_start + F, **reg["cameo"]})
        prev_kind = "zoom" if last else kind

    loop = None
    if fmt.get("exact_loop") and build != "out":
        F_last = _frames(regs[-1], fmt, fps)
        L = min(round(2.0 * fps), F_last - 2)
        # SEAM (2026-07-29): the last L frames KEEP diving at travel denoise (alive, not settling)
        # while dive.py morphs home — natural dive → palette-match → gap-scaled morph toward frame 0
        # (no hard copy). `morph_frames` = trailing frames that morph. The old denoise-ramp + s0
        # loop_composite tail is gone. See PLAN.md "THE SEAM".
        loop = {"frames": L, "morph_frames": min(12, L - 2)}
    return phases, zoom, denoise, exponent, loop, cameos, arrivals, approach, seam_arrivals
