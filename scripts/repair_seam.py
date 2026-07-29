#!/usr/bin/env python3
"""repair_seam — regenerate ONLY a video's loop-seam tail with the blendCN morph, reusing the
saved generation frames. The engine is a feedback chain whose sole heavy state is the previous
frame (on disk); everything else (seed=base+i, zoom/denoise/prompt schedule, drift=sin(i)) is a
deterministic function of the frame index. So we can resume at the seam without replaying the
whole dive on the GPU — regenerate ~L frames instead of the full video.

Non-destructive & preserves everything (per Phil): the source version is untouched; the repair
lands in a FRESH vN whose build/frames/ holds the original body frames + new seam frames, and
build/frames_orig_seam/ keeps the ORIGINAL seam frames for side-by-side comparison.

The seam: over the last L frames the dive keeps zooming while the frame morphs toward frame 0
— init cross-fades the (still-zooming) feedback toward frame 0, denoise ramps down, and a depth
ControlNet from frame 0 steers the structure onto it, so the last frame lands ON frame 0 (exact
loop) instead of hard-cutting from a different world.

Usage:
  python3 scripts/repair_seam.py cosmic_scales_remix --model turbo
  python3 scripts/repair_seam.py circuit_city --model turbo --den-hi 0.5 --den-lo 0.14
"""
import argparse
import io
import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
import dive  # noqa: E402
import seam_lab  # noqa: E402
from engine import grammar  # noqa: E402


def newest_complete_version(name, total):
    base = ROOT / "output" / name
    best = None
    for d in sorted(base.glob("v[0-9]*")):
        if len(list((d / "build" / "frames").glob("*.png"))) >= total:
            best = d
    return best


def load(fr, i):
    return Image.open(fr / f"{i:05d}.png").convert("RGB")


