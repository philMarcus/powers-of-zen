#!/usr/bin/env python3
"""post_gate — cadence-based posting (Phil 2026-08-17: every N hours, not twice daily).

An HOURLY Task Scheduler job runs this gate; it fires the real poster only when the
dashboard-managed clock says so:

  journeys.json settings:
    post_every_hours : cadence (default 19 — a bit more than daily, walks the time of day)
    post_next        : "YYYY-MM-DD HH:MM" of the next allowed fire (dashboard-editable)

After firing (or when the machine slept past several windows) post_next advances by
whole cadence steps until it is at least half a cadence in the future — a backlog never
causes burst posting (2026-09-28: the old "first step in the future" rule fired again
55 minutes after a catch-up post).
"""
import fcntl
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

FMT = "%Y-%m-%d %H:%M"
LOCK = Path("/tmp/zoomer_post_gate.lock")
POSTER_TIMEOUT = 90 * 60   # hard ceiling on one poster run; a hung browser can't wedge the gate


def log(msg):
    print(f"=== {time.strftime('%H:%M:%S')} {msg}", flush=True)


def main():
    # ONE gate at a time (2026-08-19): the hourly task and the dashboard's Post-now
    # button share this code path; without a lock a poster run outliving its hour let
    # the next gate fire a SECOND poster at the same still-queued video (double upload).
    lockf = open(LOCK, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("another gate/poster run is in flight — exiting (it owns the window)")
        return
    jd = pl.jload()
    s = jd["settings"]
    every = float(s.get("post_every_hours", 19))
    nxt_s = s.get("post_next")
    now = datetime.now()
    if not nxt_s:
        s["post_next"] = now.strftime(FMT)
        pl.jsave(jd)
        log(f"post_next initialized to now; cadence {every}h")
        nxt_s = s["post_next"]
    nxt = None
    for fmt in (FMT, "%Y-%m-%d %H:%M:%S", "%H:%M"):
        try:
            nxt = datetime.strptime(nxt_s.strip(), fmt)
            if fmt == "%H:%M":            # bare time = today
                nxt = now.replace(hour=nxt.hour, minute=nxt.minute,
                                  second=0, microsecond=0)
            break
        except ValueError:
            continue
    if nxt is None:
        log(f"post_next {nxt_s!r} unparseable — fix it in Settings (YYYY-MM-DD HH:MM)")
        return
    # DEAD-ZONE REMAP (Phil 2026-08-24): the VIRTUAL schedule keeps walking the clock in
    # 19h steps, but the ACTUAL post avoids the 01:00-06:59 audience trough:
    #   virtual in [01:00, 03:30) -> post at 21:00 the NIGHT BEFORE (pull earlier)
    #   virtual in [03:30, 07:00) -> post at 09:00 that morning    (push later)
    # The cadence clock ALWAYS advances from the VIRTUAL time (see the advance below), so
    # remaps never distort the walk.
    def effective(dt):
        t = dt.hour * 60 + dt.minute
        if 60 <= t < 210:
            return (dt - timedelta(days=1)).replace(hour=21, minute=0,
                                                    second=0, microsecond=0)
        if 210 <= t < 420:
            return dt.replace(hour=9, minute=0, second=0, microsecond=0)
        return dt
    eff = effective(nxt)
    if eff != nxt:
        log(f"dead-zone remap: virtual {nxt.strftime(FMT)} -> actual {eff.strftime(FMT)}")
    if now < eff:
        log(f"not yet — next post at {eff.strftime(FMT)}"
            + (f" (virtual {nxt.strftime(FMT)})" if eff != nxt else "")
            + f" (cadence {every}h)")
        return
    if 60 <= now.hour * 60 + now.minute < 420:
        # woke up INSIDE the trough (gate was down past its slot) — never post 01-07
        log("inside the dead zone now — holding until it ends")
        return
    # HOLD the window when nothing is queued (2026-08-17: the 18:00 window burned on an
    # empty queue and pushed the clock 19h — the gate must retry hourly until a video
    # exists, then the cadence counts from the ACTUAL post)
    target = pl.next_to_post(pl.load())
    if not target:
        log(f"gate open but nothing queued — holding the window, retrying next hour")
        return
    log(f"gate open (scheduled {nxt.strftime(FMT)}) — running poster")
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "poster.py")],
                           cwd=str(ROOT), timeout=POSTER_TIMEOUT)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = -1
        log(f"poster exceeded {POSTER_TIMEOUT // 60}min and was killed")
    # GROUND-TRUTH advance (2026-08-19): burn the 19h window only if the target video
    # actually went live somewhere — the poster exits 0 even when every platform flagged,
    # so rc alone can't be trusted. Anything else holds the window for an hourly retry
    # (a failed video leaves the queue, so the next retry posts the NEXT video).
    after = pl.get(pl.load(), target["journey"]) or {}
    went_live = any(p.get("status") == "live" and p.get("ts", "") >= now.strftime("%Y-%m-%d")
                    for p in after.get("platforms", {}).values())
    if rc != 0 or not went_live:
        pl.telem("post_gate", detail=f"rc {rc}, live={went_live} — window held for retry")
        log(f"post did not verify (rc {rc}, went_live={went_live}) — "
            "holding the window, retrying next hour")
        return
    # advance from the VIRTUAL scheduled time, not the actual post moment (Phil
    # 2026-08-24): a dead-zone remap must not shift the 19h walk. Catch up whole steps
    # if the machine slept past windows; always land ON the hour.
    nxt = nxt + timedelta(hours=every)
    # MINIMUM GAP (Phil 2026-09-28: two posts went out an hour apart after the queue had
    # been empty for two days — "catch up whole steps" landed on the first lattice point
    # in the future, 55 min after the post that had just gone out). Stay on the 19h lattice
    # (the walk keeps its phase) but never fire again sooner than HALF a cadence after the
    # post that actually happened: the next point must be >= now + every/2.
    floor_t = datetime.now() + timedelta(hours=every / 2)
    while nxt <= floor_t:
        nxt += timedelta(hours=every)
    nxt = (nxt + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
    jd = pl.jload()                      # re-read: poster runs for minutes
    jd["settings"]["post_next"] = nxt.strftime(FMT)
    pl.jsave(jd)
    pl.telem("post_gate", detail=f"fired (rc {rc}); next {nxt.strftime(FMT)}")
    log(f"next post: {nxt.strftime(FMT)}")


if __name__ == "__main__":
    main()
