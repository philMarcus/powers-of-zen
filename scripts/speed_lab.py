#!/usr/bin/env python3
"""SPEED LAB (2026-09-23) — render the SAME 36 frames under different ComfyUI loader settings,
time them, and prove the pixels did not change. Zero-quality-change candidates only: every arm
uses the same checkpoint, steps, cfg, seed, tracker and plate; only how ComfyUI stages weights
differs. A second baseline arm gives the nondeterminism floor for the pixel comparison.

  python3 scripts/speed_lab.py            # waits for the nightly batch lock, then runs all arms
  python3 scripts/speed_lab.py --arms A_base,B_nodyn

Bed: mantis_drumline v1 (seed 673194, no planet), card 3 = frames 72..107: tracker active
(approach frames outside resolve windows), a cameo window at 102+. ComfyUI is RESTARTED per arm
(by PID, never by pattern) and restored to the baseline flags at the end, whatever happens.
Output: output/speed_lab/<arm>/ (frames + dive log) and output/speed_lab/report.txt."""
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import night_batch as nb  # noqa: E402  (comfy_up-style launch + boost_comfy)

COMFY_DIR = "/mnt/c/Users/Phil/ComfyUI"
COMFY_LOG = Path(COMFY_DIR) / "ComfyUI" / "user" / "comfyui.log"
BASE_FLAGS = ["--windows-standalone-build", "--listen", "0.0.0.0"]
PS = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
LAB = ROOT / "output" / "speed_lab"
JOURNEY = "mantis_drumline"
SRC, SEED, CARD, END = "v1", 673194, 3, 108          # card 3 starts at frame 72
FIRST = 72
DIVE = ["python3", "engine/dive.py", f"journeys/{JOURNEY}.json", "--from-card", str(CARD),
        "--src-version", SRC, "--frames", str(END), "--no-loop", "--no-video", "--seed", str(SEED),
        "--plate", "live", "--plate-cn", "0", "--plate-void-gate", "--plate-intro", "mix"]

ARMS = {
    # name: (extra ComfyUI flags, extra dive flags)
    "A_base":  ([], []),
    "A_again": ([], []),                                  # nondeterminism floor
    "B_nodyn": (["--disable-dynamic-vram"], []),          # legacy estimate-based loader
    "C_res02": (["--reserve-vram", "0.2"], []),           # 0.6 GB -> 0.2 GB reserve
    "P_plain": ([], ["--plain"]),   # NO tracker: an upper bound on what detection costs
}                                   # (P_plain changes the aim -> pixels differ by design)


def log(msg):
    print(f"=== {datetime.now():%H:%M:%S} {msg}", flush=True)


def comfy_pid():
    r = subprocess.run([PS, "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                        "Where-Object { $_.CommandLine -like '*ComfyUI/main.py*' } | "
                        "Select-Object -First 1).ProcessId"], capture_output=True, text=True, timeout=60)
    s = r.stdout.strip()
    return int(s) if s.isdigit() else None


def restart_comfy(flags):
    pid = comfy_pid()
    if pid:
        subprocess.run([PS, "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"],
                       capture_output=True, text=True, timeout=60)
        for _ in range(30):
            if comfy_pid() != pid:
                break
            time.sleep(1)
    cmd = " ".join(["./python_embeded/python.exe", "-s", "ComfyUI/main.py"] + BASE_FLAGS + flags)
    subprocess.run(["bash", "-lc",
                    "tmux kill-session -t comfy 2>/dev/null; "
                    f"tmux new-session -d -s comfy -c {COMFY_DIR} && "
                    f"tmux send-keys -t comfy '{cmd}' Enter"], check=True)
    import requests
    for _ in range(60):
        try:
            requests.get(f"{nb.COMFY}/system_stats", timeout=3)
            time.sleep(3)
            nb.boost_comfy()
            return True
        except Exception:
            time.sleep(3)
    raise SystemExit("ComfyUI did not come up")


def wait_for_batch():
    """Never restart ComfyUI under the nightly batch: wait for its lock AND for no dive."""
    while True:
        busy = False
        try:
            fh = open(nb.LOCK, "w")
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
            fh.close()
        except OSError:
            busy = True
        if subprocess.run(["pgrep", "-f", "engine/dive.py"], capture_output=True).returncode == 0:
            busy = True
        if not busy:
            return
        log("batch/dive still running — waiting")
        time.sleep(60)


def comfy_log_count(t0, t1, needle):
    n = 0
    for l in COMFY_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\[(\S+ \S+)\] (.*)", l)
        if not m:
            continue
        t = datetime.fromisoformat(m.group(1))
        if t0 <= t <= t1 and needle in m.group(2):
            n += 1
    return n


