#!/usr/bin/env python3
"""seam_lab — ISOLATED seam-mechanism prototyping. NOT a full render.

The loop seam is the one place two different worlds meet: the last frame must become
frame 0. Today engine/dive.py "solves" this by PASTING a shrunk copy of frame 0 into the
center of the (different) last world and hard-copying frame 0 on the final frame — a
picture-in-picture, not a morph. Different worlds can't be pasted together seamlessly, so
the seam looks ugly no matter how we tune denoise.

This lab tests real MORPH mechanisms on just two frames (a source last-world frame A and a
target frame B = frame 0) — generating only the ~L bridge frames between them, so we can
iterate in seconds instead of re-rendering whole videos. It emits short clips per mechanism
plus a side-by-side, so the seam is judged by eye.

Mechanisms (choose with --methods):
  paste     the CURRENT engine mechanism (loop_composite + hard frame0 copy) — the baseline
  blend     img2img feedback whose init cross-fades A->B in pixel space, denoise ramping
            down so the tail settles onto B; prompt interpolates srcprompt->dstprompt
  blendcn   same as blend PLUS a depth ControlNet taken from B, strength ramping up, so the
            generated structure is actively steered onto frame 0's composition

Usage (from repo root):
  python3 scripts/seam_lab.py --src output/neon_mycelium_turbo/frames/00098.png \
      --dst output/neon_mycelium_turbo/frames/00000.png \
      --srcprompt "glowing neon mycelium threads" --dstprompt "a neon city grid at night" \
      --methods paste,blend,blendcn --frames 16 --out output/seam_lab/mycelium
"""
import argparse
import io
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
import dive  # noqa: E402  (reuse run_workflow/upload_image/loop_composite/ring_mask/etc.)

COMFY = dive.COMFY

# ── ControlNet asset names (present in the Comfy install) ────────────────────────────────
CN_DEPTH = "controlnet-depth-sdxl.safetensors"
# depth preprocessor node — resolved at runtime from /object_info (aux node names vary)
DEPTH_PREPROC_CANDIDATES = [
    "DepthAnythingV2Preprocessor", "DepthAnythingPreprocessor",
    "Zoe-DepthMapPreprocessor", "MiDaS-DepthMapPreprocessor",
]


def object_info():
    import requests
    return requests.get(f"{COMFY}/object_info", timeout=30).json()


def pick_depth_preproc(info):
    for n in DEPTH_PREPROC_CANDIDATES:
        if n in info:
            return n
    return None  # fall back to raw image as control hint (SDXL depth CN tolerates it poorly)


# ── workflow builders ────────────────────────────────────────────────────────────────────
def base_ckpt_nodes(checkpoint, prompt, negative, prev_prompt=None, blend=1.0):
    """The shared checkpoint + positive/negative conditioning subgraph (mirrors dive.py)."""
    wf = {
        "ckpt": {"class_type": "CheckpointLoaderSimple",
                 "inputs": {"ckpt_name": checkpoint}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["ckpt", 1]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["ckpt", 1]}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"filename_prefix": "seamlab/f", "images": ["decode", 0]}},
    }
    positive = ["pos", 0]
    if prev_prompt is not None and blend < 1.0:
        wf["pos_old"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prev_prompt, "clip": ["ckpt", 1]}}
        wf["posmix"] = {"class_type": "ConditioningAverage",
                        "inputs": {"conditioning_to": ["pos", 0], "conditioning_from": ["pos_old", 0],
                                   "conditioning_to_strength": blend}}
        positive = ["posmix", 0]
    return wf, positive


