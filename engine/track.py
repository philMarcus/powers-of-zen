#!/usr/bin/env python3
"""TRACKER v3 — unified two-stage object tracking for the approach loop (PLAN "TRACKER v3").

The engine zooms by cropping toward an aim point (dive.zoom_transform). During an approach run
this module OWNS the aim: it commits to an emergence POINT before the target is detectable
(points.pick_point), tries semantic detection at a low cadence (detect.locate — Florence is too
slow and too flaky for every frame), and after the first confident lock FOLLOWS the object by
propagating its position through the KNOWN zoom geometry between detections. Detections only
gently correct the propagated track; a missed or garbage detection can never yank the camera
(v5's lurch), and the track is glued to the OBJECT, not a screen position (v6's drift).

WHY exact propagation matters (the v6 bug): v6 advanced its tracked point with the aim it ASKED
for, but zoom_transform silently clamps the crop window to the frame — at z=1.045 the crop can
only recenter by ±2.2% of the frame per frame, while the ease formula assumes up to ±35%. So the
assumed point marched to center on paper while the real object stayed put (or escaped). The
[0.15,0.85] aim clamp never binds; the CROP clamp always does. Rotation was ignored too.
`crop_center`/`propagate` here mirror the real transform (rotation + crop clamp) exactly, and
dive.zoom_transform derives its crop from the same helper so the two can never drift apart.

Camera-smoothness comes for free: real recenter speed is bounded by the crop authority
(1-1/z)/2 per frame no matter what the track does — a redirect just means a few frames of
max-authority steering, never a visible jump. The gating below fixes the WANDER (v5): a
detection near the current heading confirms it (lock/correct); a detection far from the heading
is only believed after TWO consecutive observations agree (garbage boxes are sporadic and
scattered; a real object is found twice in the same place).
"""
import math

import points


def crop_center(z, cx, cy):
    """The EFFECTIVE crop center after zoom_transform clamps the crop window to the frame.
    The window is 1/z of the frame, so its center can sit at most (1-1/z)/2 from 0.5."""
    half = (1.0 - 1.0 / z) / 2.0 if z > 1.0 else 0.0
    return (min(0.5 + half, max(0.5 - half, cx)),
            min(0.5 + half, max(0.5 - half, cy)))


def rotate_pt(fx, fy, deg, w, h):
    """Where a fractional content point lands after PIL img.rotate(deg, expand=False) about the
    image center. Rotation is in PIXEL space (aspect matters), y-down; PIL rotates content
    counterclockwise on screen for positive deg."""
    if not deg:
        return fx, fy
    a = math.radians(deg)
    px, py = fx * w - w / 2.0, fy * h - h / 2.0
    qx = px * math.cos(a) + py * math.sin(a)
    qy = -px * math.sin(a) + py * math.cos(a)
    return (qx + w / 2.0) / w, (qy + h / 2.0) / h


def propagate(fx, fy, z, rot_deg, cx, cy, w, h):
    """Map a fractional content point through zoom_transform(img, z, rot_deg, cx, cy) EXACTLY:
    rotate about center, then crop the (clamped) 1/z window toward (cx,cy) and rescale."""
    fx, fy = rotate_pt(fx, fy, rot_deg, w, h)
    ecx, ecy = crop_center(z, cx, cy)
    return 0.5 + (fx - ecx) * z, 0.5 + (fy - ecy) * z


