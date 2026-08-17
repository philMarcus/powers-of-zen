#!/usr/bin/env python3
"""orbit_lab — the ENGINE 3 Phase-2 gate: does warp-and-reimagine survive re-diffusion?

Re-renders a card's travel section from an existing render with a TRUE ORBIT: each frame,
the previous frame's own depth (DepthAnything via ComfyUI, EMA-smoothed) drives a
depth-parallax revolve about the card's subject, THEN the scheduled zoom applies untouched
(iron law: the scale axis never changes), then the frame re-diffuses at schedule denoise
plus a disocclusion boost. If the world reads as the camera circling it — near sweeping
against far, new sides being invented — engine 3 is GO.

Preview (no GPU):  python3 scripts/orbit_lab.py abyssal_chandelier --card young_star --src v2
Run (GPU):         ... --run [--deg 1.2] [--frames 20]
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
import engine.warp as warp  # noqa: E402
import pipeline as pl  # noqa: E402
from score import win, FFMPEG, _run  # noqa: E402


def load(fr, i):
    return Image.open(fr / f"{i:05d}.png").convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--card", required=True)
    ap.add_argument("--src", default=None)
    ap.add_argument("--deg", type=float, default=0.8, help="orbit degrees per frame")
    ap.add_argument("--frames", type=int, default=20, help="window length")
    ap.add_argument("--pivot-depth", type=float, default=0.55)
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()

    spec = json.loads(pl.journey_path(a.journey).read_text(encoding="utf-8"))
    sfx, model, _ = _style.resolve(spec, None)
    spec["style_suffix"] = sfx
    cfg = {**dive.DEFAULTS, **spec.get("settings", {})}
    cfg.update(dive.MODEL_PRESETS.get(model or "ds", {}))
    compiled = grammar.compile_journey(spec, cfg["fps"], "in")
    (phases, zoom, den_sched, _exp, loop, _cameos, arrivals, approach, seam_arrivals) = compiled
    total = len(zoom)

    regs = spec["registers"]
    names = [r["name"] for r in regs]
    rs = spec.get("render_start")
    rot = names.index(rs) if rs in names else 0
    order = [r["name"] for r in (regs[rot:] + regs[:rot])]
    if a.card not in order:
        sys.exit(f"card {a.card!r} not in {order}")
    k = order.index(a.card)
    cf = dive.register_frame_counts(spec, cfg["fps"])
    S, F = sum(cf[:k]), cf[k]
    fa = 0 if k == 0 else max(2, round(F * 0.25))
    w0 = S + fa + 2                      # after the arrival settles; travel section
    w1 = min(w0 + a.frames, S + F, total - (loop["frames"] if loop else 0))
    net = a.deg * (w1 - w0)
    print(f"{a.journey} · {a.card}: orbit window {w0}..{w1 - 1} "
          f"({a.deg}°/frame, net {net:.0f}°)")
    if not a.run:
        print("preview only — --run to render (GPU)")
        return

    base = ROOT / "output" / a.journey
    vs = sorted([d for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                key=lambda d: int(d.name[1:]))
    src = (base / a.src) if a.src else next(
        (d for d in reversed(vs)
         if len(list((d / "build" / "frames").glob("*.png"))) >= total), None)
    if not src:
        sys.exit("no complete source render")
    srcfr = src / "build" / "frames"
    out_dir = ROOT / "output" / "orbit_lab" / f"{a.journey}_{a.card}"
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)

    T = cfg["transition_frames"]
    prev = load(srcfr, w0 - 1)
    depth_s = None
    frames = []
    for j in range(w1 - w0):
        i = w0 + j
        prompt, prev_prompt, kk, p_idx = dive.phase_info(phases, i)
        in_trans = prev_prompt is not None and kk < T
        d_raw = warp.depth_via_comfy(prev)
        depth_s = warp.ema(depth_s, d_raw, alpha=0.6)
        # V2 (2026-08-17): quantize depth into coherent PLANES before warping — raw
        # DepthAnything on abstract fields is noisy, and noisy parallax shredded v1
        from PIL import ImageFilter as _IF
        _dq = Image.fromarray((depth_s * 255).astype(np.uint8)).filter(
            _IF.GaussianBlur(9))
        depth_w = np.round(np.asarray(_dq, np.float32) / 255.0 * 4) / 4
        # ORBIT first (the camera moves), then the scheduled zoom untouched (iron law)
        orbited, stretch = warp.orbit(prev, depth_w, a.deg, pivot=(0.5, 0.47),
                                      pivot_depth=a.pivot_depth)
        cx = 0.5 + cfg["drift"] * math.sin(2 * math.pi * i / 263)
        cy = 0.5 + cfg["drift"] * math.sin(2 * math.pi * i / 419 + 1.7)
        fed = dive.zoom_transform(orbited, zoom[i], cfg["rotate_per_frame"], cx, cy)
        fed = dive.detail_boost(fed, cfg)
        # V3: the warp's extra bilinear pass low-passes the image every frame and 0.40
        # denoise re-synthesizes less than it loses (v1+v2 wash-out). Counter with a
        # post-warp unsharp + a raised re-synthesis floor during the orbit.
        from PIL import ImageFilter as _IF2
        fed = fed.filter(_IF2.UnsharpMask(radius=2, percent=90, threshold=2))
        den = max(0.52, warp.disocclusion_denoise(den_sched[i], stretch, k=0.22))
        ref = dive.upload_image(fed, "orbit_feed.png")
        # V2 ANCHOR: the v1 failure passed NO ControlNet — dive's own approach frames hold
        # structure with depth-CN from the fed frame; the orbit needs the same identity
        # hold or re-diffusion drifts the subject away instead of circling it.
        wf = dive.build_workflow(cfg, prompt, cfg["seed"] + i, init_image=ref, denoise=den,
                                 prev_prompt=prev_prompt if in_trans else None,
                                 blend=min(1.0, (kk + 1) / (T + 1)) if in_trans else 1.0,
                                 ctrl_image=ref, cn_strength=0.5,
                                 depth_preproc=dive.pick_depth_preproc())
        img = Image.open(io.BytesIO(dive.run_workflow(wf))).convert("RGB")
        img.save(out_dir / "frames" / f"{i:05d}.png")
        frames.append(img)
        prev = img
        print(f"  f{i} den {den:.2f} orbit {a.deg * (j + 1):.0f}°", flush=True)

    for j in range(w1 - w0):
        i = w0 + j
        row = Image.new("RGB", (288 * 2 + 4, 512), (10, 10, 10))
        row.paste(frames[j].resize((288, 512)), (0, 0))
        row.paste(load(srcfr, i).resize((288, 512)), (292, 0))
        d = ImageDraw.Draw(row)
        d.text((6, 6), f"ORBIT f{i}", fill=(255, 255, 0))
        d.text((298, 6), "original", fill=(180, 180, 180))
        row.save(out_dir / f"ab_{j:03d}.png")
    _run([FFMPEG, "-y", "-loglevel", "error", "-framerate", "6",
          "-i", win(str(out_dir / "ab_%03d.png")),
          "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
          "-c:v", "libx264", "-pix_fmt", "yuv420p", win(str(out_dir / "orbit_AB.mp4"))])
    print(f"A/B -> {out_dir.relative_to(ROOT)}/orbit_AB.mp4")


if __name__ == "__main__":
    main()
