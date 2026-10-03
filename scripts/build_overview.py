#!/usr/bin/env python3
"""Build dashboard/overview.html — the "How it works" tab (Phil 2026-09-19: "a big visual,
graphically organized overview of everything in the project ... nice for humans to look at").

One self-contained page (inline CSS + hand-authored inline SVG + a few base64 thumbnails of REAL
frames), rendered by the dashboard with st.components.v1.html. Static on purpose for now: run
this script again to refresh the counts and the frame strip.

    python3 scripts/build_overview.py

Figures follow one rule each: depict the mechanism, label the arrows, one claim per figure.
Curves in "inside one card" are computed from the engine's real formulas (grammar zoom weights,
dive's arrival boost + anacrusis), not drawn by eye.
"""
import base64
import io
import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

# PREVIEW build. The published copy is /index.html at the repo root (powersofzen.com landing,
# promoted 2026-10-02 and hand-polished there — first-person voice, corrected stats). A rebuild
# never overwrites it: diff this preview against index.html and promote by hand.
OUT = ROOT / "dashboard" / "overview.html"


# ── small SVG helpers ─────────────────────────────────────────────────────────────────
def box(x, y, w, h, title, sub="", cls="", sub2=""):
    t = [f'<g class="node {cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>']
    cy = y + h / 2
    if sub2:
        t.append(f'<text x="{x + w / 2}" y="{cy - 12}" class="t">{title}</text>')
        t.append(f'<text x="{x + w / 2}" y="{cy + 5}" class="s">{sub}</text>')
        t.append(f'<text x="{x + w / 2}" y="{cy + 20}" class="s">{sub2}</text>')
    elif sub:
        t.append(f'<text x="{x + w / 2}" y="{cy - 3}" class="t">{title}</text>')
        t.append(f'<text x="{x + w / 2}" y="{cy + 14}" class="s">{sub}</text>')
    else:
        t.append(f'<text x="{x + w / 2}" y="{cy + 5}" class="t">{title}</text>')
    t.append("</g>")
    return "".join(t)


def arrow(x1, y1, x2, y2, label="", lx=None, ly=None, cls="", anchor="middle"):
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="edge {cls}" marker-end="url(#ah)"/>'
    if label:
        lx = (x1 + x2) / 2 if lx is None else lx
        ly = (y1 + y2) / 2 - 7 if ly is None else ly
        lines = label.split("|")
        for k, ln in enumerate(lines):
            yy = ly - 15 * (len(lines) - 1 - k)
            s += f'<text x="{lx}" y="{yy}" class="el" text-anchor="{anchor}">{ln}</text>'
    return s


DEFS = ('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'fill="currentColor"/></marker></defs>')


def svg(w, h, body, label):
    # the stylesheet centres labels by default; a CSS rule beats a presentation attribute, so
    # per-label alignment has to travel as an inline style
    import re
    body = re.sub(r' text-anchor="(start|end|middle)"', r' style="text-anchor:\1"', body)
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}" '
            f'xmlns="http://www.w3.org/2000/svg">{DEFS}{body}</svg>')


# ── FIGURE A: the daily loop ──────────────────────────────────────────────────────────
def fig_pipeline():
    W, H = 1120, 330
    bw, bh, gap = 196, 66, 110
    xs = [10 + i * (bw + gap) for i in range(4)]
    y1, y2 = 30, 218
    b = []
    top = [("Refill", "00:00 · agents compose journeys", ""),
           ("Render queue", "outbox/journeys.json", ""),
           ("Night batch", "01:30 · dive renderer", ""),
           ("Video Review", "you: pick cut, mark the start", "human")]
    bot = [("Music", "you: audition 5, choose 1", "human"),
           ("Production queue", "ready to post", ""),
           ("Poster", "YouTube + Instagram", ""),
           ("Stats + analysis", "views, likes, saves, qscore", "")]
    for (t, s_, c), x in zip(top, xs):
        b.append(box(x, y1, bw, bh, t, s_, c))
    for (t, s_, c), x in zip(bot, reversed(xs)):
        b.append(box(x, y2, bw, bh, t, s_, c))
    lab_top = ["audited|journeys", "queue order,|time budget", "video, captions,|5 music tracks"]
    for i, lab in enumerate(lab_top):
        b.append(arrow(xs[i] + bw + 4, y1 + bh / 2, xs[i + 1] - 4, y1 + bh / 2, lab,
                       ly=y1 + bh / 2 - 9))
    # down the right side
    xr = xs[3] + bw / 2
    b.append(arrow(xr, y1 + bh + 4, xr, y2 - 4, "approve", lx=xr - 12, ly=(y1 + bh + y2) / 2 + 4,
                   anchor="end"))
    lab_bot = ["chosen|track", "every 19 h,|never 01–07", "live|URLs"]
    for i, lab in enumerate(lab_bot):
        xa = xs[3 - i] - 4
        xb = xs[2 - i] + bw + 4
        b.append(arrow(xa, y2 + bh / 2, xb, y2 + bh / 2, lab, ly=y2 + bh / 2 - 9))
    # up the left side, closing the loop
    xl = xs[0] + bw / 2
    b.append(arrow(xl, y2 - 4, xl, y1 + bh + 4, "what works feeds|the next briefs",
                   lx=xl + 12, ly=(y1 + bh + y2) / 2 + 12, anchor="start"))
    b.append(f'<text x="{W / 2}" y="{(y1 + bh + y2) / 2 + 4}" class="big">runs itself every '
             f'day · two human steps</text>')
    return svg(W, H, "".join(b), "The daily loop: refill, render queue, night batch, video "
                                  "review, music, production queue, poster, stats, back to refill")


