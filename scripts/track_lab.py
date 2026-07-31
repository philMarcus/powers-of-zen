#!/usr/bin/env python3
"""TRACKER v3 lab — develop/verify the tracker against saved frames without re-rendering.

  selftest                                  exact-propagation check vs dive.zoom_transform
  bench <frame.png> <phrase>                time detect.locate (large-ft vs base-ft)
  sweep <frames_dir> <phrase> <a> <b> [st]  run detect.locate over frames a..b step st -> jsonl
  overlay <run_dir> [out.mp4]               draw build/track.jsonl over build/frames -> mp4

Run from the project root: python3 scripts/track_lab.py <cmd> ...
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "engine")
from PIL import Image, ImageDraw  # noqa: E402

import track  # noqa: E402

SCRATCH = Path("/tmp/claude-0/-mnt-c-Users-Phil-zoomer/f76349a0-798b-4536-8fa0-d370ecd103a5/scratchpad")


# ---------------------------------------------------------------- selftest ----
def selftest():
    """propagate() must land where zoom_transform actually puts a content point — including
    crop-clamped aims and rotation (the exact divergence that broke v6)."""
    import dive
    W, H = 576, 1024
    cases = [  # (dot fx, fy, z, rot_deg, aim cx, cy)
        (0.30, 0.40, 1.045, 0.0, 0.5, 0.5),
        (0.30, 0.40, 1.045, 0.0, 0.85, 0.15),   # aim hard-clamped by the crop window
        (0.70, 0.25, 1.010, 0.0, 0.60, 0.40),   # tiny zoom: almost no crop authority
        (0.70, 0.65, 1.200, 0.0, 0.65, 0.55),   # plunge-speed zoom
        (0.30, 0.40, 1.045, 0.15, 0.5, 0.5),    # the real per-frame rotation
        (0.35, 0.60, 1.100, 5.0, 0.55, 0.45),   # exaggerated rotation: catches a sign error
        (0.85, 0.80, 1.150, 0.15, 0.75, 0.70),  # near-edge dot, off-center aim
    ]
    import numpy as np
    worst = 0.0
    for fx, fy, z, rot, cx, cy in cases:
        img = Image.new("RGB", (W, H), "black")
        d = ImageDraw.Draw(img)
        px, py = fx * W, fy * H
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(255, 255, 255))
        out = dive.zoom_transform(img, z, rot, cx, cy)
        a = np.asarray(out.convert("L"), dtype=np.float32)
        if a.sum() < 1:
            print(f"  case {(fx, fy, z, rot, cx, cy)}: dot left the frame (bad test case)")
            continue
        ys, xs = np.mgrid[0:H, 0:W]
        mx, my = (xs * a).sum() / a.sum() / W, (ys * a).sum() / a.sum() / H
        tx, ty = track.propagate(fx, fy, z, rot, cx, cy, W, H)
        err = ((mx - tx) ** 2 + (my - ty) ** 2) ** 0.5 * W   # error in x-pixels
        worst = max(worst, err)
        print(f"  z={z:<5} rot={rot:<4} aim=({cx},{cy})  actual=({mx:.4f},{my:.4f}) "
              f"predicted=({tx:.4f},{ty:.4f})  err={err:.2f}px")
    print(f"selftest {'PASS' if worst < 3.0 else 'FAIL'} (worst {worst:.2f}px)")
    return worst < 3.0


# ------------------------------------------------------------------- bench ----
def bench(frame, phrase):
    import detect
    img = Image.open(frame).convert("RGB")
    for model in ("microsoft/Florence-2-large-ft", "microsoft/Florence-2-base-ft"):
        ts = []
        for k in range(3):
            t0 = time.time()
            b = detect.locate(img, phrase, model=model)
            ts.append(time.time() - t0)
            got = f"({b['cx']:.2f},{b['cy']:.2f}) {b['w']:.2f}x{b['h']:.2f}" if b else "none"
            print(f"  {model.split('/')[-1]} run{k}: {ts[-1]:.1f}s  -> {got}", flush=True)
        print(f"  {model.split('/')[-1]}: median {sorted(ts)[1]:.1f}s")


# ------------------------------------------------------------------- sweep ----
def sweep(frames_dir, phrase, a, b, step=4, model="microsoft/Florence-2-large-ft"):
    import detect
    src = Path(frames_dir)
    out = SCRATCH / f"sweep_{src.parts[-4]}_{phrase.replace(' ', '_')[:24]}.jsonl"
    rows = []
    t0 = time.time()
    for i in range(a, b + 1, step):
        p = src / f"{i:05d}.png"
        if not p.exists():
            continue
        bb = detect.locate(Image.open(p).convert("RGB"), phrase, model=model)
        row = {"i": i, "phrase": phrase}
        if bb:
            row["det"] = [round(bb["cx"], 3), round(bb["cy"], 3),
                          round(bb["w"], 3), round(bb["h"], 3)]
        rows.append(row)
        got = (f"({bb['cx']:.2f},{bb['cy']:.2f}) {bb['w']:.2f}x{bb['h']:.2f}"
               if bb else "-")
        print(f"  f{i:04d}: {got}", flush=True)
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    n = sum(1 for r in rows if "det" in r)
    print(f"{phrase!r}: {n}/{len(rows)} hits, {(time.time()-t0)/max(1,len(rows)):.1f}s/frame "
          f"-> {out}")


# ----------------------------------------------------------------- overlay ----
def overlay(run_dir, out_mp4=None):
    """Draw the per-frame track/aim/detections from build/track.jsonl over build/frames."""
    import subprocess
    import dive
    run = Path(run_dir)
    rows = {}
    for line in (run / "build" / "track.jsonl").read_text().splitlines():
        r = json.loads(line)
        rows[r["i"]] = r
    frames = sorted((run / "build" / "frames").glob("*.png"))
    out_dir = run / "build" / "track_overlay"
    out_dir.mkdir(exist_ok=True)
    for p in frames:
        i = int(p.stem)
        im = Image.open(p).convert("RGB")
        w, h = im.size
        d = ImageDraw.Draw(im)
        r = rows.get(i)
        if r:
            cx, cy = r["aim"]
            d.ellipse([cx * w - 6, cy * h - 6, cx * w + 6, cy * h + 6],
                      outline=(255, 255, 255), width=2)          # white ring = aim
            if r.get("track"):
                tx, ty = r["track"]
                s = max(0.04, r.get("size", 0)) * w / 2
                col = (0, 255, 90) if r.get("phase") == "object" else (0, 180, 255)
                d.line([tx * w - 14, ty * h, tx * w + 14, ty * h], fill=col, width=3)
                d.line([tx * w, ty * h - 14, tx * w, ty * h + 14], fill=col, width=3)
                if r.get("phase") == "object":
                    d.rectangle([tx * w - s, ty * h - s, tx * w + s, ty * h + s],
                                outline=col, width=2)            # green = locked box
            if r.get("det"):
                bx, by, bw, bh = r["det"]
                d.rectangle([(bx - bw / 2) * w, (by - bh / 2) * h,
                             (bx + bw / 2) * w, (by + bh / 2) * h],
                            outline=(255, 210, 0), width=2)      # yellow = raw detection
            if r.get("pending"):
                px, py = r["pending"]
                d.line([px * w - 9, py * h - 9, px * w + 9, py * h + 9],
                       fill=(255, 0, 200), width=3)              # magenta X = candidate
                d.line([px * w - 9, py * h + 9, px * w + 9, py * h - 9],
                       fill=(255, 0, 200), width=3)
            txt = f"f{i} {r.get('mode','')} {r.get('phase','')} {r.get('event') or ''}"
        else:
            txt = f"f{i}"
        d.text((8, 8), txt, fill=(255, 255, 255))
        im.save(out_dir / p.name)
    out_mp4 = out_mp4 or str(run / "track_overlay.mp4")
    subprocess.run([dive.FFMPEG, "-y", "-loglevel", "error", "-framerate", "12",
                    "-i", str(out_dir / "%05d.png"), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "20", out_mp4], check=True)
    print(f"overlay -> {out_mp4} ({len(frames)} frames, {len(rows)} logged)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "bench":
        bench(sys.argv[2], sys.argv[3])
    elif cmd == "sweep":
        sweep(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]),
              int(sys.argv[6]) if len(sys.argv) > 6 else 4)
    elif cmd == "overlay":
        overlay(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(__doc__)
