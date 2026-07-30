#!/usr/bin/env python3
"""POC #2: does aiming the zoom at the DETECTED object (instead of center) make it GROW instead of
fly by — and does a light depth-ControlNet keep it ALIVE (regenerated every frame) instead of
static? Standalone; does not touch the engine. Detect each frame, aim cx,cy at the target box,
zoom toward it, img2img with a depth CN from the (zoomed) previous frame.

Outputs: a filmstrip montage (judge grows+alive at a glance) and an mp4 clip.

Usage: python3 scripts/zoom_probe.py [start_frame] [query] [N] [cn] [denoise] [zoom_per]
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "engine")
sys.path.insert(0, "scripts")
import dive           # noqa: E402
import seam_lab       # noqa: E402
import detect         # noqa: E402
from PIL import Image  # noqa: E402

OUT = Path("/tmp/claude-0/-mnt-c-Users-Phil-zoomer/bcbde943-89be-485d-a581-0eb08e40ff22/scratchpad/zoomclip")
OUT.mkdir(parents=True, exist_ok=True)

START = sys.argv[1] if len(sys.argv) > 1 else "output/stormglass_ds/v1/build/frames/00233.png"
QUERY = sys.argv[2] if len(sys.argv) > 2 else "the gas planet"
N = int(sys.argv[3]) if len(sys.argv) > 3 else 24
CN = float(sys.argv[4]) if len(sys.argv) > 4 else 0.45
DEN = float(sys.argv[5]) if len(sys.argv) > 5 else 0.42
ZOOM = float(sys.argv[6]) if len(sys.argv) > 6 else 1.07

STYLE = "hyperdetailed, cinematic volumetric light, dramatic stormlight, moody, otherworldly"
# the target's OWN surface/interior — what we paint as it fills the view
PROMPT = ("a colossal banded gas giant planet filling the view, swirling stormy cloud bands and a "
          "great glowing storm eye churning across its curved face, " + STYLE)

cfg = {**dive.DEFAULTS}
cfg.update(dive.MODEL_PRESETS["ds"])
cfg["build"] = "in"
depth = seam_lab.pick_depth_preproc(seam_lab.object_info())
print(f"start={START} query='{QUERY}' N={N} CN={CN} denoise={DEN} zoom/frame={ZOOM} depth={depth}")


def clamp(v, lo=0.12, hi=0.88):
    return max(lo, min(hi, v))


prev = Image.open(START).convert("RGB")
frames = [prev.copy()]
b = detect.detect(prev, QUERY, pick="largest")
cx, cy = (b["cx"], b["cy"]) if b else (0.5, 0.5)
print(f"  frame  0: target=({cx:.2f},{cy:.2f})" + ("" if b else " [none -> center]"))
for i in range(1, N + 1):
    fed = dive.zoom_transform(prev, ZOOM, 0.0, clamp(cx), clamp(cy))
    fed = dive.detail_boost(fed, cfg)
    nm = dive.upload_image(fed, f"zp_{i:03d}.png")
    wf = seam_lab.seam_workflow(cfg, nm, PROMPT, cfg["seed"] + i, DEN, None, 1.0,
                                ctrl_name=nm, cn_strength=CN, depth_preproc=depth)
    out = seam_lab.gen(wf)
    if out.size != prev.size:
        out = out.resize(prev.size, Image.LANCZOS)
    prev = out
    frames.append(out)
    # re-detect on the fresh frame; the object should now sit nearer center — aim there (smoothed).
    b = detect.detect(prev, QUERY, pick="largest")
    if b:
        cx = 0.6 * b["cx"] + 0.4 * cx
        cy = 0.6 * b["cy"] + 0.4 * cy
        note = f"target=({b['cx']:.2f},{b['cy']:.2f}) area={b['area']:.2f}"
    else:
        cx += (0.5 - cx) * 0.5; cy += (0.5 - cy) * 0.5   # lost it -> assume it centered, ease in
        note = "no detect -> ease to center"
    print(f"  frame {i:2d}: {note}  aim=({cx:.2f},{cy:.2f})", flush=True)

for i, f in enumerate(frames):
    f.save(OUT / f"f{i:03d}.png")

# filmstrip montage: every ~Nth frame in a row-grid, downscaled
pick = list(range(0, len(frames), max(1, len(frames) // 9)))[:9]
tw, th = 216, 384
cols = 3
rows = (len(pick) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), "black")
for k, idx in enumerate(pick):
    t = frames[idx].resize((tw, th), Image.LANCZOS)
    sheet.paste(t, ((k % cols) * tw, (k // cols) * th))
sheet.save(OUT / "montage.png")
print(f"montage -> {OUT/'montage.png'} (frames {pick})")

# mp4 clip
subprocess.run([dive.FFMPEG, "-y", "-loglevel", "error", "-framerate", "12",
                "-i", "f%03d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "clip.mp4"],
               cwd=OUT, check=True)
print(f"clip -> {OUT/'clip.mp4'}")
