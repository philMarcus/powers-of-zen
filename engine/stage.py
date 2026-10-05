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


# ---- LOOKS (2026-10-05, Phil: "if all the atoms look samey ... we'll have samey video"; "from
# time to time gems in the fuzziness"): one drawn look per journey changes how every sphere in
# every kit is shaded. The structure (kit) and the look are independent axes of variety.
LOOKS = ('gem', 'fuzzy', 'plasma', 'glass', 'wire', 'ink')
LOOK_WEIGHTS = {'gem': 25, 'fuzzy': 25, 'plasma': 20, 'glass': 14, 'wire': 8, 'ink': 8}
LOOK_GLOW = {'gem': 0.6, 'fuzzy': 1.0, 'plasma': 1.8, 'glass': 0.35, 'wire': 0.4, 'ink': 0.25}


def _fib_hemisphere(n=22):
    """Facet directions for the gem look: n near-even unit vectors on the camera-facing
    hemisphere (view space, z < 0)."""
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - k / n)                     # polar angle from -z over one hemisphere
    th = np.pi * (1 + 5 ** 0.5) * k
    return np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), -np.cos(phi)], -1).astype(np.float32)


_FACETS = _fib_hemisphere()


def draw_look(key):
    """Deterministic weighted draw of a look from a journey key."""
    import zlib
    r = zlib.crc32(str(key).encode()) % sum(LOOK_WEIGHTS.values())
    acc = 0
    for name, wgt in LOOK_WEIGHTS.items():
        acc += wgt
        if r < acc:
            return name
    return 'fuzzy'


def shade_sphere(look, n, nz, rho2, base, light, extra, bg):
    """Per-pixel colour of a sphere cap under a LOOK. n: view-space normals (...,3), nz: the
    cap height (1 at centre, 0 at the rim), base: rgb (3,), light: unit vector into the scene."""
    b = base[None, None, :]
    if look == 'gem':
        # facets: snap the normal to the nearest facet direction, hard speculars, a lit rim
        idx = np.argmax(n @ _FACETS.T, axis=-1)
        nq = _FACETS[idx]
        ndl = np.clip(-(nq @ light), 0, 1)
        spec = ndl ** 48
        rim = (1.0 - nz) ** 3
        return (b * (0.35 + 0.65 * ndl)[..., None] + 1.1 * spec[..., None]
                + 0.35 * rim[..., None] * (0.5 * b + 0.5) + extra * b)
    ndl = np.clip(-(n @ light), 0, 1)
    if look == 'plasma':
        core = np.clip(1.0 - rho2, 0, 1) ** 1.5
        return b * (0.5 + 0.5 * ndl)[..., None] + core[..., None] * (0.55 + 0.45 * b) + extra * b
    if look == 'glass':
        fres = (1.0 - nz) ** 2
        spec = ndl ** 40
        return (0.30 * b + fres[..., None] * (0.55 * b + 0.55) + 0.9 * spec[..., None]
                + 0.25 * (1 - fres)[..., None] * np.asarray(bg, np.float32)[None, None, :] + extra * b)
    if look == 'wire':
        ring = np.clip((np.sqrt(rho2) - 0.70) / 0.30, 0, 1)
        return 0.10 * b + ring[..., None] * (0.7 * b + 0.5) + 0.5 * extra * b
    if look == 'ink':
        rim = (1.0 - nz) ** 2
        spec = ndl ** 30
        return 0.22 * b * (0.6 + 0.4 * ndl)[..., None] + 0.45 * rim[..., None] * (0.4 * b + 0.6) + 0.5 * spec[..., None]
    # fuzzy (the original soft shading)
    spec = ndl ** 24
    shade = 0.42 + 0.58 * ndl
    return b * shade[..., None] + 0.55 * spec[..., None] + extra * b


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
        # per-frame deterministic jitter (not a running RNG): the warm-up and lap copies of a
        # staged card 0 must render the SAME frame j identically whatever was drawn before
        _jr = np.random.default_rng(((getattr(self, 'seed', 0) + 1) * 1000003 + f) & 0xFFFFFFFF)
        jit = _jr.normal(scale=self.jitter, size=(len(self.items), 3)) if self.jitter else None
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
            if kind == 'capsule':
                # a TUBE segment from c to `extra_b` (stored in the colour slot's neighbour):
                # items are ('capsule', a, b, R, rgb, extra) — see kit_tubes v5
                qb = np.asarray(R, np.float32) - cam       # R holds b for capsules
                Rr = float(rgb)                            # rgb slot holds the radius
                rgb, extra = extra[0], extra[1]
                if qb[2] <= 0.05:
                    continue
                pbx, pby = 0.5 * w + w * qb[0] / qb[2], 0.5 * h + w * qb[1] / qb[2]
                rpa, rpb = w * Rr / q[2], w * Rr / qb[2]
                rmax = max(rpa, rpb)
                if rmax < 0.4:
                    continue
                x0, x1 = int(max(0, min(px, pbx) - rmax - 1)), int(min(w, max(px, pbx) + rmax + 2))
                y0, y1 = int(max(0, min(py, pby) - rmax - 1)), int(min(h, max(py, pby) + rmax + 2))
                if x1 <= x0 or y1 <= y0:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                dx, dy = pbx - px, pby - py
                L2 = dx * dx + dy * dy
                t = np.clip(((xx - px) * dx + (yy - py) * dy) / max(L2, 1e-6), 0, 1)
                cxp, cyp = px + t * dx, py + t * dy        # nearest point on the segment
                rp = rpa + (rpb - rpa) * t                 # radius in px along the segment
                u, v = (xx - cxp) / rp, (yy - cyp) / rp
                rho2 = u * u + v * v
                inside = rho2 <= 1.0
                if not inside.any():
                    continue
                nz = np.sqrt(np.clip(1.0 - rho2, 0, 1))
                zc = q[2] + (qb[2] - q[2]) * t
                depth = zc - Rr * nz
                rpx = rp
            else:
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
            base = np.asarray(rgb, np.float32)
            px_col = shade_sphere(getattr(self, 'look', 'fuzzy'), n, nz, rho2, base, self.light,
                                  extra, self.bg)
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
        glow = glow / (1.0 + 0.8 * glow)            # soft-clip accumulated glow (thousands of
        col = col + glow * LOOK_GLOW.get(getattr(self, 'look', 'fuzzy'), 1.0)   # halos blew a lattice white
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
                z_far=7.0, bond_far=3.2, fuzzy=False, bonds=None):
    """fuzzy=True (2026-10-04, after the hero fog atom rang/burst twice): the ATOMIC-band picture
    without a hero — large soft glowing spheres (electron clouds) at their lattice sites, a faint
    bright core in each, no bonds, more thermal shiver; the plunge enters one cloud."""
    if fuzzy:
        radius = max(radius, spacing * 0.30)
        glow = 0.22
        jitter = max(jitter, spacing * 0.05)
        z_far = min(z_far, 5.0)
    """An infinite crystal seen along a random (seeded) direction, far ranks into fog."""
    rng = np.random.default_rng(seed)
    if variant == 'random':
        # AMORPHOUS NETWORK (glass, melt, silica random network): a jittered cubic grid with
        # a third of its sites removed, bonded to nearest neighbours — no long-range order
        basis, sites, _b = LATTICES['cubic']
        jitter = max(jitter, spacing * 0.22)
        _bonds_default = True
    else:
        basis, sites, _b = LATTICES[variant]
        _bonds_default = _b
    bonds = _bonds_default if bonds is None else bonds
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
    if variant == 'random':
        keep = rng.random(len(pts)) > 0.33
        pts, spc = pts[keep], spc[keep]
    ok = _in_view_mask(pts, zmax=z_far)
    pts, spc = pts[ok], spc[ok]
    for p, s in zip(pts, spc):
        stage.items.append(('sphere', p, radius * (1.0 if s == 0 else 0.7), colors[s % len(colors)], glow))
        if fuzzy:
            stage.items.append(('glow', p, radius * 1.5, colors[s % len(colors)], 0.06))
            stage.items.append(('sphere', p, radius * 0.10, (1.0, 1.0, 1.0), 0.8))
    near = pts[:, 2] < bond_far
    if bonds and not fuzzy and near.sum() > 1:
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


