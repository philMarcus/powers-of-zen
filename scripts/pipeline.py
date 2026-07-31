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
STATES = ["rendered", "review", "queued", "live", "failed", "rejected"]
# "rejected": reviewed and turned down (kept for the record; no dashboard tab shows it, the
# scheduler never picks it). Re-promote by setting state back to "review".


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


def queued(data):
    """Queued videos in Phil's chosen order (order field asc, then insertion)."""
    q = [v for v in data["videos"] if v.get("state") == "queued"]
    return sorted(q, key=lambda v: v.get("order", 999))


def set_order(data, journeys):
    """Write CONTIGUOUS, distinct order (0..n-1) to `journeys` in the given sequence. Use this for
    reordering instead of swapping two videos' order values — swapping breaks when orders are
    missing or duplicated (they default to 999 / can collide), which silently no-ops a move."""
    for i, jn in enumerate(journeys):
        v = get(data, jn)
        if v:
            v["order"] = i


def move(data, journey, delta):
    """Move a queued video up (delta=-1) or down (delta=+1) in the post order; renormalizes all
    queued orders so the result is always exactly the intended sequence. Returns True if it moved."""
    seq = [v["journey"] for v in queued(data)]
    if journey not in seq:
        return False
    j = seq.index(journey)
    k = j + delta
    if not (0 <= k < len(seq)):
        return False
    seq[j], seq[k] = seq[k], seq[j]
    set_order(data, seq)
    return True


def next_to_post(data):
    """Top of the ordered queue whose scheduled time (if any) has arrived."""
    now = _now()
    for v in queued(data):
        if not v.get("scheduled") or v["scheduled"] <= now:
            return v
    return None


def blank_platforms():
    return {p: {"status": "pending", "url": "", "ts": ""} for p in PLATFORMS}


GPU_BUSY_PCT = 30  # utilization.gpu at/above this = something is really using the GPU


def gpu_busy():
    """True if the GPU is ACTUALLY under load — a dive render, seam repair, music gen, OR a game.
    Reads nvidia-smi utilization directly instead of matching process names: the old pgrep
    approach falsely tripped on any process whose *command line* merely mentioned the render
    scripts (e.g. a bash watcher with 'engine/dive.py' in its until-condition), so the flag never
    cleared after a render. Gate GPU-heavy work (music gen, local-VLM captioning) on this. Works
    from Windows (dashboard) via wsl.exe and from WSL directly; fails OPEN (returns False) so a
    smi hiccup never blocks the user."""
    import os
    import subprocess
    smi = "/mnt/c/Windows/System32/nvidia-smi.exe"  # WSL2 GPU passthrough exposes the Windows smi
    inner = f"'{smi}' --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1"
    try:
        argv = (["wsl.exe", "bash", "-lc", inner] if os.name == "nt" else ["bash", "-lc", inner])
        r = subprocess.run(argv, capture_output=True, text=True, timeout=8)
        vals = [int(x) for x in (r.stdout or "").split() if x.strip().isdigit()]
        return bool(vals) and vals[0] >= GPU_BUSY_PCT
    except Exception:
        return False


def paused_platforms(data):
    """Platforms the scheduler should NOT auto-post to (e.g. TikTok while a new-account
    review/spam-flag settles). Set via meta.paused_platforms in pipeline.json."""
    return list(data.get("meta", {}).get("paused_platforms", []))


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
