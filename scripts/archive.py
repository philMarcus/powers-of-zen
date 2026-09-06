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
  AUTO-PRUNE at archive time (Phil 2026-09-06): rebuildable artifacts
  (build/labeled + build/raw.mp4 + build/interp.mp4 — regenerable from build/frames via
  dive.assemble) are DELETED from a tree just before it moves, so they never reach E:
  and are gone from C: — roughly halves per-tree storage. build/frames stays (repairs
  read it). The same class inside KEPT trees is reported but left alone (those trees may
  still be edited); --prune-e cleans trees already on E: from before this existed.

Usage:
  python3 scripts/archive.py            # dry run: table + totals, touches nothing
  python3 scripts/archive.py --run      # prune regenerable + move the ARCHIVE class to E:
  python3 scripts/archive.py --prune-e  # delete regenerable already sitting in the E: archive
Every move/prune is appended to outbox/archive_manifest.jsonl.
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


# Regenerable build artifacts inside a render tree — rebuildable from build/frames via
# dive.assemble, so we DELETE rather than keep them (Phil 2026-09-06). Never touches
# build/frames, the final mp4, run.json, hero/resolve debug, or anything else.
REGEN_GLOBS = ("v*/build/labeled", "v*/build/raw.mp4", "v*/build/interp.mp4")


def prune_regenerable(tree):
    """Delete the regenerable artifacts in `tree`; return bytes freed."""
    freed = 0
    for g in REGEN_GLOBS:
        for q in tree.glob(g):
            try:
                if q.is_dir():
                    b, _ = du(q)
                    shutil.rmtree(q)
                    freed += b
                elif q.is_file():
                    freed += q.stat().st_size
                    q.unlink()
            except OSError as e:
                print(f"  prune skip {q}: {e}")
    return freed


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
    ap.add_argument("--prune-e", action="store_true",
                    help="delete regenerable artifacts already in the E: archive (moved there "
                         "before auto-prune existed); rebuildable from the build/frames on E:")
    a = ap.parse_args()

    if a.prune_e:
        root = DEST / "output"
        if not root.exists():
            sys.exit(f"no archive at {root}")
        total, ntrees = 0, 0
        for tree in sorted(root.iterdir()):
            if not tree.is_dir():
                continue
            freed = prune_regenerable(tree)
            if freed:
                ntrees += 1
                total += freed
                print(f"  {tree.name}: pruned {freed/1e9:.2f}G", flush=True)
                with open(MANIFEST, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "prune_e": tree.name, "bytes": freed}) + "\n")
        pl.telem("archive_prune_e", detail=f"pruned {total/1e9:.1f}G on E: ({ntrees} trees)")
        print(f"\npruned {total/1e9:.2f}G of regenerable across {ntrees} trees on E:")
        return

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
        if dst.exists():
            print(f"  destination exists — skipping {rel}")
            continue
        # AUTO-PRUNE (Phil 2026-09-06): drop rebuildable artifacts BEFORE the move so they
        # never reach E: and are gone from C: — halves per-tree storage. build/frames stays
        # (repairs read it); the source/dest file counts still match so verify passes.
        pruned = prune_regenerable(p)
        sb, sn = du(p)
        print(f"moving {rel} ({sb/1e9:.2f}G; pruned {pruned/1e9:.2f}G regenerable) ...", flush=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        # robocopy on the WINDOWS side: native NTFS->NTFS is several times faster than
        # two passes through WSL's 9p mount. /MOVE deletes the source after copying;
        # exit codes < 8 are success. Fallback to shutil if robocopy is unavailable.
        import subprocess
        def w(pth):
            return str(pth).replace("/mnt/c/", "C:\\").replace("/mnt/e/", "E:\\").replace("/", "\\")
        r = subprocess.run(["/mnt/c/Windows/System32/Robocopy.exe", w(p), w(dst),
                            "/E", "/MOVE", "/NFL", "/NDL", "/NJH", "/NJS", "/R:2", "/W:2"],
                           capture_output=True, text=True)
        if r.returncode >= 8:
            print(f"  robocopy failed rc {r.returncode} — source kept: {(r.stdout or '')[-200:]}")
            continue
        if p.exists() and any(p.rglob("*")):
            print(f"  source not fully moved — check {rel}")
            continue
        db, dn = du(dst)
        if (db, dn) != (sb, sn):
            print(f"  VERIFY note: {sn} files {sb}B -> {dn} files {db}B")
        moved += sb
        with open(MANIFEST, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "src": str(rel), "dst": str(dst), "bytes": sb,
                                "files": sn, "reason": why,
                                "pruned_bytes": pruned}) + "\n")
    pl.telem("archive", detail=f"moved {moved/1e9:.1f}G to E:")
    print(f"\narchived {moved/1e9:.2f}G to {DEST}")


if __name__ == "__main__":
    main()