# ── FIGURE B: one video = a circular chain ────────────────────────────────────────────
CHAIN = [("flared star", 12), ("storm world", 6.9), ("mountain country", 4.0),
         ("mine yard", 2.4), ("cavern hall", 1.6), ("sphere ranks", -0.6),
         ("water cages", -8.4), ("untouched matter", -12.8), ("quivering trio", -15.4),
         ("arrival ring", 0.9), ("echo shells", 16.5)]


def fig_chain():
    W, H = 640, 470
    cx, cy, R = 320, 236, 150
    n = len(CHAIN)
    b = [f'<circle cx="{cx}" cy="{cy}" r="{R}" class="ring"/>']
    pts = []
    for i, (nm, ex) in enumerate(CHAIN):
        a = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        pts.append((x, y, a))
    # direction arrow along the ring (clockwise)
    a0 = -math.pi / 2 + 0.18
    b.append(f'<path d="M{cx + (R + 0) * math.cos(a0):.1f},{cy + R * math.sin(a0):.1f} '
             f'A{R},{R} 0 0 1 {cx + R * math.cos(a0 + 0.22):.1f},{cy + R * math.sin(a0 + 0.22):.1f}" '
             f'class="edge" marker-end="url(#ah)"/>')
    for i, ((nm, ex), (x, y, a)) in enumerate(zip(CHAIN, pts)):
        cls = "dot"
        if i == 0:
            cls += " play"
        if i == 6:
            cls += " rstart"
        if i in (8, 9):
            cls += " seam"
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" class="{cls}"/>')
        lx, ly = cx + (R + 24) * math.cos(a), cy + (R + 24) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.12 else ("start" if math.cos(a) > 0 else "end")
        sign = "−" if ex < 0 else ""
        exs = f"10<tspan dy='-5' font-size='9'>{sign}{abs(ex):g}</tspan><tspan dy='5'> </tspan>"
        b.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" class="lbl" text-anchor="{anchor}">'
                 f'{exs}{nm}</text>')
    b.append(f'<text x="{cx}" y="{cy - 14}" class="big">one journey</text>')
    b.append(f'<text x="{cx}" y="{cy + 8}" class="s">11 world cards, each ×10 deeper,</text>')
    b.append(f'<text x="{cx}" y="{cy + 26}" class="s">the last one contains the first</text>')
    return svg(W, H, "".join(b), "A journey is a circular chain of world cards from cosmic "
                                  "scale down to subatomic and back through a seam")


