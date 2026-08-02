#!/usr/bin/env python3
"""replace_opening — regenerate a render's BAD OPENING without losing a frame OR a scene.

The problem (Phil, 2026-08-02): some otherwise-great renders open on a close-up frame 0 the
loop can't gracefully come home to. Cutting the card would drop 28 frames and shift the music
grid; a full re-render costs an hour. And the card-0 SCENE itself is wanted content — it only
failed as a COLD txt2img opening; rendered mid-dive it's fine (Phil: "we can assume the journey
card contains something we want in the video"). So this keeps every frame slot AND every scene:

    old render order:   [card0: BAD txt2img start][card1 .. cardN-1][tail -> homes to frame 0]
    new render order:   [--- card0's world, arrived at mid-dive ---][card1 .. cardN-1 (KEPT)]

The old tail slots, the old card-0 slots AND card 1's arrival phase are regenerated as ONE
continuous arc (L + C0 + fa frames, typically 24+28+7=59) rendering the ORIGINAL compiled
schedule for those slots: the tail runs its own loop-home prompts (which already plunge INTO
card 0's world); slot 0 gets a seam-class on-beat morph into card 0's world (it IS a bar
line, with the standard anacrusis); card 0's slots run card 0's own travel/plunge at FULL
zoom energy — no homing drag before the boundary (v1 converged early: the flip landed off
the beat and the plunge visibly decelerated); card 1's arrival is regenerated so the on-beat
flip runs FROM the new card-0 world (the kept arrival used to morph out of the OLD bad
feedback — an abrupt pivot "from nowhere"); IPA ramps only inside that arrival window, with
depth-CN + a small blend on the last frames landing on kept frame C0+fa — fully-card-1
footage past the morph. Counter: the original exponent schedule is already correct
everywhere. Non-destructive: fresh vN.

Usage (repo root, ComfyUI up):
  python3 scripts/replace_opening.py pollen_court --dry-run
  python3 scripts/replace_opening.py pollen_court [--src-version v1] [--queue-review]
"""
import argparse
import io
import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import dive  # noqa: E402
import pipeline as pl  # noqa: E402
import seam_lab  # noqa: E402
from engine import grammar  # noqa: E402
from engine import style as _style  # noqa: E402

SEED_STRIDE = 31337   # regenerated slots draw NEW noise (the old seeds made the bad frames)


def load(fr, i):
    return Image.open(fr / f"{i:05d}.png").convert("RGB")


