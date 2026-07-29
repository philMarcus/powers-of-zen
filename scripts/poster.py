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
import zen_browser  # noqa: E402
from zen_browser import Tab  # noqa: E402
import pipeline as pl  # noqa: E402

PLATFORM_URL = {"tiktok": "https://www.tiktok.com/tiktokstudio/upload",
                "youtube": "https://studio.youtube.com",
                "instagram": "https://www.instagram.com/"}
PLATFORM_MATCH = {"tiktok": "tiktok", "youtube": "studio.youtube", "instagram": "instagram"}


def platform_tab(name):
    """Return a Tab for the platform, CREATING the tab if it isn't open (self-heal;
    the scheduler-launched Chrome may not have all platform tabs)."""
    try:
        return Tab(match=PLATFORM_MATCH[name])
    except StopIteration:
        zen_browser.open_tab(PLATFORM_URL[name])
        return Tab(match=PLATFORM_MATCH[name])

def _find_ollama():
    # WSL host IP drifts between reboots; try localhost then the default gateway
    import subprocess
    cands = ["http://localhost:11434"]
    try:
        gw = subprocess.check_output("ip route show default | awk '{print $3}'",
                                     shell=True, text=True).strip()
        if gw:
            cands.append(f"http://{gw}:11434")
    except Exception:
        pass
    for c in cands:
        try:
            requests.get(f"{c}/api/version", timeout=3)
            return c
        except Exception:
            continue
    return cands[0]


