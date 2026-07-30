#!/usr/bin/env python3
"""Swap a production video's ugly loop seam for the repaired one — WITHOUT changing anything else
(same start point, same music track + sync, same cut, same model). "Replace only the seam frames."

Why this is empirical, not recomputed: the production video was phase-shifted so its loop seam
plays mid-video and it opens on an intentional macro-realm frame. That shift was baked in with
phase_shift.cut_time(), but the START_REGISTER config has since drifted, so recomputing the shift
would move the opening. Instead we MEASURE the exact frame-rotation the current production applied
to its render (residual ~0 confirms it's a clean rotation), then apply that SAME rotation to the
repaired render and re-attach the current production's own audio. The seam frames — repaired by
repair_seam.py — land at the same mid-video spot; everything else is byte-for-byte the same footage.

Prereq: repair_seam.py has already produced a fresh vN whose build/repair.json names the source
version. Non-destructive: the old production file is backed up under _seam_backup/ first.

Usage:  python3 scripts/reseam_production.py <journey>
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import dive           # noqa: E402
import pipeline as pl  # noqa: E402
import phase_shift as ps  # noqa: E402

FF = dive.FFMPEG
WORK = ROOT / "_seamwork"
WORK.mkdir(exist_ok=True)


def win(p):
    """Windows ffmpeg.exe can't open /mnt/c/... paths — map to C:/... (fwd slashes are fine)."""
    s = str(p)
    return "C:/" + s[len("/mnt/c/"):] if s.startswith("/mnt/c/") else s


def cut_basename(name, cut):
    return f"{name}.mp4" if cut == "zoomout" else f"{name}_divein.mp4"


def probe_fps_nframes(mp4):
    r = subprocess.run([FF, "-i", win(mp4)], capture_output=True, text=True)
    fps = float(re.search(r"(\d+(?:\.\d+)?) fps", r.stderr).group(1))
    # exact frame count
    d = WORK / "_probe"; d.mkdir(exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", win(mp4),
                    "-vf", "scale=32:32,format=gray", win(d / "%05d.png")], check=True)
    n = len(list(d.glob("*.png")))
    return fps, n


def decode_gray(mp4, size=96):
    d = WORK / ("dec_" + Path(mp4).stem); d.mkdir(exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", win(mp4),
                    "-vf", f"scale={size}:{size},format=gray", win(d / "%04d.png")], check=True)
    frs = sorted(d.glob("*.png"))
    return np.stack([np.asarray(Image.open(p), dtype=np.float32) for p in frs])


def measure_rotation(prod_mp4, orig_mp4):
    """R such that production[k] ~= original[(k+R) % N]; returns (R, residual, second_best)."""
    P = decode_gray(prod_mp4)
    U = decode_gray(orig_mp4)
    N = min(len(P), len(U)); P, U = P[:N], U[:N]
    diffs = [np.abs(P - np.roll(U, -r, axis=0)).mean() for r in range(N)]
    R = int(np.argmin(diffs))
    resid = diffs[R]
    second = sorted(diffs)[1]
    return R, resid, second, N


