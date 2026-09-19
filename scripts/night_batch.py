#!/usr/bin/env python3
"""night_batch — the nightly render batch (Task Scheduler, 01:30).

Renders the journey queue from outbox/journeys.json IN QUEUE ORDER, as many as fit
~render_budget_min of GPU time (tier templates retired 2026-08-26 — the queue's mix is
the nightly mix; the refill's Monte Carlo tier draw keeps that mix on target — see
pipeline.pick_tonight), each through engine/dive.py, ingests to the REVIEW queue,
captions, and updates the registry + telemetry. Phil wakes up to captioned videos in
Video Review.

Usage:
  python3 scripts/night_batch.py               # auto-pick (the scheduled form)
  python3 scripts/night_batch.py j1 j2 ...     # render exactly these (manual; no
                                               #   backpressure gate, no budget cap)
  python3 scripts/night_batch.py --dry-run     # show what tonight would do, then exit

Replaces render_batch.sh (now a thin wrapper). Fixes carried over from its postmortems:
queue_review BEFORE caption (queue_review CREATES the pipeline entry captions write
into); exit codes actually checked (a dead render no longer gets 'done -> REVIEW');
the already-rendered check searches output/<j>_ds/ AND output/<j>/ like queue_review.
Backpressure: when max_ready_videos are already approved-and-waiting to post, the
night is skipped — no point stockpiling past ~10 days of posts.
"""
import fcntl
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402
import queue_review  # noqa: E402

COMFY = "http://localhost:8188"
COMFY_START = "/mnt/c/Users/Phil/start_comfyui.sh"
# lock lives on WSL's own fs, not /mnt/c — flock over 9p/drvfs is unreliable
LOCK = Path("/tmp/zoomer_night_batch.lock")

LOGF = None


def log(msg):
    line = f"=== {time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    if LOGF:
        LOGF.write(line + "\n")
        LOGF.flush()


