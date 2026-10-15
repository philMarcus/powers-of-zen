"""MIDDLE-GROUND arms strip + numbers + a 6-wide looped clip (today | M0 | M1 | M2 | M3 | M4), sulfur lattice k7."""
import os, glob, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
Z = '/mnt/c/Users/Phil/zoomer'
FFMPEG = ("/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
          "ffmpeg-8.1.1-full_build/bin/ffmpeg.exe")
def wpath(p): return subprocess.run(['wslpath', '-w', p], capture_output=True, text=True).stdout.strip()
def latest(d):
    vs = sorted(glob.glob(f'{d}/v*'), key=lambda p: int(os.path.basename(p)[1:])); return vs[-1] + '/build' if vs else None
def detail(p):
    im = Image.open(p).convert('L').resize((288, 512)); a = np.asarray(im, np.float32); b = np.asarray(im.filter(ImageFilter.GaussianBlur(3)), np.float32); return float(np.abs(a - b).mean())
def stats(p):
    im = Image.open(p).convert('RGB').resize((144, 256)); a = np.asarray(im, np.float32) / 255; mx, mn = a.max(-1), a.min(-1)
    s = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean()); hsv = np.asarray(im.convert('HSV'), np.float32); h, sv = hsv[..., 0] * 360 / 255, hsv[..., 1]
    hist = np.histogram(h[sv > 60], bins=24, range=(0, 360))[0].astype(np.float32); hist = hist / max(hist.sum(), 1)
    return s, float(-(hist[hist > 0] * np.log2(hist[hist > 0])).sum())
arms = [('today (drawn scale)', latest(f'{Z}/output/valdes_blow_platelive_paint_l0b')),
        ('M0 today, bold scale', latest(f'{Z}/output/valdes_blow_platelive_paint_m0')),
        ('M1 orb 0.9 id 0.5, today repaint, fog bg', latest(f'{Z}/output/valdes_blow_platelive_paint_m1')),
        ('M2 = M1 + blurred dim field', latest(f'{Z}/output/valdes_blow_platelive_paint_m2')),
        ('M3 orb 0.5 id 0.40 repaint 0.40/0.45', latest(f'{Z}/output/valdes_blow_platelive_paint_m3')),
        ('M4 orb 0.9 id 0.5 repaint 0.30/0.32', latest(f'{Z}/output/valdes_blow_platelive_paint_m4'))]
a, z = 224, 255
ks = list(range(a, z + 1, 4))[:8]
W, H = 150, 266
rows = [(lbl, d + '/frames', None) for lbl, d in arms if d] + [(f'{lbl} STAGE LAYER', d + '/stage', '_stage') for lbl, d in arms[2:3] if d]
im = Image.new('RGB', (8 * W, len(rows) * (H + 16) + 190), (8, 8, 10)); dr = ImageDraw.Draw(im)
for r, (lbl, d, suf) in enumerate(rows):
    for c, k in enumerate(ks):
        p = f'{d}/{k:05d}{suf or ""}.png'
        if not os.path.exists(p) and suf:
            cands = sorted(glob.glob(f'{d}/*_stage.png'))
            if cands: p = min(cands, key=lambda q: abs(int(os.path.basename(q)[:5]) - k))
        if os.path.exists(p): im.paste(Image.open(p).convert('RGB').resize((W, H)), (c * W, r * (H + 16) + 16))
    dr.text((3, r * (H + 16) + 2), f'{lbl} f{ks[0]}..{ks[-1]}', fill=(235, 235, 235))
y = len(rows) * (H + 16) + 20; x = 0
d1 = arms[2][1]
if d1:
    for p in sorted(glob.glob(f'{d1}/stage/elem_7_*.png')): im.paste(Image.open(p).convert('RGB').resize((160, 160)), (x, y)); x += 165
d2 = arms[3][1]
if d2 and os.path.exists(f'{d2}/stage/field_7.png'): im.paste(Image.open(f'{d2}/stage/field_7.png').convert('RGB').resize((96, 160)), (x, y))
out = f'{Z}/scratchpad/orange/paint_mid_strip.png'; im.save(out); print('strip ->', out)
print('\narm: fine detail / saturation / hue entropy over the card')
for lbl, d in arms:
    if not d: continue
    ps = [f'{d}/frames/{k:05d}.png' for k in range(a, z + 1) if os.path.exists(f'{d}/frames/{k:05d}.png')]
    if ps:
        st = np.array([stats(p) for p in ps]); print(f'{lbl:42s} detail {np.mean([detail(p) for p in ps]):.1f} sat {st[:,0].mean():.2f} hue-ent {st[:,1].mean():.2f} (n={len(ps)})')
have = [(lbl, d) for lbl, d in arms if d and os.path.exists(f'{d}/frames/{a:05d}.png')]
if len(have) >= 2:
    outm = f'{Z}/review/compare/paint_MID_lattice.mp4'
    cmd = [FFMPEG, '-y', '-loglevel', 'error']
    for lbl, d in have: cmd += ['-framerate', '12', '-start_number', str(a), '-i', wpath(f'{d}/frames') + '\\%05d.png']
    fc = ''.join(f'[{i}:v]trim=end_frame={z - a + 1},setpts=PTS-STARTPTS,scale=288:512[v{i}];' for i in range(len(have)))
    fc += ''.join(f'[v{i}]' for i in range(len(have))) + f'hstack=inputs={len(have)},loop=loop=3:size={z - a + 1}:start=0[v]'
    cmd += ['-filter_complex', fc, '-map', '[v]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', wpath(outm)]
    r = subprocess.run(cmd, capture_output=True, text=True); print('clip ->', outm if r.returncode == 0 else f'FAILED {r.stderr[-300:]}', '| order:', ' | '.join(l.split(' ')[0] for l, _ in have))
