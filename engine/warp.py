#!/usr/bin/env python3
"""ENGINE 3 warp core — depth-aware reprojection of a frame (planned 2026-08-15).

Crop-and-reimagine was the special case "zoom" of warp-and-reimagine: these primitives
move the camera any way, and the re-diffusion invents what the move reveals. Every warp
takes the frame plus its DEPTH (estimated by the same DepthAnything the CN already uses),
displaces pixels by depth-dependent amounts (parallax), and reports a DISOCCLUSION measure
so callers can boost denoise where geometry was revealed.

Primitives (all take/return PIL RGB; depth is float HxW in [0,1], NEAR = 1):
  truck(img, depth, dx, dy)      — lateral camera translation (near slides farther)
  orbit(img, depth, deg, pivot)  — camera revolves about a vertical axis through `pivot`;
                                   pixels nearer than the pivot plane sweep opposite the
                                   farther field: TRUE revolution, not roll
  tilt(img, pitch)               — perspective pitch (homography; top recedes/advances)
  dolly(img, depth, v)           — forward translation: depth-dependent scale (vertigo when
                                   run against the zoom)

Depth utilities:
  depth_via_comfy(img)           — one DepthAnythingV2 inference through ComfyUI
  ema(prev, new, alpha)          — temporal smoothing (estimator shimmer kills warps)

The iron law lives with the CALLER: these are per-frame steps; the scale-zoom schedule is
applied separately and never altered here.
"""
import io
import time

import numpy as np
import requests
from PIL import Image

COMFY = "http://localhost:8188"


# ── depth ─────────────────────────────────────────────────────────────────────────────
def depth_via_comfy(img, timeout=120):
    """DepthAnythingV2 on one frame via ComfyUI; returns float HxW in [0,1], near=1."""
    import engine.dive as dive
    name = dive.upload_image(img, "warp_depth_in.png")
    wf = {
        "img": {"class_type": "LoadImage", "inputs": {"image": name}},
        "prep": {"class_type": "DepthAnythingV2Preprocessor",
                 "inputs": {"image": ["img", 0], "resolution": 512}},
        "save": {"class_type": "SaveImage",
                 "inputs": {"images": ["prep", 0], "filename_prefix": "warp_depth/d"}},
    }
    r = requests.post(f"{COMFY}/prompt", json={"prompt": wf}, timeout=30)
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=30).json()
        if pid in h:
            for node in h[pid].get("outputs", {}).values():
                for im in node.get("images", []):
                    v = requests.get(f"{COMFY}/view", params={
                        "filename": im["filename"], "subfolder": im.get("subfolder", ""),
                        "type": im.get("type", "output")}, timeout=60)
                    d = np.asarray(Image.open(io.BytesIO(v.content)).convert("L"),
                                   np.float32) / 255.0
                    if d.shape != (img.height, img.width):
                        d = np.asarray(Image.fromarray((d * 255).astype(np.uint8))
                                       .resize((img.width, img.height)), np.float32) / 255.0
                    return d
        time.sleep(0.3)
    raise TimeoutError("depth preproc timed out")


def ema(prev, new, alpha=0.6):
    """Temporal smoothing: alpha * new + (1-alpha) * prev (prev may be None)."""
    return new if prev is None else alpha * new + (1.0 - alpha) * prev


# ── core remap ────────────────────────────────────────────────────────────────────────
def _remap(img, map_x, map_y):
    """Inverse-map bilinear sample: out[y, x] = img[map_y, map_x]. Also returns the
    disocclusion measure: local stretching of the sampling grid (>1 = revealed area)."""
    a = np.asarray(img, np.float32)
    H, W = a.shape[:2]
    x0 = np.clip(np.floor(map_x).astype(int), 0, W - 2)
    y0 = np.clip(np.floor(map_y).astype(int), 0, H - 2)
    fx = np.clip(map_x - x0, 0, 1)[..., None]
    fy = np.clip(map_y - y0, 0, 1)[..., None]
    out = (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
           + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)
    # stretch = how much source area each output pixel spans; disocclusion where the map
    # gradient collapses (neighbouring outputs sample nearly the same source point)
    gx = np.abs(np.gradient(map_x, axis=1))
    gy = np.abs(np.gradient(map_y, axis=0))
    stretch = np.maximum(1.0 - np.minimum(gx, 1.0), 1.0 - np.minimum(gy, 1.0))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), stretch


def _near(depth):
    """0 at the far plane, 1 at the nearest — the parallax weight."""
    return np.clip(depth, 0.0, 1.0)


# ── primitives ────────────────────────────────────────────────────────────────────────
def truck(img, depth, dx=0.0, dy=0.0):
    """Lateral move in px at the NEAR plane; farther content moves proportionally less."""
    H, W = depth.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    n = _near(depth)
    return _remap(img, xx + dx * n, yy + dy * n)


def orbit(img, depth, deg, pivot=(0.5, 0.5), pivot_depth=0.55, swing=1.0):
    """Camera revolves `deg` about a vertical axis through the pivot point.
    Approximation for small per-frame angles: horizontal parallax proportional to
    (depth - pivot_depth): nearer-than-pivot sweeps one way, farther the other, scaled by
    distance from the pivot column (things at frame edge sweep more). `swing` scales the
    vertical bow (slight ellipse) that sells the revolve."""
    H, W = depth.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rad = np.deg2rad(deg)
    px = pivot[0] * W
    rel = (depth - pivot_depth)                       # + near of pivot, - beyond it
    dx = np.sin(rad) * rel * W * 0.55
    bow = (1.0 - np.cos(rad)) * rel * (xx - px) * 0.35 * swing
    return _remap(img, xx + dx, yy + bow)


def tilt(img, pitch_deg, horizon=0.45):
    """Perspective pitch via homography: positive pitch lifts the horizon (top recedes),
    the classic pitch-over from face-on toward oblique. Depth-independent base move —
    combine with truck/dolly for foreshortened terrain."""
    W, H = img.size
    p = np.deg2rad(pitch_deg)
    squeeze = np.tan(p) * 0.5
    hy = horizon * H
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = (yy - hy) / H
    scale = 1.0 + squeeze * t                          # rows above horizon compress
    map_x = (xx - W / 2) / np.maximum(scale, 0.4) + W / 2
    map_y = hy + (yy - hy) / np.maximum(scale, 0.4)
    return _remap(img, map_x, map_y)


def dolly(img, depth, v=0.01):
    """Forward translation: each pixel scales about the center by 1 + v*near(depth) —
    near grows faster than far (true perspective change; against the zoom = vertigo)."""
    H, W = depth.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    n = _near(depth)
    s = 1.0 + v * n
    map_x = (xx - W / 2) / s + W / 2
    map_y = (yy - H / 2) / s + H / 2
    return _remap(img, map_x, map_y)


def disocclusion_denoise(base_den, stretch, k=0.25, cap=0.85):
    """A caller helper: lift denoise where the warp revealed geometry.
    Returns a scalar boost from the mean stretch (frame-global for now; the masked local
    variant lands with the full engine-3 integration)."""
    return min(cap, base_den + k * float(np.clip(stretch, 0, 1).mean()))
