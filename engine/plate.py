"""PLANET PLATE (2026-09-17 — PLAN.md "PLANET DESCENT — THE PLATE PLAN"; lab flag, default OFF).

The space->planet card has never worked because the planet never EXISTS in the pixels the
feedback chain feeds on: at cfg 2 / travel denoise 0.40 the fed image owns the frame, the
tracker has never once locked a planet (0 object-phase frames in all 8 approaches on disk),
and the "space" is inherited texture that the arrival then morphs into landscape. Every fix
so far steered the diffusion (words, depth-CN, warps). This module supplies the PIXELS —
the one channel the engine provably obeys (a pasted cameo sprite persists and grows through
the zoom while everything around it churns):

  * a SPHERE rendered procedurally from a once-generated surface texture (txt2img of the
    NEXT card's orbit-view scene), composited into the fed frame every frame at the EXACT
    scheduled size (hero formula: s_j = s0 * prod(z), s0 chosen so the disc covers the frame
    by the card boundary) — the disc interior is fed back inside itself (crop-and-reimagine
    within the disc) so its surface stays alive and grows;
  * a VOID plate (txt2img of the card's own scene, spaceless) blended under the void so the
    space stays space, zoomed alongside the frame each step;
  * a GRADED NOISE MASK (DifferentialDiffusion + SetLatentNoiseMask): full denoise inside
    the disc, a fraction outside — the void is never re-diffused hard enough to become terrain;
  * optional REGIONAL prompts (ConditioningSetMask): an orbit-view prompt inside the disc, the
    schedule's own prompt outside;
  * the tracker is BYPASSED on plate cards (we own the sphere's centre — it is the zoom's
    fixed point, easing toward frame centre as it grows so the descent lands on the surface,
    not the limb); cameos are refused on plate cards (the takeover class).

dive.py owns the loop, the diffusion calls and the zoom; this module owns geometry + pixels.
Modes (dive --plate MODE):  low    = plate + global denoise cap 0.32 (the cameo mechanism)
                            mask   = plate + graded noise mask, scheduled denoise
                            region = mask + regional prompts
"""
import math
import re

import numpy as np
from PIL import Image, ImageFilter

# a planet-class card: a round WORLD target that descends to the planetary band next
# the planet-card rule lives in scripts/pipeline.py (the batch and the dashboard need it
# without engine imports); this module delegates so the three can never disagree
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "scripts"))
from pipeline import PLANET_TARGET, is_planet_card as _is_planet_card  # noqa: E402


def is_plate_card(reg, nxt):
    return _is_planet_card(reg, nxt)


def _scene(reg):
    return reg.get("scene") or reg.get("interior") or ""


def _pal(reg, text):
    pal = reg.get("palette")
    return f"{text}, {pal} colors" if pal else text


def surface_prompt(nxt, style):
    """The sphere's texture: the NEXT card's world (it already describes the planet from
    orbit) painted as a flat surface seen from straight above, no limb, no space."""
    return _pal(nxt, f"a satellite view looking straight down onto the surface of {_scene(nxt)}, "
                     f"a flat aerial map of the ground filling the entire frame edge to edge, "
                     f"no sky, no horizon, {style}")


SURFACE_NEG = ("planet, sphere, globe, ball, black space, stars, starfield, horizon, "
               "curved limb, curve of the world, night sky, sky, skyline, sunset, beach, "
               "cliffs, ground-level view, eye-level view, frame, border, vignette")
# the surface plate must be TOP-DOWN: a caption naming sky/horizon/shore means SDXL painted a
# ground-level landscape (garnet: an aurora over a sea cliff) — reject + re-roll
SURFACE_BAIT = re.compile(
    r"\b(sky|skies|horizon|skyline|sunset|sunrise|beach|shore(?:line)?|cliffs?|coastline at night|"
    r"aurora borealis|northern lights|in the distance|mountains? in the background|"
    r"standing|person|people)\b", re.I)


def void_prompt(reg, style):
    """The void plate: the star card's own scene as deep space, no ground, no horizon —
    the T_ESTABLISH_SPACE idea, generated once for this card."""
    return _pal(reg, f"an immense expanse of {_scene(reg)}, deep black space stretching beyond "
                     f"the frame in every direction, no ground, no horizon, seen from within, "
                     f"{style}")


VOID_NEG = ("landscape, horizon, ground, terrain, foreground rocks, flowers, meadow, beach, "
            "desert, mountains, trees, buildings, sky above land, close-up, macro, "
            "planet, moon, globe, sphere, necklace, pendant, jewelry, product shot")


def inside_prompt(nxt, style):
    """Regional prompt INSIDE the disc while the globe is still an object in the frame.
    v3: never name "a planet" as an OBJECT here — v2's region arm painted a small planet
    inside the disc and the handoff dove into that marble. Describe the SURFACE filling the
    disc, curving away to the limb."""
    return _pal(nxt, f"the vast surface of {_scene(nxt)}, filling the view and curving away "
                     f"to the limb of the world against black space, a thin glowing rim of "
                     f"atmosphere at the edge, {style}")


GLOBE_CLAUSE = "a single round planet hanging in the black void of space"
# while the globe is an OBJECT in the frame: once it is wider than the portrait frame its upper
# and lower limbs are gentle arcs, and a scene word like "floor"/"plain" lets the model flatten
# them into a HORIZON with space beneath (vernal_clutch's star_floor card, 2026-09-19: "the
# planet stretched out horizontally and faded away into space")
GLOBE_NEG = "horizon, horizon line, flat ground, floor, ground plane, landscape, skyline"

# VOID-PLATE OBJECT GATE (2026-09-17, garnet lab): a cold txt2img of a star scene can come
# back as a PRODUCT SHOT — garnet's "two stars sharing one pinched envelope ... a moon-silver
# disc wound about the compact one" under the crystalline deck rendered a glass pendant on a
# necklace chain (the molecular-library jewelry prior). Same defence as the frame-0 figure
# gate: judge the CAPTION (names what the picture is ABOUT), re-roll the seed on a hit.
OBJECT_BAIT = re.compile(
    r"\b(necklace|pendant|jewel(?:le)?ry|chain|ring|earrings?|bracelet|brooch|gem(?:stone)?s?|"
    r"ornament|vase|bottle|jar|snow globe|lamp|bowl|plate|dish|table|tabletop|coin|medal|"
    r"watch|clock|logo|badge|button|marble|bead)\b", re.I)


