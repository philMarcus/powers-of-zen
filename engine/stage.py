#!/usr/bin/env python3
"""THE MICRO STAGE (2026-10-03, PLAN "THE MICRO STAGE") — v0 renderer, CPU, numpy only.

A STAGE is a built 3-D world (a film set) the dive camera flies through: real structure for a
micro realm (a crystal lattice, a nucleus of nucleons, ...), rendered every frame as PIXELS +
DEPTH at the exact scheduled zoom, so the feedback chain feeds on structure that cannot drift
(the planet-plate lesson: pixels at the scheduled geometry are the one channel the chain obeys;
depth-CN alone lets the prior eat the zoom).

Camera model = the scaffold's looming law made literal: the frame plane sits at depth 1 and the
camera ADVANCES by (z-1)/z per frame along the ray through the aim point, so a point at depth d
scales by d/(d-adv), the aim is the zoom's fixed point, and the aim ray's instances grow in
place — exactly what dive.zoom_transform does to the pixels.

Primitives: shaded sphere impostors (z-buffered, painter-free), capsules (tubes as sphere
chains), additive glow splats (fog / probability clouds). Kits build instance lists in WORLD
space once (seeded); frame(k) renders RGB + depth (near = bright, controlnet polarity).
"""
import math
import numpy as np
from PIL import Image, ImageFilter

W, H = 576, 1024
D_MIN, D_MAX = 0.35, 14.0


def depth_value(d):
    t = np.log(np.clip(d, D_MIN, D_MAX) / D_MIN) / np.log(D_MAX / D_MIN)
    return 1.0 - 0.94 * t


def rot_matrix(rng):
    """A random rotation (uniform-ish) so a lattice is seen along a generic direction."""
    q = rng.normal(size=4); q /= np.linalg.norm(q)
    a, b, c, d = q
    return np.array([[a*a+b*b-c*c-d*d, 2*(b*c-a*d), 2*(b*d+a*c)],
                     [2*(b*c+a*d), a*a-b*b+c*c-d*d, 2*(c*d-a*b)],
                     [2*(b*d-a*c), 2*(c*d+a*b), a*a-b*b-c*c+d*d]])