def run(argv, timeout=None):
    """Run a child with output into the batch log; return (rc, tail-of-output).
    Timeouts are MANDATORY protection (audit 2026-08-19): a ComfyUI that accepts the
    prompt but never finishes left dive polling forever, the batch holding its lock
    forever, and every later night exiting 'already running' — the 2026-08-08 class."""
    try:
        r = subprocess.run(argv, cwd=str(ROOT), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        if LOGF:
            LOGF.write((e.stdout or "") if isinstance(e.stdout, str) else "")
            LOGF.flush()
        return 124, f"timed out after {timeout}s"
    if LOGF:
        LOGF.write(r.stdout or "")
        LOGF.flush()
    tail = " | ".join((r.stdout or "").strip().splitlines()[-3:])
    return r.returncode, tail[-300:]


def comfy_up():
    import requests
    try:
        requests.get(f"{COMFY}/system_stats", timeout=3)
        return True
    except Exception:
        pass
    log("starting ComfyUI")
    # NEVER run start_comfyui.sh here: it ends in `exec tmux attach`, which blocks forever
    # in a scheduled run — the 2026-08-08 batch hung on that line holding the lock, and every
    # night after exited with "already running" until the reboot. Recreate the session
    # detached (same command the script uses); kill-session first so a dead pane from a
    # crashed ComfyUI can't swallow the start.
    run(["bash", "-lc",
         "tmux kill-session -t comfy 2>/dev/null; "
         "tmux new-session -d -s comfy -c /mnt/c/Users/Phil/ComfyUI && "
         "tmux send-keys -t comfy './python_embeded/python.exe -s ComfyUI/main.py "
         "--windows-standalone-build --listen 0.0.0.0' Enter"])
    for _ in range(60):
        try:
            requests.get(f"{COMFY}/system_stats", timeout=3)
            log("ComfyUI ready")
            return True
        except Exception:
            time.sleep(5)
    return False


def wait_gpu_free():
    """Don't fight a game/other job: wait up to 2h, then proceed anyway (matches the
    old batch's behavior — at 01:30 'busy after 2h' means something is wedged, and a
    slow render beats a silently skipped night). Two signals (audit 2026-08-19): real
    ComfyUI work via comfy_busy(), and HIGH raw utilization (>=60%) for a game — the
    old bare gpu_busy() (>=30%) false-positived on a dashboard left open overnight
    (Chrome decodes the looping previews on the GPU) and burned 2h of the budget."""
    for i in range(240):
        if not pl.comfy_busy() and not pl.gpu_busy(threshold=60):
            return
        if i == 0:
            log("GPU busy — waiting for it to free up")
        time.sleep(30)
    log("GPU still busy after 2h — rendering anyway")


def compile_queue(jd):
    """(ests, tiers) for every queued journey; uncompilable specs -> render_failed."""
    ests, tiers = {}, {}
    for name in pl.jqueue(jd):
        p = pl.journey_path(name)
        # retry once after a pause: a spec caught mid-write (an over-running refill
        # composer) or a drvfs hiccup must not become PERMANENT render_failed state
        for attempt in (0, 1):
            try:
                if not p:
                    raise FileNotFoundError("no journey file")
                frames = pl.journey_frames(name)
                cards = len(json.loads(p.read_text(encoding="utf-8"))["registers"])
                err = None
                break
            except Exception as e:
                err = e
                if attempt == 0:
                    time.sleep(5)
                    p = pl.journey_path(name)
        if err is not None:
            e = err
            log(f"{name}: spec does not compile — marking render_failed ({e})")
            jj = pl.jload()
            jj["journeys"].setdefault(name, {})
            jj["journeys"][name].update({"state": "render_failed",
                                         "note": f"does not compile: {e}", "ts": pl._now()})
            pl.jsave(jj)
            pl.telem("render_fail", journey=name, detail=f"compile: {e}")
            continue
        ests[name] = pl.est_render_sec(frames)
        tiers[name] = pl.tier_of(cards)
    return ests, tiers


def has_complete_render(journey):
    """A finished frame set under output/<j>_ds/ or output/<j>/ (same search
    queue_review uses — the old batch only looked at output/<j>/ and re-rendered
    skyfog-class journeys whose renders live in the _ds dir)."""
    try:
        total = pl.journey_frames(journey)
    except Exception:
        return False
    return queue_review.newest_complete(f"{journey}_ds", total,
                                        bases=[f"{journey}_ds", journey]) is not None


def render_one(journey, force=False, new_seed=True, from_card=None):
    """dive -> queue_review -> caption. Returns (ok, note). A force re-render gets a fresh
    base seed by default (same journey + same seed = the same frames again); new_seed=False
    keeps the journey's seed — for re-rendering through an ENGINE change. from_card=K is a
    PARTIAL re-render: keep cards 0..K-1's frames, regenerate from card K (dive --from-card)."""
    if has_complete_render(journey) and not (force or from_card):
        log(f"{journey}: complete render already exists — ingesting only")
    else:
        t0 = time.time()
        argv = ["python3", "engine/dive.py", str(pl.journey_path(journey))]
        _pm = pl.jload()["settings"].get("plate_mode")
        if _pm:
            # PLANET PLATE (2026-09-17): lab arm B for every planet-class card — see
            # PLAN "PLANET DESCENT". Journeys without a planet-class card are unaffected
            # (dive prints "no planet-class card in range").
            # --plate-intro plain: the grow/enter introductions (2026-09-18) stay out of
            # the nightly until Phil has judged the full-video test
            argv += ["--plate", str(_pm), "--plate-cn", "0", "--plate-void-gate",
                     "--plate-intro", str(pl.jload()["settings"].get("plate_intro", "plain"))]
        if from_card:
            argv += ["--from-card", str(from_card)]
        if (force or from_card) and new_seed:
            import random
            argv += ["--seed", str(random.randrange(1, 10**6))]
        if len(argv) > 3:
            log(f"{journey}: {' '.join(argv[3:])}")
        # ceiling = 2.5x the estimate (slowest observed render ran ~1.4x) + 30min slack;
        # a render past that is wedged, not slow — kill it and move to the next journey
        try:
            cap = int(pl.est_render_sec(pl.journey_frames(journey)) * 2.5) + 1800
        except Exception:
            cap = 4 * 3600
        rc, tail = run(argv, timeout=cap)
        if rc != 0:
            return False, f"dive failed: {tail}"
        log(f"{journey}: rendered in {time.time() - t0:.0f}s")
    # queue_review FIRST — it creates the pipeline entry caption.py writes into
    rc, tail = run(["python3", "scripts/queue_review.py", journey, "ds"], timeout=1800)
    if rc != 0:
        return False, f"queue_review failed: {tail}"
    rc, tail = run(["python3", "scripts/caption.py", journey], timeout=1800)
    if rc != 0:
        log(f"{journey}: caption.py exited {rc} ({tail}) — video is in Review uncaptioned")
    d = pl.load()
    v = pl.get(d, journey)
    capped = bool(v and (v.get("caption_options") or v.get("caption")))
    return True, ("" if capped else "in Review but UNCAPTIONED (Ollama down?)")


def main():
    global LOGF
    # UNKNOWN FLAGS ARE FATAL. This script used to ignore them, so `night_batch.py --help`
    # (2026-09-19, a probe) started a REAL batch and launched a render. Anything that is not
    # a known flag or a journey name stops here, before any work.
    _known = {"--dry-run", "--scheduled"}
    _unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _known]
    if _unknown:
        sys.exit(f"night_batch: unknown option {' '.join(_unknown)} — nothing was started.\n"
                 f"usage: night_batch.py [--dry-run] [--scheduled] [journey ...]")
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = "--dry-run" in sys.argv

    jd = pl.jload()
    s = jd["settings"]
    ready = len(pl.queued(pl.load()))

    if not args:  # auto-pick mode: backpressure + pause gates apply
        # MISSED-NIGHT GUARD (2026-08-28): the render task now has StartWhenAvailable, so a
        # 01:30 start missed by a reboot fires as soon as the machine is back — fine at
        # 01:40, NOT at 14:00 when Phil is at the keyboard. Scheduled runs (the .bat passes
        # --scheduled) refuse to start outside the night window; manual runs are unaffected.
        if "--scheduled" in sys.argv and not (0 <= time.localtime().tm_hour < 7):
            print("scheduled start outside the 00:00-07:00 night window (missed-night "
                  "catch-up after a reboot?) — skipping; tonight's 01:30 will render")
            if not dry:
                pl.telem("batch_skip", reason="catch-up outside night window")
            return
        if s.get("render_paused"):
            print("render_paused is set — skipping tonight")
            if not dry:
                pl.telem("batch_skip", reason="render_paused")
            return
        if ready >= s["max_ready_videos"]:
            print(f"backpressure: {ready} videos ready to post "
                  f"(max {s['max_ready_videos']}) — skipping tonight")
            if not dry:
                pl.telem("batch_skip", reason=f"backpressure {ready}")
            return
        ests, tiers = compile_queue(jd)
        picks, total = pl.pick_tonight(pl.jload(), ests)
        mode = "queue"
        if not picks:
            print("journey queue is empty — nothing to render "
                  "(queue journeys in the dashboard's Journeys tab)")
            if not dry:
                pl.telem("batch_skip", reason="empty queue")
            return
        print("tonight (queue order): " + " + ".join(
            f"{n}({tiers[n][0].upper()} ~{ests[n] // 60}min)" for n in picks)
            + f" = {total / 3600:.1f}h of {s['render_budget_min'] // 60}h budget")
    else:
        picks, mode = args, "manual"
        bad = [n for n in picks if not pl.journey_path(n)]
        if bad:
            sys.exit(f"no journey file for: {', '.join(bad)}")
        print(f"manual batch: {' + '.join(picks)}")
    if dry:
        print(f"(dry run — ready-to-post {ready}/{s['max_ready_videos']}, "
              f"queue depth {len(pl.jqueue(jd))}/{s['journey_queue_target']})")
        return

    # single instance — a manual run and the 01:30 task must never interleave renders
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another night_batch is already running — exiting")

    logpath = ROOT / "outbox" / f"night_batch_{time.strftime('%m%d_%H%M%S')}.log"
    LOGF = open(logpath, "w", encoding="utf-8")
    log(f"batch start [{mode}] — {len(picks)} journeys: {' '.join(picks)}")

    if not comfy_up():
        log("ABORT: ComfyUI never came up "
            f"(start it by hand: bash {COMFY_START})")
        pl.telem("render_fail", detail="ComfyUI never came up")
        sys.exit(1)
    wait_gpu_free()

    t0 = time.time()
    done, failed, notes = [], [], []
    for j in picks:
        log(f"--- {j} ---")
        entry = pl.jload()["journeys"].get(j, {})
        try:
            ok, note = render_one(j, force=entry.get("force", False),
                                  new_seed=entry.get("new_seed", True),
                                  from_card=entry.get("from_card"))
        except Exception as e:
            ok, note = False, f"{type(e).__name__}: {e}"
        jj = pl.jload()
        if ok:
            jj["journeys"].pop(j, None)   # decision consumed; state derives to 'rendered'
            done.append(j)
            if note:
                notes.append(f"{j}: {note}")
            pl.telem("render", journey=j, detail=note or "-> REVIEW (captioned)")
            log(f"{j} -> REVIEW" + (f" ({note})" if note else " (captioned)"))
        else:
            jj["journeys"].setdefault(j, {})
            jj["journeys"][j].update({"state": "render_failed", "note": note,
                                      "ts": pl._now()})
            failed.append(j)
            pl.telem("render_fail", journey=j, detail=note)
            log(f"{j} FAILED: {note}")
        pl.jsave(jj)

    # MUSIC PRE-GENERATION (Phil 2026-08-17): after all renders, one ACE-Step load makes +
    # ranks every new video's candidates against the unshifted cut, so approving in the
    # morning costs seconds of realignment instead of minutes of generation.
    for j in done:
        log(f"music pregen: {j}")
        rc, tail = run([sys.executable, str(ROOT / "scripts" / "music_gen.py"), j,
                        "--pregen"], timeout=3600)
        if rc != 0:
            log(f"  pregen failed (non-fatal): {tail[-160:]}")

    hrs = (time.time() - t0) / 3600
    summary = (f"batch done in {hrs:.1f}h — {len(done)} to Review"
               + (f", {len(failed)} failed ({', '.join(failed)})" if failed else "")
               + (f" · {'; '.join(notes)}" if notes else ""))
    log(summary)
    pl.telem("batch_done", detail=summary)
    try:      # release the ~7 GB SDXL stack so the morning GPU isn't full of last night
        import requests
        requests.post(f"{COMFY}/free", json={"unload_models": True, "free_memory": True},
                      timeout=10)
        log("ComfyUI models unloaded — VRAM freed")
    except Exception:
        pass
    log(f"log: {logpath.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
