#!/usr/bin/env python3
"""Powers of Zen — operations dashboard (Streamlit).

Reads/writes the single source of truth (outbox/pipeline.json) via scripts/pipeline.py,
and reads the event log (outbox/telemetry.jsonl). Run:

    streamlit run dashboard/app.py

Panels: Queue (edit caption, schedule) · Review (approve → queue) · Live · Telemetry.
Editing here writes straight back to pipeline.json — the scheduler/poster read the same file.
"""
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
    import json
    p = _spec_path(journey)
    return json.loads(p.read_text()).get("music_theme", "") if p.exists() else ""


def set_music_theme(journey, theme):
    import json
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


def card(v, actions):
    """Render one video with a preview + editable caption + the given action buttons."""
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
        # switch the chosen variant (dive-in/zoom-out, DS/turbo) — swaps the file in
        # production/ and updates pipeline. Works in Review AND Queue.
        mc = st.columns([1, 1, 2])
        nm = mc[0].selectbox("model", ["turbo", "ds"],
                             index=["turbo", "ds"].index(v["model"]), key=f"m_{v['journey']}")
        nc = mc[1].selectbox("cut", ["divein", "zoomout"],
                             index=["divein", "zoomout"].index(v["cut"]), key=f"c_{v['journey']}")
        if mc[2].button("↔ apply cut/model", key=f"sw_{v['journey']}"):
            if (nm, nc) != (v["model"], v["cut"]):
                promote.switch(v["journey"], nm, nc)
            st.rerun()
        c = st.columns(len(actions) + 1)
        if c[0].button("💾 Save", key=f"save_{v['journey']}"):
            d = data()
            vv = pl.get(d, v["journey"])
            vv["caption"], vv["yt_title"] = cap, yt
            vv["scheduled"] = sched.strip() or None
            pl.save(d)
            set_music_theme(v["journey"], mtheme)
            pl.telem("edit", journey=v["journey"])
            st.success("saved"); st.rerun()
        for i, (label, newstate) in enumerate(actions, start=1):
            if c[i].button(label, key=f"act_{newstate}_{v['journey']}"):
                d = data()
                pl.get(d, v["journey"])["state"] = newstate
                pl.save(d)
                pl.telem(newstate, journey=v["journey"])
                st.rerun()
    st.divider()


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


d = data()
counts = Counter(v.get("state") for v in d["videos"])
music_review = [v for v in d["videos"] if v.get("music", {}).get("candidates")]
st.title("🕳️ Powers of Zen — ops")
cols = st.columns(6)
for i, s in enumerate(["review", "queued", "live", "failed", "rendered"]):
    cols[i].metric(s, counts.get(s, 0))
nxt = pl.next_to_post(d)
cols[5].metric("next post", nxt["journey"] if nxt else "—")

tabs = st.tabs([f"Queue ({counts.get('queued',0)})", f"Review ({counts.get('review',0)})",
                f"🎵 Music ({len(music_review)})",
                f"Live ({counts.get('live',0)})", f"Failed ({counts.get('failed',0)})",
                "Telemetry"])

with tabs[0]:  # queued -> post next; reorderable
    st.write("Approved & in post order (top posts next). ⬆⬇ to reorder; every ~3rd a "
             "zoom-out is a nice rhythm but arrange however you like.")
    qv = pl.queued(d)
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
            card(v, [("↩ Unqueue", "review")])

with tabs[1]:  # review -> approve to queue (freshly rendered, cut/model not yet decided)
    st.write("Awaiting your decision — switch cut/model, edit caption, then Approve → Queue.")
    for v in by_state(d, "review"):
        card(v, [("✅ Approve → Queue", "queued")])

with tabs[2]:  # music review — audition candidate tracks and choose one
    st.write("Audition candidate tracks (all auto-locked to the morphs — the accent lands "
             "on every morph). Pick one → it's promoted into the posting slot. "
             "To (re)generate 5: run `python3 scripts/music_gen.py <journey>` on the box.")
    if not music_review:
        st.info("No candidates yet. Approve a video's cut, then run "
                "`scripts/music_gen.py <journey>` to generate 5 tracks to choose from.")
    for v in music_review:
        m = v["music"]
        tag = f"✅ {m['chosen']}" if m.get("chosen") else "— choose one —"
        st.subheader(f"{v['journey']} · {v['cut']} · {m['bpm']}bpm {m.get('key','')} · {tag}")
        # editable theme → regenerate all candidates from the new scene description
        tcol = st.columns([5, 1])
        newtheme = tcol[0].text_input("🎵 music theme", get_music_theme(v["journey"]),
                                      key=f"mtm_{v['journey']}")
        if tcol[1].button("🔄 Regenerate", key=f"regen_{v['journey']}"):
            set_music_theme(v["journey"], newtheme)
            regenerate_music(v["journey"])
            st.info(f"Regenerating {v['journey']} candidates with the new theme — "
                    "refresh in ~2–3 min.")
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
                st.caption(f"**{c['id']}** · lock {c['lock']}×" +
                           (" · ✅ chosen" if is_chosen else ""))
                if st.button("✅ Chosen" if is_chosen else "Choose",
                             key=f"ch_{v['journey']}_{c['id']}", disabled=is_chosen):
                    choose_track(v["journey"], c["id"]); st.rerun()
        st.divider()

with tabs[3]:  # live
    for v in by_state(d, "live"):
        pstat = " · ".join(f"{k}:{v['platforms'][k]['status']}" for k in pl.PLATFORMS)
        st.markdown(f"**{v['journey']}** ({v['model']}/{v['cut']}) — {pstat}")
        links = [v["platforms"][k]["url"] for k in pl.PLATFORMS if v["platforms"][k].get("url")]
        for ln in links:
            st.markdown(f"- {ln}")
        st.caption(v.get("caption", ""))
        st.divider()

with tabs[4]:  # failed
    for v in by_state(d, "failed"):
        st.error(f"**{v['journey']}** — " +
                 " · ".join(f"{k}:{v['platforms'][k]['status']}" for k in pl.PLATFORMS))
        card(v, [("🔁 Retry → Queue", "queued")])

with tabs[5]:  # telemetry
    ev = pl.read_telem(200)[::-1]
    if not ev:
        st.info("no events yet")
    for e in ev:
        icon = {"post": "✅", "post_fail": "❌", "flag": "⚠️", "render": "🎬",
                "render_fail": "💥"}.get(e["event"], "•")
        st.text(f"{icon} {e['ts']}  {e['event']}  {e.get('journey','')} "
                f"{e.get('platform','')}  {e.get('detail','')}")