class Stage:
    """items: list of ('sphere', center(3), radius, rgb(3), emit) | ('glow', center, radius, rgb, k).
    zooms/aims: per-frame schedule slices (same as scaffold.Resolver)."""

    def __init__(self, zooms, aims, w=W, h=H, fog_rgb=(0.02, 0.02, 0.04), fog_dist=6.0,
                 light=(-0.5, -0.6, -0.62), bg=(0.01, 0.01, 0.02)):
        self.zooms, self.aims, self.w, self.h = list(zooms), list(aims), w, h
        self.fog_rgb, self.fog_dist, self.bg = np.array(fog_rgb, np.float32), fog_dist, np.array(bg, np.float32)
        L = np.array(light, np.float32); self.light = L / np.linalg.norm(L)
        self.items = []
        self.jitter = 0.0            # per-frame thermal shiver (world units)
        self.rng = np.random.default_rng(0)

    # ---- camera ---------------------------------------------------------------------
    def _advance(self, f):
        return sum((z - 1.0) / z for z in self.zooms[:f])

    def _camera(self, f):
        ax, ay = self.aims[min(f, len(self.aims) - 1)]
        d = np.array([(ax - 0.5), (ay - 0.5) * self.h / self.w, 1.0], np.float32)
        d /= np.linalg.norm(d)
        return self._advance(f) * d

    # ---- render ---------------------------------------------------------------------
    def frame(self, f):
        w, h = self.w, self.h
        cam = self._camera(f)
        col = np.tile(self.bg, (h, w, 1)).astype(np.float32)
        zb = np.full((h, w), np.inf, np.float32)
        glow = np.zeros((h, w, 3), np.float32)
        jit = self.rng.normal(scale=self.jitter, size=(len(self.items), 3)) if self.jitter else None
        # near-to-far for the z-buffer is irrelevant (true z test); sort far->near so
        # overdraw stays bounded by occlusion
        order = sorted(range(len(self.items)), key=lambda i: -float(self.items[i][1][2]))
        for i in order:
            kind, c, R, rgb, extra = self.items[i]
            q = np.asarray(c, np.float32) - cam
            if jit is not None:
                q = q + jit[i]
            if q[2] <= 0.05:
                continue
            px, py = 0.5 * w + w * q[0] / q[2], 0.5 * h + w * q[1] / q[2]
            rpx = w * R / q[2]
            if kind == 'glow':
                rpx *= 1.0
                x0, x1 = int(max(0, px - 3 * rpx)), int(min(w, px + 3 * rpx + 1))
                y0, y1 = int(max(0, py - 3 * rpx)), int(min(h, py + 3 * rpx + 1))
                if x1 <= x0 or y1 <= y0 or rpx < 0.3:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                g = np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * rpx * rpx)) * extra
                # glow is occluded by nearer opaque surfaces
                vis = (zb[y0:y1, x0:x1] > q[2]).astype(np.float32)
                glow[y0:y1, x0:x1] += (g * vis)[..., None] * np.asarray(rgb, np.float32)
                continue
            if rpx < 0.4:
                continue
            x0, x1 = int(max(0, px - rpx - 1)), int(min(w, px + rpx + 2))
            y0, y1 = int(max(0, py - rpx - 1)), int(min(h, py + rpx + 2))
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            u, v = (xx - px) / rpx, (yy - py) / rpx
            rho2 = u * u + v * v
            inside = rho2 <= 1.0
            if not inside.any():
                continue
            nz = np.sqrt(np.clip(1.0 - rho2, 0, 1))
            depth = q[2] - R * nz                          # surface depth toward the camera
            zi = zb[y0:y1, x0:x1]
            hit = inside & (depth < zi)
            if not hit.any():
                continue
            # view-space normal (camera looks down +z; the visible cap faces -z)
            n = np.stack([u, v, -nz], -1)
            ndl = np.clip(-(n @ self.light), 0, 1)        # light vector points INTO the scene
            spec = ndl ** 24
            shade = 0.42 + 0.58 * ndl
            base = np.asarray(rgb, np.float32)
            px_col = base[None, None, :] * shade[..., None] + 0.55 * spec[..., None] + extra * base
            # anti-aliased rim
            aa = np.clip((1.0 - np.sqrt(rho2)) * rpx, 0, 1)[..., None]
            region = col[y0:y1, x0:x1]
            mix = (hit[..., None] * aa)
            col[y0:y1, x0:x1] = region * (1 - mix) + px_col * mix
            zb[y0:y1, x0:x1] = np.where(hit, depth, zi)
        # depth fog toward the void colour, then glow on top
        zfin = np.where(np.isinf(zb), self.fog_dist * 3, zb)
        fog = np.clip(1.0 - np.exp(-zfin / self.fog_dist), 0, 1)[..., None]
        col = col * (1 - fog) + self.fog_rgb * fog
        col = col + glow
        col = col / (1.0 + 0.55 * col)                    # soft tone map: glow piles up, never clips to white
        col = np.clip(col * 1.35, 0, 1)
        dmap = np.where(np.isinf(zb), 0.03, depth_value(zb)).astype(np.float32)
        return col, dmap

    def frame_images(self, f):
        col, d = self.frame(f)
        rgb = Image.fromarray((col * 255).astype(np.uint8))
        dep = Image.fromarray((np.clip(d, 0, 1) * 255).astype(np.uint8)).convert('RGB')
        return rgb, dep


# ---- kits -------------------------------------------------------------------------------
def _in_view_mask(pts, cam=(0, 0, 0), margin=1.9, zmin=0.25, zmax=D_MAX):
    q = pts - np.asarray(cam, np.float32)
    ok = (q[:, 2] > zmin) & (q[:, 2] < zmax)
    ok &= np.abs(q[:, 0]) < margin * q[:, 2] * 0.5
    ok &= np.abs(q[:, 1]) < margin * q[:, 2] * 0.5 * (H / W)
    return ok


LATTICES = {
    # name: (basis vectors as rows (unit cell), fractional atom sites [(frac, species)], bonds?)
    'cubic':  (np.eye(3), [((0, 0, 0), 0)], True),                                    # halite-like (one species shown)
    'fcc':    (np.eye(3), [((0, 0, 0), 0), ((.5, .5, 0), 0), ((.5, 0, .5), 0), ((0, .5, .5), 0)], False),
    'diamond': (np.eye(3), [((0, 0, 0), 0), ((.5, .5, 0), 0), ((.5, 0, .5), 0), ((0, .5, .5), 0),
                            ((.25, .25, .25), 1), ((.75, .75, .25), 1), ((.75, .25, .75), 1), ((.25, .75, .75), 1)], True),
    'hex':    (np.array([[1, 0, 0], [0.5, math.sqrt(3) / 2, 0], [0, 0, 1.63]]),
               [((0, 0, 0), 0), ((1 / 3, 1 / 3, 0.5), 0)], True),                     # hcp (ice-like rings)
    'rhombo': (np.array([[1, 0, 0], [0.35, 0.94, 0], [0.35, 0.25, 0.9]]), [((0, 0, 0), 0), ((.5, .5, .5), 1)], True),  # calcite-ish
    'sheets': (np.array([[1, 0, 0], [0.5, math.sqrt(3) / 2, 0], [0, 0, 2.4]]),
               [((0, 0, 0), 0), ((1 / 3, 1 / 3, 0), 0)], True),                       # graphite-like honeycomb layers
}


