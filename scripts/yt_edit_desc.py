#!/usr/bin/env python3
"""Edit the DESCRIPTION of already-published YouTube videos in Studio (2026-10-03, Phil: "edit the
ones with the identical descriptions now"). Replaces the 09-10 SEO template (two boilerplate lines +
the same hashtags on every upload — the prime suspect for YouTube going dark) with the classic
description = the video's IG caption. Same CDP + trusted-input machinery as the poster.

  python3 scripts/yt_edit_desc.py --probe <journey>    # open the edit page, print what is there
  python3 scripts/yt_edit_desc.py --only  <journey>    # edit ONE video, verify by reload
  python3 scripts/yt_edit_desc.py --all                # every live video still carrying the template
Writes outbox/yt_edit_desc.log, telem yt_desc_edit per video, and updates pipeline.json
(yt_desc = classic, old copy in yt_desc_seo_backup, yt_desc_edited = ts). Stops on the first failure."""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402
import poster  # noqa: E402

TEMPLATE_MARK = "hypnotic infinite-zoom loops"
DSEL = "document.querySelector('ytcp-video-description #textbox')"
LOG = ROOT / "outbox" / "yt_edit_desc.log"


def log(msg):
    line = f"=== {datetime.now():%H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def vid_of(v):
    m = re.search(r"shorts/([A-Za-z0-9_-]+)", ((v.get("platforms") or {}).get("youtube") or {}).get("url", ""))
    return m.group(1) if m else None


def targets(only=None):
    out = []
    for v in pl.load()["videos"]:
        yt = (v.get("platforms") or {}).get("youtube") or {}
        if yt.get("status") != "live" or not vid_of(v):
            continue
        if only and v["journey"] != only:
            continue
        if only or TEMPLATE_MARK in (v.get("yt_desc") or ""):
            out.append(v)
    return out


def open_edit(tab, vid):
    tab.goto(f"https://studio.youtube.com/video/{vid}/edit")
    ok = poster.wait_for(tab, f"({DSEL})?true:null", 45, 1.5)
    if not ok:
        return None
    time.sleep(2.0)                                   # let the form hydrate
    poster._yt_close_overlays(tab)
    return tab.eval(f"({DSEL}).innerText")


def save_buttons(tab):
    return tab.eval("[...document.querySelectorAll('ytcp-button,button')]"
                    ".filter(b=>/^save$/i.test(b.textContent.trim()))"
                    ".map(b=>b.tagName+'#'+b.id+' disabled='+(b.hasAttribute('disabled')||b.getAttribute('aria-disabled')==='true'))")


def click_save(tab):
    return tab.eval("(function(){const b=[...document.querySelectorAll('ytcp-button,button')]"
                    ".find(b=>/^save$/i.test(b.textContent.trim())&&!(b.hasAttribute('disabled')||b.getAttribute('aria-disabled')==='true'));"
                    "if(!b)return 'NO_ENABLED_SAVE';(b.querySelector('button')||b).click();return 'clicked'})()")


def edit_one(tab, v, classic):
    vid = vid_of(v)
    cur = open_edit(tab, vid)
    if cur is None:
        return False, "edit page / description box never appeared"
    if norm(cur) == norm(classic):
        return True, "already classic"
    if not poster._yt_set_field(tab, DSEL, classic):
        return False, "description text did not land"
    time.sleep(1.5)
    r = click_save(tab)
    if r != "clicked":
        return False, f"save: {r}"
    # saved = the Save button goes disabled again (nothing left to save) or a 'saved' toast
    done = poster.wait_for(tab, "(function(){const t=document.body.innerText.toLowerCase();"
                                "if(t.includes('changes saved')||t.includes('saved'))return true;"
                                "const b=[...document.querySelectorAll('ytcp-button,button')]"
                                ".find(b=>/^save$/i.test(b.textContent.trim()));"
                                "return (b&&(b.hasAttribute('disabled')||b.getAttribute('aria-disabled')==='true'))?true:null})()", 40, 1.0)
    if not done:
        return False, "no save confirmation"
    time.sleep(2.0)
    back = open_edit(tab, vid)                        # reload: the server's copy
    if back is None or norm(back) != norm(classic):
        return False, f"readback differs: {norm(back)[:120]!r}"
    return True, "saved + verified by reload"


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("--probe", "--only", "--all"):
        sys.exit("usage: yt_edit_desc.py --probe <journey> | --only <journey> | --all")
    mode = args[0]
    only = args[1] if mode in ("--probe", "--only") else None
    vids = targets(only)
    if not vids:
        sys.exit("no matching live video")
    tab = poster.platform_tab("youtube")
    if mode == "--probe":
        v = vids[0]
        cur = open_edit(tab, vid_of(v))
        print("current description:\n", cur)
        print("save buttons:", save_buttons(tab))
        print("classic would be:\n", v.get("caption"))
        return
    log(f"{mode}: {len(vids)} video(s)")
    for i, v in enumerate(vids):
        classic = (v.get("caption") or "").strip()
        if not classic:
            log(f"{v['journey']}: no caption to restore — skipped")
            continue
        ok, note = edit_one(tab, v, classic)
        log(f"{v['journey']} ({vid_of(v)}): {'OK' if ok else 'FAILED'} — {note}")
        pl.telem("yt_desc_edit", journey=v["journey"], detail=("ok: " if ok else "FAILED: ") + note)
        if not ok:
            sys.exit(1)
        p = pl.load()                                 # merge-into-fresh (pipeline.json has no locking)
        for w in p["videos"]:
            if w["journey"] == v["journey"]:
                if TEMPLATE_MARK in (w.get("yt_desc") or ""):
                    w["yt_desc_seo_backup"] = w["yt_desc"]
                w["yt_desc"] = classic
                w["yt_desc_edited"] = pl._now()
        pl.save(p)
        if i + 1 < len(vids):
            time.sleep(6.0)
    log("done")


if __name__ == "__main__":
    main()