def _pack(rng, n, radius, iters=60):
    """Random close packing of n spheres in a droplet: (positions, droplet radius)."""
    Rd = radius * 2.0 * (n / 0.64) ** (1 / 3) / 2.0 * 1.05
    p = rng.normal(size=(n, 3)); p /= np.linalg.norm(p, axis=1)[:, None]
    p *= Rd * rng.random(n)[:, None] ** (1 / 3)
    for _ in range(iters):
        d = p[:, None, :] - p[None, :, :]
        dist = np.linalg.norm(d, axis=-1) + np.eye(n) * 9
        over = np.clip(2 * radius - dist, 0, None)
        p += (d / dist[..., None] * over[..., None]).sum(1) * 0.5
        r = np.linalg.norm(p, axis=1)
        p -= (p / r[:, None]) * np.clip(r - Rd, 0, None)[:, None] * 0.5
    return p, Rd


def kit_nucleus(stage, n=100, radius=0.065, centre=(0, 0, 2.2), colors=((1.0, 0.55, 0.25), (0.8, 0.85, 1.0)),
                frac_a=0.45, seed=0, glow=0.22, halo=True, spill=0.0, field=True, n_field=44,
                spread=(3.0, 3.4, 9.0)):
    """Nuclei as a FIELD (Phil 2026-10-04: "there needs to be more of them" — the house sea
    doctrine: many instances at all depths, the plunge picks one): the TARGET droplet of
    close-packed two-colour nucleons at `centre`, and n_field smaller droplets scattered through
    the frustum (fewer nucleons, same nucleon size), far ones fading into the void's fog."""
    rng = np.random.default_rng(seed)
    c0 = np.asarray(centre, np.float32)
    p, Rd = _pack(rng, n, radius)
    kinds = (rng.random(n) < frac_a).astype(int)
    for q, k in zip(p, kinds):
        stage.items.append(('sphere', c0 + q, radius, colors[k], glow))
        stage.items.append(('glow', c0 + q, radius * 1.4, colors[k], glow * 0.12))
    if halo:
        for _ in range(2):
            v = rng.normal(size=3); v /= np.linalg.norm(v)
            stage.items.append(('sphere', c0 + v * Rd * 3.2, radius * 0.9, colors[1], 0.3))
    if field:
        for i in range(n_field):
            z = 0.7 + spread[2] * rng.random() ** 0.8
            c = np.array([(rng.random() - 0.5) * spread[0] * max(0.6, z / 3.0),
                          (rng.random() - 0.5) * spread[1] * max(0.6, z / 3.0), z], np.float32)
            if np.linalg.norm(c - c0) < Rd * 2.5:
                continue
            m = int(rng.integers(24, 70))
            if z > 5.5:                 # far: one soft glowing blob stands for the droplet
                stage.items.append(('glow', c, radius * (m / 0.64) ** (1 / 3) * 0.9, colors[int(rng.random() < 0.5)], glow * 0.5))
                stage.items.append(('sphere', c, radius * (m / 0.64) ** (1 / 3) * 0.55, colors[1], glow * 0.3))
                continue
            pq, _ = _pack(rng, m, radius, iters=25)
            kq = (rng.random(m) < frac_a).astype(int)
            for q, k in zip(pq, kq):
                stage.items.append(('sphere', c + q, radius, colors[k], glow * 0.8))
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
    st.seed = seed
    p = dict(params or {})
    A = sum((z - 1.0) / z for z in zooms)
    d = aim_dir(anchor[0], anchor[1], w, h)
    if kit == 'nucleus':
        n, radius = int(p.get('n', 100)), float(p.get('radius', 0.065))
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
    def _vivid(c):
        c = np.array(c, np.float32)
        mx = c.max()
        if mx < 0.85:                       # lift value so the stage reads bright, keep hue
            c = c / max(mx, 1e-3) * 0.85
        m = c.mean()
        c = m + (c - m) * 1.25              # a little more saturation
        return tuple(np.clip(c, 0, 1))
    species = [_vivid(cols[k]) for k in order[::-1] if lum[k] > 0.12] or [_vivid(cols[order[-1]])]
    if len(species) == 1:
        species.append(tuple(np.clip(np.array(species[0]) * 0.6 + 0.2, 0, 1)))
    return species[:3], tuple(np.clip(dark, 0, 0.12))


import re  # noqa: E402  (used above; stage.py had no re import before)


