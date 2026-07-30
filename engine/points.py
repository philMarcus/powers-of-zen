#!/usr/bin/env python3
"""Prominent-point picker for engine-2.0 object emergence. Before the next object is big enough
for Florence to detect, we pick a distinct POINT already on screen and commit to zooming into it
while the prompt paints the target forming there ("it becomes an elephant for all we care"). This
solves the chicken-and-egg (too small to detect → never grows) AND gives the dive an intentional
off-center DIRECTION instead of a boring dead-center zoom.

Method: difference-of-Gaussians (blob response — a compact spot that differs from its surround,
bright-on-dark OR dark-on-bright — NOT edges), weighted toward a moderate off-center band so the
heading is interesting but not extreme. Pure numpy/PIL (fast, no GPU). Deterministic given a seed.
"""
import numpy as np
from PIL import Image, ImageFilter


def _dog(im_l, r_small, r_large):
    """|blur_small - blur_large| — high on compact blobs of size ~r_large, low on flat areas/edges."""
    s = np.asarray(im_l.filter(ImageFilter.GaussianBlur(r_small)), dtype=np.float32)
    b = np.asarray(im_l.filter(ImageFilter.GaussianBlur(r_large)), dtype=np.float32)
    return np.abs(s - b)


def pick_point(pil, size=160, ecc_peak=0.28, ecc_lo=0.12, ecc_hi=0.46,
               blob_frac=0.035, seed=0, avoid=None, avoid_r=0.14):
    """Return (cx, cy) fractional of the most prominent OFF-CENTER blob. `avoid` = a point to
    suppress (so consecutive picks differ). `seed` breaks near-ties deterministically."""
    w0, h0 = pil.size
    W = size
    H = max(8, round(size * h0 / w0))
    im = pil.convert("L").resize((W, H))
    dog = _dog(im, 1.0, max(2.0, blob_frac * size))
    dog = np.asarray(Image.fromarray(np.clip(dog, 0, 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ex, ey = xx / W - 0.5, yy / H - 0.5
    ecc = np.sqrt(ex * ex + ey * ey) / 0.5                     # 0 center .. ~1 corner
    w = np.exp(-((ecc - ecc_peak) ** 2) / (2 * 0.16 ** 2))     # prefer a moderate off-center ring
    w[ecc < ecc_lo] = 0.04                                     # kill dead-center
    w[ecc > ecc_hi] *= 0.25                                    # discourage the very edges
    if avoid is not None:
        ax, ay = avoid
        d = np.sqrt((xx / W - ax) ** 2 + (yy / H - ay) ** 2)
        w = w * np.clip(d / avoid_r, 0.0, 1.0)                 # suppress near the avoided point

    score = dog * w
    # tiny deterministic jitter to break ties differently per approach (varies direction)
    rng = np.random.default_rng(seed)
    score = score + rng.random(score.shape).astype(np.float32) * (score.max() * 1e-3 + 1e-6)
    idx = int(np.argmax(score))
    py, px = divmod(idx, W)
    return round((px + 0.5) / W, 4), round((py + 0.5) / H, 4)


if __name__ == "__main__":
    # CLI: draw the picked point on frames so we can eyeball it.
    import sys
    from PIL import ImageDraw
    src = sys.argv[1]
    OUT = ("/tmp/claude-0/-mnt-c-Users-Phil-zoomer/bcbde943-89be-485d-a581-0eb08e40ff22/scratchpad")
    tiles = []
    for a in sys.argv[2:]:
        p = f"{src}/{int(a):05d}.png"
        im = Image.open(p).convert("RGB")
        cx, cy = pick_point(im)
        d = ImageDraw.Draw(im)
        x, y = cx * im.width, cy * im.height
        r = im.width * 0.06
        d.ellipse([x - r, y - r, x + r, y + r], outline=(0, 255, 0), width=5)
        d.line([x - r, y, x + r, y], fill=(0, 255, 0), width=3)
        d.line([x, y - r, x, y + r], fill=(0, 255, 0), width=3)
        d.text((8, 8), f"f{a} ({cx:.2f},{cy:.2f})", fill=(0, 255, 0))
        tiles.append(im.resize((216, 384)))
    cols = min(4, len(tiles)); rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 216, rows * 384), "black")
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * 216, (k // cols) * 384))
    sheet.save(f"{OUT}/points.png"); print(f"{OUT}/points.png")
