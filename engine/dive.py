#!/usr/bin/env python3
"""Zoomer dive engine — Deforum-style feedback zoom driven through the ComfyUI API.

Each output frame is made by zoom-cropping the previous frame, then re-diffusing it
(img2img, low denoise) with a prompt that changes over the journey. The feedback loop
is what creates the continuous morphing dive.

Anti-collapse: every fed-back frame is re-sharpened, contrast/saturation-lifted and
dusted with noise so detail never death-spirals into mush.
Palette anchoring: each phase captures reference color stats just after its transition
window; later frames are pulled back toward them so one world's palette can't colonize
the next (the feedback loop otherwise drifts to monochrome).
Prompt blending: the first frames of each phase blend old and new prompts
(ConditioningAverage) with a denoise boost, so worlds dissolve instead of switch.
Loop crossfade: the last frames are blended into the first frames so the video loops
without a visible seam.

Usage:
    python3 engine/dive.py journeys/foo.json [--model turbo|ds] [--frames N] [--no-video]
"""
import argparse
import io
import json
import math
import subprocess
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

import grammar

COMFY = "http://localhost:8188"
FFMPEG = ("/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/"
          "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
          "ffmpeg-8.1.1-full_build/bin/ffmpeg.exe")

MODEL_PRESETS = {
    "turbo": {"checkpoint": "SDXL-TURBO\\sd_xl_turbo_1.0_fp16.safetensors",
              "steps": 8, "cfg": 1.5, "sampler": "euler_ancestral",
              "scheduler": "normal", "denoise": 0.58},
    # DreamShaper XL Turbo/Lightning: DPM++ SDE + KARRAS is required (not "normal"),
    # cfg 2, ~4-8 effective steps (steps*denoise). Source: civitai model card.
    "ds": {"checkpoint": "dreamshaperXL.safetensors",
           "steps": 12, "cfg": 2.0, "sampler": "dpmpp_sde",
           "scheduler": "karras", "denoise": 0.50},
}

DEFAULTS = {
    "checkpoint": MODEL_PRESETS["turbo"]["checkpoint"],
    "width": 576,
    "height": 1024,
    "zoom_per_frame": 1.045,
    "rotate_per_frame": 0.15,
    "drift": 0.03,        # wandering zoom-center amplitude (fraction of frame size)
    "denoise": 0.58,
    "steps": 8,           # effective diffusion steps ≈ steps * denoise
    "cfg": 1.5,
    "sampler": "euler_ancestral",
    "scheduler": "normal",
    "fps": 12,            # raw generation rate
    "final_fps": 24,      # motion-interpolated output rate (0 = skip interpolation)
    "seed": 1234,
    "negative": ("text, watermark, logo, blurry, frame, border, low quality, "
                 "human face, portrait, close-up person"),
    # anti-collapse re-texturing of each fed-back frame
    "sharpen": 1.35,
    "contrast": 1.04,
    "saturation": 1.03,
    "noise": 0.05,
    # phase transitions: prompt blending + extra denoise so worlds dissolve, not switch
    "transition_frames": 6,
    "transition_denoise_boost": 0.06,   # beat changes within a register: gentle
    "arrival_denoise_boost": 0.18,      # register boundaries: strong repaint so
                                        # palettes can actually flip between worlds
    # palette anchoring strength (0 = off)
    "color_match": 0.5,
    # loop seam: crossfade this many tail frames into the head frames (0 = off)
    "loop_fade_frames": 0,
    "counter": True,      # 10^n overlay — the Powers of Zen signature, on by
                          # default; the value is pinned to the current register
                          # and spins at handoffs, so it's honest even in wraps.
                          # False disables; "auto" = only on monotonic ladders.
    "reverse": False,     # legacy, ignored (both cuts always emitted)
    "build": "in",        # "in": crop center, invent interiors (LARGE->SMALL cards)
                          # "out": shrink + outpaint borders (SMALL->LARGE cards);
                          #        worlds physically inherited, no double-objects
}