def kit_quark(stage, centre=(0, 0, 3.0), size=0.9, colors=((1.0, 0.75, 0.3), (1.0, 0.75, 0.3)), tube_rgb=(1.0, 0.6, 0.2),
              seed=0, glow=0.4, field=True, n_field=14, spread=(3.0, 3.4, 9.0)):
    """Three glowing cores at the corners of a triangle, taut flux tubes between them, as a
    FIELD of such trios (the target trio at `centre`), loose sparks in the void around."""
    rng = np.random.default_rng(seed)

    def trio(c0, sz, strength):
        Rm = rot_matrix(rng)
        pts = np.array([[1, 0, 0], [-0.5, math.sqrt(3) / 2, 0], [-0.5, -math.sqrt(3) / 2, 0]], np.float32) * sz * 0.5
        pts = pts @ Rm.T + c0
        r_core = sz * 0.11
        for k, p in enumerate(pts):
            stage.items.append(('sphere', p, r_core, colors[k % len(colors)], glow * strength))
            stage.items.append(('glow', p, r_core * 2.2, colors[k % len(colors)], glow * 0.5 * strength))
        for a in range(3):
            pa, pb = pts[a], pts[(a + 1) % 3]
            for t in np.linspace(0.08, 0.92, 26):
                w = 0.55 + 0.45 * abs(2 * t - 1)
                stage.items.append(('sphere', pa + (pb - pa) * t, r_core * 0.28 * w, tube_rgb, glow * 0.6 * strength))
        return r_core

    c0 = np.asarray(centre, np.float32)
    r_core = trio(c0, size, 1.0)
    if field:
        for i in range(n_field):
            z = 0.8 + spread[2] * rng.random() ** 0.8
            c = np.array([(rng.random() - 0.5) * spread[0] * max(0.6, z / 3.0),
                          (rng.random() - 0.5) * spread[1] * max(0.6, z / 3.0), z], np.float32)
            if np.linalg.norm(c - c0) < size:
                continue
            trio(c, size * (0.7 + 0.6 * rng.random()), 0.75)
    for _ in range(80):
        v = rng.normal(size=3); v /= np.linalg.norm(v)
        p = c0 + v * size * (0.9 + 3.0 * rng.random())
        stage.items.append(('glow', p, r_core * 0.5, tube_rgb, 0.08))
    stage.jitter = r_core * 0.05
    return stage


KITS['quark'] = kit_quark


def _apply_look(st, look, species, dark):
    """Set the stage's look and its look-dependent background: ink = dark bodies on a LIGHT
    fog (the palette's lightest colour lifted), plasma = a deeper void."""
    st.look = look
    if look == 'ink':
        light = np.clip(np.array(species[0], np.float32) * 0.45 + 0.55, 0, 1)
        st.bg = light * 0.92
        st.fog_rgb = light
    elif look == 'plasma':
        st.bg = np.array(dark, np.float32) * 0.5
        st.fog_rgb = np.array(dark, np.float32) * 0.6
    return st


def build_card_stage_v2(spec_stage, palette, zooms, anchor, w, h, seed=0, fill=0.55, look=None):
    """Journey-field entry point: `stage` = {"kit": lattice|nucleus|quark|fog|tubes|tissue|fluid|
    tracks|pasta, "look": gem|fuzzy|plasma|glass|wire|ink, ...kit params}. Colours default from
    the card palette (species + void); explicit params win; the look defaults to the caller's
    (the journey's drawn look)."""
    p = dict(spec_stage or {})
    kit = p.pop('kit', 'lattice')
    look = p.pop('look', None) or look or 'fuzzy'
    den_arr, den_trav = KIT_DEN.get(kit, (None, None))
    species, dark = palette_colours(palette)
    if look == 'ink':                       # dark bodies: deepen the species
        species = [tuple(np.clip(np.array(c) * 0.55, 0, 1)) for c in species]
    elif look in ('plasma', 'gem'):         # emissive / faceted: brighter species
        species = [tuple(np.clip(np.array(c) * 1.1 + 0.05, 0, 1)) for c in species]
    p.setdefault('colors', species[:2])
    st_params = p
    if kit in ('fluid', 'tracks', 'pasta'):
        st = Stage(zooms, [anchor] * max(1, len(zooms)), w, h, bg=dark, fog_rgb=dark)
        st.anchor = anchor
        st.seed = seed
        A = sum((z - 1.0) / z for z in zooms)
        size = float(p.get('size', 1.0))
        d = aim_dir(anchor[0], anchor[1], w, h)
        d_T = A + size * 0.5 / fill
        p['centre'] = tuple(d * d_T)
        KITS[kit](st, seed=seed, **p)
        st.target, st.advance_total, st.d_target = tuple(d * d_T), A, d_T
        st.den_arrival, st.den_travel = den_arr, den_trav
        return _apply_look(st, look, species, dark)
    if kit == 'quark':
        st = Stage(zooms, [anchor] * max(1, len(zooms)), w, h, bg=dark, fog_rgb=dark)
        st.anchor = anchor
        st.seed = seed
        A = sum((z - 1.0) / z for z in zooms)
        size = float(p.get('size', 0.9))
        d_T = A + size * 0.5 / fill
        d = aim_dir(anchor[0], anchor[1], w, h)
        p['centre'] = tuple(d * d_T)
        p.setdefault('tube_rgb', species[-1] if len(species) > 1 else species[0])
        kit_quark(st, seed=seed, **p)
        st.target, st.advance_total, st.d_target = tuple(d * d_T), A, d_T
        st.den_arrival, st.den_travel = den_arr, den_trav
        return _apply_look(st, look, species, dark)
    if kit in ('fog', 'tubes', 'tissue'):
        st = Stage(zooms, [anchor] * max(1, len(zooms)), w, h, bg=dark, fog_rgb=dark)
        st.anchor = anchor
        st.seed = seed
        A = sum((z - 1.0) / z for z in zooms)
        d = aim_dir(anchor[0], anchor[1], w, h)
        if kit == 'fog':
            size = float(p.get('size', 1.0))
            d_T = A + size * 0.5 / fill          # the outer shell fills the frame at the bar line
            p['centre'] = tuple(d * d_T)
            kit_fog_atom(st, seed=seed, **p)
        elif kit == 'tissue':
            size = float(p.get('size', 1.0))
            cell = float(p.get('cell', 0.22))
            d_T = A + cell * size * 0.5 / fill        # ONE cell fills the frame at the bar line
            p['centre'] = tuple(d * d_T)
            kit_tissue(st, seed=seed, **p)
        else:
            size = float(p.get('size', 0.9))
            d_T = A + size * 0.5 / fill
            p['target_depth'] = tuple(d * d_T)
            kit_tubes(st, seed=seed, **p)
        st.target, st.advance_total, st.d_target = tuple(d * d_T), A, d_T
        st.den_arrival, st.den_travel = den_arr, den_trav
        return _apply_look(st, look, species, dark)
    st = build_card_stage(kit, st_params, zooms, anchor, w, h, seed=seed, fill=fill)
    st.seed = seed
    st.bg = np.array(dark, np.float32); st.fog_rgb = np.array(dark, np.float32)
    st.den_arrival, st.den_travel = den_arr, den_trav
    return _apply_look(st, look, species, dark)