def soft_disc(w, h, rfrac, feather):
    """White filled circle of radius rfrac·(half-diagonal), soft-edged. rfrac=1 covers corners."""
    m = Image.new("L", (w, h), 0)
    R = rfrac * ((w * w + h * h) ** 0.5) / 2 * 1.02
    ImageDraw.Draw(m).ellipse([w / 2 - R, h / 2 - R, w / 2 + R, h / 2 + R], fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--model", default="turbo")
    ap.add_argument("--src-version", help="source vN dir name (default = newest complete)")
    ap.add_argument("--den-hi", type=float, default=0.5, help="dive/morph denoise")
    ap.add_argument("--den-lo", type=float, default=0.45, help="(unused)")
    ap.add_argument("--morph-frames", type=int, default=6,
                    help="how many trailing frames morph into the exact frame 0 (brief; no frames added)")
    ap.add_argument("--palette", type=float, default=0.8,
                    help="strength of the palette pull toward frame 0 (ramps 0→this across the seam)")
    ap.add_argument("--cn-lo", type=float, default=0.30, help="depth-ControlNet strength at start")
    ap.add_argument("--cn-hi", type=float, default=0.90, help="depth-ControlNet strength at end")
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()

    import requests
    try:
        requests.get(f"{dive.COMFY}/system_stats", timeout=5)
    except Exception:
        print("ComfyUI not up at", dive.COMFY); sys.exit(1)

    spec = json.loads((ROOT / "journeys" / f"{args.journey}.json").read_text())
    cfg = {**dive.DEFAULTS, **spec.get("settings", {})}
    cfg.update(dive.MODEL_PRESETS[args.model])
    cfg["build"] = "in"
    phases, zoom, den_sched, exponent, loop, cameos, arr = grammar.compile_journey(spec, cfg["fps"], "in")
    if not loop:
        print("journey has no exact_loop — nothing to repair"); sys.exit(1)
    total = len(zoom); L = loop["frames"]; seam_start = total - L
    name = f"{spec.get('name', args.journey)}_{args.model}"

    src = (ROOT / "output" / name / args.src_version) if args.src_version else newest_complete_version(name, total)
    if not src or not (src / "build" / "frames" / f"{total-1:05d}.png").exists():
        print(f"no complete source frames for {name} (need {total} frames in a vN/build/frames)"); sys.exit(1)
    srcfr = src / "build" / "frames"
    print(f"repair {name}: source={src.name}, total={total}, seam {seam_start}..{total-1} (L={L})")

    # fresh output version (never overwrite; mirror dive.py's vN scheme)
    base = ROOT / "output" / name
    n = 1 + max([int(d.name[1:]) for d in base.glob("v[0-9]*") if d.name[1:].isdigit()], default=0)
    out_dir = base / f"v{n}"
    outfr = out_dir / "build" / "frames"; outfr.mkdir(parents=True, exist_ok=True)
    origfr = out_dir / "build" / "frames_orig_seam"; origfr.mkdir(parents=True, exist_ok=True)
    print(f"[repair] out dir: {out_dir}")

    # preserve everything: copy the untouched body frames + keep the ORIGINAL seam frames
    for i in range(seam_start):
        shutil.copy(srcfr / f"{i:05d}.png", outfr / f"{i:05d}.png")
    for i in range(seam_start, total):
        shutil.copy(srcfr / f"{i:05d}.png", origfr / f"{i:05d}.png")

    # depth ControlNet from frame 0
    depth = seam_lab.pick_depth_preproc(seam_lab.object_info())
    print(f"[repair] depth preprocessor: {depth or '(raw frame as hint)'}")
    frame0 = load(srcfr, 0)
    ctrl_name = dive.upload_image(frame0, f"repair_ctrl_{name}.png")

    src_prompt = phases[-1]["prompt"]   # last register (keeps plunging toward the desk = frame 0)
    dst_prompt = phases[0]["prompt"]    # first register = frame 0
    prev = load(srcfr, seam_start - 1)  # the real frame just before the seam
    W, H = cfg["width"], cfg["height"]
    f0ref = dive.channel_stats(frame0)  # frame 0's palette anchor (mean/std per channel)
    morph_n = args.morph_frames         # how many trailing frames do the brief morph into frame 0
    morph_start = (L - 1) - morph_n

    # NATURAL DIVE → PALETTE MATCH → BRIEF MORPH (no added frames, so the music grid is untouched):
    #  • most of the seam is a real moving dive (last-register prompt) — full zoom, alive.
    #  • every frame's palette is pulled toward frame 0's (ramping) — the missing last→first blend.
    #  • only the final `morph_n` frames morph into the EXACT frame 0, and since the dive already
    #    ended on a same-room, palette-matched image, that morph is brief and clean.
    for j in range(L - 1):              # regenerate seam_start .. total-2
        i = seam_start + j
        t = (j + 1) / L
        z = zoom[i]
        drift = cfg["drift"] * (1 - (i - seam_start + 1) / L)
        cx = 0.5 + drift * math.sin(2 * math.pi * i / 263)
        cy = 0.5 + drift * math.sin(2 * math.pi * i / 419 + 1.7)
        fed = dive.zoom_transform(prev, z, cfg["rotate_per_frame"], cx, cy)  # keep diving (full zoom)
        fed = dive.detail_boost(fed, cfg)
        if j < morph_start:                      # NATURAL DIVE portion
            init, prompt, prev_p, blend = fed, src_prompt, None, 1.0
        else:                                    # BRIEF MORPH into frame 0
            m = (j - morph_start + 1) / morph_n  # 0→1 across the last morph_n frames
            init = Image.blend(fed, frame0, min(1.0, m * 0.9))
            prompt, prev_p, blend = dst_prompt, src_prompt, 0.4 + 0.6 * m
        wf = seam_lab.seam_workflow(cfg, dive.upload_image(init, f"repair_init_{i:05d}.png"),
                                    prompt, cfg["seed"] + i, args.den_hi, prev_prompt=prev_p, blend=blend)
        out = Image.open(io.BytesIO(dive.run_workflow(wf))).convert("RGB")
        if out.size != (W, H):
            out = out.resize((W, H), Image.LANCZOS)
        out = dive.color_match(out, f0ref, args.palette * t)   # warm the palette toward frame 0
        out.save(outfr / f"{i:05d}.png"); prev = out
        tag = "morph" if j >= morph_start else "dive "
        print(f"  seam {i}  {tag} t={t:.2f} palette={args.palette*t:.2f} den={args.den_hi}", flush=True)

    frame0.save(outfr / f"{total-1:05d}.png")   # exact loop: last frame IS frame 0

    (out_dir / "build" / "repair.json").write_text(json.dumps({
        "source": src.name, "seam_start": seam_start, "L": L, "mechanism": "blendCN",
        "den": [args.den_hi, args.den_lo], "cn": [args.cn_lo, args.cn_hi]}, indent=2))

    # a seam-preview loop clip: frames around the wrap, looped, so the loop cut is judgeable
    seam_preview(outfr, seam_start, total, out_dir / f"seam_preview_{name}.mp4")
    orig_preview(origfr, srcfr, seam_start, total, out_dir / f"seam_preview_{name}_ORIG.mp4")

    if not args.no_video:
        cfg.setdefault("loop_fade_frames", 0)
        dive.assemble(cfg, name, out_dir, outfr, total, exponent=exponent)
        print(f"[repair] assembled full video in {out_dir}")
    print("DONE. Compare seam_preview (new) vs seam_preview_*_ORIG (old).")


def _clip(frames, out_path, fps=12, loops=3):
    import subprocess
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


def seam_preview(fr, seam_start, total, out_path, pad=6):
    """[a few frames before the wrap … last frame][first few frames] looped — the join is the
    loop cut, so you SEE whether it reads as continuous."""
    frames = [load(fr, i) for i in range(seam_start - pad, total)] + [load(fr, i) for i in range(pad)]
    _clip(frames, out_path)


def orig_preview(origfr, srcfr, seam_start, total, out_path, pad=6):
    frames = [load(srcfr, i) for i in range(seam_start - pad, seam_start)] \
        + [load(origfr, i) for i in range(seam_start, total)] \
        + [load(srcfr, i) for i in range(pad)]
    _clip(frames, out_path)


if __name__ == "__main__":
    main()
