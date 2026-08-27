#!/usr/bin/env python3
"""camera_lab — ENGINE 3 Phase D gate: do the camera-vocabulary moves read as CAMERA
MOTION (revolution, not content churn) at full sharpness? (PLAN "Phase D", built
2026-08-27; the dolly_lab pattern applied to the move vocabulary.)

Arms are REAL dive.py runs over the first N cards of a journey's render order, same
seed, same schedule — the ONLY variable is the per-card `camera` plan, injected into a
DERIVED spec under output/camera_lab/specs/ (the catalog journey is never touched, and
nothing here enters the pipeline):
  base   no camera fields = the production engine exactly
  cam    the move plan under test (default: orbit 0.35 on card 1, spiral 0.5 on card 2
         — abyssal_chandelier's ember_nursery + young_star)

Deliverables (Phil's standing lab format — 12fps SLOW LOOPED, never a fast
once-through): side-by-side A/B loop, one-after-another sequence, sampled strip. The
cam arm's frames are annotated with the move active on that frame.

GATE: the revolve reads as the camera circling (near sweeps opposite far, the pivot
holds), no structure smear by card end, no added morph-feel vs base.

Usage:
  python3 scripts/camera_lab.py                          # abyssal_chandelier, 4 cards
  python3 scripts/camera_lab.py --journey X --cards 3 \
      --moves "card_a=orbit:0.4,card_b=spiral:0.5"
  python3 scripts/camera_lab.py --montage-only           # rebuild clips from records
"""
import argparse
import copy
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
import camera as _camera  # noqa: E402
import engine.dive as dive  # noqa: E402
import pipeline as pl  # noqa: E402
from score import win, FFMPEG, _run  # noqa: E402

LAB = ROOT / "output" / "camera_lab"
DEFAULT_MOVES = "ember_nursery=orbit:0.35,young_star=spiral:0.5"


def parse_moves(s):
    out = {}
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        card, mv = part.split("=")
        move, _, rate = mv.partition(":")
        out[card.strip()] = ({"move": move.strip(), "rate": float(rate)} if rate
                             else move.strip())
    return out


def derive_spec(journey, arm, moves):
    """Write the derived lab spec (renamed; cam arm carries the camera plan)."""
    spec = copy.deepcopy(json.loads(pl.journey_path(journey).read_text(encoding="utf-8")))
    spec["name"] = f"{journey}_cam{arm}"
    # arms must draw the SOURCE journey's scaffolds, or the A/B diverges at every
    # resolve window pre-roll regardless of the camera plan (found 2026-08-27)
    spec["scaffold_name"] = journey
    if moves:
        by_name = {r["name"]: r for r in spec["registers"]}
        for card, plan in moves.items():
            if card not in by_name:
                raise SystemExit(f"--moves names unknown card {card!r}")
            by_name[card]["camera"] = plan
        probs = _camera.validate(spec)
        if probs:
            raise SystemExit("camera plan fails validation: " + " | ".join(probs))
    sdir = LAB / "specs"
    sdir.mkdir(parents=True, exist_ok=True)
    p = sdir / f"{spec['name']}.json"
    p.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p, spec


