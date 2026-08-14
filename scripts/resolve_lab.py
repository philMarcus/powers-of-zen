#!/usr/bin/env python3
"""resolve_lab — A/B the RESOLVE-ON-APPROACH protocol on a rendered card boundary.

The failed pattern (2026-08-14, abyssal vent_plain / ivory chessboard): mid-dive frames are
born from the previous frame's close-up texture, so wide/populated realm arrivals collapse
into texture morphs. The protocol: during the transition window, drive the depth ControlNet
with an ANIMATED PROCEDURAL SCAFFOLD (engine/scaffold.py) — the new realm's instance-sea
placed in world space, projected through the engine's own zoom each frame, so instances
resolve from sub-pixel grain and grow exactly as the approach implies. Prompts, denoise
choreography, zoom and drift all stay schedule-faithful (rhythm doctrine).

Preview (no GPU):  python3 scripts/resolve_lab.py abyssal_chandelier --card vent_plain
Run the A/B (GPU): python3 scripts/resolve_lab.py abyssal_chandelier --card vent_plain --run
"""
import argparse
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import engine.dive as dive  # noqa: E402
import engine.grammar as grammar  # noqa: E402
import engine.style as _style  # noqa: E402
from engine.scaffold import Resolver, mode_for_band  # noqa: E402
import pipeline as pl  # noqa: E402
from novelty_audit import band  # noqa: E402
from score import win, FFMPEG, _run  # noqa: E402


