#!/usr/bin/env python3
"""Procedural depth scaffolds for RESOLVE-ON-APPROACH realm transitions (2026-08-14).

Phil's microscope grammar: a realm shift is never a camera pulling wide — the current
texture RESOLVES into countless tiny instances of the next realm, which grow on approach
until the dive picks one. These scaffolds impose that structure through the depth
ControlNet during a transition window: instances are placed in WORLD SPACE once per
transition (seeded), then projected through the same per-frame zoom the engine applies,
so they enter sub-pixel and grow exactly as a real approach would — the conditioning is
derived from the camera motion and cannot fight it. Pure numpy: deterministic, free, no
foreign image content (the feedback chain + prompt still own the pixels).

Arrangement MODES (chosen per card from its REALMS band; journey `resolve` field overrides):
  sea      — free 3-D scatter (cells, plankton, stars, molecules, diatoms)
  lattice  — regular ranks with slight jitter (crystals, atoms)
  surface  — instances on an oblique ground (forest crowns, city blocks, terrain)
  web      — strands with bright junctions (cosmic web, neuron nets, mycelium)
Single-object shifts (approach ONE thing) are NOT scaffolded — the tracker already owns
those. Seams keep their own treatment.

Output frames are float [0,1], near=bright — the polarity controlnet-depth-sdxl expects.
"""
import numpy as np

W, H = 576, 1024
D_MIN, D_MAX = 0.5, 16.0     # instance depth range (~1.5 decades, log-uniform sampling)


def depth_value(d):
    """Depth-map brightness for an instance at distance d: LOG-mapped onto the full 0..1
    range (near 1.0 -> far ~0.06), so the ControlNet sees genuinely layered planes instead
    of a clamp-bright wall (the 2-D reading Phil flagged)."""
    t = np.log(np.clip(d, D_MIN, D_MAX) / D_MIN) / np.log(D_MAX / D_MIN)
    return float(1.0 - 0.94 * t)


def _gauss_blob(depth, cx, cy, r, val, hard=True):
    """Stamp a blob. V3 (2026-08-17): when stamped far->near (painter's algorithm) the
    HARD core OVERWRITES what's behind it — a real occlusion edge, so the CN sees spheres
    IN space, not discs ON a plane. Soft gaussian rim outside the core."""
    x0, x1 = max(0, int(cx - 3 * r)), min(W, int(cx + 3 * r) + 1)
    y0, y1 = max(0, int(cy - 3 * r)), min(H, int(cy + 3 * r) + 1)
    if x0 >= x1 or y0 >= y1 or r < 0.4:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    g = np.exp(-d2 / (2 * r * r)) * val
    if hard and r >= 2.0:
        core = d2 <= (0.72 * r) ** 2
        region = depth[y0:y1, x0:x1]
        region[core] = val * (1.0 - 0.25 * (np.sqrt(d2[core]) / (0.72 * r)) ** 2)
        depth[y0:y1, x0:x1] = np.maximum(region, g)
    else:
        depth[y0:y1, x0:x1] = np.maximum(depth[y0:y1, x0:x1], g)


def _project(p0, center, Z):
    """World point -> frame point after cumulative zoom Z about `center` (fractional)."""
    return (center[0] + (p0[0] - center[0]) * Z, center[1] + (p0[1] - center[1]) * Z)


