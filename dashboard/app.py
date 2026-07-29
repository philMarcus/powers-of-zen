#!/usr/bin/env python3
"""Powers of Zen — operations dashboard (Streamlit).

Reads/writes the single source of truth (outbox/pipeline.json) via scripts/pipeline.py,
and reads the event log (outbox/telemetry.jsonl). Run:

    streamlit run dashboard/app.py

Stage flow (tabs left→right): Video Review → 🎵 Music → Production → Live / Failed.
  • Video Review (state 'review'): pick cut/model, edit caption, Approve → Music.
  • Music (state 'music'): audition/choose a track (or Generate 5 if none) → Production.
  • Production (state 'queued'): ordered post queue; tweak cut/model, change the music
    pick, reorder. Switching model invalidates the music (it was aligned to the old
    render) → Generate musics → the video hops back to Music.
Editing here writes straight to pipeline.json — the scheduler/poster read the same file.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pipeline as pl  # noqa: E402
import promote  # noqa: E402

st.set_page_config(page_title="Powers of Zen", page_icon="🕳️", layout="wide")


def data():
    return pl.load()


def by_state(d, s):
    return [v for v in d["videos"] if v.get("state") == s]


def video_path(v):
    p = pl.ROOT / v["file"]
    return str(p) if p.exists() else None


def _spec_path(journey):
    return pl.ROOT / "journeys" / f"{journey}.json"


def get_music_theme(journey):
    p = _spec_path(journey)
    return json.loads(p.read_text()).get("music_theme", "") if p.exists() else ""


def set_music_theme(journey, theme):
    p = _spec_path(journey)
    if not p.exists():
        return
    spec = json.loads(p.read_text()); spec["music_theme"] = theme
    p.write_text(json.dumps(spec, indent=2))


def regenerate_music(journey):
    """Fire music_gen for this journey (non-blocking). Generation needs the WSL/GPU env,
    so on Windows we shell into wsl; candidates repopulate here on the next refresh."""
    import os
    import subprocess
    if os.name == "nt":
        cmd = ["wsl", "bash", "-lc",
               f"cd /mnt/c/Users/Phil/zoomer && python3 scripts/music_gen.py {journey}"]
    else:
        cmd = ["python3", "scripts/music_gen.py", journey]
    subprocess.Popen(cmd, cwd=str(pl.ROOT),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── music state helpers ──────────────────────────────────────────────────────────────────
def music_fresh(v):
    """True if this video has candidate tracks that were built for its CURRENT model+cut."""
    m = v.get("music") or {}
    return (bool(m.get("candidates"))
            and m.get("for_model", v["model"]) == v["model"]
            and m.get("for_cut", v["cut"]) == v["cut"])


def music_stale(v):
    """True if candidates exist but were aligned to a DIFFERENT model/cut (now invalid)."""
    m = v.get("music") or {}
    return (bool(m.get("candidates"))
            and (m.get("for_model", v["model"]) != v["model"]
                 or m.get("for_cut", v["cut"]) != v["cut"]))


def apply_switch(journey, model, cut):
    """Change a video's cut/model. If that invalidates its music (candidates were aligned to
    the old render), clear the music and — if the video was in Production — send it back to
    Music so new tracks can be generated for the new render."""
    dd = data(); v = pl.get(dd, journey)
    if not v or (model, cut) == (v["model"], v["cut"]):
        return
    promote.switch(journey, model, cut)
    dd = data(); v = pl.get(dd, journey)
    m = v.get("music") or {}
    if m.get("candidates") and (m.get("for_model") != model or m.get("for_cut") != cut):
        v["music"] = {"chosen": None, "candidates": [],
                      "stale_from": f"{m.get('for_model')}/{m.get('for_cut')}"}
        if v.get("state") == "queued":
            v["state"] = "music"
        pl.save(dd)


def choose_track(journey, cand_id):
    """Promote a candidate track into the posting slot (file copy + pipeline update — no
    heavy deps, so it's safe to run from the Windows dashboard python)."""
    import shutil
    dd = data(); v = pl.get(dd, journey); m = v.get("music", {})
    cand = next((c for c in m.get("candidates", []) if c["id"] == cand_id), None)
    if not cand:
        return
    src = pl.ROOT / cand["aligned"]; dst = pl.ROOT / v["file"]
    silent = dst.with_name(dst.stem + "_silent.mp4")
    if not silent.exists():
        shutil.copy(str(dst), str(silent))
    shutil.copy(str(src), str(dst))
    m["chosen"] = cand_id; m["stage"] = "done"
    pl.save(dd); pl.telem("music_choose", journey=journey, detail=cand_id)


def set_state(journey, newstate):
    dd = data(); pl.get(dd, journey)["state"] = newstate
    pl.save(dd); pl.telem(newstate, journey=journey)


# ── posted-status helpers (a video can be LIVE on some platforms and FAILED on others) ────
def platforms_by_status(v, status):
    return [k for k in pl.PLATFORMS if v.get("platforms", {}).get(k, {}).get("status") == status]


def any_live(v):
    return bool(platforms_by_status(v, "live"))


def any_failed(v):
    return bool(platforms_by_status(v, "failed"))


def platform_line(v):
    """Per-platform status with icons, e.g. '✅ tiktok · ✅ youtube · ❌ instagram'.
    Paused platforms show ⏸ regardless of stored status (they aren't really 'failed')."""
    icon = {"live": "✅", "failed": "❌", "pending": "—"}
    paused = globals().get("PAUSED", [])
    parts = []
    for k in pl.PLATFORMS:
        s = v.get("platforms", {}).get(k, {}).get("status", "pending")
        mark = "⏸" if k in paused else icon.get(s, "•")
        parts.append(f"{mark} {k}")
    return " · ".join(parts)


# ── shared card (preview + caption + cut/model switch) ───────────────────────────────────
def card(v, actions, show_switch=True):
    """Render one video: preview + editable caption + cut/model switch + action buttons.
    `actions` is a list of (label, newstate)."""
    col1, col2 = st.columns([1, 2])
    with col1:
        vp = video_path(v)
        if vp:
            st.video(vp)
        else:
            st.warning(f"file missing: {v['file']}")
        st.caption(f"**{v['journey']}** · {v['model']} · {v['cut']} · {v.get('cameo') or 'no cameo'}")
    with col2:
        cap = st.text_area("caption (TikTok/Instagram)", v.get("caption", ""),
                           key=f"cap_{v['journey']}", height=90)
        yt = st.text_input("YouTube title", v.get("yt_title", ""), key=f"yt_{v['journey']}")
        sched = st.text_input("scheduled (YYYY-MM-DD HH:MM, blank = ASAP)",
                              v.get("scheduled") or "", key=f"sch_{v['journey']}")
        mtheme = st.text_area("🎵 music theme (the scene — drives track generation)",
                              get_music_theme(v["journey"]), key=f"mt_{v['journey']}", height=68)
        if show_switch:
            mc = st.columns([1, 1, 2])
            nm = mc[0].selectbox("model", ["turbo", "ds"],
                                 index=["turbo", "ds"].index(v["model"]), key=f"m_{v['journey']}")
            nc = mc[1].selectbox("cut", ["divein", "zoomout"],
                                 index=["divein", "zoomout"].index(v["cut"]), key=f"c_{v['journey']}")
            if mc[2].button("↔ apply cut/model", key=f"sw_{v['journey']}"):
                apply_switch(v["journey"], nm, nc)
                st.rerun()
        c = st.columns(len(actions) + 1)
        if c[0].button("💾 Save", key=f"save_{v['journey']}"):
            d = data(); vv = pl.get(d, v["journey"])
            vv["caption"], vv["yt_title"] = cap, yt
            vv["scheduled"] = sched.strip() or None
            pl.save(d)
            set_music_theme(v["journey"], mtheme)
            pl.telem("edit", journey=v["journey"])
            st.success("saved"); st.rerun()
        for i, (label, newstate) in enumerate(actions, start=1):
            if c[i].button(label, key=f"act_{newstate}_{v['journey']}"):
                set_state(v["journey"], newstate); st.rerun()
    st.divider()


def audition_candidates(v, choose_advances_to=None):
    """Show candidate tracks with Choose buttons. If choose_advances_to is a state, choosing
    also moves the video there (Music → Production)."""
    m = v["music"]
    cands = m.get("candidates", [])
    cols = st.columns(min(len(cands), 3) or 1)
    for i, c in enumerate(cands):
        with cols[i % len(cols)]:
            ap = pl.ROOT / c["aligned"]
            if ap.exists():
                st.video(str(ap))
            else:
                st.warning(f"missing: {c['aligned']}")
            is_chosen = m.get("chosen") == c["id"]
            st.caption(f"**{c['id']}** · lock {c['lock']}×" + (" · ✅ chosen" if is_chosen else ""))
            if st.button("✅ Chosen" if is_chosen else "Choose",
                         key=f"ch_{v['journey']}_{c['id']}"):
                choose_track(v["journey"], c["id"])
                if choose_advances_to:
                    set_state(v["journey"], choose_advances_to)
                st.rerun()


# ── header + tabs ────────────────────────────────────────────────────────────────────────
d = data()
counts = Counter(v.get("state") for v in d["videos"])
# Live/Failed are by PLATFORM status, not the top-level state: a video live on IG+YT but
# dropped on TikTok is BOTH live (somewhere) and failed (somewhere), so it shows in both.
live_vids = [v for v in d["videos"] if any_live(v)]
failed_vids = [v for v in d["videos"] if any_failed(v)]
PAUSED = pl.paused_platforms(d)
PREASONS = d.get("meta", {}).get("paused_reasons", {})
st.title("🕳️ Powers of Zen — ops")
cols = st.columns(6)
cols[0].metric("video review", counts.get("review", 0))
cols[1].metric("music", counts.get("music", 0))
cols[2].metric("production", counts.get("queued", 0))
cols[3].metric("live (any)", len(live_vids))
cols[4].metric("failed (any)", len(failed_vids))
nxt = pl.next_to_post(d)
cols[5].metric("next post", nxt["journey"] if nxt else "—")

tabs = st.tabs([f"🎬 Video Review ({counts.get('review',0)})",
                f"🎵 Music ({counts.get('music',0)})",
                f"🚀 Production ({counts.get('queued',0)})",
                f"Live ({len(live_vids)})",
                f"Failed ({len(failed_vids)})",
                "Telemetry"])

with tabs[0]:  # VIDEO REVIEW — pick cut/model, edit caption, send to Music
    st.write("Look at the video, pick cut/model, edit the caption/theme, then **Approve → Music** "
             "to choose a soundtrack.")
    rv = by_state(d, "review")
    if not rv:
        st.info("Nothing awaiting video review.")
    for v in rv:
        card(v, [("✅ Approve → Music", "music")])

with tabs[1]:  # MUSIC — audition/generate a track, then send to Production
    st.write("Pick the soundtrack. Every candidate is auto-locked so its accent lands on each "
             "morph. Choose one → it moves to **Production**. Switch a video's model and it lands "
             "back here to get tracks for the new render.")
    mv = by_state(d, "music")
    if not mv:
        st.info("Nothing needs music. Approve a video in Video Review to send it here.")
    for v in mv:
        m = v.get("music") or {}
        tag = f"✅ {m['chosen']}" if m.get("chosen") else "— choose one —"
        st.subheader(f"{v['journey']} · {v['model']}/{v['cut']}"
                     + (f" · {m['bpm']}bpm {m.get('key','')}" if m.get("bpm") else "")
                     + f" · {tag}")
        tcol = st.columns([5, 1])
        newtheme = tcol[0].text_input("🎵 music theme (scene)", get_music_theme(v["journey"]),
                                      key=f"mtm_{v['journey']}")
        if not music_fresh(v):
            note = (f"music was generated for {m.get('stale_from')}, not {v['model']}/{v['cut']}"
                    if m.get("stale_from") or music_stale(v) else "no tracks generated yet")
            st.warning(f"{note} — generate 5 tracks for this render.")
            if tcol[1].button("🎵 Generate 5", key=f"gen_{v['journey']}"):
                set_music_theme(v["journey"], newtheme)
                regenerate_music(v["journey"])
                st.info(f"Generating 5 tracks for {v['journey']} ({v['model']}/{v['cut']}) — "
                        "refresh in ~2–3 min.")
        else:
            if tcol[1].button("🔄 Regenerate", key=f"regen_{v['journey']}"):
                set_music_theme(v["journey"], newtheme)
                regenerate_music(v["journey"])
                st.info(f"Regenerating {v['journey']} candidates — refresh in ~2–3 min.")
            audition_candidates(v, choose_advances_to="queued")
        cc = st.columns([1, 1, 4])
        if cc[0].button("↩ Back to Review", key=f"back_{v['journey']}"):
            set_state(v["journey"], "review"); st.rerun()
        if cc[1].button("🔇 Skip music → Production", key=f"skip_{v['journey']}"):
            set_state(v["journey"], "queued"); st.rerun()
        st.divider()

with tabs[2]:  # PRODUCTION — the ordered post queue; tweak cut/model + change the music pick
    st.write("Approved & in post order (top posts next). ⬆⬇ to reorder. You can still switch "
             "cut/model or change the music pick here.")
    qv = pl.queued(d)
    if not qv:
        st.info("Production queue is empty.")
    for i, v in enumerate(qv):
        top = st.columns([1, 1, 1, 9])
        if top[0].button("⬆", key=f"up_{v['journey']}", disabled=(i == 0)):
            dd = data(); a = pl.get(dd, v["journey"]); b = pl.get(dd, qv[i - 1]["journey"])
            a["order"], b["order"] = b.get("order", i - 1), a.get("order", i)
            pl.save(dd); st.rerun()
        if top[1].button("⬇", key=f"dn_{v['journey']}", disabled=(i == len(qv) - 1)):
            dd = data(); a = pl.get(dd, v["journey"]); b = pl.get(dd, qv[i + 1]["journey"])
            a["order"], b["order"] = b.get("order", i + 1), a.get("order", i)
            pl.save(dd); st.rerun()
        top[2].subheader(f"#{i + 1}")
        with top[3]:
            m = v.get("music") or {}
            chosen = m.get("chosen")
            st.caption("🎵 " + (f"music: **{chosen}**" if chosen else "no music selected"))
            card(v, [("↩ Unqueue", "music" if not chosen else "review")])
            if music_stale(v):
                st.warning(f"music was built for {m.get('for_model')}/{m.get('for_cut')} — "
                           "regenerate for the current render.")
                if st.button("🎵 Generate musics → Music", key=f"pgen_{v['journey']}"):
                    regenerate_music(v["journey"])
                    set_state(v["journey"], "music")
                    st.info("Generating tracks — the video moved to the Music tab.")
                    st.rerun()
            elif music_fresh(v):
                with st.expander("🎵 change music pick"):
                    audition_candidates(v)   # re-choose; stays in Production
        st.divider()

with tabs[3]:  # LIVE — anything live on at least one platform (noting where)
    if not live_vids:
        st.info("Nothing live yet.")
    for v in live_vids:
        live_on = ", ".join(platforms_by_status(v, "live"))
        failed_on = ", ".join(platforms_by_status(v, "failed"))
        st.markdown(f"**{v['journey']}** ({v['model']}/{v['cut']}) — {platform_line(v)}")
        note = f"live on **{live_on}**" + (f" · ❌ not on **{failed_on}**" if failed_on else "")
        st.caption(note)
        for k in pl.PLATFORMS:
            if v["platforms"].get(k, {}).get("url"):
                st.markdown(f"- {k}: {v['platforms'][k]['url']}")
        st.caption(v.get("caption", ""))
        st.divider()

with tabs[4]:  # FAILED — anything failed on at least one platform (noting where)
    if not failed_vids:
        st.info("No failures.")
    for v in failed_vids:
        live_on = ", ".join(platforms_by_status(v, "live"))
        st.error(f"**{v['journey']}** — {platform_line(v)}")
        # per-failed-platform reason: paused platforms show the pause reason, not "dropped"
        for k in platforms_by_status(v, "failed"):
            if k in PAUSED:
                st.caption(f"⏸ **{k}**: {PREASONS.get(k, 'paused')}")
            else:
                note = v["platforms"][k].get("note", "")
                st.caption(f"❌ **{k}**: {note or 'failed'}")
        if live_on:
            st.caption(f"✅ live on **{live_on}**")
        if st.button("🔁 Retry failed → Production", key=f"retry_{v['journey']}"):
            # re-queue; the poster is resume-safe (skips platforms already live, retries the
            # failed ones). Paused platforms stay skipped.
            set_state(v["journey"], "queued"); st.rerun()
        st.divider()

with tabs[5]:  # TELEMETRY
    ev = pl.read_telem(200)[::-1]
    if not ev:
        st.info("no events yet")
    for e in ev:
        icon = {"post": "✅", "post_fail": "❌", "flag": "⚠️", "render": "🎬",
                "render_fail": "💥", "music_gen": "🎵", "music_choose": "🎶",
                "switch": "🔀"}.get(e["event"], "•")
        st.text(f"{icon} {e['ts']}  {e['event']}  {e.get('journey','')} "
                f"{e.get('platform','')}  {e.get('detail','')}")