# ---- fog atom + molecular tube kits (2026-10-03 evening) ---------------------------------------
def kit_fog_atom(stage, centre=(0, 0, 3.0), size=1.0, colors=((0.6, 0.8, 1.0), (1.0, 0.95, 0.85)),
                 shells=3, seed=0, glow=0.5, neighbours=12, lobes=1, field=True):
    """ONE atom as fog about a point — v2 (2026-10-03 evening, after the anvil card rendered as a
    SUNBURST/EYE: a smooth centred glow is exactly the prior's bait). Now: a bright core point,
    the probability shells as DENSE GRAINY RINGS of small puffs (visible orbitals with gaps and
    a per-shell hue drift, not one smooth blob), optional two lobes, and — because the cards say
    "a field of luminous atom cores ... each wrapped in nested shells" — the neighbouring atoms
    of the lattice as the same picture at distance (field=True), so the frame is a field with
    structure, never a single centred glow."""
    rng = np.random.default_rng(seed)
    c0 = np.asarray(centre, np.float32)
    core_rgb = np.array(colors[1 % len(colors)], np.float32)
    fog_rgb = np.array(colors[0], np.float32)

    def one_atom(c, scale, strength, grain=True):
        stage.items.append(('sphere', c, size * 0.035 * scale, tuple(core_rgb), 1.4 * strength))
        stage.items.append(('glow', c, size * 0.10 * scale, tuple(core_rgb), glow * 1.2 * strength))
        for k in range(1, shells + 1):
            r = size * 0.5 * scale * (k / shells) ** 1.25
            hue_mix = fog_rgb * (1 - 0.25 * (k - 1)) + core_rgb * 0.25 * (k - 1)
            col = tuple(np.clip(hue_mix, 0, 1))
            stage.items.append(('glow', c, r, col, glow * 0.10 * strength / k))
            if grain:
                n = int(26 * k * scale ** 0.5) + 8
                # a shell with GAPS: puffs cluster in 2-4 bands (the orbital lobes)
                bands = rng.integers(2, 5)
                for _ in range(n):
                    v = rng.normal(size=3); v /= np.linalg.norm(v)
                    if (int((math.atan2(v[1], v[0]) + math.pi) / (2 * math.pi) * bands * 2) % 2) == 1 and rng.random() < 0.7:
                        continue
                    p = c + v * r * (0.9 + 0.2 * rng.random())
                    stage.items.append(('glow', p, r * 0.16, col, glow * 0.22 * strength / k ** 0.7))
        if lobes >= 2:
            ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
            for sgn in (-1, 1):
                stage.items.append(('glow', c + sgn * ax * size * 0.3 * scale, size * 0.22 * scale, tuple(fog_rgb), glow * 0.4 * strength))

    one_atom(c0, 1.0, 1.0)
    if field:
        # neighbours on a jittered lattice around the hero atom (same spacing in every direction)
        a = size * 1.9
        for i in range(-2, 3):
            for j in range(-3, 4):
                for k in range(-1, 4):
                    if i == 0 and j == 0 and k == 0:
                        continue
                    p = c0 + np.array([i * a, j * a, k * a], np.float32) + rng.normal(scale=0.08 * a, size=3)
                    if p[2] < 0.4:
                        continue
                    one_atom(p, 1.0, 0.55, grain=(abs(i) + abs(j) + abs(k) <= 2))
    else:
        for _ in range(neighbours):
            v = rng.normal(size=3); v /= np.linalg.norm(v)
            one_atom(c0 + v * size * (1.6 + 2.5 * rng.random()), 1.0, 0.4, grain=False)
    stage.jitter = size * 0.004
    return stage


_PDB_CACHE = {}


def pdb_trace(pdb_id, chain=None):
    """CA trace (N x 3, unit-normalised) of a PDB entry, fetched once and cached on disk under
    output/realm_refs/pdb/. Falls back to a synthetic helix bundle when offline."""
    from pathlib import Path as _P
    d = _P('/mnt/c/Users/Phil/zoomer/output/realm_refs/pdb'); d.mkdir(parents=True, exist_ok=True)
    f = d / f'{pdb_id.upper()}.pdb'
    if pdb_id in _PDB_CACHE:
        return _PDB_CACHE[pdb_id]
    txt = None
    if f.exists():
        txt = f.read_text()
    else:
        try:
            import urllib.request
            txt = urllib.request.urlopen(f'https://files.rcsb.org/download/{pdb_id.upper()}.pdb', timeout=20).read().decode()
            f.write_text(txt)
        except Exception:
            txt = None
    chains = {}
    if txt:
        for l in txt.splitlines():
            if l.startswith('ATOM') and l[12:16].strip() == 'CA':
                chains.setdefault(l[21], []).append((float(l[30:38]), float(l[38:46]), float(l[46:54])))
    if not chains:                                   # offline fallback: three coiled helices
        t = np.linspace(0, 12 * np.pi, 400)
        chains = {k: list(zip(np.cos(t + k) * 6 + k * 9, np.sin(t + k) * 6, t * 1.5)) for k in range(3)}
    keep = [chain] if chain and chain in chains else list(chains.keys())
    pts = [np.array(chains[c], np.float32) for c in keep]
    allp = np.concatenate(pts)
    ctr, scale = allp.mean(0), np.abs(allp - allp.mean(0)).max()
    out = [(p - ctr) / scale for p in pts]
    _PDB_CACHE[pdb_id] = out
    return out


_PDB_LIBRARY = {   # molecule -> (pdb id, chains hint); the variety source for the molecular band
    'hemoglobin': '4HHB', 'myoglobin': '1MBN', 'insulin': '4INS', 'lysozyme': '1LYZ', 'gfp': '1EMA',
    'dna': '1BNA', 'nucleosome': '1AOI', 'tubulin': '1TUB', 'actin': '1J6Z', 'collagen': '1CGD',
    'keratin': '3TNU', 'atp': '1BMF', 'antibody': '1IGT', 'rhodopsin': '1F88', 'ferritin': '1FHA',
    'aquaporin': '1J4N', 'spectrin': '1U5P', 'crystallin': '2KLJ', 'luciferase': '1LCI',
    'ribosome_small': '1FJG', 'photosystem': '1JB0', 'porin': '2OMF', 'chaperone': '1AON',
    'kinesin': '3KIN', 'myosin': '1B7T', 'transferrin': '1A8E', 'albumin': '1AO6', 'pepsin': '4PEP',
    'rubisco': '1RCX', 'carboxysome': '1RCX', 'phycobilisome': '1KN1', 'chlorophyll': '1JB0',
    'cellulose': '1CGD', 'spool': '1AOI', 'histone': '1AOI', 'chromosome': '1AOI',
}


