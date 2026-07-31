#!/usr/bin/env python3
"""Write short-video captions for a rendered journey with a LOCAL model (Ollama). Reads the
journey's worlds and returns FIVE caption options (each ending in journey-specific hashtags); the
always-on brand hashtags are appended programmatically. The YouTube title is NOT written separately
— it's the caption BODY (the descriptive line before the mascot question), i.e. a truncation of the
caption. Stores everything in the pipeline entry so a video already HAS a caption + YT title by the
time it's in the review queue.

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

# Captioning is TEXT-based off the journey's worlds (reliable clean JSON). The vision model
# qwen3-vl:4b is a reasoning model that returns empty responses under format=json, and gemma4
# nests its reasoning inside the JSON — mistral-small returns exactly the structure we ask for.
# (TODO: light image-grounding via moondream to feed the actual rendered look.)
VLM_MODEL = "mistral-small3.2:24b"
# always-on brand hashtags (programmatic) — NO #fyp (dropped 2026-07-29). Journey-specific tags
# come from the model per video.
BRAND_TAGS = ["#powersofzen", "#oddlysatisfying", "#zoomer",
              # always-on reach set (Phil 2026-07-31): what the work IS (animation/art/AI art)
              # + the listening mood the music sits in
              "#animation", "#art", "#aiart", "#chillbeats"]

PROMPT = (
    'You are writing captions for "Powers of Zen" — a hypnotic, seamless Powers-of-Ten-style '
    'zoom short that dives continuously through every scale of a world and loops forever. Brand '
    'voice: dreamy, awe-striking, oddly satisfying; it makes people rewatch to find the loop.\n\n'
    'This video travels through these worlds, in order:\n{worlds}\nVisual style: {style}\n\n'
    'Give FIVE distinct "captions". Each caption is ONE short evocative TikTok/Instagram line that '
    'makes someone watch to the end and rewatch the loop — hint at the journey, at most 1–2 tasteful '
    'emoji, NO hashtags and NO questions. (The YouTube title is taken from this same line, so make it '
    'work standing alone.)\n'
    '{mascot_line}'
    'Also give: "hashtags" — 3–4 tags SPECIFIC to this video\'s worlds/theme (never #fyp, #viral, '
    'or generic filler); "music_theme" — one vivid line describing the scene/mood to inspire an '
    'instrumental soundtrack for this dive.\n'
    'Respond with ONLY JSON: {{"captions": ["...", ... 5 total], '
    '"spot_line": "...", "hashtags": ["#..","#.."], "music_theme": "..."}}'
)
MASCOT_INSTR = (
    'A hidden character named {m} appears briefly somewhere in the video. Also write "spot_line" — '
    'ONE short, fun, VARIED question inviting viewers to find {m} (e.g. ask if they can spot {m}, or '
    'at what moment {m} pops up), with one playful emoji. Do NOT ask people to comment.\n'
)
NO_MASCOT_INSTR = 'There is no hidden character — leave "spot_line" empty.\n'


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
    """(style words, ['- world', ...]) for the prompt. Handles BOTH schemas: engine-2 journeys
    use `scene` + a `style` deck NAME, engine-1 used `interior` + free-text `style_suffix`.
    (This was a hard KeyError on every new journey — captioning was dead for the whole
    engine-2 catalog, which is why the dashboard's Generate button did nothing.)"""
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "engine"))
    import style as _style
    spec = json.loads((ROOT / "journeys" / f"{journey}.json").read_text())
    sfx, _model, _name = _style.resolve(spec, None)
    worlds = [f"- {r.get('scene') or r.get('interior') or r.get('name', '')}"
              for r in spec["registers"]]
    return sfx or spec.get("style_suffix", ""), worlds


def _parse(raw):
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}


def _dedupe_tags(tags):
    out, seen = [], set()
    for t in tags:
        t = t.strip()
        if t and t.startswith("#") and t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    return out


