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
import os
import sys
from collections import Counter
from pathlib import Path

import streamlit as st

# ffmpeg path — the dashboard runs on WINDOWS python (streamlit.exe), so it needs a Windows path;
# the /mnt/c form only works under WSL. (score.py/phase_shift.py hardcode the WSL form.)
_FF = ("Users/Phil/AppData/Local/Microsoft/WinGet/Packages/"
       "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe")
FFMPEG = ("C:\\" + _FF.replace("/", "\\")) if os.name == "nt" else ("/mnt/c/" + _FF)

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
    # resolves across journeys/ + engine1/ + engine0/ (legacy specs still feed music/caption)
    return pl.journey_path(journey)


def _read_spec(p):
    """Journey specs are UTF-8 (em-dashes in every music_theme). This dashboard runs on WINDOWS
    python, whose default text encoding is cp1252 — an unencoded read_text() either MOJIBAKES the
    spec ("—" → "â€”") or, once that mojibake has been written back, raises UnicodeDecodeError on
    byte 0x9d and takes the whole Streamlit script down. ALWAYS pass encoding here."""
    return json.loads(p.read_text(encoding="utf-8"))


def get_music_theme(journey):
    p = _spec_path(journey)
    if not p:
        return ""
    try:
        return _read_spec(p).get("music_theme", "")
    except Exception as e:      # never let one damaged spec blank a whole tab
        st.warning(f"couldn't read journeys/{journey}.json: {e}")
        return ""


def set_music_theme(journey, theme):
    p = _spec_path(journey)
    if not p:
        return
    try:
        spec = _read_spec(p)
    except Exception as e:
        st.error(f"not saving music theme — journeys/{journey}.json is unreadable: {e}")
        return
    spec["music_theme"] = theme
    # ensure_ascii=False keeps the em-dash a real character instead of a \uXXXX escape that a
    # later cp1252 round-trip can corrupt; encoding=utf-8 so Windows doesn't write cp1252.
    p.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def regenerate_music(journey, fresh=False):
    """Fire music_gen for this journey (non-blocking). Generation needs the WSL/GPU env,
    so on Windows we shell into wsl; candidates repopulate here on the next refresh.

    fresh=True (the Music-tab Regenerate/Generate buttons, 2026-08-31): FORCE a full GPU
    generation with re-rolled seeds + wildcard lanes — the point of the button is different
    tracks. Without it the realign fast path returned the SAME five every click (Phil's bug).
    fresh=False (approve_to_music): keep the fast path — realign the overnight pregen keepers
    to the marked start (seconds, no GPU)."""
    import os
    import subprocess
    dd0 = data()
    v0 = pl.get(dd0, journey)
    if fresh:
        flag = " --fresh"
    else:
        flag = " --realign" if (v0 or {}).get("music_pregen") else ""
    if os.name == "nt":
        cmd = ["wsl", "bash", "-lc",
               f"cd /mnt/c/Users/Phil/zoomer && python3 -u scripts/music_gen.py {journey}{flag}"]
    else:
        cmd = ["bash", "-lc", f"python3 -u scripts/music_gen.py {journey}{flag}"]
    # log, don't DEVNULL: a crashed gen used to vanish without a trace (resonance_hall's
    # bad keyscale died silently and the video just sat in Music with no candidates).
    # python3 -u (2026-09-10): without it Python block-buffers stdout into the file, so the
    # log sits at 0 bytes for the whole ~10 min run and tailing it shows nothing — which is
    # exactly what "the button did nothing" looks like from outside.
    logf = open(pl.ROOT / "outbox" / f"music_gen_{journey}.log", "w")
    subprocess.Popen(cmd, cwd=str(pl.ROOT), stdout=logf, stderr=subprocess.STDOUT)


def apply_caption_pick(journey, radio_key):
    """on_change for the caption-options radio. Fires ONLY on a real user click, so it can never
    re-assert a stale selection over a hand-edited caption on a rerun (that bug reverted every
    manual edit). Writes the picked caption + its matching YouTube title into the pipeline and
    into the live text fields."""
    pick = st.session_state.get(radio_key)
    if not pick:
        return
    dd = data()
    vv = pl.get(dd, journey)
    if not vv or pick == vv.get("caption"):
        return
    opts = vv.get("caption_options") or []
    vv["caption"] = pick
    yts = vv.get("yt_title_options") or []
    if pick in opts:
        pi = opts.index(pick)
        if pi < len(yts) and yts[pi]:
            vv["yt_title"] = yts[pi]
    st.session_state[f"cap_{journey}"] = vv["caption"]
    st.session_state[f"yt_{journey}"] = vv.get("yt_title", "")
    pl.save(dd)


def assemble_caption(body, spot_line, tags, hook):
    """body [+ spot question if hook] + hashtags — mirrors scripts/caption.py so the toggle can
    re-assemble the caption options without re-calling the model."""
    parts = [body.strip()]
    if hook and (spot_line or "").strip():
        parts.append(spot_line.strip())
    if (tags or "").strip():
        parts.append(tags.strip())
    return " ".join(p for p in parts if p)


def gen_captions(journey, model, no_theme=False):
    """Fire the local-VLM captioner (non-blocking; writes ~5 caption+title options). --force so the
    dashboard button always runs. --no-theme in Production (music theme is already locked by then)."""
    import subprocess
    flag = " --no-theme" if no_theme else ""
    args = (f"cd /mnt/c/Users/Phil/zoomer && python3 scripts/caption.py {journey} "
            f"--model {model} --force{flag}")
    cmd = ["wsl", "bash", "-lc", args] if os.name == "nt" else ["bash", "-lc", args]
    logf = open(pl.ROOT / "outbox" / f"caption_{journey}.log", "w")
    subprocess.Popen(cmd, cwd=str(pl.ROOT), stdout=logf, stderr=subprocess.STDOUT)


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
    if (v["model"], v["cut"]) != (model, cut):
        # switch refused (that variant has no file anywhere) — nothing changed
        st.warning(f"no {model}/{cut} file exists for {journey} — kept {v['model']}/{v['cut']}")
        return
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


# ── start-frame / cover-frame marking (pause the looping video, read the time, mark it) ──────
def extract_frame(video_rel, t):
    """Grab the frame at t seconds → a png (for confirming what you're marking). Never raises."""
    import subprocess
    try:
        (pl.ROOT / "outbox" / "shots").mkdir(parents=True, exist_ok=True)
        out_rel = f"outbox/shots/mark_{Path(video_rel).stem}.png"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{max(0.0, t):.2f}",
                        "-i", video_rel, "-frames:v", "1", out_rel],
                       cwd=str(pl.ROOT), capture_output=True, timeout=30)
        p = pl.ROOT / out_rel
        return str(p) if p.exists() else None
    except Exception:
        return None