def kit_lattice(stage, variant='cubic', spacing=0.42, radius=0.055, colors=((0.55, 0.75, 1.0), (0.95, 0.45, 0.7)),
                bond_rgb=(0.75, 0.8, 0.9), bond_r=0.014, jitter=0.012, seed=0, extent=16, glow=0.16,
                z_far=7.0, bond_far=3.2):
    """An infinite crystal seen along a random (seeded) direction, far ranks into fog."""
    rng = np.random.default_rng(seed)
    basis, sites, bonds = LATTICES[variant]
    Rm = rot_matrix(rng)
    pts, spc = [], []
    rngs = range(-extent, extent + 1)
    ijk = np.array([(i, j, k) for i in rngs for j in rngs for k in rngs], np.float32)
    for frac, s in sites:
        p = (ijk + np.asarray(frac, np.float32)) @ basis * spacing
        pts.append(p); spc.append(np.full(len(p), s))
    pts = np.concatenate(pts) @ Rm.T
    spc = np.concatenate(spc)
    pts = pts + np.array([0, 0, D_MAX * 0.45], np.float32)       # push the block in front of the camera
    pts = pts + rng.normal(scale=jitter, size=pts.shape)
    ok = _in_view_mask(pts, zmax=z_far)
    pts, spc = pts[ok], spc[ok]
    for p, s in zip(pts, spc):
        stage.items.append(('sphere', p, radius * (1.0 if s == 0 else 0.7), colors[s % len(colors)], glow))
    near = pts[:, 2] < bond_far
    if bonds and near.sum() > 1:
        # bonds = nearest-neighbour pairs under 1.15 x the shortest spacing, as sphere chains
        # (near ranks only — beyond bond_far a bond is sub-pixel)
        from scipy.spatial import cKDTree
        npts = pts[near]
        tree = cKDTree(npts)
        dmin = tree.query(npts, k=2)[0][:, 1].min()
        pairs = tree.query_pairs(dmin * 1.15)
        for a, b in pairs:
            pa, pb = npts[a], npts[b]
            n = max(2, int(np.linalg.norm(pb - pa) / (bond_r * 1.2)))
            for t in np.linspace(0.15, 0.85, n):
                stage.items.append(('sphere', pa + (pb - pa) * t, bond_r, bond_rgb, 0.0))
    stage.jitter = jitter * 0.6
    stage.fog_dist = 5.5
    return stage


def kit_nucleus(stage, n=140, radius=0.09, centre=(0, 0, 2.2), colors=((1.0, 0.55, 0.25), (0.8, 0.85, 1.0)),
                frac_a=0.45, seed=0, glow=0.18, halo=True, spill=0.0):
    """A droplet of close-packed nucleons in two colours (random close packing by relaxation),
    glowing; optional halo of loose spheres far outside (the halo nucleus)."""
    rng = np.random.default_rng(seed)
    Rd = radius * 2.0 * (n / 0.64) ** (1 / 3) / 2.0 * 1.05     # droplet radius for packing fraction ~0.64
    p = rng.normal(size=(n, 3)); p /= np.linalg.norm(p, axis=1)[:, None]
    p *= Rd * rng.random(n)[:, None] ** (1 / 3)
    for _ in range(60):                                        # push apart, pull in
        d = p[:, None, :] - p[None, :, :]
        dist = np.linalg.norm(d, axis=-1) + np.eye(n) * 9
        over = np.clip(2 * radius - dist, 0, None)
        push = (d / dist[..., None] * over[..., None]).sum(1) * 0.5
        p += push
        r = np.linalg.norm(p, axis=1)
        p -= (p / r[:, None]) * np.clip(r - Rd, 0, None)[:, None] * 0.5
    kinds = (rng.random(n) < frac_a).astype(int)
    c0 = np.asarray(centre, np.float32)
    for q, k in zip(p, kinds):
        stage.items.append(('sphere', c0 + q, radius, colors[k], glow))
        stage.items.append(('glow', c0 + q, radius * 1.4, colors[k], glow * 0.12))
    if halo:
        for _ in range(2):
            v = rng.normal(size=3); v /= np.linalg.norm(v)
            stage.items.append(('sphere', c0 + v * Rd * 3.2, radius * 0.9, colors[1], 0.3))
        stage.items.append(('glow', c0, Rd * 3.0, (0.3, 0.35, 0.6), 0.06))
    stage.jitter = radius * 0.06
    return stage