def main():
    journey = sys.argv[1]
    d = pl.load(); v = pl.get(d, journey)
    model, cut = v["model"], v["cut"]
    name = f"{journey}_{model}"
    base = ROOT / "output" / name
    prod = ROOT / v["file"]
    if not prod.exists():
        print(f"production file missing: {prod}"); sys.exit(1)

    # repaired = newest vN; its repair.json names the source version the production came from
    vers = sorted([p for p in base.glob("v[0-9]*") if p.name[1:].isdigit()],
                  key=lambda p: int(p.name[1:]))
    rep_dir = vers[-1]
    rj = json.loads((rep_dir / "build" / "repair.json").read_text())
    src_dir = base / rj["source"]
    cb = cut_basename(name, cut)
    U = src_dir / cb          # original assembled cut (pre-repair) — what production was rotated from
    Rep = rep_dir / cb        # repaired assembled cut (same footage + fixed seam)
    for p in (U, Rep):
        if not p.exists():
            print(f"missing cut file: {p}"); sys.exit(1)
    print(f"{journey}: model={model} cut={cut}\n  source(U)={U}\n  repaired(Rep)={Rep}\n  production(P)={prod}")

    R, resid, second, N = measure_rotation(prod, U)
    print(f"  measured rotation R={R}/{N} frames  residual={resid:.2f} (2nd-best {second:.2f})")
    if resid > 4.0:
        print(f"  !! residual {resid:.2f} too high — production is NOT a clean rotation of {rj['source']};"
              " aborting so we don't move the start point."); sys.exit(2)

    fps, nRep = probe_fps_nframes(Rep)
    if nRep != N:
        print(f"  !! frame-count mismatch (production {N} vs repaired {nRep}); aborting."); sys.exit(3)

    # rotate the repaired cut by EXACTLY R frames (frame-exact trim+concat — a seconds-based shift
    # rounds off by a frame, which offsets the whole video by ~1 frame and desyncs the copied audio)
    rot = WORK / f"{journey}_rot.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", win(Rep), "-filter_complex",
                    f"[0:v]trim=start_frame={R},setpts=PTS-STARTPTS[a];"
                    f"[0:v]trim=end_frame={R},setpts=PTS-STARTPTS[b];"
                    "[a][b]concat=n=2:v=1[v]",
                    "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", win(rot)],
                   check=True)
    print(f"  rotated repaired cut by exactly {R} frames")

    # keep the production's OWN audio (identical music + sync); just replace the video stream
    aud = WORK / f"{journey}_aud.m4a"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", win(prod), "-vn", "-c:a", "copy", win(aud)], check=True)
    newp = WORK / f"{journey}_new_production.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", win(rot), "-i", win(aud),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", "-shortest", win(newp)],
                   check=True)

    # VERIFY the start point is preserved — by which BODY frame each video opens on (immune to the
    # minterpolate jitter that makes raw frame MADs noisy: v2 was re-interpolated, so even identical
    # source frames differ ~30 MAD from v1's interpolation). We find the nearest source body frame.
    body = sorted((src_dir / "build" / "frames").glob("*.png"))
    def cc(a):  # center-crop away the corner counter overlay before matching
        h, w = a.shape[:2]; return a[int(h * .12):int(h * .88), int(w * .12):int(w * .88)]
    bodyimg = [cc(np.asarray(Image.open(p).convert("RGB").resize((96, 96)), dtype=np.float32)) for p in body]
    def opens_on(mp4):
        o = WORK / "_vf.png"
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", win(mp4),
                        "-frames:v", "1", "-vf", "scale=96:96", win(o)], check=True)
        f = cc(np.asarray(Image.open(o).convert("RGB"), dtype=np.float32))
        return int(np.argmin([np.abs(f - b).mean() for b in bodyimg]))
    new_open, old_open = opens_on(newp), opens_on(prod)
    print(f"  VERIFY start point: old production opens on body frame {old_open}, new opens on {new_open} "
          f"(match = same start ✓)")
    if abs(new_open - old_open) > 3:
        print("  !! start point moved — aborting."); sys.exit(4)

    # back up the TRUE original once (only-if-absent, so re-runs don't clobber it), then place the
    # new video (production + the chosen music candidate, which is a copy of the production file)
    bak = ROOT / "_seam_backup"; bak.mkdir(exist_ok=True)
    if not (bak / prod.name).exists():
        shutil.copy(prod, bak / prod.name)
    shutil.copy(newp, prod)
    chosen = v["music"]["chosen"]
    cand = next((c for c in v["music"]["candidates"] if c["id"] == chosen), None)
    if cand and cand.get("aligned"):
        ap = ROOT / cand["aligned"]
        if ap.exists():
            cbak = bak / f"{journey}__{ap.name}"   # journey-prefixed: candidate ids collide (choir…)
            if not cbak.exists():
                shutil.copy(ap, cbak)
            shutil.copy(newp, ap)
            print(f"  updated chosen candidate too: {cand['aligned']}")
    pl.telem("reseam", journey=journey, detail=f"R={R} resid={resid:.2f} open={new_open}(was {old_open})")
    print(f"  DONE -> {prod}  (backup in _seam_backup/)")


if __name__ == "__main__":
    main()
