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
PLANET_TARGET = re.compile(r"\b(planet|world|moon)\b", re.I)


def is_plate_card(reg, nxt):
    tp = reg.get("target_phrase") or reg.get("target") or ""
    if not PLANET_TARGET.search(tp):
        return False
    if reg.get("kind") == "seam":
        return False
    e0, e1 = reg.get("exp"), nxt.get("exp")
    return (isinstance(e0, (int, float)) and isinstance(e1, (int, float))
            and e0 >= 8.0 and 4.5 <= e1 <= 9.5)


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


def render_sphere(tex, diam_px, light=(-0.45, -0.55, 0.70), rim_rgb=None, spin_deg=0.0):
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
    shade = (0.38 + 0.62 * ndl) * (0.72 + 0.28 * np.sqrt(z))
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


# ── per-card state ─────────────────────────────────────────────────────────────────
class Plate:
    """One plate = one planet card. Frames [s, e) render through it (arrival included: the
    sphere is introduced during the arrival morph and grows through travel + plunge)."""

    def __init__(self, card_idx, s, e, fa, reg, nxt, style, w, h, zooms, seed,
                 n_card=None, start_pos=(0.62, 0.40), s_limb=1.15, ease=0.06, outside=0.27,
                 spin_rate=1.5, intro="grow", edge="right"):
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
        self.k = {"grow": 1.5, "enter": 0.6, "plain": 1.0}.get(intro, 1.0)
        self.size0 = s_limb * (1.0 / Z) ** self.k    # diameter, fraction of frame WIDTH
        self.size = self.size0
        self.edge = edge
        self.shift = (0.0, 0.0)           # px the carried disc must move this frame (enter)
        self.entry = None
        if intro == "enter":
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
        self.tx, self.ty = start_pos      # sphere centre (fractional), the zoom's fixed point
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
        self.prompts = {"surface": surface_prompt(nxt, style),
                        "void": void_prompt(reg, style),
                        "inside": inside_prompt(nxt, style)}
        self.log = []

    # assets --------------------------------------------------------------------------
    def set_assets(self, tex_img, void_img):
        t = np.asarray(tex_img.convert("RGB"), np.float32) / 255.0
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
        if self.intro == "enter" and j < self.n:
            # the globe slides in from beyond the edge: an ease-out path from the entry
            # point to the goal, arriving at the bar line. The crop still aims at the
            # globe (the ease formula on its DESIRED position), and whatever the crop
            # carries the old disc to, the composite translates it to the desired spot.
            u = (j + 1) / max(1, self.n)
            e = 1.0 - (1.0 - u) ** 2
            des = (self.entry[0] + (self.goal[0] - self.entry[0]) * e,
                   self.entry[1] + (self.goal[1] - self.entry[1]) * e)
            cx = des[0] - (des[0] + self.ease * (ax - des[0]) - 0.5) / z
            cy = des[1] - (des[1] + self.ease * (ay - des[1]) - 0.5) / z
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
        if not self.spin_rate or self.tex is None:
            return fed
        import warp as _warp
        cx, cy = self.carried_px()
        out, _ = _warp.hero_orbit(fed, cx, cy, self.radius_px(), self.spin_rate, 0.0)
        return out

    def radius_px(self):
        return self.size * self.w / 2.0

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
        a = np.asarray(fed.convert("RGB"), np.float32) / 255.0
        H, W = a.shape[:2]
        j = self.frame
        if first:
            w_id, w_shade, w_void = 1.0, 1.0, (0.0 if live else 0.6)
        else:
            # v3: NO per-frame shade multiply — it compounded (0.65^28 at the limb = black,
            # the v2 "dark ball"). The limb/lighting now comes only from the identity blend
            # toward the shaded render, which converges without compounding.
            w_id = max(0.20, 0.45 - 0.25 * j / max(1, self.n))
            # a SMALL globe is a plate, not carried content: a disc a few pixels wide has
            # nothing in the fed frame worth preserving and the void's full denoise repaints
            # over it (v9 grow lab: the globe never established). Paste it near-opaque while
            # small, relaxing to the usual identity blend by 0.30 x width.
            _hold = 0.50 if self.intro == "grow" else 0.30   # v10: grow's globe was re-read
            if self.size < _hold:                            # as a lumpy ball while relaxing
                w_id = max(w_id, 1.0 - 0.55 * (self.size / _hold))
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
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            dist_o = np.sqrt((xx - ox) ** 2 + (yy - oy) ** 2)
            dist_n = np.sqrt((xx - nx) ** 2 + (yy - ny) ** 2)
            src_m = np.clip((R_old - dist_o) / 3.0, 0, 1)
            # VACATE ONLY THE CRESCENT the globe actually left: the old disc (+ its thin rim)
            # MINUS what the new disc covers. The first cut cleared a disc 1.34R wide back to
            # the dark void plate every frame, which overwrote the live star field around
            # the planet and carved a black moat round it (Phil's "border", 2026-09-18). The
            # rim glow is now thin enough that the crescent clears it — no stripe wake.
            vac_m = np.clip((R_old * 1.05 - dist_o) / 4.0, 0, 1) \
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
            if self.void is not None:
                v = np.asarray(self.void, np.float32) / 255.0
                a = a * (1 - vac_m[..., None]) + v * vac_m[..., None]   # vacate disc + halo
            a = a * (1 - mm[..., None]) + moved * mm[..., None]        # land it at the new
        cx, cy = self.centre_px()
        R = self.radius_px()
        if self.tex is None:
            return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
        rgb, alpha, shade = render_sphere(self.tex, 2 * R, rim_rgb=self.rim, spin_deg=self.spin)
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
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))

    def disc_mask(self, feather_px=6):
        """0..1 disc (1 inside), feathered at the limb — the regional-prompt mask."""
        cx, cy = self.centre_px()
        R = self.radius_px()
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
        m = self.disc_mask(feather_px)
        return (outside + (inside - outside) * m).astype(np.float32)

    def outside_mask(self, feather_px=6):
        """1 outside the disc, 0 inside — the IP-Adapter attention mask for the void hold."""
        return (1.0 - self.disc_mask(feather_px)).astype(np.float32)

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
