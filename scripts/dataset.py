#!/usr/bin/env python3
"""THE ANALYSIS TABLE (2026-09-25) — one row per posted video, every variable we control or
measure, and the outcomes at FIXED EXPOSURE AGES so a 2-day-old video is comparable to a
40-day-old one. Written to outbox/dataset.csv (+ .json). Pure joins, no modelling here.

  python3 scripts/dataset.py            # rebuild (music features refreshed first)
  python3 scripts/dataset.py --print    # column summary

Sources: outbox/pipeline.json (what was posted, when, with which music/cameo/engine settings),
journeys/*.json (what the journey IS: tier, scale span, planet card, tempo, style, cameo card),
outbox/video_features.json (frame luminance/saturation/contrast — ig_analyze's cache),
outbox/music_features.json (deck + measured audio, scripts/music_features.py),
outbox/ig_stats.jsonl (views/likes/comments snapshots, followers at the time),
outbox/ig_insights.jsonl (reach/shares/saves/follows/watch time), outbox/yt_stats.jsonl.

Outcome columns: ig_views/likes/comments = latest; ig_likes_48h / ig_views_48h / _7d = the first
snapshot at or after 48 h / 7 d post-publish (NaN if the video is younger, or if the series has
no snapshot in the window); ig_like_rate = likes/views (latest); shares/saves/follows/reach from
insights (latest); yt_views latest; followers_at_post = the account's follower count on the
first snapshot after posting (the audience size the video was shown to)."""
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

OUT = ROOT / "outbox" / "dataset.csv"
TS = "%Y-%m-%d %H:%M:%S"


