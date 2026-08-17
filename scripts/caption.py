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
    'A hidden character named "{m}" appears briefly somewhere in the video. Also write "spot_line" — '
    'ONE short, fun, VARIED question inviting viewers to find {m} (e.g. ask if they can spot {m}, or '
    'at what moment {m} pops up), with one playful emoji. Write the character\'s name EXACTLY as '
    '"{m}" — never shorten it, never drop or change any word of it. Do NOT ask people to comment.\n'
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
    spec = json.loads(pl.journey_path(journey).read_text(encoding="utf-8"))
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


def _fix_mascot_name(text, key, display):
    """Force the FULL rhyming display name in user-facing text. The VLM is told to write it
    verbatim but still shortens "Adam the Atom" -> "Adam" (and may fall back on the internal
    key). Placeholder-swap so an already-correct name can't grow a second tail."""
    if not (text and display):
        return text
    ph = "\x00M\x00"
    out = re.sub(re.escape(display), ph, text, flags=re.I)
    for alt in sorted({key, display.split()[0]}, key=len, reverse=True):
        if alt:
            out = re.sub(rf"\b{re.escape(alt)}\b", ph, out, flags=re.I)
    return out.replace(ph, display)


def _fix_mascot_tag(tag, key, display):
    """A hashtag naming the mascot uses the display name squished: #clarkthequark."""
    if not (display and isinstance(tag, str)):
        return tag
    body = tag.lstrip("#")
    if body.lower() in {key.lower(), display.split()[0].lower()}:
        return "#" + re.sub(r"[^a-z0-9]", "", display.lower())
    return tag


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
    p = pl.journey_path(journey)
    if not (p and theme):
        return
    spec = json.loads(p.read_text(encoding="utf-8"))
    if not spec.get("music_theme"):        # don't clobber a theme Phil already set
        spec["music_theme"] = theme
        p.write_text(json.dumps(spec, indent=2))


def generate(journey, model="ds", no_theme=False):
    d = pl.load(); v = pl.get(d, journey)
    jf = pl.journey_path(journey)
    if not jf:
        print(f"  no journey file for {journey}"); return None
    # captioning is text-only off the worlds, so frames aren't required (they're for future
    # image-grounding); a cleaned-up render still gets captioned.
    style, worlds = journey_worlds(journey)
    # user-facing name only: the pipeline entry stores the internal key (sprite stem), captions
    # always say the rhyming display name (Phil 2026-08-17) — see pl.MASCOT_DISPLAY.
    cameo_key = (v.get("cameo") or "").strip() if v else ""
    mascot = pl.MASCOT_DISPLAY.get(cameo_key.lower(), cameo_key.title()) if cameo_key else ""
    mline = MASCOT_INSTR.format(m=mascot) if mascot else NO_MASCOT_INSTR
    url = _ollama()
    try:
        r = requests.post(f"{url}/api/generate", json={
            "model": VLM_MODEL,
            "prompt": PROMPT.format(worlds="\n".join(worlds), style=style, mascot_line=mline),
            "stream": False, "format": "json", "options": {"num_predict": 1200},
            # keep_alive=0 -> unload the 24B captioner the instant it answers. Ollama's default
            # keeps it resident for 5 min holding ~7.6 GB, which on this 10 GB card starves the
            # very next ComfyUI render: SDXL+ControlNet+CLIP+DepthAnything+Florence no longer fit,
            # ComfyUI falls back to per-step CPU<->GPU weight swapping (1.5 s/it -> 33 s/it) and
            # dive.py times out. This is a ONE-SHOT text call — there is nothing to keep warm.
            "keep_alive": 0}, timeout=300)
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
    bodies = [_fix_mascot_name(b, cameo_key, mascot) for b in bodies]
    # YouTube title = the descriptive caption body itself (the part before the mascot question +
    # hashtags), truncated to YT's limit — not a separately-written title.
    yts = [b[:100] for b in bodies]
    spot = _fix_mascot_name((data.get("spot_line") or "").strip(), cameo_key, mascot) if mascot else ""
    tags = " ".join(_dedupe_tags([_fix_mascot_tag(t, cameo_key, mascot)
                                  for t in list(data.get("hashtags", []))] + BRAND_TAGS))
    mtheme = (data.get("music_theme") or "").strip()
    # RE-READ before writing: the Ollama call above holds this process for ~40s while the
    # dashboard may be editing pipeline.json — merge into a fresh copy, own fields only
    # (same lost-update class as music_gen's, found 2026-08-01).
    d = pl.load(); v = pl.get(d, journey)
    # respect a pre-set spot toggle; else default on when there's a mascot + a spot line
    hook = bool(mascot and spot) and (v.get("spot_hook", True) if v else True)
    opts = [assemble_caption(b, spot, tags, hook) for b in bodies]
    if v:
        # NEVER clobber a caption the user wrote or picked. Regenerating offers NEW options; it
        # only fills the live caption when there isn't one yet (Phil 2026-07-31: "if there's
        # something in the caption and I generate new captions, don't change the box").
        had = (v.get("caption") or "").strip()
        v.update({"caption_bodies": bodies, "yt_title_options": yts, "spot_line": spot,
                  "caption_tags": tags, "spot_hook": hook, "caption_options": opts})
        if not had:
            v["caption"] = opts[0]
            v["yt_title"] = yts[0] or v.get("yt_title", "")
        pl.save(d)
        if not no_theme:
            set_music_theme_if_empty(journey, mtheme)
        pl.telem("caption", journey=journey, detail=f"{len(opts)} options, spot={hook}")
    else:
        # There is nowhere to store these. This used to print the success line anyway, so a
        # batch that captioned BEFORE queue_review.py (which is what CREATES the entry) looked
        # like it worked and left butterfly_meridian + lather_atlas in Review with no caption.
        print(f"  !! {journey} is NOT in pipeline.json — {len(opts)} captions GENERATED BUT "
              f"DISCARDED. Run scripts/queue_review.py first, then re-run this.")
    print(f"  {journey}: {len(opts)} caption+title pairs (spot={hook}); theme='{mtheme[:40]}'"
          + ("" if not no_theme else " [theme skipped]")
          + ("" if v else "  [NOT SAVED]"))
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
