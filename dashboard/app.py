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

st.set_page_config(page_title="Powers of Zen", page_icon="🕳️", layout="wide")


def data():
    return pl.load()


def by_state(d, s):
    return [v for v in d["videos"] if v.get("state") == s]


def video_path(v):
    p = pl.ROOT / v["file"]
    return str(p) if p.exists() else None


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
        c = st.columns(len(actions) + 1)
        if c[0].button("💾 Save", key=f"save_{v['journey']}"):
            d = data()
            vv = pl.get(d, v["journey"])
            vv["caption"], vv["yt_title"] = cap, yt
            vv["scheduled"] = sched.strip() or None
            pl.save(d)
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


d = data()
counts = Counter(v.get("state") for v in d["videos"])
st.title("🕳️ Powers of Zen — ops")
cols = st.columns(6)
for i, s in enumerate(["review", "queued", "live", "failed", "rendered"]):
    cols[i].metric(s, counts.get(s, 0))
nxt = pl.next_to_post(d)
cols[5].metric("next post", nxt["journey"] if nxt else "—")

tabs = st.tabs([f"Queue ({counts.get('queued',0)})", f"Review ({counts.get('review',0)})",
                f"Live ({counts.get('live',0)})", f"Failed ({counts.get('failed',0)})",
                "Telemetry"])

with tabs[0]:  # queued -> post next; can send back to review
    st.write("Approved & waiting to post (the scheduler/poster take the top one).")
    for v in by_state(d, "queued"):
        card(v, [("↩ Unqueue", "review")])

with tabs[1]:  # review -> approve to queue
    st.write("In `production/`, awaiting your approval. Edit the caption, then Approve.")
    for v in by_state(d, "review"):
        card(v, [("✅ Approve → Queue", "queued")])

with tabs[2]:  # live
    for v in by_state(d, "live"):
        pstat = " · ".join(f"{k}:{v['platforms'][k]['status']}" for k in pl.PLATFORMS)
        st.markdown(f"**{v['journey']}** ({v['model']}/{v['cut']}) — {pstat}")
        links = [v["platforms"][k]["url"] for k in pl.PLATFORMS if v["platforms"][k].get("url")]
        for ln in links:
            st.markdown(f"- {ln}")
        st.caption(v.get("caption", ""))
        st.divider()

with tabs[3]:  # failed
    for v in by_state(d, "failed"):
        st.error(f"**{v['journey']}** — " +
                 " · ".join(f"{k}:{v['platforms'][k]['status']}" for k in pl.PLATFORMS))
        card(v, [("🔁 Retry → Queue", "queued")])

with tabs[4]:  # telemetry
    ev = pl.read_telem(200)[::-1]
    if not ev:
        st.info("no events yet")
    for e in ev:
        icon = {"post": "✅", "post_fail": "❌", "flag": "⚠️", "render": "🎬",
                "render_fail": "💥"}.get(e["event"], "•")
        st.text(f"{icon} {e['ts']}  {e['event']}  {e.get('journey','')} "
                f"{e.get('platform','')}  {e.get('detail','')}")