def jl(path):
    rows = []
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def parse_ts(s):
    for fmt in (TS, "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def at_age(series, t0, hours):
    """First snapshot at or after t0 + hours (within a 36 h window), else None."""
    target = t0 + timedelta(hours=hours)
    for ts, r in series:
        if ts >= target:
            return r if ts <= target + timedelta(hours=36) else None
    return None


def journey_meta(j):
    p = pl.journey_path(j)
    if not p:
        return {}
    spec = json.loads(p.read_text(encoding="utf-8"))
    regs = spec.get("registers") or []
    exps = [r.get("exp") for r in regs if isinstance(r.get("exp"), (int, float))]
    fmt = spec.get("format") or {}
    fpb = fmt.get("frames_per_beat", 7)
    cards = len(regs)
    seams = sum(1 for r in regs if r.get("kind") == "seam")
    cameo_reg = next((r for r in regs if r.get("cameo")), None)
    scene_words = " ".join((r.get("scene") or "") for r in regs).lower()
    return {
        "cards": cards, "tier": pl.tier_of(cards) if cards else None,
        "engine": "e2" if (regs and "scene" in regs[0]) else "e1",
        "style": spec.get("style") or "", "music_lane_authored": spec.get("music_lane") or "",
        "fpb": fpb, "bpm_nominal": round(720 / fpb) if fpb else None,
        "video_s": round(cards * 4 * fpb / 12, 1) if cards else None,
        "exp_max": max(exps) if exps else None, "exp_min": min(exps) if exps else None,
        "scale_span": (max(exps) - min(exps)) if exps else None,
        "cosmic": bool(exps) and max(exps) >= 11, "subatomic": bool(exps) and min(exps) <= -8,
        "full_scale": bool(exps) and max(exps) >= 11 and min(exps) <= -8,
        "planet_card": pl.has_planet_card(spec), "seams": seams,
        "cameo_card_exp": cameo_reg.get("exp") if cameo_reg else None,
        "has_water": any(w in scene_words for w in ("ocean", "sea", "reef", "tide", "river", "lake")),
        "has_creature": any(w in scene_words for w in ("bird", "fish", "insect", "beetle", "moth",
                                                        "octopus", "jelly", "whale", "ant", "bee")),
    }


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "music_features.py")],
                   capture_output=True)
    p = pl.load()
    feats = json.loads((ROOT / "outbox" / "video_features.json").read_text(encoding="utf-8")) \
        if (ROOT / "outbox" / "video_features.json").exists() else {}
    mus = json.loads((ROOT / "outbox" / "music_features.json").read_text(encoding="utf-8")) \
        if (ROOT / "outbox" / "music_features.json").exists() else {}
    stats, ins, yt = jl("outbox/ig_stats.jsonl"), jl("outbox/ig_insights.jsonl"), jl("outbox/yt_stats.jsonl")
    by_code, by_j = {}, {}
    for r in stats:
        ts = parse_ts(r.get("ts", ""))
        if not ts or not r.get("views"):
            continue
        by_code.setdefault(r.get("code"), []).append((ts, r))
        if r.get("journey"):
            by_j.setdefault(r["journey"], []).append((ts, r))
    ins_by = {}
    for r in ins:
        if r.get("journey"):
            ins_by[r["journey"]] = r                   # append-ordered: newest wins
    yt_by = {}
    for r in yt:
        if r.get("journey"):
            yt_by[r["journey"]] = r
    now = datetime.now()
    rows = []
    for v in p["videos"]:
        if v.get("state") != "live":
            continue
        j = v["journey"]
        ig = (v.get("platforms") or {}).get("instagram") or {}
        code = None
        m = re.search(r"/reel/([A-Za-z0-9_-]+)", ig.get("url") or "")
        if m:
            code = m.group(1)
        t0 = parse_ts(ig.get("ts") or "") or parse_ts(((v.get("platforms") or {}).get("youtube") or {}).get("ts") or "")
        series = sorted(by_code.get(code, []) or by_j.get(j, []), key=lambda x: x[0])
        latest = series[-1][1] if series else {}
        row = {"journey": j, "posted": t0.strftime(TS) if t0 else "", "age_days": round((now - t0).days, 1) if t0 else None,
               "post_hour": t0.hour if t0 else None, "post_weekday": t0.strftime("%a") if t0 else "",
               "ig_code": code or "", "cut": v.get("cut"), "model": v.get("model"), "cameo": v.get("cameo") or "",
               "caption_len": len(v.get("caption") or ""), "n_hashtags": (v.get("caption") or "").count("#"),
               "spot_hook": bool(v.get("spot_hook"))}
        row.update(journey_meta(j))
        ep = v.get("engine_params") or {}
        row.update({"parallax_gain": ep.get("parallax_gain"), "plate": ep.get("plate") or ("" if ep else None),
                    "plate_intro": ep.get("plate_intro") or "", "era_engine_params": bool(ep)})
        f = feats.get(j) or {}
        row.update({"lum": f.get("lum"), "sat": f.get("sat"), "contrast": f.get("contrast"), "dark_frac": f.get("dark_frac")})
        mf = mus.get(j) or {}
        row.update({"music_" + k: mf.get(k) for k in ("chosen", "lane", "rhythm", "family", "mode", "bpm", "kick", "lock", "fit",
                                                      "brightness_hz", "rolloff85_hz", "low_share", "high_share",
                                                      "loudness_rms", "dynamics", "onsets_per_s", "pulse_bpm",
                                                      "pulse_strength", "flatness")})
        row["music_instruments"] = "|".join(mf.get("instruments") or [])
        # outcomes
        row.update({"ig_views": latest.get("views"), "ig_likes": latest.get("likes"), "ig_comments": latest.get("comments"),
                    "ig_like_rate": (latest.get("likes") / latest.get("views")) if latest.get("views") else None,
                    "followers_at_post": series[0][1].get("followers") if series else None,
                    "followers_latest": latest.get("followers")})
        for h, tag in ((48, "48h"), (168, "7d")):
            r = at_age(series, t0, h) if (t0 and series) else None
            row[f"ig_views_{tag}"] = r.get("views") if r else None
            row[f"ig_likes_{tag}"] = r.get("likes") if r else None
        i = ins_by.get(j) or {}
        row.update({"ig_reach": i.get("reach"), "ig_shares": i.get("shares"), "ig_saves": i.get("saves"),
                    "ig_follows": i.get("follows"), "ig_watch_s": i.get("watch_s"), "ig_avg_play_s": i.get("avg_play_s")})
        row["yt_views"] = (yt_by.get(j) or {}).get("views")
        rows.append(row)
    rows.sort(key=lambda r: r["posted"])
    cols = list(rows[0].keys()) if rows else []
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    (OUT.with_suffix(".json")).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"dataset: {len(rows)} videos x {len(cols)} columns -> {OUT}")
    if "--print" in sys.argv:
        import pandas as pd
        df = pd.read_csv(OUT)
        print(df.describe(include="all").T[["count", "unique", "top", "mean", "min", "max"]].to_string())


if __name__ == "__main__":
    main()
