"""comfy_fs — the engine's view of ComfyUI's OWN folders (2026-10-10).

ComfyUI's SaveImage / SaveAudio nodes write every result to ComfyUI/output/<subfolder>/ and
every /upload/image lands in ComfyUI/input/. The engine fetches each result over /view and
keeps its own copy (build/frames, output/music), so the ComfyUI copy is scratch — and until
today nothing deleted it: 91,074 frames (86 GB, every frame since July) plus 7.6 GB of
Florence uploads filled C: to 100% and killed a music pregen mid-write.

Two layers now: the engine unlinks each scratch file as soon as it has fetched it (here),
and `scripts/archive.py --comfy` sweeps whatever a crash left behind (age-guarded, nightly
via `--nightly`). Both are best-effort: a missing folder or a permission error is never a
render failure, and nothing outside the pipeline's own prefixes is ever touched.

CACHE NOTE: ComfyUI serves a byte-identical re-submission from its node cache WITHOUT
re-running the save node, so a deleted result file would 404 on the re-fetch. The frame
workflow can't repeat (the feed image changes every frame) and music takes carry their
seed, so their outputs are safe to drop at once. Florence detection CAN repeat on an
identical frame (detect.py names uploads by content hash for exactly that reuse) — its
mask outputs are therefore left to the sweep; only its uploads are dropped (detect
re-uploads before every submit, so a cached re-run never needs the old file)."""
import atexit
import os
import time
from pathlib import Path

COMFY_DIR = Path(os.environ.get("ZOOMER_COMFY_DIR", "/mnt/c/Users/Phil/ComfyUI/ComfyUI"))

# A file ComfyUI wrote less than ~a second ago refuses to unlink from WSL with PermissionError
# (errno 13 — the Windows side still holds a share lock on the fresh file; measured 2026-10-10:
# refused at +0.7 s, fine at +1.25 s). Sleeping per frame would tax every render, so a refused
# path is parked here and retried on the NEXT call (one frame later it is long free) and once
# more at interpreter exit. Anything still left is the nightly sweep's job.
_pending = []


def _try(p):
    try:
        p.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def flush_pending(retry_wait=0.0):
    """Retry every parked path once (after `retry_wait` seconds if given). Returns #still parked."""
    if _pending and retry_wait:
        time.sleep(retry_wait)
    _pending[:] = [q for q in _pending if not _try(q)]
    return len(_pending)


def _unlink(p):
    flush_pending()
    if _try(p):
        return True
    _pending.append(p)
    return False


def unlink_output(filename, subfolder="", kind="output"):
    """Delete one ComfyUI result file (as named in the /history entry). True if removed now;
    False = parked for the next call (see _pending). Never raises."""
    if not filename:
        return False
    base = COMFY_DIR / ("temp" if kind == "temp" else "output")
    return _unlink((base / subfolder / filename) if subfolder else (base / filename))


def unlink_input(name):
    """Delete one uploaded input (the name /upload/image returned). Same contract as above."""
    if not name:
        return False
    return _unlink(COMFY_DIR / "input" / name)


atexit.register(lambda: flush_pending(retry_wait=1.0))