def _bait(pil, rx, model=None):
    import detect          # lazy (detect imports dive; by call time dive is loaded)
    try:
        if model:
            detect.MODEL = model
        cap = detect.caption(pil)
    except Exception:
        return None
    if not cap:
        return None
    hits = sorted({w.lower() for w in rx.findall(cap)})
    return (hits, cap.strip()) if hits else None


def void_bait(pil, model=None):
    """(matched words, caption) if the void plate reads as an OBJECT, else None. Never
    raises — a detector failure must not kill a render."""
    return _bait(pil, OBJECT_BAIT, model)


def surface_bait(pil, model=None):
    """(matched words, caption) if the surface plate reads as a GROUND-LEVEL view."""
    return _bait(pil, SURFACE_BAIT, model)


# ── sphere renderer ────────────────────────────────────────────────────────────────
def _bilinear(tex, tx, ty):
    """Sample tex (H,W,3) float at fractional coords tx,ty in [0,1] (arrays)."""
    TH, TW = tex.shape[:2]
    x = np.clip(tx * (TW - 1), 0, TW - 1.001)
    y = np.clip(ty * (TH - 1), 0, TH - 1.001)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    c00 = tex[y0, x0]
    c10 = tex[y0, x0 + 1]
    c01 = tex[y0 + 1, x0]
    c11 = tex[y0 + 1, x0 + 1]
    return (c00 * (1 - fx) * (1 - fy) + c10 * fx * (1 - fy)
            + c01 * (1 - fx) * fy + c11 * fx * fy)


def render_sphere(tex, diam_px, light=(-0.45, -0.55, 0.70), rim_rgb=None, spin_deg=0.0,
                  ambient=0.38):
    """Orthographic globe of diameter diam_px from an equirect hemisphere texture.
    Returns (rgb float32 (D,D,3) in 0..1, alpha float32 (D,D), shade float32 (D,D)) where
    D = the canvas (disc + atmosphere rim), alpha covers disc + rim glow, and shade is the
    multiplicative limb/lighting dome (1 outside the disc) for re-imposing the sphere read
    on fed-back pixels."""
    R = max(3.0, diam_px / 2.0)
    pad = int(math.ceil(R * 0.05)) + 3
    D = int(math.ceil(2 * R)) + 2 * pad
    c = D / 2.0
    yy, xx = np.mgrid[0:D, 0:D].astype(np.float32)
    u = (xx - c) / R
    v = (yy - c) / R
    r2 = u * u + v * v
    inside = r2 < 1.0
    z = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    # texture mapping: the texture is a FULL 360-degree equirect map (2:1); the visible
    # hemisphere shows half of it, and `spin_deg` revolves the globe about its vertical
    # axis (v3, 2026-09-17: a fixed-point zoom into a static disc locked the interior into
    # concentric rings in the mask arms — revolution breaks the radial symmetry, and it is
    # the orbit motion Phil asked for in August)
    lon = np.arctan2(u, np.maximum(z, 1e-4)) + math.radians(spin_deg)
    lat = np.arcsin(np.clip(v, -1.0, 1.0))
    tx = np.mod(lon / (2 * math.pi) + 0.5, 1.0)
    ty = np.clip(lat / math.pi + 0.5, 0.0, 1.0)
    rgb = _bilinear(tex, tx, ty) * 1.08
    # lighting: lambert from `light` + ambient, gentle limb darkening (v3: brighter — the
    # v2 globe read as a dark ball against a bright void)
    lx, ly, lz = light
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    ndl = np.clip((u * lx + v * ly + z * lz) / ln, 0.0, 1.0)
    shade = (ambient + (1.0 - ambient) * ndl) * (0.72 + 0.28 * np.sqrt(z))
    rgb = np.clip(rgb * shade[..., None], 0.0, 1.0)
    # rim: a thin bright atmosphere line just inside the limb + a soft glow outside
    r = np.sqrt(r2)
    if rim_rgb is None:
        bright = tex.reshape(-1, 3)
        q = np.quantile(bright.mean(axis=1), 0.8)
        rim_rgb = np.clip(bright[bright.mean(axis=1) >= q].mean(axis=0) * 1.25 + 0.15, 0, 1)
    rim_rgb = np.asarray(rim_rgb, np.float32)
    # THIN RIM (Phil 2026-09-18: the border around the planet "doesn't look great"): a fine
    # atmosphere line at the limb and almost no halo outside it. The wide glow (sigma 0.05R at
    # alpha 0.85) was also what forced the wide vacate that carved a dark moat round the globe.
    inner_line = np.exp(-((r - 0.990) / 0.012) ** 2) * inside
    rgb = np.clip(rgb + inner_line[..., None] * rim_rgb * 0.35, 0.0, 1.0)
    glow = np.exp(-((np.maximum(r, 1.0) - 1.0) / 0.012) ** 2) * (~inside)
    alpha = np.where(inside, np.clip((1.0 - r) / 0.012, 0.0, 1.0), 0.0).astype(np.float32)
    alpha = np.maximum(alpha, 0.40 * glow).astype(np.float32)
    rgb = np.where(inside[..., None], rgb, rim_rgb[None, None, :] * 0.9)
    shade_full = np.where(inside, shade, 1.0).astype(np.float32)
    return rgb.astype(np.float32), alpha, shade_full


def lift_darks(t, knee=0.28, slope=0.36):
    """No VOID-BLACK regions on a globe. Grow v12-v14 all showed "a dark bite out of the
    sphere": not shading, not identity drift — sargasso's surface texture has a near-black
    river across a sixth of it, and black-on-black against the void reads as a missing chunk.
    Luminance under `knee` is compressed toward it (L=0 -> ~0.18, continuous and monotone at
    the knee) in the pixel's own hue, or the texture's mean hue where the pixel has none."""
    lw = np.array([0.299, 0.587, 0.114], np.float32)
    lum = t @ lw
    mean = t.reshape(-1, 3).mean(axis=0)
    col = t + 0.03 * mean[None, None, :]
    cl = np.maximum(col @ lw, 1e-4)
    target = knee - (knee - lum) * slope
    lifted = np.clip(col * (target / cl)[..., None], 0.0, 1.0)
    return np.where((lum < knee)[..., None], lifted, t).astype(np.float32)