def phase_shift_video(src_rel, t):
    """Rotate the loop to open at t seconds → a NEW file (never in place: the browser may hold
    the played file open, which locks it). Returns the new relative path or None."""
    import subprocess
    src = pl.ROOT / src_rel
    dst = src.with_name(src.stem + "_shift.mp4")
    try:
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", src.name, "-filter_complex",
             f"[0:v]trim=start={t:.3f},setpts=PTS-STARTPTS[a];"
             f"[0:v]trim=duration={t:.3f},setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1[v]",
             "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", dst.name],
            cwd=str(src.parent), capture_output=True, timeout=180)
        # POSIX separators always: this path is stored in pipeline.json, which is also read
        # under WSL (poster.py runs via wsl.exe). A Windows-side str() yields backslashes, and
        # `ROOT / "review_divein\\x.mp4"` is one bogus filename under WSL. poster.win_path()
        # converts "/"->"\" for Chrome, so forward slashes work on both sides.
        return dst.relative_to(pl.ROOT).as_posix() if dst.exists() else None
    except Exception:
        return None


def approve_to_music(journey):
    """Approve a reviewed video into Music. If a start frame was marked, phase-shift the video to
    open there (to a NEW file, always re-derived from the un-shifted cut so it's re-markable),
    then generate music — but ONLY if the GPU is free; otherwise the Music tab shows a Generate
    button (VLM/ACE-Step would fight an active render)."""
    dd = data(); v = pl.get(dd, journey)
    t = v.get("start_t")
    base = v.get("orig_file") or v["file"]          # always shift from the un-shifted cut
    if t and t > 0.05:
        newrel = phase_shift_video(base, float(t))
        if newrel:
            v["orig_file"] = base
            v["file"] = newrel
            pl.telem("phase_shift", journey=journey, detail=f"start @ {t:.2f}s")
    elif v.get("orig_file"):                         # start cleared → revert to the un-shifted cut
        v["file"] = v["orig_file"]
    v["state"] = "music"
    pl.save(dd); pl.telem("music", journey=journey)
    # gate on ComfyUI's ACTUAL queue, not GPU utilization — the dashboard's own looping
    # video previews kept utilization high and silently skipped this (2026-08-09).
    # PREGEN NEEDS NO GATE (2026-09-19): a video with music_pregen only has to be REALIGNED to
    # the marked start — ffmpeg, seconds, no GPU, touches nothing in ComfyUI. The gate sat in
    # front of that too, so during ~20h of back-to-back renders every approval was skipped and
    # Phil could not pick music for videos whose five tracks were already on disk.
    if v.get("music_pregen") or not pl.comfy_busy():
        regenerate_music(journey)                   # realign (no GPU) or async full gen
    else:
        pl.telem("music_skip", journey=journey, detail="ComfyUI busy — use Generate in Music tab")


def render_marker(v, kind):
    """kind='start' (Video Review → phase-shift on approve) or 'cover' (Production → thumbnail)."""
    field = "start_t" if kind == "start" else "cover_t"
    label = "📍 start frame — sec (watch the loop, enter the time)" if kind == "start" \
        else "🖼 cover frame — sec"
    cur = float(v.get(field) or 0.0)
    cc = st.columns([2, 1, 1])
    t = cc[0].number_input(label, min_value=0.0, value=cur, step=0.1,
                           key=f"{field}_{v['journey']}")
    if cc[1].button("🔎 preview", key=f"prev_{field}_{v['journey']}"):
        st.session_state[f"pimg_{field}_{v['journey']}"] = extract_frame(v["file"], t)
    if cc[2].button("✅ set", key=f"set_{field}_{v['journey']}"):
        dd = data(); pl.get(dd, v["journey"])[field] = round(t, 2)
        pl.save(dd); st.success(f"{kind} frame set @ {t:.1f}s"); st.rerun()
    pimg = st.session_state.get(f"pimg_{field}_{v['journey']}")
    if pimg:
        st.image(pimg, caption=f"{kind} @ {t:.1f}s", width=200)
    if v.get(field):
        st.caption(f"current {kind}: **{v[field]:.1f}s**"
                   + (" — video will phase-shift to open here on approve" if kind == "start" else ""))


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
def card(v, actions, show_switch=True, marker=None, captions=False, extras=None):
    """Render one video: preview + editable caption + cut/model switch + action buttons.
    `actions` is a list of (label, newstate-or-callable). `marker` in {'start','cover',None}
    shows a frame-marking control. `captions=True` shows the auto-caption options + a generate
    button. `extras(v)` renders extra controls just above the action row."""
    col1, col2 = st.columns([1, 2])
    with col1:
        vp = video_path(v)
        if vp:
            st.video(vp, loop=True)
        else:
            st.warning(f"file missing: {v['file']}")
        # cameo shown by its user-facing rhyming display name (pl.MASCOT_DISPLAY); the stored
        # value stays the internal sprite key.
        cam = (v.get("cameo") or "").strip()
        cam_disp = pl.MASCOT_DISPLAY.get(cam.lower(), cam.title()) if cam else "no cameo"
        st.caption(f"**{v['journey']}** · {v['model']} · {v['cut']} · {cam_disp}")
    with col2:
        if captions:
            no_theme = v.get("state") == "queued"     # Production: don't redo the (locked) music theme
            # "can you spot <mascot>?" hook toggle — shown for ANY cameo (even before captions run),
            # so you can pre-decide; drop it if the sprite didn't render well.
            if v.get("cameo"):
                _ck = v["cameo"].strip()
                _cd = pl.MASCOT_DISPLAY.get(_ck.lower(), _ck.title())
                hook = st.toggle(f"🔎 include “can you spot {_cd}?” hook",
                                 value=v.get("spot_hook", True), key=f"hook_{v['journey']}")
                if hook != v.get("spot_hook", True):
                    dd = data(); vv = pl.get(dd, v["journey"])
                    vv["spot_hook"] = hook
                    bodies = vv.get("caption_bodies", [])
                    if bodies:      # re-assemble existing options without re-calling the model
                        old = vv.get("caption_options", [])
                        cur = vv.get("caption")
                        idx = old.index(cur) if cur in old else None
                        new = [assemble_caption(b, vv.get("spot_line", ""), vv.get("caption_tags", ""), hook)
                               for b in bodies]
                        vv["caption_options"] = new
                        if idx is not None:      # only re-point the caption if it WAS an option;
                            vv["caption"] = new[min(idx, len(new) - 1)]   # a hand-edit is left alone
                            st.session_state[f"cap_{v['journey']}"] = vv["caption"]
                    pl.save(dd); st.rerun()
            opts = v.get("caption_options") or []
            gc = st.columns([3, 1])
            if opts:
                # A KEYED st.radio IGNORES `index` on every rerun and restores its OWN stored
                # selection. So reading its return value each run and syncing from it wrote the
                # stale selection over a hand-edited caption — Save was undone by its own
                # st.rerun(). Never derive the caption from the radio's restored value: act ONLY
                # in on_change, which fires just once, when the user actually clicks an option.
                rk = f"capopt_{v['journey']}"
                if rk not in st.session_state:      # first render only; afterwards state rules
                    st.session_state[rk] = (v["caption"] if v.get("caption") in opts else None)
                gc[0].radio("✍ caption options (picking one also sets the matching YouTube "
                            "title) — nothing selected means your hand-edited caption is in use",
                            opts, key=rk, on_change=apply_caption_pick,
                            args=(v["journey"], rk))
            else:
                gc[0].caption("no auto-captions yet — Generate (~5 caption+title options, local VLM).")
            if gc[1].button("✍ Generate", key=f"gencap_{v['journey']}"):
                gen_captions(v["journey"], v.get("model", "ds"), no_theme=no_theme)
                st.info("Generating ~5 captions…" + (" ⚠ GPU busy, may be slow" if pl.gpu_busy() else "")
                        + " — refresh in ~30s.")
        cap = st.text_area("caption (TikTok/Instagram)", v.get("caption", ""),
                           key=f"cap_{v['journey']}", height=90)
        yt = st.text_input("YouTube title (the caption line before the mascot question)",
                           v.get("yt_title", ""), key=f"yt_{v['journey']}")
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
        if marker:
            render_marker(v, marker)
        if extras:
            extras(v)
        c = st.columns(len(actions) + 1)
        if c[0].button("💾 Save", key=f"save_{v['journey']}"):
            d = data(); vv = pl.get(d, v["journey"])
            vv["caption"], vv["yt_title"] = cap, yt
            # a hand-written caption is no longer one of the options -> clear the radio so it
            # shows nothing selected (and can't re-assert itself on the next redraw)
            if cap not in (vv.get("caption_options") or []):
                st.session_state[f"capopt_{v['journey']}"] = None
            pl.save(d)
            set_music_theme(v["journey"], mtheme)
            pl.telem("edit", journey=v["journey"])
            st.success("saved"); st.rerun()
        for i, (label, newstate) in enumerate(actions, start=1):
            kk = newstate if isinstance(newstate, str) else f"fn{i}"
            if c[i].button(label, key=f"act_{kk}_{v['journey']}"):
                if callable(newstate):               # custom action (e.g. the reject variants)
                    newstate(v["journey"])
                elif newstate == "music":
                    approve_to_music(v["journey"])   # phase-shift to the marked start, then → Music
                else:
                    set_state(v["journey"], newstate)
                st.rerun()
    st.divider()