# ── FIGURE C: inside one card — the real schedules ────────────────────────────────────
def fig_card():
    W, H = 1120, 330
    F, fpb = 28, 7
    wts = [0.30 + 0.70 * math.sin(math.pi * (j + 0.5) / F) ** 2 for j in range(F)]
    s_ = sum(wts)
    z = [math.exp(math.log(10.0) * w / s_) for w in wts]           # grammar.compile_journey
    den = [0.58] * 6 + [0.40] * (F - 8) + [0.40 + 0.18 * 0.4, 0.40 + 0.18 * 0.7]   # dive.py
    x0, x1, yt, yb = 70, 1080, 70, 270
    fx = lambda j: x0 + (x1 - x0) * (j + 3) / (F + 8)               # frames -3 .. F+5
    b = []
    # phase bands
    for a_, e_, nm in ((0, 7, "ARRIVE · the morph"), (7, 16, "TRAVEL · look around"),
                       (16, 28, "PLUNGE · dive into the target")):
        b.append(f'<rect x="{fx(a_):.1f}" y="34" width="{fx(e_) - fx(a_) - 3:.1f}" height="22" '
                 f'rx="5" class="band"/>')
        b.append(f'<text x="{(fx(a_) + fx(e_)) / 2:.1f}" y="49" class="s">{nm}</text>')
    # bar lines + beats
    for j in (0, F):
        b.append(f'<line x1="{fx(j):.1f}" y1="28" x2="{fx(j):.1f}" y2="{yb + 8}" class="barline"/>')
        b.append(f'<text x="{fx(j):.1f}" y="20" class="el">bar line = downbeat</text>')
    for j in range(0, F + 1, fpb):
        b.append(f'<line x1="{fx(j):.1f}" y1="{yb}" x2="{fx(j):.1f}" y2="{yb + 8}" class="tick"/>')
        if j < F:
            b.append(f'<text x="{fx(j) + 4:.1f}" y="{yb + 22}" class="s" text-anchor="start">'
                     f'beat {j // fpb + 1}</text>')
    b.append(f'<line x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}" class="axis"/>')
    # zoom curve (accent), scaled 1.00 .. 1.14
    zy = lambda v: yb - (v - 1.0) / 0.16 * (yb - yt)
    ext = [z[-3], z[-2], z[-1]] + z + z[:5]
    pz = " ".join(f"{fx(j - 3):.1f},{zy(v):.1f}" for j, v in enumerate(ext))
    b.append(f'<polyline points="{pz}" class="curve accent"/>')
    jm = max(range(F), key=lambda j: z[j])
    b.append(f'<text x="{fx(jm):.1f}" y="{zy(z[jm]) - 10:.1f}" class="el accent-t">zoom per '
             f'frame peaks ×{z[jm]:.3f}</text>')
    b.append(f'<text x="{fx(1) + 6:.1f}" y="{zy(z[1]) - 8:.1f}" class="el accent-t" '
             f'text-anchor="start">×{z[0]:.3f}</text>')
    # denoise step line, scaled 0.30 .. 0.62
    dy = lambda v: yb - (v - 0.30) / 0.32 * (yb - yt)
    dext = [0.40, 0.40 + 0.18 * 0.4, 0.40 + 0.18 * 0.7] + den + [0.58] * 5
    pd = []
    for j, v in enumerate(dext):
        pd.append(f"{fx(j - 3):.1f},{dy(v):.1f}")
        pd.append(f"{fx(j - 2):.1f},{dy(v):.1f}")
    b.append(f'<polyline points="{" ".join(pd)}" class="curve"/>')
    b.append(f'<text x="{fx(3):.1f}" y="{dy(0.58) - 8:.1f}" class="el">denoise 0.58 on the '
             f'beat</text>')
    b.append(f'<text x="{fx(14):.1f}" y="{dy(0.40) + 18:.1f}" class="el">0.40 while '
             f'travelling: structures persist</text>')
    b.append(f'<text x="{fx(F - 2) - 8:.1f}" y="{dy(0.50):.1f}" class="el" text-anchor="end">'
             f'2-frame pickup into the beat</text>')
    b.append(f'<text x="{W / 2}" y="{H - 8}" class="s">one card = one bar of music = 28 frames '
             f'at 103 bpm · the whole card multiplies scale by exactly 10</text>')
    return svg(W, H, "".join(b), "Inside one card: zoom rate rises and falls across the bar, "
                                  "denoise peaks on the downbeat with a two-frame pickup")


# ── FIGURE D: the frame loop ──────────────────────────────────────────────────────────
def fig_frameloop():
    W, H = 1120, 470
    bw, bh = 196, 60
    xs = [40, 322, 604, 886]
    y1, y2 = 120, 290
    b = []
    top = [("previous frame", "the only memory"), ("crop-zoom", "toward the aim"),
           ("parallax residual", "near grows faster than far"),
           ("detail boost", "sharpen · palette match")]
    bot = [("new frame", "saved, then fed back"), ("diffusion img2img", "DreamShaper XL · ComfyUI"),
           ("composite layer", "cameo sprite · planet plate")]
    for (t, s_), x in zip(top, xs):
        b.append(box(x, y1, bw, bh, t, s_))
    bx = [xs[0], xs[1] + 141, xs[3]]
    for (t, s_), x in zip(bot, bx):
        b.append(box(x, y2, bw, bh, t, s_, "accent" if "diffusion" in t else ""))
    for i in range(3):
        b.append(arrow(xs[i] + bw + 4, y1 + bh / 2, xs[i + 1] - 4, y1 + bh / 2))
    b.append(arrow(xs[3] + bw / 2, y1 + bh + 4, xs[3] + bw / 2, y2 - 4))
    b.append(arrow(bx[2] - 4, y2 + bh / 2, bx[1] + bw + 4, y2 + bh / 2))
    b.append(arrow(bx[1] - 4, y2 + bh / 2, bx[0] + bw + 4, y2 + bh / 2))
    b.append(arrow(xs[0] + bw / 2, y2 - 4, xs[0] + bw / 2, y1 + bh + 4, "feeds the next frame",
                   lx=xs[0] + bw / 2 + 10, ly=(y1 + bh + y2) / 2 + 4, anchor="start"))
    # side inputs (top)
    ins_top = [(xs[1], "tracker v3 → aim", "schedule → zoom z"),
               (xs[2], "DepthAnything → depth", "resolve scaffold → depth"),
               (xs[3], "palette anchor per phase", "")]
    for x, l1, l2 in ins_top:
        b.append(f'<g class="node ghost"><rect x="{x + 8}" y="28" width="{bw - 16}" height="52" rx="8"/>'
                 f'<text x="{x + bw / 2}" y="{49 if l2 else 58}" class="s">{l1}</text>'
                 + (f'<text x="{x + bw / 2}" y="66" class="s">{l2}</text>' if l2 else "") + "</g>")
        b.append(arrow(x + bw / 2, 82, x + bw / 2, y1 - 4, cls="thin"))
    # side inputs (bottom) into diffusion
    dx = bx[1]
    items = ["prompt crossfade old → new world", "depth ControlNet: feedback or scaffold",
             "IP-Adapter: loop home · void hold", "denoise schedule + noise mask"]
    b.append(f'<g class="node ghost"><rect x="{dx - 40}" y="{y2 + bh + 30}" width="{bw + 80}" '
             f'height="{18 * len(items) + 14}" rx="8"/>'
             + "".join(f'<text x="{dx + bw / 2}" y="{y2 + bh + 50 + 18 * i}" class="s">{t}</text>'
                       for i, t in enumerate(items)) + "</g>")
    b.append(arrow(dx + bw / 2, y2 + bh + 28, dx + bw / 2, y2 + bh + 4, cls="thin"))
    b.append(f'<text x="{(xs[1] + xs[2] + bw) / 2}" y="{(y1 + bh + y2) / 2 + 4}" class="big">every '
             f'frame is freshly generated · nothing is pasted and kept</text>')
    return svg(W, H, "".join(b), "The frame loop: previous frame, crop-zoom, parallax, detail "
                                  "boost, composite layer, diffusion, new frame, fed back")