def run_arm(name, cflags, dflags):
    out = LAB / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    restart_comfy(cflags)
    t0 = datetime.now()
    log(f"{name}: ComfyUI flags {cflags or '(baseline)'}  dive extra {dflags or '-'}")
    with open(out / "dive.log", "w") as fh:
        r = subprocess.run(DIVE + dflags, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT, timeout=3600)
    t1 = datetime.now()
    txt = (out / "dive.log").read_text(errors="replace")
    m = re.search(r"\[dive\] run dir: (\S+)", txt)
    if r.returncode != 0 or not m:
        raise SystemExit(f"{name}: dive failed (rc {r.returncode}) — see {out / 'dive.log'}")
    run = Path(m.group(1))
    frames = sorted((run / "build" / "frames").glob("*.png"))
    fr = [f for f in frames if FIRST <= int(f.stem) < END]
    mt = [f.stat().st_mtime for f in fr]
    deltas = [b - a for a, b in zip(mt, mt[1:])]
    for f in fr:
        shutil.copy2(f, out / f.name)
    shutil.rmtree(run)                              # throwaway vN — never leave it for queue_review
    res = {"arm": name, "comfy_flags": cflags, "dive_flags": dflags, "frames": len(fr),
           "wall_s": round(mt[-1] - mt[0], 1), "median_s_per_frame": round(float(np.median(deltas)), 2),
           "mean_s_per_frame": round(float(np.mean(deltas)), 2),
           "florence_loads": comfy_log_count(t0, t1, "Requested to load Florence2"),
           "sdxl_loads": comfy_log_count(t0, t1, "Requested to load SDXL"),
           "prompts": comfy_log_count(t0, t1, "Prompt executed")}
    (out / "result.json").write_text(json.dumps(res, indent=1))
    log(f"{name}: {res['frames']} frames, median {res['median_s_per_frame']} s/frame, "
        f"wall {res['wall_s']} s, SDXL loads {res['sdxl_loads']}, Florence loads {res['florence_loads']}")
    return res


def compare(a, b):
    """Pixel identity of arm b vs arm a over the shared frames: byte-equal count, mean abs
    diff (0-255), worst-frame PSNR."""
    eq, mad, psnr = 0, [], []
    for fa in sorted((LAB / a).glob("*.png")):
        fb = LAB / b / fa.name
        if not fb.exists():
            continue
        x = np.asarray(Image.open(fa).convert("RGB"), np.float32)
        y = np.asarray(Image.open(fb).convert("RGB"), np.float32)
        d = np.abs(x - y)
        if fa.read_bytes() == fb.read_bytes():
            eq += 1
        mad.append(float(d.mean()))
        mse = float((d ** 2).mean())
        psnr.append(99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse))
    return eq, len(mad), round(float(np.mean(mad)), 3), round(float(min(psnr)), 1)


def main():
    arms = sys.argv[sys.argv.index("--arms") + 1].split(",") if "--arms" in sys.argv else list(ARMS)
    LAB.mkdir(parents=True, exist_ok=True)
    wait_for_batch()
    results = []
    try:
        for name in arms:
            cflags, dflags = ARMS[name]
            results.append(run_arm(name, cflags, dflags))
    finally:
        log("restoring baseline ComfyUI")
        restart_comfy([])
    lines = [f"SPEED LAB {datetime.now():%Y-%m-%d %H:%M}  bed {JOURNEY} {SRC} card {CARD} "
             f"frames {FIRST}..{END - 1} seed {SEED}", ""]
    for r in results:
        lines.append(f"{r['arm']:9s} median {r['median_s_per_frame']:5.2f} s/frame  mean {r['mean_s_per_frame']:5.2f}  "
                     f"wall {r['wall_s']:6.1f} s  prompts {r['prompts']:3d}  SDXL loads {r['sdxl_loads']:2d}  "
                     f"Florence loads {r['florence_loads']:2d}  flags {r['comfy_flags'] or '-'} {r['dive_flags'] or ''}")
    if "A_base" in arms:
        lines.append("")
        lines.append("pixels vs A_base (byte-equal / n, mean abs diff 0-255, worst PSNR dB):")
        for r in results:
            if r["arm"] != "A_base":
                eq, n, mad, ps = compare("A_base", r["arm"])
                lines.append(f"  {r['arm']:9s} {eq:2d}/{n}  mad {mad:6.3f}  psnr {ps}")
    rep = "\n".join(lines)
    (LAB / "report.txt").write_text(rep)
    print("\n" + rep)


if __name__ == "__main__":
    main()
