#!/usr/bin/env python3
"""Recaption a LIVE Powers of Zen post — edit the caption/title on already-published
videos across TikTok / YouTube / Instagram. Reads the (updated) caption from
pipeline.json, so: edit in the dashboard → run this to push it to the live posts.

Reuses the poster's CDP + assertion + fail-loud infrastructure. Editing is simpler than
posting (no upload/checks/publish) — just navigate to the post, replace the caption
field, save.

Usage:
  python3 scripts/recaption.py <journey>            # push pipeline caption to all 3
  python3 scripts/recaption.py <journey> --dry-run  # fill, DON'T save
  python3 scripts/recaption.py <journey> --only youtube
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402
import zen_browser  # noqa: E402
from poster import (platform_tab, set_text, wait_for, expect, flag,  # noqa: E402
                    PlatformError, click_css)


def edit_youtube(v, dry_run):
    url = v["platforms"]["youtube"].get("url", "")
    vid = url.rstrip("/").split("/")[-1].split("?")[0] if url else ""
    expect(vid, "youtube", "video_id", None, "no YouTube video id stored")
    tab = platform_tab("youtube")
    tab.goto(f"https://studio.youtube.com/video/{vid}/edit")
    tsel = ("document.querySelector('#title-textarea #textbox')"
            "||document.querySelector('ytcp-social-suggestions-textbox #textbox')"
            "||document.querySelectorAll('#textbox')[0]")
    expect(wait_for(tab, f"({tsel})?true:null", 30), "youtube", "edit_page", tab,
           "video edit page/title field not found")
    expect(set_text(tab, tsel, v["yt_title"]), "youtube", "title", tab, "title not settable")
    dsel = "document.querySelector('ytcp-video-description #textbox')"
    if tab.eval(f"({dsel})?true:null"):
        set_text(tab, dsel, v["yt_desc"])
    if dry_run:
        got = tab.eval(f"({tsel})?.textContent?.slice(0,50)")
        print(f"  [dry-run] YouTube: title now '{got}', NOT saving.")
        return "dry-run"
    saved = tab.eval("(function(){const b=document.querySelector('#save')"
                     "||[...document.querySelectorAll('ytcp-button,button')].find(x=>x.textContent.trim()==='Save');"
                     "if(b){b.click();return 'ok'}return null})()")
    expect(saved, "youtube", "save", tab, "Save button not found")
    ok = wait_for(tab, "document.body.innerText.includes('saved')"
                       "||document.body.innerText.includes('Changes saved')?true:null", 20)
    return "recaptioned" if ok else "saved(unconfirmed)"


def edit_tiktok(v, dry_run):
    tab = platform_tab("tiktok")
    tab.goto("https://www.tiktok.com/tiktokstudio/content")
    expect(wait_for(tab, "document.querySelector('a[href*=\"/video/\"]')?true:null", 20),
           "tiktok", "content_list", tab, "posts list not loaded")
    # hover the top (most recent) post row to reveal its action icons
    coords = tab.eval("(function(){const a=document.querySelector('a[href*=\"/video/\"]');"
                      "const r=(a.closest('[class]')||a).getBoundingClientRect();"
                      "return JSON.stringify([Math.round(r.left+r.width/2),Math.round(r.top+r.height/2)])})()")
    cx, cy = json.loads(coords)
    tab.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=cx, y=cy)
    time.sleep(1.5)
    # Actions column icons are hover-revealed; find small clickables in this row's y-band,
    # on the right side, and click the LEFTMOST (pencil = edit). Document-wide (they sit in
    # a separate cell, not inside the title link).
    clicked = tab.eval(f"(function(){{const cy={cy};"
                       "const ic=[...document.querySelectorAll('svg,button,[role=\"button\"],a')]"
                       ".filter(e=>{const b=e.getBoundingClientRect();return b.width>0&&b.width<70"
                       "&&Math.abs(b.top+b.height/2-cy)<28&&b.left>window.innerWidth*0.62})"
                       ".sort((p,q)=>p.getBoundingClientRect().left-q.getBoundingClientRect().left);"
                       "if(ic.length){(ic[0].closest('button,[role=\"button\"],a')||ic[0]).click();"
                       "return 'found '+ic.length+' icons'}return null})()")
    expect(clicked, "tiktok", "edit_pencil", tab, "edit (pencil) icon not found on post row")
    print(f"    tiktok edit: {clicked}")
    time.sleep(3)
    capsel = ("document.querySelector('.public-DraftEditor-content')"
              "||document.querySelector('div[contenteditable=\"true\"]')")
    expect(wait_for(tab, f"({capsel})?true:null", 15), "tiktok", "edit_caption_field", tab,
           "editable caption field not found on TikTok post")
    expect(set_text(tab, capsel, v["caption"]), "tiktok", "caption", tab, "caption not settable")
    if dry_run:
        print(f"  [dry-run] TikTok: caption set, NOT saving.")
        return "dry-run"
    saved = tab.eval("(function(){const b=[...document.querySelectorAll('button')]"
                     ".find(x=>['Save','Update','Done'].includes(x.textContent.trim()));"
                     "if(b){b.click();return 'ok'}return null})()")
    expect(saved, "tiktok", "save", tab, "Save/Update button not found")
    time.sleep(3)
    return "recaptioned"


def edit_instagram(v, dry_run):
    tab = platform_tab("instagram")
    tab.goto("https://www.instagram.com/powers.of.zen/")
    time.sleep(5)
    tab.eval("document.querySelector('main a[href*=\"/reel/\"],main a[href*=\"/p/\"]')?.click()")  # newest post
    time.sleep(4)
    # ... menu -> Edit
    tab.eval("(function(){const b=[...document.querySelectorAll('[aria-label=\"More options\"],svg[aria-label=\"More options\"]')].pop();b?.closest('[role=button],button,div')?.click()})()")
    time.sleep(1)
    tab.eval("(function(){const e=[...document.querySelectorAll('button,[role=\"button\"]')].find(x=>x.textContent.trim()==='Edit');e?.click()})()")
    time.sleep(3)
    csel = ("document.querySelector('div[contenteditable=\"true\"][aria-label*=\"caption\" i]')"
            "||document.querySelector('textarea')||document.querySelector('div[contenteditable=\"true\"]')")
    expect(wait_for(tab, f"({csel})?true:null", 15), "instagram", "edit_caption_field", tab,
           "editable caption field not found on IG post")
    expect(set_text(tab, csel, v["caption"]), "instagram", "caption", tab, "caption not settable")
    if dry_run:
        print(f"  [dry-run] Instagram: caption set, NOT saving.")
        return "dry-run"
    saved = tab.eval("(function(){const e=[...document.querySelectorAll('button,[role=\"button\"],div')]"
                     ".find(x=>x.textContent.trim()==='Done'&&x.offsetParent);if(e){e.click();return 'ok'}return null})()")
    expect(saved, "instagram", "save", tab, "Done button not found")
    time.sleep(3)
    return "recaptioned"


EDITORS = {"tiktok": edit_tiktok, "youtube": edit_youtube, "instagram": edit_instagram}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="comma list of platforms")
    args = ap.parse_args()
    import requests
    try:
        requests.get("http://localhost:9222/json/version", timeout=5)
    except Exception:
        print("Chrome CDP not up — run scripts/start_chrome_zen.sh"); sys.exit(1)
    d = pl.load(); v = pl.get(d, args.journey)
    if not v:
        print(f"no pipeline entry for {args.journey}"); sys.exit(1)
    print(f"Recaption {v['journey']} -> \"{v['caption'][:60]}...\""
          f"{'  [DRY RUN]' if args.dry_run else ''}")
    for name in (args.only.split(",") if args.only else pl.PLATFORMS):
        try:
            r = EDITORS[name](v, args.dry_run)
            print(f"  {name}: {r}")
            if not args.dry_run and not str(r).startswith(("FLAG", "ERR")):
                pl.telem("recaption", journey=v["journey"], platform=name)
        except PlatformError as e:
            print(f"  {name}: FLAGGED {e}")
        except Exception as e:
            print(f"  {name}: ERROR {e}")


if __name__ == "__main__":
    main()