# ── FIGURE F: closing the loop ────────────────────────────────────────────────────────
def fig_loop():
    W, H = 1120, 300
    x0, cw, y = 40, 84, 60
    names = ["card 0", "card 1", "card 2", "…", "card N", "lap: card 0 again"]
    widths = [cw, cw, cw, 60, cw, cw + 70]
    b, x = [], x0
    xs = []
    for nm, w in zip(names, widths):
        cls = "node cut" if nm == "card 0" else ("node accent" if nm.startswith("lap") else "node")
        b.append(f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w - 6}" height="46" rx="8"/>'
                 f'<text x="{x + (w - 6) / 2}" y="{y + 28}" class="s">{nm}</text></g>')
        xs.append((x, w))
        x += w
    b.append(f'<text x="{xs[0][0] + (xs[0][1] - 6) / 2}" y="{y + 66}" class="el">cold first</text>')
    b.append(f'<text x="{xs[0][0] + (xs[0][1] - 6) / 2}" y="{y + 81}" class="el">frame: cut</text>')
    xa, xb = xs[1][0], xs[5][0] + xs[5][1] - 6
    b.append(f'<path d="M{xa},{y + 60} v10 H{xb} v-10" class="edge" fill="none"/>')
    b.append(f'<text x="{(xa + xb) / 2}" y="{y + 88}" class="el">delivered video: exactly N bars, '
             f'every world once</text>')
    # homing arrow from the tail back to the frames leading into the start
    xt = xs[5][0] + xs[5][1] - 20
    b.append(f'<path d="M{xt},{y - 4} C{xt},{y - 52} {xa + 10},{y - 52} {xa + 10},{y - 6}" '
             f'class="edge accent" fill="none" marker-end="url(#ah)"/>')
    b.append(f'<text x="{(xt + xa) / 2}" y="{y - 46}" class="el accent-t">tail homes onto the '
             f'frames that lead into the opening · IP-Adapter carries the world, depth aligns the '
             f'landing</text>')
    # play order
    y2 = 196
    b.append(f'<text x="{x0}" y="{y2 - 12}" class="el" text-anchor="start">then the finished loop is '
             f'rotated so it opens where the composer chose (play order ≠ render order)</text>')
    seq = ["10¹² star", "planet descent", "10⁴", "10²", "…", "10⁻¹⁵", "seam", "10¹⁶"]
    x = x0
    for i, nm in enumerate(seq):
        w = 126 if nm != "…" else 60
        cls = "node play" if i == 0 else ("node seam" if nm == "seam" else "node")
        b.append(f'<g class="{cls}"><rect x="{x}" y="{y2}" width="{w - 6}" height="40" rx="8"/>'
                 f'<text x="{x + (w - 6) / 2}" y="{y2 + 25}" class="s">{nm}</text></g>')
        x += w
    b.append(f'<path d="M{x - 6},{y2 + 20} h26 v46 H{x0 - 16} v-46 h12" class="edge" fill="none" '
             f'marker-end="url(#ah)"/>')
    b.append(f'<text x="{(x0 + x) / 2}" y="{y2 + 84}" class="el">scale falls monotonically, wraps '
             f'once through the seam, loops back into the opening</text>')
    return svg(W, H, "".join(b), "Closing the loop: the cold first card is cut, an extra lap "
                                  "re-renders it mid-chain, the tail homes onto the opening")


