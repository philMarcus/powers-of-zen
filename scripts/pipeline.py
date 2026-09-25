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

outbox/journeys.json : journey registry (render queue + settings) — see the journey
  registry section below. night_batch.py picks from it; the dashboard edits it.

Everything (dashboard, scheduler, poster.py, promote.py, night_batch.py) reads/writes
via this module.
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "outbox" / "pipeline.json"
TELEMETRY = ROOT / "outbox" / "telemetry.jsonl"
PLATFORMS = ["tiktok", "youtube", "instagram"]
STATES = ["rendered", "review", "music", "queued", "live", "failed", "rejected"]
# "rejected": reviewed and turned down (kept for the record; no dashboard tab shows it, the
# scheduler never picks it). Re-promote by setting state back to "review".

# Mascot cast canonical scales (the dive-video SKILL table). A cameo must sit on a card whose
# exp is within CAMEO_EXP_TOL of its mascot's realm — the sprite matches the register (Phil
# 2026-08-03: realm-match BEATS cast rotation; rotation applies only among matching mascots).
MASCOT_EXP = {"clark": -15, "adam": -10, "tina": -8, "belle": -5, "lee": -3, "newman": 0,
              "dora": 1, "kitty": 3, "lorraine": 5, "janet": 7, "lamar": 11,
              "aleksey": 21, "amos": 26}
CAMEO_EXP_TOL = 3.0

# RHYMING DISPLAY NAMES (Phil 2026-08-17 naming doctrine). Everything USER-FACING — captions,
# the "can you spot …" hook, hashtags, the VLM prompt, the dashboard — says the display name;
# the INTERNAL key never changes (sprite filenames, journey JSON `cameo.sprite`, MASCOT_EXP keys,
# pipeline entries' `cameo` field all stay the lowercase stem). Two display first names differ
# from their key on purpose: aleksey -> "Alexis", newman -> "Dwight".
# Lookup: MASCOT_DISPLAY.get(key, key.title())
MASCOT_DISPLAY = {
    "adam": "Adam the Atom",
    "aleksey": "Alexis the Galaxy",
    "amos": "Cosmo",
    "belle": "Belle the Cell",
    "clark": "Clark the Quark",
    "dora": "Dora the Flora",
    "janet": "Janet the Planet",
    "kitty": "Kitty the City",
    "lamar": "Lamar the Star",
    "lee": "Lee the Flea",
    "lorraine": "Lorraine the Terrane",
    "newman": "Dwight the Light",
    "tina": "Tina the DNA",
}


def mascot_display(key):
    """User-facing name for a mascot key (sprite stem). Internal keys are never renamed."""
    return MASCOT_DISPLAY.get((key or "").strip().lower(), (key or "").title())


def cameo_realm_check(spec):
    """-> list of problem strings (empty = ok): every cameo's mascot vs its card's exp."""
    probs = []
    for r in spec.get("registers", []):
        c = r.get("cameo")
        if not c:
            continue
        stem = Path(c.get("sprite", "")).stem.lower()
        me = MASCOT_EXP.get(stem)
        if me is None:
            probs.append(f"cameo on {r.get('name')}: unknown mascot {stem!r}")
        elif abs(float(r.get("exp", 0)) - me) > CAMEO_EXP_TOL:
            probs.append(f"cameo {stem} (realm 10^{me}) on card {r.get('name')} "
                         f"exp {r.get('exp')} — OFF-REALM")
    return probs


def load():
    # explicit utf-8: captions have emoji, and Windows Python defaults to cp1252
    if PIPELINE.exists():
        return json.loads(PIPELINE.read_text(encoding="utf-8"))
    return {"meta": {"cadence": "2/day 08:00,18:00 EDT"}, "videos": []}


