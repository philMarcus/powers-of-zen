#!/usr/bin/env python3
"""Write short-video captions (+ a YouTube title) for a rendered journey with a LOCAL vision
model (Ollama). Looks at a few frames of the render + the journey's worlds, returns THREE caption
options (each ending in journey-specific hashtags); the always-on brand hashtags are appended
programmatically. Stores them in the pipeline entry so a video already HAS a caption + YT title by
the time it's in the review queue.

GPU-heavy (the VLM runs on the GPU) — refuses to run while a render/GPU job is active unless
--force. Model-agnostic caption; prefers DS frames if present (same caption for DS or turbo).

Usage:
  python3 scripts/caption.py <journey> [--model ds] [--force]
  python3 scripts/caption.py --all         # caption every review-queue video missing one
"""
import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

VLM_MODEL = "qwen3-vl:4b"
# always-on brand hashtags (programmatic) — NO #fyp (dropped 2026-07-29). Journey-specific tags
# come from the model per video.
BRAND_TAGS = ["#powersofzen", "#oddlysatisfying", "#zoomer"]

PROMPT = (
    'You are writing captions for "Powers of Zen" — a hypnotic, seamless Powers-of-Ten-style '
    'zoom short that dives continuously through every scale of a world and loops forever. Brand '
    'voice: dreamy, awe-striking, oddly satisfying; it makes people rewatch to find the loop.\n\n'
    'This video travels through these worlds, in order:\n{worlds}\nVisual style: {style}\n'
    'The attached images are moments from the dive.\n\n'
    'Write THREE distinct caption options for TikTok / Instagram Reels. Each caption: ONE short, '
    'evocative line that makes someone watch to the end and rewatch the loop; hint at the journey '
    'without explaining it; at most 1–2 tasteful emoji; then 3–4 hashtags SPECIFIC to this video\'s '
    'worlds / theme. Never use #fyp, #viral, or generic filler tags.\n'
    'Also write ONE punchy YouTube Shorts title (under 80 chars, no hashtags).\n'
    'Respond with ONLY JSON: {{"captions": ["...", "...", "..."], "yt_title": "..."}}'
)


def _ollama():
    """localhost first, then the WSL default-gateway host (Ollama runs on the Windows side)."""
    urls = ["http://localhost:11434"]
    try:
        gw = subprocess.run(["bash", "-lc", "ip route 2>/dev/null | awk '/default/{print $3; exit}'"],
                            capture_output=True, text=True, timeout=5).stdout.strip()
        if gw:
            urls.append(f"http://{gw}:11434")
    except Exception:
        pass
    for u in urls:
        try:
            requests.get(u + "/api/tags", timeout=3)
            return u
        except Exception:
            continue
    return urls[-1]


def frames_for(journey, model):
    base = ROOT / "output" / f"{journey}_{model}"
    if not base.exists():
        return []
    for v in sorted([p for p in base.glob("v[0-9]*") if p.name[1:].isdigit()],
                    key=lambda p: int(p.name[1:]), reverse=True):
        pngs = sorted((v / "build" / "frames").glob("*.png"))
        if pngs:
            n = len(pngs)
            return [pngs[int(n * f)] for f in (0.1, 0.37, 0.63, 0.9)]
    return []


def journey_worlds(journey):
    spec = json.loads((ROOT / "journeys" / f"{journey}.json").read_text())
    return spec.get("style_suffix", ""), [f"- {r['interior']}" for r in spec["registers"]]


def _parse(raw):
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}


def _append_brand(cap):
    have = {t.lower() for t in re.findall(r"#\w+", cap.lower())}
    add = [t for t in BRAND_TAGS if t.lower() not in have]
    return (cap.rstrip() + " " + " ".join(add)).strip() if add else cap.strip()


def generate(journey, model="ds"):
    frames = frames_for(journey, model) or frames_for(journey, "turbo") or frames_for(journey, "")
    if not frames:
        print(f"  no frames for {journey}"); return None
    style, worlds = journey_worlds(journey)
    url = _ollama()
    try:
        r = requests.post(f"{url}/api/generate", json={
            "model": VLM_MODEL, "prompt": PROMPT.format(worlds="\n".join(worlds), style=style),
            "images": [base64.b64encode(Path(f).read_bytes()).decode() for f in frames],
            "stream": False, "format": "json"}, timeout=240)
        data = _parse(r.json().get("response", ""))
    except Exception as e:
        print(f"  VLM error for {journey}: {e}"); return None
    caps = [_append_brand(c) for c in data.get("captions", []) if c.strip()][:3]
    yt = (data.get("yt_title") or "").strip()[:100]
    if not caps:
        print(f"  no captions parsed for {journey}"); return None
    d = pl.load(); v = pl.get(d, journey)
    if v:
        v["caption_options"] = caps
        v["caption"] = caps[0]
        if yt:
            v["yt_title"] = yt
        pl.save(d); pl.telem("caption", journey=journey, detail=f"{len(caps)} options")
    print(f"  {journey}: {len(caps)} captions; yt='{yt[:50]}'")
    for i, c in enumerate(caps):
        print(f"    [{i}] {c}")
    return caps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey", nargs="?")
    ap.add_argument("--model", default="ds")
    ap.add_argument("--all", action="store_true", help="caption every review video missing captions")
    ap.add_argument("--force", action="store_true", help="run even if the GPU is busy")
    args = ap.parse_args()
    if pl.gpu_busy() and not args.force:
        print("GPU busy (render/music running) — skipping caption gen. Re-run when free, or --force.")
        return
    if args.all:
        d = pl.load()
        todo = [v for v in d["videos"] if v.get("state") in ("review", "music", "queued")
                and not v.get("caption_options")]
        print(f"captioning {len(todo)} video(s) missing captions…")
        for v in todo:
            generate(v["journey"], v.get("model", args.model))
    elif args.journey:
        generate(args.journey, args.model)
    else:
        ap.error("give a <journey> or --all")


if __name__ == "__main__":
    main()