def kit_tubes(stage, pdb='4HHB', n_copies=14, size=0.9, radius=None, colors=((0.95, 0.5, 0.6), (0.6, 0.85, 1.0)),
              seed=0, glow=0.12, spread=(2.2, 2.4, 7.0), target_depth=None, membrane=False, stride=1,
              arrangement='sea', density=1.0):
    """A sea of real molecules — v4 (2026-10-04 evening, Phil: "molecules are a big part of
    variety"). TUBES, not beads: the CA trace is resampled at 0.45 r so the spheres fuse into a
    smooth tube (radius size/40), one palette colour per chain cycling through the species, a
    bright accent on every 7th residue (side chains / prosthetic groups). ARRANGEMENTS from the
    card's words: 'sea' (free scatter at all depths), 'bundle' (copies aligned along one axis,
    for collagen/cellulose/keratin/fibre cards), 'sheet' (copies seated in a tilted plane with a
    lipid-head membrane behind, for membrane-protein cards), 'chain' (copies strung along a
    curve, for polysome/necklace cards). Copy count scales with the molecule's footprint and
    `density`; non-target copies stay beyond z 1.4 (no frame-filling lumps); a haze of far small
    copies gives depth. The target copy sits on the aim ray (target_depth)."""
    rng = np.random.default_rng(seed)
    chains = pdb_trace(pdb)
    radius = radius if radius is not None else size / 40.0
    n_ca = sum(len(c) for c in chains)
    foot = (size * 0.5) ** 2 * min(1.0, n_ca / 600.0)
    n_auto = int(np.clip(1.6 * density / max(foot, 1e-3), n_copies, 320))
    n_total = max(n_copies, n_auto)
    axis = rng.normal(size=3); axis /= np.linalg.norm(axis)
    if arrangement == 'bundle':
        axis = np.array([0.35, 0.9, 0.25], np.float32); axis /= np.linalg.norm(axis)
    Rm_bundle = rot_matrix(rng)
    accent = tuple(np.clip(np.array(colors[-1]) * 0.5 + 0.5, 0, 1))
    c_tgt = np.asarray(target_depth, np.float32) if target_depth is not None else np.array([0, 0, 3.0], np.float32)
    ex = np.array([1.0, 0, 0], np.float32); ey = np.array([0, math.cos(0.45), math.sin(0.45)], np.float32)
    ez = np.cross(ex, ey)
    for k in range(n_total + 10):
        if k == 0:
            c, sz = c_tgt, size
        else:
            if arrangement == 'sheet':
                u, v = (rng.random() - 0.5) * 6.0, (rng.random() - 0.5) * 7.0
                c = c_tgt + ex * u * size + ey * v * size + ez * rng.normal(scale=0.08 * size)
                if c[2] < 1.4:
                    continue
            elif arrangement == 'chain':
                t = (k / max(1, n_total)) * 2 * math.pi * 1.5
                c = c_tgt + np.array([math.cos(t) * 1.4 * size, (t - 2.5) * 0.55 * size, math.sin(t) * 1.2 * size + 1.0], np.float32)
                if c[2] < 1.4:
                    continue
            else:
                z = 1.4 + spread[2] * rng.random() ** 0.7
                c = np.array([(rng.random() - 0.5) * spread[0] * max(0.7, z / 2.5),
                              (rng.random() - 0.5) * spread[1] * max(0.7, z / 2.5), z], np.float32)
            sz = size * (0.7 + 0.6 * rng.random())
        Rm = Rm_bundle if arrangement == 'bundle' else rot_matrix(rng)
        if arrangement == 'bundle':
            # every copy shares the orientation; the bundle runs along `axis`, copies offset across it
            perp = np.cross(axis, [0, 0, 1.0]); perp /= np.linalg.norm(perp)
            perp2 = np.cross(axis, perp)
            if k > 0:
                c = c_tgt + perp * (rng.random() - 0.5) * 3.2 * size + perp2 * (rng.random() - 0.5) * 3.2 * size \
                    + axis * (rng.random() - 0.5) * 6.0 * size
                if c[2] < 1.2:
                    continue
        for ci, ch in enumerate(chains):
            col = colors[ci % len(colors)]
            pts = (ch[::stride] * sz * 0.5) @ Rm.T + c
            # v5 (2026-10-05, step 3): one CAPSULE per trace segment — a true tube with its own
            # shading and depth, so near molecules stay tubes instead of fusing into bead lumps
            for idx, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
                stage.items.append(('capsule', a, b, radius, (col, glow)))
                if (idx + 1) % 7 == 0:
                    stage.items.append(('sphere', b, radius * 1.7, accent, glow * 2.0))
    if membrane or arrangement == 'sheet':
        mcol = tuple(np.clip(np.array(colors[1 % len(colors)]) * 0.55, 0, 1))
        base = c_tgt + ez * size * 0.6
        head = radius * 2.0
        ext = int(3.4 * size / (head * 2.2))
        for i in range(-ext, ext + 1):
            for j in range(-ext, ext + 1):
                q = base + ex * i * head * 2.2 + ey * j * head * 2.2 + rng.normal(scale=head * 0.3, size=3)
                stage.items.append(('sphere', q, head, mcol, glow * 0.4))
    stage.jitter = radius * 0.05
    return stage


KITS['fog'] = kit_fog_atom
KITS['tubes'] = kit_tubes
# per-kit denoise (arrival costume, travel floor); None = the dive flag's value. Brand pass 2
# (2026-10-03): a fog field survives 0.45 but 0.60 turns it into a sunburst — keep fog soft.
KIT_DEN = {'fog': (0.50, 0.45)}