def run_arm(spec_path, spec, frames):
    out_base = ROOT / "output" / spec["name"]
    before = {d.name for d in out_base.glob("v*")} if out_base.exists() else set()
    cmd = [sys.executable, str(ROOT / "engine" / "dive.py"), str(spec_path),
           "--frames", str(frames), "--no-video"]
    print(f"\n=== ARM {spec['name']}: {' '.join(cmd[2:])}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(f"{spec['name']} render failed (exit {r.returncode})")
    new = [d for d in out_base.glob("v*") if d.name not in before]
    if len(new) != 1:
        raise SystemExit(f"{spec['name']}: expected one new vN, found {new}")
    print(f"=== done in {(time.time() - t0) / 60:.1f} min -> {new[0]}", flush=True)
    return new[0]


def frame_label(sched, i):
    x = sched[i] if i < len(sched) else None
    if not x:
        return ""
    amt = x.get("orbit") or x.get("roll") or x.get("dolly") or x.get("tilt") or 0
    return f"{x['move']} {amt:+.2f}"


def montage(journey, runs, labels, scheds, frames, card_bounds):
    tmp = LAB / f"{journey}_ab_frames"
    tmp.mkdir(parents=True, exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    arms = list(runs)
    W, H, BAR = 576, 1024, 44
    n = 0
    for i in range(frames):
        cols = []
        for a in arms:
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            if not p.exists():
                cols = None
                break
            cols.append(Image.open(p).convert("RGB"))
        if cols is None:
            break
        out = Image.new("RGB", (W * len(cols), H + BAR), (12, 12, 16))
        d = ImageDraw.Draw(out)
        for k, (a, im) in enumerate(zip(arms, cols)):
            out.paste(im, (k * W, BAR))
            lbl = labels[a] + ("  ·  " + frame_label(scheds[a], i)
                               if scheds.get(a) else "")
            d.text((k * W + 12, 10), lbl.strip(" ·"), fill=(240, 230, 200))
        card = sum(1 for b in card_bounds if i >= b)
        d.text((out.width - 150, 10), f"f{i:03d} card {card}", fill=(150, 160, 190))
        out.save(tmp / f"{i:05d}.png")
        n += 1
    clip = LAB / f"{journey}_camera_AB_loop.mp4"
    _run([FFMPEG, "-y", "-loglevel", "error", "-stream_loop", "2", "-framerate", "12",
          "-i", win(tmp / "%05d.png"),
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", win(clip)])
    picks = [0, n // 4, n // 2, 3 * n // 4, n - 1]
    sw = 240
    strip = Image.new("RGB", (sw * len(picks), (sw * H // W + 24) * len(arms)), (12, 12, 16))
    d = ImageDraw.Draw(strip)
    for r_, a in enumerate(arms):
        y0 = r_ * (sw * H // W + 24)
        d.text((6, y0 + 4), labels[a], fill=(240, 230, 200))
        for c_, i in enumerate(picks):
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            if p.exists():
                strip.paste(Image.open(p).convert("RGB").resize((sw, sw * H // W)),
                            (c_ * sw, y0 + 24))
    spath = LAB / f"{journey}_camera_AB_strip.png"
    strip.save(spath)
    print(f"\nlab deliverables:\n  {clip}\n  {spath}  ({n} frames x {len(arms)} arms)")
    return clip


def sequence(journey, runs, labels, scheds, frames):
    tmp = LAB / f"{journey}_seq_frames"
    tmp.mkdir(parents=True, exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    W, H = 576, 1024
    n = 0
    for a in runs:
        card = Image.new("RGB", (W, H), (10, 10, 14))
        d = ImageDraw.Draw(card)
        d.text((W // 2 - 8 * len(labels[a]), H // 2 - 20), labels[a], fill=(240, 230, 200))
        for _ in range(12):
            card.save(tmp / f"{n:05d}.png")
            n += 1
        for i in range(frames):
            p = Path(runs[a]) / "build" / "frames" / f"{i:05d}.png"
            if not p.exists():
                break
            im = Image.open(p).convert("RGB")
            d = ImageDraw.Draw(im)
            lbl = labels[a] + ("  ·  " + frame_label(scheds[a], i)
                               if scheds.get(a) else "")
            d.text((12, 10), lbl.strip(" ·"), fill=(240, 230, 200))
            d.text((W - 90, 10), f"f{i:03d}", fill=(150, 160, 190))
            im.save(tmp / f"{n:05d}.png")
            n += 1
    clip = LAB / f"{journey}_camera_SEQ.mp4"
    _run([FFMPEG, "-y", "-loglevel", "error", "-stream_loop", "1", "-framerate", "12",
          "-i", win(tmp / "%05d.png"),
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", win(clip)])
    print(f"sequential cut: {clip}")
    return clip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journey", default="abyssal_chandelier")
    ap.add_argument("--cards", type=int, default=4)
    ap.add_argument("--moves", default=DEFAULT_MOVES,
                    help="cam-arm plan: card=move:rate,card2=move:rate")
    ap.add_argument("--montage-only", action="store_true")
    a = ap.parse_args()

    spec0 = json.loads(pl.journey_path(a.journey).read_text(encoding="utf-8"))
    fps = {**dive.DEFAULTS, **spec0.get("settings", {})}["fps"]
    cfr = dive.register_frame_counts(spec0, fps)
    frames = sum(cfr[:a.cards])
    bounds = [sum(cfr[:k]) for k in range(1, a.cards)]
    moves = parse_moves(a.moves)
    rec = LAB / f"{a.journey}_runs.json"

    specs = {}
    for arm, mv in (("base", {}), ("cam", moves)):
        _, spec = derive_spec(a.journey, arm, mv)
        specs[arm] = spec
    labels = {"base": "baseline",
              "cam": "camera: " + ", ".join(f"{c}={m['move'] if isinstance(m, dict) else m}"
                                            for c, m in moves.items())}
    scheds = {"cam": _camera.schedule(specs["cam"], fps)}

    if a.montage_only:
        runs = json.loads(rec.read_text())["runs"]
    else:
        print(f"camera_lab: {a.journey}, {a.cards} cards = {frames} frames/arm "
              f"(~{frames * 2 * 19 / 60:.0f} min GPU for both arms)")
        runs = json.loads(rec.read_text())["runs"] if rec.exists() else {}
        for arm in ("base", "cam"):
            spec_path = LAB / "specs" / f"{specs[arm]['name']}.json"
            runs[arm] = str(run_arm(spec_path, specs[arm], frames))
        LAB.mkdir(parents=True, exist_ok=True)
        rec.write_text(json.dumps({"journey": a.journey, "frames": frames,
                                   "moves": a.moves, "runs": runs,
                                   "ts": time.strftime("%Y-%m-%d %H:%M")}, indent=2))
    montage(a.journey, runs, labels, scheds, frames, bounds)
    sequence(a.journey, runs, labels, scheds, frames)


if __name__ == "__main__":
    main()
