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
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

import figure
import grammar
import style as _style
import track

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
    "approach_cn": 0.45,  # engine-2.0 object-approach: depth-ControlNet strength (structure whisper)
    "track_cadence": 4,   # TRACKER v3: detect every Nth approach frame (locate ~2.4s/call)
    "track_model": "microsoft/Florence-2-large-ft",
    # rate at which the tracked object settles onto its run's rule-of-thirds ANCHOR (never
    # toward center — see track.step). The offset is multiplied every frame, so this compounds:
    # 0.3 snapped to center, and even 0.05 removed 76% of the off-center composition over a
    # 28-frame card (measured in v10 — every scale slid to a dead-center zoom). 0.03 toward a
    # THIRDS anchor holds the object ~0.24 off-center for the whole bar; 0 would freeze the
    # composition exactly.
    "approach_lock_ease": 0.03,
    "denoise": 0.58,
    "steps": 8,           # effective diffusion steps ≈ steps * denoise
    "cfg": 1.5,
    "sampler": "euler_ancestral",
    "scheduler": "normal",
    "fps": 12,            # raw generation rate
    "final_fps": 24,      # motion-interpolated output rate (0 = skip interpolation)
    "seed": 1234,
    # The old negative was "human face, portrait, close-up person" — all CLOSE-UP terms, which
    # did nothing about quantum_orrery's full-body haloed goddess. DreamShaper is a fantasy-
    # character fine-tune; it needs the whole-figure vocabulary pushed away, plus the regalia
    # ("halo", "crown", "robe") that summons a figure to wear it. Distant tiny figures at scale
    # are still fine — the negative is weak at cfg 2.0, and engine/figure.py judges from the
    # frame's CAPTION, which names the subject and ignores background texture.
    "negative": ("text, watermark, logo, blurry, frame, border, low quality, "
                 "person, people, human figure, standing figure, full body, woman, man, "
                 "goddess, angel, fantasy character, portrait, face, hands, anatomy, "
                 "halo, crown, robe, album cover"),
    # frame-0 lone-figure guard (see engine/figure.py): frame 0 is the only txt2img frame, so
    # the checkpoint's prior rules it and the feedback chain then locks it in for the whole
    # render. Catch it in ~20s instead of discovering it an hour later.
    "figure_guard": True,
    "figure_retries": 4,      # seed re-rolls before giving up on frame 0
    # (detection is caption-based, not area-based: a caption names what the image is ABOUT, so
    #  a featured individual is named while distant texture figures are not — see figure.py)
    "figure_watch": 28,       # also check every Nth frame mid-render (0 = off); warns only
    # anti-collapse re-texturing of each fed-back frame
    "sharpen": 1.35,
    "contrast": 1.04,
    "saturation": 1.03,
    "noise": 0.05,
    # phase transitions: prompt blending + extra denoise so worlds dissolve, not switch
    # (transition/seam/anacrusis frame counts are MUSICAL geometry tuned at 7 frames-per-beat;
    #  cfg-time scaling below re-derives them for a journey's own format.frames_per_beat)
    "transition_frames": 6,
    "anacrusis_frames": 2,              # pickup window before each downbeat (~a sixteenth)
    "transition_denoise_boost": 0.06,   # beat changes within a register: gentle
    "arrival_denoise_boost": 0.18,      # register boundaries: strong repaint so
                                        # palettes can actually flip between worlds
    "seam_morph_frames": 12,            # a SEAM morph = the arrival boost held for MORE
                                        # frames (not a harder per-frame change) — duration
                                        # carries the bigger semantic jump (Phil 2026-07-31)
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


CN_DEPTH = "controlnet-depth-sdxl.safetensors"   # object-approach structural guidance

# frame-0-only negatives (2026-08-02): the txt2img frame fights three close-up pressures at once
# (the 9:16 portrait prior, the deck's gloss vocabulary, concrete nouns). These push back on the
# framing WITHOUT touching the look. Never applied to feedback frames — mid-dive frames are
# SUPPOSED to be close-ups.
FRAME0_NEG_EXTRA = ("close-up, macro, product shot, tabletop, still life, "
                    "shallow depth of field, bokeh")

# IP-Adapter loop homing (2026-08-02, validated in seam_tail_ab on dollhouse/snowfall/copper_rain):
# frame 0's IMAGE conditions the tail's generation, so the WORLD converges on home while every
# pixel is freshly rendered — replaces the gap-scaled 0.82 pixel morph (a fading photograph on
# far-world gaps, the mechanism Phil reverted in July).
IPA_PRESET = "PLUS (high strength)"              # ip-adapter-plus_sdxl_vit-h + CLIP-ViT-H


def clean_box(b, min_side=0.06, max_span=0.9, max_aspect=6.0, min_area=0.01):
    """Sanity-filter a detector box before it may SEED a point-track run — reject the garbage
    Florence returns on our scenes (edge slivers, top-of-frame horizon strips, full-span masks,
    dust-mote specks). Only a clean, plausibly-object-shaped box is trusted to seed the point."""
    w, h = b["w"], b["h"]
    if w < min_side or h < min_side:      return False   # sliver / speck
    if w > max_span and h > max_span:     return False   # whole-frame degenerate mask
    if w * h < min_area:                  return False   # too tiny to be the target
    ar = w / h if h else 99.0
    if ar > max_aspect or ar < 1 / max_aspect:  return False   # strip (rivulet / horizon line)
    return True