def seam_workflow(cfg, init_name, prompt, seed, denoise, prev_prompt, blend,
                  ctrl_name=None, cn_strength=0.0, depth_preproc=None):
    """img2img from init_name; optional depth-ControlNet steered from ctrl_name (= frame 0)."""
    wf, positive = base_ckpt_nodes(cfg["checkpoint"], prompt, cfg["negative"], prev_prompt, blend)
    wf["load"] = {"class_type": "LoadImage", "inputs": {"image": init_name}}
    wf["latent"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["load", 0], "vae": ["ckpt", 2]}}
    negative = ["neg", 0]
    if ctrl_name and cn_strength > 0:
        wf["cnet"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN_DEPTH}}
        wf["cimg"] = {"class_type": "LoadImage", "inputs": {"image": ctrl_name}}
        control_img = ["cimg", 0]
        if depth_preproc:
            wf["cprep"] = {"class_type": depth_preproc,
                           "inputs": {"image": ["cimg", 0], "resolution": 1024}}
            control_img = ["cprep", 0]
        wf["cnapply"] = {"class_type": "ControlNetApplyAdvanced",
                         "inputs": {"positive": positive, "negative": negative,
                                    "control_net": ["cnet", 0], "image": control_img,
                                    "strength": round(cn_strength, 3),
                                    "start_percent": 0.0, "end_percent": 1.0}}
        positive, negative = ["cnapply", 0], ["cnapply", 1]
    wf["sample"] = {"class_type": "KSampler",
                    "inputs": {"seed": seed, "steps": cfg["steps"], "cfg": cfg["cfg"],
                               "sampler_name": cfg["sampler"], "scheduler": cfg["scheduler"],
                               "denoise": round(denoise, 3), "model": ["ckpt", 0],
                               "positive": positive, "negative": negative, "latent_image": ["latent", 0]}}
    return wf


def gen(wf):
    png = dive.run_workflow(wf)
    return Image.open(io.BytesIO(png)).convert("RGB")


# ── the three mechanisms ─────────────────────────────────────────────────────────────────
def method_paste(A, B, L, cfg):
    """Baseline: current engine loop tail — grow a shrunk copy of B in A's center, last=copy."""
    frames = []
    import math
    s0 = 0.10
    prev = A
    for j in range(L):
        t = (j + 1) / L
        s = math.exp(math.log(s0) * (1 - t))
        out = dive.loop_composite(prev, B, s)
        frames.append(out)
        prev = out
    frames.append(B.copy())  # exact loop hard copy
    return frames


def method_blend(A, B, L, cfg, cn=False, depth_preproc=None):
    """Morph: init cross-fades A->B, denoise ramps down, prompt interpolates. Optional depth CN."""
    frames = []
    prev = A
    ctrl_name = dive.upload_image(B, "seam_ctrl_B.png") if cn else None
    for j in range(L):
        t = (j + 1) / L
        a = t                       # init weight toward B
        # init = pixel cross-fade of the running feedback toward the target
        init = Image.blend(prev, B, a)
        init_name = dive.upload_image(init, f"seam_init_{j:03d}.png")
        # denoise high early (repaint the morph), low late (settle onto B)
        denoise = 0.55 + (0.14 - 0.55) * t
        cn_strength = (0.30 + 0.60 * t) if cn else 0.0
        wf = seam_workflow(cfg, init_name, cfg["dstprompt"], cfg["seed"] + j, denoise,
                           prev_prompt=cfg["srcprompt"], blend=t,
                           ctrl_name=ctrl_name, cn_strength=cn_strength, depth_preproc=depth_preproc)
        out = gen(wf)
        if out.size != A.size:
            out = out.resize(A.size, Image.LANCZOS)
        frames.append(out)
        prev = out
    # final settle: one low-denoise pass whose init IS B => output ~= B without a hard cut
    init_name = dive.upload_image(B, "seam_init_final.png")
    wf = seam_workflow(cfg, init_name, cfg["dstprompt"], cfg["seed"] + L, 0.10,
                       prev_prompt=None, blend=1.0,
                       ctrl_name=ctrl_name, cn_strength=(0.9 if cn else 0.0), depth_preproc=depth_preproc)
    out = gen(wf)
    if out.size != A.size:
        out = out.resize(A.size, Image.LANCZOS)
    frames.append(out)
    return frames


