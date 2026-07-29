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


def set_text_verified(tab, selector_js, text, tries=10, wait=1.2):
    """set_text + READ BACK confirmation. set_text only proves execCommand ran, not that the
    value landed — a field can exist-but-not-yet-be-editable (dialog still animating), where
    focus doesn't stick and the text silently never applies (this is what failed YouTube's
    title at 8am). Retry until the field's text actually contains what we set. Returns bool."""
    needle = _norm(text)[:20]
    for _ in range(tries):
        set_text(tab, selector_js, text)
        got = tab.eval(f"(function(){{const el=({selector_js});return el?(el.textContent||el.value||''):''}})()")
        if needle and needle in _norm(got or ""):
            return True
        time.sleep(wait)
    return False


def dump_context(tab):
    """Cheap TEXT snapshot for diagnosis without a screenshot: visible buttons + headings."""
    return tab.eval(
        "JSON.stringify({"
        "buttons:[...document.querySelectorAll('button,[role=button],ytcp-button,a')]"
        ".map(b=>b.textContent.trim()).filter(t=>t&&t.length<28).slice(0,30),"
        "headings:[...document.querySelectorAll('h1,h2,h3,[role=heading]')]"
        ".map(h=>h.textContent.trim()).filter(Boolean).slice(0,8)})")


# ---------------------------------------------------------------- platforms
def _norm(s):
    """Lowercase, keep only alphanumerics — for matching a caption against a content-list row
    regardless of emoji/whitespace/hashtag differences."""
    return "".join(c for c in (s or "").lower() if c.isalnum())


def verify_tiktok_posted(tab, caption, timeout=100):
    """GROUND TRUTH: a TikTok post only counts if it actually shows up in the account's
    content list. TikTok drops some posts (custom audio on a new account) AFTER flashing a
    publish/under-review signal — so the in-flow 'success' string LIES. Navigate to the
    content list and confirm a row whose caption matches this post. Returns True/False.

    The needle is the caption's leading words (hashtags/emoji stripped); captions are unique
    per journey, so a normalized-substring match is reliable."""
    plain = caption.split("#")[0]                      # drop hashtags
    needle = _norm(plain)[:18]
    if len(needle) < 6:                                # caption too short to match safely
        needle = _norm(caption)[:18]
    tab.goto("https://www.tiktok.com/tiktokstudio/content")
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = tab.eval("JSON.stringify([...document.querySelectorAll('a[href*=\"/video/\"]')]"
                        ".map(a=>{const r=a.closest('tr')||a.closest('[class]');"
                        "return (r?r.innerText:a.innerText)}))")
        try:
            for row in json.loads(rows or "[]"):
                if needle and needle in _norm(row):
                    return True
        except Exception:
            pass
        time.sleep(4)
    return False


def tiktok_set_ai_label(tab, tries=5):
    """Turn ON 'AI-generated content' and VERIFY it stuck. State lives in the switch's class
    (Switch__content--checked-true). A SYNTHESIZED click on the switch element flips it — the
    old code used click_css (which multiplies by COORD_SCALE) on raw getBoundingClientRect
    coords, double-scaling them so it clicked off-target and silently missed. Returns True only
    when the switch verifies ON; the caller must refuse to post otherwise."""
    tab.eval("[...document.querySelectorAll('div,span,button')]"
             ".find(e=>e.textContent.trim()==='Show more'&&e.children.length<=1)?.click()")
    time.sleep(1)
    ROW = ("(function(){const l=[...document.querySelectorAll('*')].find(e=>e.children.length===0"
           "&&e.textContent.trim()==='AI-generated content');if(!l)return null;let row=l;"
           "for(let i=0;i<6;i++){row=row.parentElement||row;if(row.querySelector('.Switch__root'))break;}"
           "return row})()")

    def state():
        return tab.eval(f"(function(){{const row={ROW};if(!row)return 'NO_ROW';"
                        "const c=row.querySelector('.Switch__content');"
                        "return c?(c.className.includes('checked-true')?'ON':'OFF'):'NO_SWITCH'}})()")

    for _ in range(tries):
        st = state()
        if st == "ON":
            return True
        if st in ("NO_ROW", "NO_SWITCH"):
            time.sleep(1.5)
            continue
        coords = tab.eval(f"(function(){{const row={ROW};const s=row&&row.querySelector('.Switch__root');"
                          "if(!s)return null;s.scrollIntoView({block:'center'});const b=s.getBoundingClientRect();"
                          "return JSON.stringify([Math.round(b.left+b.width/2),Math.round(b.top+b.height/2)])}})()")
        if coords:
            x, y = json.loads(coords)
            tab.click(x, y)                       # synthesized press+release, CSS px (no scaling)
            time.sleep(1)
            # some accounts show a 'Turn on' confirmation modal; click it if present
            tab.eval("[...document.querySelectorAll('[role=dialog] button,.TUXModal button,button')]"
                     ".find(b=>/^turn on$/i.test(b.textContent.trim()))?.click()")
            time.sleep(1)
    return state() == "ON"


