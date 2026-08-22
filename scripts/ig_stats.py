#!/usr/bin/env python3
"""Instagram performance snapshot for @powers.of.zen — likes/views per reel + followers.

Read-only: drives the zen Chrome profile (CDP :9222) in its OWN tab (opened for the run,
closed after), never touching the poster's platform tabs. Sources of truth:
  * profile og:description  -> follower count
  * reels grid tiles        -> view (play) count per reel
  * each reel's og:description -> "X likes, Y comments" + caption snippet
Reel -> journey mapping: pipeline platform urls, then telemetry post events, then caption
match. Appends one row per reel to outbox/ig_stats.jsonl (a snapshot log — run it daily/
whenever; likes-per-view trends come from diffing snapshots).

Runs three ways (Phil 2026-08-22 — count more often than the 19h post cadence):
  * after every posting run (poster.py calls it, warm Chrome)
  * scheduled at 12:00 + 00:00 (PowersOfZen-igstats-* tasks -> scheduled_ig_stats.bat)
  * by hand

Usage:
  python3 scripts/ig_stats.py            # snapshot + table (likes/view, joined with journey)
  python3 scripts/ig_stats.py --no-save  # print only, don't append to the log
  python3 scripts/ig_stats.py --force    # scrape even while a poster/gate run is in flight
"""
import argparse
import fcntl
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
import zen_browser as zb  # noqa: E402

PROFILE = "https://www.instagram.com/powers.of.zen/"
STATS = pl.ROOT / "outbox" / "ig_stats.jsonl"
LOCK = Path("/tmp/zoomer_ig_stats.lock")
GATE_LOCK = Path("/tmp/zoomer_post_gate.lock")   # held by post_gate for a whole poster run


def parse_count(s):
    """'1,234' / '12.3K' / '1.2M' -> int"""
    if s is None:
        return None
    s = s.strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([KM]?)$", s, re.I)
    if not m:
        return None
    v = float(m.group(1))
    return int(v * {"": 1, "K": 1e3, "M": 1e6}[m.group(2).upper()])


def og_description(tab):
    return tab.eval("document.querySelector('meta[property=\"og:description\"]')?.content || ''")


def open_scratch_tab():
    """A dedicated tab for the scrape, so the poster's platform tabs keep their pages."""
    zb.open_tab("about:blank")
    return zb.Tab(match="about:blank")


def close_tab(tab_ws_id):
    try:
        urllib.request.urlopen(f"http://localhost:{zb.PORT}/json/close/{tab_ws_id}", timeout=5)
    except Exception:
        pass


def goto(tab, url, settle=3.0):
    tab.cmd("Page.navigate", url=url)
    time.sleep(settle)


def cdp_up():
    try:
        urllib.request.urlopen(f"http://localhost:{zb.PORT}/json/version", timeout=5)
        return True
    except Exception:
        return False


def ensure_chrome():
    """Self-heal a down zen Chrome (same contract as poster.py's: the scheduled noon/
    midnight runs hit whatever state the machine is in — a reboot leaves CDP down)."""
    if cdp_up():
        return True
    print("Chrome CDP down — launching via scripts/start_chrome_zen.sh")
    try:
        subprocess.run(["bash", str(pl.ROOT / "scripts" / "start_chrome_zen.sh")],
                       cwd=str(pl.ROOT), timeout=30)
    except subprocess.TimeoutExpired:
        print("start_chrome_zen.sh hung past 30s — continuing to the CDP wait anyway")
    for _ in range(12):
        time.sleep(5)
        if cdp_up():
            pl.telem("igstats_chrome_selfheal")
            time.sleep(10)               # let the profile's tabs settle before we drive it
            return True
    print("Chrome CDP still not reachable on :9222 — no snapshot this run.")
    return False