if __name__ == '__main__':
    import sys, time
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/stage_demo'); out.mkdir(parents=True, exist_ok=True)
    zooms = [1.045] * 40
    aims = [(0.62, 0.58)] * 40
    for name, build in (('cubic', lambda s: kit_lattice(s, 'cubic', seed=3)),
                        ('hex', lambda s: kit_lattice(s, 'hex', spacing=0.5, colors=((0.6, 0.9, 1.0), (1, 1, 1)), seed=5)),
                        ('diamond', lambda s: kit_lattice(s, 'diamond', spacing=0.6, seed=7, colors=((0.9, 0.95, 1.0), (0.9, 0.95, 1.0)))),
                        ('nucleus', lambda s: kit_nucleus(s, seed=11))):
        t0 = time.time()
        st = build(Stage(zooms, aims))
        tb = time.time() - t0
        for f in (0, 20, 39):
            rgb, dep = st.frame_images(f)
            rgb.save(out / f'{name}_{f:02d}.png'); dep.save(out / f'{name}_{f:02d}_depth.png')
        print(f'{name}: {len(st.items)} items, build {tb:.1f}s, frame {(time.time() - t0 - tb) / 3:.1f}s')


# ---- a stage for ONE dive card (engine integration, dive.py --stage) ---------------------------
KITS = {'lattice': kit_lattice, 'nucleus': kit_nucleus}


def aim_dir(ax, ay, w, h):
    d = np.array([(ax - 0.5), (ay - 0.5) * h / w, 1.0], np.float32)
    return d / np.linalg.norm(d)


def build_card_stage(kit, params, zooms, anchor, w, h, seed=0, fill=0.55):
    """Build the stage for one card: the kit's world, then the PLUNGE TARGET placed on the aim
    ray at the depth that makes it fill the frame at the card's last frame (the containment
    contract made physical): d_T = total advance + R / fill. For a lattice the nearest atom is
    moved onto that point by translating the whole crystal (periodicity kept); for a nucleus
    the droplet's centre is put there."""
    st = Stage(zooms, [anchor] * max(1, len(zooms)), w, h)
    st.anchor = anchor
    p = dict(params or {})
    A = sum((z - 1.0) / z for z in zooms)
    d = aim_dir(anchor[0], anchor[1], w, h)
    if kit == 'nucleus':
        n, radius = int(p.get('n', 140)), float(p.get('radius', 0.09))
        Rd = radius * 2.0 * (n / 0.64) ** (1 / 3) / 2.0 * 1.05
        d_T = A + Rd / fill
        p['centre'] = tuple(d * d_T)
        kit_nucleus(st, seed=seed, **p)
        st.target = tuple(d * d_T)
    else:
        kit_lattice(st, seed=seed, **p)
        R = float(p.get('radius', 0.055))
        d_T = A + R / fill
        P_T = d * d_T
        atoms = [(k, it) for k, it in enumerate(st.items) if it[0] == 'sphere' and abs(it[2] - R) < 1e-6
                 or (it[0] == 'sphere' and abs(it[2] - R * 0.7) < 1e-6)]
        if atoms:
            k0, best = min(atoms, key=lambda kt: float(np.linalg.norm(np.asarray(kt[1][1]) - P_T)))
            shift = P_T - np.asarray(best[1], np.float32)
            st.items = [(it[0], np.asarray(it[1], np.float32) + shift, it[2], it[3], it[4]) for it in st.items]
        st.target = tuple(P_T)
    st.advance_total, st.d_target = A, d_T
    return st