def safe_card(v, *a, **kw):
    """card() for ONE video, isolated. Streamlit runs the whole script top-to-bottom, so an
    exception while drawing video #5 aborts the run and every video BELOW it silently vanishes
    from the tab — while the header metric (computed before the tabs) still counts it. That is
    exactly how a single mojibaked journey spec hid frost_window from Production. Never let one
    video take out the rest of the queue."""
    try:
        card(v, *a, **kw)
    except Exception as e:
        st.error(f"⚠ couldn't render **{v.get('journey')}**: {type(e).__name__}: {e}")
        with st.expander("traceback"):
            import traceback
            st.code(traceback.format_exc())
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
                st.video(str(ap), loop=True)
            else:
                st.warning(f"missing: {c['aligned']}")
            is_chosen = m.get("chosen") == c["id"]
            # TWO DIFFERENT NUMBERS, LABELLED AS SUCH (Phil's correction, 2026-09-10):
            # "the highest lock music is not necessarily the best — some don't have much
            # strong beat at all but might have a high lock value... that's better for
            # comparing internally in a video where to place the start rather than across
            # videos." So BEAT (kick = deep-pulse presence) is the quality signal and leads;
            # SYNC (lock) is shown as what it is — how well this track's own accents sit on
            # the morphs — and never ranked between tracks. An earlier cut of this line
            # marked the highest LOCK as best, which is exactly the misread he flagged.
            _kick = c.get("kick")
            _best_k = max([(x.get("kick") or 0) for x in cands] or [0])
            if _kick is None:
                _beat = "beat ?"
            elif _kick >= 0.40:
                _beat = f"🥁 strong beat {_kick:.2f}"
            elif _kick >= 0.20:
                _beat = f"🥁 clear beat {_kick:.2f}"
            elif _kick >= 0.10:
                _beat = f"faint beat {_kick:.2f}"
            else:
                _beat = f"⚠️ no strong beat {_kick:.2f}"
            _mark = " 🥇" if (_kick is not None and _best_k > 0 and _kick >= _best_k - 0.001) else ""
            # METER FIT (2026-09-10): the picture's morph is reliably periodic, so a take that
            # feels like it lands somewhere different each time is phrasing in a grouping that
            # is not the video's bar. It only OFFENDS when there is a pulse loud enough to
            # hear it — saguaro's choir_of_dust-b (fit 0.71, kick 0.42) drifts audibly while
            # analog_dawn-wild (fit -0.11 but kick 0.03) is harmless under the same picture.
            _fit = c.get("fit")
            if _fit is None:
                _meter = ""
            elif _fit >= 1.0:
                _meter = " · ✓ fits the bar"
            elif (_kick or 0) >= 0.20:
                _meter = f" · ⚠️ PHRASES OFF THE BAR (fit {_fit:.2f}) — will drift against the morphs"
            else:
                _meter = f" · off-bar phrasing (fit {_fit:.2f}) but no real pulse"
            st.caption(f"**{c['id']}**{_mark} · {_beat} · sync {c['lock']}×{_meter}"
                       + (f" · {c['mood']}" if c.get("mood") else "")
                       + (" · ✅ chosen" if is_chosen else ""))
            if st.button("✅ Chosen" if is_chosen else "Choose",
                         # index in the key: duplicate candidate ids (a music_gen plan
                         # collision) must degrade to a cosmetic dupe, never crash the tab
                         key=f"ch_{v['journey']}_{i}_{c['id']}"):
                choose_track(v["journey"], c["id"])
                if choose_advances_to:
                    set_state(v["journey"], choose_advances_to)
                st.rerun()


# ── journeys tab helpers (registry = outbox/journeys.json via pipeline.py) ──────────────
def jdata():
    return pl.jload()