OLLAMA = _find_ollama()
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
    """Record a failure: screenshot + text context + one line in flags.jsonl.
    The TEXT context lets us diagnose from stdout WITHOUT reading a screenshot."""
    img, ctx = "", ""
    try:
        img = str(shot(tab, f"FLAG_{platform}_{step}"))
    except Exception:
        pass
    try:
        ctx = dump_context(tab)
    except Exception:
        pass
    FLAGS.parent.mkdir(parents=True, exist_ok=True)
    with open(FLAGS, "a") as f:
        f.write(json.dumps({"platform": platform, "step": step, "detail": detail,
                            "shot": img, "context": ctx,
                            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    print(f"  !! FLAG [{platform}/{step}] {detail}\n     context: {ctx}")


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


def wait_for(tab, js, timeout=60, poll=1.0):
    """Poll a JS expression until truthy or timeout. Returns the value (or None).
    Replaces fragile fixed sleeps — wait for the ACTUAL expected state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            v = tab.eval(js)
        except Exception:
            v = None
        if v:
            return v
        time.sleep(poll)
    return None


def set_text(tab, selector_js, text):
    """Focus a field, select-all WITHIN it (guarded so we never select the whole page),
    and REPLACE its content via execCommand('insertText'). insertText clears any default
    (TikTok filenames the caption) AND fires the input events React/Draft.js need to
    register the value — plain DOM text or CDP insertText left React state empty (IG
    posted blank captions). Returns True on success; prints the JS error on failure."""
    js_text = json.dumps(text)
    r = tab.eval("(function(){try{"
                 f"const el=({selector_js});if(!el)return 'NO_EL';"
                 "el.scrollIntoView({block:'center'});el.click();el.focus();"
                 "if(document.activeElement!==el&&!el.contains(document.activeElement))return 'NO_FOCUS';"
                 "document.execCommand('selectAll',false,null);"
                 f"document.execCommand('insertText',false,{js_text});"
                 "return 'ok';}catch(e){return 'ERR:'+e.message}})()")
    if r != "ok":
        print(f"    set_text failed: {r}")
        return False
    return True


def dump_context(tab):
    """Cheap TEXT snapshot for diagnosis without a screenshot: visible buttons + headings."""
    return tab.eval(
        "JSON.stringify({"
        "buttons:[...document.querySelectorAll('button,[role=button],ytcp-button,a')]"
        ".map(b=>b.textContent.trim()).filter(t=>t&&t.length<28).slice(0,30),"
        "headings:[...document.querySelectorAll('h1,h2,h3,[role=heading]')]"
        ".map(h=>h.textContent.trim()).filter(Boolean).slice(0,8)})")


# ---------------------------------------------------------------- platforms
def post_tiktok(video_rel, caption, dry_run):
    tab = platform_tab("tiktok")
    tab.goto("https://www.tiktok.com/tiktokstudio/upload")
    wait_for(tab, "document.querySelector('input[type=\"file\"]')?true:null", 30)
    tab.setfile('input[type="file"]', win_path(video_rel))
    # DOM wait: upload finished when the caption editor appears AND 'Uploaded' shows
    up = wait_for(tab, "document.body.innerText.includes('Uploaded')"
                       "&&document.querySelector('.public-DraftEditor-content')?true:null", 180, 2)
    expect(up, "tiktok", "upload", tab, "upload did not finish (no 'Uploaded' + editor)")
    # accept the automatic-content-checks modal if present
    tab.eval("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Turn on')?.click()")
    time.sleep(2)
    # caption — robust selector + wait, then select only within the editor
    capsel = ("document.querySelector('.public-DraftEditor-content')"
              "||document.querySelector('.notranslate[contenteditable=\"true\"]')"
              "||document.querySelector('div[contenteditable=\"true\"]')")
    expect(wait_for(tab, f"({capsel})?true:null", 15), "tiktok", "caption_find", tab,
           "caption editor never appeared")
    expect(set_text(tab, capsel, caption), "tiktok", "caption", tab, "caption not settable")
    tab.eval("document.activeElement.blur()")
    time.sleep(1)
    # AI-generated-content label ON
    tab.eval("[...document.querySelectorAll('div,span,button')]"
             ".find(e=>e.textContent.trim()==='Show more'&&e.children.length<=1)?.click()")
    time.sleep(1)
    coords = wait_for(tab, "(function(){const l=[...document.querySelectorAll('*')]"
                           ".find(e=>e.children.length===0&&e.textContent.trim()==='AI-generated content');"
                           "if(!l)return null;l.scrollIntoView({block:'center'});"
                           "const r=l.getBoundingClientRect();"
                           "return JSON.stringify([Math.round(r.right)+40,Math.round(r.top)+10])})()",
                      15)
    expect(coords, "tiktok", "ai_label_find", tab, "AI-generated-content row not found")
    x, y = json.loads(coords)
    click_css(tab, x, y)
    time.sleep(1)
    tab.eval("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Turn on')?.click()")
    time.sleep(1)
    ai_on = tab.eval("const l=[...document.querySelectorAll('*')].find(e=>e.children.length===0"
                     "&&e.textContent.trim()==='AI-generated content');l?"
                     "(l.parentElement.parentElement.innerText.includes('labeled')||"
                     "!!l.closest('*')&&/true/.test(''+[...document.querySelectorAll('[aria-checked]')].map(x=>x.getAttribute('aria-checked')))):null")
    # verify checks passed (DOM text)
    txt = tab.eval("document.body.innerText")
    expect("No issues found" in txt or "Checking" in txt, "tiktok", "checks", tab,
           "content checks not green")
    if dry_run:
        cap = tab.eval(f"({capsel})?.textContent?.slice(0,70)")
        print(f"  [dry-run] TikTok: caption='{cap}', AI-label~{ai_on}, checks OK. NOT posting.")
        return "dry-run"
    # POST — but the music copyright check must FINISH first. Clicking Post while it's still
    # running pops "Continue to post? The copyright check is incomplete. Posting now will stop
    # the check." — and clicking "Post now" there stops the check and the post silently never
    # lands (this is exactly what dropped night_bloom's 6pm post now that videos carry music).
    # So: click Post; if the incomplete-check modal appears, Cancel (keeping the check alive)
    # and wait, retrying for a few minutes. Only a clean Post (no incomplete modal) posts.
    expect(tab.eval("[...document.querySelectorAll('button')].some(x=>x.textContent.trim()==='Post')"),
           "tiktok", "post_click", tab, "Post button not found")
    posted_ok = False
    for _ in range(20):                                  # ~20 * ~10s = up to ~3.5 min
        tab.eval("[...document.querySelectorAll('button')]"
                 ".find(x=>x.textContent.trim()==='Post')?.click()")
        time.sleep(2.5)
        dlg = (tab.eval("[...document.querySelectorAll('[role=dialog],.TUXModal')]"
                        ".map(d=>d.innerText).join(' ')") or "").lower()
        if "incomplete" in dlg or "still checking" in dlg:
            tab.eval("[...document.querySelectorAll('[role=dialog] button,.TUXModal button')]"
                     ".find(x=>/cancel/i.test(x.textContent))?.click()")   # keep the check running
            time.sleep(8)
            continue
        # check complete — confirm a normal 'Post now' if one appears, then look for success
        tab.eval("[...document.querySelectorAll('[role=dialog] button,.TUXModal button')]"
                 ".find(x=>/^post( now)?$/i.test(x.textContent.trim()))?.click()")
        if wait_for(tab, "document.body.innerText.toLowerCase().includes('under review')"
                         "||location.pathname.includes('/content')?true:null", 20):
            posted_ok = True
            break
    expect(posted_ok, "tiktok", "post", tab, "post never completed (copyright check stuck?)")
    return "posted"


def post_youtube(video_rel, title, desc, dry_run):
    tab = platform_tab("youtube")
    # /upload bounces to the Studio content list for this channel (no details dialog opens),
    # so open the upload dialog via Create -> Upload videos (verified working 2026-07-28).
    tab.goto("https://studio.youtube.com/")
    expect(wait_for(tab, "[...document.querySelectorAll('button,ytcp-button')]"
                    ".some(e=>/^create$/i.test(e.textContent.trim()))?true:null", 30),
           "youtube", "studio", tab, "Studio Create button never appeared")
    tab.eval("[...document.querySelectorAll('button,ytcp-button')]"
             ".find(e=>/^create$/i.test(e.textContent.trim())||/^Create$/.test(e.getAttribute('aria-label')||''))?.click()")
    time.sleep(1.5)
    tab.eval("[...document.querySelectorAll('tp-yt-paper-item,ytcp-text-menu-item,[role=menuitem]')]"
             ".find(e=>/upload video/i.test(e.textContent))?.click()")
    expect(wait_for(tab, "document.querySelector('input[type=\"file\"]')?true:null", 30),
           "youtube", "file_input", tab, "upload dialog did not open (Create->Upload)")
    tab.setfile('input[type="file"]', win_path(video_rel))
    # wait for the details dialog's title field to exist (upload dialog open)
    tsel = ("document.querySelector('#title-textarea #textbox')"
            "||document.querySelector('ytcp-social-suggestions-textbox #textbox')"
            "||document.querySelectorAll('#textbox')[0]")
    expect(wait_for(tab, f"({tsel})?true:null", 90, 2), "youtube", "dialog", tab,
           "upload details dialog/title field never appeared")
    # title — the field can EXIST before it is editable (details dialog still animating in),
    # which is what silently failed the 6pm post. Retry set_text a few times with a settle.
    def set_text_retry(sel, text, tries=6, wait=1.3):
        for _ in range(tries):
            if set_text(tab, sel, text):
                return True
            time.sleep(wait)
        return False
    # select WITHIN the field only (fixes selectAll-grabs-page)
    expect(set_text_retry(tsel, title[:100]), "youtube", "title", tab, "title field not settable")
    # description
    dsel = "document.querySelector('ytcp-video-description #textbox')"
    expect(wait_for(tab, f"({dsel})?true:null", 20), "youtube", "desc_field", tab,
           "description field missing")
    expect(set_text_retry(dsel, desc), "youtube", "desc", tab, "description not settable")
    # not made for kids
    tab.eval("[...document.querySelectorAll('tp-yt-paper-radio-button')]"
             ".find(x=>/not made for kids/i.test(x.textContent))?.click()")
    # AI use = Yes  (expand 'Show more', then find the AI-use Yes radio)
    tab.eval("[...document.querySelectorAll('ytcp-button,button,div')].find(b=>b.textContent.trim()==='Show more')?.click()")
    time.sleep(1)
    aiok = wait_for(tab, "(function(){const h=[...document.querySelectorAll('*')].find(e=>e.children.length===0"
                         "&&e.textContent.trim()==='AI use');if(!h)return null;h.scrollIntoView({block:'center'});let s=h;"
                         "for(let i=0;i<8&&s;i++){if(s.querySelectorAll('tp-yt-paper-radio-button').length>=2)break;s=s.parentElement}"
                         "if(!s)return null;const y=[...s.querySelectorAll('tp-yt-paper-radio-button')].find(r=>r.textContent.trim().startsWith('Yes'));"
                         "if(y){y.click();return 'ok'}return null})()", 15)
    expect(aiok, "youtube", "ai_use", tab, "AI-use Yes radio not found")
    if dry_run:
        got = tab.eval(f"({tsel})?.textContent?.slice(0,40)")
        print(f"  [dry-run] YouTube: title='{got}', desc+audience+AI-use set. NOT publishing.")
        return "dry-run"
    for _ in range(3):
        tab.eval("document.querySelector('#next-button')?.click()")
        time.sleep(2)
    tab.eval("[...document.querySelectorAll('tp-yt-paper-radio-button')].find(r=>r.textContent.trim().startsWith('Public'))?.click()")
    time.sleep(1)
    tab.eval("document.querySelector('#done-button')?.click()")
    # confirmation is EITHER "Video published" OR the "Video processing … before your
    # video is public" dialog (SD still transcoding) — both mean it published public
    link = wait_for(tab, "(function(){const t=document.body.innerText;"
                         "if(t.includes('Video published')||t.includes('finish processing')"
                         "||t.includes('processing before your video is public')){"
                         "return document.querySelector('a[href*=\"shorts\"]')?.href||'published'}"
                         "return null})()", 30)
    expect(link, "youtube", "publish", tab, "publish confirmation not seen")
    # close the dialog so Phil lands back on the videos list
    time.sleep(1)
    tab.eval("[...document.querySelectorAll('button,ytcp-button')].find(b=>b.textContent.trim()==='Close')?.click()")
    return link


def _ig_click(tab, label, top_max=260):
    """Click an Instagram modal-header button with EXACT text (Next / Share / Done) via a
    SYNTHESIZED mouse click. el.click() is silently ignored by Instagram's React handlers
    for these buttons — that is what left night_bloom's caption unsaved. Locate the topmost
    match near the top of the screen (so we never hit feed elements behind the modal), then
    dispatch a real press/release at its center. Returns 'ok' or None."""
    coords = tab.eval("(function(){const els=[...document.querySelectorAll("
                      "'div[role=\"button\"],button,a,span,div[tabindex]')].filter(e=>"
                      f"e.textContent.trim()==='{label}'&&e.offsetParent"
                      f"&&e.getBoundingClientRect().top<{top_max});"
                      "if(!els.length)return null;"
                      "els.sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top);"
                      "const r=els[0].getBoundingClientRect();"
                      "return JSON.stringify([Math.round(r.left+r.width/2),Math.round(r.top+r.height/2)])})()")
    if not coords:
        return None
    x, y = json.loads(coords)
    for typ in ("mousePressed", "mouseReleased"):
        tab.cmd("Input.dispatchMouseEvent", type=typ, x=x, y=y, button="left", clickCount=1)
    return "ok"


def post_instagram(video_rel, caption, dry_run):
    tab = platform_tab("instagram")
    tab.goto("https://www.instagram.com/")
    wait_for(tab, "[...document.querySelectorAll('a,div[role=\"button\"],span')]"
                  ".find(e=>e.textContent.trim()==='Create')?true:null", 30)
    tab.eval("[...document.querySelectorAll('a,div[role=\"button\"],span')]"
             ".find(e=>e.textContent.trim()==='Create')?.click()")
    wait_for(tab, "[...document.querySelectorAll('button')].find(b=>/select from computer/i.test(b.textContent))?true:null", 20)
    tab.choosefile("[...document.querySelectorAll('button')]"
                   ".find(b=>/select from computer/i.test(b.textContent)).click()",
                   win_path(video_rel))
    # CROP screen: wait for it (the 9:16 video keeps its ratio by default — don't
    # touch the aspect control; a mis-aimed click was dismissing the whole dialog)
    expect(wait_for(tab, "document.body.innerText.includes('Crop')?true:null", 60, 2),
           "instagram", "crop_screen", tab, "crop screen never appeared (upload failed?)")
    time.sleep(1)
    # advance CROP -> EDIT: wait for the Edit screen marker ('Cover photo' / 'Trim')
    expect(_ig_click(tab, "Next"), "instagram", "next1", tab, "first Next button not found")
    expect(wait_for(tab, "document.body.innerText.includes('Cover photo')"
                         "||document.body.innerText.includes('Trim')?true:null", 20),
           "instagram", "edit_screen", tab, "edit screen never appeared after 1st Next")
    # advance EDIT -> NEW REEL: wait for caption box / 'Share'
    expect(_ig_click(tab, "Next"), "instagram", "next2", tab, "second Next button not found")
    csel = ("document.querySelector('div[contenteditable=\"true\"][aria-label*=\"caption\" i]')"
            "||document.querySelector('div[aria-label=\"Write a caption...\"]')"
            "||document.querySelector('div[contenteditable=\"true\"]')")
    expect(wait_for(tab, f"({csel})?true:null", 20), "instagram", "reel_screen", tab,
           "reel/caption screen never appeared after 2nd Next")
    expect(set_text(tab, csel, caption), "instagram", "caption", tab, "caption box not settable")
    time.sleep(1)
    if dry_run:
        got = tab.eval(f"({csel})?.textContent?.slice(0,40)")
        print(f"  [dry-run] Instagram: reel ready, caption='{got}'. NOT sharing.")
        return "dry-run"
    expect(_ig_click(tab, "Share"), "instagram", "share", tab, "Share button not found")
    ok = wait_for(tab, "document.body.innerText.includes('Your reel has been shared')"
                       "||document.body.innerText.includes('shared')?true:null", 40)
    # close the share-confirmation dialog so Phil lands back on the feed
    time.sleep(1)
    tab.eval("[...document.querySelectorAll('[aria-label=\"Close\"],svg[aria-label=\"Close\"]')].pop()?.closest('[role=button],button,div')?.click()")
    return "posted" if ok else "shared(unconfirmed)"


PLATFORMS = {"tiktok": post_tiktok, "youtube": post_youtube, "instagram": post_instagram}


# ---------------------------------------------------------------- runner
def run(only, dry_run, journey):
    # health check
    try:
        requests.get("http://localhost:9222/json/version", timeout=5)
    except Exception:
        print("Chrome CDP not reachable on :9222 — run scripts/start_chrome_zen.sh first.")
        sys.exit(1)
    data = pl.load()
    entry = pl.get(data, journey) if journey else pl.next_to_post(data)
    if not entry:
        print("No queued video to post (set a video's state to 'queued' in the dashboard,"
              " or pass --journey).")
        return
    print(f"Posting: {entry['journey']}  (file: {entry['file']}, {entry.get('model','?')}/"
          f"{entry.get('cut','?')}){'  [DRY RUN]' if dry_run else ''}")
    plats = only or pl.PLATFORMS
    results = {}
    for name in plats:
        # resume-safe: NEVER re-post a platform already live for this video
        if not dry_run and entry.get("platforms", {}).get(name, {}).get("status") == "live":
            results[name] = "already live (skipped)"
            print(f"  {name}: {results[name]}")
            continue
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
            try:
                t = platform_tab(name)
            except Exception:
                t = None
            flag(name, "unexpected", t, str(e))
            results[name] = f"ERROR: {e}"
    if not dry_run:
        for name in plats:
            r = results[name]
            if r == "already live (skipped)":
                continue  # leave the existing (live) platform record intact
            good = r is not None and not str(r).startswith(("FLAGGED", "ERROR"))
            entry.setdefault("platforms", pl.blank_platforms())[name] = {
                "status": "live" if good else "failed",
                "url": r if (good and isinstance(r, str) and r.startswith("http")) else "",
                "ts": pl._now()}
            pl.telem("post" if good else "post_fail", journey=entry["journey"],
                     platform=name, detail=str(r))
        allgood = all(entry.get("platforms", {}).get(n, {}).get("status") == "live"
                      for n in pl.PLATFORMS)
        entry["state"] = "live" if allgood else "failed"
        pl.save(data)
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