def load(fr, i):
    return Image.open(fr / f"{i:05d}.png").convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--card", required=True, help="register name whose ARRIVAL to resolve")
    ap.add_argument("--src", default=None, help="source vN (default newest complete)")
    ap.add_argument("--mode", default=None, help="sea|lattice|surface|web (default: by band)")
    ap.add_argument("--density", type=float, default=None)
    ap.add_argument("--size", type=float, default=None)
    ap.add_argument("--cn-peak", type=float, default=0.6)
    ap.add_argument("--run", action="store_true", help="actually render (GPU)")
    a = ap.parse_args()

    spec = json.loads(pl.journey_path(a.journey).read_text(encoding="utf-8"))
    sfx, model, _ = _style.resolve(spec, None)
    spec["style_suffix"] = sfx
    cfg = {**dive.DEFAULTS, **spec.get("settings", {})}
    cfg.update(dive.MODEL_PRESETS.get(model or "ds", {}))
    _fpb = spec.get("format", {}).get("frames_per_beat", 7)
    if _fpb != 7:
        _s = _fpb / 7.0
        cfg["transition_frames"] = max(2, round(dive.DEFAULTS["transition_frames"] * _s))
        cfg["seam_morph_frames"] = max(cfg["transition_frames"] + 1,
                                       round(dive.DEFAULTS["seam_morph_frames"] * _s))
        cfg["anacrusis_frames"] = max(1, round(dive.DEFAULTS["anacrusis_frames"] * _s))
    compiled = grammar.compile_journey(spec, cfg["fps"], "in")
    (phases, zoom, den_sched, _exp, loop, _cameos, arrivals, approach, seam_arrivals) = compiled
    total = len(zoom)

    # locate the card in RENDER order (grammar rotates by render_start)
    regs = spec["registers"]
    names = [r["name"] for r in regs]
    rs = spec.get("render_start")
    rot = names.index(rs) if rs in names else 0
    order = regs[rot:] + regs[:rot]
    onames = [r["name"] for r in order]
    if a.card not in onames:
        sys.exit(f"card {a.card!r} not in {onames}")
    k = onames.index(a.card)
    cf = dive.register_frame_counts(spec, cfg["fps"])
    S = sum(cf[:k])
    F = cf[k]
    fa = 0 if k == 0 else max(2, round(F * 0.25))
    card = order[k]
    exp = card.get("exp")
    mode = a.mode or (spec.get("resolve", {}) or {}).get("mode") or mode_for_band(band(exp))

    pre, post = 6, min(10, F - fa - 2)
    w0, w1 = S - pre, S + fa + post          # [w0, w1) = the resolve window
    print(f"{a.journey} · card {a.card} (render idx {k}, exp {exp}) -> mode {mode}")
    print(f"window frames {w0}..{w1 - 1} (pre {pre} / arrival {fa} / travel {post}), "
          f"total {total}, fpb {_fpb}")

    # scaffold, animated by the window's own zoom schedule + dive's drift aim
    zooms = [zoom[i] for i in range(w0, w1)]
    aims = []
    for i in range(w0, w1):
        cx = 0.5 + cfg["drift"] * math.sin(2 * math.pi * i / 263)
        cy = 0.5 + cfg["drift"] * math.sin(2 * math.pi * i / 419 + 1.7)
        aims.append((cx, cy))
    seed = abs(hash(f"{a.journey}:{a.card}")) % (2 ** 31)
    # per-mode defaults: surface instances are chimney/crown-scale (big, fewer);
    # seas start near sub-pixel and resolve
    dflt = {"sea": (1.3, 0.3), "lattice": (1.0, 0.4),
            "surface": (0.9, 0.8), "web": (1.0, 0.5)}[mode]
    density = a.density if a.density is not None else dflt[0]
    size = a.size if a.size is not None else dflt[1]
    resv = Resolver(mode, zooms, aims, seed=seed, density=density, size=size)

    def cn_at(j):
        n = w1 - w0
        if j < pre:
            return 0.20 * (j + 1) / pre
        t = (j - pre) / max(1, n - pre)
        s = a.cn_peak * min(1.0, 0.35 + 1.3 * t)
        if j >= n - 2:                        # handoff taper
            s *= 0.6
        return min(a.cn_peak, s)

    out_dir = ROOT / "output" / "resolve_lab" / f"{a.journey}_{a.card}"
    out_dir.mkdir(parents=True, exist_ok=True)
    scafdir = out_dir / "scaffold"
    scafdir.mkdir(exist_ok=True)
    for j in range(w1 - w0):
        d = resv.frame(j)
        Image.fromarray((d * 255).astype(np.uint8)).save(scafdir / f"{j:03d}.png")
    print(f"scaffold preview -> {scafdir.relative_to(ROOT)} "
          f"(cn ramp {cn_at(0):.2f}..{cn_at(w1 - w0 - 1):.2f})")
    if not a.run:
        print("preview only — rerun with --run to render the A/B (GPU)")
        return

    # source frames
    base = ROOT / "output" / a.journey
    vs = sorted([d for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                key=lambda d: int(d.name[1:]))
    src = (base / a.src) if a.src else next(
        (d for d in reversed(vs)
         if len(list((d / "build" / "frames").glob("*.png"))) >= total), None)
    if not src:
        sys.exit("no complete source render")
    srcfr = src / "build" / "frames"
    print(f"source: {src.relative_to(ROOT)}")

    # dive's boost bookkeeping, reproduced exactly (rhythm doctrine)
    seam_starts, arrival_starts = set(), set()
    acc = 0
    for pi, ph in enumerate(phases):
        if pi in seam_arrivals:
            seam_starts.add(acc)
        if pi in arrivals:
            arrival_starts.add(acc)
        acc += ph["frames"]
    T = cfg["transition_frames"]
    anac = cfg["anacrusis_frames"]

    newfr = out_dir / "resolve"
    newfr.mkdir(exist_ok=True)
    prev = load(srcfr, w0 - 1)
    frames = []
    for j in range(w1 - w0):
        i = w0 + j
        prompt, prev_prompt, kk, p_idx = dive.phase_info(phases, i)
        in_trans = prev_prompt is not None and kk < T
        base_den = den_sched[i]
        boost = 0
        if in_trans:
            boost = (cfg["arrival_denoise_boost"] if p_idx in arrivals
                     else cfg["transition_denoise_boost"])
        if any(0 <= i - b < cfg["seam_morph_frames"] for b in seam_starts):
            boost = max(boost, cfg["arrival_denoise_boost"])
        den = min(0.85, base_den + boost)
        dist = next((s - i for s in arrival_starts if 0 < s - i <= anac), None)
        if dist is not None:
            fac = ((0.7 if dist == 1 else 0.4) if anac == 2
                   else (anac + 1 - dist) / (anac + 1))
            den = min(0.85, max(den, base_den + cfg["arrival_denoise_boost"] * fac))
        cx, cy = aims[j]
        fed = dive.zoom_transform(prev, zoom[i], cfg["rotate_per_frame"], cx, cy)
        fed = dive.detail_boost(fed, cfg)
        scaf = Image.open(scafdir / f"{j:03d}.png").convert("RGB")
        ctrl = dive.upload_image(scaf, f"rl_ctrl_{j:03d}.png")
        init = dive.upload_image(fed, f"rl_init_{j:03d}.png")
        blend = min(1.0, (kk + 1) / (T + 1)) if in_trans else 1.0
        wf = dive.build_workflow(cfg, prompt, cfg["seed"] + i, init_image=init,
                                 denoise=den, prev_prompt=prev_prompt if in_trans else None,
                                 blend=blend, ctrl_image=ctrl, cn_strength=cn_at(j),
                                 depth_preproc=None)
        img = Image.open(io.BytesIO(dive.run_workflow(wf))).convert("RGB")
        img.save(newfr / f"{i:05d}.png")
        frames.append(img)
        prev = img
        print(f"  f{i} den {den:.2f} cn {cn_at(j):.2f} "
              f"{'ARRIVAL' if p_idx in arrivals and in_trans else ''}", flush=True)

    # A/B strip: resolve | original
    pairs = []
    for j in range(w1 - w0):
        i = w0 + j
        a_im = frames[j].resize((288, 512))
        b_im = load(srcfr, i).resize((288, 512))
        row = Image.new("RGB", (288 * 2 + 4, 512), (10, 10, 10))
        row.paste(a_im, (0, 0))
        row.paste(b_im, (292, 0))
        d = ImageDraw.Draw(row)
        d.text((6, 6), f"RESOLVE f{i}", fill=(255, 255, 0))
        d.text((298, 6), "original", fill=(180, 180, 180))
        row.save(out_dir / f"ab_{j:03d}.png")
        pairs.append(row)
    _run([FFMPEG, "-y", "-loglevel", "error", "-framerate", "6",
          "-i", win(str(out_dir / "ab_%03d.png")),
          "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
          "-c:v", "libx264", "-pix_fmt", "yuv420p", win(str(out_dir / "resolve_AB.mp4"))])
    print(f"A/B -> {out_dir.relative_to(ROOT)}/resolve_AB.mp4")


if __name__ == "__main__":
    main()
