"""Grammar compiler: world-card journeys -> phases + per-frame schedules.

A register card (dive-in order, LARGE -> SMALL):
    {"name": "city", "exp": 3,
     "interior": "an impossible city of luminous towers seen from above",
     "next_target": "a strange glowing creature resting in a plaza"}

Each register becomes two beats compiled through fixed templates:
    A (travel):  vast interior everywhere, next target tiny at the very center
    B (plunge):  next target growing huge at center, interior rushing past
The final register has no next_target; it hosts the exact-loop tail instead.

Per-frame schedules:
    zoom   — arrive->look->plunge curve; each register's product is exactly x10
    denoise — travel value; ramps down over the loop tail so frame 0 survives
    exponent — semantic 10^n m counter value, interpolated between register exps
"""
import math

TEMPLATE_ARRIVAL = ("{target} now filling the entire view up close, its surface "
                    "spreading open into {interior}, {style}")
TEMPLATE_TRAVEL = ("traveling through {interior}, vast {interior} in every direction, "
                   "one single tiny glowing {target}, alone, very far away in the "
                   "distance ahead, {style}")
TEMPLATE_PLUNGE = ("plunging toward a single {target}, the only {target}, growing "
                   "huge ahead, walls of {interior} rushing past the edges of the "
                   "frame, {style}")
TEMPLATE_FINAL = ("deep inside {interior}, endless intricate glowing detail in every "
                  "direction, {style}")


def _p(text, reg):
    pal = reg.get("palette")
    return f"{text}, {pal} colors" if pal else text


def compile_journey(spec, fps, travel_denoise=0.40):
    fmt = spec.get("format", {})
    sec = fmt.get("sec_per_scale", fmt.get("sec_per_decade", 2.4))
    travel_denoise = fmt.get("travel_denoise", travel_denoise)
    style = spec.get("style_suffix", "")
    regs = spec["registers"]
    F = max(12, round(sec * fps))

    phases, zoom, denoise, exponent, cameos = [], [], [], [], []
    for k, reg in enumerate(regs):
        nxt = regs[k + 1] if k + 1 < len(regs) else None
        reg_start = len(zoom)
        # arrival beat: the target we just plunged toward, verbatim, becoming this
        # world — same object at two sizes is what sells the scale handoff
        fa = round(F * 0.25) if k > 0 else 0
        if fa:
            phases.append({"prompt": _p(TEMPLATE_ARRIVAL.format(
                target=regs[k - 1]["next_target"], interior=reg["interior"],
                style=style), reg), "frames": fa})
        if nxt:
            ft = round(F * (0.35 if fa else 0.55))
            phases.append({"prompt": _p(TEMPLATE_TRAVEL.format(
                interior=reg["interior"], target=reg["next_target"], style=style),
                reg), "frames": ft})
            phases.append({"prompt": _p(TEMPLATE_PLUNGE.format(
                interior=reg["interior"], target=reg["next_target"], style=style),
                reg), "frames": F - fa - ft})
        else:
            phases.append({"prompt": _p(TEMPLATE_FINAL.format(
                interior=reg["interior"], style=style), reg), "frames": F - fa})

        # arrive -> look -> plunge zoom curve; per-register product is exactly x10
        w = [0.30 + 0.70 * math.sin(math.pi * (j + 0.5) / F) ** 2 for j in range(F)]
        s = sum(w)
        zoom += [math.exp(math.log(10) * wj / s) for wj in w]
        denoise += [travel_denoise] * F

        end_exp = nxt["exp"] if nxt else reg["exp"] - 1
        exponent += [reg["exp"] + (end_exp - reg["exp"]) * (j + 0.5) / F
                     for j in range(F)]

        if reg.get("cameo"):
            # hidden-mascot window: after this register's arrival beat to its end
            cameos.append({"start": reg_start + fa, "end": reg_start + F,
                           **reg["cameo"]})

    loop = None
    if fmt.get("exact_loop"):
        L = min(round(1.5 * fps), F - 2)
        total = len(zoom)
        for j in range(L):
            t = (j + 1) / L
            denoise[total - L + j] = travel_denoise + (0.18 - travel_denoise) * t
        loop = {"frames": L, "s0": 0.10}
    return phases, zoom, denoise, exponent, loop, cameos