# ── entrances ──────────────────────────────────────────────────────────────────────
def perimeter_point(t, w, h):
    """A point on the frame boundary, t in [0,1) running clockwise from the top-left corner,
    in fractional coords, plus the outward unit normal (in PIXEL space)."""
    P = 2.0 * (w + h)
    d = (t % 1.0) * P
    if d < w:
        return (d / w, 0.0), (0.0, -1.0)
    d -= w
    if d < h:
        return (1.0, d / h), (1.0, 0.0)
    d -= h
    if d < w:
        return (1.0 - d / w, 1.0), (0.0, 1.0)
    d -= w
    return (0.0, 1.0 - d / h), (-1.0, 0.0)


def draw_entrance(key, w, h, s_limb, z_card, kind=None):
    """ONE description for every way a globe can arrive (Phil 2026-09-19: "start anywhere in
    frame or come in from any direction with a small planet and grow it — the most possible
    variety of entrances"). Deterministic from `key` (journey:card[:seed]).

        start  where the globe is when it is introduced — in frame, or beyond ANY point of
               the frame boundary (not just four edges)
        goal   where it sits at the bar line (a central region, never dead centre)
        k      growth law: size = s_limb * (Z/Z_card)^k. 0.6 = already a globe (~0.3 x width),
               1.0 = the zoom's own rate, 1.75 = a point of light
        bow    sideways bulge of the path as a fraction of its length (0 = straight)

    kinds: 'enter' (big globe from off-frame) · 'grow' (a point that swells in place) ·
    'travel' (a SMALL globe that comes from off-frame or across the frame while it grows) ·
    None = a weighted draw of all three."""
    import zlib
    hv = zlib.crc32(key.encode())
    r = lambda n: ((zlib.crc32(f"{key}#{n}".encode()) % 10000) / 10000.0)   # noqa: E731
    if kind is None:
        kind = ("enter", "enter", "enter", "grow", "grow", "grow",
                "travel", "travel", "travel", "travel")[hv % 10]
    goal = (0.42 + 0.20 * r(1), 0.40 + 0.14 * r(2))
    spin = (1.0 + 1.0 * r(11)) * (1.0 if r(12) < 0.5 else -1.0)      # deg/frame, either way
    bow = (-0.16, 0.0, 0.0, 0.16)[int(r(3) * 4) % 4]
    if kind == "grow":
        k = 1.75
        start = (0.30 + 0.40 * r(4), 0.28 + 0.40 * r(5))
        # it swells WHERE IT IS (no path: the zoom's own slow ease toward centre carries it,
        # and a stationary point keeps the full spiked star glint)
        goal = start
        bow = 0.0
    else:
        k = 0.6 if kind == "enter" else (1.10 + 0.35 * r(6))
        size0 = s_limb * (1.0 / z_card) ** k                 # diameter, fraction of width
        rpx = size0 * w / 2.0
        if kind == "travel" and r(7) < 0.5:
            # DRIFTS IN FROM INSIDE THE FRAME (artifact-free by construction: it rides the
            # zoom's stream, see Plate.aim): starts near any point of the frame boundary, a
            # little inside it, far from where it will settle
            (px, py), (nx, ny) = perimeter_point(r(8), w, h)
            inset = 0.07 + 0.10 * r(9)
            start = (px - nx * inset * (h / w if nx else 1.0) * 0.6, py - ny * inset)
            start = (min(0.93, max(0.07, start[0])), min(0.93, max(0.06, start[1])))
            # the stream's fixed point P = S - (G - S)/(Zpath - 1) must lie in the frame;
            # Zpath >= ~4 on any card, so keep S - (G - S)/3 inside
            for _ in range(12):
                Px, Py = start[0] - (goal[0] - start[0]) / 3.0, start[1] - (goal[1] - start[1]) / 3.0
                if 0.01 <= Px <= 0.99 and 0.01 <= Py <= 0.99:
                    break
                start = (start[0] + 0.12 * (goal[0] - start[0]), start[1] + 0.12 * (goal[1] - start[1]))
        else:
            (px, py), (nx, ny) = perimeter_point(r(8), w, h)
            pad = rpx + 0.03 * w
            start = (px + nx * pad / w, py + ny * pad / h)
            if kind == "enter":
                bow = 0.0                 # the approved enter is a straight path
                # PATH BUDGET. The approved enter crosses ~350 px in a card; the portrait frame
                # makes a top/bottom entry twice that, and the crescent the globe vacates each
                # frame twice as thick. Settle nearer the side it came from, and if the path is
                # still long let it start partly in view (it arrives inside the arrival morph).
                goal = (min(0.62, max(0.40, 0.5 + (start[0] - 0.5) * 0.25)),
                        min(0.60, max(0.36, 0.48 + (start[1] - 0.48) * 0.25)))
                dxp, dyp = (start[0] - goal[0]) * w, (start[1] - goal[1]) * h
                L = math.hypot(dxp, dyp)
                if L > 430.0:
                    start = (goal[0] + dxp * (430.0 / L) / w, goal[1] + dyp * (430.0 / L) / h)
    # the SUN moves too: lit from the left, the right or anywhere above (never from below —
    # under-lighting reads as wrong even in space). Same elevation as the approved look.
    az = math.radians(180.0 + 180.0 * r(10))
    light = (round(0.71 * math.cos(az), 3), round(0.71 * math.sin(az), 3), 0.70)
    return {"kind": kind, "start": (round(start[0], 4), round(start[1], 4)),
            "goal": (round(goal[0], 4), round(goal[1], 4)), "k": round(k, 3), "bow": bow,
            "light": light, "spin": round(spin, 2)}