# ---- palette-derived kit colours + the quark kit (2026-10-03 evening) ---------------------------
def palette_colours(palette):
    """(species colours [2+], dark colour) from a card's authored palette via engine/palette.py:
    the phrases' colours, darkest one as the void/fog, the rest (brightest first) as species."""
    try:
        import palette as _p
    except ImportError:  # pragma: no cover
        return [(0.8, 0.85, 1.0), (0.95, 0.5, 0.6)], (0.02, 0.02, 0.04)
    cols = [_p.phrase_rgb(ph) for ph in re.split(r",|\bon\b|\bover\b|\bunder\b|\bthrough\b", palette or '')]
    cols = [np.array(c, np.float32) / 255.0 for c in cols if c]
    if not cols:
        return [(0.8, 0.85, 1.0), (0.95, 0.5, 0.6)], (0.02, 0.02, 0.04)
    lum = [float(c @ np.array([0.3, 0.59, 0.11])) for c in cols]
    order = np.argsort(lum)
    dark = cols[order[0]] * 0.35 if len(cols) > 1 else np.array([0.02, 0.02, 0.04])
    species = [tuple(cols[k]) for k in order[::-1] if lum[k] > 0.12] or [tuple(cols[order[-1]])]
    if len(species) == 1:
        species.append(tuple(np.clip(np.array(species[0]) * 0.6 + 0.2, 0, 1)))
    return species[:3], tuple(np.clip(dark, 0, 0.12))


import re  # noqa: E402  (used above; stage.py had no re import before)


def kit_quark(stage, centre=(0, 0, 3.0), size=0.9, colors=((1.0, 0.75, 0.3), (1.0, 0.75, 0.3)), tube_rgb=(1.0, 0.6, 0.2),
              seed=0, glow=0.4):
    """Three glowing cores at the corners of a triangle, taut flux tubes between them (sphere
    chains that thin toward the middle), a faint spark bath around."""
    rng = np.random.default_rng(seed)
    c0 = np.asarray(centre, np.float32)
    Rm = rot_matrix(rng)
    pts = np.array([[1, 0, 0], [-0.5, math.sqrt(3) / 2, 0], [-0.5, -math.sqrt(3) / 2, 0]], np.float32) * size * 0.5
    pts = pts @ Rm.T + c0
    r_core = size * 0.11
    for k, p in enumerate(pts):
        stage.items.append(('sphere', p, r_core, colors[k % len(colors)], glow))
        stage.items.append(('glow', p, r_core * 2.2, colors[k % len(colors)], glow * 0.5))
    for a in range(3):
        pa, pb = pts[a], pts[(a + 1) % 3]
        n = 26
        for t in np.linspace(0.08, 0.92, n):
            w = 0.55 + 0.45 * abs(2 * t - 1)              # tube thins at the middle (a taut string)
            stage.items.append(('sphere', pa + (pb - pa) * t, r_core * 0.28 * w, tube_rgb, glow * 0.6))
    for _ in range(60):                                   # loose sparks in the void around
        v = rng.normal(size=3); v /= np.linalg.norm(v)
        p = c0 + v * size * (0.9 + 1.6 * rng.random())
        stage.items.append(('glow', p, r_core * 0.5, tube_rgb, 0.08))
    stage.jitter = r_core * 0.05
    return stage


KITS['quark'] = kit_quark


def build_card_stage_v2(spec_stage, palette, zooms, anchor, w, h, seed=0, fill=0.55):
    """Journey-field entry point: `stage` = {"kit": lattice|nucleus|quark, ...kit params}.
    Colours default from the card palette (species + void); explicit params win."""
    p = dict(spec_stage or {})
    kit = p.pop('kit', 'lattice')
    species, dark = palette_colours(palette)
    p.setdefault('colors', species[:2])
    st_params = p
    if kit == 'quark':
        st = Stage(zooms, [anchor] * max(1, len(zooms)), w, h, bg=dark, fog_rgb=dark)
        st.anchor = anchor
        A = sum((z - 1.0) / z for z in zooms)
        size = float(p.get('size', 0.9))
        d_T = A + size * 0.5 / fill
        d = aim_dir(anchor[0], anchor[1], w, h)
        p['centre'] = tuple(d * d_T)
        p.setdefault('tube_rgb', species[-1] if len(species) > 1 else species[0])
        kit_quark(st, seed=seed, **p)
        st.target, st.advance_total, st.d_target = tuple(d * d_T), A, d_T
        return st
    st = build_card_stage(kit, st_params, zooms, anchor, w, h, seed=seed, fill=fill)
    st.bg = np.array(dark, np.float32); st.fog_rgb = np.array(dark, np.float32)
    return st