# ── FIGURE G: music alignment ─────────────────────────────────────────────────────────
def fig_music():
    W, H = 1120, 250
    x0, x1 = 210, 1080
    b = []
    rows = [(54, "video morphs", 1.0, 0.0, "every bar, exact"),
            (124, "track as generated", 0.978, 0.31, "its own bar is ~2% off, phase arbitrary"),
            (194, "after stretch + slide", 1.0, 0.0, "deep accents land on every morph")]
    n = 11
    for y, nm, k, ph, note in rows:
        b.append(f'<text x="{x0 - 16}" y="{y + 4}" class="t" text-anchor="end">{nm}</text>')
        b.append(f'<text x="{x0 - 16}" y="{y + 20}" class="s" text-anchor="end">{note}</text>')
        b.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" class="axis"/>')
        step = (x1 - x0) / (n - 0.5)
        for i in range(n):
            x = x0 + step * (i * k + ph) + 14
            if x > x1:
                continue
            if nm == "video morphs":
                b.append(f'<line x1="{x:.1f}" y1="{y - 16}" x2="{x:.1f}" y2="{y + 16}" class="barline"/>')
            else:
                cls = "beat accent-f" if nm.startswith("after") else "beat"
                b.append(f'<circle cx="{x:.1f}" cy="{y}" r="7" class="{cls}"/>')
                for q in (0.25, 0.5, 0.75):
                    xq = x + step * k * q
                    if xq < x1:
                        b.append(f'<circle cx="{xq:.1f}" cy="{y}" r="2.6" class="beat small"/>')
    # guide lines from morphs down
    step = (x1 - x0) / (n - 0.5)
    for i in range(n):
        x = x0 + step * i + 14
        b.append(f'<line x1="{x:.1f}" y1="70" x2="{x:.1f}" y2="{194 + 18}" class="guide"/>')
    return svg(W, H, "".join(b), "Music alignment: the track's own bar is measured, stretched to "
                                  "the video bar, and slid so deep accents land on the morphs")


