#!/usr/bin/env python3
"""replace_tail — regenerate ONLY an existing render's loop tail with IPA homing (ipacn),
schedule-faithful, and splice it into a fresh vN. The counterpart to replace_opening for
renders whose OPENING is fine but whose loop seam predates the IPA fold-in (or read badly).

Keeps frame 0 and every body frame byte-identical; regenerates the last L (loop) frames via
seam_tail_ab.regen_tail — the compiled schedule's own prompts/crossfades and dive.py's exact
denoise cadence, with IPA/depth-CN homing onto frame 0. Assembles with the counter and
(optionally) re-queues the review video. Non-destructive: fresh vN, tail also kept under
output/seam_lab/<name>_tail/.

For a video already IN PRODUCTION (phase-shifted + music), do NOT --queue-review (it would
reset the pipeline state to review): make a candidate with scripts/make_candidate.py instead.

Usage (repo root, ComfyUI up):
  python3 scripts/replace_tail.py sugar_nebula --queue-review     # review-stage video
  python3 scripts/replace_tail.py frost_window                    # then make_candidate.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "scripts"))
import dive  # noqa: E402
import pipeline as pl  # noqa: E402
import seam_lab  # noqa: E402
import seam_tail_ab  # noqa: E402
from engine import grammar  # noqa: E402
from engine import style as _style  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey")
    ap.add_argument("--model", help="turbo|ds (default: the deck's pick)")
    ap.add_argument("--src-version", help="source vN (default: newest complete)")
    ap.add_argument("--queue-review", action="store_true",
                    help="re-queue the review video from the new vN (review-stage only)")
    args = ap.parse_args()

    import requests
    try:
        requests.get(f"{dive.COMFY}/system_stats", timeout=5)
    except Exception:
        sys.exit(f"ComfyUI not up at {dive.COMFY}")

    spec = json.loads(pl.journey_path(args.journey).read_text(encoding="utf-8"))
    sfx, deck_model, sname = _style.resolve(spec)
    spec["style_suffix"] = sfx
    model = args.model or deck_model or "ds"
    cfg = {**dive.DEFAULTS, **spec.get("settings", {})}
    cfg.update(dive.MODEL_PRESETS[model])
    cfg["build"] = "in"
    compiled = grammar.compile_journey(spec, cfg["fps"], "in")
    zoom, exponent, loop = compiled[1], compiled[3], compiled[4]
    if not loop:
        sys.exit("journey has no exact_loop — no tail to replace")
    total, L = len(zoom), loop["frames"]
    seam_start = total - L

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
    print(f"[tail] {args.journey}: src={base.name}/{src.name} model={model} "
          f"regenerate {seam_start}..{total-1} (L={L})", flush=True)

    depth = seam_lab.pick_depth_preproc(seam_lab.object_info())
    lab_dir = ROOT / "output" / "seam_lab" / f"{base.name}_tail"
    seam_tail_ab.regen_tail("ipacn", cfg, srcfr, compiled, lab_dir, depth)

    n = 1 + max([int(d.name[1:]) for d in base.glob("v[0-9]*") if d.name[1:].isdigit()],
                default=0)
    out_dir = base / f"v{n}"
    fr = out_dir / "build" / "frames"
    fr.mkdir(parents=True, exist_ok=True)
    for i in range(seam_start):
        shutil.copy(srcfr / f"{i:05d}.png", fr / f"{i:05d}.png")
    for i in range(seam_start, total):
        shutil.copy(lab_dir / "ipacn" / f"{i:05d}.png", fr / f"{i:05d}.png")
    (out_dir / "run.json").write_text(json.dumps({
        "journey": args.journey, "model": model, "checkpoint": cfg["checkpoint"],
        "style": sname, "frames": total, "seed": cfg["seed"],
        "splice": {"body_src": src.name, "tail_src": f"output/seam_lab/{base.name}_tail/ipacn",
                   "tail_frames": [seam_start, total - 1],
                   "mechanism": "ipacn schedule-faithful"}}, indent=2))

    counter_flag = spec.get("format", {}).get("counter", cfg["counter"])
    show = bool(counter_flag) if counter_flag != "auto" else all(
        a > b for a, b in zip([r["exp"] for r in spec["registers"]],
                              [r["exp"] for r in spec["registers"]][1:]))
    dive.assemble(cfg, args.journey, out_dir, fr, total,
                  exponent=exponent if show else None)
    print(f"[tail] assembled {out_dir}", flush=True)

    if args.queue_review:
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "queue_review.py"),
                        args.journey, model, "--src", str(out_dir)], check=True)


if __name__ == "__main__":
    main()
