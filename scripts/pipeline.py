#!/usr/bin/env python3
"""Powers of Zen data model — the single source of truth.

outbox/pipeline.json : state of every video. Each video:
  {journey, model, cut(divein|zoomout), file, title, caption, yt_title, yt_desc,
   cameo, state, scheduled, platforms{tiktok/youtube/instagram: {status,url,ts}},
   created}
  state ∈ rendered → review → queued → live → failed
    rendered: exists, not yet reviewed
    review:   in production/, awaiting Phil's approval
    queued:   approved, ready/scheduled to post
    live:     posted to all platforms
    failed:   a post failed (see platforms + telemetry)

outbox/telemetry.jsonl : append-only event log {ts, event, ...} for the dashboard
  events: post, post_fail, render, render_fail, flag, promote, approve, schedule

Everything (dashboard, scheduler, poster.py, promote.py) reads/writes via this module.
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "outbox" / "pipeline.json"
TELEMETRY = ROOT / "outbox" / "telemetry.jsonl"
PLATFORMS = ["tiktok", "youtube", "instagram"]
STATES = ["rendered", "review", "queued", "live", "failed"]


def load():
    # explicit utf-8: captions have emoji, and Windows Python defaults to cp1252
    if PIPELINE.exists():
        return json.loads(PIPELINE.read_text(encoding="utf-8"))
    return {"meta": {"cadence": "2/day 08:00,18:00 EDT"}, "videos": []}


def save(data):
    data.setdefault("meta", {})["updated"] = _now()
    PIPELINE.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def telem(event, **fields):
    """Append one event to telemetry.jsonl (the dashboard activity/failure feed)."""
    TELEMETRY.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _now(), "event": event, **fields},
                           ensure_ascii=False) + "\n")


def read_telem(limit=200):
    if not TELEMETRY.exists():
        return []
    lines = TELEMETRY.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(x) for x in lines if x.strip()]


def cut_of(file):
    return "divein" if "_divein" in file else "zoomout"


def get(data, journey):
    return next((v for v in data["videos"] if v["journey"] == journey), None)


def next_to_post(data):
    """First video in state 'queued' (optionally past its scheduled time)."""
    now = _now()
    for v in data["videos"]:
        if v.get("state") == "queued" and (not v.get("scheduled") or v["scheduled"] <= now):
            return v
    return None


def blank_platforms():
    return {p: {"status": "pending", "url": "", "ts": ""} for p in PLATFORMS}


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":  # quick status dump
    d = load()
    from collections import Counter
    c = Counter(v.get("state") for v in d["videos"])
    print(f"pipeline.json: {len(d['videos'])} videos — " +
          ", ".join(f"{k}:{n}" for k, n in c.items()))
    nxt = next_to_post(d)
    print("next to post:", nxt["journey"] if nxt else "(none queued)")
