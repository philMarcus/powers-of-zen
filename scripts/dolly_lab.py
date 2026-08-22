#!/usr/bin/env python3
"""dolly_lab — DEPTH 2.0 Phase A/B gate: does depth-differential parallax make the dive
read 3-D in MOTION? (PLAN "PARALLAX ERA", approved 2026-08-22.)

Four arms, same journey, same seed, same schedule — the ONLY variable is the parallax
residual on the fed-back frame (and arm 4 adds the persistent scaffold sea):
  a0    --parallax 0             baseline = today's production engine
  a05   --parallax 0.5           half-gain residual
  a10   --parallax 1.0           full gain (nearest plane ~z^1.5, far field recedes)
  a10p  --parallax 1.0 --resolve-persist   + scaffold stays the depth source all card

Each arm is a REAL dive.py run (schedule-faithful by construction) over the first N cards
of the journey's render order; deliverable is a 12fps SLOW LOOPED side-by-side
(Phil's standing lab format — never a fast once-through) plus a sampled frame strip.

GATE (from the plan): near instances visibly overtake far ones and exit fast at the
edges; no structure smear by card end; no added morph-feel.

Usage:
  python3 scripts/dolly_lab.py                     # squid_lantern, 3 cards, all 4 arms
  python3 scripts/dolly_lab.py --journey X --cards 2 --arms a0,a10
  python3 scripts/dolly_lab.py --montage-only      # rebuild clips from recorded runs
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import engine.dive as dive  # noqa: E402
import pipeline as pl  # noqa: E402
from score import win, FFMPEG, _run  # noqa: E402

ARMS = {
    "a0":   ("baseline",     ["--parallax", "0"]),
    "a05":  ("gain 0.5",     ["--parallax", "0.5"]),
    "a10":  ("gain 1.0",     ["--parallax", "1.0"]),
    "a10p": ("1.0 + persist", ["--parallax", "1.0", "--resolve-persist"]),
    # Phil 2026-08-22 evening: 0.5 read most 3-D of the first four — test persist on it
    "a05p": ("0.5 + persist", ["--parallax", "0.5", "--resolve-persist"]),
}
LAB = ROOT / "output" / "dolly_lab"


def card_frames(journey, n_cards):
    spec = json.loads(pl.journey_path(journey).read_text(encoding="utf-8"))
    fps = {**dive.DEFAULTS, **spec.get("settings", {})}["fps"]
    cfr = dive.register_frame_counts(spec, fps)          # render-order per-card counts
    return sum(cfr[:n_cards]), cfr


def newest_v(journey_out):
    vs = sorted((d for d in journey_out.glob("v*") if d.name[1:].isdigit()),
                key=lambda d: int(d.name[1:]))
    return vs[-1] if vs else None


def run_arm(journey, arm, frames):
    label, extra = ARMS[arm]
    jpath = pl.journey_path(journey)
    out_base = ROOT / "output" / journey
    before = {d.name for d in out_base.glob("v*")} if out_base.exists() else set()
    cmd = [sys.executable, str(ROOT / "engine" / "dive.py"), str(jpath),
           "--frames", str(frames), "--no-video"] + extra
    print(f"\n=== ARM {arm} ({label}): {' '.join(cmd[2:])}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(f"arm {arm} render failed (exit {r.returncode})")
    new = [d for d in out_base.glob("v*") if d.name not in before]
    if len(new) != 1:
        raise SystemExit(f"arm {arm}: expected one new vN, found {new}")
    print(f"=== ARM {arm} done in {(time.time() - t0) / 60:.1f} min -> {new[0]}", flush=True)
    return new[0]


def montage(journey, runs, frames, card_bounds):
    """Side-by-side labeled frames -> 12fps clip looped 3x + a sampled strip."""
    LAB.mkdir(parents=True, exist_ok=True)
    tmp = LAB / f"{journey}_ab_frames"
    tmp.mkdir(exist_ok=True)
    arms = list(runs)
    W, H, BAR = 576, 1024, 44
    for i in range(frames):
        cols = []
        ok = True
        for a in arms:
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            if not p.exists():
                ok = False
                break
            cols.append(Image.open(p).convert("RGB"))
        if not ok:
            break
        out = Image.new("RGB", (W * len(cols), H + BAR), (12, 12, 16))
        d = ImageDraw.Draw(out)
        for k, (a, im) in enumerate(zip(arms, cols)):
            out.paste(im, (k * W, BAR))
            d.text((k * W + 12, 10), ARMS[a][0], fill=(240, 230, 200))
        # card boundary tick so "by card end" is judgeable
        card = sum(1 for b in card_bounds if i >= b)
        d.text((out.width - 150, 10), f"f{i:03d} card {card}", fill=(150, 160, 190))
        out.save(tmp / f"{i:05d}.png")
    n = len(list(tmp.glob("*.png")))
    clip = LAB / f"{journey}_dolly_AB_loop.mp4"
    _run([FFMPEG, "-y", "-loglevel", "error",
          "-stream_loop", "2", "-framerate", "12",
          "-i", win(tmp / "%05d.png"),
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", win(clip)])
    # sampled strip: rows = arms, cols = frames
    picks = [0, n // 4, n // 2, 3 * n // 4, n - 1]
    sw = 240
    strip = Image.new("RGB", (sw * len(picks), (sw * H // W + 24) * len(arms)), (12, 12, 16))
    d = ImageDraw.Draw(strip)
    for r_, a in enumerate(arms):
        y0 = r_ * (sw * H // W + 24)
        d.text((6, y0 + 4), ARMS[a][0], fill=(240, 230, 200))
        for c_, i in enumerate(picks):
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            if p.exists():
                im = Image.open(p).convert("RGB").resize((sw, sw * H // W))
                strip.paste(im, (c_ * sw, y0 + 24))
    spath = LAB / f"{journey}_dolly_AB_strip.png"
    strip.save(spath)
    print(f"\nlab deliverables:\n  {clip}\n  {spath}  ({n} frames x {len(arms)} arms)")
    return clip, spath


def sequence(journey, runs, frames, order):
    """One-after-another cut (Phil 2026-08-22: four at once is hard to judge — play the
    arms IN ORDER, full frame, each with a 1s label card, whole thing looped twice)."""
    LAB.mkdir(parents=True, exist_ok=True)
    tmp = LAB / f"{journey}_seq_frames"
    tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    W, H = 576, 1024
    n = 0
    for arm in order:
        if arm not in runs:
            continue
        card = Image.new("RGB", (W, H), (10, 10, 14))
        d = ImageDraw.Draw(card)
        d.text((W // 2 - 8 * len(ARMS[arm][0]), H // 2 - 20), ARMS[arm][0],
               fill=(240, 230, 200))
        for _ in range(12):                       # 1s label card at 12fps
            card.save(tmp / f"{n:05d}.png")
            n += 1
        for i in range(frames):
            p = Path(runs[arm]) / "build" / "frames" / f"{i:05d}.png"
            if not p.exists():
                break
            im = Image.open(p).convert("RGB")
            d = ImageDraw.Draw(im)
            d.text((12, 10), ARMS[arm][0], fill=(240, 230, 200))
            d.text((W - 90, 10), f"f{i:03d}", fill=(150, 160, 190))
            im.save(tmp / f"{n:05d}.png")
            n += 1
    clip = LAB / f"{journey}_dolly_SEQ.mp4"
    _run([FFMPEG, "-y", "-loglevel", "error",
          "-stream_loop", "1", "-framerate", "12", "-i", win(tmp / "%05d.png"),
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", win(clip)])
    print(f"sequential cut: {clip} ({n} frames x2 loops)")
    return clip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", default="squid_lantern")
    ap.add_argument("--cards", type=int, default=3,
                    help="render the first N cards of the render order")
    ap.add_argument("--arms", default="a0,a05,a10,a10p")
    ap.add_argument("--montage-only", action="store_true",
                    help="rebuild the clip/strip from the recorded runs file")
    ap.add_argument("--sequence-only", metavar="ARMORDER",
                    help="build only the one-after-another cut from recorded runs, "
                         "e.g. a0,a05,a10,a10p")
    a = ap.parse_args()

    frames, cfr = card_frames(a.journey, a.cards)
    bounds = [sum(cfr[:k]) for k in range(1, a.cards)]
    rec = LAB / f"{a.journey}_runs.json"
    if a.sequence_only:
        runs = json.loads(rec.read_text())["runs"]
        sequence(a.journey, runs, frames, [x.strip() for x in a.sequence_only.split(",")])
        return
    if a.montage_only:
        runs = json.loads(rec.read_text())["runs"]
    else:
        arms = [x.strip() for x in a.arms.split(",")]
        print(f"dolly_lab: {a.journey}, {a.cards} cards = {frames} frames/arm, "
              f"arms {arms} (~{frames * len(arms) * 19 / 60:.0f} min GPU)")
        # merge into the existing record — running one extra arm later must not clobber
        # the earlier arms' run mapping
        runs = json.loads(rec.read_text())["runs"] if rec.exists() else {}
        for arm in arms:
            runs[arm] = str(run_arm(a.journey, arm, frames))
        LAB.mkdir(parents=True, exist_ok=True)
        rec.write_text(json.dumps(
            {"journey": a.journey, "frames": frames, "runs": runs,
             "ts": time.strftime("%Y-%m-%d %H:%M")}, indent=2))
    montage(a.journey, runs, frames, bounds)


if __name__ == "__main__":
    main()