# ---- AUTO-STAGE: suggest a kit for an existing card from its words + band ---------------------
_RX = {
    'lattice': re.compile(r"\b(lattice|crystal|rhomb|cubic|hexagon|tetrahedr|unit cell|courses? of atoms|"
                          r"atoms? (?:set|at rest|in ranks|packed)|graphite|diamond|dendrit|sheet silicate)", re.I),
    'nucleus': re.compile(r"\b(nucleus|nuclei|droplet of|glowing spheres|nucleon|proton|neutron|alpha|pasta)\b", re.I),
    'quark':   re.compile(r"\b(quark|gluon|flux tube|three glowing cores|taut (?:amber |light )?strands?|rope of light)", re.I),
    'fog':     re.compile(r"\b(fog|probability|electron cloud|cloud of|shells? of radiance|orbital|haze about|lobes?|"
                          r"one atom|single atom|an atom)\b", re.I),
    'cells':   re.compile(r"\b(cells|cellular|tissue|epiderm\w*|mesophyll|honeycomb of cells|palisade|cortex)\b", re.I),
    'tubes':   re.compile(r"\b(protein|helix|helical|ribbon|chain|rope|collagen|backbone|coil|enzyme|antibody|"
                          r"motor|turbine|fib(?:er|re|ril)s?)\b", re.I),
}
_VARIANT = [('hex', re.compile(r"\b(ice|hexagon|six-sided|quartz|snow)\b", re.I)),
            ('rhombo', re.compile(r"\b(calcite|rhomb|leaning|slanted box)\b", re.I)),
            ('diamond', re.compile(r"\b(diamond|carbon|tetrahedr)\b", re.I)),
            ('sheets', re.compile(r"\b(graphite|sheet|layer|mica|slate|clay|stack)", re.I)),
            ('fcc', re.compile(r"\b(metal|copper|gold|silver|iron|brass|bronze|close-packed)\b", re.I)),
            ('cubic', re.compile(r"\b(salt|halite|cube|cubic)\b", re.I))]
_PDB_BY_WORD = [('1BNA', re.compile(r"\b(dna|double.helix|base.pair|nucleosome)\b", re.I)),
                ('1TUB', re.compile(r"\b(microtubule|tubulin)\b", re.I)),
                ('1CGD', re.compile(r"\b(collagen|triple.helix)\b", re.I)),
                ('4HHB', re.compile(r"\b(hemoglobin|haemoglobin|blood|oxygen)\b", re.I)),
                ('1IGT', re.compile(r"\b(antibody|immunoglobulin)\b", re.I)),
                ('2VV5', re.compile(r"\b(atp|synthase|rotor|turbine)\b", re.I))]


_RX_PASTA = re.compile(r"\b(pasta|spaghetti|lasagn\w*|gnocchi|kneaded|woven sheets?|rods? of matter|parking.garage)\b", re.I)
_RX_TRACKS = re.compile(r"\b(tracks?|bubble chamber|spray|streaks?|cascade|forking|spiral(?:ling)? path)\b", re.I)
_RX_FLUID = re.compile(r"\b(fluid|soup|melted|melting|seething|broth|boil(?:ing)?|fireball)\b", re.I)
_RX_AMORPH = re.compile(r"\b(glass|glassy|amorphous|random network|molten|melt|tangle|disorder\w*)\b", re.I)
_RX_COULOMB = re.compile(r"\b(bare nuclei|white dwarf|frozen plasma|crystalli[sz]ed plasma|coulomb)\b", re.I)


def suggest_stage(reg, seed_key=''):
    """A `stage` dict for a card, or None (render as today). WORDS FIRST (the card names its
    picture), then a journey-seeded draw among the band's kits so two journeys with the same
    kind of card do not get the same stage (Phil 2026-10-05: avoid sameness, take liberties)."""
    import zlib
    exp = reg.get('exp')
    if not isinstance(exp, (int, float)) or exp > -3.5:
        return None
    draw = zlib.crc32(f"{seed_key}|{reg.get('name')}".encode()) % 100
    txt = f"{reg.get('scene') or ''} {reg.get('target') or reg.get('target_phrase') or ''}"
    if exp <= -12:
        if _RX['quark'].search(txt):
            return {'kit': 'quark'}
        if _RX_PASTA.search(txt):
            return {'kit': 'pasta'}
        if _RX_TRACKS.search(txt):
            return {'kit': 'tracks', 'look': 'ink'}
        if _RX_FLUID.search(txt) and not _RX['nucleus'].search(txt):
            return {'kit': 'fluid'}
        # nucleus words or nothing specific: a seeded spread across the subnuclear kits
        if draw < 60:
            return {'kit': 'nucleus'}
        if draw < 78:
            return {'kit': 'fluid'}
        if draw < 92:
            return {'kit': 'pasta'}
        return {'kit': 'tracks', 'look': 'ink'}
    if exp <= -8.5:
        if _RX['lattice'].search(txt):
            var = next((v for v, rx in _VARIANT if rx.search(txt)), 'cubic')
            return {'kit': 'lattice', 'variant': var, 'spacing': 0.5, 'radius': 0.06}
        # every other atomic-band card -> a lattice (the honest picture at 10^-10 m is atoms in
        # their courses). Phil 2026-10-04: the hero fog atom rang/burst; the fuzzy lattice became
        # ringed roses — neither is used. Amorphous words -> the random network; "bare nuclei /
        # white dwarf" -> the Coulomb crystal (glowing points, no bonds, plasma look); otherwise
        # the variant is named by the words or DRAWN per journey (cubic/hex/fcc/diamond).
        if _RX_COULOMB.search(txt):
            return {'kit': 'lattice', 'variant': 'cubic', 'bonds': False, 'glow': 0.5,
                    'radius': 0.05, 'look': 'plasma'}
        if _RX_AMORPH.search(txt):
            return {'kit': 'lattice', 'variant': 'random', 'spacing': 0.5, 'radius': 0.06, 'glow': 0.2}
        var = next((v for v, rx in _VARIANT if rx.search(txt)), None)
        if var is None:
            var = ['cubic', 'hex', 'fcc', 'diamond', 'random', 'rhombo'][draw % 6]
        return {'kit': 'lattice', 'variant': var, 'spacing': 0.5, 'radius': 0.06, 'glow': 0.2}
    if exp <= -6:
        # a LATTICE named in the molecular band (ice lattice, water cages, clathrate) is a
        # lattice card whatever its exponent (anvil's ice_lattice at -6.9 was left plain)
        if _RX['lattice'].search(txt) and not _RX['tubes'].search(txt):
            var = next((v for v, rx in _VARIANT if rx.search(txt)), 'cubic')
            return {'kit': 'lattice', 'variant': var, 'spacing': 0.5, 'radius': 0.06, 'glow': 0.2}
        # molecular (tubes v4): the molecule from the card's words, the arrangement from its
        # structure words; cards with no molecular word stay plain
        if not _RX['tubes'].search(txt):
            return None
        low = txt.lower()
        pdb = next((pid for pid, rx in _PDB_BY_WORD if rx.search(txt)), None)
        if pdb is None:
            for key, pid in _PDB_LIBRARY.items():
                if key in low:
                    pdb = pid; break
        # waxes / fatty chains / lipid lamellae are not proteins: short rods laid side by side
        if re.search(r"\b(wax|waxy|fatty|lipid|suberin|cutin|lamellae|lamella)\b", low):
            return {'kit': 'tubes', 'pdb': '1CGD', 'arrangement': 'bundle', 'size': 0.55, 'density': 1.6}
        if pdb is None:
            pdb = ['4HHB', '1MBN', '1LYZ', '1EMA', '1AO6', '1A8E'][abs(hash(txt)) % 6]
        arr = ('bundle' if re.search(r"\b(collagen|cellulose|keratin|fib(?:er|re|ril)s?|rope|cable|bundle|strands?)\b", low)
               else 'sheet' if re.search(r"\b(membrane|bilayer|thylakoid|disc|sheet|wall|skin)\b", low)
               else 'chain' if re.search(r"\b(polysome|necklace|string of|bead-string|chain of)\b", low)
               else 'sea')
        return {'kit': 'tubes', 'pdb': pdb, 'arrangement': arr, 'size': 0.9}
    # cellular (-6 .. -3.5): tissue for MANY cells (a tissue, cells packed/paved/ranked), never
    # for the interior of ONE cell (organelles, a division theatre, a cell's fluid)
    if re.search(r"\b(within|inside|interior of|in) (one|a single|the) [a-z\- ]*cell\b|\bone cell\b|\bsingle cell\b",
                 txt, re.I):
        return None
    if _RX['cells'].search(txt):
        return {'kit': 'tissue', 'cell': 0.22}
    return None


