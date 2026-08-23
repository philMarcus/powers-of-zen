#!/usr/bin/env python3
"""Meta Business Suite content-insights scrape — the per-reel metrics the reels-grid
can't see: reach, SHARES (= reposts/reshares, Phil's ask 2026-08-22), SAVES, follows
from the post, watch time, average play time.

Auth: Business Suite was linked to the IG account 2026-08-22 ("Continue with Instagram"
OAuth — no Facebook account involved); the session lives in the zen Chrome profile. If it
expires the scrape detects the login page and exits with telem ig_insights_login — re-run
the popup flow by hand once (business.facebook.com -> Continue with Instagram -> Log in
as powers.of.zen).

Collection: rows are read INCREMENTALLY while scrolling (same lesson as ig_stats' reels
grid — tables virtualize; collect-then-scroll loses rows). Caption -> journey mapping via
pipeline captions (rows carry no shortcode). Appends to outbox/ig_insights.jsonl; the
default "Last 28 days" range is accepted (insights lag ~1 day behind).

Runs from scheduled_ig_stats.bat (12:00 + 00:00) after ig_stats, and after every post.

Usage:
  python3 scripts/ig_insights.py            # snapshot + table
  python3 scripts/ig_insights.py --no-save
  python3 scripts/ig_insights.py --force    # scrape even while a poster run is in flight
"""
import argparse
import fcntl
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
import zen_browser as zb  # noqa: E402
from ig_stats import parse_count, ensure_chrome, poster_in_flight, close_tab  # noqa: E402

ASSET, BIZ = "1341441785714020", "1893578345013511"
URL = (f"https://business.facebook.com/latest/insights/content"
       f"?asset_id={ASSET}&business_id={BIZ}")
OUT = pl.ROOT / "outbox" / "ig_insights.jsonl"
LOCK = Path("/tmp/zoomer_ig_insights.lock")
COLS = ["caption", "date", "views", "reach", "viewers", "interactions", "likes",
        "comments", "shares", "saves", "link_clicks", "replies", "follows",
        "watch", "avg_play", "views_3s", "earnings"]
NUM = {"views", "reach", "viewers", "interactions", "likes", "comments", "shares",
       "saves", "link_clicks", "replies", "follows", "views_3s"}


def dur_s(s):
    """'2h 55m' / '13m 16s' / '6s' -> seconds (None for '--')."""
    if not s or not re.search(r"\d", s):
        return None
    total = 0
    for v, u in re.findall(r"(\d+)\s*([hms])", s):
        total += int(v) * {"h": 3600, "m": 60, "s": 1}[u]
    return total or None


def rows_js():
    """Visible data rows -> list of cell-text lists (header row filtered by caller)."""
    return """
        [...document.querySelectorAll('[role=row]')]
          .map(r => [...r.querySelectorAll('[role=cell],[role=gridcell],td,th')]
            .map(c => (c.innerText||'').trim()))
          .filter(cells => cells.length >= 10)
    """


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    lockf = open(LOCK, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another ig_insights run is in flight — exiting")
        return
    if poster_in_flight() and not a.force:
        print("poster/gate run in flight — skipping")
        return
    if not ensure_chrome():
        return

    tabs_before = {t["id"] for t in zb.tabs()}
    zb.open_tab("about:blank")
    tab = zb.Tab(match="about:blank")
    tab_id = next((t["id"] for t in zb.tabs() if t["id"] not in tabs_before), None)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    seen = {}
    try:
        tab.cmd("Page.navigate", url=URL)
        for _ in range(15):                       # heavy React app: wait for real rows
            time.sleep(3)
            if "loginpage" in (tab.eval("location.href") or ""):
                print("Business Suite session EXPIRED — relink by hand (see docstring)")
                pl.telem("ig_insights_login")
                return
            if tab.eval(f"({rows_js()}).length") or 0:
                break
        # collect incrementally while scrolling (virtualized table)
        stale = 0
        while stale < 3:
            batch = tab.eval(rows_js()) or []
            new = 0
            for cells in batch:
                r = dict(zip(COLS, cells + [""] * (len(COLS) - len(cells))))
                if r["caption"].lower().startswith("title"):
                    continue                       # header
                key = (r["caption"][:60], r["date"])
                if key in seen:
                    continue
                seen[key] = r
                new += 1
            stale = 0 if new else stale + 1
            tab.eval("""
                (() => {
                  const rs = document.querySelectorAll('[role=row]');
                  if (rs.length) rs[rs.length - 1].scrollIntoView({block: 'center'});
                })()
            """)
            time.sleep(1.2)
    finally:
        if tab_id:
            close_tab(tab_id)

    # caption -> journey (same fallback join as ig_stats; rows carry no shortcode)
    caps = {}
    d = pl.load()
    vids = d["videos"] if isinstance(d, dict) else d
    if isinstance(vids, dict):
        vids = list(vids.values())
    for v in vids:
        if v.get("caption"):
            caps[v["journey"]] = v["caption"][:35].lower()
    out = []
    for (cap, date), r in seen.items():
        row = {"ts": ts, "date": r["date"],
               "journey": next((j for j, c in caps.items() if c and c in cap.lower()), None)}
        for k in NUM:
            row[k] = parse_count(re.sub(r"[^\d,.KM]", "", r.get(k) or "") or None)
        row["watch_s"] = dur_s(r.get("watch"))
        row["avg_play_s"] = dur_s(r.get("avg_play"))
        row["caption_head"] = cap[:45]
        # virtualized rows sometimes mount before their numbers paint — a viewless copy
        # of a row learned nothing and would shadow good data in newest-wins joins
        if row["views"] is not None:
            out.append(row)

    print(f"{'journey':22} {'views':>6} {'reach':>6} {'shr':>4} {'sav':>4} {'fol':>4} "
          f"{'watch':>8} {'avg':>5}")
    for r in sorted(out, key=lambda r: -(r["views"] or 0)):
        w = f"{(r['watch_s'] or 0) // 60}m" if r["watch_s"] else "?"
        print(f"{(r['journey'] or '?'):22} {r['views'] or '?':>6} {r['reach'] or '?':>6} "
              f"{r['shares'] if r['shares'] is not None else '?':>4} "
              f"{r['saves'] if r['saves'] is not None else '?':>4} "
              f"{r['follows'] if r['follows'] is not None else '?':>4} "
              f"{w:>8} {str(r['avg_play_s'] or '?') + 's':>5}")
    if not a.no_save:
        with open(OUT, "a", encoding="utf-8") as f:
            for r in out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nappended {len(out)} rows to {OUT.relative_to(pl.ROOT)}")
        pl.telem("ig_insights", detail=f"{len(out)} posts")


if __name__ == "__main__":
    main()
