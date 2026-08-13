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

Usage:
  python3 scripts/ig_stats.py            # snapshot + table (likes/view, joined with journey)
  python3 scripts/ig_stats.py --no-save  # print only, don't append to the log
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402
import zen_browser as zb  # noqa: E402

PROFILE = "https://www.instagram.com/powers.of.zen/"
STATS = pl.ROOT / "outbox" / "ig_stats.jsonl"


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
    a = ap.parse_args()

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
        goto(tab, PROFILE + "reels/", settle=4)
        for _ in range(6):
            tab.eval("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.2)
        n_tiles = tab.eval("""
            (() => {
              const seen = new Set(); let i = 0;
              for (const a of document.querySelectorAll('a[href*="/reel/"]')) {
                const code = (a.getAttribute('href') || '').replace(/\\/+$/, '').split('/').pop();
                if (!code || seen.has(code)) continue;
                seen.add(code); a.dataset.zzi = i++;
              }
              return i;
            })()
        """) or 0
        rows = []
        for i in range(min(n_tiles, a.max)):
            # the overlay is CSS :hover — synthetic JS mouse events don't trigger it, but a
            # TRUSTED pointer move via CDP Input does. Hover tile-to-tile like a human would.
            g = tab.eval(f"""
                (() => {{
                  const a = document.querySelector('a[data-zzi="{i}"]');
                  if (!a) return null;
                  a.scrollIntoView({{block: 'center'}});
                  const b = a.getBoundingClientRect();
                  return {{x: b.x + b.width / 2, y: b.y + b.height / 2,
                           code: a.getAttribute('href').replace(/\\/+$/, '').split('/').pop(),
                           views: (a.innerText || '').trim().split('\\n')[0] || null}};
                }})()
            """)
            if not g:
                continue
            tab.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=g["x"], y=g["y"])
            time.sleep(0.3)
            hov = tab.eval(f"(document.querySelector('a[data-zzi=\"{i}\"]').innerText || '')"
                           ".trim().split('\\n').filter(s => s.trim())") or []
            nums = [parse_count(x) for x in hov if parse_count(x) is not None]
            views = parse_count(g.get("views"))
            # hovered overlay shows [likes, comments]; if the text never changed we only saw
            # the view count again — treat as hover-miss (page-visit fallback fills it)
            likes = comments = None
            if nums and not (len(nums) == 1 and nums[0] == views):
                likes = nums[0]
                comments = nums[1] if len(nums) >= 2 else None
            rows.append({"ts": ts, "code": g["code"], "views": views,
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
        with open(STATS, "a", encoding="utf-8") as f:
            for r in rows:
                rr = {k: v for k, v in r.items() if k != "og"}
                f.write(json.dumps(rr, ensure_ascii=False) + "\n")
        print(f"\nsnapshot appended to {STATS.relative_to(pl.ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
