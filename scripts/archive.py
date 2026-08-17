#!/usr/bin/env python3
"""archive — move finished work from the crowded C: drive to the E: archive.

Policy (Phil 2026-08-17, C: at 98%):
  ARCHIVE (move to E:\\zoomer_archive, fully recoverable):
    * output/<journey>/ render trees for videos whose state is live / rejected / failed
      (the posting files in production/ and review/ stay on C: — only render
      intermediates move; a future repair can read frames from E: or copy them back)
    * lab evidence dirs (tempo_lab, seam_lab, orbit_lab, resolve_lab)
    * orphan output dirs with no pipeline entry and no queued journey
  KEEP on C: (never archived):
    * review/music/queued-stage render trees (active repairs need local frames)
    * output/mascots (render input!), output/music (pregen tracks are referenced by path)
    * production/, production_alternates/, review*/, outbox/, journeys/, styles/
  DELETE-CLASS (identified but NOT touched — Phil approves separately):
    * build/labeled + build/raw.mp4 + build/interp.mp4 inside KEPT trees (regenerable
      from build/frames via dive.assemble)

Usage:
  python3 scripts/archive.py            # dry run: table + totals, touches nothing
  python3 scripts/archive.py --run     # move the ARCHIVE class (copy → verify → remove)
Every move is appended to outbox/archive_manifest.jsonl.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

DEST = Path("/mnt/e/zoomer_archive")
MANIFEST = ROOT / "outbox" / "archive_manifest.jsonl"
LAB_DIRS = ["tempo_lab", "seam_lab", "orbit_lab", "resolve_lab"]
KEEP_ALWAYS = {"mascots", "music", "realm_refs", "candidates"}
ACTIVE_STATES = {"review", "music", "queued", "rendered"}


def du(path):
    total = 0
    files = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
            files += 1
    return total, files


def classify():
    d = pl.load()
    vids = d["videos"] if isinstance(d, dict) else d
    if isinstance(vids, dict):
        vids = list(vids.values())
    state = {v["journey"]: v.get("state") for v in vids}
    jd = pl.jload()
    queued = set(pl.jqueue(jd))
    out = ROOT / "output"
    archive, keep = [], []
    for p in sorted(out.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        if name in KEEP_ALWAYS:
            keep.append((p, "always-keep"))
            continue
        if name in LAB_DIRS:
            archive.append((p, "lab evidence"))
            continue
        # map output dir -> journey (strip _ds/_turbo suffixes)
        j = name
        for suf in ("_ds", "_turbo"):
            if j.endswith(suf):
                j = j[: -len(suf)]
        st = state.get(j)
        if st in ("live", "rejected", "failed"):
            archive.append((p, f"video {st}"))
        elif st in ACTIVE_STATES:
            keep.append((p, f"video {st}"))
        elif j in queued:
            keep.append((p, "journey queued"))
        elif st is None:
            archive.append((p, "orphan (no pipeline entry)"))
        else:
            keep.append((p, st or "unknown"))
    return archive, keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="actually move (default: dry run)")
    a = ap.parse_args()

    archive, keep = classify()
    tot_a = 0
    print(f"{'ARCHIVE -> E:':40} {'size':>9}  reason")
    for p, why in archive:
        b, n = du(p)
        tot_a += b
        print(f"  {p.relative_to(ROOT).as_posix():38} {b/1e9:7.2f}G  {why}")
    print(f"  {'TOTAL':38} {tot_a/1e9:7.2f}G")
    tot_k = 0
    print(f"\n{'KEEP on C:':40}")
    for p, why in keep:
        b, n = du(p)
        tot_k += b
        print(f"  {p.relative_to(ROOT).as_posix():38} {b/1e9:7.2f}G  {why}")
    print(f"  {'TOTAL':38} {tot_k/1e9:7.2f}G")

    # delete-class report (not touched)
    dl = 0
    for p, _ in keep:
        for sub in ("labeled",):
            for q in p.glob(f"v*/build/{sub}"):
                b, _n = du(q)
                dl += b
        for q in list(p.glob("v*/build/raw.mp4")) + list(p.glob("v*/build/interp.mp4")):
            dl += q.stat().st_size
    print(f"\nDELETE-CLASS inside kept trees (regenerable; NOT touched): {dl/1e9:.2f}G")

    if not a.run:
        print("\ndry run — nothing moved. --run to archive.")
        return
    if not DEST.parent.exists():
        sys.exit("E: drive not mounted at /mnt/e — aborting")
    DEST.mkdir(parents=True, exist_ok=True)
    moved = 0
    for p, why in archive:
        rel = p.relative_to(ROOT)
        dst = DEST / rel
        sb, sn = du(p)
        print(f"moving {rel} ({sb/1e9:.2f}G) ...", flush=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            print(f"  destination exists — skipping {rel}")
            continue
        shutil.copytree(p, dst)
        db, dn = du(dst)
        if (db, dn) != (sb, sn):
            print(f"  VERIFY FAILED ({sn} files {sb}B -> {dn} files {db}B) — source kept")
            continue
        shutil.rmtree(p)
        moved += sb
        with open(MANIFEST, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "src": str(rel), "dst": str(dst), "bytes": sb,
                                "files": sn, "reason": why}) + "\n")
    pl.telem("archive", detail=f"moved {moved/1e9:.1f}G to E:")
    print(f"\narchived {moved/1e9:.2f}G to {DEST}")


if __name__ == "__main__":
    main()