def rotated_regs(spec):
    regs = spec["registers"]
    rs = spec.get("render_start")
    names = [r.get("name") for r in regs]
    if rs in names:
        k = names.index(rs)
        regs = regs[k:] + regs[:k]
    return regs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--model", help="turbo|ds (default: the deck's pick)")
    ap.add_argument("--src-version", help="source vN (default: newest complete)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--queue-review", action="store_true",
                    help="after assembly, re-queue the journey's review video from the new vN")
    args = ap.parse_args()

    spec = json.loads(pl.journey_path(args.journey).read_text(encoding="utf-8"))
    sfx, deck_model, sname = _style.resolve(spec)
    spec["style_suffix"] = sfx
    model = args.model or deck_model or "ds"
    cfg = {**dive.DEFAULTS, **spec.get("settings", {})}
    cfg.update(dive.MODEL_PRESETS[model])
    cfg["build"] = "in"
    out = grammar.compile_journey(spec, cfg["fps"], "in")
    (phases, zoom, den_sched, exponent, loop,
     _cameos, arrivals, _approach, _seam_arr) = out
    if not loop:
        sys.exit("journey has no exact_loop — nothing to re-home")
    total, L = len(zoom), loop["frames"]
    cf = dive.register_frame_counts(spec, cfg["fps"])
    C0 = cf[0]
    regs = rotated_regs(spec)
    if len(regs) < 3:
        sys.exit("need at least 3 cards to regenerate the opening")
    # card 1's ARRIVAL phase (starts exactly at C0) is regenerated too (v2, Phil 2026-08-02):
    # the kept arrival morphed out of the OLD bad card-0 feedback — keeping it made the video
    # pivot to a trajectory "from nowhere" right after a clean hand-off (the abrupt shift into
    # card one). Regenerating it lets the on-beat flip run FROM the new card-0 world; we land
    # PAST the morph, on fully-card-1 footage.
    acc = 0
    fa = 0
    for ph in phases:
        if acc == C0:
            fa = ph["frames"]
            break
        acc += ph["frames"]
    if not fa:
        sys.exit(f"no phase boundary at frame {C0} — schedule mismatch")
    arc = L + C0 + fa                 # slots: [total-L .. total-1] + [0 .. C0+fa-1]
    resume_at = total - L - 1         # last KEPT frame — the chain resumes from its image

    # a cameo whose window touches the regenerated slots would be silently lost
    for r in (regs[0], regs[-1]):
        if r.get("cameo"):
            sys.exit(f"cameo on card {r['name']!r} sits in the regenerated slots — "
                     f"move it to a mid-journey card first (edit the journey), then re-run")

    base = ROOT / "output" / f"{args.journey}_{model}"
    if not base.exists():
        base = ROOT / "output" / args.journey
    if args.src_version:
        src = base / args.src_version
    else:
        src = None
        for d in sorted(base.glob("v[0-9]*"), key=lambda p: int(p.name[1:])):
            if (d / "build" / "frames" / f"{total-1:05d}.png").exists():
                src = d                # newest complete
    if not src or not (src / "build" / "frames" / f"{total-1:05d}.png").exists():
        sys.exit(f"no complete source frames under {base} (need {total})")
    srcfr = src / "build" / "frames"

    print(f"[open] {args.journey}: src={base.name}/{src.name} total={total} — regenerate "
          f"{arc} slots [{total-L}..{total-1}]+[0..{C0+fa-1}]: dive back INTO card0 "
          f"{regs[0]['name']!r} (scene kept, no txt2img, full plunge), on-beat arrival into "
          f"card {regs[1]['name']!r} ({fa}f, regenerated), land on kept frame {C0+fa}",
          flush=True)
    print(f"[open] tail slots:  {dive.phase_info(phases, total - L)[0][:70]}…", flush=True)
    print(f"[open] card0 slots: {dive.phase_info(phases, 0)[0][:70]}…", flush=True)
    print(f"[open] arrival:     {dive.phase_info(phases, C0)[0][:70]}…", flush=True)
    if args.dry_run:
        return

    import requests
    try:
        requests.get(f"{dive.COMFY}/system_stats", timeout=5)
    except Exception:
        sys.exit(f"ComfyUI not up at {dive.COMFY}")

    n = 1 + max([int(d.name[1:]) for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                default=0)
    out_dir = base / f"v{n}"
    fr = out_dir / "build" / "frames"
    fr.mkdir(parents=True, exist_ok=True)
    for i in range(C0 + fa, total - L):                # the KEPT body, byte-identical
        shutil.copy(srcfr / f"{i:05d}.png", fr / f"{i:05d}.png")

    home = load(srcfr, C0 + fa)                        # first kept frame: card 1, PAST the morph
    home_ref = dive.upload_image(home, f"open_home_{args.journey}.png")
    home_pal = dive.channel_stats(home)
    depth = seam_lab.pick_depth_preproc(seam_lab.object_info())
    W, H = cfg["width"], cfg["height"]
    T = cfg["transition_frames"]
    boost = cfg["arrival_denoise_boost"]

    prev = load(srcfr, resume_at)
    for a in range(arc):
        i = (total - L + a) % total                    # slots: tail, then 0 .. C0+fa-1
        # ORIGINAL schedule for this slot — card 0's scene is passed through, never skipped,
        # and its plunge keeps FULL zoom energy (no homing drag before the bar line: v1 of
        # this tool converged early, which pre-empted the flip OFF the beat and visibly
        # decelerated the dive — Phil heard both). Slot 0's phase has no previous in the flat
        # list; in the circular arc its previous is the tail's last phase.
        prompt, prev_p, k, p_idx = dive.phase_info(phases, i)
        if p_idx == 0 and prev_p is None and k < T:
            prev_p = phases[-1]["prompt"]
        in_trans = prev_p is not None and k < T
        # denoise: the engine's own morph choreography. Scheduled base + arrival boost on the
        # crossfade (card 1's arrival phase is in `arrivals`), a seam-class held boost for the
        # flip into card 0 at slot 0 (a bar line the schedule never flipped — it was txt2img),
        # and the standard 2-frame anacrusis INTO both boundaries.
        den = den_sched[i] if den_sched else cfg["denoise"]
        if in_trans:
            den = min(0.85, den + (boost if p_idx in arrivals
                                   else cfg["transition_denoise_boost"]))
        if 0 <= i < cfg["seam_morph_frames"]:
            den = min(0.85, max(den, (den_sched[i] if den_sched else cfg["denoise"]) + boost))
        base = den_sched[i] if den_sched else cfg["denoise"]
        if i in (total - 1, C0 - 1):                   # anacrusis: pickup into the downbeat
            den = min(0.85, max(den, base + boost * 0.7))
        elif i in (total - 2, C0 - 2):
            den = min(0.85, max(den, base + boost * 0.4))
        drift = cfg["drift"] * (1 - (a + 1) / arc)
        cx = 0.5 + drift * math.sin(2 * math.pi * i / 263)
        cy = 0.5 + drift * math.sin(2 * math.pi * i / 419 + 1.7)
        fed = dive.zoom_transform(prev, zoom[i], cfg["rotate_per_frame"], cx, cy)
        fed = dive.detail_boost(fed, cfg)
        # HOMING — confined to card 1's regenerated ARRIVAL window: the flip runs ON the beat
        # from the new card-0 world, IPA pulls it toward the true landing footage, depth-CN
        # and a small blend only align the last frames onto kept frame C0+fa.
        ipa_w, ctl, cn_s = 0.0, None, 0.0
        if 0 <= i - C0 < fa:
            m = (i - C0 + 1) / fa
            ipa_w = 0.9 * m ** 1.5
            if i >= C0 + fa - 4:
                cn_s = 0.25 + 0.45 * (i - (C0 + fa - 4) + 1) / 4
                ctl = home_ref
            if i >= C0 + fa - 2:
                fed = Image.blend(fed, home, 0.15 if i == C0 + fa - 2 else 0.30)
        wf = seam_lab.seam_workflow(cfg, dive.upload_image(fed, f"open_init_{i:05d}.png"),
                                    prompt, cfg["seed"] + i + SEED_STRIDE, den,
                                    prev_prompt=prev_p if in_trans else None,
                                    blend=(k + 1) / (T + 1) if in_trans else 1.0,
                                    ctrl_name=ctl, cn_strength=cn_s, depth_preproc=depth)
        if ipa_w > 0.01:
            seam_lab.add_ipadapter(wf, home_ref, ipa_w)
        img = Image.open(io.BytesIO(dive.run_workflow(wf))).convert("RGB")
        if img.size != (W, H):
            img = img.resize((W, H), Image.LANCZOS)
        if 0 <= i - C0 < fa:
            img = dive.color_match(img, home_pal, 0.8 * (i - C0 + 1) / fa)
        img.save(fr / f"{i:05d}.png")
        prev = img
        print(f"[open] arc {a+1}/{arc} (slot {i}) den={den:.2f} ipa={ipa_w:.2f} "
              f"cn={cn_s:.2f} :: {prompt[:46]}", flush=True)

    (out_dir / "run.json").write_text(json.dumps({
        "journey": args.journey, "model": model, "checkpoint": cfg["checkpoint"],
        "style": sname, "frames": total, "seed": cfg["seed"],
        "replace_opening": {"src": src.name, "card0": regs[0]["name"],
                            "arc_slots": [total - L, C0 + fa - 1], "home_frame": C0 + fa,
                            "mechanism": "schedule-prompts + on-beat arrival + ipacn landing",
                            "seed_stride": SEED_STRIDE}}, indent=2))

    counter_flag = spec.get("format", {}).get("counter", cfg["counter"])
    show = bool(counter_flag) if counter_flag != "auto" else all(
        a > b for a, b in zip([r["exp"] for r in spec["registers"]],
                              [r["exp"] for r in spec["registers"]][1:]))
    # the ORIGINAL exponent schedule is already correct for every slot: the tail spins toward
    # card 0's register (we still dive into card 0's world) and card 0's slots descend it
    dive.assemble(cfg, args.journey, out_dir, fr, total,
                  exponent=exponent if show else None)
    print(f"[open] assembled {out_dir}", flush=True)

    if args.queue_review:
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "queue_review.py"),
                        args.journey, model, "--src", str(out_dir)], check=True)


if __name__ == "__main__":
    main()