def pick_depth_preproc():
    """Resolve a depth-map preprocessor node name from the running ComfyUI (aux node names vary)."""
    try:
        info = requests.get(f"{COMFY}/object_info", timeout=10).json()
    except Exception:
        return None
    for cand in ("DepthAnythingV2Preprocessor", "DepthAnythingPreprocessor",
                 "MiDaS-DepthMapPreprocessor", "Zoe-DepthMapPreprocessor"):
        if cand in info:
            return cand
    return None


def build_workflow(cfg, prompt, seed, init_image=None, denoise=None,
                   prev_prompt=None, blend=1.0, mask_image=None,
                   ctrl_image=None, cn_strength=0.0, depth_preproc=None,
                   ipa_image=None, ipa_weight=0.0, neg_extra=None):
    """ComfyUI API-format workflow. txt2img when init_image is None, else img2img.
    When prev_prompt is given, positive conditioning is a weighted average of the old
    and new prompts (blend = weight of the NEW prompt). When ctrl_image + cn_strength are
    given, a depth ControlNet steers structure onto it (object-approach: hold the target's
    identity as it grows while the pixels are still fully regenerated — NOT a paste).
    When ipa_image + ipa_weight are given, that image conditions the MODEL via IP-Adapter
    (loop homing: pull the generation toward frame 0's world, not its pixels).
    neg_extra appends to the negative for THIS call only (frame-0 anti-close-up terms)."""
    wf = {
        "ckpt": {"class_type": "CheckpointLoaderSimple",
                 "inputs": {"ckpt_name": cfg["checkpoint"]}},
        "pos": {"class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["ckpt", 1]}},
        "neg": {"class_type": "CLIPTextEncode",
                "inputs": {"text": cfg["negative"] + (", " + neg_extra if neg_extra else ""),
                           "clip": ["ckpt", 1]}},
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
    negative = ["neg", 0]
    if ctrl_image and cn_strength > 0:
        wf["cnet"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": CN_DEPTH}}
        wf["cimg"] = {"class_type": "LoadImage", "inputs": {"image": ctrl_image}}
        control_img = ["cimg", 0]
        if depth_preproc:
            wf["cprep"] = {"class_type": depth_preproc,
                           "inputs": {"image": ["cimg", 0],
                                      "resolution": cfg.get("cn_resolution", 512)}}
            control_img = ["cprep", 0]
        wf["cnapply"] = {"class_type": "ControlNetApplyAdvanced",
                         "inputs": {"positive": positive, "negative": negative,
                                    "control_net": ["cnet", 0], "image": control_img,
                                    "strength": round(cn_strength, 3),
                                    "start_percent": 0.0, "end_percent": 1.0}}
        positive, negative = ["cnapply", 0], ["cnapply", 1]
    model_ref = ["ckpt", 0]
    if ipa_image and ipa_weight > 0.01:
        wf["ipa_loader"] = {"class_type": "IPAdapterUnifiedLoader",
                            "inputs": {"model": ["ckpt", 0], "preset": IPA_PRESET}}
        wf["ipa_img"] = {"class_type": "LoadImage", "inputs": {"image": ipa_image}}
        wf["ipa"] = {"class_type": "IPAdapterAdvanced",
                     "inputs": {"model": ["ipa_loader", 0], "ipadapter": ["ipa_loader", 1],
                                "image": ["ipa_img", 0], "weight": round(float(ipa_weight), 3),
                                "weight_type": "ease in-out", "combine_embeds": "concat",
                                "start_at": 0.0, "end_at": 1.0, "embeds_scaling": "V only"}}
        model_ref = ["ipa", 0]
    wf["sample"] = {"class_type": "KSampler",
                    "inputs": {"seed": seed, "steps": cfg["steps"], "cfg": cfg["cfg"],
                               "sampler_name": cfg["sampler"],
                               "scheduler": cfg["scheduler"],
                               "denoise": (denoise if denoise is not None else 1.0),
                               "model": model_ref, "positive": positive,
                               "negative": negative, "latent_image": ["latent", 0]}}
    return wf


def run_workflow(wf, timeout=900):
    """Queue a workflow, wait for completion, return the output image bytes. Resilient to transient
    ComfyUI connection hiccups (a single /history timeout must NOT kill a 200-frame render).

    900s, not 300s: a normal frame is ~15s, but when VRAM is tight ComfyUI silently switches to
    per-step CPU<->GPU weight swapping and the SAME frame takes 310s. At 300s that killed two
    renders outright (2026-07-31) — and the work wasn't even lost, the job completed at 310s with
    nobody listening. A slow frame must never cost an hour's render; a genuinely hung ComfyUI is
    rare and 15 minutes is an acceptable price for noticing it."""
    pid = None
    for attempt in range(5):
        try:
            r = requests.post(f"{COMFY}/prompt", json={"prompt": wf}, timeout=30)
            r.raise_for_status()
            pid = r.json()["prompt_id"]
            break
        except requests.exceptions.RequestException:
            if attempt == 4:
                raise
            time.sleep(3)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            h = requests.get(f"{COMFY}/history/{pid}", timeout=30).json()
        except requests.exceptions.RequestException:
            time.sleep(1.0)      # transient hiccup — retry, don't crash the render
            continue
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
    A drifting center breaks radial-symmetry lock (concentric-ring artifacts).
    The crop window clamps to the frame via track.crop_center — the SAME helper the tracker
    propagates points through, so the assumed and actual transforms can never diverge (the
    v6 bug: it advanced its track with the unclamped aim and drifted off the object)."""
    w, h = img.size
    if rotate_deg:
        img = img.rotate(rotate_deg, resample=Image.BICUBIC, expand=False)
    ecx, ecy = track.crop_center(zoom, cx, cy)
    cw, ch = w / zoom, h / zoom
    left, top = ecx * w - cw / 2, ecy * h - ch / 2
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


def frame_gap(a, b):
    """Mean absolute per-channel difference between two frames (0–255) — the seam morph scales
    its strength to this gap between the arriving dive and frame 0."""
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


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


def register_frame_counts(spec, fps):
    """Per-CARD (register) frame counts in render order (render_start-rotated) — the same
    math grammar and the music grid use. Card boundaries = cumulative sums of these."""
    regs = spec["registers"]
    rs = spec.get("render_start")
    names = [r.get("name") for r in regs]
    if rs in names:
        k = names.index(rs)
        regs = regs[k:] + regs[:k]
    fmt = spec.get("format", {})
    return [grammar._frames(r, fmt, fps) for r in regs]


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
    ap.add_argument("--style", help="style deck name (styles/deck.json); overrides the journey's "
                    "chosen style — for A/B look-tests")
    ap.add_argument("--build", choices=("in", "out"),
                    help="build direction; overrides journey format and suffixes the name")
    ap.add_argument("--frames", type=int, help="override total frame count (smoke tests)")
    ap.add_argument("--plain", action="store_true",
                    help="pure feedback zoom — no tracking, no depth-CN (A/B vs the engine-1 look)")
    ap.add_argument("--classic-tail", action="store_true",
                    help="loop tail uses the pre-IPA gap-scaled pixel morph (A/B vs IPA homing)")
    ap.add_argument("--resolve", action="store_true",
                    help="RESOLVE-ON-APPROACH: field-card arrivals get animated procedural "
                         "depth scaffolds (engine/scaffold.py) so the new realm resolves out "
                         "of the old texture as countless growing instances")
    ap.add_argument("--cn", type=float, metavar="STRENGTH",
                    help="override depth-ControlNet strength; --cn 0 disables the CN but KEEPS "
                         "tracking/composition (the clean A/B for 'is the CN hurting the look?'). "
                         "Suffixes the run name so the two variants don't share a vN sequence.")
    ap.add_argument("--allow-figures", action="store_true",
                    help="disable the frame-0 lone-figure gate (engine/figure.py). Only for\na journey that WANTS a person on screen.")
    ap.add_argument("--no-video", action="store_true", help="skip assembly")
    ap.add_argument("--resume", action="store_true",
                    help="continue the newest vN from its last saved frame (feedback chain: only "
                         "the last frame is needed) — same journey/settings, e.g. after a crash")
    ap.add_argument("--seed", type=int,
                    help="override the base seed (per-frame seed = base + i). A re-render keeps "
                         "the same draw unless the base changes — pass a new one to explore, "
                         "omit to reproduce (e.g. same seed through an engine change)")
    ap.add_argument("--from-card", type=int, metavar="K",
                    help="partial re-render: copy the frames of cards 0..K-1 from an existing "
                         "render into a FRESH vN (source untouched) and regenerate from card K's "
                         "first frame on. Card boundaries only — the tracker, palette anchors and "
                         "anchor rotation all re-derive cleanly there. Composes with --seed (new "
                         "draw for the regenerated frames) and with an edited journey whose cards "
                         "before K kept their durs.")
    ap.add_argument("--src-version", metavar="vN",
                    help="with --from-card: take the prefix frames from this version "
                         "(default: newest vN with enough frames)")
    args = ap.parse_args()

    spec = json.loads(Path(args.journey).read_text())
    cfg = {**DEFAULTS, **spec.get("settings", {})}
    # TEMPO (2026-08-13): the beat grid is format.frames_per_beat (7 = 103bpm; bpm = 720/fpb
    # at 12fps raw). The morph geometry above is MUSICAL, tuned at fpb 7 — scale it with the
    # journey's own beat so a 120bpm journey keeps the same fraction-of-a-bar everywhere.
    # A journey's explicit settings override wins unscaled (a conscious per-journey choice).
    _fpb = spec.get("format", {}).get("frames_per_beat", 7)
    if _fpb != 7 and any(r.get("dur") is not None for r in spec.get("registers", [])):
        _s = _fpb / 7.0
        _ov = spec.get("settings", {})
        if "transition_frames" not in _ov:
            cfg["transition_frames"] = max(2, round(DEFAULTS["transition_frames"] * _s))
        if "seam_morph_frames" not in _ov:
            cfg["seam_morph_frames"] = max(cfg["transition_frames"] + 1,
                                           round(DEFAULTS["seam_morph_frames"] * _s))
        if "anacrusis_frames" not in _ov:
            cfg["anacrusis_frames"] = max(1, round(DEFAULTS["anacrusis_frames"] * _s))
        print(f"[dive] tempo: fpb {_fpb} ({720 / _fpb:.0f}bpm) -> transition "
              f"{cfg['transition_frames']}f, seam {cfg['seam_morph_frames']}f, "
              f"anacrusis {cfg['anacrusis_frames']}f", flush=True)
    # STYLE (Layer 2): resolve the look from the deck and inject it as the style_suffix the
    # grammar reads. The deck may also RECOMMEND a checkpoint when --model isn't passed.
    sfx, deck_model, style_name = _style.resolve(spec, args.style)
    spec["style_suffix"] = sfx
    # HOUSE DEFAULT = ds (DreamShaper). Phil 2026-07-31: "dreamshaper really has made better
    # videos" — turbo only on an explicit --model turbo. Legacy journeys carry no `style`, so
    # the deck recommends nothing and cfg would otherwise keep DEFAULTS' turbo checkpoint
    # (silently, since old runs always passed --model explicitly). Routing the fallback through
    # MODEL_PRESETS also brings ds's required sampler (dpmpp_sde/karras), not just its ckpt.
    eff_model = args.model or deck_model or "ds"
    cfg.update(MODEL_PRESETS[eff_model])
    if style_name:
        print(f"[style] {style_name}  ->  {sfx}", flush=True)
    cfg["build"] = args.build or spec.get("format", {}).get("build", cfg["build"])
    if args.seed is not None:
        cfg["seed"] = args.seed
    zoom_sched = den_sched = exponent = loop = None
    cameos, arrivals, approach, seam_arrivals = [], set(), [], set()
    if "registers" in spec:
        (phases, zoom_sched, den_sched, exponent, loop, cameos, arrivals, approach,
         seam_arrivals) = grammar.compile_journey(spec, cfg["fps"], cfg["build"])
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
    if args.plain:
        approach = []
        name = f"{name}_plain"
    if args.cn is not None:
        cfg["approach_cn"] = args.cn
        name = f"{name}_cn{args.cn:g}".replace(".", "")
    # build-out has no txt2img frame 0 to gate, and --resume starts mid-chain (frame 0 already
    # judged), so the gate only applies to a fresh build-IN render.
    img_guard = cfg["figure_guard"] and not args.allow_figures and cfg["build"] != "out"

    base = Path(__file__).resolve().parent.parent / "output" / name
    start_i = 0
    start_run_idx = 0     # approach runs already consumed by a copied prefix (--from-card)
    run_extra = {}
    img = frame0 = None
    out_dir = frames_dir = None
    if args.from_card is not None:
        # PARTIAL RE-RENDER (Level 1, 2026-08-01): repair_seam's pattern generalized from "the
        # seam" to "any card boundary". The feedback chain's only heavy state is the previous
        # frame; every schedule is a pure function of (spec, frame index); and at a CARD
        # boundary the mid-run state that is NOT pure (tracker lock, palette phase_refs)
        # re-initializes naturally. Non-destructive: fresh vN, prefix frames hard-copied.
        if args.resume:
            sys.exit("[dive] --from-card and --resume are mutually exclusive")
        if "registers" not in spec:
            sys.exit("[dive] --from-card needs a register journey (phases-schema has no cards)")
        # CARD = a journey register, NOT a compiled phase (grammar splits each register into
        # arrival/look/plunge sub-phases).
        _cf = register_frame_counts(spec, cfg["fps"])
        if not (0 < args.from_card < len(_cf)):
            sys.exit(f"[dive] --from-card must be 1..{len(_cf) - 1} (0 = just render fresh)")
        N = sum(_cf[:args.from_card])
        if loop and N >= total - loop["frames"]:
            sys.exit("[dive] that boundary is inside the loop tail — use scripts/repair_seam.py")
        for c in cameos:
            if c["start"] < N < c["end"]:
                sys.exit(f"[dive] frame {N} is inside the cameo window "
                         f"{c['start']}..{c['end']} — the sprite's propagated position can't be "
                         f"reconstructed mid-window; pick a card outside it")
        vs = sorted([d for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                    key=lambda d: int(d.name[1:]))
        if args.src_version:
            vs = [d for d in vs if d.name == args.src_version]
        src = next((d for d in reversed(vs)
                    if len(list((d / "build" / "frames").glob("*.png"))) >= N), None)
        if not src:
            sys.exit(f"[dive] no version under {base} has the {N} prefix frames"
                     + (f" (asked for {args.src_version})" if args.src_version else ""))
        n = 1 + max([int(d.name[1:]) for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                    default=0)
        out_dir = base / f"v{n}"
        frames_dir = out_dir / "build" / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for i in range(N):
            shutil.copy(src / "build" / "frames" / f"{i:05d}.png", frames_dir / f"{i:05d}.png")
        start_i = N
        img = Image.open(frames_dir / f"{N - 1:05d}.png").convert("RGB")
        frame0 = Image.open(frames_dir / "00000.png").convert("RGB")
        for c in cameos:          # cameos fully inside the prefix are already in those frames
            if c["end"] <= N:
                c["_done"] = True
        # the frozen rule-of-thirds anchor rotates per approach run — count the runs the
        # prefix consumed so the regenerated cards continue the rotation, not restart it
        _prev_ap = None
        for _a in approach[:N]:
            if _a is not None and _a is not _prev_ap:
                start_run_idx += 1
            _prev_ap = _a
        run_extra = {"from_card": args.from_card, "from_frame": N, "prefix_src": src.name}
        print(f"[dive] FROM CARD {args.from_card} (frame {N}/{total}) — prefix from {src.name}, "
              f"regenerating {total - N} frames into {out_dir.name}", flush=True)
    elif args.resume:   # continue the newest vN from its last saved frame (only the last frame is needed)
        vs = sorted([d for d in base.glob("v[0-9]*") if d.name[1:].isdigit()], key=lambda d: int(d.name[1:]))
        if vs and (vs[-1] / "build" / "frames").exists():
            frames_dir = vs[-1] / "build" / "frames"
            existing = sorted(frames_dir.glob("*.png"))
            if existing:
                out_dir = vs[-1]; start_i = len(existing)
                img = Image.open(existing[-1]).convert("RGB")
                frame0 = Image.open(frames_dir / "00000.png").convert("RGB")
                print(f"[dive] RESUME {out_dir.name} from frame {start_i}/{total}", flush=True)
    if start_i == 0:   # fresh vN (never overwrite a previous render)
        n = 1 + max([int(d.name[1:]) for d in base.glob("v[0-9]*") if d.name[1:].isdigit()], default=0)
        out_dir = base / f"v{n}"
        frames_dir = out_dir / "build" / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
    print(f"[dive] run dir: {out_dir}", flush=True)

    print(f"[dive] {name}: {total} frames, {cfg['width']}x{cfg['height']}, "
          f"zoom {cfg['zoom_per_frame']}/frame, denoise {cfg['denoise']}, "
          f"MODEL {eff_model} ({cfg['checkpoint']})", flush=True)
    # provenance manifest — the run dir no longer carries a _ds/_turbo suffix (the style deck
    # picks the model), so record what actually produced these frames.
    (out_dir / "run.json").write_text(json.dumps({
        "journey": args.journey, "name": name, "model": eff_model,
        "checkpoint": cfg["checkpoint"], "style": style_name, "frames": total,
        "fps": cfg["fps"], "seed": cfg["seed"],
        # per-CARD (register) frame counts: lets a future --from-card verify its prefix
        # still aligns after a journey edit
        "card_frames": (register_frame_counts(spec, cfg["fps"]) if "registers" in spec
                        else [p["frames"] for p in phases]),
        **run_extra,
    }, indent=2))

    t0 = time.time()
    # img / frame0 already set above (None for a fresh run, loaded frames for --resume)
    cam = None
    root = Path(__file__).resolve().parent.parent
    phase_refs = {}
    T = cfg["transition_frames"]
    in_loop_tail = lambda i: loop and i >= total - loop["frames"]
    # RESOLVE-ON-APPROACH (2026-08-14, Phil's microscope grammar): a realm shift is the old
    # texture RESOLVING into countless tiny instances of the new realm. During tagged arrival
    # windows the depth-CN is driven by an animated procedural scaffold (instances placed in
    # world space, projected through this render's own zoom + drift, with depth-parallax) —
    # composition imposed, pixels still owned by the feedback chain + prompt. Single-object
    # approaches keep the tracker; seam arrivals keep the seam treatment; cameo cards resolve
    # only through their arrival (the paste window must stay clean).
    resolve_windows = []
    if getattr(args, "resolve", False) and "registers" in spec and cfg["build"] != "out":
        import zlib as _zlib
        import scaffold as _scaffold
        _regs = spec["registers"]
        _names = [r["name"] for r in _regs]
        _rs = spec.get("render_start")
        _rot = _names.index(_rs) if _rs in _names else 0
        _order = _regs[_rot:] + _regs[:_rot]
        _cfr = register_frame_counts(spec, cfg["fps"])
        _acc = 0
        for _k, _reg in enumerate(_order):
            _F = _cfr[_k]
            _S = _acc
            _acc += _F
            _rv = _reg.get("resolve")
            if _k == 0 or _rv is False or _order[_k - 1].get("kind") == "seam":
                continue
            _fa = max(2, round(_F * 0.25))
            _post = 0 if _reg.get("cameo") else min(10, _F - _fa - 2)
            _w0, _w1 = _S - 6, _S + _fa + _post
            if loop:
                _w1 = min(_w1, total - loop["frames"])
            if _w1 - _w0 < 6:
                continue
            _rv = _rv if isinstance(_rv, dict) else {}
            _mode = _rv.get("mode") or _scaffold.mode_for_band(
                _scaffold.band_of(_reg.get("exp", 0)))
            _dflt = {"sea": (1.3, 0.3), "lattice": (1.0, 0.4),
                     "surface": (0.9, 0.8), "web": (1.0, 0.5)}[_mode]
            _zw = [zoom_sched[x] for x in range(_w0, _w1)]
            _aw = [(0.5 + cfg["drift"] * math.sin(2 * math.pi * x / 263),
                    0.5 + cfg["drift"] * math.sin(2 * math.pi * x / 419 + 1.7))
                   for x in range(_w0, _w1)]
            _res = _scaffold.Resolver(
                _mode, _zw, _aw,
                seed=_zlib.crc32(f"{name}:{_reg.get('name')}".encode()),
                density=_rv.get("density", _dflt[0]), size=_rv.get("size", _dflt[1]),
                variant=_rv.get("variant"))
            resolve_windows.append({"w0": _w0, "w1": _w1, "res": _res, "pre": 6,
                                    "card": _reg.get("name"), "mode": _mode})
        if resolve_windows:
            print("[dive] RESOLVE ON — " + ", ".join(
                f"{w['card']}({w['mode']})[{w['w0']}..{w['w1'] - 1}]"
                for w in resolve_windows), flush=True)
    # TRACKER v3 (2026-07-31, PLAN "TRACKER v3"): two-stage point→object tracking with EXACT
    # geometry propagation (engine/track.py). Emergence point committed per run; detect.locate
    # tries at a low cadence; the first confident lock hands off seamlessly (the aim was already
    # heading somewhere — a lock just moves the destination); between detections the track rides
    # the known zoom geometry, so missed/garbage detections can't yank the camera.
    _depth = None
    _trk = None
    # rotates each approach run's preferred rule-of-thirds corner; a --from-card prefix
    # already consumed start_run_idx runs, so the continuation keeps the rotation phase
    _run_idx = start_run_idx - 1
    if any(approach):
        _depth = pick_depth_preproc()
        print(f"[dive] TRACKER v3 ON ({sum(a is not None for a in approach)} approach frames; "
              f"detect every {cfg['track_cadence']}, {cfg['track_model'].split('/')[-1]}); "
              f"depth preproc={_depth}", flush=True)
    # per-frame aim/track debug log — the overlay + offline replay read this
    # (scripts/track_lab.py overlay). Row "i" = the frame the state was OBSERVED in (i-1: the
    # tracker sees the previous frame and aims the transform that generates frame i).
    tlog = open(out_dir / "build" / "track.jsonl", "a" if start_i else "w")
    # start frames of arrival phases (every register morph gets the anacrusis; seam arrivals
    # additionally hold their boost for seam_morph_frames)
    seam_starts, arrival_starts = set(), set()
    _acc = 0
    for _pi, _ph in enumerate(phases):
        if _pi in seam_arrivals:
            seam_starts.add(_acc)
        if _pi in arrivals:
            arrival_starts.add(_acc)
        _acc += _ph["frames"]
    for i in range(start_i, total):
        prompt, prev_prompt, k, p_idx = phase_info(phases, i)
        in_transition = prev_prompt is not None and k < T
        base_den = den_sched[i] if den_sched else cfg["denoise"]
        z = zoom_sched[i] if zoom_sched else cfg["zoom_per_frame"]
        seed = cfg["seed"] + i
        if img is None:
            # frame-0 ESTABLISH override (2026-08-02): the schedule's travel prompt names the
            # card's TARGET, and in txt2img SDXL composes a product-shot close-up around it
            # (all 5 renders of 08-01/02 opened close; seed-held ablations confirmed). Frame 0
            # renders the scene WIDE with no target + anti-close-up negatives instead; the
            # feedback chain inherits the wide framing from frame 1 on.
            f0_prompt = grammar.establish_prompt(spec) if cfg["build"] != "out" else prompt
            if f0_prompt != prompt:
                print(f"[dive] frame-0 establish: {f0_prompt[:110]}", flush=True)
            wf = build_workflow(cfg, f0_prompt, seed, neg_extra=FRAME0_NEG_EXTRA)  # txt2img init
        else:
            drift = cfg["drift"]
            if in_loop_tail(i):   # re-center so the frame-0 composite lines up
                drift *= 1 - (i - (total - loop["frames"]) + 1) / loop["frames"]
            # periods far longer than any video: reads as one slow directional
            # wander, not an oscillation (sinusoidal wobble was jarring)
            cx = 0.5 + drift * math.sin(2 * math.pi * i / 263)
            cy = 0.5 + drift * math.sin(2 * math.pi * i / 419 + 1.7)
            # TRACKER v3: the tracker owns the aim on approach frames (not the loop tail — the
            # loop mechanism owns that). The scheduled ×10 arrive-look-plunge zoom (zoom_sched)
            # grows the target; the tracker only steers WHERE.
            ap = approach[i] if i < len(approach) else None
            approaching = bool(ap) and not in_loop_tail(i) and cfg["build"] != "out"
            rwin = next((w for w in resolve_windows if w["w0"] <= i < w["w1"]), None) \
                if resolve_windows else None
            if rwin:
                approaching = False       # the field is still resolving — drift aim, no lock
            ev = None
            if approaching:
                if _trk is None or _trk.ap is not ap:
                    _run_idx += 1
                    _trk = track.Tracker(ap, cfg["width"], cfg["height"],
                                         rot=cfg["rotate_per_frame"],
                                         cadence=cfg["track_cadence"],
                                         ease=cfg["approach_lock_ease"],
                                         model=cfg["track_model"])
                if _trk.need_repick:
                    _trk.begin(img, seed=i, run_idx=_run_idx)
                ev = _trk.maybe_observe(img)
                row = {"i": i - 1, "mode": "track", "z": round(z, 4), **_trk.log_row()}
                if ev:
                    row["event"] = ev
                cx, cy = _trk.step(z)
            else:
                _trk = None
                row = {"i": i - 1, "mode": "tail" if in_loop_tail(i) else "drift",
                       "z": round(z, 4)}
            row["aim"] = [round(cx, 4), round(cy, 4)]
            tlog.write(json.dumps(row) + "\n")
            tlog.flush()
            # MORPHS (Phil 2026-07-31, final shape): every register morph keeps engine-1's
            # per-frame intensity (travel + arrival boost = 0.58). A SEAM differs only by MORE
            # FRAMES — the boost holds for seam_morph_frames (12) instead of the normal 6-frame
            # crossfade — never by a harder per-frame change ("more frames rather than a bigger
            # change within a frame ... looks better"). And EVERY morph gets the musical
            # ANACRUSIS: the last ~sixteenth (2 frames at 7fpb) before the boundary rises
            # toward the coming boost, so the old world shimmers in anticipation and the flip
            # peaks ON the downbeat — exactly the track's pickup-into-strong-beat.
            boost = 0
            if in_transition:
                boost = (cfg["arrival_denoise_boost"] if p_idx in arrivals
                         else cfg["transition_denoise_boost"])
            if any(0 <= i - b < cfg["seam_morph_frames"] for b in seam_starts):
                boost = max(boost, cfg["arrival_denoise_boost"])
            den = min(0.85, base_den + boost)
            anac = cfg["anacrusis_frames"]
            dist = next((s - i for s in arrival_starts if 0 < s - i <= anac), None)
            if dist is not None:
                # fpb 7 keeps the hand-tuned 0.7/0.4 curve exactly; other beats get the
                # same linear rise generalized to their own pickup length
                fac = ((0.7 if dist == 1 else 0.4) if anac == 2
                       else (anac + 1 - dist) / (anac + 1))
                den = min(0.85, max(den, base_den + cfg["arrival_denoise_boost"] * fac))
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
                    # init-once window (not `i == start`): frame 0 is txt2img and never reaches
                    # this branch, so a card-0 cameo (start=0) silently NEVER pasted — dollhouse's
                    # cameo is missing for this reason. Window semantics paste it from frame 1,
                    # and also survive --resume landing mid-window.
                    if not c.get("_done") and c["start"] <= i < c["end"]:
                        c["_done"] = True
                        cam = {"px": c["pos"][0], "py": c["pos"][1],
                               "size": c["size"], "end": c["end"],
                               "art": load_sprite(root / c["sprite"])}
                if cam:
                    if i >= cam["end"] or cam["size"] > 0.30:
                        cam = None
                    else:
                        # world-attached: moves and grows with the zoom itself (exact
                        # propagation — crop clamp + rotation, same math as the tracker)
                        cam["px"], cam["py"] = track.propagate(
                            cam["px"], cam["py"], z, cfg["rotate_per_frame"], cx, cy,
                            cfg["width"], cfg["height"])
                        cam["size"] *= z
                        if -0.1 < cam["px"] < 1.1 and -0.1 < cam["py"] < 1.1:
                            fed = paste_sprite(fed, *cam["art"], cam["px"],
                                               cam["py"], cam["size"])
                            cam_pasted = True
                if cam_pasted:
                    den = min(den, 0.32)   # keep the mascot's face recognizable
            tail_ipa_w, tail_ctl, tail_cn = 0.0, None, 0.0
            if in_loop_tail(i):
                j = i - (total - loop["frames"])
                L_tail = loop["frames"]
                if args.classic_tail:
                    # CLASSIC SEAM (2026-07-29, A/B only): blend the feedback toward frame 0
                    # with a strength AUTO-SCALED to the gap. On far-world gaps this hits 0.82
                    # = a fading-photograph cross-dissolve (Phil reverted it on dollhouse and
                    # snowfall) — kept behind --classic-tail for comparison.
                    mstart = L_tail - loop["morph_frames"]
                    if j >= mstart:
                        if loop.get("morph_strength") is None:
                            gap = frame_gap(fed, frame0)
                            loop["morph_strength"] = max(0.0, min(0.82, (gap - 15) / 55))
                        m = (j - mstart + 1) / loop["morph_frames"]
                        if loop["morph_strength"] > 0.01:
                            fed = Image.blend(fed, frame0, loop["morph_strength"] * m)
                else:
                    # IPA HOMING (2026-08-02, "ipacn" — won the seam_tail_ab A/B on all three
                    # cases incl. both blendcn-reverted hard ones): frame 0's IMAGE conditions
                    # the generation with weight ramping in, so the WORLD converges while every
                    # frame is freshly rendered and still zooming. Depth-CN from frame 0 aligns
                    # the landing composition over the morph window; a small FIXED pixel blend
                    # (never gap-scaled, max 0.35) seals the final frames. Palette pull after
                    # generation is unchanged below.
                    t_home = (j + 1) / L_tail
                    if loop.get("_home_ref") is None:
                        loop["_home_ref"] = upload_image(frame0, f"zoomer_loop_home_{name}.png")
                    tail_ipa_w = 0.95 * t_home ** 1.5
                    mstart = L_tail - loop["morph_frames"]
                    if j >= mstart:
                        m = (j - mstart + 1) / loop["morph_frames"]
                        tail_ctl, tail_cn = loop["_home_ref"], 0.2 + 0.6 * m
                    if j >= L_tail - 6:
                        fed = Image.blend(fed, frame0, 0.35 * (j - (L_tail - 6) + 1) / 6)
            res_ctl, res_cn = None, 0.0
            if rwin and not in_loop_tail(i):
                _j = i - rwin["w0"]
                _n = rwin["w1"] - rwin["w0"]
                res_ctl = upload_image(rwin["res"].frame_image(_j),
                                       f"zoomer_resolve_{name}.png")
                if _j < rwin["pre"]:
                    res_cn = 0.20 * (_j + 1) / rwin["pre"]
                else:
                    _t = (_j - rwin["pre"]) / max(1, _n - rwin["pre"])
                    res_cn = 0.6 * min(1.0, 0.35 + 1.3 * _t)
                    if _j >= _n - 2:
                        res_cn *= 0.6     # handoff taper into normal travel
            ref = upload_image(fed, f"zoomer_feed_{name}.png")
            wf = build_workflow(cfg, prompt, seed, init_image=ref, denoise=den,
                                prev_prompt=prev_prompt if in_transition else None,
                                blend=(k + 1) / (T + 1) if in_transition else 1.0,
                                mask_image=mask_ref,
                                # object-approach: depth-CN from the (zoomed) feedback holds the
                                # target's identity as it grows while pixels regenerate (not a
                                # paste). In the loop tail the SAME channel instead carries
                                # frame 0's depth (landing alignment) — never both at once.
                                ctrl_image=res_ctl or (ref if approaching else tail_ctl),
                                cn_strength=res_cn if res_ctl
                                else (cfg["approach_cn"] if approaching else tail_cn),
                                depth_preproc=None if res_ctl else _depth,
                                ipa_image=loop.get("_home_ref") if tail_ipa_w > 0.01 else None,
                                ipa_weight=tail_ipa_w)
        png = run_workflow(wf)
        img = Image.open(io.BytesIO(png)).convert("RGB")
        if img.size != (cfg["width"], cfg["height"]):
            img = img.resize((cfg["width"], cfg["height"]), Image.LANCZOS)
        # ── frame-0 lone-figure gate ──────────────────────────────────────────────────────
        # Only frame 0 is txt2img, so this is the one frame the checkpoint's prior can hijack
        # (quantum_orrery -> a haloed goddess), and the feedback chain then carries it through
        # every later frame. Re-roll the seed here for ~20s rather than find out in an hour.
        if i == 0 and img_guard:
            for attempt in range(1, cfg["figure_retries"] + 1):
                hit = figure.find(img, model=cfg.get("track_model"))
                if not hit:
                    break
                print(f"[dive] FIGURE on frame 0 ({figure.describe(hit)}) — "
                      f"re-rolling seed, attempt {attempt}/{cfg['figure_retries']}", flush=True)
                seed += 9973                       # a big coprime stride: a genuinely new draw
                png = run_workflow(build_workflow(cfg, f0_prompt, seed,
                                                  neg_extra=FRAME0_NEG_EXTRA))
                img = Image.open(io.BytesIO(png)).convert("RGB")
                if img.size != (cfg["width"], cfg["height"]):
                    img = img.resize((cfg["width"], cfg["height"]), Image.LANCZOS)
            else:
                if figure.find(img, model=cfg.get("track_model")):
                    sys.exit(
                        f"[dive] ABORT: frame 0 keeps rendering a lone figure after "
                        f"{cfg['figure_retries']} seeds. This is a PROMPT problem, not luck — "
                        f"fix the render_start card (drop halo/gilded/regalia words, name a "
                        f"concrete object) or pick a different render_start. "
                        f"Re-run with --allow-figures to override.")
        # mid-render watch: cheap, and a figure can still emerge at a later card's arrival
        elif img_guard and cfg["figure_watch"] and i and i % cfg["figure_watch"] == 0:
            hit = figure.find(img, model=cfg.get("track_model"))
            if hit:
                print(f"[dive] ⚠ figure at frame {i}: {figure.describe(hit)}", flush=True)
        if cfg["build"] == "out":
            for c in cameos:
                if i == c["start"]:
                    # build-out cameo: paste once — the protected center then
                    # carries the sprite physically through every later frame
                    img = paste_sprite(img, *load_sprite(root / c["sprite"]),
                                       c["pos"][0], c["pos"][1], c["size"])
        if loop and frame0 is not None and in_loop_tail(i):
            # warm the palette toward frame 0 across the tail (the missing last→first blend)
            j = i - (total - loop["frames"])
            img = color_match(img, channel_stats(frame0), min(0.85, 0.9 * (j + 1) / loop["frames"]))
        if i == 0:
            frame0 = img.copy()
        # (no hard copy of frame 0 — the tail morph lands on ≈frame 0; a duplicate froze the loop)
        img.save(frames_dir / f"{i:05d}.png")
        if k == T and p_idx not in phase_refs:
            phase_refs[p_idx] = channel_stats(img)   # this phase's palette anchor
        if i % 10 == 0 or i == total - 1:
            # rate over frames RENDERED this process (a --resume/--from-card run starts at
            # start_i; dividing by i counted the copied prefix as free work and showed
            # "0.1s/frame, ~2s left" on a 7-minute partial render)
            rate = (time.time() - t0) / (i - start_i + 1)
            print(f"[dive] frame {i + 1}/{total} ({rate:.1f}s/frame, "
                  f"~{rate * (total - i - 1):.0f}s left) :: {prompt[:60]}", flush=True)

    if not args.no_video:
        # counter flag: journeys declare it in the `format` block (per the skill); fall back to
        # settings/DEFAULTS. (Was read only from cfg, so a journey's format.counter was ignored —
        # skyfog's counter:false silently rendered a nonsense 10^n overlay on a non-ladder path.)
        counter_flag = spec.get("format", {}).get("counter", cfg["counter"])
        show_counter = exponent is not None and not args.frames
        if show_counter and counter_flag == "auto":
            exps = [r["exp"] for r in spec["registers"]]
            show_counter = all(a > b for a, b in zip(exps, exps[1:]))
        elif show_counter:
            show_counter = bool(counter_flag)
        assemble(cfg, name, out_dir, frames_dir, total,
                 exponent=exponent if show_counter else None)
    print(f"[dive] done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
