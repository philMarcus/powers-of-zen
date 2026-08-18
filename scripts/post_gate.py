#!/usr/bin/env python3
"""post_gate — cadence-based posting (Phil 2026-08-17: every N hours, not twice daily).

An HOURLY Task Scheduler job runs this gate; it fires the real poster only when the
dashboard-managed clock says so:

  journeys.json settings:
    post_every_hours : cadence (default 19 — a bit more than daily, walks the time of day)
    post_next        : "YYYY-MM-DD HH:MM" of the next allowed fire (dashboard-editable)

After firing (or when the machine slept past several windows) post_next advances by
whole cadence steps until it is in the future — a backlog never causes burst posting.
"""
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

FMT = "%Y-%m-%d %H:%M"


def log(msg):
    print(f"=== {time.strftime('%H:%M:%S')} {msg}", flush=True)


def main():
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
    if now < nxt:
        log(f"not yet — next post at {nxt.strftime(FMT)} (cadence {every}h)")
        return
    # HOLD the window when nothing is queued (2026-08-17: the 18:00 window burned on an
    # empty queue and pushed the clock 19h — the gate must retry hourly until a video
    # exists, then the cadence counts from the ACTUAL post)
    if not pl.next_to_post(pl.load()):
        log(f"gate open but nothing queued — holding the window, retrying next hour")
        return
    log(f"gate open (scheduled {nxt.strftime(FMT)}) — running poster")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "poster.py")],
                       cwd=str(ROOT))
    nxt = datetime.now() + timedelta(hours=every)
    # always land ON the hour (Phil): round to the nearest whole hour
    nxt = (nxt + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
    jd = pl.jload()                      # re-read: poster runs for minutes
    jd["settings"]["post_next"] = nxt.strftime(FMT)
    pl.jsave(jd)
    pl.telem("post_gate", detail=f"fired (rc {r.returncode}); next {nxt.strftime(FMT)}")
    log(f"next post: {nxt.strftime(FMT)}")


if __name__ == "__main__":
    main()