def build_workflow(cfg, prompt, seed, init_image=None, denoise=None,
                   prev_prompt=None, blend=1.0, mask_image=None):
    """ComfyUI API-format workflow. txt2img when init_image is None, else img2img.
    When prev_prompt is given, positive conditioning is a weighted average of the old
    and new prompts (blend = weight of the NEW prompt)."""
    wf = {
        "ckpt": {"class_type": "CheckpointLoaderSimple",
                 "inputs": {"ckpt_name": cfg["checkpoint"]}},
        "pos": {"class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["ckpt", 1]}},
        "neg": {"class_type": "CLIPTextEncode",
                "inputs": {"text": cfg["negative"], "clip": ["ckpt", 1]}},
        "decode": {"class_type": "VAEDecode",
                   "inputs": {"samples": ["sample", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage",
                 "inputs": {"filename_prefix": "zoomer/frame", "images": ["decode", 0]}},
    }
    positive = ["pos", 0]
    if prev_prompt is not None and blend < 1.0:
        wf["pos_old"] = {"class_type": "CLIPTextEncode",
                         "inputs": {"text": prev_prompt, "clip": ["ckpt", 1]}}
        wf["posmix"] = {"class_type": "ConditioningAverage",
                        "inputs": {"conditioning_to": ["pos", 0],
                                   "conditioning_from": ["pos_old", 0],
                                   "conditioning_to_strength": blend}}
        positive = ["posmix", 0]
    if init_image:
        wf["load"] = {"class_type": "LoadImage", "inputs": {"image": init_image}}
        if mask_image:
            # masked denoise: repaint the border ring, protect the inherited center
            wf["enc"] = {"class_type": "VAEEncode",
                         "inputs": {"pixels": ["load", 0], "vae": ["ckpt", 2]}}
            wf["loadmask"] = {"class_type": "LoadImage",
                              "inputs": {"image": mask_image}}
            wf["tomask"] = {"class_type": "ImageToMask",
                            "inputs": {"image": ["loadmask", 0], "channel": "red"}}
            wf["latent"] = {"class_type": "SetLatentNoiseMask",
                            "inputs": {"samples": ["enc", 0], "mask": ["tomask", 0]}}
        else:
            wf["latent"] = {"class_type": "VAEEncode",
                            "inputs": {"pixels": ["load", 0], "vae": ["ckpt", 2]}}
    else:
        wf["latent"] = {"class_type": "EmptyLatentImage",
                        "inputs": {"width": cfg["width"], "height": cfg["height"],
                                   "batch_size": 1}}
    wf["sample"] = {"class_type": "KSampler",
                    "inputs": {"seed": seed, "steps": cfg["steps"], "cfg": cfg["cfg"],
                               "sampler_name": cfg["sampler"],
                               "scheduler": cfg["scheduler"],
                               "denoise": (denoise if denoise is not None else 1.0),
                               "model": ["ckpt", 0], "positive": positive,
                               "negative": ["neg", 0], "latent_image": ["latent", 0]}}
    return wf


def run_workflow(wf, timeout=300):
    """Queue a workflow, wait for completion, return the output image bytes."""
    r = requests.post(f"{COMFY}/prompt", json={"prompt": wf}, timeout=30)
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=30).json()
        if pid in h:
            status = h[pid].get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error: {json.dumps(status)[:2000]}")
            outputs = h[pid].get("outputs", {})
            for node in outputs.values():
                for img in node.get("images", []):
                    v = requests.get(f"{COMFY}/view", params={
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output")}, timeout=60)
                    v.raise_for_status()
                    return v.content
        time.sleep(0.25)
    raise TimeoutError(f"workflow {pid} did not finish in {timeout}s")


def upload_image(img, name):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = requests.post(f"{COMFY}/upload/image",
                      files={"image": (name, buf, "image/png")},
                      data={"overwrite": "true"}, timeout=60)
    r.raise_for_status()
    return r.json()["name"]


def zoom_transform(img, zoom, rotate_deg, cx=0.5, cy=0.5):
    """Zoom toward (cx, cy) (crop + upscale), with optional slow rotation.
    A drifting center breaks radial-symmetry lock (concentric-ring artifacts)."""
    w, h = img.size
    if rotate_deg:
        img = img.rotate(rotate_deg, resample=Image.BICUBIC, expand=False)
    cw, ch = w / zoom, h / zoom
    left = min(max(cx * w - cw / 2, 0), w - cw)
    top = min(max(cy * h - ch / 2, 0), h - ch)
    return img.crop((left, top, left + cw, top + ch)).resize((w, h), Image.LANCZOS)


def detail_boost(img, cfg):
    """Fight feedback collapse: sharpen, lift contrast/saturation, add faint noise."""
    if cfg["sharpen"]:
        img = ImageEnhance.Sharpness(img).enhance(cfg["sharpen"])
    if cfg["contrast"]:
        img = ImageEnhance.Contrast(img).enhance(cfg["contrast"])
    if cfg["saturation"]:
        img = ImageEnhance.Color(img).enhance(cfg["saturation"])
    if cfg["noise"]:
        grain = Image.effect_noise(img.size, 64).convert("RGB")
        img = Image.blend(img, grain, cfg["noise"])
    return img


def channel_stats(img):
    s = ImageStat.Stat(img)
    return s.mean, s.stddev


def color_match(img, ref, strength):
    """Pull img's per-channel mean/std partway toward the reference stats."""
    means, stds = channel_stats(img)
    rmeans, rstds = ref
    out = []
    for c, m, sd, rm, rsd in zip(img.split(), means, stds, rmeans, rstds):
        sd = sd or 1.0
        lut = [int(max(0, min(255, v + strength * ((v - m) * (rsd / sd) + rm - v))))
               for v in range(256)]
        out.append(c.point(lut))
    return Image.merge("RGB", out)


FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def shrink_transform(img, zoom, cx=0.5, cy=0.5):
    """Build-out step: shrink the whole frame toward (cx, cy). Returns the new
    canvas (old frame as border seed, shrunk copy pasted over) and the paste box."""
    w, h = img.size
    sw, sh = max(2, round(w / zoom)), max(2, round(h / zoom))
    px, py = round(cx * w - sw / 2), round(cy * h - sh / 2)
    canvas = img.copy()
    canvas.paste(img.resize((sw, sh), Image.LANCZOS), (px, py))
    return canvas, (px, py, sw, sh)


def ring_mask(w, h, box, center_val=30):
    """White border ring (repaint), near-black center (protect), soft feather."""
    px, py, sw, sh = box
    m = Image.new("L", (w, h), 255)
    inset = max(2, int(min(sw, sh) * 0.05))
    ImageDraw.Draw(m).rectangle([px + inset, py + inset,
                                 px + sw - inset, py + sh - inset],
                                fill=center_val)
    return m.filter(ImageFilter.GaussianBlur(max(2, int(w * 0.02)))).convert("RGB")


def loop_composite(fed, frame0, s, blur_frac=0.14):
    """Paste frame0 scaled by s into the center of fed with a soft-edged mask."""
    w, h = fed.size
    sw, sh = max(2, int(w * s)), max(2, int(h * s))
    small = frame0.resize((sw, sh), Image.LANCZOS)
    mask = Image.new("L", (sw, sh), 0)
    inset = max(2, int(min(sw, sh) * blur_frac))
    ImageDraw.Draw(mask).rectangle([inset, inset, sw - inset, sh - inset], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(inset))
    out = fed.copy()
    out.paste(small, ((w - sw) // 2, (h - sh) // 2), mask)
    return out


def load_sprite(path):
    """Center-crop a mascot render and build a soft circular alpha for compositing."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    side = int(min(w, h) * 0.62)
    img = img.crop(((w - side) // 2, (h - side) // 2,
                    (w + side) // 2, (h + side) // 2))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([side * 0.02, side * 0.02,
                                  side * 0.98, side * 0.98], fill=225)
    return img, mask.filter(ImageFilter.GaussianBlur(side * 0.10))


def paste_sprite(fed, sprite, mask, px, py, size):
    """Paste sprite centered at fraction coords (px, py) at `size` fraction of width."""
    w, h = fed.size
    side = max(8, int(w * size))
    sp = sprite.resize((side, side), Image.LANCZOS)
    mk = mask.resize((side, side), Image.LANCZOS)
    out = fed.copy()
    out.paste(sp, (int(px * w - side / 2), int(py * h - side / 2)), mk)
    return out


def draw_counter(img, exp_value, pulse_age=None):
    """Odometer-style scale counter: 10^n m, bottom-left, pulse ring on crossings."""
    big = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 30)
    sup = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 18)
    unit = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 21)
    n = int(round(exp_value))
    x, y = 22, img.height - 88
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    shadow = (0, 0, 0, 160)
    white = (255, 255, 255, 230)
    w10 = d.textlength("10", font=big)
    wexp = d.textlength(str(n), font=sup)
    for dx, dy, col in ((2, 2, shadow), (0, 0, white)):
        d.text((x + dx, y + dy), "10", font=big, fill=col)
        d.text((x + w10 + 2 + dx, y - 9 + dy), str(n), font=sup, fill=col)
        d.text((x + w10 + wexp + 9 + dx, y + 8 + dy), "m", font=unit, fill=col)
    if pulse_age is not None:
        cx, cy = x + (w10 + wexp + 30) / 2, y + 17
        r = 24 + pulse_age * 7
        a = max(0, 130 - pulse_age * 26)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, a), width=2)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def phase_info(phases, i):
    """Return (prompt, prev_prompt, frames_into_phase, phase_index) for frame i."""
    n = 0
    for p_idx, ph in enumerate(phases):
        if i < n + ph["frames"]:
            prev = phases[p_idx - 1]["prompt"] if p_idx > 0 else None
            return ph["prompt"], prev, i - n, p_idx
        n += ph["frames"]
    last = len(phases) - 1
    return phases[last]["prompt"], None, i - n, last


def assemble(cfg, name, out_dir, frames_dir, total, exponent=None):
    # zoom-out is always the primary cut: build-out generates it forward,
    # build-in generates dive-in footage that gets reversed into the primary
    fwd = f"{name}.mp4" if cfg["build"] == "out" else f"{name}_divein.mp4"
    rev = f"{name}_divein.mp4" if cfg["build"] == "out" else f"{name}.mp4"
    """Loop crossfade, raw encode, motion interpolation, counter overlay, reverse cut."""
    K = min(cfg["loop_fade_frames"], total // 2)
    if K:
        heads = [Image.open(frames_dir / f"{i:05d}.png").convert("RGB") for i in range(K)]
        for i in range(K):
            t = total - K + i
            tail = Image.open(frames_dir / f"{t:05d}.png").convert("RGB")
            Image.blend(tail, heads[i], (i + 1) / (K + 1)).save(frames_dir / f"{t:05d}.png")
        print(f"[dive] loop crossfade over last {K} frames", flush=True)

    raw = "build/raw.mp4"
    subprocess.run([FFMPEG, "-y", "-framerate", str(cfg["fps"]),
                    "-i", "build/frames/%05d.png",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", raw],
                   cwd=out_dir, check=True, capture_output=True)

    interp = "build/interp.mp4"
    if cfg["final_fps"]:
        t0 = time.time()
        subprocess.run([FFMPEG, "-y", "-i", raw,
                        "-vf", (f"minterpolate=fps={cfg['final_fps']}:mi_mode=mci:"
                                "mc_mode=aobmc:me_mode=bidir:vsbmc=1"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", interp],
                       cwd=out_dir, check=True, capture_output=True)
        print(f"[dive] interpolated {cfg['fps']} -> {cfg['final_fps']}fps "
              f"in {time.time() - t0:.0f}s", flush=True)
    else:
        interp = raw

    final = fwd
    if exponent:
        # counter is drawn AFTER interpolation so the text stays crisp
        lbl = out_dir / "build" / "labeled"
        lbl.mkdir(exist_ok=True)
        for f in lbl.glob("*.png"):
            f.unlink()
        subprocess.run([FFMPEG, "-y", "-i", interp, "build/labeled/%05d.png"],
                       cwd=out_dir, check=True, capture_output=True)
        outs = sorted(lbl.glob("*.png"))
        n_out = len(outs)
        exps = [exponent[min(total - 1, int(j * total / n_out))] for j in range(n_out)]
        pulse_at = [j for j in range(1, n_out)
                    if int(round(exps[j])) != int(round(exps[j - 1]))]
        for j, f in enumerate(outs):
            age = next((j - p for p in reversed(pulse_at) if 0 <= j - p <= 5), None)
            draw_counter(Image.open(f).convert("RGB"), exps[j], age).save(f)
        fr = cfg["final_fps"] or cfg["fps"]
        subprocess.run([FFMPEG, "-y", "-framerate", str(fr),
                        "-i", "build/labeled/%05d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", final],
                       cwd=out_dir, check=True, capture_output=True)
        print(f"[dive] counter overlay on {n_out} frames "
              f"({len(pulse_at)} decade pulses)", flush=True)
    else:
        (out_dir / final).write_bytes((out_dir / interp).read_bytes())

    subprocess.run([FFMPEG, "-y", "-i", fwd, "-vf", "reverse",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", rev],
                   cwd=out_dir, check=True, capture_output=True)
    for label, f in (("primary (zoom-out)", f"{name}.mp4"),
                     ("alt (dive-in)", f"{name}_divein.mp4")):
        mp4 = out_dir / f
        print(f"[dive] {label}: {mp4} ({mp4.stat().st_size // 1024} KB, "
              f"{total / cfg['fps']:.1f}s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey", help="journey JSON file")
    ap.add_argument("--model", choices=sorted(MODEL_PRESETS),
                    help="model preset; overrides journey settings and suffixes the name")
    ap.add_argument("--build", choices=("in", "out"),
                    help="build direction; overrides journey format and suffixes the name")
    ap.add_argument("--frames", type=int, help="override total frame count (smoke tests)")
    ap.add_argument("--no-video", action="store_true", help="skip assembly")
    args = ap.parse_args()

    spec = json.loads(Path(args.journey).read_text())
    cfg = {**DEFAULTS, **spec.get("settings", {})}
    if args.model:
        cfg.update(MODEL_PRESETS[args.model])
    cfg["build"] = args.build or spec.get("format", {}).get("build", cfg["build"])
    zoom_sched = den_sched = exponent = loop = None
    cameos, arrivals = [], set()
    if "registers" in spec:
        phases, zoom_sched, den_sched, exponent, loop, cameos, arrivals = \
            grammar.compile_journey(spec, cfg["fps"], cfg["build"])
        if cfg["build"] == "out" and spec.get("format", {}).get("exact_loop"):
            cfg["loop_fade_frames"] = max(cfg["loop_fade_frames"], 8)
    else:
        phases = spec["phases"]
    total = args.frames or sum(p["frames"] for p in phases)
    name = spec.get("name") or Path(args.journey).stem
    if args.model:
        name = f"{name}_{args.model}"
    if args.build:
        name = f"{name}_{args.build}"

    # never overwrite a previous render: each run gets a fresh vN folder
    base = Path(__file__).resolve().parent.parent / "output" / name
    n = 1 + max([int(d.name[1:]) for d in base.glob("v[0-9]*")
                 if d.name[1:].isdigit()], default=0)
    out_dir = base / f"v{n}"
    frames_dir = out_dir / "build" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    print(f"[dive] run dir: {out_dir}", flush=True)

    print(f"[dive] {name}: {total} frames, {cfg['width']}x{cfg['height']}, "
          f"zoom {cfg['zoom_per_frame']}/frame, denoise {cfg['denoise']}, "
          f"ckpt {cfg['checkpoint']}", flush=True)

    t0 = time.time()
    img = None
    frame0 = None
    cam = None
    root = Path(__file__).resolve().parent.parent
    phase_refs = {}
    T = cfg["transition_frames"]
    in_loop_tail = lambda i: loop and i >= total - loop["frames"]
    for i in range(total):
        prompt, prev_prompt, k, p_idx = phase_info(phases, i)
        in_transition = prev_prompt is not None and k < T
        base_den = den_sched[i] if den_sched else cfg["denoise"]
        z = zoom_sched[i] if zoom_sched else cfg["zoom_per_frame"]
        seed = cfg["seed"] + i
        if img is None:
            wf = build_workflow(cfg, prompt, seed)                  # txt2img init
        else:
            drift = cfg["drift"]
            if in_loop_tail(i):   # re-center so the frame-0 composite lines up
                drift *= 1 - (i - (total - loop["frames"]) + 1) / loop["frames"]
            # periods far longer than any video: reads as one slow directional
            # wander, not an oscillation (sinusoidal wobble was jarring)
            cx = 0.5 + drift * math.sin(2 * math.pi * i / 263)
            cy = 0.5 + drift * math.sin(2 * math.pi * i / 419 + 1.7)
            boost = 0
            if in_transition:
                boost = (cfg["arrival_denoise_boost"] if p_idx in arrivals
                         else cfg["transition_denoise_boost"])
            den = min(0.85, base_den + boost)
            mask_ref = None
            if cfg["build"] == "out":
                fed, box = shrink_transform(img, z, cx, cy)
                fed = detail_boost(fed, cfg)
                if cfg["color_match"] and not in_transition and p_idx in phase_refs:
                    fed = color_match(fed, phase_refs[p_idx], cfg["color_match"])
                mask_ref = upload_image(
                    ring_mask(fed.width, fed.height, box),
                    f"zoomer_mask_{name}.png")
            else:
                fed = zoom_transform(img, z, cfg["rotate_per_frame"], cx, cy)
                fed = detail_boost(fed, cfg)
                if cfg["color_match"] and not in_transition and p_idx in phase_refs:
                    fed = color_match(fed, phase_refs[p_idx], cfg["color_match"])
                cam_pasted = False
                for c in cameos:
                    if i == c["start"]:
                        cam = {"px": c["pos"][0], "py": c["pos"][1],
                               "size": c["size"], "end": c["end"],
                               "art": load_sprite(root / c["sprite"])}
                if cam:
                    if i >= cam["end"] or cam["size"] > 0.30:
                        cam = None
                    else:
                        # world-attached: moves and grows with the zoom itself
                        cam["px"] = 0.5 + (cam["px"] - cx) * z
                        cam["py"] = 0.5 + (cam["py"] - cy) * z
                        cam["size"] *= z
                        if -0.1 < cam["px"] < 1.1 and -0.1 < cam["py"] < 1.1:
                            fed = paste_sprite(fed, *cam["art"], cam["px"],
                                               cam["py"], cam["size"])
                            cam_pasted = True
                if cam_pasted:
                    den = min(den, 0.32)   # keep the mascot's face recognizable
                if in_loop_tail(i):
                    # grow frame 0 in the center until the last frame IS the first;
                    # masked denoise pixel-locks the composite and repaints ONLY the
                    # shrinking ring around it, so surroundings morph into frame 0
                    # instead of freezing (findable-seam fix, 2026-07-26)
                    j = i - (total - loop["frames"])
                    t_ = (j + 1) / loop["frames"]
                    s = math.exp(math.log(loop["s0"]) * (1 - t_))
                    fed = loop_composite(fed, frame0, s)
                    w_, h_ = fed.size
                    sw, sh = max(2, int(w_ * s)), max(2, int(h_ * s))
                    box = ((w_ - sw) // 2, (h_ - sh) // 2, sw, sh)
                    mask_ref = upload_image(ring_mask(w_, h_, box, center_val=10),
                                            f"zoomer_mask_{name}.png")
                    den = max(den, cfg["denoise"])   # ring stays lively; center is locked
            ref = upload_image(fed, f"zoomer_feed_{name}.png")
            wf = build_workflow(cfg, prompt, seed, init_image=ref, denoise=den,
                                prev_prompt=prev_prompt if in_transition else None,
                                blend=(k + 1) / (T + 1) if in_transition else 1.0,
                                mask_image=mask_ref)
        png = run_workflow(wf)
        img = Image.open(io.BytesIO(png)).convert("RGB")
        if img.size != (cfg["width"], cfg["height"]):
            img = img.resize((cfg["width"], cfg["height"]), Image.LANCZOS)
        if cfg["build"] == "out":
            for c in cameos:
                if i == c["start"]:
                    # build-out cameo: paste once — the protected center then
                    # carries the sprite physically through every later frame
                    img = paste_sprite(img, *load_sprite(root / c["sprite"]),
                                       c["pos"][0], c["pos"][1], c["size"])
        if i == 0:
            frame0 = img.copy()
        if loop and i == total - 1:
            img = frame0.copy()                       # exact loop: last frame = first
        img.save(frames_dir / f"{i:05d}.png")
        if k == T and p_idx not in phase_refs:
            phase_refs[p_idx] = channel_stats(img)   # this phase's palette anchor
        if i % 10 == 0 or i == total - 1:
            rate = (time.time() - t0) / (i + 1)
            print(f"[dive] frame {i + 1}/{total} ({rate:.1f}s/frame, "
                  f"~{rate * (total - i - 1):.0f}s left) :: {prompt[:60]}", flush=True)

    if not args.no_video:
        show_counter = exponent is not None and not args.frames
        if show_counter and cfg["counter"] == "auto":
            exps = [r["exp"] for r in spec["registers"]]
            show_counter = all(a > b for a, b in zip(exps, exps[1:]))
        elif show_counter:
            show_counter = bool(cfg["counter"])
        assemble(cfg, name, out_dir, frames_dir, total,
                 exponent=exponent if show_counter else None)
    print(f"[dive] done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
