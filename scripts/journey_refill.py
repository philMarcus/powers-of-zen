#!/usr/bin/env python3
"""journey_refill — the midnight coordinator→composers run (Task Scheduler, 00:00).

Tops the journey render queue up toward settings.journey_queue_target (composing at
most refill_max_per_night per run) with ONE headless Claude session:

  coordinator (Fable) — reads journeys/VARIATIONS.md + the active catalog, extends
    VARIATIONS.md if it's mined out, writes n bare-bones BRIEFS (tier pre-assigned
    by THIS script from tier_share deficits — deterministic, not the model's whim)
    to outbox/refill_briefs_<date>.md, then spawns n parallel composer subagents
    (Opus) that each flesh one brief into journeys/<name>.json via the
    journey-composer skill.

Claude only WRITES files. This script then diffs the catalog, runs the render_start
audit + a real compile on each new journey, and auto-queues only the passers
(failures stay visible in the dashboard's Journeys tab with a note).

Usage: python3 scripts/journey_refill.py [--dry-run]
"""
import fcntl
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pipeline as pl  # noqa: E402

LOCK = Path("/tmp/zoomer_refill.lock")   # WSL-local fs — flock over drvfs is unreliable
CLAUDE_TIMEOUT = 45 * 60                 # hard stop well before the 01:30 render batch
CARD_RANGE = {"short": "4-5", "medium": "6-8", "long": "9-11"}


def log(msg):
    print(f"=== {time.strftime('%H:%M:%S')} {msg}", flush=True)


def queued_tiers(jd):
    out = []
    for name in pl.jqueue(jd):
        p = pl.journey_path(name)
        try:
            import json
            out.append(pl.tier_of(len(json.loads(
                p.read_text(encoding="utf-8"))["registers"])))
        except Exception:
            pass
    return out


def coordinator_prompt(briefs, date):
    # tempo is ASSIGNED per brief like the tier (2026-08-14 lesson: six composers left to
    # choose all picked the same fpb — variety must be deterministic, not the model's whim);
    # cycle favors the 7/8 heartland with 6 and 9 as accents (5 and 10 are rare tails Phil
    # reserves for deliberate spice, never the nightly default)
    _FPB_CYCLE = [7, 8, 6, 8, 9]
    tier_lines = "\n".join(
        f"  brief {i + 1}: {t.upper()} ({CARD_RANGE[t]} cards) · "
        f"format.frames_per_beat = {_FPB_CYCLE[i % len(_FPB_CYCLE)]} (assigned — composer "
        f"must use it)"
        for i, t in enumerate(briefs))
    n = len(briefs)
    try:
        audit = subprocess.run([sys.executable, str(ROOT / "scripts" / "novelty_audit.py"),
                                "--brief"], capture_output=True, text=True, timeout=120).stdout
    except Exception:
        audit = "(novelty audit unavailable)"
    return f"""You are the overnight JOURNEY COORDINATOR for Powers of Zen. Your job tonight: get {n} new dive-video journeys composed. You coordinate; composer subagents write the journey files.

Tonight's MEASURED catalog-repetitiveness report (this is data, not vibes — brief against it):
{audit}

Step 1 — study what exists so the new journeys are maximally DIFFERENT from it:
- Read journeys/VARIATIONS.md (the differentiation library — its PERFORMANCE NOTES are measured audience findings) and journeys/REALMS.md (the scale-band formalism: real archetypes per power of ten, the material-continuation rule, POV attitudes).
- Survey the active catalog: read every journeys/*.json top-level (name, theme, style, seam cards) — Glob journeys/*.json (ignore journeys/engine1/ and journeys/engine0/, they are retired schemas).
- If the variation library feels mined out (most entries already used by the catalog), ADD fresh entries to VARIATIONS.md first, in its existing format, and draw on those. Same for a REALMS.md band the report shows mined out.
- Aim briefs at what the report says is MISSING: under-built bands (molecular machinery especially), populated ecosystems, unbroken material continuation — while avoiding the overused-word monoculture.

Step 2 — write {n} bare-bones briefs to outbox/refill_briefs_{date}.md. Each brief: a working name (snake_case, must not collide with ANY existing journey in journeys/, journeys/engine1/, journeys/engine0/, or any output/ directory), a 1-2 sentence concept, a palette family, a math/space personality, a seam idea, and its assigned length tier. The tiers are FIXED, one brief each:
{tier_lines}
Make the {n} briefs maximally distinct from the catalog AND from each other (different palette families, different math patterns, different seam types).

Step 3 — spawn {n} composer subagents IN PARALLEL via the Agent tool (pass model "opus" if the tool supports a model override). Each subagent gets: its ONE brief verbatim, its tier's card-count range, and the instruction to follow the journey-composer skill (.claude/skills/journey-composer/SKILL.md) exactly and write the finished journey to journeys/<name>.json. The skill is the authoring doctrine — the brief only seeds it.

Step 4 — after all composers finish, end with one line per new journey: name, tier, card count.

Hard rules: do NOT queue anything, do NOT edit existing journeys (VARIATIONS.md additions excepted), do NOT delete anything. If a composer fails, note it and move on — never rewrite its journey yourself from scratch in this session."""


