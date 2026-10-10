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
  python3 scripts/archive.py --comfy [--run]   # ComfyUI scratch (saved frames, uploads, masks,
                                               # music takes) -> DELETED; the 2026-10-10 86 GB
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

# COMFYUI SCRATCH (found 2026-10-10 with C: at 100%, 425 MB free): every frame the engine renders
# is SAVED by ComfyUI's SaveImage node into ComfyUI/output/zoomer/ and fetched over /view into
# the run's build/frames — the ComfyUI copy was never deleted (91,074 frames = 86.7 GB, every
# frame since July). Same story for the Florence detection uploads (input/det_*, input/cap_*),
# their masks (output/det_mask_*), the repair/A-B init uploads and the ACE-Step takes
# (output/zen_music/*, already copied to output/music/). All of it is the pipeline's own
# scratch, reproducible from nothing — DELETE, never archive. The age guard keeps anything a
# run in flight might still read; other subfolders of ComfyUI/output (megamastermind,
# seamlab, warp_depth, realm_*) belong to other projects / lab evidence and are never touched.
COMFY_DIR = Path("/mnt/c/Users/Phil/ComfyUI/ComfyUI")
COMFY_SCRATCH = [   # (subdir, glob, min age in minutes, what it is)
    ("output/zoomer", "frame_*", 180, "rendered frames (the copy is in build/frames)"),
    ("output", "det_mask_*", 180, "Florence detection masks"),
    ("output/zen_music", "*", 1440, "ACE-Step takes (the copy is in output/music)"),
    ("input", "det_*", 180, "Florence detection uploads"),
    ("input", "cap_*", 180, "Florence caption uploads"),
    ("input", "repair_init*", 180, "repair-tool init uploads"),
    ("input", "open_init*", 180, "replace_opening init uploads"),
    ("input", "ab_init*", 180, "seam-lab init uploads"),
    ("input", "zoomer_*", 7 * 1440, "named engine uploads (overwritten per frame)"),
]


def comfy_cleanup(run):
    """Delete the pipeline's ComfyUI scratch files older than their class's age guard.
    Returns bytes freed (0 on a dry run). One manifest row + one telem event per run."""
    now = time.time()
    rows = []
    for sub, pat, age, what in COMFY_SCRATCH:
        d = COMFY_DIR / sub
        if not d.is_dir():
            continue
        hits = []
        for q in d.glob(pat):
            try:
                st = q.stat()
                if q.is_file() and now - st.st_mtime > age * 60:
                    hits.append((q, st.st_size))
            except OSError:
                pass
        rows.append((sub, pat, age, what, hits, sum(b for _, b in hits)))
    tot = sum(r[5] for r in rows)
    print(f"{'COMFYUI SCRATCH (delete)':40} {'files':>7} {'size':>8}  what")
    for sub, pat, age, what, hits, b in rows:
        print(f"  {sub + '/' + pat:38} {len(hits):7d} {b/1e9:7.2f}G  {what} (> {age} min old)")
    print(f"  {'TOTAL':38} {sum(len(r[4]) for r in rows):7d} {tot/1e9:7.2f}G")
    if not run:
        print("\ndry run — nothing deleted. --comfy --run to delete.")
        return 0
    freed, nf, failed = 0, 0, 0
    for sub, pat, age, what, hits, b in rows:
        for q, sz in hits:
            try:
                q.unlink()
                freed += sz
                nf += 1
            except OSError:
                failed += 1
        if hits:
            print(f"  deleted {sub}/{pat}: {len(hits)} files, {b/1e9:.2f}G", flush=True)
            with open(MANIFEST, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "comfy_scratch": f"{sub}/{pat}", "files": len(hits),
                                    "bytes": b}) + "\n")
    pl.telem("cleanup_comfy", detail=f"deleted {freed/1e9:.1f}G ({nf} files"
                                     + (f", {failed} failed" if failed else "") + ") of ComfyUI scratch")
    print(f"\ndeleted {freed/1e9:.2f}G of ComfyUI scratch ({nf} files"
          + (f", {failed} failed" if failed else "") + ")")
    return freed


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
        # never move a tree something is still writing (a lab arm or a render in flight):
        # any file touched in the last 90 minutes keeps the whole tree on C: this pass
        try:
            newest = max((q.stat().st_mtime for q in p.rglob("*") if q.is_file()), default=0)
        except OSError:
            newest = time.time()
        if time.time() - newest < 90 * 60:
            keep.append((p, "recently written (in flight?)"))
            continue
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