# ---- TISSUE kit: cells packed wall to wall (cellular band, 272 cards) -------------------------
def kit_tissue(stage, centre=(0, 0, 3.0), size=1.0, colors=((0.55, 0.85, 0.6), (0.95, 0.9, 0.7)),
               wall_rgb=None, cell=0.22, n_layers=3, layer_gap=0.9, organelles=3, seed=0, glow=0.1,
               tilt=0.35, target_depth=None):
    """A tissue in section seen obliquely: a few stacked sheets of polygonal cells (2-D Voronoi
    on each sheet), the walls as raised ridges (sphere chains along the Voronoi edges), a few
    organelle spheres inside every cell, the sheets receding into fog. The target cell sits on
    the aim ray so the plunge enters one cell."""
    from scipy.spatial import Voronoi
    rng = np.random.default_rng(seed)
    wall_rgb = wall_rgb or tuple(np.clip(np.array(colors[1]) * 0.9 + 0.1, 0, 1))
    c0 = np.asarray(centre, np.float32)
    # sheet basis: a plane facing the camera, tilted so it recedes (depth across the frame)
    ex = np.array([1.0, 0.0, 0.0], np.float32)
    ey = np.array([0.0, math.cos(tilt), math.sin(tilt)], np.float32)
    ez = np.cross(ex, ey)
    ext = size * 3.2
    for L in range(n_layers):
        origin = c0 + ez * (L * layer_gap * size) + rng.normal(scale=0.05 * size, size=3)
        n = int((2 * ext / cell) ** 2 * 0.9)
        pts = (rng.random((n, 2)) - 0.5) * 2 * ext
        # hexagonal-ish regularity: relax toward a jittered grid
        g = np.array([(i * cell + (j % 2) * cell / 2, j * cell * 0.87) for i in range(-int(ext / cell) - 1, int(ext / cell) + 2)
                      for j in range(-int(ext / cell) - 1, int(ext / cell) + 2)], np.float32)
        g += rng.normal(scale=cell * 0.18, size=g.shape)
        pts = g
        vor = Voronoi(pts)
        r_wall = cell * 0.075 * size
        for (a, b), (p1, p2) in zip(vor.ridge_vertices, vor.ridge_points):
            if a < 0 or b < 0:
                continue
            va, vb = vor.vertices[a], vor.vertices[b]
            if np.abs(va).max() > ext or np.abs(vb).max() > ext:
                continue
            A3 = origin + ex * va[0] * size + ey * va[1] * size
            B3 = origin + ex * vb[0] * size + ey * vb[1] * size
            nseg = max(2, int(np.linalg.norm(B3 - A3) / (r_wall * 1.1)))
            for t in np.linspace(0, 1, nseg):
                # ridge stands a little proud of the sheet (toward the camera)
                stage.items.append(('sphere', A3 + (B3 - A3) * t - ez * r_wall * 0.6, r_wall, wall_rgb, glow * 0.5))
        for q in pts:
            if np.abs(q).max() > ext * 0.95:
                continue
            cc = origin + ex * q[0] * size + ey * q[1] * size
            # cell floor: a flat disc of soft glow (the cytoplasm) + organelles
            stage.items.append(('glow', cc + ez * cell * 0.2 * size, cell * 0.42 * size, colors[0], glow * 0.35))
            for _ in range(organelles):
                o = cc + ex * rng.normal(scale=cell * 0.22) * size + ey * rng.normal(scale=cell * 0.22) * size
                stage.items.append(('sphere', o - ez * cell * 0.05 * size, cell * (0.07 + 0.05 * rng.random()) * size,
                                    colors[1 % len(colors)], glow))
    stage.jitter = cell * size * 0.004
    return stage


KITS['tissue'] = kit_tissue


# ---- SUBATOMIC-INSPIRED KITS (2026-10-05, Phil: "take some more liberties ... more stages
# inspired by subatomic realms, not necessarily accurate") -----------------------------------
def kit_fluid(stage, centre=(0, 0, 3.0), size=1.0, colors=((1.0, 0.75, 0.3), (0.95, 0.4, 0.5)), seed=0,
              glow=0.3, n=260, spread=(3.0, 3.4, 8.0)):
    """The quark-gluon fluid: no bound triplets anywhere — a seething broth of loose sparks and
    short writhing strands at all depths, densest around the target point."""
    rng = np.random.default_rng(seed)
    c0 = np.asarray(centre, np.float32)
    r0 = size * 0.045
    for k in range(n):
        if k < n // 3:
            c = c0 + rng.normal(scale=size * 0.45, size=3)
        else:
            z = 0.8 + spread[2] * rng.random() ** 0.8
            c = np.array([(rng.random() - 0.5) * spread[0] * max(0.6, z / 3.0),
                          (rng.random() - 0.5) * spread[1] * max(0.6, z / 3.0), z], np.float32)
        col = colors[int(rng.random() < 0.5) % len(colors)]
        if rng.random() < 0.55:
            stage.items.append(('sphere', c, r0 * (0.6 + 0.8 * rng.random()), col, glow))
            stage.items.append(('glow', c, r0 * 2.5, col, glow * 0.3))
        else:                                   # a short writhing strand of beads
            d = rng.normal(size=3); d /= np.linalg.norm(d)
            m = int(rng.integers(3, 8))
            for t in range(m):
                wob = rng.normal(scale=r0 * 0.6, size=3)
                stage.items.append(('sphere', c + d * t * r0 * 1.6 + wob, r0 * 0.55, col, glow * 0.8))
    stage.jitter = r0 * 0.15
    return stage


