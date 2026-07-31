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

    def __init__(self, ap, w, h, rot=0.15, cadence=4, ease=0.3, gain=0.5,
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
        self.frame = 0                    # frames into this run
        self.need_repick = True           # begin() pending (fresh run, or track escaped)
        self.last_box = None              # last raw detection (for the debug log)

    # -- emergence -------------------------------------------------------------
    def begin(self, img, seed=0):
        """Commit to a prominent emergence point (or re-commit after losing the object)."""
        self.tx, self.ty = points.pick_point(img, seed=seed)
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
        if b is not None and max(b["w"], b["h"]) > 0.8:
            b = None
        self.last_box = b
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
            self.phase, self.pending = "object", None
            return ev
        # far from the heading — a REDIRECT needs two consecutive agreeing observations
        if self.pending and math.hypot(bx - self.pending["x"], by - self.pending["y"]) <= self.agree:
            self.tx, self.ty, self.size = bx, by, bsize
            ev = "lock-redirect" if self.phase == "point" else "switch"
            self.phase, self.pending = "object", None
            return ev
        self.pending = {"x": bx, "y": by, "size": bsize, "misses": 0}
        return "candidate"

    # -- aim + geometry advance ------------------------------------------------
    def step(self, z):
        """Aim for THIS frame (ease the tracked point toward center), then advance the track
        (and any pending candidate) through the TRUE transform. Returns (cx, cy) for
        zoom_transform. Big offsets automatically get max-authority steering: the ease may ask
        for more recentering than the crop can give, the crop clamp caps it, and propagation
        follows the CAP — so the track stays true and edge objects are steered back before
        they escape (any point inside the frame converges under max authority)."""
        cx = self.tx - (self.tx - 0.5) * (1 - self.ease) / z
        cy = self.ty - (self.ty - 0.5) * (1 - self.ease) / z
        cx, cy = min(0.85, max(0.15, cx)), min(0.85, max(0.15, cy))
        self.tx, self.ty = propagate(self.tx, self.ty, z, self.rot, cx, cy, self.w, self.h)
        self.size *= z
        if self.pending:
            px, py = propagate(self.pending["x"], self.pending["y"], z, self.rot,
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
               "size": round(self.size, 4)}
        if self.last_box:
            row["det"] = [round(self.last_box["cx"], 4), round(self.last_box["cy"], 4),
                          round(self.last_box["w"], 4), round(self.last_box["h"], 4)]
        if self.pending:
            row["pending"] = [round(self.pending["x"], 4), round(self.pending["y"], 4)]
        return row