def run_claude(prompt, model):
    exe = shutil.which("claude")
    if not exe:
        return 127, "claude CLI not on PATH"
    argv = [exe, "-p", prompt, "--model", model,
            "--permission-mode", "acceptEdits", "--max-turns", "60",
            "--allowedTools",
            "Bash(python3 scripts/audit_starts.py:*),Bash(python3 scripts/preflight.py:*)"]
    try:
        r = subprocess.run(argv, cwd=str(ROOT), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=CLAUDE_TIMEOUT)
        print(r.stdout or "", flush=True)
        return r.returncode, (r.stdout or "")[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "claude run hit the 45min timeout"


def audit_pass(name):
    """(ok, why). Real compile (same as the renderer) + the render_start audit line."""
    try:
        pl.journey_frames(name)
    except Exception as e:
        return False, f"does not compile: {e}"
    r = subprocess.run(["python3", "scripts/audit_starts.py"], cwd=str(ROOT),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in (r.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == name:
            return (parts[0] == "ok"), line.strip()
    return False, "not seen by audit_starts (schema?)"


def main():
    dry = "--dry-run" in sys.argv
    jd = pl.jload()
    s = jd["settings"]
    if s.get("refill_paused"):
        log("refill_paused is set — skipping")
        return
    depth = len(pl.jqueue(jd))
    target = s["journey_queue_target"]
    n = min(s["refill_max_per_night"], target - depth)
    if n <= 0:
        log(f"journey queue {depth}/{target} — no refill needed")
        return

    briefs = pl.refill_tiers(jd, queued_tiers(jd), n)
    log(f"queue {depth}/{target} — composing {n}: {', '.join(briefs)}")
    if dry:
        return

    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("another refill is already running — exiting")

    before = set(pl.journey_names())
    date = time.strftime("%Y%m%d")
    prompt = coordinator_prompt(briefs, date)
    rc, tail = run_claude(prompt, "fable")
    if rc != 0:
        log(f"coordinator on fable failed (rc {rc}: {tail[-200:]}) — retrying on opus")
        rc, tail = run_claude(prompt, "opus")
    new = sorted(set(pl.journey_names()) - before)
    if rc != 0 and not new:
        log(f"refill FAILED (rc {rc}) — no new journeys")
        pl.telem("refill_fail", detail=tail[-300:])
        sys.exit(1)

    log(f"{len(new)} new journeys: {', '.join(new) or '(none)'}")
    queued_n = 0
    for name in new:
        ok, why = audit_pass(name)
        jj = pl.jload()
        if ok:
            order = 1 + max([jj["journeys"][q].get("order", 0)
                             for q in pl.jqueue(jj)] or [-1])
            jj["journeys"][name] = {"state": "queued", "order": order, "ts": pl._now(),
                                    "note": "composed by midnight refill"}
            queued_n += 1
            pl.telem("refill", journey=name, detail=f"auto-queued ({why})")
            log(f"  {name}: QUEUED ({why})")
        else:
            jj["journeys"][name] = {"note": f"refill: audit failed — {why}",
                                    "ts": pl._now()}
            pl.telem("refill", journey=name, detail=f"NOT queued: {why}")
            log(f"  {name}: NOT queued — {why}")
        pl.jsave(jj)
    summary = f"refill done: {len(new)} composed, {queued_n} queued (briefs: {', '.join(briefs)})"
    log(summary)
    pl.telem("refill_done", detail=summary)


if __name__ == "__main__":
    main()
