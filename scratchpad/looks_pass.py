#!/usr/bin/env python3
"""LOOKS brand pass: each (kit, look) tile through ONE img2img (den 0.5, stage depth as CN 0.7)
with a real card prompt + deck — does DreamShaper keep the material difference?
Waits for the GPU (no dive.py running, ComfyUI queue empty). -> output/stage_lab/looks_pass.png"""
import io, json, sys, time, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path('/mnt/c/Users/Phil/zoomer')
sys.path.insert(0, str(ROOT / 'engine')); sys.path.insert(0, str(ROOT / 'scripts'))
import dive, stage, style as _style, pipeline as pl  # noqa: E402

def gpu_free():
    try:
        q = json.loads(__import__('urllib.request').request.urlopen('http://localhost:8188/queue', timeout=5).read())
        busy = bool(q['queue_running'] or q['queue_pending'])
    except Exception:
        busy = True
    procs = subprocess.run(['pgrep', '-f', 'engine/dive.py'], capture_output=True, text=True).stdout.strip()
    return not busy and not procs

while not gpu_free():
    time.sleep(20)
print('[looks] gpu free', time.strftime('%H:%M:%S'), flush=True)
cfg = {**dive.DEFAULTS, **dive.MODEL_PRESETS['ds']}
spec = json.load(open(pl.journey_path('cork_dehesa'), encoding='utf-8'))
sfx, _, _ = _style.resolve(spec)
regs = {r['name']: r for r in spec['registers']}
cases = [('nucleus', {"kit": "nucleus"}, regs['shelled_nucleus']),
         ('lattice', {"kit": "lattice", "variant": "diamond", "spacing": 0.5, "radius": 0.06, "glow": 0.2}, regs['carbon_atom'])]
zooms = [1.0857] * 28
rows = []
for label, kitdef, reg in cases:
    prompt = f"moving through {reg['scene']}, {sfx}, {reg.get('palette')} colors"
    tiles = []
    for look in stage.LOOKS:
        st = stage.build_card_stage_v2(dict(kitdef), reg.get('palette'), zooms, (0.38, 0.6), 576, 1024, seed=5, look=look)
        rgb, dep = st.frame_images(14)
        ref = dive.upload_image(rgb, f'zoomer_lk_{label}_{look}.png'); ctl = dive.upload_image(dep, f'zoomer_lkd_{label}_{look}.png')
        wf = dive.build_workflow(cfg, prompt, 1234, init_image=ref, denoise=0.5, ctrl_image=ctl, cn_strength=0.7, depth_preproc=None)
        im = Image.open(io.BytesIO(dive.run_workflow(wf))).convert('RGB')
        tiles.append((f'{label} {look}', rgb, im)); print('[looks]', label, look, flush=True)
    rows.append(tiles)
tw, th = 150, 266
sheet = Image.new('RGB', (tw * 6, (th * 2 + 16) * 2), (15, 15, 15)); dr = ImageDraw.Draw(sheet)
for r_, tiles in enumerate(rows):
    for c_, (lab, a, b) in enumerate(tiles):
        y = r_ * (th * 2 + 16)
        a = a.copy(); a.thumbnail((tw, th)); b = b.copy(); b.thumbnail((tw, th))
        sheet.paste(a, (c_ * tw, y + 16)); sheet.paste(b, (c_ * tw, y + 16 + th)); dr.text((c_ * tw + 3, y + 2), lab, fill=(255, 255, 0))
(ROOT / 'output' / 'stage_lab').mkdir(exist_ok=True)
sheet.save(ROOT / 'output' / 'stage_lab' / 'looks_pass.png'); print('[looks] ->', ROOT / 'output' / 'stage_lab' / 'looks_pass.png', flush=True)
