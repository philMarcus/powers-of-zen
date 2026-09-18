#!/usr/bin/env python3
"""PLANET PLATE LAB (2026-09-17 — PLAN.md "PLANET DESCENT — THE PLATE PLAN").

Renders ONE planet card of an existing (non-live) render through engine/plate.py in each
lab arm, from the card's first frame through the next card's arrival, and cuts Phil's
standing lab deliverables (12fps SLOW LOOPED, judged one clip at a time — never a fast
once-through; plus a one-after-another SEQ cut, which he prefers over side-by-side):

  A  baseline  = the source render's own frames (no GPU)
  B  low       = plate + global denoise cap 0.32 (the cameo mechanism, simplest)
  C  mask      = plate + graded latent noise mask (void protected), scheduled denoise
  D  region    = C + regional prompts (orbit-view prompt inside the disc)

    python3 scripts/plate_lab.py sargasso_windrow --card 1 --src v1
    python3 scripts/plate_lab.py garnet_glass --card 5 --src v1 --arms mask,region

Every arm = `dive.py <journey> --from-card K --src-version vN --frames <card end + next
arrival + 8> --no-loop --plate ARM --plate-card K --no-video` — same seed as the source,
prefix frames byte-copied, so the arms differ ONLY in the plate. Output:
  output/plate_lab/<journey>/<journey>_plate_<arm>_loop.mp4   (one per arm, looped x3)
  output/plate_lab/<journey>/<journey>_plate_SEQ.mp4          (A, B, C, D one after another)
  output/plate_lab/<journey>/<journey>_plate_strip.png        (sampled frames, all arms)
  output/plate_lab/<journey>/<journey>_plate_gate.json        (measured gate numbers)

GATE (measured, PLAN): disc radius per frame tracks the schedule; void pixels stay void
(edge density / luminance outside the disc flat across the card); the boundary lands on the
surface. The clip is what Phil judges; the numbers say whether the mechanism did what it
claims before taste enters.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import dive  # noqa: E402
import grammar  # noqa: E402
from score import win, FFMPEG, _run  # noqa: E402

LAB = ROOT / "output" / "plate_lab"
ARMS = {"low": "B  plate + denoise cap 0.32",
        "mask": "C  plate + graded noise mask",
        "region": "D  mask + regional prompts",
        "live": "E  live arrival: IPA void hold, disc-only cap, globe fades in"}


def card_layout(spec, card):
    fps = {**dive.DEFAULTS, **spec.get("settings", {})}["fps"]
    cfr = dive.register_frame_counts(spec, fps)
    N = sum(cfr[:card])
    F = cfr[card]
    F_next = cfr[card + 1] if card + 1 < len(cfr) else cfr[0]
    fa_next = max(2, round(F_next * 0.25))
    end = N + F + F_next + 4      # the plate spans the bar line: show the whole next card
    return N, F, fa_next, end


def run_arm(journey, card, src, arm, end, extra):
    argv = [sys.executable, str(ROOT / "engine" / "dive.py"), str(ROOT / "journeys" / f"{journey}.json"),
            "--from-card", str(card), "--src-version", src, "--frames", str(end), "--no-loop",
            "--plate", arm, "--plate-card", str(card), "--no-video"] + extra
    print(f"\n[{arm}] {' '.join(argv[2:])}", flush=True)
    t0 = time.time()
    log = LAB / journey / f"dive_{arm}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as fh:
        r = subprocess.run(argv, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"[{arm}] dive failed (rc {r.returncode}) — see {log}")
    base = ROOT / "output" / f"{journey}_plate{arm}"
    vs = sorted([d for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                key=lambda d: int(d.name[1:]))
    run = vs[-1]
    print(f"[{arm}] done in {time.time() - t0:.0f}s -> {run}", flush=True)
    return run


def measure(run_dir, N, end, plate_rows):
    """Gate numbers per frame: disc radius (from plate.jsonl schedule), void edge density
    and luminance OUTSIDE the scheduled disc, and the same inside."""
    rows = []
    by_i = {r["i"]: r for r in plate_rows}
    for i in range(N, end):
        p = run_dir / "build" / "frames" / f"{i:05d}.png"
        if not p.exists():
            break
        a = np.asarray(Image.open(p).convert("L"), np.float32) / 255.0
        H, W = a.shape
        gy, gx = np.gradient(a)
        edge = np.sqrt(gx * gx + gy * gy)
        r = by_i.get(i)
        if r and not r.get("covered"):
            yy, xx = np.mgrid[0:H, 0:W]
            d = np.sqrt((xx - r["tx"] * W) ** 2 + (yy - r["ty"] * H) ** 2)
            R = r["size"] * W / 2
            out = d > R * 1.08
            ins = d < R * 0.92
            rows.append({"i": i, "size": r["size"], "covered": False,
                         "void_lum": round(float(a[out].mean()), 4) if out.any() else None,
                         "void_edge": round(float(edge[out].mean()), 4) if out.any() else None,
                         "disc_lum": round(float(a[ins].mean()), 4) if ins.any() else None,
                         "disc_edge": round(float(edge[ins].mean()), 4) if ins.any() else None})
        else:
            rows.append({"i": i, "size": r["size"] if r else None,
                         "covered": bool(r and r.get("covered")),
                         "lum": round(float(a.mean()), 4), "edge": round(float(edge.mean()), 4)})
    return rows


def clip_from_frames(frames_dir, lo, hi, label, out_mp4, tmp, loops=2, start_n=0):
    """Write labelled frames [lo, hi) into tmp starting at index start_n; return next n."""
    n = start_n
    for i in range(lo, hi):
        p = frames_dir / f"{i:05d}.png"
        if not p.exists():
            break
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, im.width, 30), fill=(10, 10, 14))
        d.text((12, 8), label, fill=(240, 230, 200))
        d.text((im.width - 90, 8), f"f{i:03d}", fill=(150, 160, 190))
        im.save(tmp / f"{n:05d}.png")
        n += 1
    if out_mp4 is not None:
        _run([FFMPEG, "-y", "-loglevel", "error", "-stream_loop", str(loops), "-framerate", "12",
              "-i", win(tmp / "%05d.png"),
              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", win(out_mp4)])
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--card", type=int, required=True, help="render-order card index (the planet card)")
    ap.add_argument("--src", default=None, help="source vN with the prefix frames (default newest)")
    ap.add_argument("--arms", default="low,mask,region")
    ap.add_argument("--pre", type=int, default=6, help="frames of run-in before the card in the clips")
    ap.add_argument("--extra", default="", help="extra dive args (quoted), e.g. '--plate-end 2.0'")
    ap.add_argument("--clips-only", action="store_true", help="skip rendering; rebuild clips from existing runs")
    ap.add_argument("--tag", default="", help="suffix for the deliverable names (e.g. v3)")
    args = ap.parse_args()

    spec = json.loads((ROOT / "journeys" / f"{args.journey}.json").read_text(encoding="utf-8"))
    N, F, fa_next, end = card_layout(spec, args.card)
    src_base = ROOT / "output" / args.journey
    vs = sorted([d for d in src_base.glob("v[0-9]*") if d.name[1:].isdigit()],
                key=lambda d: int(d.name[1:]))
    src = args.src or vs[-1].name
    src_dir = src_base / src
    assert (src_dir / "build" / "frames" / f"{end - 1:05d}.png").exists(), \
        f"{src_dir} lacks frames through {end - 1}"
    print(f"{args.journey} card {args.card}: frames {N}..{N + F - 1} (+ the next card +4) "
          f"-> render to {end}; source {src}")
    lab = LAB / args.journey
    lab.mkdir(parents=True, exist_ok=True)
    extra = args.extra.split() if args.extra else []

    runs = {"baseline": src_dir}
    for arm in [a for a in args.arms.split(",") if a]:
        if args.clips_only:
            base = ROOT / "output" / f"{args.journey}_plate{arm}"
            vv = sorted([d for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                        key=lambda d: int(d.name[1:]))
            if vv:
                runs[arm] = vv[-1]
            continue
        runs[arm] = run_arm(args.journey, args.card, src, arm, end, extra)

    # ── deliverables ──
    labels = {"baseline": "A  baseline (source render)", **ARMS}
    lo, hi = max(0, N - args.pre), end
    gate = {}
    for arm, run in runs.items():
        tmp = lab / f"_tmp_{arm}"
        tmp.mkdir(exist_ok=True)
        for old in tmp.glob("*.png"):
            old.unlink()
        clip = lab / f"{args.journey}_plate_{arm}{('_' + args.tag) if args.tag else ''}_loop.mp4"
        clip_from_frames(run / "build" / "frames", lo, hi, labels[arm], clip, tmp, loops=2)
        print(f"  {clip}")
        plog = run / "build" / "plate.jsonl"
        rows = [json.loads(l) for l in plog.read_text().splitlines() if l.strip()] \
            if plog.exists() else []
        gate[arm] = measure(run, N, end, rows)
    # sequential cut: A, B, C, D one after another with a title card each
    tmp = lab / "_tmp_seq"
    tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    n = 0
    for arm, run in runs.items():
        card = Image.new("RGB", (576, 1024), (10, 10, 14))
        ImageDraw.Draw(card).text((40, 500), labels[arm], fill=(240, 230, 200))
        for _ in range(12):
            card.save(tmp / f"{n:05d}.png")
            n += 1
        n = clip_from_frames(run / "build" / "frames", lo, hi, labels[arm], None, tmp, start_n=n)
    seq = lab / f"{args.journey}_plate_SEQ{('_' + args.tag) if args.tag else ''}.mp4"
    _run([FFMPEG, "-y", "-loglevel", "error", "-stream_loop", "1", "-framerate", "12",
          "-i", win(tmp / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
          win(seq)])
    print(f"  {seq}")
    # strip: every 3rd frame of the card + arrival, all arms stacked
    picks = list(range(N, end, 3))
    sw = 120
    sh = sw * 1024 // 576
    strip = Image.new("RGB", (sw * len(picks), (sh + 16) * len(runs)), (12, 12, 16))
    d = ImageDraw.Draw(strip)
    for r_, (arm, run) in enumerate(runs.items()):
        y0 = r_ * (sh + 16)
        d.text((4, y0 + 2), labels[arm], fill=(240, 230, 200))
        for c_, i in enumerate(picks):
            p = run / "build" / "frames" / f"{i:05d}.png"
            if p.exists():
                th = Image.open(p).convert("RGB").resize((sw, sh))
                strip.paste(th, (c_ * sw, y0 + 16))
                dd = ImageDraw.Draw(strip)
                dd.text((c_ * sw + 2, y0 + 16), str(i), fill=(255, 255, 0))
                if i >= N + F:
                    dd.rectangle((c_ * sw, y0 + 16 + sh - 6, c_ * sw + sw, y0 + 16 + sh), fill=(200, 0, 0))
    sp = lab / f"{args.journey}_plate_strip{('_' + args.tag) if args.tag else ''}.png"
    strip.save(sp)
    print(f"  {sp}")
    (lab / f"{args.journey}_plate_gate{('_' + args.tag) if args.tag else ''}.json").write_text(json.dumps(
        {"journey": args.journey, "card": args.card, "src": src, "N": N, "F": F, "end": end,
         "runs": {a: str(r) for a, r in runs.items()}, "gate": gate}, indent=1))
    # one-line gate summary per arm
    for arm, rows in gate.items():
        pre = [r for r in rows if not r.get("covered") and r.get("void_edge") is not None]
        if pre:
            ve = [r["void_edge"] for r in pre]
            vl = [r["void_lum"] for r in pre]
            print(f"  gate {arm:9s}: void edge {ve[0]:.4f} -> {ve[-1]:.4f} (max {max(ve):.4f}), "
                  f"void lum {vl[0]:.3f} -> {vl[-1]:.3f}; covered from frame "
                  f"{next((r['i'] for r in rows if r.get('covered')), None)}")


if __name__ == "__main__":
    main()
