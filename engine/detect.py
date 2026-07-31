#!/usr/bin/env python3
"""Object localization for engine-2.0 targeted zoom. Uses Florence-2 (via ComfyUI) to find WHERE
the next zoom target is in a frame, so the engine can aim cx,cy at it instead of center-zooming
past it. Returns fractional boxes so it's resolution-independent.

Florence-2's box coordinates aren't exposed through ComfyUI's API as text, so we take its MASK
output (fill_mask), then recover boxes as connected components of that mask — which also gives us
the "which one" selection (largest / topmost / etc.) for busy multi-object scenes.

  detect(pil, "planet")                     -> largest matching box (cx,cy,w,h fractional) or None
  detect(pil, "planet", pick="topmost")     -> pick among matches
  boxes(pil, "planet")                       -> all matches, largest-first
"""
import json
import time
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dive  # noqa: E402

COMFY = dive.COMFY
MODEL = "microsoft/Florence-2-base-ft"     # base-ft: ~2s/frame, accurate enough for localization


def _submit(wf):
    data = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(COMFY + "/prompt", data, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["prompt_id"]


def _wait(pid, timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        try:
            h = json.load(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=10))
        except Exception:
            h = {}
        if pid in h and h[pid].get("outputs"):
            return h[pid]
        time.sleep(1.0)
    return None


def _fetch(im):
    url = (f"{COMFY}/view?filename={urllib.parse.quote(im['filename'])}"
           f"&subfolder={urllib.parse.quote(im.get('subfolder',''))}&type={im['type']}")
    from io import BytesIO
    return Image.open(BytesIO(urllib.request.urlopen(url, timeout=30).read()))


def florence_mask(pil, query, task="caption_to_phrase_grounding"):
    """Return Florence-2's fill_mask for `query` as an HxW float array in [0,1] (0 if nothing)."""
    import hashlib
    rgb = pil.convert("RGB")
    # name the upload by CONTENT (+query) — NOT (query,size). ComfyUI caches a workflow result by
    # its input values, so a name that repeats across different frames returns a STALE detection
    # from a prior frame. A content hash makes each distinct frame a fresh run (identical frames
    # legitimately reuse the cache).
    h = hashlib.md5(rgb.tobytes()).hexdigest()[:12]
    name = dive.upload_image(rgb, f"det_{h}_{abs(hash(query)) % 10**6}.png")
    wf = {
        "load": {"class_type": "LoadImage", "inputs": {"image": name}},
        "flm": {"class_type": "DownloadAndLoadFlorence2Model",
                "inputs": {"model": MODEL, "precision": "fp16"}},
        "run": {"class_type": "Florence2Run",
                "inputs": {"image": ["load", 0], "florence2_model": ["flm", 0],
                           "text_input": query, "task": task, "fill_mask": True,
                           "keep_model_loaded": True, "max_new_tokens": 512, "num_beams": 3,
                           "do_sample": False, "output_mask_select": "", "seed": 1}},
        "m2i": {"class_type": "MaskToImage", "inputs": {"mask": ["run", 1]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["m2i", 0], "filename_prefix": "det_mask"}},
    }
    h = _wait(_submit(wf))
    if not h:
        return None
    for o in h["outputs"].values():
        if o.get("images"):
            m = np.asarray(_fetch(o["images"][0]).convert("L"), dtype=np.float32) / 255.0
            return m
    return None


def _components(mask, thresh=0.5, grid=160, min_area=0.004):
    """Connected components of a binary mask, downsampled to `grid` rows for speed. Returns boxes
    (fractional) sorted largest-first: [{area, cx, cy, w, h, box=(x0,y0,x1,y1)}]."""
    H, W = mask.shape
    gh = grid
    gw = max(1, round(grid * W / H))
    small = np.asarray(Image.fromarray((mask * 255).astype("uint8")).resize((gw, gh)), dtype=np.float32) > (thresh * 255)
    lab = np.zeros((gh, gw), dtype=np.int32)
    out = []
    cur = 0
    for i in range(gh):
        for j in range(gw):
            if small[i, j] and lab[i, j] == 0:
                cur += 1
                q = deque([(i, j)]); lab[i, j] = cur
                mi = ma = i; mj = na = j; area = 0
                while q:
                    y, x = q.popleft(); area += 1
                    mi = min(mi, y); ma = max(ma, y); mj = min(mj, x); na = max(na, x)
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < gh and 0 <= nx < gw and small[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur; q.append((ny, nx))
                x0, x1 = mj / gw, (na + 1) / gw
                y0, y1 = mi / gh, (ma + 1) / gh
                af = area / (gh * gw)
                if af >= min_area:
                    out.append({"area": af, "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2,
                                "w": x1 - x0, "h": y1 - y0, "box": (x0, y0, x1, y1)})
    out.sort(key=lambda b: -b["area"])
    return out


# referring_expression_segmentation + a DESCRIPTIVE phrase gives a clean object mask (generic
# "the planet" degenerates to a half/full mask; "the round banded planet" nails it). journeys'
# next_target text already IS such a phrase, so we feed it straight in.
DEFAULT_TASK = "referring_expression_segmentation"
# a "box" spanning nearly the whole frame in BOTH dims is a failed segmentation (Florence returns a
# half/full mask when the phrase is too long/abstract or the object isn't there), not a real target.
FULLSPAN = 0.9


def boxes(pil, query, task=DEFAULT_TASK):
    m = florence_mask(pil, query, task)
    if m is None:
        return []
    return [b for b in _components(m) if not (b["w"] >= FULLSPAN and b["h"] >= FULLSPAN)]


def detect(pil, query, pick="largest", task=DEFAULT_TASK):
    """Locate the target; return one box dict (fractional) or None.
    pick: 'largest' | 'topmost' | 'centermost' | 'most_square'."""
    bs = boxes(pil, query, task)
    if not bs:
        return None
    if pick == "topmost":
        bs = sorted(bs, key=lambda b: b["cy"])
    elif pick == "centermost":
        bs = sorted(bs, key=lambda b: (b["cx"] - 0.5) ** 2 + (b["cy"] - 0.5) ** 2)
    elif pick == "most_square":
        bs = sorted(bs, key=lambda b: abs(b["w"] - b["h"]))
    return bs[0]


GROUND = "caption_to_phrase_grounding"
SEG = "referring_expression_segmentation"


def _clean(b, min_side=0.03, min_area=0.006, max_aspect=6.0):
    """Reject Florence's garbage boxes (edge slivers, full-frame degenerate masks, dust specks)."""
    w, h = b["w"], b["h"]
    if w < min_side or h < min_side:      return False
    if w >= FULLSPAN and h >= FULLSPAN:   return False
    if b["area"] < min_area:              return False
    ar = w / h if h else 99.0
    return 1 / max_aspect <= ar <= max_aspect


def locate(pil, query, pick="largest", model="microsoft/Florence-2-large-ft"):
    """Robust semantic localization: run BOTH Florence tasks (they catch DIFFERENT cases — grounding
    found the lighthouse, segmentation the galaxy, both the dark planet) and return the best CLEAN
    box, or None if the object isn't (yet) distinguishable. Semantic → finds a dark planet a
    brightness heuristic can't. ~2 model calls/frame; real-time isn't needed (Phil 2026-07-31)."""
    global MODEL
    if model:
        MODEL = model
    cands = []
    for task in (GROUND, SEG):
        cands += [b for b in boxes(pil, query, task) if _clean(b)]
    if not cands:
        return None
    if pick == "centermost":
        cands.sort(key=lambda b: (b["cx"] - 0.5) ** 2 + (b["cy"] - 0.5) ** 2)
    else:
        cands.sort(key=lambda b: -b["area"])
    return cands[0]


if __name__ == "__main__":
    # CLI: python3 engine/detect.py <frames_dir> <query> <frame> [frame ...]  -> print boxes
    src = Path(sys.argv[1]); query = sys.argv[2]
    for fi in [int(x) for x in sys.argv[3:]]:
        p = src / f"{fi:05d}.png"
        bs = boxes(Image.open(p), query)
        print(f"frame {fi}: {len(bs)} '{query}' box(es)")
        for b in bs:
            print(f"   area={b['area']:.3f} center=({b['cx']:.2f},{b['cy']:.2f}) size=({b['w']:.2f}x{b['h']:.2f})")