def journey_meta(name):
    """(cards, frames, tier, est_sec, style, theme) straight off the spec — no engine
    imports (this runs on WINDOWS python; grammar/style live in the WSL env). Frame
    count mirrors grammar._frames for the dur-in-beats schema; night_batch re-derives
    it with the real compile before rendering."""
    spec = _read_spec(pl.journey_path(name))
    regs = spec["registers"]
    fpb = spec.get("format", {}).get("frames_per_beat", 7)
    frames = sum(max(fpb, round((r.get("dur") or 4) * fpb)) for r in regs)
    tier = pl.tier_of(len(regs))
    return (len(regs), frames, tier, pl.est_render_sec(frames, planet=pl.has_planet_card(spec)),
            spec.get("style") or (spec.get("style_suffix") or "")[:24],
            spec.get("theme", ""))


@st.cache_data(ttl=120)
def audit_lines():
    """{journey: 'ok ...'/'!! ...'} from scripts/audit_starts.py (WSL env — the audit
    imports nothing heavy but lives repo-side; cached so reruns don't shell out)."""
    import subprocess
    args = "cd /mnt/c/Users/Phil/zoomer && python3 scripts/audit_starts.py"
    cmd = ["wsl", "bash", "-lc", args] if os.name == "nt" else ["bash", "-lc", args]
    try:
        r = subprocess.run(cmd, cwd=str(pl.ROOT), capture_output=True, text=True, timeout=60)
        out = {}
        for line in (r.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("ok", "!!"):
                out[parts[1]] = line.strip()
        return out
    except Exception:
        return {}


def jset(name, **fields):
    """Merge fields into a journey's registry entry (fresh load→save)."""
    jj = jdata()
    jj["journeys"].setdefault(name, {})
    jj["journeys"][name].update(fields, ts=pl._now())
    pl.jsave(jj)


def jpop(name):
    jj = jdata()
    jj["journeys"].pop(name, None)
    pl.jsave(jj)


def jqueue_append(name, **extra):
    jj = jdata()
    order = 1 + max([jj["journeys"][q].get("order", 0) for q in pl.jqueue(jj)] or [-1])
    jj["journeys"].setdefault(name, {})
    jj["journeys"][name].update({"state": "queued", "order": order,
                                 "ts": pl._now(), **extra})
    pl.jsave(jj)


def reject_review(journey, requeue=None):
    """Reject a video at Video Review. requeue=None: the JOURNEY was the problem — mark it
    rejected too (never re-render). 'front'/'back': the RENDER was the problem, not the idea
    — send the journey back to the render queue at that end, force=True so the batch renders
    a fresh vN even though a complete render exists (queue_review will flip this entry back
    to review when the new render lands)."""
    set_state(journey, "rejected")
    jj = jdata()
    if requeue:
        # 🎲 checkbox on the card: new seed = explore a different draw (default);
        # unchecked = same seed, for re-rendering through an ENGINE change.
        # ↻ from-card > 0 = PARTIAL re-render (keep cards 0..K-1's frames, dive --from-card).
        new_seed = bool(st.session_state.get(f"reseed_{journey}", True))
        from_card = int(st.session_state.get(f"fromcard_{journey}", 0) or 0)
        jj["journeys"].setdefault(journey, {})
        note = ("re-render: video rejected in review"
                + (f" (from card {from_card})" if from_card else "")
                + ("" if new_seed else " (same seed)"))
        jj["journeys"][journey].update({"state": "queued", "force": True,
                                        "new_seed": new_seed, "ts": pl._now(), "note": note})
        if from_card:
            jj["journeys"][journey]["from_card"] = from_card
        else:
            jj["journeys"][journey].pop("from_card", None)
        others = [q for q in pl.jqueue(jj) if q != journey]
        pl.set_jorder(jj, [journey] + others if requeue == "front" else others + [journey])
        pl.telem("jqueued", journey=journey,
                 detail=f"reject -> re-queue {requeue}"
                        + (f", from card {from_card}" if from_card else "")
                        + ("" if new_seed else ", same seed"))
    else:
        jj["journeys"][journey] = {"state": "rejected", "ts": pl._now(),
                                   "note": "rejected at video review"}
    pl.jsave(jj)


# ── header + tabs ────────────────────────────────────────────────────────────────────────
d = data()
counts = Counter(v.get("state") for v in d["videos"])
# Live/Failed are by PLATFORM status, not the top-level state: a video live on IG+YT but
# dropped on TikTok is BOTH live (somewhere) and failed (somewhere), so it shows in both.
live_vids = [v for v in d["videos"] if any_live(v)]
# newest went-live first (Phil 2026-08-17): latest platform live timestamp, falling back
# to created — the old insertion order read as random
live_vids.sort(key=lambda v: max([pp.get("ts", "") or "" for pp in v.get("platforms", {}).values()]
                                 + [v.get("created", "")]), reverse=True)
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

JD = pl.jload()
tabs = st.tabs([f"🗺 Journeys ({len(pl.jqueue(JD))})",
                f"🎬 Video Review ({counts.get('review',0)})",
                f"🎵 Music ({counts.get('music',0)})",
                f"🚀 Production ({counts.get('queued',0)})",
                f"Live ({len(live_vids)})",
                f"Failed ({len(failed_vids)})",
                "Telemetry",
                "⚙ Settings",
                "🧭 How it works"])

with tabs[1]:  # VIDEO REVIEW — pick cut/model, edit caption, send to Music
    st.write("Look at the video, pick cut/model, edit the caption/theme, then **Approve → Music** "
             "to choose a soundtrack.")
    def _rendered_at(v):
        # newest RENDER first (Phil 2026-09-18): `created` is the entry's first-ever date and
        # never moves on a re-render, so sort by the review file's own mtime (queue_review
        # re-copies it on every ingest / re-assembly); fall back to created.
        try:
            return (os.path.getmtime(pl.ROOT / v["file"]), v.get("created", ""))
        except Exception:
            return (0.0, v.get("created", ""))
    rv = sorted(by_state(d, "review"), key=_rendered_at, reverse=True)
    if not rv:
        st.info("Nothing awaiting video review.")
    def review_extras(v):
        ec = st.columns([3, 2])
        ec[0].checkbox("🎲 new seed if re-queued (uncheck to keep the seed — e.g. re-render "
                       "through an engine change)",
                       value=True, key=f"reseed_{v['journey']}")
        try:
            maxc = len(_read_spec(pl.journey_path(v["journey"]))["registers"]) - 1
        except Exception:
            maxc = 12
        ec[1].number_input("↻ from card (0 = full re-render; K keeps cards 0..K-1's frames)",
                           0, maxc, 0, key=f"fromcard_{v['journey']}")

    for v in rv:
        safe_card(v, [("✅ Approve → Music", "music"),
                      ("🔁 Reject → front of queue", lambda j: reject_review(j, "front")),
                      ("🔁 Reject → back of queue", lambda j: reject_review(j, "back")),
                      ("🗑 Reject journey", lambda j: reject_review(j))],
                  marker="start", captions=True, extras=review_extras)

with tabs[2]:  # MUSIC — audition/generate a track, then send to Production
    st.caption("🥁 **beat** = deep-pulse presence, the thing you hear as a strong beat — rank "
               "by this. **sync** = how well that track's own accents sit on the morphs; it is "
               "a within-track number (it picks where the loop starts), NOT a quality score to "
               "compare tracks by. **fit** = does the track phrase in the video's bar? Below "
               "1.0 a rival phrase length is stronger, so its downbeat walks around the "
               "morphs — audible only when the pulse is strong.")
    st.write("Pick the soundtrack. Every candidate is auto-locked so its accent lands on each "
             "morph. Choose one → it moves to **Production**. Switch a video's model and it lands "
             "back here to get tracks for the new render.")
    mv = by_state(d, "music")
    if not mv:
        st.info("Nothing needs music. Approve a video in Video Review to send it here.")
    gpu_busy = pl.comfy_busy() if mv else False
    if gpu_busy and mv:
        st.warning("⚠ ComfyUI is mid-job (a render or music gen). Videos with pre-generated "
                   "tracks still get their music on approve (aligning needs no GPU). Only a "
                   "full Generate / Regenerate has to queue behind the running job.")
    for v in mv:
        m = v.get("music") or {}
        tag = f"✅ {m['chosen']}" if m.get("chosen") else "— choose one —"
        st.subheader(f"{v['journey']} · {v['model']}/{v['cut']}"
                     + (f" · {m['bpm']}bpm {m.get('key','')}" if m.get("bpm") else "")
                     + f" · {tag}"
                     # regeneration is otherwise invisible: the lanes come back with the same
                     # names, so only a changing stamp proves the five takes are new
                     + (f" · generated {m['generated_at']}" if m.get("generated_at") else ""))
        tcol = st.columns([5, 1])
        newtheme = tcol[0].text_input("🎵 music theme (scene)", get_music_theme(v["journey"]),
                                      key=f"mtm_{v['journey']}")
        if not music_fresh(v):
            note = (f"music was generated for {m.get('stale_from')}, not {v['model']}/{v['cut']}"
                    if m.get("stale_from") or music_stale(v) else "no tracks generated yet")
            st.warning(f"{note} — generate 5 tracks for this render.")
            if v.get("music_pregen"):
                # the overnight tracks exist; they only need aligning to this cut + start.
                # No GPU, so it works while a render is running.
                if st.button("⚡ Align the pre-generated tracks (no GPU, ~1 min)",
                             key=f"realign_{v['journey']}"):
                    regenerate_music(v["journey"])
                    st.info("Aligning the five pre-generated tracks — refresh in about a minute.")
            if tcol[1].button("🎵 Generate 5", key=f"gen_{v['journey']}"):
                set_music_theme(v["journey"], newtheme)
                regenerate_music(v["journey"], fresh=True)
                st.info(f"Generating 5 tracks for {v['journey']} ({v['model']}/{v['cut']}) "
                        "on ComfyUI — refresh in ~2–3 min.")
        else:
            if tcol[1].button("🔄 Regenerate", key=f"regen_{v['journey']}",
                              help="full GPU generation with re-rolled seeds AND lanes — "
                                   "genuinely different tracks each click (~2–3 min)"):
                set_music_theme(v["journey"], newtheme)
                regenerate_music(v["journey"], fresh=True)
                st.info(f"Regenerating {v['journey']} with fresh seeds + lanes — ComfyUI is "
                        "generating 5 new tracks, refresh in ~2–3 min.")
            audition_candidates(v, choose_advances_to="queued")
        cc = st.columns([1, 1, 4])
        if cc[0].button("↩ Back to Review", key=f"back_{v['journey']}"):
            # REVERT to the UN-SHIFTED cut (Phil 2026-08-23): the start marker is applied
            # against the original on approve, so the review player must SHOW the original.
            # Leaving v.file on the _shift copy made re-marking a start un-doable (the time
            # entered never matched what was on screen) — the ruby_furnace class of bug.
            dd2 = data(); vv = pl.get(dd2, v["journey"])
            if vv.get("orig_file"):
                vv["file"] = vv["orig_file"]
            vv["state"] = "review"
            pl.save(dd2); pl.telem("state", journey=v["journey"], detail="review (unshifted)")
            st.rerun()
        if cc[1].button("🔇 Skip music → Production", key=f"skip_{v['journey']}"):
            set_state(v["journey"], "queued"); st.rerun()
        st.divider()

with tabs[3]:  # PRODUCTION — the ordered post queue; tweak cut/model + change the music pick
    st.write("Approved & in post order (top posts next). ⬆⬇ to reorder. You can still switch "
             "cut/model or change the music pick here.")
    qv = pl.queued(d)
    pnc = st.columns([1, 5])
    if pnc[0].button("📤 Post now", disabled=not qv,
                     help="posts the top video immediately; the next post then reschedules "
                          "cadence hours later, rounded to the nearest hour"):
        # open the gate (post_next = now) and fire it — reusing post_gate.py end to end
        # means the button and the hourly task share ONE code path (posting, verification,
        # and the advance-to-nearest-hour reschedule can't diverge)
        import subprocess
        from datetime import datetime
        jj = pl.jload()
        jj["settings"]["post_next"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        pl.jsave(jj)
        args = ("cd /mnt/c/Users/Phil/zoomer && "
                "python3 scripts/post_gate.py >> outbox/post_gate.log 2>&1")
        cmd = ["wsl", "bash", "-lc", args] if os.name == "nt" else ["bash", "-lc", args]
        subprocess.Popen(cmd, cwd=str(pl.ROOT))
        pnc[1].info("posting the top video — takes a few minutes (browser + verification); "
                    "watch outbox/post_gate.log, it lands in the Live tab when verified")
    if not qv:
        st.info("Production queue is empty.")
    for i, v in enumerate(qv):
        top = st.columns([1, 1, 1, 9])
        if top[0].button("⬆", key=f"up_{v['journey']}", disabled=(i == 0)):
            dd = data(); pl.move(dd, v["journey"], -1); pl.save(dd); st.rerun()
        if top[1].button("⬇", key=f"dn_{v['journey']}", disabled=(i == len(qv) - 1)):
            dd = data(); pl.move(dd, v["journey"], +1); pl.save(dd); st.rerun()
        top[2].subheader(f"#{i + 1}")
        with top[3]:
            m = v.get("music") or {}
            chosen = m.get("chosen")
            st.caption("🎵 " + (f"music: **{chosen}**" if chosen else "no music selected"))
            safe_card(v, [("↩ Unqueue", "music" if not chosen else "review")],
                      marker="cover", captions=True)
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

with tabs[0]:  # JOURNEYS — the render queue the 01:30 batch draws from (journeys come first)
    jd = JD
    s = jd["settings"]
    TIER_CHIP = {"short": "🟢 S", "medium": "🟡 M", "long": "🔴 L"}

    # states: stored decision or derived (pipeline entry ⇒ rendered, else new)
    meta, broken = {}, {}
    for name in pl.journey_names():
        try:
            meta[name] = journey_meta(name)
        except Exception as e:
            broken[name] = f"{type(e).__name__}: {e}"
    states = {n: pl.jstate(n, jd, d) for n in meta}
    q_names = [n for n in pl.jqueue(jd) if n in meta]
    avail = [n for n in meta if states[n] == "new" and n not in broken]
    rendered = [n for n in meta if states[n] == "rendered"]
    rfailed = [n for n in meta if states[n] == "render_failed"]
    rejected = [n for n in meta if states[n] == "rejected"]
    ests = {n: meta[n][3] for n in q_names}
    tiers = {n: meta[n][2] for n in q_names}
    picks, total = pl.pick_tonight(jd, ests)

    from collections import Counter as _C
    tc = _C(tiers.values())
    hc = st.columns(4)
    hc[0].metric("journey queue", f"{len(q_names)}/{s['journey_queue_target']}",
                 f"{tc.get('long',0)}L {tc.get('medium',0)}M {tc.get('short',0)}S",
                 delta_color="off")
    nights = (sum(ests.values()) / (s["render_budget_min"] * 60)) if q_names else 0
    hc[1].metric("est. runway", f"{nights:.1f} nights")
    ready = counts.get("queued", 0)
    awaiting = counts.get("review", 0) + counts.get("music", 0)
    hc[2].metric("ready to post", f"{ready}/{s['max_ready_videos']}",
                 f"{awaiting}/{s.get('max_review_videos', 20)} awaiting review", delta_color="off")
    hc[3].metric("tonight", f"{len(picks)} renders" if picks else "—")
    if s.get("render_paused"):
        st.warning("⏸ nightly rendering is PAUSED (Settings tab)")
    elif awaiting >= s.get("max_review_videos", 20):
        st.warning(f"⛔ backpressure: {awaiting} videos awaiting your review — "
                   "the 01:30 batch will skip until the review queue drains below "
                   f"{s.get('max_review_videos', 20)}")
    elif ready >= s["max_ready_videos"]:
        st.warning(f"⛔ backpressure: {ready} videos ready to post — "
                   "the 01:30 batch will skip until the production queue drains")
    elif picks:
        st.info("🌙 tonight (queue order): " + " + ".join(
            f"{n} ({tiers[n][0].upper()} ~{ests[n] // 60}min)" for n in picks)
            + f" = {total / 3600:.1f}h of {s['render_budget_min'] // 60}h")
    else:
        st.info("queue is empty — the midnight refill will compose journeys, or Queue some below")

    st.subheader(f"render queue ({len(q_names)})")
    run_total = 0
    for i, n in enumerate(q_names):
        cards, frames, tier, est, style, theme = meta[n]
        run_total += est
        row = st.columns([1, 1, 6, 1, 1])
        if row[0].button("⬆", key=f"jq_up_{n}", disabled=(i == 0)):
            jj = jdata(); pl.jmove(jj, n, -1); pl.jsave(jj); st.rerun()
        if row[1].button("⬇", key=f"jq_dn_{n}", disabled=(i == len(q_names) - 1)):
            jj = jdata(); pl.jmove(jj, n, +1); pl.jsave(jj); st.rerun()
        e = jd["journeys"].get(n, {})
        row[2].markdown(f"**{n}** · {TIER_CHIP[tier]} · {cards} cards/{frames}f "
                        f"· ~{est // 60}min (cum {run_total // 60}) · {style}"
                        + (" · 🌙 tonight" if n in picks else "")
                        + (f" · ↻ from card {e['from_card']}" if e.get("from_card")
                           else (" · 🔁 force re-render" if e.get("force") else "")))
        if e.get("note"):
            row[2].caption(e["note"])
        if row[3].button("↩", key=f"jq_unq_{n}", help="unqueue"):
            jpop(n); st.rerun()
        if row[4].button("🗑", key=f"jq_rej_{n}", help="reject"):
            jset(n, state="rejected"); pl.telem("rejected", journey=n); st.rerun()
    if not q_names:
        st.caption("nothing queued")

    if rfailed:
        st.subheader(f"⚠ render failed ({len(rfailed)})")
        for n in rfailed:
            e = jd["journeys"].get(n, {})
            row = st.columns([8, 1, 1])
            row[0].markdown(f"**{n}** — {e.get('note', 'failed')}")
            if row[1].button("🔁", key=f"rf_rq_{n}", help="re-queue"):
                jqueue_append(n); st.rerun()
            if row[2].button("🗑", key=f"rf_rej_{n}", help="reject"):
                jset(n, state="rejected"); st.rerun()

    st.subheader(f"available ({len(avail)})")
    audits = audit_lines()
    for n in sorted(avail, key=lambda x: meta[x][2]):
        cards, frames, tier, est, style, theme = meta[n]
        a = audits.get(n, "")
        badge = "✅" if a.startswith("ok") else ("❗" if a else "•")
        row = st.columns([8, 1, 1])
        row[0].markdown(f"{badge} **{n}** · {TIER_CHIP[tier]} · {cards} cards/{frames}f "
                        f"· ~{est // 60}min · {style}")
        note = (jd["journeys"].get(n, {}) or {}).get("note", "")
        cap = " · ".join(x for x in [theme[:80], note, a if not a.startswith("ok") else ""] if x)
        if cap:
            row[0].caption(cap)
        if row[1].button("➕", key=f"av_q_{n}", help="queue for render"):
            jqueue_append(n); pl.telem("jqueued", journey=n); st.rerun()
        if row[2].button("🗑", key=f"av_rej_{n}", help="reject"):
            jset(n, state="rejected"); pl.telem("rejected", journey=n); st.rerun()
    for n, err in broken.items():
        st.error(f"**{n}**: spec unreadable — {err}")

    st.subheader(f"rendered ({len(rendered)})")
    for n in rendered:
        cards, frames, tier, est, style, theme = meta[n]
        v = pl.get(d, n) or {}
        vstate = v.get("state", "?")
        chip = {"review": "🎬 review", "music": "🎵 music", "queued": "🚀 production",
                "live": "🟢 live", "failed": "🔴 failed", "rejected": "🗑 rejected"}
        row = st.columns([9, 1])
        row[0].markdown(f"**{n}** · {TIER_CHIP[tier]} · {chip.get(vstate, vstate)}"
                        + (f" · {platform_line(v)}" if any_live(v) or any_failed(v) else ""))
        if row[1].button("🔁", key=f"rd_rq_{n}", help="re-queue (renders a fresh vN)"):
            jqueue_append(n, force=True); st.rerun()

    if rejected:
        with st.expander(f"rejected ({len(rejected)})"):
            for n in rejected:
                row = st.columns([9, 1])
                row[0].markdown(f"**{n}**")
                if row[1].button("♻", key=f"rj_re_{n}", help="restore to available"):
                    jpop(n); st.rerun()

    with st.expander("legacy journeys (not queueable — superseded schemas)"):
        for sub in ("engine1", "engine0"):
            names = sorted(p.stem for p in (pl.JOURNEYS_DIR / sub).glob("*.json"))
            st.caption(f"**{sub}** ({len(names)}): " + ", ".join(names))

with tabs[4]:  # LIVE — anything live on at least one platform (noting where)
    if not live_vids:
        st.info("Nothing live yet.")
    # latest scraped IG numbers per reel shortcode (outbox/ig_stats.jsonl, appended by
    # scripts/ig_stats.py after every post + the 12:00/00:00 PowersOfZen-igstats task) —
    # read fresh on every rerun (never cache this), file is append-ordered so last row wins
    import re as _re
    import math as _math
    IG_STATS = {}
    _igp = pl.ROOT / "outbox" / "ig_stats.jsonl"
    if _igp.exists():
        for _line in _igp.read_text(encoding="utf-8").splitlines():
            try:
                _r = json.loads(_line)
            except Exception:
                continue
            if _r.get("code"):
                IG_STATS[_r["code"]] = _r
            if _r.get("journey"):        # fallback join for old posts with no recorded URL
                IG_STATS["j:" + _r["journey"]] = _r
    # ---- header: freshest snapshot + TOP 5 BY QSCORE (Phil 2026-08-22) ----
    # qscore = the agreed ranking metric (audience-stats skill / ig_analyze.py): actual
    # engagement E = likes + 3*comments divided by the catalog's own fitted scaling law
    # a*views^b — like-rate mechanically decays with reach, so raw like% punishes videos
    # that EARNED a push; qscore 1.0 = catalog-typical at that reach. Pure-python OLS on
    # (log views, log E) — same fit as ig_analyze, no numpy on the Windows side.
    _srows = [dict(r) for c, r in IG_STATS.items()
              if not c.startswith("j:") and r.get("views") and r.get("likes") is not None]
    if _srows:
        _newest = max(r.get("ts", "") for r in _srows)
        _fol = next((r.get("followers") for r in _srows
                     if r.get("ts") == _newest and r.get("followers")), None)
        st.caption(f"📈 **{_fol if _fol is not None else '—'} followers** · IG stats over "
                   f"{len(_srows)} reels · last scrape {_newest[:16]} "
                   "(auto: after every post + 12:00 + 00:00)")
    if len(_srows) >= 5:
        for _r in _srows:
            _r["E"] = _r["likes"] + 3 * (_r.get("comments") or 0)
        _xs = [_math.log(_r["views"]) for _r in _srows]
        _ys = [_math.log(_r["E"] + 0.5) for _r in _srows]
        _mx = sum(_xs) / len(_xs); _my = sum(_ys) / len(_ys)
        _b = (sum((x - _mx) * (y - _my) for x, y in zip(_xs, _ys))
              / (sum((x - _mx) ** 2 for x in _xs) or 1.0))
        _a = _math.exp(_my - _b * _mx)
        for _r in _srows:
            _r["q"] = (_r["E"] + 0.5) / (_a * _r["views"] ** _b)
        st.markdown("**🏆 Top 5 by qscore** (engagement ÷ expected at that reach; 1.0 = typical)")
        # display floor 100 views (fit uses ALL rows, same as ig_analyze): sub-100-view
        # qscores are jumpy — one comment swings them (audience-stats doctrine)
        _top = sorted((r for r in _srows if r["views"] >= 100), key=lambda r: -r["q"])[:5]
        _cols = st.columns(5)
        for _c, _r in zip(_cols, _top):
            _c.metric(_r.get("journey") or _r["code"], f"{_r['q']:.2f}×")
            _c.caption(f"👁 {_r['views']} · ❤️ {_r['likes']} · 💬 {_r.get('comments') or 0}")
        st.divider()
    for v in live_vids:
        live_on = ", ".join(platforms_by_status(v, "live"))
        failed_on = ", ".join(platforms_by_status(v, "failed"))
        st.markdown(f"**{v['journey']}** ({v['model']}/{v['cut']}) — {platform_line(v)}")
        note = f"live on **{live_on}**" + (f" · ❌ not on **{failed_on}**" if failed_on else "")
        st.caption(note)
        _igu = v.get("platforms", {}).get("instagram", {}).get("url") or ""
        _mc = _re.search(r"/reel/([^/?]+)", _igu)
        _stat = (IG_STATS.get(_mc.group(1)) if _mc else None) \
            or IG_STATS.get("j:" + v["journey"])
        if _stat:
            st.caption(f"👁 {_stat.get('views', '—')} views · ❤️ {_stat.get('likes', '—')} likes"
                       f" · 💬 {_stat.get('comments', 0)} comments"
                       f" · IG, scraped {_stat.get('ts', '')[:16]}")
        for k in pl.PLATFORMS:
            if v["platforms"].get(k, {}).get("url"):
                st.markdown(f"- {k}: {v['platforms'][k]['url']}")
        st.caption(v.get("caption", ""))
        st.divider()

with tabs[5]:  # FAILED — anything failed on at least one platform (noting where)
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

with tabs[6]:  # TELEMETRY
    ev = pl.read_telem(200)[::-1]
    if not ev:
        st.info("no events yet")
    for e in ev:
        icon = {"post": "✅", "post_fail": "❌", "flag": "⚠️", "render": "🎬",
                "render_fail": "💥", "music_gen": "🎵", "music_choose": "🎶",
                "switch": "🔀", "batch_skip": "⏭", "batch_done": "🌙",
                "refill": "🧭", "refill_done": "🧭", "refill_fail": "💥",
                "jqueued": "🗺", "ig_stats": "📊", "ig_insights": "📈",
                "ig_insights_login": "🔑"}.get(e["event"], "•")
        st.text(f"{icon} {e['ts']}  {e['event']}  {e.get('journey','')} "
                f"{e.get('platform','')}  {e.get('detail','')}"
                + (f"  {e.get('reason','')}" if e.get('reason') else ""))

with tabs[7]:  # SETTINGS — the pipeline knobs (outbox/journeys.json + platform pauses)
    st.write("Pipeline knobs. Refill 00:00 and render 01:30 live in Windows Task "
             "Scheduler (scripts/SCHEDULER.md); POSTING is cadence-based below.")
    jd = pl.jload()
    s = jd["settings"]
    st.markdown("**posting cadence** — an hourly gate fires the poster once `next post` "
                "arrives, then advances by the cadence (missed windows never burst-post)")
    pcad = st.columns(2)
    post_every = pcad[0].number_input("post every (hours)", 1.0, 96.0,
                                      float(s.get("post_every_hours", 19)), step=1.0)
    post_next = pcad[1].text_input("next post (YYYY-MM-DD HH:MM)",
                                   s.get("post_next", ""))
    c = st.columns(4)
    budget = c[0].number_input("render budget (min/night)", 30, 600,
                               int(s["render_budget_min"]), step=30)
    maxready = c[1].number_input("backpressure: max ready-to-post videos", 1, 100,
                                 int(s["max_ready_videos"]))
    maxreview = c[1].number_input("backpressure: max videos awaiting review", 1, 100,
                                  int(s.get("max_review_videos", 20)))
    qtarget = c[2].number_input("journey queue target", 1, 100,
                                int(s["journey_queue_target"]))
    maxnight = c[3].number_input("refill: max composed/night", 0, 10,
                                 int(s["refill_max_per_night"]))
    c2 = st.columns(3)
    shares = {}
    for i, t in enumerate(("long", "medium", "short")):
        shares[t] = c2[i].number_input(f"tier share — {t}", 0.0, 1.0,
                                       float(s["tier_share"].get(t, 0.3)), step=0.05,
                                       help="Monte Carlo weights for the refill's tier "
                                            "draw — the queue (and so the nightly render "
                                            "mix, which runs in queue order) converges "
                                            "to these ratios")
    t1, t2, t3 = st.columns(3)
    rpaused = t1.toggle("⏸ pause nightly rendering", value=bool(s["render_paused"]))
    # PLANET PLATE (2026-09-17): lab arm B on every planet-class card in the nightly
    _pmodes = ["live", "low", "off"]
    pmode = t1.selectbox("🪐 planet plate (space→planet descent)", _pmodes,
                         index=_pmodes.index(s.get("plate_mode") or "off")
                         if (s.get("plate_mode") or "off") in _pmodes else 0,
                         help="live = the approved descent (live arrival, globe enters the "
                              "frame); low = the first version (pixel-blended arrival); off = "
                              "the pre-plate engine. Applies to the next renders.")
    _pintros = ["enter", "mix", "auto", "grow", "plain"]
    pintro = t1.selectbox("🪐 how the globe arrives", _pintros,
                          index=_pintros.index(s.get("plate_intro") or "enter")
                          if (s.get("plate_intro") or "enter") in _pintros else 0,
                          help="enter = slides in from beyond a frame edge (edge varies per "
                               "journey) — the approved one; mix = the unified entrances (each "
                               "journey draws one: a globe entering from any direction, a point "
                               "that swells in place anywhere in frame, or a small planet that "
                               "travels in while it grows) — still in the lab; grow = from a "
                               "point; auto = enter or grow; plain = appears at the zoom's rate.")
    # PALETTE ANCHOR (2026-10-03): the counter to the chain's drift toward one orange
    # palette — colour-match toward the card's authored palette instead of a drifted frame
    panchor = t2.number_input("🎨 palette anchor strength (0 = off)", 0.0, 1.0,
                              float(s.get("palette_anchor") or 0.0), step=0.05,
                              help="Every travel frame is colour-matched toward the card's "
                                   "AUTHORED palette at this strength (the lab used 0.5: a "
                                   "cerulean card recovered from a fully orange start in ~16 "
                                   "frames). 0 = the old behaviour (match toward the phase's own "
                                   "first frame, which drifts orange). Applies to the next renders.")
    fpaused = t2.toggle("⏸ pause midnight refill", value=bool(s["refill_paused"]))
    st.markdown("**platform pauses** (scheduler skips paused platforms when posting)")
    pc = st.columns(len(pl.PLATFORMS))
    plat_paused = {}
    for i, k in enumerate(pl.PLATFORMS):
        plat_paused[k] = pc[i].toggle(f"⏸ {k}", value=(k in PAUSED),
                                      key=f"set_pause_{k}")
    if st.button("💾 Save settings"):
        jj = pl.jload()
        jj["settings"].pop("nightly_templates", None)   # retired 2026-08-26 (queue order)
        jj["settings"].update({
            "render_budget_min": int(budget), "max_ready_videos": int(maxready),
            "max_review_videos": int(maxreview),
            "journey_queue_target": int(qtarget), "refill_max_per_night": int(maxnight),
            "tier_share": shares,
            "render_paused": bool(rpaused), "refill_paused": bool(fpaused),
            "plate_mode": ("" if pmode == "off" else pmode), "plate_intro": pintro,
            "palette_anchor": float(panchor),
            "post_every_hours": float(post_every),
            "post_next": post_next.strip()})
        pl.jsave(jj)
        dd = data()
        dd.setdefault("meta", {})["paused_platforms"] = \
            [k for k, p in plat_paused.items() if p]
        pl.save(dd)
        pl.telem("settings", detail="edited in dashboard")
        st.success("saved"); st.rerun()


with tabs[8]:  # HOW IT WORKS — the visual map of the whole project (static page, 2026-09-19)
    # Built by scripts/build_overview.py into dashboard/overview.html: one self-contained page
    # (inline CSS + SVG + a few real frames). Static on purpose for now; rebuild to refresh.
    # 2026-10-03: the page was promoted to the repo root as index.html (the powersofzen.com
    # landing page, hand-polished there) — read that; the dashboard/ copy is only a preview build
    _ov = pl.ROOT / "index.html"
    if not _ov.exists():
        _ov = pl.ROOT / "dashboard" / "overview.html"
    if _ov.exists():
        import streamlit.components.v1 as _components
        _components.html(_ov.read_text(encoding="utf-8"), height=7000, scrolling=True)
        st.caption("Static snapshot. Rebuild with: python3 scripts/build_overview.py")
    else:
        st.info("Overview page not built yet — run: python3 scripts/build_overview.py")