class Tracker:
    """One Tracker per approach run (one card's dive toward its target_phrase).

    Per frame, in order:  maybe_observe(img)  ->  cx, cy = step(z)  ->  zoom_transform(...)
    `step` returns the aim for THIS frame's zoom and advances the internal state through the
    true geometry. Phases: 'point' (committed emergence point, detector still searching) ->
    'object' (locked; detections gently correct the propagated box)."""

    def __init__(self, ap, w, h, rot=0.15, cadence=4, ease=0.03, gain=0.5,
                 confirm=0.15, agree=0.18, size_stop=0.55,
                 model="microsoft/Florence-2-large-ft"):
        self.ap = ap                      # the grammar's approach dict (identity marks the run)
        self.phrase = ap["phrase"]
        self.pick = ap.get("pick", "salient")
        self.w, self.h, self.rot = w, h, rot
        self.cadence, self.ease, self.gain = cadence, ease, gain
        self.confirm, self.agree, self.size_stop = confirm, agree, size_stop
        self.model = model
        self.phase = "point"
        self.tx = self.ty = 0.5           # tracked target position (fractional, current frame)
        self.size = 0.0                   # locked box max(w,h), propagated (grows by z/frame)
        self.pending = None               # unconfirmed redirect candidate {x,y,size,misses}
        self.anchor = (0.5, 0.5)          # composition anchor, FROZEN per run (see begin/lock)
        self.redirect_until = 10          # no heading swings after this frame of the run
        self.frame = 0                    # frames into this run
        self.need_repick = True           # begin() pending (fresh run, or track escaped)
        self.last_box = None              # last raw detection (for the debug log)
        self.last_obs_frame = -1          # run-frame of that detection (log only fresh ones)

    # -- emergence -------------------------------------------------------------
    def begin(self, img, seed=0, run_idx=0):
        """Commit to a prominent emergence point (or re-commit after losing the object), and
        FREEZE this run's composition anchor to the nearest rule-of-thirds intersection.
        `run_idx` rotates the preferred third so consecutive scales compose to different
        corners — the heading shifts at each card boundary (on the beat), never mid-bar."""
        self.tx, self.ty = points.pick_point(
            img, seed=seed, prefer=points.THIRDS_ORDER[run_idx % len(points.THIRDS_ORDER)])
        self.anchor = points.nearest_third(self.tx, self.ty)
        self.phase, self.size, self.pending = "point", 0.0, None
        self.need_repick = False

    # -- detection beats -------------------------------------------------------
    def maybe_observe(self, img):
        """Run detect.locate on detection beats; gate the result into the track. Returns an
        event string for logging, or None on non-beat frames. Never raises (a Florence hiccup
        must not kill a render) and never moves the track more than the gating allows."""
        if self.frame % self.cadence:
            return None
        if self.phase == "object" and self.size >= self.size_stop:
            return "filled"               # object already fills the frame; nothing to learn
        try:
            import detect                 # lazy: detect imports dive (loaded by now)
            b = detect.locate(img, self.phrase, pick=self.pick, model=self.model)
        except Exception as e:
            self.last_box = None
            return f"detect-error:{type(e).__name__}"
        # degenerate-box filter: locate()'s _clean only rejects full-span in BOTH dims, but the
        # v4 sweep showed near-full-WIDTH boxes (1.00x0.62, centered) that would agree with each
        # other and confirm a false center lock. An emergence-phase target is never that big.
        # Also (v6 lesson, the ONE bad lock of the render): a 5:1 sliver in the outer frame
        # margin got two agreeing hits and redirected the camera cornerward. A box we'd DIVE
        # INTO is roughly object-shaped (aspect <= 3.5) and steerable-to (center not jammed in
        # the outer 10% band) — anything else is Florence grounding noise.
        if b is not None:
            ar = b["w"] / b["h"] if b["h"] else 99.0
            edge = min(b["cx"], 1 - b["cx"], b["cy"], 1 - b["cy"])
            if max(b["w"], b["h"]) > 0.8 or not (1 / 3.5 <= ar <= 3.5) or edge < 0.10:
                b = None
        self.last_box, self.last_obs_frame = b, self.frame
        if b is None:
            if self.pending:
                self.pending["misses"] += 1
                if self.pending["misses"] > 2:
                    self.pending = None   # stale candidate — expire it
            return "miss"
        bx, by, bsize = b["cx"], b["cy"], max(b["w"], b["h"])
        d = math.hypot(bx - self.tx, by - self.ty)
        if d <= max(self.confirm, 0.5 * self.size):
            # confirms the current heading: first lock snaps, later hits correct GENTLY
            g = 1.0 if self.phase == "point" else self.gain
            self.tx += g * (bx - self.tx)
            self.ty += g * (by - self.ty)
            self.size = bsize if self.phase == "point" else self.size + g * (bsize - self.size)
            ev = "lock" if self.phase == "point" else "correct"
            if ev == "lock":                  # first lock re-anchors to the object's own third
                self.anchor = points.nearest_third(self.tx, self.ty)
            self.phase, self.pending = "object", None
            return ev
        # far from the heading — a REDIRECT needs two consecutive agreeing observations, AND
        # must land in the first half of the run: a redirect swings the heading, and an abrupt
        # direction change that doesn't fall on a beat breaks the rhythm (Phil 2026-07-31).
        # Late in a run we keep the committed heading and let the arrival morph do the work.
        if (self.pending and math.hypot(bx - self.pending["x"], by - self.pending["y"]) <= self.agree
                and self.frame <= self.redirect_until):
            self.tx, self.ty, self.size = bx, by, bsize
            self.anchor = points.nearest_third(bx, by)
            ev = "lock-redirect" if self.phase == "point" else "switch"
            self.phase, self.pending = "object", None
            return ev
        self.pending = {"x": bx, "y": by, "size": bsize, "misses": 0}
        return "candidate"

    # -- aim + geometry advance ------------------------------------------------
    def step(self, z, rot=None):
        """Aim for THIS frame, then advance the track (and any pending candidate) through the
        TRUE transform. Returns (cx, cy) for zoom_transform. `rot` overrides the standing
        per-frame rotation for THIS step (camera-vocabulary roll varies it per frame; the
        propagation must use whatever zoom_transform actually applies).

        COMPOSITION, not centering (Phil 2026-07-31). The old form eased the object toward
        CENTER, and because the offset is multiplied by (1-ease) EVERY frame it compounds:
        even ease=0.05 removed 76% of the off-center composition over a 28-frame card, so
        every scale slid into a dead-center zoom. Now we ease toward this run's FROZEN
        rule-of-thirds anchor at a slow rate — the object holds an intentional off-center
        position, the heading stays constant for the whole bar, and the only direction change
        lands at the card boundary (i.e. on the beat), which is what engine-1 felt like.
        ease=0 would hold position exactly; the small default just settles the composition.

        Solving t_new = t + ease*(anchor - t) against t_new = 0.5 + (t - c)*z gives c below.
        Feasibility: at ease=0 the required |c-0.5| is |t-0.5|(1-1/z) <= (1-1/z)/2, i.e. always
        within crop authority for any on-screen point, so the clamp never fights the hold."""
        r = self.rot if rot is None else rot
        ax, ay = self.anchor
        cx = self.tx - (self.tx + self.ease * (ax - self.tx) - 0.5) / z
        cy = self.ty - (self.ty + self.ease * (ay - self.ty) - 0.5) / z
        cx, cy = min(0.85, max(0.15, cx)), min(0.85, max(0.15, cy))
        self.tx, self.ty = propagate(self.tx, self.ty, z, r, cx, cy, self.w, self.h)
        self.size *= z
        if self.pending:
            px, py = propagate(self.pending["x"], self.pending["y"], z, r,
                               cx, cy, self.w, self.h)
            if -0.05 <= px <= 1.05 and -0.05 <= py <= 1.05:
                self.pending["x"], self.pending["y"] = px, py
                self.pending["size"] *= z
            else:
                self.pending = None
        # diffusion can re-seat the object; if a correction ever walks the track off-frame the
        # object is unrecoverable (zoom only crops inward) — fall back to a fresh emergence pick
        if not (-0.08 <= self.tx <= 1.08 and -0.08 <= self.ty <= 1.08):
            self.need_repick = True
        self.frame += 1
        return cx, cy

    def log_row(self):
        """State snapshot for build/track.jsonl (rounded; the overlay tool draws from this)."""
        row = {"run_frame": self.frame, "phase": self.phase,
               "track": [round(self.tx, 4), round(self.ty, 4)],
               "anchor": [round(self.anchor[0], 3), round(self.anchor[1], 3)],
               "size": round(self.size, 4)}
        if self.last_box and self.last_obs_frame == self.frame:   # fresh this frame, not stale
            row["det"] = [round(self.last_box["cx"], 4), round(self.last_box["cy"], 4),
                          round(self.last_box["w"], 4), round(self.last_box["h"], 4)]
        if self.pending:
            row["pending"] = [round(self.pending["x"], 4), round(self.pending["y"], 4)]
        return row