def poster_in_flight():
    """True while post_gate/poster owns its lock. A scheduled scrape then just skips:
    the poster ends every run with its own snapshot, and two CDP drivers hovering the
    same Chrome at once is asking for flaky reads."""
    try:
        f = open(GATE_LOCK, "w")
    except OSError:
        return False
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(f, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        f.close()


def url_to_journey():
    """reel shortcode -> journey, from pipeline urls + telemetry post events."""
    m = {}
    d = pl.load()
    vids = d["videos"] if isinstance(d, dict) else d
    if isinstance(vids, dict):
        vids = list(vids.values())
    for v in vids:
        u = (v.get("platforms", {}).get("instagram", {}) or {}).get("url", "")
        if "/reel/" in (u or ""):
            m[u.rstrip("/").split("/")[-1]] = v["journey"]
    tf = pl.ROOT / "outbox" / "telemetry.jsonl"
    if tf.exists():
        for line in tf.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event") == "post" and e.get("platform") == "instagram" \
                    and "/reel/" in (e.get("detail") or ""):
                m[e["detail"].rstrip("/").split("/")[-1]] = e.get("journey")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--max", type=int, default=60, help="max reels to visit")
    ap.add_argument("--force", action="store_true",
                    help="scrape even while a poster/gate run is in flight")
    a = ap.parse_args()

    # one scrape at a time (two would interleave hovers + double-append rows)
    lockf = open(LOCK, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another ig_stats run is in flight — exiting")
        return
    if poster_in_flight() and not a.force:
        print("poster/gate run in flight — skipping (it snapshots when it finishes)")
        return
    if not ensure_chrome():
        return

    tabs_before = {t["id"] for t in zb.tabs()}
    tab = open_scratch_tab()
    tab_id = next((t["id"] for t in zb.tabs() if t["id"] not in tabs_before), None)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        # 1) followers
        goto(tab, PROFILE, settle=4)
        og = og_description(tab)
        fm = re.search(r"([\d,.KM]+)\s+Followers", og or "", re.I)
        followers = parse_count(fm.group(1)) if fm else None
        print(f"followers: {followers}   ({og[:80]!r})")

        # 2) reels grid: one pass, HOVER each tile (Phil's suggestion 2026-08-13) — the grid
        # overlay shows likes + comments instantly on hover, so nothing needs a page load.
        # Un-hovered tile text = play count; hovered = "likes\ncomments". React handles the
        # bubbling mouseover, so synthetic events are enough.
        # TAG INCREMENTALLY WHILE SCROLLING (2026-08-22): IG virtualizes the grid — the old
        # tag-once-after-scrolling pass only saw the tiles still mounted at the bottom (28 of
        # 43, and one run lost the NEWEST 7 — the exact reels fresh counts matter for). Each
        # tile's shortcode + absolute page-Y is recorded the first time it mounts; the hover
        # pass then scrolls to that Y and re-finds the anchor BY CODE, so a React remount
        # (which drops dataset tags) can't lose it.
        goto(tab, PROFILE + "reels/", settle=4)
        TAG = """
            (() => {
              window.__zz = window.__zz || {y: {}, order: []};
              for (const a of document.querySelectorAll('a[href*="/reel/"]')) {
                const code = (a.getAttribute('href') || '').replace(/\\/+$/, '').split('/').pop();
                if (!code || code in window.__zz.y) continue;
                window.__zz.y[code] = window.scrollY + a.getBoundingClientRect().y;
                window.__zz.order.push(code);
              }
              return window.__zz.order.length;
            })()
        """
        tab.eval(TAG)
        for _ in range(8):
            tab.eval("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.2)
            tab.eval(TAG)
        tiles = tab.eval("window.__zz.order.map(c => [c, window.__zz.y[c]])") or []
        find_by_code = """
                  const a = [...document.querySelectorAll('a[href*="/reel/"]')]
                      .find(el => (el.getAttribute('href') || '').includes(%r));
        """
        rows = []
        for code, y in tiles[: a.max]:
            # the overlay is CSS :hover — synthetic JS mouse events don't trigger it, but a
            # TRUSTED pointer move via CDP Input does. Hover tile-to-tile like a human would.
            tab.eval(f"window.scrollTo(0, Math.max(0, {y} - window.innerHeight / 2))")
            time.sleep(0.5)
            g = tab.eval("""
                (() => {
                  %s
                  if (!a) return null;
                  const b = a.getBoundingClientRect();
                  return {x: b.x + b.width / 2, y: b.y + b.height / 2,
                          views: (a.innerText || '').trim().split('\\n')[0] || null};
                })()
            """ % (find_by_code % code))
            if not g:
                rows.append({"ts": ts, "code": code, "views": None, "likes": None,
                             "comments": None, "followers": followers, "og": ""})
                continue          # tile unmounted even at its own Y — page-visit fallback
            tab.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=g["x"], y=g["y"])
            time.sleep(0.3)
            hov = tab.eval("""
                (() => {
                  %s
                  return ((a && a.innerText) || '').trim().split('\\n').filter(s => s.trim());
                })()
            """ % (find_by_code % code)) or []
            nums = [parse_count(x) for x in hov if parse_count(x) is not None]
            views = parse_count(g.get("views"))
            # hovered overlay shows [likes, comments]; if the text never changed we only saw
            # the view count again — treat as hover-miss (page-visit fallback fills it)
            likes = comments = None
            if nums and not (len(nums) == 1 and nums[0] == views):
                likes = nums[0]
                comments = nums[1] if len(nums) >= 2 else None
            rows.append({"ts": ts, "code": code, "views": views,
                         "likes": likes, "comments": comments,
                         "followers": followers, "og": ""})
        tab.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=4, y=4)
        print(f"reels on grid: {len(rows)} (trusted-hover pass, "
              f"{sum(1 for r in rows if r['likes'] is not None)} with likes)")

        # 3) page-visit FALLBACK — only for tiles whose hover gave nothing, and (below, after
        # mapping) for codes no pipeline/telemetry url explains: the reel page's og:description
        # carries likes + the caption snippet.
        jmap_early = url_to_journey()
        for r in rows:
            if r["likes"] is None or r["code"] not in jmap_early:
                goto(tab, f"https://www.instagram.com/reel/{r['code']}/", settle=2.5)
                og = og_description(tab) or ""
                r["og"] = og[:160]
                lm = re.search(r"([\d,.KM]+)\s+likes?,\s*([\d,.KM]+)\s+comments?", og, re.I)
                if lm:
                    if r["likes"] is None:
                        r["likes"] = parse_count(lm.group(1))
                    if r["comments"] is None:
                        r["comments"] = parse_count(lm.group(2))
    finally:
        if tab_id:
            close_tab(tab_id)

    # 4) map to journeys + report
    jmap = url_to_journey()
    caps = {}
    d = pl.load()
    vids = d["videos"] if isinstance(d, dict) else d
    if isinstance(vids, dict):
        vids = list(vids.values())
    for v in vids:
        if v.get("caption"):
            caps[v["journey"]] = v["caption"][:60].lower()
    for r in rows:
        r["journey"] = jmap.get(r["code"])
        if not r["journey"]:                      # caption fallback
            ogl = r["og"].lower()
            r["journey"] = next((j for j, c in caps.items() if c and c[:35] in ogl), None)

    print(f"\n{'journey':24} {'views':>8} {'likes':>6} {'like%':>6}  code")
    for r in sorted(rows, key=lambda r: -(r["views"] or 0)):
        pct = (100 * r["likes"] / r["views"]) if (r["likes"] and r["views"]) else None
        print(f"{(r['journey'] or '?'):24} {r['views'] or '?':>8} {r['likes'] or '?':>6} "
              f"{f'{pct:.1f}%' if pct else '?':>6}  {r['code']}")

    if not a.no_save:
        # a viewless row would SHADOW the reel's last good snapshot in the analyzer's
        # newest-wins join — save only rows that actually learned something
        keep = [r for r in rows if r.get("views") is not None]
        with open(STATS, "a", encoding="utf-8") as f:
            for r in keep:
                rr = {k: v for k, v in r.items() if k != "og"}
                f.write(json.dumps(rr, ensure_ascii=False) + "\n")
        print(f"\nsnapshot appended to {STATS.relative_to(pl.ROOT)} ({len(keep)} rows"
              + (f", {len(rows) - len(keep)} viewless dropped" if len(keep) < len(rows) else "")
              + ")")
        pl.telem("ig_stats", detail=f"{len(keep)} reels, followers {followers}")


if __name__ == "__main__":
    main()