# ── per-card state ─────────────────────────────────────────────────────────────────
class Plate:
    GLINT_PX = 40.0      # grow: below this radius the globe is drawn as a point of light
    MIN_CAP_PX = 34.0    # the protected (low-denoise) zone never shrinks below this radius

    """One plate = one planet card. Frames [s, e) render through it (arrival included: the
    sphere is introduced during the arrival morph and grows through travel + plunge)."""

    def __init__(self, card_idx, s, e, fa, reg, nxt, style, w, h, zooms, seed,
                 n_card=None, start_pos=(0.62, 0.40), s_limb=1.15, ease=0.06, outside=0.27,
                 spin_rate=1.5, intro="grow", edge="right", entrance=None):
        """Frames [s, e) = the planet card PLUS the next card (the plate spans the bar line:
        the next card is authored as the ORBIT VIEW, so the globe must reach that view — a
        disc wider than the frame, limb still visible top and bottom — exactly at the
        boundary, then keep growing through the arrival until the frame lies inside it, and
        only then hand off to the next card's normal approach on the surface). `zooms` =
        the schedule over the whole span; `n_card` = the planet card's frames; s_limb = the
        globe diameter (x frame width) at the bar line."""
        self.card_idx, self.s, self.e, self.fa = card_idx, s, e, fa
        self.reg, self.nxt = reg, nxt
        self.w, self.h = w, h
        self.zooms = list(zooms)
        self.n = n_card if n_card else len(self.zooms)
        Z = 1.0
        for z in self.zooms[:self.n]:
            Z *= z
        self.s_limb = s_limb
        self.Zcard = Z
        # INTRODUCTION (Phil 2026-09-18: never "appear in the middle out of nowhere" — the
        # globe either GROWS from a point, as a real approach looks, or ENTERS from beyond a
        # frame edge; vary it per journey). Size follows a power of the cumulative zoom,
        # s_j = s_limb * (Z_j / Z_card)^k, so it is s_limb exactly at the bar line whatever k:
        #   grow  k=2.0 -> starts at s_limb/100 (a star-like point) and accelerates in
        #   enter k=0.6 -> starts at ~a quarter of s_limb, already a globe, sliding in from
        #                  beyond `edge` along an ease-out path to the anchor by the bar line
        #   plain k=1.0 -> the zoom's own rate (the lab's arm B)
        self.intro = intro
        # grow k 2.0 -> 1.5 (v9 lab): at 2.0 the globe sat under a tenth of the width for two
        # thirds of the card and then had ~8 frames to reach the orbit view — it never
        # established. 1.5 starts it as a visible bright dot (~0.036 x width) and spreads
        # the growth.
        # grow 1.5 -> 1.75 (v14): the point is now introduced a beat later (after the arrival),
        # so a slightly steeper law keeps a ~8-frame point-of-light phase before it swells
        self.k = {"grow": 1.75, "enter": 0.6, "plain": 1.0}.get(intro, 1.0)
        if entrance:
            self.k = float(entrance["k"])
        self.size0 = s_limb * (1.0 / Z) ** self.k    # diameter, fraction of frame WIDTH
        self.size = self.size0
        self.edge = edge
        self.shift = (0.0, 0.0)           # px the carried disc must move this frame (enter)
        self.entry = None
        self.bow = 0.0
        self.entrance = entrance
        self.light = tuple(entrance["light"]) if entrance and entrance.get("light") \
            else (-0.45, -0.55, 0.70)
        if entrance:
            # unified entrances: any start, any settle point, any growth law, optional bow
            self.entry = tuple(entrance["start"])
            self.goal = tuple(entrance["goal"])
            self.bow = float(entrance.get("bow", 0.0))
            self.tx, self.ty = self.entry
            if abs(self.entry[0] - self.goal[0]) + abs(self.entry[1] - self.goal[1]) < 0.02:
                self.entry = None         # swells in place: no path
        elif intro == "enter":
            r_frac = self.size0 / 2.0                         # radius as a fraction of W
            ax, ay = 0.5, 0.5
            pad = 0.03
            self.entry = {"right": (1.0 + r_frac + pad, 0.42),
                          "left": (-r_frac - pad, 0.42),
                          "top": (0.55, -(r_frac * w / h) - pad),
                          "bottom": (0.45, 1.0 + (r_frac * w / h) + pad)}.get(edge,
                                                                            (1.0 + r_frac + pad, 0.42))
            self.tx, self.ty = self.entry
            self.goal = (0.56, 0.46)      # where the path lands at the bar line (then the
                                          # usual ease toward centre takes over)
        self.done = False                 # set once the frame lies inside the disc
        # a globe that STARTS AS A POINT is introduced only after the card's arrival morph
        # (v13: its first ~4 frames showed nothing — the arrival at full boost owned them and
        # the point could not compete). A globe that starts big enters during the arrival,
        # off-frame anyway, exactly as approved.
        self.small_start = (self.size0 * w / 2.0) < self.GLINT_PX * 1.5
        self.hold = fa if self.small_start else 0
        # unified entrances ride the zoom's own stream (see aim); legacy enter keeps the
        # approved aim (fixed point = the globe)
        # ONLY for k >= 1. A globe that grows slower than the zoom (enter, k 0.6) sheds a thin
        # annulus of itself every frame; the approved mechanism clears it as a by-product of
        # translating the globe, and with the translation gone the annuli piled up into a
        # striped glass collar (enterBottom lab), while a radial pull to clear them drew a
        # sunburst in CPU simulation. So k < 1 entrances keep the APPROVED aim + vacate
        # unchanged and only their geometry (entry point, goal, light) is drawn.
        self.ride_flow = bool(entrance) and self.entry is not None and self.k >= 1.0
        self.start_in_frame = bool(entrance) and (0.0 <= entrance["start"][0] <= 1.0
                                                  and 0.0 <= entrance["start"][1] <= 1.0)
        self._zpath = 1.0
        for _z in self.zooms[self.hold:self.n]:
            self._zpath *= _z
        self.introduced = False
        # sphere centre (fractional), the zoom's fixed point
        self.tx, self.ty = tuple(entrance["start"]) if entrance else start_pos
        self.anchor = (0.5, 0.5)          # eases toward centre as it grows (descent lands on
        self.ease = ease                  # the surface, not the limb)
        self.outside = outside            # noise-mask value outside the disc (mask modes)
        self.seed = seed
        self.frame = 0                    # frames rendered through this plate so far
        self.Zacc = 1.0
        self.tex = None                   # (T,T,3) float32 surface texture
        self.void = None                  # PIL void plate, zoomed alongside the frame
        self.rim = None
        self.spin = 0.0                   # cumulative revolution (deg); see render_sphere
        self.spin_rate = spin_rate        # deg per frame
        if entrance and entrance.get("spin") is not None:
            self.spin_rate = float(entrance["spin"])      # drawn: either direction, 1-2 deg
        self.prompts = {"surface": surface_prompt(nxt, style),
                        "void": void_prompt(reg, style),
                        "inside": inside_prompt(nxt, style)}
        self.log = []

    # assets --------------------------------------------------------------------------
    def set_assets(self, tex_img, void_img):
        t = np.asarray(tex_img.convert("RGB"), np.float32) / 255.0
        t = lift_darks(t)
        if t.shape[1] < 2 * t.shape[0] - 2:
            # square top-down texture -> 2:1 equirect by mirroring (seam-free at both ends)
            t = np.concatenate([t, t[:, ::-1]], axis=1)
        self.tex = t
        self.void = void_img.convert("RGB").resize((self.w, self.h), Image.LANCZOS)

    # geometry ------------------------------------------------------------------------
    def aim(self, z, rot_deg, track_mod):
        """Aim for THIS frame's zoom (the Tracker.step formula: hold the sphere centre with a
        slow ease toward the anchor), then advance centre + size through the true transform.
        `track_mod` = engine.track (propagate + crop clamp), so pixels and geometry agree."""
        ax, ay = self.anchor
        j = self.frame
        if self.entry is not None and j < self.n:
            # the globe travels from its start to its settle point, arriving at the bar
            # line. The crop still aims at the globe (the ease formula on its DESIRED
            # position), and whatever the crop carries the old disc to, the composite
            # translates it to the desired spot. A point-start globe only begins its path
            # when it is introduced (after the arrival morph).
            u = (j + 1 - self.hold) / max(1, self.n - self.hold)
            u = min(1.0, max(0.0, u))
            # EVEN PACE with a soft landing (was ease-out 1-(1-u)^2: ~44 px/frame at the
            # start = a big sliver to fill behind the globe every early frame, which the
            # model read as a ghost bubble). smoothstep-blended linear: peak ~1.25x the mean.
            e = 0.5 * u + 0.5 * (u * u * (3.0 - 2.0 * u))
            if self.ride_flow and self.start_in_frame:
                # FLOW PACE: progress follows the cumulative zoom, so a straight path is
                # EXACTLY the zoom's own outward stream from one fixed point behind the start
                # — the globe drifts with the void around it and nothing is ever vacated
                jj = int(min(max(0, j + 1 - self.hold), self.n - self.hold))
                zc = 1.0
                for _z in self.zooms[self.hold:self.hold + jj]:
                    zc *= _z
                e = (zc - 1.0) / max(1e-6, self._zpath - 1.0)
            des = (self.entry[0] + (self.goal[0] - self.entry[0]) * e,
                   self.entry[1] + (self.goal[1] - self.entry[1]) * e)
            if self.bow:
                # a gentle arc: bulge sideways, measured in PIXEL space so it is a true
                # perpendicular in the portrait frame
                dxp = (self.goal[0] - self.entry[0]) * self.w
                dyp = (self.goal[1] - self.entry[1]) * self.h
                ln = math.hypot(dxp, dyp) or 1.0
                off = self.bow * ln * math.sin(math.pi * e)
                des = (des[0] + (-dyp / ln) * off / self.w, des[1] + (dxp / ln) * off / self.h)
            cx = des[0] - (des[0] + self.ease * (ax - des[0]) - 0.5) / z
            cy = des[1] - (des[1] + self.ease * (ay - des[1]) - 0.5) / z
            if self.ride_flow and z > 1.0005:
                # RIDE THE FLOW (unified entrances, after the travelB lab): every void object
                # streams outward from the zoom's fixed point; put that point where the stream
                # itself carries the globe from where it is to where the path wants it,
                # P = (z*old - des) / (z - 1). Globe and void then move TOGETHER — no crescent
                # to vacate, nothing to fill, nothing for the model to repaint as a tail. P is
                # confined to the frame (the crop clamp), so a globe still coming in through
                # an edge moves against the stream and keeps a (smaller) translated remainder.
                Px = min(1.0, max(0.0, (z * self.tx - des[0]) / (z - 1.0)))
                Py = min(1.0, max(0.0, (z * self.ty - des[1]) / (z - 1.0)))
                cx, cy = Px + (0.5 - Px) / z, Py + (0.5 - Py) / z
            cx, cy = min(0.85, max(0.15, cx)), min(0.85, max(0.15, cy))
            px, py = track_mod.propagate(self.tx, self.ty, z, rot_deg, cx, cy,
                                         self.w, self.h)
            self.shift = ((des[0] - px) * self.w, (des[1] - py) * self.h)
            self.tx, self.ty = des
        else:
            cx = self.tx - (self.tx + self.ease * (ax - self.tx) - 0.5) / z
            cy = self.ty - (self.ty + self.ease * (ay - self.ty) - 0.5) / z
            cx, cy = min(0.85, max(0.15, cx)), min(0.85, max(0.15, cy))
            self.tx, self.ty = track_mod.propagate(self.tx, self.ty, z, rot_deg, cx, cy,
                                                   self.w, self.h)
            self.shift = (0.0, 0.0)
        self.Zacc *= z
        self.prev_size = self.size        # the carried disc's diameter (before this growth)
        self.size = self.s_limb * (self.Zacc / self.Zcard) ** self.k
        self.spin += self.spin_rate
        self.frame += 1
        return cx, cy

    def carried_px(self):
        """Where the crop carried the previous disc to (before this frame's translation)."""
        cx, cy = self.centre_px()
        return cx - self.shift[0], cy - self.shift[1]

    def rotate_disc(self, fed):
        """Revolve the fed-back disc interior by this frame's spin increment so the carried
        content and the texture-rendered globe agree (warp.hero_orbit: interior rotates about
        the vertical axis, trailing limb disoccluded -> the identity blend + diffusion fill
        it)."""
        if not self.spin_rate or self.tex is None or not self.introduced:
            return fed
        import warp as _warp
        cx, cy = self.carried_px()
        out, _ = _warp.hero_orbit(fed, cx, cy, self.radius_px(), self.spin_rate, 0.0)
        return out

    def radius_px(self):
        return self.size * self.w / 2.0

    @staticmethod
    def _void_copy(a, vac_m, o, Ro, n, Rn, trail):
        """The vacated crescent filled by a TRANSLATED COPY of live void: one offset T for the
        whole crescent, chosen so every source pixel is in frame and clear of both the old and
        the new disc, preferring directions away from the trail (the trail may carry leftovers).
        Real texture with the right statistics, no smear; returns None if no offset fits."""
        H, W = vac_m.shape
        ys, xs = np.nonzero(vac_m > 0.02)
        if len(ys) == 0:
            return None
        step = math.hypot(n[0] - o[0], n[1] - o[1])
        best = None
        for extra in (0.0, 0.5):
            L = Ro + Rn + step + 40.0 + extra * Rn
            for kdir in range(16):
                ang = 2.0 * math.pi * kdir / 16.0
                ux, uy = math.cos(ang), math.sin(ang)
                sx = np.rint(xs + ux * L).astype(np.int32)
                sy = np.rint(ys + uy * L).astype(np.int32)
                ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
                sxc, syc = np.clip(sx, 0, W - 1), np.clip(sy, 0, H - 1)
                ok &= np.hypot(sxc - o[0], syc - o[1]) > Ro * 1.05
                ok &= np.hypot(sxc - n[0], syc - n[1]) > Rn * 1.06
                score = ok.mean() - 0.2 * max(0.0, ux * trail[0] + uy * trail[1]) - 0.02 * extra
                if best is None or score > best[0]:
                    best = (score, ok, sxc, syc)
        _, ok, sxc, syc = best
        if ok.mean() < 0.85:
            return None
        fill = a.copy()
        samp = a[syc, sxc]
        if (~ok).any():
            samp[~ok] = samp[ok].mean(axis=0)
        fill[ys, xs] = samp
        return fill

    @staticmethod
    def _mover_halo(R):
        """Glint halo sigma (px) for a travelling point — tight, so the vacate can clear it."""
        return min(12.0, max(5.0, 1.2 * R))

    def cap_now(self):
        """Effective denoise allowed INSIDE the protected zone this frame. 0.30 is the ring-free
        regime for a globe; a POINT needs far less (v12 lab: at 0.30 the glint survived one frame
        brilliantly and was re-read as an ordinary glowing dot the next) — 0.12 while the globe
        is under GLINT_PX, easing to 0.30 by twice that radius."""
        if not self.small_start:
            return 0.30
        R = self.radius_px()
        if R < self.GLINT_PX:
            return 0.08 + 0.04 * (R / self.GLINT_PX)
        t = min(1.0, max(0.0, (R - self.GLINT_PX) / self.GLINT_PX))
        return 0.12 + 0.18 * t

    def centre_px(self):
        return self.tx * self.w, self.ty * self.h

    def covered(self):
        """True once the whole frame lies inside the disc (limb gone: we are over the
        surface). Farthest frame corner vs radius."""
        cx, cy = self.centre_px()
        far = max(math.hypot(cx - x, cy - y) for x in (0, self.w) for y in (0, self.h))
        return far <= self.radius_px() * 0.985

    # pixels ----------------------------------------------------------------------------
    def composite(self, fed, first, live=False):
        """Composite the sphere (and the void plate) into the fed-back frame.
        first=True introduces the sphere; later frames blend it at a decaying identity
        weight over the disc content the chain already carried forward, and (pixel mode)
        hold the void toward the void plate.
        live=True (2026-09-18, Phil: "a bit of a fade into where the planet appears"): NO
        void pixel blend at all — the void is held by IP-Adapter conditioning toward the
        void plate in dive.py (the seam lesson: a pixel blend reads as a fading photograph,
        conditioning reads as a live morph) — and the globe FADES IN across the arrival beat
        (intro ramp over `fa` frames) instead of pasting in one frame."""
        if not self.introduced:
            if self.frame <= self.hold:
                return fed                  # not yet: the arrival morph has the frame
            first, self.introduced = True, True
        else:
            first = False
        a = np.asarray(fed.convert("RGB"), np.float32) / 255.0
        H, W = a.shape[:2]
        j = self.frame
        if first:
            w_id, w_shade, w_void = 1.0, 1.0, (0.0 if live else 0.6)
        else:
            # v3: NO per-frame shade multiply — it compounded (0.65^28 at the limb = black,
            # the v2 "dark ball"). The limb/lighting now comes only from the identity blend
            # toward the shaded render, which converges without compounding.
            # identity floor 0.20 -> 0.40 (Phil 2026-10-04: the globes converge to one tan
            # mottled "cloud belt" planet whatever the surface plate shows — the repaint eats
            # the authored texture over the card; hold the plate's features harder)
            w_id = max(0.40, 0.55 - 0.15 * j / max(1, self.n))
            # a SMALL globe is a plate, not carried content: a disc a few pixels wide has
            # nothing in the fed frame worth preserving and the void's full denoise repaints
            # over it (v9 grow lab: the globe never established). Paste it near-opaque while
            # small, relaxing to the usual identity blend by 0.30 x width.
            if self.small_start:
                # v12: HOLD IDENTITY through the growth. v11 relaxed to 0.45 by half the
                # width and the globe drifted from a banded planet to a cratered rock with a
                # dark hollow. Near-opaque while it is a point, then >= 0.6 until 0.6 x
                # width, easing to the usual blend by 0.9.
                if self.size < 0.20:
                    w_id = max(w_id, 1.0 - 0.4 * (self.size / 0.20))
                elif self.size < 0.60:
                    w_id = max(w_id, 0.60)
                elif self.size < 0.90:
                    w_id = max(w_id, 0.60 - 0.30 * (self.size - 0.60) / 0.30)
            elif self.size < 0.30:
                w_id = max(w_id, 1.0 - 0.55 * (self.size / 0.30))
            w_shade = 0.0
            w_void = 0.0 if live else 0.25
        # ENTER: move the carried disc from where the crop left it to where the path wants
        # it, filling the vacated sliver with the void plate (thin per frame; the diffusion
        # heals the rest). The identity blend below then lands on the moved content.
        if not first and (abs(self.shift[0]) > 0.5 or abs(self.shift[1]) > 0.5):
            ox, oy = self.carried_px()
            nx, ny = self.centre_px()
            R_ = self.radius_px()
            # the CARRIED disc has the PREVIOUS diameter scaled by this frame's zoom — never
            # the new one: a patch cut at the new radius pasted a sliver of old surroundings
            # just outside the limb every frame (a stack of arcs trailing the globe)
            R_old = getattr(self, "prev_size", self.size) * self.w / 2.0 * \
                (self.zooms[min(self.frame - 1, len(self.zooms) - 1)] if self.zooms else 1.0)
            R_old = min(R_old, R_)
            # what must be cleared behind the globe: the old disc + thin rim, and — while a
            # moving globe still wears its glint — the glint's halo too (a bright soft dot
            # left behind every frame = a string of stars trailing the traveller)
            R_clear = R_old * 1.12
            if self.small_start and R_old < self.GLINT_PX:
                R_clear = max(R_clear, R_old + 2.0 * self._mover_halo(R_old))
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            dist_o = np.sqrt((xx - ox) ** 2 + (yy - oy) ** 2)
            dist_n = np.sqrt((xx - nx) ** 2 + (yy - ny) ** 2)
            src_m = np.clip((R_old - dist_o) / 3.0, 0, 1)
            # VACATE ONLY THE CRESCENT the globe actually left: the old disc (+ its thin rim)
            # MINUS what the new disc covers. The first cut cleared a disc 1.34R wide back to
            # the dark void plate every frame, which overwrote the live star field around
            # the planet and carved a black moat round it (Phil's "border", 2026-09-18). The
            # rim glow is now thin enough that the crescent clears it — no stripe wake.
            # clear a little PAST the old limb (1.12 R_old): with a live-void fill a wider
            # clear cannot carve a moat any more, and it takes the old limb's edge line with
            # it (faint arcs trailed the globe when the clear stopped at the limb)
            vac_m = np.clip((R_clear - dist_o) / 14.0, 0, 1) \
                * (1.0 - np.clip((R_ * 1.00 - dist_n) / 4.0, 0, 1))
            patch = a.copy()
            dx, dy = int(round(nx - ox)), int(round(ny - oy))
            moved = np.zeros_like(a)
            mm = np.zeros((H, W), np.float32)
            ys, ye = max(0, dy), min(H, H + dy)
            xs, xe = max(0, dx), min(W, W + dx)
            if ye > ys and xe > xs:
                moved[ys:ye, xs:xe] = patch[ys - dy:ye - dy, xs - dx:xe - dx]
                mm[ys:ye, xs:xe] = src_m[ys - dy:ye - dy, xs - dx:xe - dx]
            # FILL THE VACATED CRESCENT WITH THE LIVE VOID, never the void plate (Phil
            # 2026-09-18, sargasso: a dark ribbed column trailing the rising globe — the dark
            # plate slivers stacked up frame after frame in a bright ray field, and
            # DepthAnything read them as a solid stalk). Mirror the fed frame across the OLD
            # limb: a crescent pixel at distance d inside the old edge takes the void pixel
            # the same distance OUTSIDE it, along the same radius (edge-clamped at the frame
            # border, where an entering globe's trailing side lies). Continuous at the limb,
            # made of the same stuff as its surroundings; the void's full denoise does the rest.
            if vac_m.max() > 0:
                # DIRECTIONAL fill (v3 of this step): pull the void in ALONG THE MOTION AXIS —
                # each crescent pixel takes the void pixel found by walking from it, in the
                # trailing direction, to just past the old disc's edge. A mirror across the
                # limb left a circular, symmetric echo that the model painted as a glassy
                # bubble under the rising globe (sargasso v2 f31-43); a straight pull has no
                # circular symmetry and is continuous with the void behind the globe.
                _mv = math.hypot(nx - ox, ny - oy)
                _tx, _ty = ((ox - nx) / _mv, (oy - ny) / _mv) if _mv > 1e-3 else (0.0, 1.0)
                _px, _py = xx - ox, yy - oy
                _b = _px * _tx + _py * _ty
                _disc = np.maximum(_b * _b - (_px * _px + _py * _py) + R_clear ** 2, 0.0)
                _ell = -_b + np.sqrt(_disc) + 3.0          # distance to the old edge along t
                _sx = np.clip(np.rint(xx + _tx * _ell), 0, W - 1).astype(np.int32)
                _sy = np.clip(np.rint(yy + _ty * _ell), 0, H - 1).astype(np.int32)
                fill = patch[_sy, _sx]
                # a mirrored sample that was clamped at the frame border can land back INSIDE
                # a disc (an entering globe still overlaps the edge it came through): that
                # replicated the globe's own edge row into a stem under it. Those samples take
                # the mean of the true void instead; the void's denoise textures it.
                _bad = (dist_o[_sy, _sx] < R_clear * 0.98) | (dist_n[_sy, _sx] < R_ * 1.04)
                _voidpx = (dist_o > R_clear * 1.03) & (dist_n > R_ * 1.10)
                if _bad.any() and _voidpx.any():
                    fill = np.where(_bad[..., None], patch[_voidpx].mean(axis=0)[None, None, :],
                                    fill)
                if self.ride_flow:
                    # UNIFIED ENTRANCES: a small fast globe leaves a crescent a quarter of its
                    # own radius thick, and the directional pull smears the pixels right behind
                    # the old limb across it — which the model repaints as MORE GLOBE (travelB
                    # lab: a barrel-shaped body trailing the disc, then a glassy ghost sphere;
                    # and once a tail exists the pull copies the tail, so it feeds itself).
                    # Fill with REAL live void copied from a clean region instead; the pull
                    # stays as the fallback when the globe is too big for a clean region to fit.
                    _vc = self._void_copy(patch, vac_m, (ox, oy), R_clear, (nx, ny), R_,
                                          (_tx, _ty))
                    if _vc is not None:
                        fill = _vc
                a = a * (1 - vac_m[..., None]) + fill * vac_m[..., None]
            a = a * (1 - mm[..., None]) + moved * mm[..., None]        # land it at the new
        cx, cy = self.centre_px()
        R = self.radius_px()
        if self.tex is None:
            return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
        # a small globe's unlit side was painted as a HOLLOW and carried forward (grow v13:
        # "a cratered rock with a dark bite"). Point-start globes get a brighter night side
        # while small, easing to the normal shading by 0.8 x width.
        amb = 0.38
        if self.small_start:
            amb = 0.60 - 0.22 * min(1.0, max(0.0, (self.size - 0.35) / 0.45))
        rgb, alpha, shade = render_sphere(self.tex, 2 * R, light=self.light, rim_rgb=self.rim,
                                          spin_deg=self.spin, ambient=amb)
        if self.rim is None:
            self.rim = rgb[alpha > 0.5].mean(axis=0) if (alpha > 0.5).any() else None
        D = rgb.shape[0]
        x0, y0 = int(round(cx - D / 2)), int(round(cy - D / 2))
        # clip the sphere canvas to the frame
        sx0, sy0 = max(0, -x0), max(0, -y0)
        sx1, sy1 = min(D, W - x0), min(D, H - y0)
        # full-frame disc coverage (0 outside the globe) — the void hold must never touch
        # the disc (v3 fix: blending the near-black void plate over the WHOLE frame pulled
        # the disc toward black every frame, the other half of the v2 "dark ball")
        cover = np.zeros((H, W), np.float32)
        if sx1 > sx0 and sy1 > sy0:
            cover[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] = alpha[sy0:sy1, sx0:sx1]
        if self.void is not None and w_void > 0:
            v = np.asarray(self.void, np.float32) / 255.0
            wv = (w_void * (1.0 - cover))[..., None]
            a = a * (1 - wv) + v * wv
        if sx1 <= sx0 or sy1 <= sy0:
            return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
        fx0, fy0 = x0 + sx0, y0 + sy0
        fx1, fy1 = x0 + sx1, y0 + sy1
        sub = a[fy0:fy1, fx0:fx1]
        srgb = rgb[sy0:sy1, sx0:sx1]
        sal = alpha[sy0:sy1, sx0:sx1][..., None]
        ssh = shade[sy0:sy1, sx0:sx1][..., None]
        # identity blend of the rendered sphere over the carried-forward disc content
        blended = sub * (1 - sal * w_id) + srgb * (sal * w_id)
        # limb/lighting dome: only on the introduction frame (see w_shade above)
        if w_shade:
            blended = blended * ((1 - w_shade) + w_shade * ssh)
        a[fy0:fy1, fx0:fx1] = blended
        if self.small_start and R < self.GLINT_PX:
            # v12: a real approach starts as a POINT OF LIGHT. Under ~40 px the globe was
            # simply lost in a busy star field (v11: nothing visible for its first nine
            # frames, then "a small planet appears"). Add a star-like glint at its position
            # whose strength fades out as the disc becomes big enough to read by itself.
            g = (1.0 - R / self.GLINT_PX) ** 0.5
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            d2 = (xx - cx) ** 2 + (yy - cy) ** 2
            # v15: a FLAT-TOPPED core. v14's 1.7 px gaussian was right on the composite and
            # dim in the delivered frame — one VAE round trip (8x latent) smears a point that
            # narrow to ~40% of its peak, and the scene's own stars (big, saturated, spiked)
            # outshone it. 1.8x a 2.6 px gaussian clipped at 1 keeps a ~3 px saturated disc.
            core = np.maximum(np.minimum(1.0, 1.8 * np.exp(-d2 / (2.0 * 2.6 ** 2))),
                              0.75 * np.exp(-d2 / (2.0 * max(3.4, 1.0 * R) ** 2)))
            if self.entry is not None:
                # a TRAVELLING point: tight halo, no spikes — everything it wears must fit
                # inside what the vacate step clears behind it each frame
                halo = np.exp(-d2 / (2.0 * self._mover_halo(R) ** 2))
                spike = 0.0
            else:
                halo = np.exp(-d2 / (2.0 * max(11.0, 3.2 * R) ** 2))
                spike = (np.exp(-((xx - cx) ** 2) / 1.4) + np.exp(-((yy - cy) ** 2) / 1.4)) \
                    * np.exp(-d2 / (2.0 * max(22.0, 6.0 * R) ** 2))
            tint = np.clip((self.rim if self.rim is not None else np.array([0.85, 0.9, 1.0])) * 0.3
                           + 0.7, 0, 1).astype(np.float32)
            light = np.clip((1.0 * core + 0.34 * halo + 0.42 * spike) * g, 0.0, 1.0)
            # MAX-composite, never add: every frame feeds the next, so additive light
            # accumulated into a white bloom that swallowed the scene within ten frames
            # (caught in CPU simulation). max() is idempotent — re-applying it to a frame
            # that already carries the glint changes nothing.
            a = np.maximum(a, light[..., None] * tint[None, None, :])
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))

    def disc_mask(self, feather_px=6, min_r_px=0.0):
        """0..1 disc (1 inside), feathered at the limb — the regional-prompt mask.
        min_r_px (v12): the masks that PROTECT the globe (noise cap, IPA exclusion) never
        shrink below this radius — a disc a few pixels wide protects nothing, and the void's
        full denoise repainted the point-sized globe every frame."""
        if not self.introduced:
            return np.zeros((self.h, self.w), np.float32)      # no globe yet, nothing to mask
        cx, cy = self.centre_px()
        R = max(self.radius_px(), float(min_r_px))
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        m = np.clip((R + feather_px / 2 - d) / max(1.0, feather_px), 0.0, 1.0)
        return m.astype(np.float32)

    def noise_mask(self, feather_px=6, inside=1.0, outside=None):
        """Graded latent noise mask: `inside` in the disc, `outside` beyond it (with
        DifferentialDiffusion the value = the fraction of the denoise steps that region
        gets, i.e. per-pixel denoise strength). Live mode caps the DISC (inside 0.8 ≈ arm
        B's 0.32 at travel denoise, the ring-free regime) and leaves the void at 1.0."""
        if outside is None:
            outside = self.outside
        m = self.disc_mask(feather_px, min_r_px=self.MIN_CAP_PX)
        return (outside + (inside - outside) * m).astype(np.float32)

    def outside_mask(self, feather_px=6):
        """1 outside the disc, 0 inside — the IP-Adapter attention mask for the void hold."""
        return (1.0 - self.disc_mask(feather_px, min_r_px=self.MIN_CAP_PX)).astype(np.float32)

    @staticmethod
    def mask_image(m):
        return Image.fromarray((np.clip(m, 0, 1) * 255).astype("uint8")).convert("RGB")

    def row(self, i, **kw):
        r = {"i": i, "j": self.frame, "size": round(self.size, 4),
             "tx": round(self.tx, 4), "ty": round(self.ty, 4),
             "covered": self.covered(), "card": "planet" if self.frame <= self.n else "next",
             "spin": round(self.spin, 1),
             **kw}
        self.log.append(r)
        return r
