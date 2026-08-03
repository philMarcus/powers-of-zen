#!/usr/bin/env python3
"""make_candidate — preview (and, on approval, install) a repaired render for a video that is
ALREADY IN PRODUCTION (phase-shifted + music baked in).

Given a fresh vN made by replace_tail.py or replace_opening.py, this rotates its cut by the
production file's exact MEASURED frame rotation (empirical, like reseam_production — never a
recomputed phase shift, so the opening cannot drift) and re-attaches the production's own audio
stream. The result lands in output/candidates/<journey>_candidate.mp4 for Phil to judge;
NOTHING in production, pipeline.json, or review/ is touched.

On approval, re-run with --install: backs up the current production file to _seam_backup/
(only-if-absent), replaces it and the chosen music candidate's aligned copy, and logs telemetry
— the same swap contract reseam_production used.

Usage (repo root):
  python3 scripts/make_candidate.py mineral_heart                 # preview candidate
  python3 scripts/make_candidate.py mineral_heart --install      # approved -> swap into production
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import dive  # noqa: E402  (FFMPEG path)
import pipeline as pl  # noqa: E402
import reseam_production as rp  # noqa: E402


def cutfile(d, cut):
    hits = [p for p in d.glob("*.mp4")
            if p.stem.endswith("_divein") == (cut == "divein") and "review" not in p.stem]
    if not hits:
        sys.exit(f"no {cut} cut in {d}")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--new-version", help="repaired vN (default: newest with a run.json splice/"
                                          "replace_opening record)")
    ap.add_argument("--install", action="store_true",
                    help="approved: back up + swap the candidate into production")
    args = ap.parse_args()

    d = pl.load()
    v = pl.get(d, args.journey)
    if not v:
        sys.exit(f"no pipeline entry for {args.journey}")
    model, cut = v["model"], v["cut"]
    prod = ROOT / v["file"]
    if not prod.exists():
        sys.exit(f"production file missing: {prod}")

    base = ROOT / "output" / f"{args.journey}_{model}"
    if not base.exists():
        base = ROOT / "output" / args.journey
    vers = sorted([p for p in base.glob("v[0-9]*") if p.name[1:].isdigit()],
                  key=lambda p: int(p.name[1:]))
    if args.new_version:
        new_dir = base / args.new_version
    else:
        new_dir = None
        for p in vers:                      # newest vN that records a repair provenance
            rj = p / "run.json"
            if rj.exists():
                meta = json.loads(rj.read_text())
                if "splice" in meta or "replace_opening" in meta:
                    new_dir = p
    if not new_dir or not (new_dir / "run.json").exists():
        sys.exit(f"no repaired vN with run.json under {base} — run replace_tail/replace_opening first")
    meta = json.loads((new_dir / "run.json").read_text())
    src_name = (meta.get("splice") or {}).get("body_src") \
        or (meta.get("replace_opening") or {}).get("src")
    if not src_name:
        sys.exit(f"{new_dir}/run.json has no splice/replace_opening provenance")
    src_dir = base / src_name

    U, New = cutfile(src_dir, cut), cutfile(new_dir, cut)
    print(f"[cand] {args.journey}: cut={cut}\n  source={U}\n  new={New}\n  production={prod}",
          flush=True)

    R, resid, second, N = rp.measure_rotation(prod, U)
    print(f"[cand] rotation R={R}/{N} residual={resid:.2f} (2nd {second:.2f})", flush=True)
    if resid > 4.0:
        sys.exit(f"!! production is not a clean rotation of {src_name} (residual {resid:.2f})")
    fps, nNew = rp.probe_fps_nframes(New)
    if nNew != N:
        sys.exit(f"!! frame count mismatch: production {N} vs new {nNew}")

    rot = rp.WORK / f"{args.journey}_cand_rot.mp4"
    subprocess.run([rp.FF, "-y", "-loglevel", "error", "-i", rp.win(New), "-filter_complex",
                    f"[0:v]trim=start_frame={R},setpts=PTS-STARTPTS[a];"
                    f"[0:v]trim=end_frame={R},setpts=PTS-STARTPTS[b];"
                    "[a][b]concat=n=2:v=1[v]",
                    "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    rp.win(rot)], check=True)
    aud = rp.WORK / f"{args.journey}_cand_aud.m4a"
    subprocess.run([rp.FF, "-y", "-loglevel", "error", "-i", rp.win(prod), "-vn",
                    "-c:a", "copy", rp.win(aud)], check=True)
    out = ROOT / "output" / "candidates"
    out.mkdir(exist_ok=True)
    cand = out / f"{args.journey}_candidate.mp4"
    subprocess.run([rp.FF, "-y", "-loglevel", "error", "-i", rp.win(rot), "-i", rp.win(aud),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
                    "-shortest", rp.win(cand)], check=True)
    R2, resid2, _, _ = rp.measure_rotation(cand, New)
    print(f"[cand] verify: candidate is rotation {R2} of the new cut (want {R}), "
          f"residual {resid2:.2f}", flush=True)
    if R2 != R:
        sys.exit("!! candidate rotation mismatch")
    print(f"[cand] candidate -> {cand}", flush=True)

    if not args.install:
        print("[cand] preview only — production untouched. Approve with --install.")
        return

    bak = ROOT / "_seam_backup"
    bak.mkdir(exist_ok=True)
    if not (bak / prod.name).exists():
        shutil.copy(prod, bak / prod.name)
    shutil.copy(cand, prod)
    chosen = (v.get("music") or {}).get("chosen")
    candm = next((c for c in (v.get("music") or {}).get("candidates", [])
                  if c["id"] == chosen), None)
    if candm and candm.get("aligned"):
        ap_ = ROOT / candm["aligned"]
        if ap_.exists():
            cbak = bak / f"{args.journey}__{ap_.name}"
            if not cbak.exists():
                shutil.copy(ap_, cbak)
            shutil.copy(cand, ap_)
            print(f"[cand] updated chosen music candidate too: {candm['aligned']}")
    pl.telem("repair_install", journey=args.journey,
             detail=f"{new_dir.name} R={R} resid={resid:.2f}")
    print(f"[cand] INSTALLED -> {prod}  (backup in _seam_backup/)")


if __name__ == "__main__":
    main()