METHODS = {
    "paste": lambda A, B, L, cfg: method_paste(A, B, L, cfg),
    "blend": lambda A, B, L, cfg: method_blend(A, B, L, cfg, cn=False),
    "blendcn": lambda A, B, L, cfg: method_blend(A, B, L, cfg, cn=True, depth_preproc=cfg["depth_preproc"]),
}


# ── clip assembly ────────────────────────────────────────────────────────────────────────
def write_loop_clip(frames, A, B, out_path, fps=12):
    """Write a looping mp4 that shows the seam repeatedly: [A ... bridge ... B] x3. The JOIN
    is B->A (the loop point) so you SEE whether the seam reads as continuous. Runs the Windows
    ffmpeg with RELATIVE paths + cwd (mirrors engine/dive.py — avoids /mnt/c vs C:\\ issues)."""
    import subprocess
    out_path = Path(out_path)
    cwd = out_path.parent
    stem = out_path.stem
    tmp = cwd / (stem + "_frames")
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.png"):
        f.unlink()
    seq = [A] * 2 + frames + [B] * 2
    for i, f in enumerate(seq):
        f.save(tmp / f"{i:04d}.png")
    subprocess.run([dive.FFMPEG, "-y", "-stream_loop", "3", "-framerate", str(fps),
                    "-i", f"{stem}_frames/%04d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", out_path.name],
                   cwd=cwd, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="source last-world frame (A)")
    ap.add_argument("--dst", required=True, help="target frame 0 (B) the seam must reach")
    ap.add_argument("--srcprompt", default="")
    ap.add_argument("--dstprompt", default="")
    ap.add_argument("--methods", default="paste,blend,blendcn")
    ap.add_argument("--frames", type=int, default=16, help="bridge frames L")
    ap.add_argument("--checkpoint", default="dreamshaperXL.safetensors")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--cfg", type=float, default=2.0)
    ap.add_argument("--sampler", default="dpmpp_2m")
    ap.add_argument("--scheduler", default="karras")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--out", default="output/seam_lab/test")
    args = ap.parse_args()

    import requests
    try:
        requests.get(f"{COMFY}/system_stats", timeout=5)
    except Exception:
        print("ComfyUI not up at", COMFY, "— start it first."); sys.exit(1)

    A = Image.open(args.src).convert("RGB")
    B = Image.open(args.dst).convert("RGB")
    if A.size != B.size:
        B = B.resize(A.size, Image.LANCZOS)

    depth_preproc = None
    if "blendcn" in args.methods:
        info = object_info()
        if "ControlNetApplyAdvanced" not in info or "ControlNetLoader" not in info:
            print("ControlNet nodes missing in this Comfy install."); sys.exit(1)
        depth_preproc = pick_depth_preproc(info)
        print(f"depth preprocessor: {depth_preproc or '(none — raw image as depth hint)'}")

    cfg = {"checkpoint": args.checkpoint, "steps": args.steps, "cfg": args.cfg,
           "sampler": args.sampler, "scheduler": args.scheduler, "seed": args.seed,
           "negative": "blurry, text, watermark, low quality, deformed",
           "srcprompt": args.srcprompt, "dstprompt": args.dstprompt,
           "depth_preproc": depth_preproc}

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    for m in args.methods.split(","):
        m = m.strip()
        if m not in METHODS:
            print("unknown method", m); continue
        t0 = time.time()
        print(f"[{m}] generating {args.frames} bridge frames…", flush=True)
        frames = METHODS[m](A, B, args.frames, cfg)
        clip = out_dir / f"seam_{m}.mp4"
        write_loop_clip(frames, A, B, clip)
        print(f"[{m}] {len(frames)} frames in {time.time()-t0:.0f}s -> {clip}", flush=True)
    print("DONE. Watch the mp4s: the B->A join is the loop seam.")


if __name__ == "__main__":
    main()