class Resolver:
    """One transition's scaffold: build once, render a depth frame per step.

    zooms: per-frame zoom factors across the window (from the render schedule).
    aim:   per-frame (cx, cy) fractional zoom centers (from drift/tracker plan).
    mode:  sea | lattice | surface | web
    density/size/near_frac tune the field; seed pins it per (journey, card).
    """

    def __init__(self, mode, zooms, aims, seed=0, density=1.0, size=1.0, variant=None,
                 parallax=0.006):
        """parallax: per-frame lateral drift of the NEAREST layer (fraction of frame width);
        deeper layers drift proportionally less (1/d) — near things slide past faster, which
        is what makes the field read 3-D instead of a flat pattern (Phil 2026-08-14)."""
        self.mode = mode
        self.variant = variant
        self.parallax = parallax
        self.zooms = list(zooms)
        self.aims = list(aims)
        self.rng = np.random.default_rng(seed)
        self.density = density
        self.size = size
        self.Z = np.cumprod([1.0] + self.zooms)      # Z[f] = zoom at frame f vs start
        n_base = {"sea": 450, "lattice": 0, "surface": 90, "web": 42}[mode]
        self.items = self._build(int(n_base * density))

    def _build(self, n):
        rng = self.rng
        if self.mode == "sea":
            # 3-D scatter: xy in an over-wide region (things fly out as we zoom), layer
            # depth d gives size + brightness; clumped by mixing two spatial scales
            base = rng.random((n, 2)) * [1.6, 1.6] - 0.3
            clump = rng.random((max(4, n // 22), 2)) * [1.4, 1.4] - 0.2
            picks = clump[rng.integers(0, len(clump), n // 2)]
            base[: n // 2] = picks + rng.normal(0, 0.07, (n // 2, 2))
            # PHASE 1 (Phil 2026-08-15): LOG-UNIFORM depth across ~1.5 decades — equal
            # instances per octave, so a few huge near occluders stand off a mid crowd and
            # a deep speckle field, instead of "big and little things in a 2-D plane".
            d = D_MIN * (D_MAX / D_MIN) ** rng.random(n)
            return [("blob", (x, y), d_) for (x, y), d_ in zip(base, d)]
        if self.mode == "lattice":
            # LATTICE LIBRARY (Phil 2026-08-14: beyond cubic; variant selectable per card
            # via journey resolve.variant, listed in VARIATIONS.md): one-point perspective,
            # deeper layers contract toward the vanishing point.
            kind = self.variant or "cubic"
            items = []
            vp = (0.5, 0.48)
            layers = (0.6, 0.95, 1.5, 2.4, 3.8, 6.1, 9.7)   # log-spaced, ~1.2 decades
            for li, iz in enumerate(layers):
                step = 0.15
                for ix in np.arange(-0.6, 1.7, step):
                    row = 0
                    for iy in np.arange(-0.6, 1.9, step):
                        ox, oy, keep = 0.0, 0.0, True
                        if kind == "hex":              # close-packed: offset alternate rows
                            ox = (row % 2) * step / 2
                        elif kind == "diamond":        # two interpenetrating sublattices
                            ox = oy = (li % 2) * step / 2
                            keep = (round(ix / step) + round(iy / step)) % 2 == 0
                        elif kind == "layered":        # graphite sheets: tight rows, wide gaps
                            oy = 0.0
                            keep = (row % 3) != 2
                        if keep:
                            j = rng.normal(0, 0.006, 2)
                            x = vp[0] + (ix + ox - vp[0]) / iz + j[0]
                            y = vp[1] + (iy + oy - vp[1]) / iz + j[1]
                            items.append(("blob", (x, y), iz))
                        row += 1
            return items
        if self.mode == "surface":
            # oblique ground: rows lower in frame are nearer; crowns sit on the ground
            items = [("ground", None, None)]
            for _ in range(int(n * 1.5)):
                x, y = rng.random() * 1.4 - 0.2, rng.random() * 1.4 - 0.2
                d = 0.5 * (14.0) ** (max(0.0, 1.0 - y) ** 1.15) + rng.random() * 0.2  # top=far, log ramp
                items.append(("bigblob", (x, y), d))
            return items
        if self.mode == "web":
            # CONNECTED network (Phil 2026-08-14: loose strings are not a web): nodes in
            # depth layers, each joined to its nearest neighbours -> closed cells + junctions
            nodes = []
            for _ in range(n):
                nodes.append((rng.random() * 1.5 - 0.25, rng.random() * 1.5 - 0.25,
                              D_MIN * (D_MAX / D_MIN) ** rng.random()))
            P = np.array(nodes)
            items = []
            # weight depth so links prefer same-layer neighbours (webs live in sheets)
            D2 = ((P[:, None, 0] - P[None, :, 0]) ** 2
                  + (P[:, None, 1] - P[None, :, 1]) ** 2
                  + 2.2 * (P[:, None, 2] - P[None, :, 2]) ** 2)
            np.fill_diagonal(D2, np.inf)
            seen = set()
            for i in range(len(P)):
                for jn in np.argsort(D2[i])[:3]:
                    key = (min(i, int(jn)), max(i, int(jn)))
                    if key in seen:
                        continue
                    seen.add(key)
                    d = float((P[i, 2] + P[jn, 2]) / 2)
                    items.append(("strand",
                                  [((P[i, 0], P[i, 1]), (P[jn, 0], P[jn, 1]))], d))
            for x, y, d in nodes:
                items.append(("node", (x, y), d))
            return items
        raise ValueError(self.mode)

    def _advance(self, f):
        """Cumulative camera advance after f frames: the reference plane at depth 1.0
        grows exactly at the scheduled zoom rate; everything else looms accordingly
        (V3, 2026-08-17 — uniform Z scaling read as cardboard cutouts in formation;
        real approach means an instance at distance d scales by d/(d - advance))."""
        adv = 0.0
        for k in range(min(f, len(self.zooms))):
            z = self.zooms[k]
            adv += (z - 1.0) / z
        return adv

    def frame(self, f, floor=0.04):
        """Depth map for window frame f (0-based). Painter's algorithm far->near with
        per-instance LOOMING: d_i(f) = d_i(0) - advance(f); near instances grow fast and
        exit past the camera, far ones crawl — size, brightness and motion all agree."""
        Z = self.Z[min(f, len(self.Z) - 1)]
        adv = self._advance(f)
        aim = self.aims[min(f, len(self.aims) - 1)]
        depth = np.full((H, W), floor, np.float32)
        if self.mode == "surface":
            g = (np.linspace(0, 1, H)[:, None] ** 1.4) * 0.55   # ground: bottom near
            depth = np.maximum(depth, g.astype(np.float32) * np.ones((H, W), np.float32))
        # painter's order: farthest first, so near cores overwrite (true occlusion);
        # depth-less sentinels (surface's "ground" marker) don't join the sort
        items = sorted((it for it in self.items if it[2] is not None),
                       key=lambda it: -(it[2] - adv))
        for kind, geom, d in items:
            d = d - adv                    # LOOM: the camera has advanced
            if d <= 0.16:
                continue                   # passed the camera
            near = depth_value(d)
            d0 = d + adv                   # original authored distance
            grow = d0 / d                  # perspective expansion for THIS instance
            if kind in ("blob", "bigblob"):
                shift = self.parallax * W * f / max(0.35, d)
                px, py = _project((geom[0] * W + shift, geom[1] * H),
                                  (aim[0] * W, aim[1] * H), grow)
                base_r = 24.0 if kind == "bigblob" else 10.0
                r = (base_r * self.size / d ** 0.72)
                _gauss_blob(depth, px, py, r, near)
            elif kind == "node":
                shift = self.parallax * W * f / max(0.35, d)
                px, py = _project((geom[0] * W + shift, geom[1] * H),
                                  (aim[0] * W, aim[1] * H), grow)
                _gauss_blob(depth, px, py, max(1.2, 7.0 * self.size / d ** 0.72),
                            min(1.0, near * 1.2))
            elif kind == "strand":
                r = max(0.8, 2.6 * self.size / d ** 0.72)
                shift = self.parallax * W * f / max(0.35, d)
                for (a, b) in geom:
                    pa = _project((a[0] * W + shift, a[1] * H), (aim[0] * W, aim[1] * H), grow)
                    pb = _project((b[0] * W + shift, b[1] * H), (aim[0] * W, aim[1] * H), grow)
                    steps = int(max(abs(pb[0] - pa[0]), abs(pb[1] - pa[1]), 1) / (r * 0.9) ) + 1
                    for t in np.linspace(0, 1, steps + 1):
                        _gauss_blob(depth, pa[0] + (pb[0] - pa[0]) * t,
                                    pa[1] + (pb[1] - pa[1]) * t, r, near)
                # bright junction beads at strand starts
                pa = _project((geom[0][0][0] * W, geom[0][0][1] * H),
                              (aim[0] * W, aim[1] * H), Z)
                _gauss_blob(depth, pa[0], pa[1], r * 2.1, min(1.0, near * 1.25))
        return np.clip(depth, 0.0, 1.0)

    def frame_image(self, f):
        """PIL RGB version of frame(f) — what dive uploads as the control image."""
        from PIL import Image
        return Image.fromarray((self.frame(f) * 255).astype(np.uint8)).convert("RGB")


_BANDS = [(-16, -12, "subnuclear"), (-12, -8.5, "atomic"), (-8.5, -6, "molecular"),
          (-6, -3.5, "cellular"), (-3.5, -1.5, "mm-creature"), (-1.5, 1.5, "human"),
          (1.5, 4.5, "landscape"), (4.5, 9, "planetary"), (9, 14, "stellar"),
          (14, 22, "galactic"), (22, 27, "cosmic-web")]


def band_of(exp):
    for lo, hi, name in _BANDS:
        if lo <= exp < hi:
            return name
    return "cosmic-web" if exp >= 27 else "subnuclear"


def mode_for_band(band):
    """Default arrangement per REALMS band (journey `resolve.mode` overrides)."""
    return {"cellular": "sea", "mm-creature": "sea", "molecular": "sea", "stellar": "sea",
            "galactic": "sea", "atomic": "lattice", "subnuclear": "sea",
            "human": "surface", "landscape": "surface", "planetary": "surface",
            "cosmic-web": "web"}.get(band, "sea")
