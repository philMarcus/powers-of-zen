#!/usr/bin/env python3
"""seam_tail_ab — A/B loop-closure mechanisms on a render's REAL tail (Level 3 lab).

Regenerates ONLY the last L (loop) frames of an existing render under each requested method,
resuming the feedback chain at the tail exactly like repair_seam (same zoom/seed/prompt
schedule, camera never stops diving). Everything is NON-destructive: the source vN is
untouched and results land under output/seam_lab/<name>/ as per-method frames, per-method
seam-preview loops, and one labeled side-by-side comparison clip.

Methods:
  orig     extract the source render's existing tail (baseline; no GPU)
  blendcn  repair_seam's current mechanism: natural dive -> gap-SCALED pixel morph toward
           frame 0 + depth-CN ramp (the mechanism Phil REVERTED on dollhouse/snowfall — their
           far-world gaps forced morph 0.82 = a fading-photograph cross-dissolve)
  ipa      IP-Adapter homing: NO pixel blend — frame 0's IMAGE conditions the generation with
           weight ramping in across the tail, prompt crossfades to frame 0's, palette eases in.
           Every frame fully rendered + still zooming; the WORLD converges instead of the pixels.
  ipacn    ipa + a depth-CN ramp over the morph window and a small CAPPED pixel blend (<=0.35)
           on the last frames — IPA carries the world home, CN/blend only aligns the landing.

Usage (repo root):
  python3 scripts/seam_tail_ab.py dollhouse --model ds  --src-version v1
  python3 scripts/seam_tail_ab.py copper_rain           # engine-2: model/style from the deck
"""
import argparse
import io
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import dive  # noqa: E402
import pipeline as pl  # noqa: E402
import seam_lab  # noqa: E402
from engine import grammar  # noqa: E402
from engine import style as _style  # noqa: E402


def load(fr, i):
    return Image.open(fr / f"{i:05d}.png").convert("RGB")


def mad(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def regen_tail(method, cfg, srcfr, phases, zoom, loop, out_dir, depth):
    """Regenerate the L tail frames under one mechanism; returns the new frames."""
    total = len(zoom)
    L = loop["frames"]
    seam_start = total - L
    frame0 = load(srcfr, 0)
    ctrl_name = dive.upload_image(frame0, "ab_ctrl.png")
    ipa_name = dive.upload_image(frame0, "ab_ipa.png")
    src_prompt = phases[-1]["prompt"]
    dst_prompt = phases[0]["prompt"]
    prev = load(srcfr, seam_start - 1)
    f0ref = dive.channel_stats(frame0)
    W, H = cfg["width"], cfg["height"]
    morph_n, cut_tail = loop.get("morph_frames", 12), 3
    morph_start = L - morph_n
    morph_strength = None
    outfr = out_dir / method
    outfr.mkdir(parents=True, exist_ok=True)
    frames = []
    for j in range(L):
        i = seam_start + j
        t = (j + 1) / L
        drift = cfg["drift"] * (1 - t)
        cx = 0.5 + drift * math.sin(2 * math.pi * i / 263)
        cy = 0.5 + drift * math.sin(2 * math.pi * i / 419 + 1.7)
        fed = dive.zoom_transform(prev, zoom[i], cfg["rotate_per_frame"], cx, cy)
        fed = dive.detail_boost(fed, cfg)
        den, ctl, cn_s, ipa_w = 0.5, None, 0.0, 0.0
        if method == "blendcn":
            conv_n = morph_n - cut_tail
            if j < morph_start:                      # natural dive
                init, prompt, prev_p, blend = fed, src_prompt, None, 1.0
            elif j < morph_start + conv_n:           # converge, gap-scaled
                if morph_strength is None:
                    gap = mad(fed, frame0)
                    morph_strength = max(0.0, min(0.82, (gap - 15) / 55))
                    print(f"  [blendcn] gap={gap:.0f} -> morph_strength={morph_strength:.2f}", flush=True)
                m = (j - morph_start + 1) / conv_n
                init = Image.blend(fed, frame0, morph_strength * m) if morph_strength > 0.01 else fed
                prompt, prev_p, blend = dst_prompt, src_prompt, 0.3 + 0.5 * m
                ctl, cn_s = ctrl_name, 0.2 + 0.35 * m
            else:                                    # cut-tail keeps zooming
                init, prompt, prev_p, blend = fed, dst_prompt, src_prompt, 0.85
        elif method in ("ipa", "ipacn"):
            init = fed                               # NO pixel morph — IPA does the homing
            prompt, prev_p = dst_prompt, src_prompt
            blend = min(1.0, 0.15 + 0.85 * t)
            ipa_w = 0.95 * t ** 1.5                  # gentle early, strong at the wrap
            if method == "ipacn" and j >= morph_start:
                m = (j - morph_start + 1) / morph_n
                ctl, cn_s = ctrl_name, 0.2 + 0.6 * m
                if j >= L - 6:                       # small FIXED landing blend (never 0.82)
                    k = (j - (L - 6) + 1) / 6
                    init = Image.blend(fed, frame0, 0.35 * k)
        else:
            raise SystemExit(f"unknown method {method}")
        wf = seam_lab.seam_workflow(cfg, dive.upload_image(init, f"ab_init_{method}_{i:05d}.png"),
                                    prompt, cfg["seed"] + i, den, prev_prompt=prev_p, blend=blend,
                                    ctrl_name=ctl, cn_strength=cn_s, depth_preproc=depth)
        if ipa_w > 0.01:
            seam_lab.add_ipadapter(wf, ipa_name, ipa_w)
        out = Image.open(io.BytesIO(dive.run_workflow(wf))).convert("RGB")
        if out.size != (W, H):
            out = out.resize((W, H), Image.LANCZOS)
        out = dive.color_match(out, f0ref, 0.8 * t)
        out.save(outfr / f"{i:05d}.png")
        frames.append(out)
        prev = out
        print(f"  [{method}] frame {i} t={t:.2f} ipa={ipa_w:.2f} cn={cn_s:.2f}", flush=True)
    return frames


def label(im, text):
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 34], fill=(0, 0, 0))
    d.text((10, 8), text, fill=(255, 255, 255))
    return im


