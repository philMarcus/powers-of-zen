#!/usr/bin/env python3
"""Sea donors (Phil's reframe 2026-08-13): every library image is an INFINITE SEA.

  protein_sea    — 80+ real PDB backbones filling the frame at all depths, fog not void
  lattice_sea    — infinite rod-and-ball lattice in perspective (the mineral_heart look)
  sea_depth_*    — DEPTH SCAFFOLDS: procedural depth maps of instance seas, to drive the
                   depth ControlNet so composition is enforced structurally
"""
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path("/mnt/c/Users/Phil/zoomer/output/realm_refs/math")
W, H = 832, 1152
rng = np.random.default_rng(9)


def save(name, rgb):
    Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8)).save(OUT / name)
    print("wrote", name)


def rot(e):
    a, b, c = e
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(c), -np.sin(c)], [0, np.sin(c), np.cos(c)]])
    return Rz @ Ry @ Rx


def line(img, x0, y0, x1, y1, col, w):
    n = max(abs(int(x1) - int(x0)), abs(int(y1) - int(y0)), 1)
    xs = np.linspace(x0, x1, n).astype(int)
    ys = np.linspace(y0, y1, n).astype(int)
    for dx in range(-w, w + 1):
        for dy in range(-w, w + 1):
            if dx * dx + dy * dy > w * w:
                continue
            xx, yy = xs + dx, ys + dy
            ok = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
            img[yy[ok], xx[ok]] = np.maximum(img[yy[ok], xx[ok]], col)


def smooth(p, w=5):
    k = np.ones(w) / w
    up = np.stack([np.interp(np.linspace(0, len(p) - 1, len(p) * 4),
                             np.arange(len(p)), p[:, i]) for i in range(3)], 1)
    return np.stack([np.convolve(up[:, i], k, mode="valid") for i in range(3)], 1)


def protein_sea():
    txt = urllib.request.urlopen("https://files.rcsb.org/download/4HHB.pdb",
                                 timeout=30).read().decode()
    tr = np.array([(float(l[30:38]), float(l[38:46]), float(l[46:54]))
                   for l in txt.splitlines()
                   if l.startswith("ATOM") and l[13:15].strip() == "CA" and l[21] == "A"])
    tr -= tr.mean(0)
    tr /= np.abs(tr).max()
    trs = smooth(tr)
    img = np.zeros((H, W, 3), np.float32)
    fogc = np.array([0.05, 0.03, 0.10])
    palette = [(1.0, 0.5, 0.8), (0.5, 0.85, 1.0), (1.0, 0.8, 0.35),
               (0.55, 1.0, 0.6), (0.8, 0.6, 1.0), (1.0, 0.55, 0.4)]
    places = sorted([(0.55 + 5.5 * rng.random() ** 1.6, i) for i in range(85)], reverse=True)
    for depth, i in places:
        R = rot(rng.random(3) * 2 * np.pi)
        p = trs @ R.T
        scale = 0.9 / depth
        cx, cy = rng.uniform(-0.05, 1.05), rng.uniform(-0.05, 1.05)
        px = ((p[:, 0] * scale * 0.42 + cx) * W).astype(int)
        py = ((p[:, 1] * scale * 0.42 * (W / H) + cy) * H).astype(int)
        base = np.array(palette[i % len(palette)])
        fade = min(1.0, 1.15 / depth)
        col = base * fade + fogc * (1 - fade)
        for k in range(len(px) - 1):
            line(img, px[k], py[k], px[k + 1], py[k + 1], col, max(1, int(round(3.6 / depth))))
    img += fogc * 0.5
    pil = Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))
    save("protein_sea.png", np.asarray(pil.filter(ImageFilter.GaussianBlur(0.7)),
                                       np.float32) / 255)


def lattice_sea():
    """Infinite rod-and-ball lattice in single-point perspective (the mineral_heart look)."""
    img = np.zeros((H, W, 3), np.float32)
    fogc = np.array([0.02, 0.04, 0.08])
    pts = []
    for ix in range(-6, 7):
        for iy in range(-8, 9):
            for iz in range(1, 14):
                pts.append((ix + 0.06 * np.sin(iz), iy + 0.06 * np.cos(ix), iz))
    def proj(p):
        x, y, z = p
        zz = z + 0.4
        return (0.5 + 0.34 * x / zz) * W, (0.5 + 0.34 * y / zz) * H, zz
    # struts to +x, +y, +z neighbours
    idx = {(round(p[0], 1), round(p[1], 1), p[2]): p for p in
           [(ix, iy, iz) for ix in range(-6, 7) for iy in range(-8, 9) for iz in range(1, 14)]}
    order = sorted(idx.values(), key=lambda p: -p[2])
    for p in order:
        x0, y0, z0 = proj(p)
        if not (-100 < x0 < W + 100 and -100 < y0 < H + 100):
            continue
        fade = min(1.0, 2.6 / z0)
        col = np.array([0.55, 0.9, 1.0]) * fade + fogc * (1 - fade)
        for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            q = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
            if q in idx:
                x1, y1, _ = proj(q)
                line(img, x0, y0, x1, y1, col * 0.55, max(1, int(round(2.2 / z0 * 3))))
    for p in order:      # balls on top
        x0, y0, z0 = proj(p)
        if not (0 <= x0 < W and 0 <= y0 < H):
            continue
        fade = min(1.0, 2.6 / z0)
        col = np.array([1.0, 0.75, 0.35]) * fade + fogc * (1 - fade)
        r = max(1, int(round(7.5 / z0 * 3)))
        yy, xx = np.mgrid[max(0, int(y0) - r):min(H, int(y0) + r + 1),
                          max(0, int(x0) - r):min(W, int(x0) + r + 1)]
        m = (xx - x0) ** 2 + (yy - y0) ** 2 <= r * r
        img[yy[m], xx[m]] = np.maximum(img[yy[m], xx[m]], col)
    img += fogc
    save("lattice_sea.png", img)


def sea_depth_scaffold(name, n=110, seed=3):
    """Depth map of an instance SEA: white=near. Drives the depth ControlNet so any prompt
    renders as countless instances at stochastic depths with a big near occluder."""
    r2 = np.random.default_rng(seed)
    depth = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    for _ in range(n):
        z = 0.5 + 5.0 * r2.random() ** 1.7          # near .. far
        rad = 130.0 / z
        cx, cy = r2.uniform(-0.05, 1.05) * W, r2.uniform(-0.05, 1.05) * H
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (rad * rad)
        blob = np.exp(-d2 * 1.4) * (1.3 / z)
        depth = np.maximum(depth, blob)
    depth = np.clip(depth, 0, 1) ** 0.85
    save(name, np.stack([depth] * 3, -1))


protein_sea()
lattice_sea()
sea_depth_scaffold("sea_depth_a.png", seed=3)
sea_depth_scaffold("sea_depth_b.png", seed=8)