def kit_tracks(stage, centre=(0, 0, 3.0), size=1.0, colors=((0.85, 0.9, 1.0), (1.0, 0.6, 0.3)), seed=0,
               glow=0.25, n_tracks=16, spread=(3.2, 3.6, 7.0)):
    """Bubble-chamber tracks: a tightening spiral at the target (a particle losing energy),
    straight and gently curved tracks around it, a few forks — beads along every path."""
    rng = np.random.default_rng(seed)
    c0 = np.asarray(centre, np.float32)
    rb = size * 0.018

    def beads(pts, col, r):
        for a, b in zip(pts[:-1], pts[1:]):
            L = np.linalg.norm(b - a); m = max(1, int(L / (r * 1.6)))
            for t in np.linspace(0, 1, m, endpoint=False):
                stage.items.append(('sphere', a + (b - a) * t, r, col, glow))

    # the hero spiral, in a plane facing the camera-ish, winding to the target point
    Rm = rot_matrix(rng)
    th = np.linspace(0, 6.5 * np.pi, 160)
    rad = size * 0.55 * np.exp(-0.17 * th)
    sp = np.stack([rad * np.cos(th), rad * np.sin(th), 0.04 * size * th / th[-1]], -1) @ Rm.T + c0
    beads(sp[::-1], colors[0], rb * 1.2)
    stage.items.append(('glow', c0, size * 0.12, colors[1 % len(colors)], glow * 1.5))
    for k in range(n_tracks):
        z = 0.9 + spread[2] * rng.random() ** 0.8
        p0 = np.array([(rng.random() - 0.5) * spread[0] * max(0.6, z / 3.0),
                       (rng.random() - 0.5) * spread[1] * max(0.6, z / 3.0), z], np.float32)
        d = rng.normal(size=3); d /= np.linalg.norm(d)
        L = size * (0.8 + 1.6 * rng.random())
        curv = rng.normal(size=3) * 0.25
        t = np.linspace(0, 1, 40)[:, None]
        pts = p0 + d * t * L + curv * (t ** 2) * L
        col = colors[k % len(colors)]
        beads(pts, col, rb * (0.7 + 0.6 * rng.random()))
        if rng.random() < 0.35:                 # a fork: two branches from the midpoint
            mid = pts[20]
            for sgn in (-1, 1):
                d2 = d + sgn * np.cross(d, [0, 0, 1.0]) * 0.5 + rng.normal(scale=0.1, size=3)
                d2 /= np.linalg.norm(d2)
                beads(mid + d2 * np.linspace(0, 0.6 * L, 18)[:, None], col, rb * 0.7)
        if rng.random() < 0.3:                  # a small secondary spiral
            th2 = np.linspace(0, 4 * np.pi, 70)
            r2 = size * 0.14 * np.exp(-0.25 * th2)
            Rm2 = rot_matrix(rng)
            sp2 = np.stack([r2 * np.cos(th2), r2 * np.sin(th2), 0 * th2], -1) @ Rm2.T + pts[-1]
            beads(sp2, col, rb * 0.6)
    stage.jitter = 0.0
    return stage


def kit_pasta(stage, centre=(0, 0, 3.0), size=1.0, colors=((1.0, 0.55, 0.25), (0.8, 0.85, 1.0)), seed=0,
              glow=0.2, phase=None, spread=(3.4, 3.8, 7.5)):
    """Nuclear pasta: matter kneaded into RODS (spaghetti), SHEETS (lasagna) or dense BLOBS
    (gnocchi) — ranks of close-packed nucleons, the camera diving between them."""
    rng = np.random.default_rng(seed)
    phase = phase or ['rods', 'sheets', 'gnocchi'][int(rng.integers(0, 3))]
    c0 = np.asarray(centre, np.float32)
    r = size * 0.06
    Rm = rot_matrix(rng)
    if phase == 'rods':
        for i in range(-5, 6):
            for j in range(-4, 5):
                if rng.random() < 0.15:
                    continue
                off = np.array([i * r * 5.5, j * r * 5.5, 0], np.float32)
                col = colors[(i + j) % len(colors)]
                for t in np.linspace(-size * 2.2, size * 2.2, int(4.4 * size / (r * 1.7))):
                    p = np.array([off[0], off[1], t], np.float32) + rng.normal(scale=r * 0.12, size=3)
                    stage.items.append(('sphere', (p @ Rm.T) + c0, r, col, glow))
    elif phase == 'sheets':
        for k in range(-3, 4):
            col = colors[k % len(colors)]
            zz = k * r * 7.0
            for i in range(-14, 15):
                for j in range(-14, 15):
                    if rng.random() < 0.08:
                        continue
                    p = np.array([i * r * 1.9 + (j % 2) * r * 0.95, j * r * 1.65, zz], np.float32)
                    p += rng.normal(scale=r * 0.1, size=3)
                    stage.items.append(('sphere', (p @ Rm.T) + c0, r, col, glow))
    else:  # gnocchi: dense close-packed blobs in a loose lattice
        for i in range(-3, 4):
            for j in range(-3, 4):
                for k in range(-2, 3):
                    if rng.random() < 0.2:
                        continue
                    cc = np.array([i, j, k], np.float32) * r * 7.0 + rng.normal(scale=r * 0.8, size=3)
                    pq, _ = _pack(rng, int(rng.integers(14, 30)), r, iters=18)
                    col = colors[(i + j + k) % len(colors)]
                    for q in pq:
                        stage.items.append(('sphere', ((cc + q) @ Rm.T) + c0, r, col, glow))
    stage.phase = phase
    stage.jitter = r * 0.05
    return stage


KITS['fluid'] = kit_fluid
KITS['tracks'] = kit_tracks
KITS['pasta'] = kit_pasta
KIT_DEN.update({'tracks': (0.50, 0.45), 'fluid': (0.55, 0.45)})