# ── real frame strip ──────────────────────────────────────────────────────────────────
def thumb(path, w=176):
    im = Image.open(path).convert("RGB")
    im = im.resize((w, round(w * im.height / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def strip_descent():
    d = ROOT / "output" / "cherenkov_cistern" / "v1" / "build" / "frames"
    shots = [(160, "arrival", "the previous world re-imagines itself into the star scene, live"),
             (172, "the globe enters", "from beyond a frame edge, already a good size"),
             (190, "orbit view", "reaches full width exactly on the bar line"),
             (204, "limb leaves the frame", "still growing through the next card's arrival"),
             (222, "on the surface", "the next card's own approach takes over")]
    out = []
    for f, t, s_ in shots:
        p = d / f"{f:05d}.png"
        if not p.exists():
            return ""
        out.append(f'<figure class="shot"><img src="{thumb(p)}" alt="{t}"/>'
                   f'<figcaption><b>{t}</b><span>{s_}</span></figcaption></figure>')
    return '<div class="strip">' + "".join(out) + "</div>"


# ── technology index ──────────────────────────────────────────────────────────────────
TECH = [
    ("Format & authoring", [
        ("Three-layer format", "FORMAT fixed signature · STYLE deck · JOURNEY cards. Infinite variety stays on brand.", "PLAN.md"),
        ("World-card journeys", "A circular nesting chain: each card's target is contained in its scene and becomes the next scene.", "journeys/*.json"),
        ("Grammar compiler", "Turns cards into prompts plus per-frame zoom, denoise, exponent and approach schedules.", "engine/grammar.py"),
        ("Style deck", "13 curated looks; the composer names one, never writes the look.", "styles/deck.json"),
        ("REALMS + VARIATIONS", "What exists at each scale and how journeys differ; feeds the composer.", "journeys/REALMS.md"),
        ("Tempo as a knob", "frames per beat sets bpm (5→144, 7→103, 9→80); all musical geometry scales with it.", "engine/dive.py"),
    ]),
    ("The zoom engine", [
        ("Feedback zoom", "Crop the last frame, re-imagine it. Build-in only; build-out was rejected.", "engine/dive.py"),
        ("Arrive · look · plunge", "One breathing zoom curve per card, ×10 per card, uniform bars.", "engine/grammar.py"),
        ("On-beat morph", "Denoise peaks on the downbeat with a 2-frame pickup; seams get more frames, never more force.", "engine/dive.py"),
        ("Tracker v3", "Point emergence, then Florence-2 object lock; exact propagation through the crop; frozen thirds anchor.", "engine/track.py"),
        ("Depth ControlNet", "Holds the target's structure while every pixel regenerates (strength 0.45).", "engine/dive.py"),
        ("10ⁿ counter", "Odometer pinned to the real cumulative zoom, honest across seams.", "engine/dive.py"),
    ]),
    ("Depth & population", [
        ("Parallax residual", "Near content expands faster than far; the missing depth cue of a crop-zoom.", "engine/warp.py"),
        ("Resolve-on-approach", "Animated depth scaffolds (sea, lattice, surface, web): a realm resolves out of the old texture as countless instances.", "engine/scaffold.py"),
        ("Looming scaffolds", "Per-instance distance, painter's occlusion: size, brightness and motion agree.", "engine/scaffold.py"),
        ("Camera vocabulary", "Roll, orbit, dolly, tilt compiled per card; parked below the noise floor, kept inert.", "engine/camera.py"),
    ]),
    ("Planet descent", [
        ("Planet plate", "A globe rendered from the next card's scene, composited at an exact scheduled size every frame.", "engine/plate.py"),
        ("Live arrival", "Space held by masked IP-Adapter, not a pixel blend; globe denoise capped absolutely.", "engine/plate.py"),
        ("Enter / grow", "The globe slides in from a frame edge or swells from a point of light; never just appears.", "engine/plate.py"),
        ("Spans the bar line", "Orbit view on the beat, keeps growing, hands off when the frame is inside the disc.", "engine/plate.py"),
        ("Plate gates", "Caption checks re-roll a void that came out as jewellery or a surface with a horizon.", "engine/plate.py"),
        ("Position audit", "Moves the render start so the planet card sits mid-chain; records the play start.", "scripts/plate_position_audit.py"),
    ]),
    ("Loops, seams, openings", [
        ("Loop lap", "Render card 0 again mid-chain and cut the cold first card: the loop home is born from the chain.", "engine/grammar.py"),
        ("Trajectory homing", "The tail aims at the frames leading into the opening: IP-Adapter for the world, depth for the landing.", "engine/dive.py"),
        ("Play order", "Assembly rotates the finished loop to the composer's opening; render order is free.", "engine/dive.py"),
        ("Frame-0 establish", "A wide, target-free first prompt with scale-aware wording and anti-close-up negatives.", "engine/grammar.py"),
        ("Figure gate", "Captions frame 0; re-rolls a lone figure before an hour is wasted.", "engine/figure.py"),
        ("Repair family", "Replace an opening or a tail, or re-render from any card, without redoing the video.", "scripts/replace_*.py"),
    ]),
    ("Cast & captions", [
        ("Mascot cameos", "13 hidden characters, scale-matched to the card, pasted world-attached; the find-the-character hook.", "output/mascots/canon"),
        ("Caption writer", "Local LLM writes five caption options, YouTube description and world chain.", "scripts/caption.py"),
    ]),
    ("Music", [
        ("Music deck", "10 lanes × rhythm feels with a deep-downbeat doctrine.", "styles/music_deck.json"),
        ("ACE-Step generation", "Ten takes at the video's tempo, overnight, so approval costs seconds.", "scripts/music_gen.py"),
        ("Aligner", "Measure the track's own bar, stretch, kick-weighted phase search, seamless loop.", "scripts/align.py"),
        ("Beat · sync · fit", "Deep-pulse presence, accents on morphs, phrase length equals the bar.", "scripts/align.py"),
        ("Re-rank", "Re-judges every take on disk without a GPU.", "scripts/music_gen.py"),
    ]),
    ("Pipeline & posting", [
        ("Midnight refill", "A coordinator briefs parallel composers; the script audits and queues only passers.", "scripts/journey_refill.py"),
        ("Night batch", "Queue order within a time budget; render, ingest, caption, music; backpressure at 20 ready.", "scripts/night_batch.py"),
        ("Single source of truth", "pipeline.json for videos, journeys.json for decisions; writers merge into a fresh read.", "scripts/pipeline.py"),
        ("Cadence gate", "Posts every 19 hours, remaps the 01–07 dead zone, advances only on verified success.", "scripts/post_gate.py"),
        ("Poster", "Drives a real Chrome over CDP; trusted clicks, caption verified on the live page, self-heals.", "scripts/poster.py"),
        ("Audience analytics", "Instagram and YouTube stats; qscore = engagement against what reach predicts.", "scripts/ig_analyze.py"),
    ]),
]


def tech_html():
    out = []
    for group, items in TECH:
        cards = "".join(f'<div class="card"><h4>{n}</h4><p>{d}</p><code>{f}</code></div>'
                        for n, d, f in items)
        out.append(f'<section class="tgroup"><h3>{group}</h3><div class="cards">{cards}</div></section>')
    return "".join(out)


CSS = """
:root{--bg:#f6f5f2;--panel:#ffffff;--ink:#1c1b22;--mute:#5d5a6b;--line:#d9d6cf;--accent:#5b3fd6;
--accent-soft:#ece8fd;--human:#b3620a;--human-soft:#fdf0dd;--seam:#c2255c;--ghost:#f0eee9}
@media (prefers-color-scheme: dark){:root{--bg:#0e1117;--panel:#161a23;--ink:#ecebf3;--mute:#a09db0;
--line:#2b3040;--accent:#a08bff;--accent-soft:#241f45;--human:#f0a23b;--human-soft:#3a2a12;
--seam:#ff6b9a;--ghost:#1b202b}}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 "Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:8px 16px 40px}
header h1{font-size:30px;line-height:1.15;margin:10px 0 6px;letter-spacing:-.02em;text-wrap:balance}
header p{max-width:74ch;color:var(--mute);margin:0 0 14px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 6px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 16px;min-width:128px}
.stat b{display:block;font-size:24px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.stat span{color:var(--mute);font-size:12.5px}
section.fig{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px 22px 16px;margin:20px 0}
.kicker{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:600}
section.fig h2{font-size:21px;margin:2px 0 4px;letter-spacing:-.01em;text-wrap:balance}
section.fig .claim{color:var(--mute);max-width:80ch;margin:0 0 12px}
figure{margin:0}figcaption{color:var(--mute);font-size:13px;margin-top:8px;max-width:90ch}
svg{width:100%;height:auto;display:block;color:var(--ink);overflow:visible}
.two{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:26px;align-items:center}
@media (max-width:900px){.two{grid-template-columns:1fr}}
.legend{list-style:none;margin:0;padding:0;display:grid;gap:11px}
.legend li{display:grid;grid-template-columns:18px 1fr;gap:10px;align-items:start}
.legend i{width:14px;height:14px;border-radius:50%;margin-top:4px;border:2px solid var(--ink);background:var(--panel)}
.legend i.play{background:var(--accent);border-color:var(--accent)}
.legend i.rstart{border-color:var(--human);background:var(--human-soft)}
.legend i.seam{border-color:var(--seam);background:var(--seam)}
.legend b{display:block}.legend span{color:var(--mute);font-size:13.5px}
.node rect{fill:var(--panel);stroke:currentColor;stroke-width:1.4}
.node.human rect{fill:var(--human-soft);stroke:var(--human);stroke-width:2}
.node.accent rect{fill:var(--accent-soft);stroke:var(--accent);stroke-width:2}
.node.play rect{fill:var(--accent-soft);stroke:var(--accent);stroke-width:2}
.node.seam rect{stroke:var(--seam);stroke-width:2}
.node.cut rect{stroke-dasharray:5 4;opacity:.65}
.node.ghost rect{fill:var(--ghost);stroke:var(--line)}
text{fill:currentColor;font-family:inherit}
.t{font-size:14px;font-weight:600;text-anchor:middle}
.s{font-size:12px;text-anchor:middle;fill:var(--mute)}
.el{font-size:12px;text-anchor:middle;fill:var(--mute)}
.lbl{font-size:12.5px}
.big{font-size:14px;text-anchor:middle;font-weight:600;fill:var(--mute)}
.accent-t{fill:var(--accent)}
.edge{stroke:currentColor;stroke-width:1.5;fill:none}.edge.thin{stroke-width:1.1;opacity:.7}
.edge.accent{stroke:var(--accent);color:var(--accent)}
.ring{fill:none;stroke:var(--line);stroke-width:2}
.dot{fill:var(--panel);stroke:currentColor;stroke-width:2}
.dot.play{fill:var(--accent);stroke:var(--accent)}.dot.rstart{stroke:var(--human);fill:var(--human-soft);stroke-width:3}
.dot.seam{fill:var(--seam);stroke:var(--seam)}
.band{fill:var(--ghost);stroke:var(--line)}
.barline{stroke:var(--accent);stroke-width:2;stroke-dasharray:2 4}
.tick,.axis{stroke:currentColor;stroke-width:1.2}.guide{stroke:var(--line);stroke-width:1;stroke-dasharray:3 5}
.curve{fill:none;stroke:currentColor;stroke-width:2}.curve.accent{stroke:var(--accent);stroke-width:2.6}
.beat{fill:var(--panel);stroke:currentColor;stroke-width:2}.beat.small{stroke-width:1.2;opacity:.6}
.beat.accent-f{fill:var(--accent);stroke:var(--accent)}
.strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:6px 0 4px}
.shot img{width:100%;border-radius:10px;display:block;border:1px solid var(--line)}
.shot figcaption{margin-top:6px}.shot b{display:block;color:var(--ink);font-size:13.5px}
.shot span{font-size:12.5px}
.rail{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:10px 0 0;font-size:12px;color:var(--mute)}
.rail div{border-top:3px solid var(--line);padding-top:6px}.rail div.on{border-color:var(--accent);color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}
.chip{font-size:12.5px;border:1px solid var(--line);border-radius:999px;padding:3px 11px;color:var(--mute);background:var(--bg)}
.scores{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}
.score{border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.score b{display:block}.score span{color:var(--mute);font-size:13px}
h2.index{font-size:21px;margin:30px 0 2px}p.index{color:var(--mute);margin:0 0 6px}
.tgroup h3{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:22px 0 8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(258px,1fr));gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.card h4{margin:0 0 3px;font-size:14.5px}.card p{margin:0 0 7px;color:var(--mute);font-size:13px;line-height:1.45}
.card code{font:11.5px ui-monospace,Consolas,monospace;color:var(--mute);opacity:.85;overflow-wrap:anywhere}
footer{color:var(--mute);font-size:12.5px;margin-top:26px}
"""


def main():
    d = pl.load()
    states = Counter(v.get("state") for v in d["videos"])
    n_j = len(list((ROOT / "journeys").glob("*.json")))
    stats = [(states.get("live", 0), "videos live"), (n_j, "journeys in the catalog"),
             (13, "visual styles"), (10, "music lanes"), (13, "hidden mascots"),
             ("×10", "scale per card"), ("0", "paid APIs · one RTX 3080")]
    stat_html = "".join(f'<div class="stat"><b>{a}</b><span>{b}</span></div>' for a, b in stats)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>How Powers of Zen works</title>
<style>{CSS}</style></head><body><main>
<header><h1>How a Powers of Zen video gets made</h1>
<p>Endless, seamless dives through every scale of the universe, produced and posted by a pipeline
that runs itself on one desktop GPU. This page is the map: the daily loop, how one video is built
frame by frame, and every piece of technology we developed along the way.</p>
<div class="stats">{stat_html}</div></header>

<section class="fig"><div class="kicker">1 · the big picture</div><h2>The daily loop</h2>
<p class="claim">Journeys are written at midnight, rendered overnight, and posted on a fixed cadence.
You touch it twice: approving a video and choosing its music.</p>
<figure>{fig_pipeline()}<figcaption>Amber boxes are the two human steps. Everything else is a scheduled
job. Results flow back into the next night's briefs, so the catalog learns what works.</figcaption></figure>
<div class="chips"><span class="chip">start + preflight audits</span><span class="chip">cameo realm check</span>
<span class="chip">planet position audit</span><span class="chip">backpressure at 20 ready</span>
<span class="chip">frame-0 figure gate</span><span class="chip">plate caption gates</span>
<span class="chip">per-render timeouts</span><span class="chip">Chrome self-heal</span>
<span class="chip">caption verified on the live page</span><span class="chip">Instagram size fallback</span></div>
</section>

<section class="fig"><div class="kicker">2 · the content</div><h2>One video is a circular chain of worlds</h2>
<p class="claim">Each card's target is something contained in its scene, and that target's surface becomes
the next scene. The last card contains the first, so the dive never ends.</p>
<div class="two"><figure>{fig_chain()}</figure>
<ul class="legend">
<li><i class="play"></i><div><b>Play start</b><span>where the video opens: the composer's choice, the top of the scale.</span></div></li>
<li><i class="rstart"></i><div><b>Render start</b><span>where the chain begins rendering: an abstract realm that is easy to establish cold, and that keeps the planet card mid-chain.</span></div></li>
<li><i class="seam"></i><div><b>The seam</b><span>the one exotic wrap, subatomic back to cosmic. It is a morph on the beat, not a zoom, and it gets more frames rather than more force.</span></div></li>
<li><i></i><div><b>Every other step</b><span>a true optical zoom into a contained object, ten times deeper per card.</span></div></li>
</ul></div>
<figcaption>The example is cherenkov_cistern. Render order and play order are independent because the finished video is a seamless loop.</figcaption>
</section>

<section class="fig"><div class="kicker">3 · the rhythm</div><h2>Inside one card: zoom and denoise are musical</h2>
<p class="claim">Every card is one bar. The camera arrives, looks, then plunges, and the world flips exactly on
the downbeat. These curves are computed from the engine's own formulas.</p>
<figure>{fig_card()}<figcaption>The smooth curve is how hard the camera zooms each frame. The step line is how much of each frame is re-imagined.
Low denoise while travelling is what makes it a zoom rather than a morph; the short peak on the beat is what lets the palette flip between worlds.</figcaption></figure>
</section>

<section class="fig"><div class="kicker">4 · the engine</div><h2>The frame loop</h2>
<p class="claim">The only memory is the previous frame. It is cropped toward a tracked target, given depth motion,
and handed to the diffusion model, which paints the next frame. Everything else steers that one step.</p>
<figure>{fig_frameloop()}<figcaption>Grey boxes are the signals that steer each stage. The composite layer is the one place
pixels are supplied directly, which is why mascots and planets persist while everything around them churns.</figcaption></figure>
</section>

<section class="fig"><div class="kicker">5 · the newest piece</div><h2>The planet descent</h2>
<p class="claim">The model could never grow a planet out of inherited texture, and the tracker never once locked one.
So the globe is supplied as pixels at an exactly scheduled size, while the space around it stays alive.</p>
{strip_descent()}
<div class="rail"><div class="on">planet card begins</div><div class="on">plate active</div><div class="on">bar line</div>
<div class="on">plate active</div><div>tracker takes over</div></div>
<figcaption>Real frames from cherenkov_cistern. The globe's texture is generated once from the next card's scene, wrapped on a sphere,
revolved slowly and composited each frame. Space is held by an IP-Adapter reference masked to outside the disc; the globe's own denoise is capped so it cannot dissolve into rings.</figcaption>
</section>

<section class="fig"><div class="kicker">6 · the loop</div><h2>Closing the loop without a visible seam</h2>
<p class="claim">The first frame of any render is the only one not born from the chain, so it is thrown away.
An extra lap re-renders that world mid-dive, and the tail homes onto the frames that lead into the opening.</p>
<figure>{fig_loop()}</figure>
</section>

<section class="fig"><div class="kicker">7 · the sound</div><h2>Music that lands on the morphs</h2>
<p class="claim">Ten takes are generated overnight at the video's tempo. Each is measured, stretched by a percent or two,
and slid until its deep accents sit on the bar lines, then looped seamlessly.</p>
<figure>{fig_music()}</figure>
<div class="scores"><div class="score"><b>beat</b><span>is there a deep pulse you can feel? Carries the ranking.</span></div>
<div class="score"><b>sync</b><span>do this track's accents sit on the morphs? Chooses where the loop starts.</span></div>
<div class="score"><b>fit</b><span>does the track phrase in the video's bar, judged against its own measured tempo?</span></div></div>
</section>

<h2 class="index">Everything we built</h2><p class="index">Each piece, what it is for, and where it lives.</p>
{tech_html()}
<footer>Built {date.today().isoformat()} by scripts/build_overview.py · static snapshot · regenerate to refresh the counts and frames.</footer>
</main>
<script>try{{const h=()=>window.parent.postMessage({{isStreamlitMessage:true,type:"streamlit:setFrameHeight",height:document.documentElement.scrollHeight}},"*");h();window.addEventListener("load",h);new ResizeObserver(h).observe(document.body)}}catch(e){{}}</script>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
