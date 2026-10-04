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
import re
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

import camera as _camera
import figure
import grammar
import plate as _plate
import style as _style
import track
import warp as _warp

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
    # DEPTH 2.0 Phase A (2026-08-22, PLAN "PARALLAX ERA"): depth-differential parallax on
    # the fed-back frame — near content expands beyond the scheduled zoom, far recedes
    # relatively, median plane rides the schedule exactly (warp.parallax_residual). Depth
    # comes from the resolve scaffold inside windows (conditioning + warp AGREE — the
    # orbit-v2 lesson) and DepthAnything at cadence elsewhere, EMA-smoothed +
    # plane-quantized (raw estimator shimmer kills warps).
    # 1.0 = PHIL'S FINAL VERDICT 2026-08-23 morning (after the full coral gain ladder
    # 0.5/0.7/1.0): "the full gain gives us more freedom and diversity with our shifts
    # between cards, and a more depth-filled world — I don't see a downside." The one-night
    # random-gain exploration (2026-08-22, draws {0.5..1.0}) is retired; its six renders
    # keep their drawn gains in engine_params for the audience data. --parallax N pins a
    # different value for labs; --parallax 0 = the off A/B. Don't change without a new
    # recorded verdict.
    "parallax_gain": 1.0,
    "parallax_depth_every": 3,   # DepthAnything cadence outside scaffold windows (frames)
    "parallax_planes": 5,        # depth quantization levels
    # Phase B: keep the arrival scaffold alive as the DEPTH source (never the CN) until its
    # card ends — "moving through a sea", not "a sea appears, then wallpaper"
    "resolve_persist": False,
    # Phase C (camera_micro — Phil 2026-08-22: MUST be a clean off-switch; he judges the
    # with/without A/B): musical micro camera motion keyed off the zoom schedule's own
    # arrive-look-plunge curve. HOVER frames (low z) get a parallax-only lateral drift, one
    # sinusoid cycle per music bar so every downbeat lands at zero offset (loop/seam-safe by
    # construction; the aim plane never moves). PLUNGE frames (high z) get a parallax-gain
    # surge instead. Both need parallax_gain > 0 — --parallax 0 kills everything at once.
    "camera_micro": False,
    "micro_drift_px": 12.0,   # lateral drift at the extreme near plane, px
    "micro_surge": 0.5,       # plunge gain multiplier: pk * (1 + surge * plunge-ness)
    # ENGINE 3 Phase D (2026-08-27): per-card `camera` moves (engine/camera.py compiles
    # the journey's camera fields into a per-frame schedule; no field = this block inert).
    # camera_den_floor DEFAULTS OFF (0): the first camera-lab round set it to 0.48 (the
    # orbit-v3 "re-synthesis must outpace resample loss" figure) and the cam arm promptly
    # re-created orbit-v3's REJECTED failure — content re-interpretation (steel towers
    # hallucinated in a stellar nursery) instead of revolution. At vocabulary rates
    # (≤0.5°/frame) orbit displaces ~1px/frame — the same order as the parallax residual,
    # which heals fine at travel denoise with detail_boost's sharpen as the unsharp.
    # The knob stays for bigger future arcs (landing) — use with the smear/reinterpret
    # trade-off in mind.
    "camera_den_floor": 0.0,
    # HOMING CURVE v2 (Phil 2026-08-23, "stronger and earlier"): the loop tail's IPA
    # weight rises from a NONZERO floor at tail start on a smoothstep ease — half strength
    # by mid-tail — instead of the old 0.95*t^1.5 that back-loaded all convergence into
    # the last ~8 frames ("the seam is too abrupt... the shift is too a drop"). The
    # depth-CN runs across the WHOLE tail (was: only the last morph window). Zoom
    # schedule, rhythm and frame counts untouched — same frames, more of them homing.
    "home_ipa_floor": 0.22,   # IPA weight at tail start
    "home_ipa_peak": 0.95,    # IPA weight at the landing
    "home_ipa_shape": 0.8,    # exponent on the smoothstep (<1 = earlier strength)
    "home_cn_floor": 0.15,    # depth-CN at tail start
    "home_cn_peak": 0.80,     # depth-CN at the landing
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
# extra negatives when the render_start is far from human scale (grammar returns
# spaceless=True): the checkpoint's postcard prior otherwise paints LAND-UNDER-SKY —
# desert + flowers in front of a 10^14 stellar nursery (whale_fall, seam forensics
# 2026-08-23). Wrong-scale terrain is a frame-0 disease; mid-dive frames never get these.
ESTABLISH_SPACE_NEG = (", landscape, horizon, ground, terrain, foreground rocks, flowers, "
                       "meadow, beach, desert, mountains, trees, buildings, sky above land")

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
                   ipa_image=None, ipa_weight=0.0, neg_extra=None,
                   diff_diffusion=False, region=None, ipa_mask=None):
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
    if region:
        # PLANET PLATE regional prompts (engine/plate.py): `region["prompt"]` conditions the
        # disc (region["mask"] = 1 inside), the schedule's own prompt the rest of the frame.
        wf["rg_pos"] = {"class_type": "CLIPTextEncode",
                        "inputs": {"text": region["prompt"], "clip": ["ckpt", 1]}}
        wf["rg_img"] = {"class_type": "LoadImage", "inputs": {"image": region["mask"]}}
        wf["rg_mask"] = {"class_type": "ImageToMask",
                         "inputs": {"image": ["rg_img", 0], "channel": "red"}}
        wf["rg_inv"] = {"class_type": "InvertMask", "inputs": {"mask": ["rg_mask", 0]}}
        wf["rg_in"] = {"class_type": "ConditioningSetMask",
                       "inputs": {"conditioning": ["rg_pos", 0], "mask": ["rg_mask", 0],
                                  "strength": 1.0, "set_cond_area": "default"}}
        wf["rg_out"] = {"class_type": "ConditioningSetMask",
                        "inputs": {"conditioning": positive, "mask": ["rg_inv", 0],
                                   "strength": 1.0, "set_cond_area": "default"}}
        wf["rg_comb"] = {"class_type": "ConditioningCombine",
                         "inputs": {"conditioning_1": ["rg_in", 0],
                                    "conditioning_2": ["rg_out", 0]}}
        positive = ["rg_comb", 0]
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
        if ipa_mask:
            # PLANET PLATE live mode: the reference conditions only the VOID (attention
            # mask = outside the disc), never the globe
            wf["ipa_mask_img"] = {"class_type": "LoadImage", "inputs": {"image": ipa_mask}}
            wf["ipa_mask"] = {"class_type": "ImageToMask",
                              "inputs": {"image": ["ipa_mask_img", 0], "channel": "red"}}
            wf["ipa"]["inputs"]["attn_mask"] = ["ipa_mask", 0]
        model_ref = ["ipa", 0]
    if diff_diffusion and init_image and mask_image:
        # graded noise mask -> per-pixel denoise strength (a mask value m = that region is
        # denoised for the last m fraction of the steps). PLANET PLATE: 1 inside the disc,
        # a fraction outside so the void is never repainted into terrain.
        wf["dd"] = {"class_type": "DifferentialDiffusion", "inputs": {"model": model_ref}}
        model_ref = ["dd", 0]
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
    """Upload a PIL image to ComfyUI's input folder. RETRIES connection hiccups (2026-10-03: a
    single ConnectTimeout on /upload/image killed a 50-minute render at frame 249 while
    ComfyUI itself was fine seconds later) — same contract run_workflow already has."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    last = None
    for attempt in range(5):
        try:
            r = requests.post(f"{COMFY}/upload/image",
                              files={"image": (name, io.BytesIO(data), "image/png")},
                              data={"overwrite": "true"}, timeout=60)
            r.raise_for_status()
            return r.json()["name"]
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
            print(f"[dive] upload_image: ComfyUI connection hiccup ({type(e).__name__}), "
                  f"retry {attempt + 1}/4 in {5 * (attempt + 1)}s", flush=True)
            time.sleep(5 * (attempt + 1))
    raise last


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


def transform_depth(depth, zoom, rotate_deg, cx, cy, w, h):
    """Carry the parallax depth map through the SAME uniform transform the fed frame gets
    (rotate + clamped crop + resize), so depth stays aligned with the image between fresh
    estimates (DEPTH 2.0 Phase A). Bilinear is fine — the map is plane-quantized anyway."""
    im = Image.fromarray((np.clip(depth, 0.0, 1.0) * 255).astype("uint8"))
    if rotate_deg:
        im = im.rotate(rotate_deg, resample=Image.BILINEAR, expand=False)
    ecx, ecy = track.crop_center(zoom, cx, cy)
    cw, ch = w / zoom, h / zoom
    left, top = ecx * w - cw / 2, ecy * h - ch / 2
    im = im.crop((left, top, left + cw, top + ch)).resize((w, h), Image.BILINEAR)
    return np.asarray(im, "float32") / 255.0


# --hero-cn applies only to ROUND targets (2026-08-29 forensics: the first lab put the
# sphere on cobalt card 1's "steep rock headland" and the model painted a ringed caldera —
# Phil: "those holes aren't really planets"). A headland is not a globe.
HERO_ROUND = re.compile(r"\b(planet|world|moon|sun|star|sphere|globe|orb|ball|egg|droplet|"
                        r"bead|pearl|marble|bubble|nucleus)\b", re.I)
# while the globe is small the prompt says GLOBE IN A VOID and the negative bans the
# hole/crater/cell readings a lone shaded disc otherwise invites
HERO_CLAUSE = ("a single round globe, a sphere lit from one side, hanging alone in the "
               "black void of space")
HERO_NEG = ("crater, hole, pit, ring, eye, cell, bubble, flat disc, landscape, ground, "
            "horizon, terrain, rocks")


def hero_specks(w, h, seed, n=160):
    """The VOID behind the hero: a sparse field of far specks (frame-0 px coords, depth
    value, radius) that projects through the cumulative zoom + the orbit pan."""
    rng = np.random.default_rng(seed)
    xs = rng.uniform(-1.5 * w, 2.5 * w, n)          # over-wide: the pan sweeps new sky in
    ys = rng.uniform(-0.6 * h, 1.6 * h, n)
    dv = rng.uniform(0.10, 0.30, n)
    rr = rng.uniform(1.2, 3.2, n)
    return np.stack([xs, ys, dv, rr], axis=1)


def hero_depth(w, h, fx, fy, frac, specks=None, Z=1.0, pan=0.0):
    """--hero-cn (2026-08-27, planet forensics; v2 2026-08-29): synthetic depth map — ONE
    shaded sphere at the tracked position whose diameter is `frac` of the frame width,
    over a VOID of far specks (v2; was a flat far plane, which with a busy fed-back
    background read as a dome on ground). Fed as the depth-CN, the model must paint the
    target at its SCHEDULED size each frame; re-diffusion can no longer re-normalize the
    object back to prior-preferred marble size (cobalt's ice world grew 12%->25% over a
    card whose zoom said x10 — the prior ate the zoom). specks project about the sphere
    center through the cumulative zoom Z and shift by the orbit pan (px)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = fx * w, fy * h
    depth = np.full((h, w), 0.04, np.float32)
    if specks is not None:
        for sx, sy, dv, rr in specks:
            px = cx + (sx - cx) * Z - pan
            py = cy + (sy - cy) * Z
            if -8 < px < w + 8 and -8 < py < h + 8:
                rad = rr * Z ** 0.5
                x0, x1 = int(max(0, px - 3 * rad)), int(min(w, px + 3 * rad + 1))
                y0, y1 = int(max(0, py - 3 * rad)), int(min(h, py + 3 * rad + 1))
                if x1 > x0 and y1 > y0:
                    g = np.exp(-((xx[y0:y1, x0:x1] - px) ** 2
                                 + (yy[y0:y1, x0:x1] - py) ** 2) / (2 * rad * rad))
                    depth[y0:y1, x0:x1] = np.maximum(depth[y0:y1, x0:x1], dv * g)
    r = max(4.0, frac * w / 2)
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
    dome = np.clip(0.95 - 0.4 * d2, 0.0, 1.0)
    depth = np.where(d2 <= 1.0, np.maximum(dome, 0.55), depth).astype(np.float32)
    return Image.fromarray((depth * 255).astype("uint8")).convert("RGB")


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


