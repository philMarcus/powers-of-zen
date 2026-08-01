#!/usr/bin/env python3
"""Phase-shift finished loop videos so playback opens on an intentional frame.

Because every video is a perfect loop, we can cut at any point and splice
end-to-start: the video then OPENS mid-register on a stable macro-realm world,
and the loop blend plays mid-video as an ordinary transition.

Start-register criteria (Phil, 2026-07-26): macro realm (~human-to-city band),
mid-travel beat (not near an arrival blend), away from loop point and wrap.
Applied to review/ (zoom-out) and review_divein/ (dive-in) copies; masters in
output/ stay untouched.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grammar  # noqa: E402
import pipeline as pl  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FFMPEG = ("/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/"
          "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
          "ffmpeg-8.1.1-full_build/bin/ffmpeg.exe")
FPS = 12

START_REGISTER = {
    "cosmic_scales": "city",
    "tide_of_life": "open_blue",
    "mineral_heart": "mineral_veins",
    "night_bloom": "village",
    "cartographer": "star",
    "dollhouse": "street",
    "food_chain": "weed_forest",
    "iris_observatory": "eyepiece",
    "black_hole": "harbor_city",
    "antenna_ball": "meadow",
    "snowfall": "village",
    "skyfog": "harbor_fog",
    "midnight_kitchen": "kitchen",
    "alexandria": "delta",
}


def cut_time(journey, cut):
    """Seconds into the given cut where the chosen register is mid-travel."""
    spec = json.loads(pl.journey_path(journey).read_text(encoding="utf-8"))
    regs = spec["registers"]
    target = START_REGISTER[journey]
    idx = 0
    raw = None
    for k, reg in enumerate(regs):
        F = max(12, round(reg.get("sec", spec.get("format", {})
                          .get("sec_per_scale", 2.4)) * FPS))
        if reg["name"] == target:
            fa = round(F * 0.25) if k > 0 else 0
            raw = idx + fa + round((F - fa) * 0.4)   # mid-travel beat
        idx += F
    total = idx
    if raw is None:
        return None
    return (raw / FPS) if cut == "divein" else ((total - raw) / FPS)


def shift(path, t):
    # windows ffmpeg.exe can't open /mnt/c/... paths: use cwd + relative names
    tmp = path.with_suffix(".shifted.mp4")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", path.name, "-filter_complex",
         f"[0:v]trim=start={t:.3f},setpts=PTS-STARTPTS[a];"
         f"[0:v]trim=duration={t:.3f},setpts=PTS-STARTPTS[b];"
         "[a][b]concat=n=2:v=1[v]",
         "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         tmp.name], check=True, cwd=path.parent)
    for attempt in range(6):   # NTFS handles linger; players lock files
        try:
            tmp.replace(path)
            return True
        except PermissionError:
            time.sleep(5)
    print(f"  !! could not replace {path.name} (file locked?) — left as {tmp.name}")
    return False


def main(only=None):
    for f in sorted((ROOT / "review").glob("*.mp4")):
        base = f.stem.removesuffix("_ds")
        if base not in START_REGISTER or (only and base not in only):
            continue
        t = cut_time(base, "zoomout")
        shift(f, t)
        print(f"review/{f.name}: opens at {START_REGISTER[base]} (t={t:.1f}s)")
        dv = ROOT / "review_divein" / f"{f.stem}_divein.mp4"
        if dv.exists():
            shift(dv, cut_time(base, "divein"))
            print(f"review_divein/{dv.name}: opens at {START_REGISTER[base]}")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
