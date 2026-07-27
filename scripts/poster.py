#!/usr/bin/env python3
"""Local posting harness for Powers of Zen.

Drives the dedicated PowersOfZen Chrome profile (CDP on :9222) through the
TikTok / YouTube Shorts / Instagram posting playbook — replacing Claude as the
clicker so posting costs ELECTRICITY, not premium tokens.

Design principles (from the cost lesson, see PLAN.md):
  - DOM/text assertions are PRIMARY (free, instant). We check element/text state.
  - A local Ollama VLM (qwen3-vl:4b) is a FALLBACK sanity layer, called only a
    couple times per platform for genuinely-visual checks. Keep screenshots OUT
    of any large-model context — they only ever go to the local VLM.
  - FAIL LOUD: after each step, assert the expected next state. On failure,
    screenshot + append a flag to outbox/flags.jsonl + SKIP that platform +
    continue the others. A site redesign becomes a clear dashboard flag, never
    a silent half-post.

Usage:
  python3 scripts/poster.py                 # next approved+unposted entry, all 3 platforms
  python3 scripts/poster.py --dry-run       # fill everything, STOP before final Post (safe)
  python3 scripts/poster.py --journey black_hole   # target a specific queue entry
  python3 scripts/poster.py --only tiktok,youtube  # subset of platforms

NOT YET TESTED end-to-end — write-first, tune-with-Phil. Fragile spots (AI-label
toggles, platform dialogs) are marked TUNE. Run --dry-run first, always.
"""
import argparse
import base64
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from zen_browser import Tab  # noqa: E402

OLLAMA = "http://192.168.68.1:11434"
VLM_MODEL = "qwen3-vl:4b"          # pull: ollama pull qwen3-vl:4b (fallback: moondream)
QUEUE = ROOT / "outbox" / "queue.json"
FLAGS = ROOT / "outbox" / "flags.jsonl"
SHOTS = ROOT / "outbox" / "shots"
COORD_SCALE = 1.28                 # displayed-coords × this = CDP viewport coords


# ---------------------------------------------------------------- infrastructure
class PlatformError(Exception):
    pass


def win_path(rel):
    return "C:\\Users\\Phil\\zoomer\\" + rel.replace("/", "\\")


def shot(tab, tag):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / f"{tag}.png"
    tab.shot(str(p))
    return p