def preview_frames(srcfr, tail, seam_start, total, pad=6, head=18):
    """[pad source frames][tail][first `head` source frames] — the tail->head join is the loop."""
    return [load(srcfr, i) for i in range(seam_start - pad, seam_start)] + list(tail) \
        + [load(srcfr, i) for i in range(head)]


def write_clip(frames, out_path, fps=12, loops=3):
    import subprocess
    out_path = Path(out_path)
    tmp = out_path.parent / (out_path.stem + "_f")
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.png"):
        f.unlink()
    for i, im in enumerate(frames):
        im.save(tmp / f"{i:04d}.png")
    subprocess.run([dive.FFMPEG, "-y", "-stream_loop", str(loops), "-framerate", str(fps),
                    "-i", f"{tmp.name}/%04d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", out_path.name],
                   cwd=out_path.parent, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--model", help="turbo|ds (engine-2 default: the deck's pick)")
    ap.add_argument("--src-version", help="source vN under output/<name>/ (default newest complete)")
    ap.add_argument("--methods", default="orig,blendcn,ipa,ipacn")
    args = ap.parse_args()

    import requests
    try:
        requests.get(f"{dive.COMFY}/system_stats", timeout=5)
    except Exception:
        raise SystemExit(f"ComfyUI not up at {dive.COMFY}")

    spec = json.loads(pl.journey_path(args.journey).read_text(encoding="utf-8"))
    sfx, deck_model, style_name = _style.resolve(spec)
    spec["style_suffix"] = sfx
    model = args.model or deck_model or "ds"
    cfg = {**dive.DEFAULTS, **spec.get("settings", {})}
    cfg.update(dive.MODEL_PRESETS[model])
    out = grammar.compile_journey(spec, cfg["fps"], "in")
    phases, zoom, _den, _exp, loop = out[0], out[1], out[2], out[3], out[4]
    if not loop:
        raise SystemExit("journey has no exact_loop — no tail to test")
    total, L = len(zoom), loop["frames"]

    # engine-1 run dirs carry the model suffix; engine-2 dirs are bare (deck picks the model).
    # Suffix FIRST: for legacy journeys the bare dir is a DIFFERENT (early turbo) render.
    base = ROOT / "output" / f"{args.journey}_{model}"
    if not base.exists():
        base = ROOT / "output" / args.journey
    if args.src_version:
        src = base / args.src_version
    else:
        src = None
        for d in sorted(base.glob("v[0-9]*")):
            if (d / "build" / "frames" / f"{total-1:05d}.png").exists():
                src = src or d          # prefer the EARLIEST complete = the original render
    if not src or not (src / "build" / "frames" / f"{total-1:05d}.png").exists():
        raise SystemExit(f"no complete source frames under {base} (need {total})")
    srcfr = src / "build" / "frames"
    seam_start = total - L
    print(f"[ab] {args.journey}: src={base.name}/{src.name} model={model} total={total} "
          f"tail={seam_start}..{total-1} (L={L})", flush=True)

    depth = seam_lab.pick_depth_preproc(seam_lab.object_info())
    out_dir = ROOT / "output" / "seam_lab" / base.name
    out_dir.mkdir(parents=True, exist_ok=True)

    previews = {}
    for m in [m.strip() for m in args.methods.split(",") if m.strip()]:
        if m == "orig":
            tail = [load(srcfr, i) for i in range(seam_start, total)]
        else:
            import time
            t0 = time.time()
            tail = regen_tail(m, cfg, srcfr, phases, zoom, loop, out_dir, depth)
            print(f"[ab] {m}: {L} frames in {time.time()-t0:.0f}s", flush=True)
        pv = preview_frames(srcfr, tail, seam_start, total)
        previews[m] = pv
        write_clip(pv, out_dir / f"seam_{m}.mp4")
        print(f"[ab] wrote {out_dir / f'seam_{m}.mp4'}", flush=True)

    # labeled side-by-side of everything just produced
    if len(previews) > 1:
        n = min(len(v) for v in previews.values())
        combo = []
        for i in range(n):
            row = [label(previews[m][i], m) for m in previews]
            w = sum(im.width for im in row)
            canvas = Image.new("RGB", (w, row[0].height))
            x = 0
            for im in row:
                canvas.paste(im, (x, 0))
                x += im.width
            combo.append(canvas)
        write_clip(combo, out_dir / "seam_AB.mp4")
        print(f"[ab] side-by-side: {out_dir / 'seam_AB.mp4'}", flush=True)


if __name__ == "__main__":
    main()
