#!/usr/bin/env python3
"""STAGE LAB step 2 measurement: for a stage arm, per frame of the card — (a) structure
persistence = correlation between the RENDERED frame's edge map and the STAGE render's edge
map (saved every 4th frame in build/stage/), (b) hue census (orange/cool), (c) a strip:
baseline v1 / stage render / fed composite / rendered.  usage: stage_measure.py <journey> <arm_dir> <S> <E> <out.png>"""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, '/mnt/c/Users/Phil/zoomer/scratchpad/orange'); from hue_curve import census
ROOT = Path('/mnt/c/Users/Phil/zoomer')
j, arm, S, E, out = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5])
base_v = sys.argv[6] if len(sys.argv) > 6 else 'v1'
base = ROOT / 'output' / j / base_v / 'build' / 'frames'
fr = arm / 'build' / 'frames'; sd = arm / 'build' / 'stage'

def edges(p):
    im = Image.open(p).convert('L').resize((144, 256)).filter(ImageFilter.FIND_EDGES)
    a = np.asarray(im, np.float32); a = (a - a.mean()) / (a.std() + 1e-6); return a

rows = []
for i in range(S, min(E, S + len(list(fr.glob('*.png'))))):
    f = fr / f'{i:05d}.png'
    if not f.exists(): break
    o, c, sm, *_ = census(f)
    st = sd / f'{i:05d}_stage.png'
    corr = float((edges(f) * edges(st)).mean()) if st.exists() else float('nan')
    bo = census(base / f'{i:05d}.png')[0] if (base / f'{i:05d}.png').exists() else float('nan')
    rows.append((i, corr, o, c, bo))
print(f"{'frame':>5} {'edge-corr vs stage':>18} {'orange':>7} {'cool':>5} | base orange")
for r in rows:
    if not np.isnan(r[1]) or r[0] in (S, E - 1):
        print(f"{r[0]:5d} {r[1]:18.3f} {r[2]:7.2f} {r[3]:5.2f} | {r[4]:.2f}")
picks = [S, S + 4, S + 8, S + 12, S + 16, S + 20, S + 24, min(E - 1, S + 27), E + 3, E + 11]
picks = [p for p in picks if (fr / f'{p:05d}.png').exists()]
tw, th = 120, 214
sheet = Image.new('RGB', (tw * len(picks) + 80, th * 4 + 14), (15, 15, 15)); dr = ImageDraw.Draw(sheet)
for r_, (lab, src) in enumerate((('baseline', lambda i: base / f'{i:05d}.png'), ('stage', lambda i: sd / f'{i:05d}_stage.png'),
                                 ('fed', lambda i: sd / f'{i:05d}_fed.png'), ('rendered', lambda i: fr / f'{i:05d}.png'))):
    dr.text((4, 14 + r_ * th + 6), lab, fill=(255, 255, 255))
    for c_, i in enumerate(picks):
        p = src(i)
        if p.exists():
            im = Image.open(p).convert('RGB'); im.thumbnail((tw, th)); sheet.paste(im, (80 + c_ * tw, 14 + r_ * th))
        if r_ == 0: dr.text((80 + c_ * tw + 3, 2), f'f{i}', fill=(255, 255, 0))
sheet.save(out); print('->', out)
