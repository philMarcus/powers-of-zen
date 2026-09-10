#!/usr/bin/env python3
"""YouTube stats snapshot — the YT counterpart to ig_stats.py.

Phil, 2026-09-10: "we take Instagram data, maybe we should collect YouTube data as well."
YT has quietly become a real channel (food_chain: 1095 YT views vs 240 on IG), so the
catalog needs the same per-video series on both platforms.

DELIBERATELY BROWSER-FREE. ig_stats has to drive CDP because IG hides counts behind a
hover overlay, but YouTube serves view/like counts in the watch page's own JSON — so this
is plain urllib: no Chrome, no CDP, no API key, no quota, and it can run while the poster
holds the browser. Video ids come from pipeline.json (platforms.youtube.url), so a video
is tracked the moment it goes live.

Writes one row per video per run to outbox/yt_stats.jsonl (append-only series, same shape
as ig_stats.jsonl: newest-wins on join). Unavailable/private videos are skipped, not
faked — a missing row is honest, a zero row would poison the series.

Usage:
  python3 scripts/yt_stats.py            # snapshot every live YT video
  python3 scripts/yt_stats.py --limit 5  # quick check
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

OUT = ROOT / "outbox" / "yt_stats.jsonl"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")


def _num(s):
    """'1,095' / '1.2K' / '3.4M' -> int."""
    s = (s or "").strip().replace(",", "")
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    if s and s[-1].upper() in mult:
        try:
            return int(float(s[:-1]) * mult[s[-1].upper()])
        except ValueError:
            return None
    try:
        return int(s)
    except ValueError:
        return None


def fetch(vid, timeout=30):
    """views / likes / comments / duration for one video id, or None if unavailable."""
    req = urllib.request.Request(f"https://www.youtube.com/watch?v={vid}",
                                 headers={"User-Agent": UA,
                                          "Accept-Language": "en-US,en;q=0.9"})
    try:
        html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"error": f"{type(e).__name__}: {str(e)[:60]}"}
    out = {}
    # views: the rendered "1,095 views" first (it is the public-facing number), then the
    # raw videoDetails counter. Skip zeros — an unplayed page renders viewCount 0.
    m = re.search(r'"viewCount":\{"videoViewCountRenderer":.*?"simpleText":"([\d,]+) views?"',
                  html)
    if m:
        out["views"] = _num(m.group(1))
    if not out.get("views"):
        for m in re.finditer(r'"viewCount":"(\d+)"', html):
            if int(m.group(1)) > 0:
                out["views"] = int(m.group(1))
                break
    m = re.search(r'"accessibilityText":"([\d,\.KMB]+) likes?"', html)
    if m:
        out["likes"] = _num(m.group(1))
    m = re.search(r'"commentCount":\{"simpleText":"([\d,\.KMB]+)"', html)
    if m:
        out["comments"] = _num(m.group(1))
    m = re.search(r'"lengthSeconds":"(\d+)"', html)
    if m:
        out["dur"] = int(m.group(1))
    if not out.get("views") and out.get("likes") is None:
        return {"error": "unavailable (private/removed?)"}
    return out


def live_videos():
    data = pl.load()
    vs = data["videos"] if isinstance(data, dict) and "videos" in data else data
    vs = vs if isinstance(vs, list) else list(vs.values())
    rows = []
    for v in vs:
        yt = (v.get("platforms") or {}).get("youtube") or {}
        url = (yt.get("url") or "").strip()
        if yt.get("status") != "live" or not url:
            continue
        vid = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        if vid:
            rows.append((v.get("journey", "?"), vid, yt.get("ts", "")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the newest N (quick check)")
    ap.add_argument("--delay", type=float, default=0.7, help="seconds between fetches")
    a = ap.parse_args()

    vids = live_videos()
    if a.limit:
        vids = vids[-a.limit:]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows, failed = [], 0
    for journey, vid, posted in vids:
        r = fetch(vid)
        if r.get("error") or not r.get("views"):
            failed += 1
            print(f"  {journey:24} {vid}  SKIP ({r.get('error', 'no views')})")
        else:
            row = {"ts": ts, "journey": journey, "video_id": vid, "posted": posted, **r}
            rows.append(row)
        time.sleep(a.delay)

    if rows:
        with OUT.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    rows.sort(key=lambda r: -(r.get("views") or 0))
    print(f"\n{'journey':26}{'views':>8}{'likes':>7}{'like%':>7}")
    for r in rows:
        lk = r.get("likes") or 0
        pct = f"{lk / r['views'] * 100:.1f}%" if r.get("views") else "?"
        print(f"{r['journey'][:25]:26}{r['views']:>8}{lk:>7}{pct:>7}")
    tot = sum(r.get("views") or 0 for r in rows)
    print(f"\n{len(rows)} videos, {tot:,} total YouTube views "
          f"({failed} skipped) -> {OUT.relative_to(ROOT)}")
    pl.telem("yt_stats", detail=f"{len(rows)} videos, {tot} views")


if __name__ == "__main__":
    main()