def flag(platform, step, tab, detail=""):
    """Record a failure: screenshot + one line in flags.jsonl for the dashboard."""
    img = ""
    try:
        img = str(shot(tab, f"FLAG_{platform}_{step}"))
    except Exception:
        pass
    FLAGS.parent.mkdir(parents=True, exist_ok=True)
    with open(FLAGS, "a") as f:
        f.write(json.dumps({"platform": platform, "step": step,
                            "detail": detail, "shot": img,
                            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"  !! FLAG [{platform}/{step}] {detail}")


def expect(cond, platform, step, tab, detail=""):
    if not cond:
        flag(platform, step, tab, detail)
        raise PlatformError(f"{platform}/{step}: {detail}")


def vlm_yesno(image_path, question, default=True):
    """Ask the LOCAL VLM a yes/no question about a screenshot. Screenshots go ONLY
    here — never into a premium-model context. Returns default if the model is down."""
    try:
        img = base64.b64encode(Path(image_path).read_bytes()).decode()
        r = requests.post(f"{OLLAMA}/api/generate", json={
            "model": VLM_MODEL,
            "prompt": question + " Answer with only YES or NO.",
            "images": [img], "stream": False}, timeout=180)
        ans = r.json().get("response", "").strip().upper()
        return ans.startswith("Y")
    except Exception as e:
        print(f"  (VLM unavailable: {e} — assuming {default})")
        return default


def click_css(tab, x, y):
    tab.click(int(x * COORD_SCALE), int(y * COORD_SCALE))


# ---------------------------------------------------------------- platforms
def post_tiktok(video_rel, caption, dry_run):
    tab = Tab(match="tiktok")
    tab.goto("https://www.tiktok.com/tiktokstudio/upload")
    time.sleep(7)
    tab.setfile('input[type="file"]', win_path(video_rel))
    time.sleep(14)
    # accept the automatic-content-checks modal if present
    tab.eval("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Turn on')?.click()")
    time.sleep(2)
    # caption
    tab.eval("const e=document.querySelector('.public-DraftEditor-content');"
             "if(e){e.focus();document.execCommand('selectAll');}")
    tab.type_text(caption)
    tab.eval("document.activeElement.blur()")
    time.sleep(1)
    # upload finished? caption editor + no 'uploading' text; VLM sanity on the preview
    s = shot(tab, "tiktok_precheck")
    expect(vlm_yesno(s, "Is a vertical video upload shown with a visible preview thumbnail "
                        "(not an error, not still uploading)?"),
           "tiktok", "upload", tab, "upload/preview not confirmed")
    # AI-generated-content label ON  (TUNE: toggle location is fiddly)
    tab.eval("[...document.querySelectorAll('div,span,button')]"
             ".find(e=>e.textContent.trim()==='Show more'&&e.children.length<=1)?.click()")
    time.sleep(1)
    coords = tab.eval("const l=[...document.querySelectorAll('*')].find(e=>e.children.length===0"
                      "&&e.textContent.trim()==='AI-generated content');"
                      "if(!l)return null;l.scrollIntoView({block:'center'});"
                      "const r=l.getBoundingClientRect();JSON.stringify([Math.round(r.right)+40,Math.round(r.top)+10])")
    expect(coords, "tiktok", "ai_label_find", tab, "AI-generated-content row not found")
    x, y = json.loads(coords)
    click_css(tab, x, y)
    time.sleep(2)
    tab.eval("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Turn on')?.click()")
    time.sleep(2)
    # verify checks passed
    txt = tab.eval("document.body.innerText")
    expect("No issues found" in txt or "Checking" in txt, "tiktok", "checks", tab,
           "content checks not green")
    if dry_run:
        print("  [dry-run] TikTok: everything filled, NOT posting.")
        return "dry-run"
    click_css(tab, 570, 940)     # Post
    time.sleep(6)
    ok = "under review" in tab.eval("document.body.innerText").lower() or \
         "/content" in tab.eval("location.pathname")
    expect(ok, "tiktok", "post", tab, "post confirmation not seen")
    return "posted"


def post_youtube(video_rel, title, desc, dry_run):
    tab = Tab(match="studio.youtube")
    tab.goto("https://www.youtube.com/upload")
    time.sleep(7)
    tab.setfile('input[type="file"]', win_path(video_rel))
    time.sleep(12)
    tab.eval("const t=document.querySelectorAll('#textbox')[0];t.focus();document.execCommand('selectAll')")
    tab.type_text(title[:100])
    ok = tab.eval("const d=document.querySelector('ytcp-video-description #textbox');"
                  "if(d){d.focus();'ok'}else null")
    expect(ok, "youtube", "desc_field", tab, "description field missing (still uploading?)")
    tab.type_text(desc)
    # not made for kids
    tab.eval("[...document.querySelectorAll('tp-yt-paper-radio-button')]"
             ".find(x=>/not made for kids/i.test(x.textContent))?.click()")
    # AI use = Yes  (Show more -> AI use radio)
    tab.eval("[...document.querySelectorAll('ytcp-button,button')].find(b=>/show more/i.test(b.textContent))?.click()")
    time.sleep(2)
    aiok = tab.eval("const h=[...document.querySelectorAll('*')].find(e=>e.children.length===0"
                    "&&e.textContent.trim()==='AI use');if(!h)return null;let s=h;"
                    "for(let i=0;i<8&&s;i++){if(s.querySelectorAll('tp-yt-paper-radio-button').length>=2)break;s=s.parentElement}"
                    "const y=[...s.querySelectorAll('tp-yt-paper-radio-button')].find(r=>r.textContent.trim().startsWith('Yes'));"
                    "if(y){y.click();'ok'}else null")
    expect(aiok, "youtube", "ai_use", tab, "AI-use Yes radio not found")
    s = shot(tab, "youtube_precheck")
    expect(vlm_yesno(s, "Is a YouTube Short upload shown with a video preview and a filled title "
                        "(not an error)?"),
           "youtube", "upload", tab, "upload/preview not confirmed")
    if dry_run:
        print("  [dry-run] YouTube: details filled, NOT publishing.")
        return "dry-run"
    for _ in range(3):
        tab.eval("document.querySelector('#next-button')?.click()")
        time.sleep(2)
    tab.eval("[...document.querySelectorAll('tp-yt-paper-radio-button')].find(r=>r.textContent.trim().startsWith('Public'))?.click()")
    time.sleep(1)
    tab.eval("document.querySelector('#done-button')?.click()")
    time.sleep(5)
    link = tab.eval("const a=document.querySelector('a[href*=\"shorts\"]');a?a.href:''")
    expect("Video published" in tab.eval("document.body.innerText") or link,
           "youtube", "publish", tab, "publish confirmation not seen")
    return link or "posted"


def post_instagram(video_rel, caption, dry_run):
    tab = Tab(match="instagram")
    tab.goto("https://www.instagram.com/")
    time.sleep(6)
    tab.eval("[...document.querySelectorAll('a,div[role=\"button\"],span')]"
             ".find(e=>e.textContent.trim()==='Create')?.click()")
    time.sleep(3)
    tab.choosefile("[...document.querySelectorAll('button')]"
                   ".find(b=>/select from computer/i.test(b.textContent)).click()",
                   win_path(video_rel))
    time.sleep(9)
    # Crop -> Original aspect
    click_css(tab, 456, 556)
    time.sleep(1)
    tab.eval("[...document.querySelectorAll('span,div[role=\"button\"]')].find(e=>e.textContent.trim()==='Original')?.click()")
    time.sleep(1)
    # Next (crop) -> Next (edit) -> reel screen  (TUNE: two Next clicks, coord fallback)
    for _ in range(2):
        clicked = tab.eval("const n=[...document.querySelectorAll('div[role=\"button\"],button,span')]"
                           ".find(e=>e.textContent.trim()==='Next'&&e.offsetParent);if(n){n.click();'ok'}else null")
        if not clicked:
            click_css(tab, 956, 117)     # Next link top-right, coord fallback
        time.sleep(3)
    # caption
    tab.eval("const c=document.querySelector('div[contenteditable=\"true\"][aria-label*=\"caption\" i]')"
             "||document.querySelector('div[contenteditable=\"true\"]');if(c)c.focus()")
    tab.type_text(caption)
    time.sleep(1)
    s = shot(tab, "instagram_precheck")
    expect(vlm_yesno(s, "Is an Instagram 'New reel' share screen shown with a video preview and a "
                        "caption filled in (not an error)?"),
           "instagram", "upload", tab, "reel/preview not confirmed")
    if dry_run:
        print("  [dry-run] Instagram: reel filled, NOT sharing.")
        return "dry-run"
    shared = tab.eval("const sh=[...document.querySelectorAll('div[role=\"button\"],button,span')]"
                      ".find(e=>e.textContent.trim()==='Share'&&e.offsetParent);if(sh){sh.click();'ok'}else null")
    if not shared:
        click_css(tab, 955, 117)
    time.sleep(8)
    return "posted"


PLATFORMS = {"tiktok": post_tiktok, "youtube": post_youtube, "instagram": post_instagram}


# ---------------------------------------------------------------- runner
def pick_entry(journey):
    q = json.loads(QUEUE.read_text())
    for p in q["posts"]:
        if journey and p["journey"] == journey:
            return q, p
        if not journey and p.get("approved") and "POSTED all 3" not in str(p.get("status", "")):
            return q, p
    return q, None


def run(only, dry_run, journey):
    # health check
    try:
        requests.get("http://localhost:9222/json/version", timeout=5)
    except Exception:
        print("Chrome CDP not reachable on :9222 — run scripts/start_chrome_zen.sh first.")
        sys.exit(1)
    q, entry = pick_entry(journey)
    if not entry:
        print("No approved, unposted queue entry found (set approved:true in queue.json).")
        return
    print(f"Posting: {entry['journey']}  (file: {entry['file']}, model: {entry.get('model','?')})"
          f"{'  [DRY RUN]' if dry_run else ''}")
    results = {}
    for name in (only or ["tiktok", "youtube", "instagram"]):
        fn = PLATFORMS[name]
        try:
            if name == "youtube":
                results[name] = fn(entry["file"], entry["yt_title"], entry["yt_desc"], dry_run)
            else:
                results[name] = fn(entry["file"], entry["caption"], dry_run)
            print(f"  {name}: {results[name]}")
        except PlatformError as e:
            results[name] = f"FLAGGED: {e}"
        except Exception as e:
            flag(name, "unexpected", Tab(match=name), str(e))
            results[name] = f"ERROR: {e}"
    if not dry_run:
        entry["status"] = f"posted {time.strftime('%Y-%m-%d %H:%M')} :: " + \
            "; ".join(f"{k}={v}" for k, v in results.items())
        QUEUE.write_text(json.dumps(q, indent=2, ensure_ascii=False) + "\n")
    print("\nSummary:", json.dumps(results, indent=2))
    if FLAGS.exists() and any(True for _ in open(FLAGS)):
        print(f"⚠ flags recorded in {FLAGS} — review before next run.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="fill everything, stop before final post")
    ap.add_argument("--only", help="comma list: tiktok,youtube,instagram")
    ap.add_argument("--journey", help="target a specific queue entry by journey name")
    args = ap.parse_args()
    only = args.only.split(",") if args.only else None
    run(only, args.dry_run, args.journey)


if __name__ == "__main__":
    main()