def wait_tiktok_checks(tab, timeout=720, poll=6):
    """Wait for BOTH TikTok checks to finish before we click Post. The upload runs a 'Music
    copyright check' (~30s) and a 'Content check lite' (est. up to ~10 min). Clicking Post
    while either is still running pops the 'copyright check is incomplete' modal — and the
    old code probed that by clicking Post/Cancel in a tight loop, which races the check and
    can look spammy. Instead we passively poll the Checks panel until no 'Checking in
    progress' remains. Returns the music-copyright status line (or None on timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        txt = tab.eval("document.body.innerText") or ""
        if "Checking in progress" not in txt and "Music copyright check" in txt:
            # both checks resolved — return the music-copyright verdict for a safety gate
            after = txt.split("Music copyright check", 1)[1][:120]
            return after.strip().split("\n")[0] if after.strip() else "resolved"
        time.sleep(poll)
    return None


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
    # AI-generated-content label ON — ALWAYS declare AI content, and REFUSE to post if we
    # can't confirm it (posting unlabeled AI video risks account penalties).
    expect(tiktok_set_ai_label(tab), "tiktok", "ai_label", tab,
           "could NOT confirm 'AI-generated content' label is ON — refusing to post (compliance)")
    # the Checks panel must at least exist (upload registered)
    expect(wait_for(tab, "document.body.innerText.includes('Music copyright check')"
                         "||document.body.innerText.includes('Checks')?true:null", 30),
           "tiktok", "checks", tab, "checks panel never appeared")
    if dry_run:
        cap = tab.eval(f"({capsel})?.textContent?.slice(0,70)")
        print(f"  [dry-run] TikTok: caption='{cap}', AI-label ON (verified). NOT posting.")
        return "dry-run"
    # POST — but the music copyright check must FINISH first. Clicking Post while it's still
    # running pops "Continue to post? The copyright check is incomplete. Posting now will stop
    # the check." — and clicking "Post now" there stops the check and the post silently never
    # lands (this is exactly what dropped night_bloom's 6pm post now that videos carry music).
    # So: click Post; if the incomplete-check modal appears, Cancel (keeping the check alive)
    # and wait, retrying for a few minutes. Only a clean Post (no incomplete modal) posts.
    # WAIT for both checks to finish (music copyright + content check) BEFORE clicking Post.
    # Clicking during a check pops the 'incomplete' modal; probing it with Post/Cancel races
    # the check and risks flagging the account. Passive wait, then a single clean Post.
    music_status = wait_tiktok_checks(tab)
    expect(music_status is not None, "tiktok", "checks_wait", tab,
           "checks never finished (still 'Checking in progress' after wait)")
    print(f"    tiktok checks done — music copyright: {music_status!r}")
    # safety gate: if the music copyright check flagged a match, DON'T post (it would drop)
    if music_status and "no issues" not in music_status.lower() and "resolved" not in music_status.lower():
        expect(False, "tiktok", "copyright", tab,
               f"music copyright check did not pass: {music_status!r} — not posting")
    expect(tab.eval("[...document.querySelectorAll('button')].some(x=>x.textContent.trim()==='Post')"),
           "tiktok", "post_click", tab, "Post button not found")
    # single Post click. If the incomplete-check modal STILL appears, Cancel (never 'Post now'
    # — that stops the check and drops the post), re-wait once, and try one more time.
    posted_ok = False
    for attempt in range(3):
        tab.eval("[...document.querySelectorAll('button')]"
                 ".find(x=>x.textContent.trim()==='Post')?.click()")
        time.sleep(3)
        dlg = (tab.eval("[...document.querySelectorAll('[role=dialog],.TUXModal')]"
                        ".map(d=>d.innerText).join(' ')") or "").lower()
        if "incomplete" in dlg or "still checking" in dlg:
            print(f"    incomplete-check modal on attempt {attempt+1} — cancelling, re-waiting")
            tab.eval("[...document.querySelectorAll('[role=dialog] button,.TUXModal button')]"
                     ".find(x=>/cancel/i.test(x.textContent))?.click()")
            wait_tiktok_checks(tab)
            continue
        if wait_for(tab, "document.body.innerText.toLowerCase().includes('under review')"
                         "||location.pathname.includes('/content')?true:null", 25):
            posted_ok = True
            break
    expect(posted_ok, "tiktok", "post", tab, "post never completed (copyright check stuck?)")
    # GROUND TRUTH: the in-flow signal only means TikTok ACCEPTED the upload — it can still
    # drop the post (custom audio on a new account). Do not report success until the video
    # actually appears in the content list. This is what stops the recurring false-positive.
    expect(verify_tiktok_posted(tab, caption), "tiktok", "verify_live", tab,
           "published signal seen but video is ABSENT from the content list — TikTok dropped "
           "it (likely custom audio on a new account). Reported as FAILED, not live.")
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
    # which is what silently failed the 8am post. set_text_verified reads back the value and
    # retries until the text actually lands (not just until execCommand runs).
    expect(set_text_verified(tab, tsel, title[:100]), "youtube", "title", tab,
           "title never confirmed set (field not editable in time?)")
    # description
    dsel = "document.querySelector('ytcp-video-description #textbox')"
    expect(wait_for(tab, f"({dsel})?true:null", 20), "youtube", "desc_field", tab,
           "description field missing")
    expect(set_text_verified(tab, dsel, desc), "youtube", "desc", tab, "description not confirmed set")
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


def verify_instagram_posted(tab, caption, timeout=60):
    """GROUND TRUTH for Instagram: after Share, confirm the newest reel on the profile actually
    carries THIS caption. The in-flow 'shared' text is an unreliable signal (it matched once
    when the post had NOT gone through). Read the reel's og:description (the real caption) and
    match a normalized needle. Returns True/False."""
    needle = _norm(caption.split("#")[0])[:18] or _norm(caption)[:18]
    deadline = time.time() + timeout
    while time.time() < deadline:
        tab.goto("https://www.instagram.com/powers.of.zen/")
        time.sleep(5)
        href = tab.eval("document.querySelector('main a[href*=\"/reel/\"],main a[href*=\"/p/\"]')"
                        "?.getAttribute('href')")
        if href:
            tab.goto("https://www.instagram.com" + href)
            time.sleep(4)
            og = tab.eval("document.querySelector('meta[property=\"og:description\"]')"
                          "?.getAttribute('content')||''") or ""
            if needle and needle in _norm(og):
                return href
        time.sleep(4)
    return None


def _ig_preview_ratio(tab):
    """width/height of the largest media element in the IG dialog (the crop preview).
    ~0.56 = 9:16 portrait (phone), ~1.0 = square."""
    return tab.eval(r"""(function(){
      const meds=[...document.querySelectorAll('[role=dialog] video,[role=dialog] img,[role=dialog] canvas')];
      if(!meds.length)return null;
      meds.sort((a,b)=>{const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();
        return rb.width*rb.height-ra.width*ra.height});
      const r=meds[0].getBoundingClientRect();return r.height?+(r.width/r.height).toFixed(3):null;})()""")


def _ig_select_original_crop(tab, tries=3):
    """On IG's crop screen, choose the 'Original' aspect so our 9:16 phone-shaped video isn't
    cropped to SQUARE — IG defaults to 1:1, which silently squared the last three posts. Open
    the 'Select crop' control, click 'Original', and VERIFY the preview became portrait.
    Returns True only when the preview ratio is portrait (< 0.75)."""
    for _ in range(tries):
        r = _ig_preview_ratio(tab)
        if r is not None and r < 0.75:
            return True
        # open the Select crop (aspect) popup — it's an svg[aria-label="Select crop"] control
        coords = tab.eval(r"""(function(){const s=document.querySelector('svg[aria-label="Select crop"]');
          if(!s)return null;const el=s.closest('div[role=button],button')||s.parentElement;const b=el.getBoundingClientRect();
          return JSON.stringify([Math.round(b.left+b.width/2),Math.round(b.top+b.height/2)]);})()""")
        if coords:
            x, y = json.loads(coords)
            for typ in ("mousePressed", "mouseReleased"):
                tab.cmd("Input.dispatchMouseEvent", type=typ, x=x, y=y, button="left", clickCount=1)
            time.sleep(1.2)
        # click the exact 'Original' option (synthesized — el.click is ignored by IG React)
        oc = tab.eval(r"""(function(){const els=[...document.querySelectorAll('span,div[role=button],button')]
          .filter(e=>e.textContent.trim()==='Original'&&e.offsetParent);if(!els.length)return null;
          els.sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top);
          const b=els[0].getBoundingClientRect();return JSON.stringify([Math.round(b.left+b.width/2),Math.round(b.top+b.height/2)]);})()""")
        if oc:
            x, y = json.loads(oc)
            for typ in ("mousePressed", "mouseReleased"):
                tab.cmd("Input.dispatchMouseEvent", type=typ, x=x, y=y, button="left", clickCount=1)
            time.sleep(1.2)
    r = _ig_preview_ratio(tab)
    return r is not None and r < 0.75


def _ig_advance(tab, label, marker_js, tries=4, settle=2.5):
    """Click an IG modal button (Next/Share) and CONFIRM the expected next screen actually
    appeared, retrying the click if it didn't. IG's React occasionally drops the first
    synthesized click, and a not-yet-rendered next screen makes a fire-and-wait step fail —
    that intermittent miss is what stalled the 8am IG post at 'edit screen after 1st Next'.
    Returns True once the marker shows, else False."""
    for _ in range(tries):
        _ig_click(tab, label)
        if wait_for(tab, marker_js, timeout=8, poll=0.5):
            return True
        time.sleep(settle)
    return False


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
    # CROP screen: wait for it. Our video is 9:16 and IG Reels preserve that ratio by default
    # (the aspect popup is icon-only and mis-clicks dismissed the dialog, so we don't touch it).
    expect(wait_for(tab, "document.body.innerText.includes('Crop')?true:null", 60, 2),
           "instagram", "crop_screen", tab, "crop screen never appeared (upload failed?)")
    time.sleep(1)
    # select the ORIGINAL (phone 9:16) crop — IG defaults to square and quietly cropped the
    # last three posts. Fail loud rather than post a squared video.
    expect(_ig_select_original_crop(tab), "instagram", "crop_original", tab,
           "could not confirm Original (phone 9:16) crop — refusing to post a squared video")
    # advance CROP -> EDIT: click Next and CONFIRM the Edit screen ('Cover photo'/'Trim')
    # appeared, retrying the click if it didn't (the 8am stall was a dropped first click).
    expect(_ig_advance(tab, "Next", "document.body.innerText.includes('Cover photo')"
                                    "||document.body.innerText.includes('Trim')?true:null"),
           "instagram", "edit_screen", tab, "edit screen never appeared after Next (crop->edit)")
    # advance EDIT -> NEW REEL: click Next and CONFIRM the caption box appeared
    csel = ("document.querySelector('div[contenteditable=\"true\"][aria-label*=\"caption\" i]')"
            "||document.querySelector('div[aria-label=\"Write a caption...\"]')"
            "||document.querySelector('div[contenteditable=\"true\"]')")
    expect(_ig_advance(tab, "Next", f"({csel})?true:null"),
           "instagram", "reel_screen", tab, "caption screen never appeared after Next (edit->reel)")
    expect(set_text(tab, csel, caption), "instagram", "caption", tab, "caption box not settable")
    time.sleep(1)
    if dry_run:
        got = tab.eval(f"({csel})?.textContent?.slice(0,40)")
        print(f"  [dry-run] Instagram: reel ready, caption='{got}'. NOT sharing.")
        return "dry-run"
    expect(_ig_click(tab, "Share"), "instagram", "share", tab, "Share button not found")
    # wait for the in-flow confirmation (best-effort), THEN verify against the live profile —
    # the 'shared' text alone has false-positived (claimed shared when the reel never posted).
    wait_for(tab, "document.body.innerText.includes('Your reel has been shared')"
                  "||document.body.innerText.includes('shared')?true:null", 40)
    href = verify_instagram_posted(tab, caption)
    expect(href, "instagram", "verify_live", tab,
           "Share clicked but the newest reel does NOT carry this caption — post did not go "
           "through. Reported as FAILED, not live.")
    return f"https://www.instagram.com{href}"
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
    plats = list(only or pl.PLATFORMS)
    # respect paused platforms on the SCHEDULED path (no --only). A manual --only run overrides
    # the pause (explicit intent) but warns. Pausing TikTok stops the scheduler from hammering a
    # new account that's under review/spam-flagged — see meta.paused_platforms.
    paused = pl.paused_platforms(data)
    if paused:
        if only:
            for p in [p for p in plats if p in paused]:
                print(f"  ⚠ {p} is PAUSED (meta.paused_platforms) but --only forces it — proceeding.")
        else:
            skipped = [p for p in plats if p in paused]
            plats = [p for p in plats if p not in paused]
            if skipped:
                print(f"  ⏸ skipping paused platform(s): {', '.join(skipped)}")
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