def assemble_caption(body, spot_line, tags, hook):
    """body [+ spot question if hook] + hashtags. Shared shape used by the dashboard toggle."""
    parts = [body.strip()]
    if hook and spot_line.strip():
        parts.append(spot_line.strip())
    if tags.strip():
        parts.append(tags.strip())
    return " ".join(p for p in parts if p)


def set_music_theme_if_empty(journey, theme):
    p = ROOT / "journeys" / f"{journey}.json"
    if not (p.exists() and theme):
        return
    spec = json.loads(p.read_text())
    if not spec.get("music_theme"):        # don't clobber a theme Phil already set
        spec["music_theme"] = theme
        p.write_text(json.dumps(spec, indent=2))


def generate(journey, model="ds", no_theme=False):
    d = pl.load(); v = pl.get(d, journey)
    jf = ROOT / "journeys" / f"{journey}.json"
    if not jf.exists():
        print(f"  no journey file for {journey}"); return None
    # captioning is text-only off the worlds, so frames aren't required (they're for future
    # image-grounding); a cleaned-up render still gets captioned.
    style, worlds = journey_worlds(journey)
    mascot = (v.get("cameo") or "").capitalize() if v else ""
    mline = MASCOT_INSTR.format(m=mascot) if mascot else NO_MASCOT_INSTR
    url = _ollama()
    try:
        r = requests.post(f"{url}/api/generate", json={
            "model": VLM_MODEL,
            "prompt": PROMPT.format(worlds="\n".join(worlds), style=style, mascot_line=mline),
            "stream": False, "format": "json", "options": {"num_predict": 1200}}, timeout=300)
        data = _parse(r.json().get("response", ""))
    except Exception as e:
        print(f"  VLM error for {journey}: {e}"); return None
    # 5 caption bodies; tolerate the older paired {caption, yt_title} shape too
    raw = data.get("captions")
    if not raw and data.get("options"):
        raw = [o.get("caption") for o in data["options"]]
    bodies = [c.strip() for c in (raw or []) if c and c.strip()][:5]
    if not bodies:
        print(f"  no captions parsed for {journey}"); return None
    # YouTube title = the descriptive caption body itself (the part before the mascot question +
    # hashtags), truncated to YT's limit — not a separately-written title.
    yts = [b[:100] for b in bodies]
    spot = (data.get("spot_line") or "").strip() if mascot else ""
    tags = " ".join(_dedupe_tags(list(data.get("hashtags", [])) + BRAND_TAGS))
    mtheme = (data.get("music_theme") or "").strip()
    # respect a pre-set spot toggle; else default on when there's a mascot + a spot line
    hook = bool(mascot and spot) and (v.get("spot_hook", True) if v else True)
    opts = [assemble_caption(b, spot, tags, hook) for b in bodies]
    if v:
        v.update({"caption_bodies": bodies, "yt_title_options": yts, "spot_line": spot,
                  "caption_tags": tags, "spot_hook": hook, "caption_options": opts,
                  "caption": opts[0], "yt_title": yts[0] or v.get("yt_title", "")})
        pl.save(d)
        if not no_theme:
            set_music_theme_if_empty(journey, mtheme)
        pl.telem("caption", journey=journey, detail=f"{len(opts)} options, spot={hook}")
    print(f"  {journey}: {len(opts)} caption+title pairs (spot={hook}); theme='{mtheme[:40]}'"
          + ("" if not no_theme else " [theme skipped]"))
    for i, c in enumerate(opts):
        print(f"    [{i}] {c}  ||  YT: {yts[i]}")
    return opts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey", nargs="?")
    ap.add_argument("--model", default="ds")
    ap.add_argument("--all", action="store_true", help="caption every review video missing captions")
    ap.add_argument("--no-theme", action="store_true", help="don't touch music_theme (production regen)")
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
            generate(v["journey"], v.get("model", args.model), no_theme=args.no_theme)
    elif args.journey:
        generate(args.journey, args.model, no_theme=args.no_theme)
    else:
        ap.error("give a <journey> or --all")


if __name__ == "__main__":
    main()