def assemble(cfg, name, out_dir, frames_dir, total, exponent=None, loop_pad=False, start=0,
             rot=0):
    # zoom-out is always the primary cut: build-out generates it forward,
    # build-in generates dive-in footage that gets reversed into the primary
    fwd = f"{name}.mp4" if cfg["build"] == "out" else f"{name}_divein.mp4"
    rev = f"{name}_divein.mp4" if cfg["build"] == "out" else f"{name}.mp4"
    """Loop crossfade, raw encode, motion interpolation, counter overlay, reverse cut.
    start (LOOP LAP, 2026-08-23): first delivered frame — frames [0..start) are the
    txt2img warm-up card, rendered but cut; the video is frames [start..total)."""
    n_raw = total - start
    K = min(cfg["loop_fade_frames"], n_raw // 2)
    if K:
        # with a lap cut, blend the tail toward the frames leading INTO the start
        # ([start-K..start)) so the final frame lands one step BEFORE the wrap target and
        # motion continues; [start..start+K) would land AHEAD and the wrap stepped backward
        h0 = start - K if start >= K else start
        heads = [Image.open(frames_dir / f"{h0 + i:05d}.png").convert("RGB")
                 for i in range(K)]
        for i in range(K):
            t = total - K + i
            tail = Image.open(frames_dir / f"{t:05d}.png").convert("RGB")
            Image.blend(tail, heads[i], (i + 1) / (K + 1)).save(frames_dir / f"{t:05d}.png")
        print(f"[dive] loop crossfade over last {K} frames", flush=True)

    # LOOP-AWARE INTERPOLATION (2026-08-14): minterpolate cannot in-between past its last
    # input frame, so every assembled video silently LOST the final ~1.5 raw frames (613 of
    # 616 expected — in every prior render) and the loop wrapped with a ~2.5-frame pop.
    # Padding the sequence with the first two frames lets the interpolator bridge
    # f_last -> f0 like any other pair; the output is trimmed to the exact frame count and
    # the pads removed (repair tools count frames/ to judge completeness).
    pad = 0
    raw = "build/raw.mp4"
    rot = int(rot) % n_raw if n_raw else 0
    if rot:
        # PLAY ORDER (2026-09-18, Phil: "the scale doesn't monotonically decrease and then
        # loop back to the biggest scale"): the chain may be RENDERED from a different card
        # than the video should OPEN on (the planet plate needs its card mid-chain, so the
        # position audit moved render_start). The delivered video is a seamless loop, so it
        # is simply rotated: delivered frame j = rendered frame start + (rot + j) % n_raw.
        # The new wrap joins two CONSECUTIVE chain frames; the render's own loop point (the
        # IPA-homed lap seam) lands mid-video. Whole-card rotations keep the music grid.
        play = out_dir / "build" / "play"
        play.mkdir(exist_ok=True)
        for f in play.glob("*.png"):
            f.unlink()
        n_seq = n_raw + (2 if loop_pad else 0)
        for j in range(n_seq):
            shutil.copy(frames_dir / f"{start + (rot + j) % n_raw:05d}.png",
                        play / f"{j:05d}.png")
        pad = 2 if loop_pad else 0
        subprocess.run([FFMPEG, "-y", "-framerate", str(cfg["fps"]), "-start_number", "0",
                        "-i", "build/play/%05d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", raw],
                       cwd=out_dir, check=True, capture_output=True)
        shutil.rmtree(play, ignore_errors=True)
        pad_in_frames = False
        print(f"[dive] play order: delivered video rotated by {rot} frames "
              f"({rot / max(1, cfg['fps']):.1f}s) to open on the play_start card", flush=True)
    else:
        pad_in_frames = bool(loop_pad)
        if loop_pad:
            for k_ in (0, 1):
                shutil.copy(frames_dir / f"{start + k_:05d}.png",
                            frames_dir / f"{total + k_:05d}.png")
            pad = 2
        subprocess.run([FFMPEG, "-y", "-framerate", str(cfg["fps"]),
                        "-start_number", str(start),
                        "-i", "build/frames/%05d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", raw],
                       cwd=out_dir, check=True, capture_output=True)

    interp = "build/interp.mp4"
    n_target = n_raw * (cfg["final_fps"] or cfg["fps"]) // cfg["fps"]
    if cfg["final_fps"]:
        t0 = time.time()
        subprocess.run([FFMPEG, "-y", "-i", raw,
                        "-vf", (f"minterpolate=fps={cfg['final_fps']}:mi_mode=mci:"
                                "mc_mode=aobmc:me_mode=bidir:vsbmc=1"),
                        "-frames:v", str(n_target),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", interp],
                       cwd=out_dir, check=True, capture_output=True)
        print(f"[dive] interpolated {cfg['fps']} -> {cfg['final_fps']}fps "
              f"({n_target} frames{', loop-bridged' if pad else ''}) "
              f"in {time.time() - t0:.0f}s", flush=True)
    elif pad:
        subprocess.run([FFMPEG, "-y", "-i", raw, "-frames:v", str(n_target),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", interp],
                       cwd=out_dir, check=True, capture_output=True)
    else:
        interp = raw
    if pad_in_frames:
        for k_ in range(pad):
            (frames_dir / f"{total + k_:05d}.png").unlink(missing_ok=True)

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
        exps = [exponent[min(total - 1, start + (rot + int(j * n_raw / n_out)) % n_raw)]
                for j in range(n_out)]
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
              f"{n_raw / cfg['fps']:.1f}s)", flush=True)


def play_rotation(spec, fps, lap_cut):
    """Frames to rotate the DELIVERED video by so it opens on the first clean (post-arrival)
    frame of the journey's `play_start` card. 0 when the field is absent, names the
    render_start card or the card after it (the delivered cut already opens there), or
    there is no lap. Uniform bars make this a whole number of cards."""
    ps = spec.get("play_start")
    if not ps or not lap_cut or "registers" not in spec:
        return 0
    regs = spec["registers"]
    names = [r.get("name") for r in regs]
    rs = spec.get("render_start")
    k0 = names.index(rs) if rs in names else 0
    order = names[k0:] + names[:k0]
    if ps not in order:
        print(f"[dive] play_start {ps!r} is not a register name — ignored", flush=True)
        return 0
    K = order.index(ps)
    if K == 0:
        return 0
    cf = register_frame_counts(spec, fps)
    first_clean = sum(cf[:K]) + max(2, round(cf[K] * 0.25))
    return max(0, first_clean - lap_cut)


def finish_video(spec, cfg, args, name, out_dir, frames_dir, total, exponent, loop, lap_cut):
    """Counter decision + play rotation + assemble — shared by a fresh render and
    --reassemble."""
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
    rot = play_rotation(spec, cfg["fps"], lap_cut) if not args.frames else 0
    assemble(cfg, name, out_dir, frames_dir, total,
             exponent=exponent if show_counter else None,
             loop_pad=bool(loop) and cfg["build"] != "out", start=lap_cut, rot=rot)
    return rot


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
    ap.add_argument("--classic-loop", action="store_true",
                    help="disable the LOOP LAP (Phil 2026-08-23, default ON): render the "
                         "extra card-0 lap and cut the txt2img warm-up card, so the loop "
                         "home is a feedback-born frame. This flag restores the old "
                         "home-onto-frame-0 behavior for A/B.")
    ap.add_argument("--resolve", dest="resolve", action="store_true", default=True,
                    help="RESOLVE-ON-APPROACH (DEFAULT ON, Phil 2026-08-14): field-card "
                         "arrivals get animated procedural depth scaffolds so the new realm "
                         "resolves out of the old texture as countless growing instances")
    ap.add_argument("--no-resolve", dest="resolve", action="store_false",
                    help="disable resolve-on-approach (A/B / legacy behavior)")
    ap.add_argument("--parallax", type=float, metavar="GAIN",
                    help="DEPTH 2.0: depth-differential parallax gain on the fed-back frame "
                         "(0 = off/today's engine; 1.0 ≈ nearest plane zooms ~z^1.5 while the "
                         "far field recedes relatively). Overrides cfg parallax_gain.")
    ap.add_argument("--resolve-persist", action="store_true",
                    help="DEPTH 2.0 Phase B: arrival scaffolds stay alive as the parallax "
                         "DEPTH source (never the CN) until their card ends — persistent "
                         "instance seas. Needs --parallax > 0 to have any effect.")
    ap.add_argument("--micro", action="store_true",
                    help="DEPTH 2.0 Phase C (camera_micro): musical micro camera motion — "
                         "parallax-only lateral drift on hover bars, parallax surge on "
                         "plunges. Default OFF (Phil judges the with/without A/B); needs "
                         "--parallax > 0.")
    ap.add_argument("--persist-cn", action="store_true",
                    help="PERSISTENCE LAB (2026-08-27, the hummingbird forensics): the "
                         "resolve scaffold stays the CN through the card's TRAVEL (window "
                         "extends to one beat before card end), cameo cards included — "
                         "instances are held in existence past the arrival instead of "
                         "churning at travel denoise. Default OFF until Phil's verdict.")
    ap.add_argument("--no-loop", action="store_true",
                    help="lab: disable the loop-homing tail (approach labs: --frames "
                         "truncates total so the tail, sized off total, eats the approach)")
    ap.add_argument("--hero-orbit", type=float, default=0.0, metavar="DEG",
                    help="lab: with --hero-cn, revolve DEG around the globe across its "
                         "approach run (sphere-interior rotation + background pan)")
    ap.add_argument("--hero-pan", type=float, default=6.0, metavar="PX_PER_DEG",
                    help="lab: background pan per orbit degree (px)")
    ap.add_argument("--hero-cn", action="store_true",
                    help="PERSISTENCE LAB (2026-08-27, the planet forensics): single-target "
                         "cards get a synthetic depth disc at the TRACKER's position whose "
                         "size follows the zoom schedule (x10 across the card), fed as the "
                         "CN — the object must GROW to fill the view by the boundary "
                         "instead of being re-painted at prior-preferred size every frame. "
                         "Default OFF until Phil's verdict.")
    ap.add_argument("--plate", choices=("low", "mask", "region", "live"),
                    help="PLANET PLATE LAB (2026-09-17, PLAN 'PLANET DESCENT'): planet-class "
                         "cards get a procedurally rendered globe (texture = txt2img of the "
                         "next card's orbit-view scene) composited at the exact scheduled "
                         "size every frame over a void plate; tracker bypassed, cameo "
                         "refused. low = global denoise cap 0.32; mask = graded latent noise "
                         "mask (void protected); region = mask + regional prompts. Default "
                         "OFF — the nightly path is byte-unchanged without it.")
    ap.add_argument("--plate-card", type=int, action="append", metavar="K",
                    help="with --plate: only these render-order card indices (repeatable); "
                         "default = every planet-class card (plate.is_plate_card)")
    ap.add_argument("--plate-limb", type=float, default=1.15, metavar="S",
                    help="with --plate: globe diameter (x frame width) at the planet card's "
                         "bar line — the ORBIT VIEW the next card is authored as (1.15 = "
                         "wider than the frame, limb visible top and bottom); the plate then "
                         "keeps growing through the next card's arrival until the frame lies "
                         "inside the disc and hands off to that card's normal approach")
    ap.add_argument("--plate-spin", type=float, default=1.5, metavar="DEG",
                    help="with --plate: the globe revolves DEG per frame about its vertical "
                         "axis (texture + fed-back disc interior together). v3: breaks the "
                         "concentric-ring lock a fixed-point zoom into a static disc falls "
                         "into, and is the orbit motion. 0 = static globe (the v2 arms).")
    ap.add_argument("--plate-cn", type=float, default=None, metavar="STRENGTH",
                    help="with --plate: depth-CN strength of the synthetic dome while the globe "
                         "is an object (default = approach_cn). v5 lab: 0 — the radially "
                         "symmetric dome under full denoise is the prime suspect for the "
                         "concentric-ring lock in the mask arms (the hero-cn 'caldera' class).")
    ap.add_argument("--plate-entrance", default="", metavar="JSON",
                    help="labs: an exact entrance dict (kind/start/goal/k/bow[/light/spin]) "
                         "instead of the journey-keyed draw")
    ap.add_argument("--plate-entrance-seed", type=int, default=0, metavar="N",
                    help="with --plate-intro mix/travel/...: vary the journey-keyed entrance "
                         "draw (labs: see several entrances on one card)")
    ap.add_argument("--plate-intro", choices=("auto", "grow", "enter", "plain", "mix", "travel",
                                              "mix-enter", "mix-grow"), default="auto",
                    help="with --plate: how the globe is introduced — grow (from a star-like "
                         "point, accelerating in), enter (already a globe, sliding in from "
                         "beyond a frame edge), plain (the zoom's own rate, lab arm B). auto = "
                         "journey-keyed variety between grow and enter (Phil 2026-09-18).")
    ap.add_argument("--plate-void-gate", action="store_true",
                    help="with --plate: caption-check both plates and re-roll seeds (x3) — "
                         "the VOID when it reads as an OBJECT (necklace/pendant/vase: the "
                         "product-shot prior) and the SURFACE when it reads as a ground-level "
                         "view (sky/horizon/beach: garnet's aurora-over-a-cliff). Lab flag.")
    ap.add_argument("--reassemble", metavar="vN",
                    help="no GPU: re-run ONLY the assembly (interpolation, counter, play "
                         "rotation, reverse cut) on an existing complete render's frames — "
                         "e.g. after adding `play_start` to the journey")
    ap.add_argument("--plan-only", action="store_true",
                    help="print the compiled plan (resolve windows, plate spans, cameos) and "
                         "exit before rendering — the position audit's verifier")
    ap.add_argument("--plate-outside", type=float, default=0.27, metavar="M",
                    help="with --plate mask/region: noise-mask value outside the disc "
                         "(fraction of the denoise the void receives)")
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
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VAL",
                    help="LAB: override any engine cfg key after presets/journey/CLI (repeatable; "
                         "typed by the key's current value, e.g. --set saturation=1.0 "
                         "--set color_match=0). Recorded in run.json 'overrides'.")
    ap.add_argument("--tail", default=None, metavar="TEXT",
                    help="LAB (orange drift): replace the style deck's brand tail with TEXT for "
                         "this run ('' drops it)")
    ap.add_argument("--neg-extra", default="", metavar="TEXT",
                    help="LAB: append TEXT to the negative prompt of every feedback frame")
    ap.add_argument("--palette-anchor", type=float, default=0.0, metavar="S",
                    help="LAB: colour-match every travel frame toward the CURRENT CARD's authored "
                         "palette (engine/palette.py swatch stats) at strength S instead of "
                         "toward the phase's own first frame (which has already drifted)")
    ap.add_argument("--palette-anchor-mode", choices=("rgb", "lab"), default="rgb",
                    help="LAB: --palette-anchor as per-channel RGB mean/std (rgb, the colour_match "
                         "LUT) or a hue-aware Reinhard lαβ transfer (lab)")
    ap.add_argument("--palette-ipa", type=float, default=0.0, metavar="W",
                    help="LAB: IP-Adapter every travel frame toward a soft colour-field image of "
                         "the current card's palette at weight W (off inside the loop tail and "
                         "plate spans, which own the IPA slot)")
    ap.add_argument("--stage", choices=("lattice", "nucleus", "quark", "fog", "tubes", "tissue"),
                    default=None,
                    help="LAB (PLAN 'THE MICRO STAGE'): render card --stage-card through a built "
                         "3-D stage (engine/stage.py) composited every frame at the exact zoom, "
                         "tracker bypassed, the stage's depth as the CN")
    ap.add_argument("--stage-auto", action="store_true",
                    help="LAB: stage every card for which engine/stage.suggest_stage proposes a kit "
                         "(atomic/subnuclear/molecular bands, by the card's words); explicit "
                         "per-card `stage` fields still win")
    ap.add_argument("--stage-card", type=int, default=None, metavar="K",
                    help="with --stage: render-order card index the stage owns")
    ap.add_argument("--stage-params", default="", metavar="JSON",
                    help="with --stage: kit parameters, e.g. '{\"variant\":\"rhombo\",\"spacing\":0.5}'")
    ap.add_argument("--stage-seed", type=int, default=0, metavar="N",
                    help="with --stage: kit seed (default: journey:card crc)")
    ap.add_argument("--stage-den", type=float, default=0.60, metavar="D",
                    help="with --stage: denoise floor across the card's arrival frames (the "
                         "costume pass — the brand-pass lab needed ~0.6 to dress a CG render)")
    ap.add_argument("--stage-den-travel", type=float, default=0.45, metavar="D",
                    help="with --stage: denoise floor after the arrival")
    ap.add_argument("--stage-cn", type=float, default=0.7, metavar="S",
                    help="with --stage: depth-CN strength of the stage's own depth map")
    ap.add_argument("--stage-id", type=float, default=0.5, metavar="W",
                    help="with --stage: identity blend toward the stage render through travel "
                         "(ramps 0.15 -> 1.0 across the arrival, decays to 0.6 W over the plunge)")
    ap.add_argument("--tag", default="", metavar="TAG",
                    help="LAB: suffix the run name (output/<journey>_<TAG>/vN) so lab arms never "
                         "share a vN sequence with the real render; --from-card prefix frames "
                         "still come from the unsuffixed journey")
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
    if args.tail is not None:
        _bt = _style.load_deck().get("brand_tail", "")
        if _bt and _bt in sfx:
            sfx = sfx.replace(_bt, args.tail).rstrip(", ").strip()
            print(f"[dive] brand tail -> {args.tail!r}", flush=True)
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
    if args.parallax is not None:
        cfg["parallax_gain"] = args.parallax
    if args.resolve_persist:
        cfg["resolve_persist"] = True
    if args.micro:
        cfg["camera_micro"] = True
    # --set KEY=VAL (2026-10-03, orange-drift lab): typed by the existing value so a knob
    # keeps its kind (float stays float, bool parses true/false); unknown keys are refused.
    cfg_overrides = {}
    for _kv in args.overrides:
        _k, _, _v = _kv.partition("=")
        if _k not in cfg:
            sys.exit(f"--set: unknown cfg key {_k!r} (known: {', '.join(sorted(cfg))})")
        _cur = cfg[_k]
        if isinstance(_cur, bool):
            _val = _v.strip().lower() in ("1", "true", "yes", "on")
        elif isinstance(_cur, int) and not isinstance(_cur, bool):
            _val = int(float(_v))
        elif isinstance(_cur, float):
            _val = float(_v)
        else:
            _val = _v
        cfg[_k] = _val
        cfg_overrides[_k] = _val
    if cfg_overrides:
        print(f"[dive] cfg overrides: {cfg_overrides}", flush=True)
    zoom_sched = den_sched = exponent = loop = None
    cameos, arrivals, approach, seam_arrivals = [], set(), [], set()
    cam_sched, cam_plan = [], []
    if "registers" in spec:
        (phases, zoom_sched, den_sched, exponent, loop, cameos, arrivals, approach,
         seam_arrivals) = grammar.compile_journey(
             spec, cfg["fps"], cfg["build"],
             loop_lap=False if args.classic_loop else None)
        if cfg["build"] == "out" and spec.get("format", {}).get("exact_loop"):
            cfg["loop_fade_frames"] = max(cfg["loop_fade_frames"], 8)
        # ENGINE 3 Phase D: compile the journey's per-card camera plans (engine/camera.py).
        # No camera fields -> empty schedule -> every frame takes today's exact code path.
        if cfg["build"] != "out":
            cam_plan = _camera.plan_summary(spec)
            if cam_plan:
                _cprobs = _camera.validate(spec)
                for _cp in _cprobs:
                    print(f"[dive] camera VALIDATION: {_cp}", flush=True)
                cam_sched = _camera.schedule(spec, cfg["fps"])
                print(f"[dive] CAMERA ON — {'; '.join(cam_plan)}"
                      + (f" (parallax_gain=0: only roll will act)"
                         if not cfg["parallax_gain"] else ""), flush=True)
    else:
        phases = spec["phases"]
    if args.no_loop:
        loop = None
    total = args.frames or sum(p["frames"] for p in phases)
    # LOOP LAP (see grammar.compile_journey): frames [0..lap_cut) are the txt2img warm-up
    # card — rendered (they seed the chain) but CUT at assembly; the tail homes onto frame
    # lap_cut. 0 = classic behavior (no lap / --classic-loop / --frames smoke tests).
    lap_cut = (loop or {}).get("lap_cut", 0) if not args.frames else 0
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
    src_name = name          # --from-card prefix frames come from the UNSUFFIXED lab source
    if args.plate and args.frames:
        # LAB RUNS ONLY (--frames): a separate run dir so arms never share a vN sequence
        # with the real render. A production render (no --frames) keeps the plain
        # journey dir — 2026-09-18: the suffix on the nightly's runs sent three complete
        # 4-hour renders to output/<journey>_platelow/ where queue_review could not find
        # them ("no complete render ... need 392 frames").
        name = f"{name}_plate{args.plate}"
    if args.tag:
        name = f"{name}_{args.tag}"
    if cfg["parallax_gain"] == "random":
        # gain-exploration draw (see DEFAULTS): deterministic from (name, seed) so a
        # same-seed re-render reproduces its gain
        import zlib as _z
        # '#' separator chosen 2026-08-22: over the first 15-journey requeue at seed 1234
        # it spreads draws across all six gains (':' clumped 7 of 15 at 0.5)
        cfg["parallax_gain"] = round(
            0.5 + 0.1 * (_z.crc32(f"{name}#{cfg['seed']}".encode()) % 6), 1)
        print(f"[dive] parallax gain (random draw): {cfg['parallax_gain']}", flush=True)
    # build-out has no txt2img frame 0 to gate, and --resume starts mid-chain (frame 0 already
    # judged), so the gate only applies to a fresh build-IN render.
    img_guard = cfg["figure_guard"] and not args.allow_figures and cfg["build"] != "out"

    base = Path(__file__).resolve().parent.parent / "output" / name
    src_base = Path(__file__).resolve().parent.parent / "output" / src_name
    if args.reassemble:
        _od = base / args.reassemble
        _fd = _od / "build" / "frames"
        _have = len(list(_fd.glob("*.png"))) if _fd.exists() else 0
        if _have < total:
            sys.exit(f"[dive] --reassemble: {_od} has {_have} frames, needs {total}")
        _rot = finish_video(spec, cfg, args, name, _od, _fd, total, exponent, loop, lap_cut)
        try:
            _rj = json.loads((_od / "run.json").read_text())
            _rj.update({"play_start": spec.get("play_start"), "play_rot": _rot,
                        "reassembled": time.strftime("%Y-%m-%d %H:%M")})
            (_od / "run.json").write_text(json.dumps(_rj, indent=2))
        except Exception:
            pass
        return
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
        vs = sorted([d for d in src_base.glob("v[0-9]*") if d.name[1:].isdigit()],
                    key=lambda d: int(d.name[1:]))
        if args.src_version:
            vs = [d for d in vs if d.name == args.src_version]
        src = next((d for d in reversed(vs)
                    if len(list((d / "build" / "frames").glob("*.png"))) >= N), None)
        if not src:
            sys.exit(f"[dive] no version under {src_base} has the {N} prefix frames"
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
        "parallax_gain": cfg["parallax_gain"], "resolve_persist": cfg["resolve_persist"],
        "camera_micro": cfg["camera_micro"], "camera": cam_plan, "lap_cut": lap_cut,
        "persist_cn": bool(args.persist_cn), "hero_cn": bool(args.hero_cn),
        "hero_orbit": args.hero_orbit,
        "plate": args.plate, "plate_cards": args.plate_card, "plate_limb": args.plate_limb,
        "plate_outside": args.plate_outside, "plate_spin": args.plate_spin,
        "plate_cn": args.plate_cn, "plate_void_gate": bool(args.plate_void_gate),
        "plate_intro": args.plate_intro,
        "play_start": spec.get("play_start"),
        "overrides": cfg_overrides, "tag": args.tag, "tail": args.tail,
        "neg_extra": args.neg_extra, "palette_anchor": args.palette_anchor,
        "palette_anchor_mode": args.palette_anchor_mode,
        "palette_ipa": args.palette_ipa,
        "stage": args.stage, "stage_card": args.stage_card, "stage_params": args.stage_params,
        "stage_auto": bool(args.stage_auto),
        "stage_den": args.stage_den, "stage_cn": args.stage_cn, "stage_id": args.stage_id,
        "play_rot": play_rotation(spec, cfg["fps"], lap_cut) if not args.frames else 0,
        # per-CARD (register) frame counts: lets a future --from-card verify its prefix
        # still aligns after a journey edit
        "card_frames": (register_frame_counts(spec, cfg["fps"]) if "registers" in spec
                        else [p["frames"] for p in phases]),
        **run_extra,
    }, indent=2))

    # VRAM LEAK GUARD (2026-08-24): a resident ACE-Step/other stack forces SDXL into
    # per-step CPU<->GPU weight swapping (~3x frame time — the 12:30 wild_yeast crawl at
    # 55s/frame with 8.9 GB idle-resident). Free whatever the last job left before frame 0;
    # worst case is one ~15s model reload.
    try:
        requests.post(f"{COMFY}/free", json={"unload_models": True, "free_memory": True},
                      timeout=15)
    except Exception:
        pass
    t0 = time.time()
    # img / frame0 already set above (None for a fresh run, loaded frames for --resume)
    cam = None
    # DEPTH 2.0 Phase A state: the parallax depth map, kept aligned to the latest generated
    # frame (propagated through the same transform at feed time, refreshed from the scaffold
    # in windows / DepthAnything at cadence elsewhere). par_med = EMA'd reference plane.
    par_depth, par_med, par_src = None, None, None
    plog = open(out_dir / "build" / "parallax.jsonl", "a") if cfg["parallax_gain"] else None
    # Phase C: plunge-ness comes from the schedule itself (p10..p90 of the per-frame zooms —
    # the arrive-look-plunge curve is already the musical phrasing)
    if zoom_sched:
        _zs = sorted(zoom_sched)
        z_lo, z_hi = _zs[len(_zs) // 10], _zs[9 * len(_zs) // 10]
    else:
        z_lo = z_hi = cfg["zoom_per_frame"]
    bar_frames = 4 * spec.get("format", {}).get("frames_per_beat", 7)
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
    import zlib as _zlib
    if getattr(args, "resolve", False) and "registers" in spec and cfg["build"] != "out":
        import scaffold as _scaffold
        _regs = spec["registers"]
        _names = [r["name"] for r in _regs]
        _rs = spec.get("render_start")
        _rot = _names.index(_rs) if _rs in _names else 0
        _order = _regs[_rot:] + _regs[:_rot]
        _cfr = register_frame_counts(spec, cfg["fps"])
        if lap_cut:
            # LOOP LAP: the lap card is a real arrival (from the last card, mid-dive) —
            # it gets a resolve window like any other card; the k==0 skip below keeps
            # applying only to the true txt2img card 0
            _order = _order + [_order[0]]
            _cfr = _cfr + [_cfr[0]]
        _acc = 0
        for _k, _reg in enumerate(_order):
            _F = _cfr[_k]
            _S = _acc
            _acc += _F
            _rv = _reg.get("resolve")
            if _k == 0 or _rv is False or _order[_k - 1].get("kind") == "seam":
                continue
            _fa = max(2, round(_F * 0.25))
            if args.persist_cn:
                # PERSISTENCE LAB (2026-08-27, garden forensics): hold the field through
                # the TRAVEL — window runs to one beat before card end (the plunge stays
                # the tracker/prompt's), cameo cards included. The old cameo rule left
                # ruby's garden card with 6 scaffolded frames of 24; its birds churned
                # into leaf rows for the rest and popped back ad hoc at the plunge.
                _post = max(0, _F - _fa - bar_frames // 4)
            else:
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
            # Phase B (DEPTH 2.0, resolve_persist): the scaffold stays alive as the PARALLAX
            # DEPTH source until its card ends (the CN window is unchanged — targeting and
            # tracker behavior stay exactly as approved). The Resolver just gets the longer
            # zoom/aim slice so instances keep looming, occluding and exiting all card long.
            _wD = _w1
            if cfg["resolve_persist"] and cfg["parallax_gain"]:
                _wD = max(_w1, min(_S + _F, (total - loop["frames"]) if loop else _S + _F))
            _zw = [zoom_sched[x] for x in range(_w0, _wD)]
            _aw = [(0.5 + cfg["drift"] * math.sin(2 * math.pi * x / 263),
                    0.5 + cfg["drift"] * math.sin(2 * math.pi * x / 419 + 1.7))
                   for x in range(_w0, _wD)]
            # scaffold seed = the JOURNEY identity, never the run name (2026-08-27): the
            # run name carries A/B suffixes (_plain/_cn/lab-derived names), and seeding
            # from it gave every renamed arm a DIFFERENT instance field — the camera lab's
            # arms diverged at the window pre-roll, before the variable under test acted.
            # spec.scaffold_name lets a derived lab spec pin the source journey's draw;
            # nightly renders (spec name == journey) are byte-unchanged.
            _sname = spec.get("scaffold_name") or spec.get("name") or Path(args.journey).stem
            _res = _scaffold.Resolver(
                _mode, _zw, _aw,
                seed=_zlib.crc32(f"{_sname}:{_reg.get('name')}".encode()),
                density=_rv.get("density", _dflt[0]), size=_rv.get("size", _dflt[1]),
                variant=_rv.get("variant"), extend=(_wD > _w1))
            resolve_windows.append({"w0": _w0, "w1": _w1, "wD": _wD, "res": _res, "pre": 6,
                                    "card": _reg.get("name"), "mode": _mode})
        if resolve_windows:
            print("[dive] RESOLVE ON — " + ", ".join(
                f"{w['card']}({w['mode']})[{w['w0']}..{w['w1'] - 1}]"
                for w in resolve_windows), flush=True)
    # PALETTE ANCHOR / PALETTE IPA (lab, 2026-10-03 — the orange-drift forensics): the fed
    # chain drifts toward one warm attractor regardless of the authored palette (the
    # diffusion pushes orange ~+0.02..0.08/frame; colour-match toward the phase's OWN first
    # frame only ratchets it). These give colour-match / IP-Adapter a FIXED authored target.
    _pal_cards = None
    if (args.palette_anchor or args.palette_ipa) and "registers" in spec:
        import palette as _palette
        _pregs = spec["registers"]
        _pnames = [r["name"] for r in _pregs]
        _prs = spec.get("render_start")
        _prot = _pnames.index(_prs) if _prs in _pnames else 0
        _porder = _pregs[_prot:] + _pregs[:_prot]
        _pcf = register_frame_counts(spec, cfg["fps"])
        _pal_cards = []            # (start_frame, register) in render order
        _pacc = 0
        for _preg_, _pn_ in zip(_porder, _pcf):
            _pal_cards.append((_pacc, _preg_))
            _pacc += _pn_
        _pal_cache = {}

        def _pal_card(i):
            reg = _pal_cards[0][1]
            for s0, r_ in _pal_cards:
                if i >= s0:
                    reg = r_
            return reg

        def palette_anchor_for(i):
            reg = _pal_card(i)
            key = (args.palette_anchor_mode, reg.get("name"))
            if key not in _pal_cache:
                _pal_cache[key] = (_palette.swatch_lab_stats(reg.get("palette") or "", seed=cfg["seed"])
                                   if args.palette_anchor_mode == "lab"
                                   else _palette.swatch_stats(reg.get("palette") or ""))
            return _pal_cache[key]

        def palette_ipa_for(i):
            reg = _pal_card(i)
            key = ("ipa", reg.get("name"))
            if key not in _pal_cache:
                im = _palette.swatch_image(reg.get("palette") or "", cfg["width"], cfg["height"],
                                           seed=cfg["seed"])
                _pal_cache[key] = upload_image(im, f"zoomer_palipa_{name}_{reg.get('name')}.png") \
                    if im is not None else None
                if im is not None:
                    (out_dir / "build").mkdir(parents=True, exist_ok=True)
                    im.save(out_dir / "build" / f"palette_{reg.get('name')}.png")
            return _pal_cache[key]
        print(f"[dive] PALETTE anchor {args.palette_anchor} / ipa {args.palette_ipa} over "
              f"{len(_pal_cards)} cards", flush=True)
    # TRACKER v3 (2026-07-31, PLAN "TRACKER v3"): two-stage point→object tracking with EXACT
    # geometry propagation (engine/track.py). Emergence point committed per run; detect.locate
    # tries at a low cadence; the first confident lock hands off seamlessly (the aim was already
    # heading somewhere — a lock just moves the destination); between detections the track rides
    # the known zoom geometry, so missed/garbage detections can't yank the camera.
    # PLANET PLATE (2026-09-17, engine/plate.py): planet-class cards render through a
    # plate — see the module docstring. plate_at[i] = the Plate owning frame i (or None).
    plates, plate_at = {}, [None] * total
    if args.plate and "registers" in spec and cfg["build"] != "out":
        _pregs = spec["registers"]
        _pnames = [r["name"] for r in _pregs]
        _prs = spec.get("render_start")
        _prot = _pnames.index(_prs) if _prs in _pnames else 0
        _porder = _pregs[_prot:] + _pregs[:_prot]
        _pcfr = register_frame_counts(spec, cfg["fps"])
        if lap_cut:
            _porder = _porder + [_porder[0]]
            _pcfr = _pcfr + [_pcfr[0]]
        _pacc = 0
        for _pk, _preg in enumerate(_porder):
            _pF = _pcfr[_pk]
            _pS, _pE = _pacc, min(_pacc + _pF, total)
            _pacc += _pF
            _pnxt = _porder[(_pk + 1) % len(_porder)] if not lap_cut else \
                (_porder[_pk + 1] if _pk + 1 < len(_porder) else _porder[1])
            _want = (args.plate_card is not None and _pk in args.plate_card) or \
                (args.plate_card is None and _plate.is_plate_card(_preg, _pnxt))
            if not _want or _pE <= _pS or _pS >= total:
                continue
            _pfa = 0 if _pk == 0 else max(2, round(_pF * 0.25))
            # the plate spans THIS card and the NEXT (until the frame lies inside the disc);
            # the size schedule runs over the FULL compiled span (zoom_sched is complete) —
            # never the --frames-truncated total (the smoke-test trap)
            _pFn = _pcfr[_pk + 1] if _pk + 1 < len(_pcfr) else _pcfr[0]
            _pE2 = min(_pS + _pF + _pFn, len(zoom_sched))
            _ih = _zlib.crc32(f"{spec.get('name')}:{_preg.get('name')}:intro".encode())
            _intro = args.plate_intro
            if _intro == "auto":
                _intro = ("grow", "enter")[_ih % 2]
            _edge = ("right", "left", "top", "bottom")[(_ih >> 3) % 4]
            # UNIFIED ENTRANCES (2026-09-19): mix = a weighted draw of enter / grow / travel
            # with any start point, settle point, growth law and bow; travel / mix-enter /
            # mix-grow force one kind but keep the drawn geometry. The legacy names (enter,
            # grow, plain) keep their exact approved behaviour.
            _entrance = None
            if _intro in ("mix", "travel", "mix-enter", "mix-grow"):
                _zc = 1.0
                for _zz in zoom_sched[_pS:_pS + _pF]:
                    _zc *= _zz
                _kind = {"mix": None, "travel": "travel", "mix-enter": "enter",
                         "mix-grow": "grow"}[_intro]
                _entrance = _plate.draw_entrance(
                    f"{spec.get('name')}:{_preg.get('name')}:{args.plate_entrance_seed}",
                    cfg["width"], cfg["height"], args.plate_limb, _zc, kind=_kind)
                _intro = _entrance["kind"]
            if args.plate_entrance:
                _entrance = json.loads(args.plate_entrance)
                _intro = _entrance.get("kind", "travel")
            _pl = _plate.Plate(_pk, _pS, _pE2, _pfa, _preg, _pnxt,
                               spec.get("style_suffix", ""),
                               cfg["width"], cfg["height"], zoom_sched[_pS:_pE2],
                               seed=cfg["seed"], n_card=_pF, s_limb=args.plate_limb,
                               outside=args.plate_outside, spin_rate=args.plate_spin,
                               intro=_intro, edge=_edge, entrance=_entrance)
            plates[_pk] = _pl
            for _x in range(_pS, min(_pE2, total)):
                plate_at[_x] = _pl
            # the plate owns the span: no resolve window in it; a cameo ON the planet card
            # is refused (the sprite-takeover class), a cameo on the NEXT card is DEFERRED —
            # it pastes from the first frame after the handoff (cork_dehesa: Janet on the
            # dusk_world card would otherwise vanish and the find-the-character caption
            # would lie)
            resolve_windows = [w for w in resolve_windows
                               if w["w1"] <= _pS or w["w0"] >= _pE2]
            for c in cameos:
                if _pS <= c["start"] < _pS + _pF:
                    c["_done"] = True
                    print(f"[dive] plate: cameo at frame {c['start']} (planet card {_pk} "
                          f"{_preg.get('name')}) refused", flush=True)
                elif _pS + _pF <= c["start"] < _pE2:
                    print(f"[dive] plate: cameo at frame {c['start']} ({_pnxt.get('name')}) "
                          f"deferred until the plate hands off", flush=True)
            print(f"[dive] PLATE ({args.plate}, intro {_intro}"
                  + (f" {_entrance}" if _entrance else
                     (' from ' + _edge if _intro == 'enter' else ''))
                  + f") card {_pk} "
                  f"{_preg.get('name')!r} -> {_pnxt.get('name')!r}: frames {_pS}..{_pE2 - 1} "
                  f"(bar line at {_pS + _pF}), globe {_pl.size0:.3f} -> {args.plate_limb} x "
                  f"width at the bar line, then until the frame is inside the disc", flush=True)
        if args.plate and not plates:
            print("[dive] PLATE: no planet-class card in range — flag has no effect", flush=True)
    # MICRO STAGE (lab, 2026-10-03 — PLAN "THE MICRO STAGE"): one card rendered through a
    # built 3-D world (engine/stage.py). Same ownership rules as the plate: no resolve
    # window, no cameo, no tracker inside the span; the stage owns aim + composition.
    stage_at = [None] * total
    stages = []
    if (args.stage or args.stage_auto
            or any(isinstance(r.get("stage"), dict) for r in spec.get("registers", []))) \
            and "registers" in spec and cfg["build"] != "out":
        import stage as _stagemod
        _sregs = spec["registers"]
        _snames = [r["name"] for r in _sregs]
        _srs = spec.get("render_start")
        _srot = _snames.index(_srs) if _srs in _snames else 0
        _sorder = _sregs[_srot:] + _sregs[:_srot]
        _scf = register_frame_counts(spec, cfg["fps"])
        # which cards: the CLI pair (lab) overrides; otherwise every card with a `stage` dict
        _splan = []
        if args.stage:
            if args.stage_card is None:
                sys.exit("[dive] --stage needs --stage-card K")
            _splan = [(args.stage_card, {"kit": args.stage,
                                         **(json.loads(args.stage_params) if args.stage_params else {})})]
        else:
            _splan = []
            for k, r in enumerate(_sorder):
                if isinstance(r.get("stage"), dict):
                    _splan.append((k, r["stage"]))
                elif args.stage_auto and r.get("stage") is not False:
                    _sg = _stagemod.suggest_stage(r)
                    if _sg:
                        _splan.append((k, _sg))
                        print(f"[dive] stage-auto: card {k} {r.get('name')!r} -> {_sg}", flush=True)
        for _sk, _sdef in _splan:
            if not (0 <= _sk < len(_scf)):
                sys.exit(f"[dive] stage card index {_sk} out of range 0..{len(_scf) - 1}")
            _sS = sum(_scf[:_sk])
            _sF = _scf[_sk]
            _sE = min(total, _sS + _sF)
            if _sk == 0 or (loop and _sE > total - loop["frames"]):
                print(f"[dive] stage: card {_sk} is the render-start/lap card — skipped (the loop "
                      f"tail owns its delivered copy)", flush=True)
                continue
            _sreg = _sorder[_sk]
            _szw = [zoom_sched[x] for x in range(_sS, _sE)]
            _sanchors = [(0.62, 0.40), (0.38, 0.40), (0.62, 0.60), (0.38, 0.60)]
            _skey = f"{spec.get('scaffold_name') or spec.get('name')}:{_sreg.get('name')}"
            _sanchor = _sanchors[_zlib.crc32(_skey.encode()) % 4]
            _sseed = args.stage_seed or (_zlib.crc32(_skey.encode()) % 100000)
            _stage = _stagemod.build_card_stage_v2(_sdef, _sreg.get("palette"), _szw, _sanchor,
                                                   cfg["width"], cfg["height"], seed=_sseed)
            _stage.S, _stage.E, _stage.fa = _sS, _sE, max(2, round(_sF * 0.25))
            _stage.card = _sk
            for _x in range(_sS, _sE):
                stage_at[_x] = _stage
            stages.append(_stage)
            resolve_windows = [w for w in resolve_windows if w["w1"] <= _sS or w["w0"] >= _sE]
            for c in cameos:
                if _sS <= c["start"] < _sE:
                    c["_done"] = True
                    print(f"[dive] stage: cameo at frame {c['start']} refused", flush=True)
            print(f"[dive] STAGE {_sdef.get('kit')} card {_sk} {_sreg.get('name')!r}: frames "
                  f"{_sS}..{_sE - 1}, {len(_stage.items)} items, anchor {_sanchor}, target depth "
                  f"{_stage.d_target:.2f} (advance {_stage.advance_total:.2f}), den {args.stage_den}/"
                  f"{args.stage_den_travel}, cn {args.stage_cn}, id {args.stage_id}", flush=True)
    if stages:
        try:   # provenance: run.json is written before the stages are built — append them
            _rj = json.loads((out_dir / "run.json").read_text())
            _rj["stage_cards"] = [(st_.card, st_.S, st_.E) for st_ in stages]
            (out_dir / "run.json").write_text(json.dumps(_rj, indent=2))
        except Exception:
            pass
    if args.plan_only:
        _pc = [(c["start"], c["end"], Path(c["sprite"]).stem) for c in cameos]
        print(f"[dive] PLAN ONLY: total {total} frames, lap_cut {lap_cut}, loop "
              f"{loop['frames'] if loop else 0} tail frames, cameos {_pc}, "
              f"plates {[(k, pl_.s, pl_.e) for k, pl_ in plates.items()]}", flush=True)
        try:
            shutil.rmtree(out_dir)          # no vN left behind for a plan
        except Exception:
            pass
        return
    plate_log = open(out_dir / "build" / "plate.jsonl", "a" if start_i else "w") \
        if plates else None
    _depth = None
    _trk = None
    _hero = None      # --hero-cn lab state: {"size": fraction-of-width}, per approach run
    # rotates each approach run's preferred rule-of-thirds corner; a --from-card prefix
    # already consumed start_run_idx runs, so the continuation keeps the rotation phase
    _run_idx = start_run_idx - 1
    if any(approach) or plates:
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
        # Phase D: this frame's camera move (None on camera-free frames — the usual case).
        # Roll folds into the rotation EVERYWHERE (transform, tracker, cameo, depth
        # alignment) so the exact-propagation contract holds; depth moves fuse into the
        # parallax residual below.
        cmv = cam_sched[i] if i < len(cam_sched) else None
        rot_i = cfg["rotate_per_frame"] + (cmv.get("roll", 0.0) if cmv else 0.0)
        seed = cfg["seed"] + i
        _st = stage_at[i] if i < len(stage_at) else None
        _pl = plate_at[i] if i < len(plate_at) else None
        if _pl is not None and (in_loop_tail(i) or _pl.done):
            _pl = None          # handed off: the next card's normal approach owns the frame
        if img is None and _pl is not None and cfg["build"] != "out":
            # PLANET PLATE at the render start: frame 0's txt2img renders the VOID plate
            # (no target, space negatives) and becomes the fed frame the plate composites
            # into — instead of a cold postcard the tail later homes onto.
            f0_prompt, f0_neg = _pl.prompts["void"], _plate.VOID_NEG + ", " + FRAME0_NEG_EXTRA
            print(f"[dive] frame-0 plate void: {f0_prompt[:110]}", flush=True)
            img = Image.open(io.BytesIO(run_workflow(
                build_workflow(cfg, f0_prompt, seed, neg_extra=f0_neg)))).convert("RGB")
        if img is None:
            # frame-0 ESTABLISH override (2026-08-02): the schedule's travel prompt names the
            # card's TARGET, and in txt2img SDXL composes a product-shot close-up around it
            # (all 5 renders of 08-01/02 opened close; seed-held ablations confirmed). Frame 0
            # renders the scene WIDE with no target + anti-close-up negatives instead; the
            # feedback chain inherits the wide framing from frame 1 on.
            if cfg["build"] != "out":
                f0_prompt, _f0_space = grammar.establish_prompt(spec)
            else:
                f0_prompt, _f0_space = prompt, False
            f0_neg = FRAME0_NEG_EXTRA + (ESTABLISH_SPACE_NEG if _f0_space else "")
            if f0_prompt != prompt:
                print(f"[dive] frame-0 establish{' (spaceless)' if _f0_space else ''}: "
                      f"{f0_prompt[:110]}", flush=True)
            wf = build_workflow(cfg, f0_prompt, seed, neg_extra=f0_neg)  # txt2img init
        else:
            drift = cfg["drift"]
            _th = 0.0
            if in_loop_tail(i):   # re-center so the loop-home composite lines up
                _th = (i - (total - loop["frames"]) + 1) / loop["frames"]
                if not lap_cut:
                    drift *= 1 - _th   # frame 0 is txt2img/centered: taper drift to zero
            # periods far longer than any video: reads as one slow directional
            # wander, not an oscillation (sinusoidal wobble was jarring)
            cx = 0.5 + drift * math.sin(2 * math.pi * i / 263)
            cy = 0.5 + drift * math.sin(2 * math.pi * i / 419 + 1.7)
            if _th and lap_cut:
                # LOOP LAP: the home frame (lap_cut-1, one step before the video start —
                # see loop-motion continuity below) was rendered WITH drift — steer the
                # tail's zoom center toward ITS drift phase, not toward dead center
                cx = (1 - _th) * cx + _th * (0.5 + cfg["drift"] * math.sin(2 * math.pi * (lap_cut - 1) / 263))
                cy = (1 - _th) * cy + _th * (0.5 + cfg["drift"] * math.sin(2 * math.pi * (lap_cut - 1) / 419 + 1.7))
            # TRACKER v3: the tracker owns the aim on approach frames (not the loop tail — the
            # loop mechanism owns that). The scheduled ×10 arrive-look-plunge zoom (zoom_sched)
            # grows the target; the tracker only steers WHERE.
            ap = approach[i] if i < len(approach) else None
            approaching = bool(ap) and not in_loop_tail(i) and cfg["build"] != "out"
            rwin = next((w for w in resolve_windows if w["w0"] <= i < w["w1"]), None) \
                if resolve_windows else None
            if rwin:
                approaching = False       # the field is still resolving — drift aim, no lock
            if _pl is not None:
                approaching, rwin = False, None   # the plate owns aim + composition
            if _st is not None:
                approaching, rwin = False, None   # the stage owns aim + composition
            ev = None
            if approaching:
                if _trk is None or _trk.ap is not ap:
                    _run_idx += 1
                    _trk = track.Tracker(ap, cfg["width"], cfg["height"],
                                         rot=cfg["rotate_per_frame"],
                                         cadence=cfg["track_cadence"],
                                         ease=cfg["approach_lock_ease"],
                                         model=cfg["track_model"])
                    # --hero-cn: seed the disc so it ends the run at ~full frame width —
                    # s0 = 1.05 / (product of the remaining scheduled zooms). The card's
                    # containment contract (target fills the view by the boundary),
                    # computed exactly instead of hoped for.
                    _hero = None
                    if args.hero_cn and HERO_ROUND.search(ap.get("phrase") or ""):
                        _jr, _Zr = i, 1.0
                        while _jr < len(approach) and approach[_jr] is ap:
                            _Zr *= zoom_sched[_jr]
                            _jr += 1
                        _hero = {"size": min(0.35, max(0.06, 1.05 / _Zr)),
                                 "n": max(1, _jr - i), "Z": 1.0, "pan": 0.0,
                                 "specks": hero_specks(cfg["width"], cfg["height"],
                                                       _zlib.crc32(f"{name}:{i}".encode()))}
                        print(f"[dive] HERO globe for {ap.get('phrase')!r}: run {_hero['n']}f, "
                              f"s0 {_hero['size']:.3f}"
                              + (f", orbit {args.hero_orbit:.0f} deg" if args.hero_orbit else ""),
                              flush=True)
                    elif args.hero_cn:
                        print(f"[dive] hero: {ap.get('phrase')!r} is not a round target — "
                              "standard approach", flush=True)
                if _trk.need_repick:
                    _trk.begin(img, seed=i, run_idx=_run_idx)
                ev = _trk.maybe_observe(img)
                row = {"i": i - 1, "mode": "track", "z": round(z, 4), **_trk.log_row()}
                if ev:
                    row["event"] = ev
                cx, cy = _trk.step(z, rot_i)
            else:
                _trk = None
                _hero = None
                if _pl is not None:
                    cx, cy = _pl.aim(z, rot_i, track)
                    row = {"i": i - 1, "mode": "plate", "z": round(z, 4),
                           "size": round(_pl.size, 4), "tx": round(_pl.tx, 4),
                           "ty": round(_pl.ty, 4)}
                elif _st is not None:
                    # the stage's anchor is the zoom's FIXED POINT: crop centre
                    # c = a - (a - 0.5)/z maps a onto itself (plate.aim's ease-0 formula)
                    _ax, _ay = _st.anchor
                    cx, cy = _ax - (_ax - 0.5) / z, _ay - (_ay - 0.5) / z
                    row = {"i": i - 1, "mode": "stage", "z": round(z, 4),
                           "tx": round(_ax, 4), "ty": round(_ay, 4)}
                else:
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
                _anch = palette_anchor_for(i) if (args.palette_anchor and not in_transition) else None
                if _anch:
                    fed = (_palette.transfer_lab(fed, _anch, args.palette_anchor)
                           if args.palette_anchor_mode == "lab"
                           else color_match(fed, _anch, args.palette_anchor))
                elif cfg["color_match"] and not in_transition and p_idx in phase_refs:
                    fed = color_match(fed, phase_refs[p_idx], cfg["color_match"])
                mask_ref = upload_image(
                    ring_mask(fed.width, fed.height, box),
                    f"zoomer_mask_{name}.png")
            else:
                fed = zoom_transform(img, z, rot_i, cx, cy)
                if _pl is not None and _pl.void is not None:
                    _pl.void = zoom_transform(_pl.void, z, rot_i, cx, cy)
                # DEPTH 2.0 Phase A: differential-parallax residual (PLAN "PARALLAX ERA").
                # Runs BEFORE detail_boost so the sharpen doubles as the post-warp unsharp
                # (the orbit-v3 lesson). Tapers out across the loop tail — the tail's job is
                # homing onto frame 0 and extra differential motion would fight the landing.
                _tap = 1.0
                if in_loop_tail(i):
                    _tap = max(0.0, 1.0 - (i - (total - loop["frames"]) + 1) / loop["frames"])
                pk = (cfg["parallax_gain"] if par_depth is not None else 0.0) * _tap
                if _pl is not None or _st is not None:
                    pk = 0.0          # the globe's/stage's scheduled growth IS the depth motion
                # Phase D: this frame's depth-move components (they ride the same depth
                # field + fused remap as the parallax; taper with it across the loop tail)
                _orb = _dol = _tlt = 0.0
                if cmv and par_depth is not None:
                    _orb = cmv.get("orbit", 0.0) * _tap
                    _dol = cmv.get("dolly", 0.0) * _tap
                    _tlt = cmv.get("tilt", 0.0) * _tap
                if pk or _orb or _dol or _tlt:
                    _pd = transform_depth(par_depth, z, rot_i, cx, cy,
                                          cfg["width"], cfg["height"])
                    par_depth = _pd            # propagated: stays aligned with the new frame
                    _m = float(np.median(_pd))
                    par_med = _m if par_med is None else 0.3 * _m + 0.7 * par_med
                    _lat = 0.0
                    if cfg["camera_micro"] and pk:
                        # plunge-ness from THIS frame's scheduled zoom: hover drifts,
                        # plunge surges (see camera_micro in DEFAULTS)
                        _zn = 0.5 if z_hi <= z_lo else min(1.0, max(
                            0.0, (z - z_lo) / (z_hi - z_lo)))
                        _lat = cfg["micro_drift_px"] * (1.0 - _zn) * math.sin(
                            2 * math.pi * (i % bar_frames) / bar_frames)
                        pk *= 1.0 + cfg["micro_surge"] * _zn
                    if _orb or _dol or _tlt:
                        # SPIRAL pivots on the locked tracked object — the world revolves
                        # around the thing we're diving toward, which holds its place
                        # (pivot depth sampled from the object's own patch). orbit/center
                        # anchors the median plane like the parallax does.
                        _piv, _pivd = (0.5, 0.5), None
                        if (cmv.get("pivot") == "target" and _trk is not None
                                and _trk.phase == "object"
                                and 0.05 < _trk.tx < 0.95 and 0.05 < _trk.ty < 0.95):
                            _piv = (_trk.tx, _trk.ty)
                            _px = int(_piv[0] * cfg["width"])
                            _py = int(_piv[1] * cfg["height"])
                            _patch = _pd[max(0, _py - 16):_py + 16,
                                         max(0, _px - 16):_px + 16]
                            if _patch.size:
                                _pivd = float(np.median(_patch))
                        fed, _stretch = _warp.camera_residual(
                            fed, _pd, z, pk, par_med, _lat, orbit_deg=_orb, pivot=_piv,
                            pivot_depth=_pivd, dolly_v=_dol, tilt_deg=_tlt)
                        if abs(_orb) + abs(_tlt) > 0.05:
                            # orbit-class warps smear at travel denoise (orbit-v3 gate) —
                            # re-synthesis must outpace resample loss
                            den = max(den, cfg["camera_den_floor"])
                    else:
                        fed, _stretch = _warp.parallax_residual(fed, _pd, z, pk, par_med, _lat)
                    _dboost = _warp.disocclusion_denoise(den, _stretch)
                    if plog:
                        _row = {"i": i, "k": round(pk, 3), "med": round(par_med, 3),
                                "lat": round(_lat, 1), "den": round(max(den, _dboost), 3),
                                "src": par_src}
                        if _orb or _dol or _tlt:
                            _row["cam"] = {"move": cmv.get("move"),
                                           "orbit": round(_orb, 4), "dolly": round(_dol, 4),
                                           "tilt": round(_tlt, 4),
                                           "pivot": [round(_piv[0], 3), round(_piv[1], 3)]}
                        plog.write(json.dumps(_row) + "\n")
                        plog.flush()
                    den = max(den, _dboost)
                fed = detail_boost(fed, cfg)
                _anch = palette_anchor_for(i) if (args.palette_anchor and not in_transition) else None
                if _anch:
                    fed = (_palette.transfer_lab(fed, _anch, args.palette_anchor)
                           if args.palette_anchor_mode == "lab"
                           else color_match(fed, _anch, args.palette_anchor))
                elif cfg["color_match"] and not in_transition and p_idx in phase_refs:
                    fed = color_match(fed, phase_refs[p_idx], cfg["color_match"])
                cam_pasted = False
                for c in cameos:
                    # init-once window (not `i == start`): frame 0 is txt2img and never reaches
                    # this branch, so a card-0 cameo (start=0) silently NEVER pasted — dollhouse's
                    # cameo is missing for this reason. Window semantics paste it from frame 1,
                    # and also survive --resume landing mid-window.
                    if not c.get("_done") and c["start"] <= i < c["end"] and _pl is None:
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
                            cam["px"], cam["py"], z, rot_i, cx, cy,
                            cfg["width"], cfg["height"])
                        cam["size"] *= z
                        if -0.1 < cam["px"] < 1.1 and -0.1 < cam["py"] < 1.1:
                            fed = paste_sprite(fed, *cam["art"], cam["px"],
                                               cam["py"], cam["size"])
                            cam_pasted = True
                if cam_pasted:
                    den = min(den, 0.32)   # keep the mascot's face recognizable
            plate_mask, plate_region, plate_ctl, plate_cn = None, None, None, 0.0
            plate_dd = plate_feed_cn = False
            plate_ipa_img, plate_ipa_w, plate_ipa_mask = None, 0.0, None
            plate_neg = None
            if _pl is not None:
                _first = _pl.tex is None
                if _first:
                    # assets, once per plate: the globe's surface texture (the NEXT card's
                    # world from straight above, square) + the void plate (this card's scene
                    # as space, frame-sized). Journey-keyed seeds so A/B arms share them.
                    _pdir = out_dir / "build" / "plate"
                    _pdir.mkdir(exist_ok=True)
                    # SQUARE (v4): a 2:1 landscape canvas made SDXL paint a seascape WITH A
                    # HORIZON, which wrapped onto the globe as an equator line and handed off
                    # to a sea-level view. The square top-down texture is mirrored to 2:1 in
                    # Plate.set_assets for the 360-degree map.
                    _tcfg = {**cfg, "width": 768, "height": 768}
                    _tseed = cfg["seed"] + 7000 + _pl.card_idx
                    _sseed = _tseed
                    for _stry in range(4):
                        _tex = Image.open(io.BytesIO(run_workflow(build_workflow(
                            _tcfg, _pl.prompts["surface"], _sseed,
                            neg_extra=_plate.SURFACE_NEG)))).convert("RGB")
                        if not args.plate_void_gate or _stry == 3:
                            break
                        _sb = _plate.surface_bait(_tex, model=cfg.get("track_model"))
                        if not _sb:
                            break
                        print(f"[dive] plate surface reads as a GROUND-LEVEL view "
                              f"({'/'.join(_sb[0])} — Florence: \"{_sb[1][:100]}\") — "
                              f"re-rolling seed ({_stry + 1}/3)", flush=True)
                        _sseed += 9973
                    _vseed = _tseed + 1000
                    for _vtry in range(4):
                        _void = Image.open(io.BytesIO(run_workflow(build_workflow(
                            cfg, _pl.prompts["void"], _vseed,
                            neg_extra=_plate.VOID_NEG + ", " + FRAME0_NEG_EXTRA)))).convert("RGB")
                        if not args.plate_void_gate or _vtry == 3:
                            break
                        _bait = _plate.void_bait(_void, model=cfg.get("track_model"))
                        if not _bait:
                            break
                        print(f"[dive] plate void reads as an OBJECT ({'/'.join(_bait[0])} — "
                              f"Florence: \"{_bait[1][:100]}\") — re-rolling seed "
                              f"({_vtry + 1}/3)", flush=True)
                        _vseed += 9973
                    _tex.save(_pdir / f"card{_pl.card_idx}_surface.png")
                    _void.save(_pdir / f"card{_pl.card_idx}_void.png")
                    _pl.set_assets(_tex, _void)
                    _pl.specks = hero_specks(cfg["width"], cfg["height"],
                                             _zlib.crc32(f"{spec.get('name')}:{_pl.card_idx}"
                                                         .encode()))
                    print(f"[dive] plate assets for card {_pl.card_idx}: surface "
                          f"{_pl.prompts['surface'][:80]!r} / void "
                          f"{_pl.prompts['void'][:60]!r}", flush=True)
                if not _pl.covered():
                    plate_neg = _plate.GLOBE_NEG    # no horizon reading while it is a globe
                if not _first:
                    fed = _pl.rotate_disc(fed)      # v3: revolve the carried interior
                fed = _pl.composite(fed, first=_first, live=(args.plate == "live"))
                _cov = _pl.covered()
                if _cov:
                    _pl.done = True     # this frame renders over the surface; from the next
                                        # frame the card's own tracked approach takes over
                if args.plate == "low":
                    den = min(den, 0.32)            # the cameo rule, frame-wide
                if args.plate in ("mask", "region") and not _cov:
                    plate_mask = upload_image(_pl.mask_image(_pl.noise_mask()),
                                              f"zoomer_pmask_{name}.png")
                    plate_dd = True
                if args.plate == "live" and not _cov:
                    # LIVE ARRIVAL (2026-09-18): denoise capped ONLY inside the disc (the
                    # ring regime), the void keeps the schedule's own denoise incl. the
                    # arrival boost; the void is HELD by IP-Adapter toward the void plate
                    # (attention-masked to outside the disc), ramping in over the arrival
                    # like the loop tail's homing — a live morph, not a dissolve.
                    # ABSOLUTE disc cap (v9): inside = 0.30/den, so the globe gets ~0.30
                    # effective denoise on EVERY frame — arm B's ring-free regime — even on
                    # the two arrival boosts (0.58), where v8's relative 0.8 let the disc run
                    # at ~0.46: it was re-read as a lumpy rock, then locked into a spiral.
                    _in = min(1.0, _pl.cap_now() / max(den, 1e-3))
                    plate_mask = upload_image(_pl.mask_image(_pl.noise_mask(inside=_in,
                                                                            outside=1.0)),
                                              f"zoomer_pmask_{name}.png")
                    plate_dd = True
                    if getattr(_pl, "void_ref", None) is None:
                        _pl.void_ref = upload_image(_pl.void, f"zoomer_pvoid_{name}.png")
                    _t = min(1.0, (_pl.frame + 1) / max(1, _pl.fa + 1))
                    plate_ipa_w = 0.25 + 0.35 * (_t * _t * (3 - 2 * _t))   # 0.25 -> 0.60
                    plate_ipa_img = _pl.void_ref
                    plate_ipa_mask = upload_image(_pl.mask_image(_pl.outside_mask()),
                                                  f"zoomer_pipam_{name}.png")
                if args.plate == "region" and not _cov:
                    plate_region = {"prompt": _pl.prompts["inside"],
                                    "mask": upload_image(_pl.mask_image(_pl.disc_mask()),
                                                         f"zoomer_prmask_{name}.png")}
                elif not _cov:
                    prompt = prompt + ", " + _plate.GLOBE_CLAUSE
                _pcn = cfg["approach_cn"] if args.plate_cn is None else args.plate_cn
                if not _cov and _pcn > 0:
                    # structure agrees with pixels: the hero depth dome at the globe's
                    # exact position/size over its void of specks
                    _himg = hero_depth(cfg["width"], cfg["height"], _pl.tx, _pl.ty, _pl.size,
                                       specks=_pl.specks, Z=_pl.Zacc)
                    plate_ctl = upload_image(_himg, f"zoomer_hero_{name}.png")
                    plate_cn = _pcn
                elif not _cov:
                    pass                            # v5: no CN while the globe is an object
                else:
                    plate_feed_cn = True            # over the surface: hold structure from
                                                    # the fed frame like a normal approach
                if _pl.frame <= 2 or _pl.frame % 4 == 0:
                    fed.save(out_dir / "build" / "plate" / f"{i:05d}_composite.png")
                    if plate_mask:
                        _pl.mask_image(_pl.noise_mask()).save(
                            out_dir / "build" / "plate" / f"{i:05d}_mask.png")
                if plate_log:
                    plate_log.write(json.dumps(_pl.row(i, den=round(den, 3),
                                                       mode=args.plate)) + "\n")
                    plate_log.flush()
            stage_ctl, stage_cn = None, 0.0
            if _st is not None:
                # MICRO STAGE: composite the built world at the exact scheduled geometry.
                # Identity ramps in across the arrival (the old texture resolves INTO the
                # stage under the costume denoise), holds through travel, relaxes over the
                # plunge; the stage's own depth is the CN so structure agrees with pixels.
                _sj = i - _st.S
                _srgb, _sdep = _st.frame_images(_sj)
                _sn = _st.E - _st.S
                if _sj < _st.fa:
                    _wid = 0.15 + 0.85 * (_sj + 1) / _st.fa
                    den = max(den, getattr(_st, "den_arrival", None) or args.stage_den)
                else:
                    _tq = max(0.0, (_sj - 0.75 * _sn) / max(1.0, 0.25 * _sn))
                    _wid = args.stage_id * (1.0 - 0.4 * min(1.0, _tq))
                    den = max(den, getattr(_st, "den_travel", None) or args.stage_den_travel)
                if _srgb.size != fed.size:
                    _srgb = _srgb.resize(fed.size, Image.LANCZOS)
                fed = Image.blend(fed, _srgb, _wid)
                stage_ctl = upload_image(_sdep, f"zoomer_stage_{name}.png")
                stage_cn = args.stage_cn
                _sdir = out_dir / "build" / "stage"
                _sdir.mkdir(parents=True, exist_ok=True)
                if _sj % 4 == 0 or _sj < 3:
                    _srgb.save(_sdir / f"{i:05d}_stage.png")
                    fed.save(_sdir / f"{i:05d}_fed.png")
                if tlog:
                    tlog.write(json.dumps({"i": i, "mode": "stage_frame", "wid": round(_wid, 3),
                                           "den": round(den, 3)}) + "\n")
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
                    # cases incl. both blendcn-reverted hard ones): the HOME frame's IMAGE
                    # conditions the generation with weight ramping in, so the WORLD converges
                    # while every frame is freshly rendered and still zooming. Depth-CN from
                    # the home frame aligns the landing composition over the morph window; a
                    # small FIXED pixel blend (never gap-scaled, max 0.35) seals the final
                    # frames. LOOP LAP (2026-08-23): the home is frame lap_cut — card 1's
                    # feedback-born start — instead of the txt2img frame 0.
                    t_home = (j + 1) / L_tail
                    # TRAJECTORY HOMING (2026-08-24 v3 — Phil: "still feels like a stop"):
                    # a STATIC home target makes the tail converge ASYMPTOTICALLY — as IPA
                    # rises every frame is pulled toward the same fixed picture, so
                    # frame-to-frame change decays below the zoom rate = a perceived
                    # deceleration into the loop (v2's one-step-early landing fixed the
                    # wrap, not the approach). The target now MOVES: tail frame j aims at
                    # original frame (lap_cut - L_tail + j), the reference trajectory
                    # leading into the video start — inter-frame change stays one zoom
                    # step all the way in, and the wrap is just the next step. The final
                    # target is lap_cut-1, preserving v2's continuous wrap.
                    if lap_cut:
                        _tidx = max(0, lap_cut - L_tail + j)
                        if loop.get("_home_idx") != _tidx:
                            loop["_home_img"] = Image.open(
                                frames_dir / f"{_tidx:05d}.png").convert("RGB")
                            loop["_home_ref"] = upload_image(
                                loop["_home_img"], f"zoomer_loop_home_{name}.png")
                            loop["_home_idx"] = _tidx
                    elif loop.get("_home_img") is None:
                        loop["_home_img"] = frame0
                        loop["_home_ref"] = upload_image(
                            loop["_home_img"], f"zoomer_loop_home_{name}.png")
                    # HOMING CURVE v2 (see DEFAULTS): smoothstep from a nonzero floor —
                    # the world converges across the whole tail, not in the last beat
                    _ss = t_home * t_home * (3 - 2 * t_home)
                    tail_ipa_w = (cfg["home_ipa_floor"]
                                  + (cfg["home_ipa_peak"] - cfg["home_ipa_floor"])
                                  * _ss ** cfg["home_ipa_shape"])
                    tail_ctl = loop["_home_ref"]
                    tail_cn = (cfg["home_cn_floor"]
                               + (cfg["home_cn_peak"] - cfg["home_cn_floor"]) * _ss)
                    if j >= L_tail - 6:
                        fed = Image.blend(fed, loop["_home_img"],
                                          0.35 * (j - (L_tail - 6) + 1) / 6)
            res_ctl, res_cn = None, 0.0
            if rwin and not in_loop_tail(i):
                # DEPTH LANGUAGE (Phil 2026-08-17, fix #1): invite the depth-of-field the
                # style tail otherwise suppresses — scoped to resolve windows only, no
                # palette/gloom change (fix #2 deliberately held)
                prompt = (prompt + ", enormous soft-focus shapes drifting close past the "
                          "camera, countless tiny ones far beyond, vast open depth between "
                          "them")
                _j = i - rwin["w0"]
                _n = rwin["w1"] - rwin["w0"]
                _scf_img = rwin["res"].frame_image(_j)
                _rdir = out_dir / "build" / "resolve"
                _rdir.mkdir(exist_ok=True)
                _scf_img.save(_rdir / f"{rwin['card']}_{_j:03d}.png")
                res_ctl = upload_image(_scf_img, f"zoomer_resolve_{name}.png")
                if _j < rwin["pre"]:
                    res_cn = 0.20 * (_j + 1) / rwin["pre"]
                else:
                    _t = (_j - rwin["pre"]) / max(1, _n - rwin["pre"])
                    res_cn = 0.6 * min(1.0, 0.35 + 1.3 * _t)
                    if _j >= _n - 2:
                        res_cn *= 0.6     # handoff taper into normal travel
            hero_ctl, hero_cn, hero_neg = None, 0.0, None
            if _hero is not None and approaching:
                # scheduled size: grows by exactly this frame's zoom so the disc reaches
                # ~full frame at the card boundary (s0 = 1.05/product-of-remaining-zooms).
                # (Do NOT adopt _trk.size: the tracker box is unclamped and propagates past
                # 1.0 once we zoom through it — adopting it hijacked the scheduled growth and
                # shut the hero/orbit off mid-approach, 2026-08-29.)
                _hero["size"] *= z
                _hero["Z"] *= z
                _hx = min(0.98, max(0.02, _trk.tx))
                _hy = min(0.98, max(0.02, _trk.ty))
                if _hero["size"] < 1.1:
                    if args.hero_orbit and _hero["size"] < 0.9:
                        # HERO ORBIT: DEG spread evenly over the run; the sphere interior
                        # revolves, the sky pans; revealed limb -> denoise boost
                        _dth = args.hero_orbit / _hero["n"]
                        _bg = args.hero_pan * _dth
                        _hero["pan"] += _bg
                        fed, _hst = _warp.hero_orbit(
                            fed, _hx * cfg["width"], _hy * cfg["height"],
                            _hero["size"] * cfg["width"] / 2, _dth, _bg)
                        fed = fed.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60))
                        den = max(den, _warp.disocclusion_denoise(den, _hst))
                    _himg = hero_depth(cfg["width"], cfg["height"], _hx, _hy, _hero["size"],
                                       specks=_hero["specks"], Z=_hero["Z"],
                                       pan=_hero["pan"])
                    _hdir = out_dir / "build" / "hero"
                    _hdir.mkdir(exist_ok=True)
                    _himg.save(_hdir / f"{i:05d}.png")
                    hero_ctl = upload_image(_himg, f"zoomer_hero_{name}.png")
                    hero_cn = 0.35 + 0.30 * min(1.0, _trk.frame / 12)
                    if _hero["size"] < 0.75:
                        # globe-in-a-void language while the globe is still an OBJECT in
                        # the frame; once it fills the view we are at its surface
                        prompt = prompt + ", " + HERO_CLAUSE
                        hero_neg = HERO_NEG
            _pal_ipa_img, _pal_ipa_w = None, 0.0
            if args.palette_ipa and not in_loop_tail(i) and plate_ipa_img is None:
                _pal_ipa_img = palette_ipa_for(i)
                _pal_ipa_w = args.palette_ipa if _pal_ipa_img else 0.0
            ref = upload_image(fed, f"zoomer_feed_{name}.png")
            wf = build_workflow(cfg, prompt, seed, init_image=ref, denoise=den,
                                prev_prompt=prev_prompt if in_transition else None,
                                blend=(k + 1) / (T + 1) if in_transition else 1.0,
                                mask_image=plate_mask or mask_ref,
                                diff_diffusion=plate_dd, region=plate_region,
                                # object-approach: depth-CN from the (zoomed) feedback holds the
                                # target's identity as it grows while pixels regenerate (not a
                                # paste). --hero-cn replaces it with the SCHEDULED-size synthetic
                                # depth (the disc IS a depth map — no preprocessor). In the loop
                                # tail the SAME channel carries frame 0's depth — never both.
                                ctrl_image=stage_ctl or res_ctl or hero_ctl or plate_ctl
                                or (ref if (approaching or plate_feed_cn) else tail_ctl),
                                cn_strength=stage_cn if stage_ctl
                                else res_cn if res_ctl
                                else (hero_cn if hero_ctl
                                      else (plate_cn if plate_ctl
                                            else (cfg["approach_cn"]
                                                  if (approaching or plate_feed_cn)
                                                  else tail_cn))),
                                depth_preproc=None if (stage_ctl or res_ctl or hero_ctl or plate_ctl)
                                else _depth,
                                ipa_image=(loop.get("_home_ref") if tail_ipa_w > 0.01
                                           else (plate_ipa_img if plate_ipa_img is not None
                                                 else _pal_ipa_img)),
                                ipa_weight=(tail_ipa_w if tail_ipa_w > 0.01
                                            else (plate_ipa_w if plate_ipa_img is not None
                                                  else _pal_ipa_w)),
                                ipa_mask=(None if tail_ipa_w > 0.01 else plate_ipa_mask),
                                neg_extra=", ".join(x for x in (hero_neg or plate_neg,
                                                                args.neg_extra) if x) or None)
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
                                                  neg_extra=f0_neg))
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
        # ── DEPTH 2.0 Phase A: refresh the parallax depth, aligned to the NEW frame ──────
        if cfg["parallax_gain"] and not in_loop_tail(i):
            # depth window: the CN window, or (Phase B, resolve_persist) the whole card —
            # the scaffold keeps being the depth source (never the CN) until its card ends
            rdep = next((w for w in resolve_windows
                         if w["w0"] <= i < w.get("wD", w["w1"])), None) \
                if resolve_windows else None
            if rdep is not None:
                par_depth, par_src = rdep["res"].frame(i - rdep["w0"]), "scaffold"
            elif par_depth is None or i % cfg["parallax_depth_every"] == 0:
                try:
                    fresh = _warp.quantize_planes(_warp.depth_via_comfy(img),
                                                  cfg["parallax_planes"])
                    par_depth, par_src = _warp.ema(par_depth, fresh, 0.6), "da"
                except Exception as e:      # a missed estimate must never kill a render —
                    print(f"[dive] parallax depth estimate failed ({e}) — "
                          "propagating the previous map", flush=True)
                    par_src = "prop"
            else:
                par_src = "prop"
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
        finish_video(spec, cfg, args, name, out_dir, frames_dir, total, exponent, loop, lap_cut)
    print(f"[dive] done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