def review_cleanup(run):
    r"""REVIEW CLASS (Phil 2026-10-04, C: at 99%): review/music/candidates/<journey>/ (5-10 aligned
    full-length takes per video, ~0.2-0.4G each set) and the review/ + review_divein/ cuts of
    videos that are LIVE / rejected / failed (or have no pipeline entry and no queued journey)
    move to E:\zoomer_archive\review_music_candidates\<journey> and ...\review_cuts\. The
    chosen track already lives in production/; nothing active (review / music / queued) moves.
    Loose probe files in review/music/*.mp4 count as orphans too."""
    import subprocess
    d = pl.load()
    vids = d["videos"] if isinstance(d, dict) else d
    if isinstance(vids, dict):
        vids = list(vids.values())
    state = {v["journey"]: v.get("state") for v in vids}
    queued = set(pl.jqueue(pl.jload()))

    def dead(j):
        st = state.get(j)
        if st in ACTIVE_STATES or j in queued:
            return False
        return st in ("live", "rejected", "failed") or st is None

    moves = []      # (src, dst, why)
    cand = ROOT / "review" / "music" / "candidates"
    if cand.exists():
        for p in sorted(cand.iterdir()):
            if p.is_dir() and dead(p.name):
                moves.append((p, DEST / "review_music_candidates" / p.name,
                              f"candidates of {state.get(p.name) or 'orphan'} video"))
    for p in sorted((ROOT / "review" / "music").glob("*.mp4")):
        moves.append((p, DEST / "review_music_probes" / p.name, "loose probe take"))
    for sub in ("review", "review_divein"):
        for p in sorted((ROOT / sub).glob("*.mp4")):
            j = p.stem
            # strip EVERY trailing cut token (…_ds_divein_shift_silent → journey): a _shift /
            # _silent companion of an ACTIVE video is its orig_file target and must stay
            changed = True
            while changed:
                changed = False
                for suf in ("_shift", "_silent", "_divein", "_review", "_ds", "_turbo"):
                    if j.endswith(suf):
                        j = j[: -len(suf)]
                        changed = True
            if dead(j):
                moves.append((p, DEST / "review_cuts" / sub / p.name,
                              f"cut of {state.get(j) or 'orphan'} video"))
    tot = 0
    print(f"{'REVIEW CLASS -> E:':52} {'size':>8}  reason")
    for src, dst, why in moves:
        b = du(src)[0] if src.is_dir() else src.stat().st_size
        tot += b
        print(f"  {src.relative_to(ROOT).as_posix():50} {b/1e9:6.2f}G  {why}")
    print(f"  {'TOTAL':50} {tot/1e9:6.2f}G   ({len(moves)} items)")
    if not run:
        print("\ndry run — nothing moved. --review --run to archive.")
        return
    if not DEST.parent.exists():
        sys.exit("E: drive not mounted at /mnt/e — aborting")

    def w(pth):
        return str(pth).replace("/mnt/c/", "C:\\").replace("/mnt/e/", "E:\\").replace("/", "\\")
    moved = 0
    for src, dst, why in moves:
        if dst.exists():
            dst = dst.with_name(f"{dst.stem}__{time.strftime('%Y%m%d_%H%M')}{dst.suffix}")
            print(f"  destination exists — archiving as {dst.name}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        sb = du(src)[0] if src.is_dir() else src.stat().st_size
        if src.is_dir():
            r = subprocess.run(["/mnt/c/Windows/System32/Robocopy.exe", w(src), w(dst),
                                "/E", "/MOVE", "/NFL", "/NDL", "/NJH", "/NJS", "/R:2", "/W:2"],
                               capture_output=True, text=True)
            ok = r.returncode < 8 and not src.exists()
        else:
            shutil.copy2(src, dst)
            ok = dst.exists() and dst.stat().st_size == sb
            if ok:
                src.unlink()
        if not ok:
            print(f"  FAILED {src.relative_to(ROOT)} — left in place", flush=True)
            continue
        moved += sb
        with open(MANIFEST, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "review_class": why,
                                "src": src.relative_to(ROOT).as_posix(), "dst": str(dst),
                                "bytes": sb}) + "\n")
        print(f"  moved {src.relative_to(ROOT).as_posix()} ({sb/1e9:.2f}G)", flush=True)
    pl.telem("archive_review", detail=f"moved {moved/1e9:.1f}G of review candidates/cuts to E:")
    print(f"\nmoved {moved/1e9:.2f}G to E:")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="actually move (default: dry run)")
    ap.add_argument("--review", action="store_true",
                    help="the REVIEW class instead: music candidates + review cuts of live/rejected/"
                         "failed/orphan videos -> E: (dry unless --run)")
    ap.add_argument("--nightly", action="store_true",
                    help="the whole cleanup, for real (night_batch runs this every night before "
                         "its gates): ComfyUI scratch deleted, then the review class and the "
                         "live/rejected/failed render trees moved to E:; prints C: free space")
    ap.add_argument("--comfy", action="store_true",
                    help="the COMFYUI SCRATCH class: the engine's saved frames / detection "
                         "uploads+masks / music takes left in ComfyUI's own folders (deleted, "
                         "never archived; dry unless --run)")
    ap.add_argument("--prune-e", action="store_true",
                    help="delete regenerable artifacts already in the E: archive (moved there "
                         "before auto-prune existed); rebuildable from the build/frames on E:")
    a = ap.parse_args()

    if a.nightly:
        # Phil 2026-10-10 ("we have a clean up process, we should run it, and automate it too"):
        # the three classes in the order that frees the most first; each prints its own table.
        a.run = True
        comfy_cleanup(True)
        print()
        review_cleanup(True)
        print()
    elif a.comfy:
        comfy_cleanup(a.run)
        return
    if a.review:
        review_cleanup(a.run)
        return
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
            # a journey re-rendered after its first archive: keep BOTH copies on E: under a dated
            # name instead of leaving the new tree on C: forever (7 trees sat that way 2026-10-10)
            dst = dst.with_name(f"{dst.name}__{time.strftime('%Y%m%d_%H%M')}")
            print(f"  destination exists — archiving as {dst.name}")
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
    free = shutil.disk_usage(str(ROOT)).free / 1e9
    print(f"C: free now: {free:.1f} GB")
    print(f"\narchived {moved/1e9:.2f}G to {DEST}")


if __name__ == "__main__":
    main()