def _atomic_write(path, text):
    """write-to-temp + os.replace: pipeline.json is ~0.5MB and read by the dashboard,
    the gate, and the batch concurrently — a plain truncate-then-stream write left a
    window where readers got half a file (JSONDecodeError) and a killed writer
    destroyed the state outright (audit 2026-08-19)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def save(data):
    data.setdefault("meta", {})["updated"] = _now()
    PIPELINE.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(PIPELINE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


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
    out = []
    for x in lines:
        if not x.strip():
            continue
        try:
            out.append(json.loads(x))
        except ValueError:
            continue   # one torn line from a concurrent append must not blank the feed
    return out


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


def gpu_busy(threshold=None):
    """True if the GPU is ACTUALLY under load — a dive render, seam repair, music gen, OR a game.
    Reads nvidia-smi utilization directly instead of matching process names: the old pgrep
    approach falsely tripped on any process whose *command line* merely mentioned the render
    scripts (e.g. a bash watcher with 'engine/dive.py' in its until-condition), so the flag never
    cleared after a render. Gate GPU-heavy work (music gen, local-VLM captioning) on this. Works
    from Windows (dashboard) via wsl.exe and from WSL directly; fails OPEN (returns False) so a
    smi hiccup never blocks the user. `threshold` overrides GPU_BUSY_PCT — pass ~60 when asking
    "is a GAME running" (default 30 false-positives on Chrome decoding dashboard previews)."""
    import os
    import subprocess
    smi = "/mnt/c/Windows/System32/nvidia-smi.exe"  # WSL2 GPU passthrough exposes the Windows smi
    inner = f"'{smi}' --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1"
    try:
        argv = (["wsl.exe", "bash", "-lc", inner] if os.name == "nt" else ["bash", "-lc", inner])
        r = subprocess.run(argv, capture_output=True, text=True, timeout=8)
        vals = [int(x) for x in (r.stdout or "").split() if x.strip().isdigit()]
        return bool(vals) and vals[0] >= (threshold if threshold is not None else GPU_BUSY_PCT)
    except Exception:
        return False


def comfy_busy():
    """True while ComfyUI is actually executing or queueing work (a dive render, seam repair,
    or music job). THIS — not raw GPU utilization — is the right gate for "would a music gen
    fight a render": gpu_busy() false-positives on the dashboard's own looping <video>
    previews (Chrome decodes them on the GPU), which silently skipped auto music gen on
    approve (2026-08-09). stdlib urllib because the dashboard runs on Windows python.
    Fails open (False) — a down ComfyUI must never block the user; the gen itself will
    surface that failure visibly."""
    import json as _json
    from urllib.request import urlopen
    try:
        with urlopen("http://localhost:8188/queue", timeout=3) as r:
            q = _json.loads(r.read().decode())
        return bool(q.get("queue_running") or q.get("queue_pending"))
    except Exception:
        return False


def paused_platforms(data):
    """Platforms the scheduler should NOT auto-post to (e.g. TikTok while a new-account
    review/spam-flag settles). Set via meta.paused_platforms in pipeline.json."""
    return list(data.get("meta", {}).get("paused_platforms", []))


# --- journey catalog (Layer 3) ------------------------------------------------
# The ACTIVE engine-2 catalog lives flat in journeys/. Superseded schemas live in
# journeys/engine1/ (world-card: interior/style_suffix) and journeys/engine0/ (phases —
# cannot compile on the current engine). Old specs stay resolvable because engine-1
# videos still flow through review/music/caption.
JOURNEYS_DIR = ROOT / "journeys"


def journey_path(name):
    """Resolve a journey name to its JSON, active catalog first. None if unknown."""
    for d in (JOURNEYS_DIR, JOURNEYS_DIR / "engine1", JOURNEYS_DIR / "engine0"):
        p = d / f"{name}.json"
        if p.exists():
            return p
    return None


def journey_names():
    """The active (engine-2) catalog — top-level journeys/*.json only."""
    return sorted(p.stem for p in JOURNEYS_DIR.glob("*.json"))


# --- journey registry: outbox/journeys.json -----------------------------------
# The render-side companion to pipeline.json. Stores only DECISIONS about journeys
# (queued to render / rejected / render_failed) plus the pipeline settings; everything
# else is DERIVED (a journey with a pipeline.json entry is "rendered"; video lifecycle
# is joined by name) so the two files can never drift apart.
JOURNEYS_JSON = ROOT / "outbox" / "journeys.json"

JSETTINGS_DEFAULTS = {
    "render_budget_min": 240,      # nightly render window (the 01:30 batch fills this)
    "max_ready_videos": 20,        # backpressure: skip the night at this many ready-to-post videos
    "max_review_videos": 20,       # backpressure 2 (Phil 2026-09-25): skip the night when this many
                                   # videos await his verdict (review + music stages) — the review
                                   # queue used to grow without bound; drains -> renders resume
    "journey_queue_target": 20,    # midnight refill tops the journey queue up toward this
    "refill_max_per_night": 5,     # never compose more than this in one midnight run
    "tier_share": {"long": 0.4, "medium": 0.3, "short": 0.3},   # refill Monte Carlo weights
    "render_paused": False,
    "refill_paused": False,
    # PLANET PLATE (2026-09-17, Phil: "tonight's videos to use this new planet descent"):
    # the nightly passes `--plate <mode> --plate-cn 0 --plate-void-gate` to dive.py for
    # every render. "low" = lab arm B (plate + denoise cap 0.32), the verdict on both beds;
    # "" / None = off (the pre-plate engine).
    "plate_mode": "low",
}


def jload():
    d = (json.loads(JOURNEYS_JSON.read_text(encoding="utf-8"))
         if JOURNEYS_JSON.exists() else {})
    # fill missing settings from defaults so new knobs appear without a migration
    d["settings"] = {**JSETTINGS_DEFAULTS, **d.get("settings", {})}
    d.setdefault("journeys", {})
    return d


def jsave(d):
    d["updated"] = _now()
    JOURNEYS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(JOURNEYS_JSON, json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def jqueue(jd):
    """Names of journeys queued to render, in Phil's chosen order."""
    q = [(n, e) for n, e in jd["journeys"].items() if e.get("state") == "queued"]
    return [n for n, _ in sorted(q, key=lambda t: t[1].get("order", 999))]


def set_jorder(jd, names):
    for i, n in enumerate(names):
        if n in jd["journeys"]:
            jd["journeys"][n]["order"] = i


def jmove(jd, name, delta):
    """Move a queued journey up/down in render order (same contract as move())."""
    seq = jqueue(jd)
    if name not in seq:
        return False
    j = seq.index(name)
    k = j + delta
    if not (0 <= k < len(seq)):
        return False
    seq[j], seq[k] = seq[k], seq[j]
    set_jorder(jd, seq)
    return True


def jstate(name, jd, pdata):
    """Stored decision (queued/rejected/render_failed) if any, else derived: 'rendered'
    once a pipeline.json entry exists (queue_review creates it only after a complete
    render), else 'new'."""
    e = jd["journeys"].get(name)
    if e and e.get("state"):
        return e["state"]
    return "rendered" if get(pdata, name) else "new"


# --- length tiers + render-time estimate --------------------------------------
def tier_of(cards):
    """Length tier from card count: the catalog runs 4–5-card shorts, 6–8-card
    standards, 9–11-card longs."""
    return "short" if cards <= 5 else ("medium" if cards <= 8 else "long")


def journey_frames(name):
    """Total frame count from the SAME compile the renderer uses (engine-2: 28 x cards).
    Raises on a spec the engine can't compile — callers treat that as a broken journey."""
    import sys as _sys
    eng = str(ROOT / "engine")
    if eng not in _sys.path:          # don't grow sys.path per call in the long-lived dashboard
        _sys.path.insert(0, eng)
    import grammar
    import style as _style
    p = journey_path(name)
    if not p:
        raise FileNotFoundError(f"no journey file for '{name}'")
    spec = json.loads(p.read_text(encoding="utf-8"))
    sfx, _model, _sname = _style.resolve(spec, None)
    spec["style_suffix"] = sfx
    return len(grammar.compile_journey(spec, 12, "in")[1])


import re as _re
PLANET_TARGET = _re.compile(r"\b(planet|world|moon)\b", _re.I)


def is_planet_card(reg, nxt):
    """THE planet-card rule (engine/plate.is_plate_card delegates here so the batch, the
    dashboard and the renderer can never disagree): a card whose target is a planet/world/
    moon, at exp >= 8, whose next card sits at exp 4.5-9.5 (the orbit view), not a seam."""
    tp = reg.get("target_phrase") or reg.get("target") or ""
    if not PLANET_TARGET.search(tp):
        return False
    if reg.get("kind") == "seam":
        return False
    e0, e1 = reg.get("exp"), nxt.get("exp")
    return (isinstance(e0, (int, float)) and isinstance(e1, (int, float))
            and e0 >= 8.0 and 4.5 <= e1 <= 9.5)


def has_planet_card(spec):
    """Does this journey render through the planet plate? (circular chain: the last card's
    next is the first)"""
    regs = spec.get("registers") or []
    n = len(regs)
    return any(is_planet_card(regs[i], regs[(i + 1) % n]) for i in range(n))


def est_render_sec(frames, planet=False):
    """Wall-clock estimate for one journey. REFIT 2026-09-23 on the 13 nightly renders of
    09-20..09-22 (parallax + loop lap + live plate era): 18.3 s/frame (max error 7%),
    plus ~820 s when the journey has a planet card (the plate span: IP-Adapter, masks,
    two txt2img assets with caption gates), plus ~42 s queue_review + caption. The old
    fit (17.9 s/frame - 606, July/August engine) was 12-34% low on every render and the
    batch overran its budget by ~1.3 h a night."""
    # 2026-09-23 afternoon: that 18.3 s/frame was measured on nights when Windows had ComfyUI
    # throttled onto the E-cores (night_batch.boost_comfy fixes it); the same frames render
    # in ~9.5 s on the P-cores (speed_lab, 4 arms, byte-identical pixels). Provisional
    # unthrottled figure 12.0 s/frame + 600 s per planet card — REFIT on the first full
    # unthrottled night's actuals (scripts/night_batch logs: "[dive] done in Ns").
    # REFIT 2026-09-25 on the first two unthrottled nights (10 renders, 09-24/25): 12.0 s/frame
    # + 250 s fixed (model warm-up, frame 0, assembly) + 600 s per planet card; sum of the ten
    # estimates within 2% of the sum of actuals, worst single journey 11% under (spouter_dawn).
    return max(600, round(12.0 * frames) + 250 + (600 if planet else 0) + 42)


def pick_tonight(jd, ests):
    """Tonight's renders: QUEUE ORDER, as many as fit render_budget_min (Phil
    2026-08-26 — tier templates RETIRED: they overrode the queue order Phil set, so a
    glut of queued longs kept rendering while his front-of-queue mediums/shorts never
    came up; now the queue's mix IS the nightly mix, and refill_tiers' Monte Carlo
    draw keeps that mix on target). `ests` maps every eligible queued journey -> est
    seconds (callers compile once; a journey missing from ests is skipped). A journey
    too big for the REMAINING budget is skipped and the next tried, so one fat long
    can't strand the night; the first pick always lands even if over budget.
    Returns (names, total_sec)."""
    budget = jd["settings"]["render_budget_min"] * 60
    picks, total = [], 0
    for n in jqueue(jd):
        if n not in ests:
            continue
        if not picks or total + ests[n] <= budget:
            picks.append(n)
            total += ests[n]
    return picks, total


def refill_tiers(jd, n):
    """Tiers for n new briefs: independent MONTE CARLO draws weighted by tier_share
    (Phil 2026-08-26 — replaces the deficit-vs-share rotation: the queue converges to
    the target mix over time WITHOUT a predictable pattern, and since the batch renders
    in queue order, the mix queued is the mix rendered)."""
    import random
    share = jd["settings"]["tier_share"]
    tiers = [t for t in ("long", "medium", "short") if share.get(t, 0) > 0]
    if not tiers:
        return ["long"] * n            # degenerate settings — never return nothing
    return random.choices(tiers, weights=[share[t] for t in tiers], k=n)


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
