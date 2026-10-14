"""PLATE-STYLE A/B strip + numbers + looped side-by-side clips (2026-10-14). Per card: today's stage (l0/n0) /
paint (l1/n1) rendered frames, the paint arm's stage layer, and its element pictures + field."""
import os, glob, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
Z = '/mnt/c/Users/Phil/zoomer'
FFMPEG = ("/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
          "ffmpeg-8.1.1-full_build/bin/ffmpeg.exe")


def latest(d):
    vs = sorted(glob.glob(f'{d}/v*'), key=lambda p: int(os.path.basename(p)[1:]))
    return vs[-1] + '/build' if vs else None


def detail(p):
    im = Image.open(p).convert('L').resize((288, 512)); a = np.asarray(im, np.float32); b = np.asarray(im.filter(ImageFilter.GaussianBlur(3)), np.float32)
    return float(np.abs(a - b).mean())


def sat(p):
    a = np.asarray(Image.open(p).convert('RGB').resize((144, 256)), np.float32) / 255; mx, mn = a.max(-1), a.min(-1)
    return float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean())


cards = [('LATTICE valdes_blow k7 sulfur_atom', 7, 224, 255, latest(f'{Z}/output/valdes_blow_platelive_paint_l0'), latest(f'{Z}/output/valdes_blow_platelive_paint_l1')),
         ('NUCLEUS lepidolite_halo_var k8 halo_nucleus', 8, 256, 287, latest(f'{Z}/output/lepidolite_halo_var_platelive_paint_n0'), latest(f'{Z}/output/lepidolite_halo_var_platelive_paint_n1'))]
W, H = 150, 266
rows = []
for lbl, k, a, z, d0, d1 in cards:
    ks = list(range(a, z + 1, 4))[:8]
    if d0: rows.append((f"today's stage · {lbl}", d0 + '/frames', ks, None))
    if d1:
        rows.append((f'PAINT · {lbl}', d1 + '/frames', ks, None))
        rows.append((f'PAINT stage layer · {lbl}', d1 + '/stage', ks, '_stage'))
im = Image.new('RGB', (8 * W, len(rows) * (H + 16) + 300), (8, 8, 10)); dr = ImageDraw.Draw(im)
for r, (lbl, d, ks, suf) in enumerate(rows):
    for c, kk in enumerate(ks):
        p = f'{d}/{kk:05d}{suf or ""}.png'
        if not os.path.exists(p) and suf:
            cands = sorted(glob.glob(f'{d}/*_stage.png'))
            if cands: p = min(cands, key=lambda q: abs(int(os.path.basename(q)[:5]) - kk))
        if os.path.exists(p): im.paste(Image.open(p).convert('RGB').resize((W, H)), (c * W, r * (H + 16) + 16))
    dr.text((3, r * (H + 16) + 2), f'{lbl} f{ks[0]}..{ks[-1]}', fill=(235, 235, 235))
# element pictures + fields along the bottom
x = 0; y = len(rows) * (H + 16) + 16
for lbl, k, a, z, d0, d1 in cards:
    if not d1: continue
    for p in sorted(glob.glob(f'{d1}/stage/elem_{k}_*.png')) + sorted(glob.glob(f'{d1}/stage/field_{k}.png')):
        im.paste(Image.open(p).convert('RGB').resize((160, 160 if 'elem' in p else 284)).crop((0, 0, 160, 284)) if 'field' in p else Image.open(p).convert('RGB').resize((160, 160)), (x, y)); x += 165
dr.text((3, y - 14), 'the AI\'s element pictures + painted field per card', fill=(235, 235, 235))
out = f'{Z}/scratchpad/orange/paint_strip.png'; im.save(out); print('strip ->', out)
print('\nper card: fine detail / saturation')
for lbl, k, a, z, d0, d1 in cards:
    line = [lbl[:30]]
    for name, d in (("today", d0), ("paint", d1)):
        if not d: continue
        ps = [f'{d}/frames/{kk:05d}.png' for kk in range(a, z + 1) if os.path.exists(f'{d}/frames/{kk:05d}.png')]
        if ps: line.append(f'{name}: detail {np.mean([detail(p) for p in ps]):.1f} sat {np.mean([sat(p) for p in ps]):.2f} (n={len(ps)})')
    print(' | '.join(line))
# looped side-by-side clips of the card: today | paint, 12 fps, x4
os.makedirs(f'{Z}/review/compare', exist_ok=True)
for lbl, k, a, z, d0, d1 in cards:
    if not (d0 and d1): continue
    tag = 'lattice' if 'LATTICE' in lbl else 'nucleus'
    outm = f'{Z}/review/compare/paint_AB_{tag}.mp4'
    cmd = [FFMPEG, '-y', '-loglevel', 'error',
           '-framerate', '12', '-start_number', str(a), '-i', f'{d0}/frames/%05d.png',
           '-framerate', '12', '-start_number', str(a), '-i', f'{d1}/frames/%05d.png',
           '-filter_complex', f"[0:v]trim=end_frame={z - a + 1},setpts=PTS-STARTPTS,drawtext=text='today':x=10:y=10:fontsize=28:fontcolor=white[a];"
                              f"[1:v]trim=end_frame={z - a + 1},setpts=PTS-STARTPTS,drawtext=text='paint':x=10:y=10:fontsize=28:fontcolor=white[b];"
                              f"[a][b]hstack=inputs=2,loop=loop=3:size={z - a + 1}:start=0[v]",
           '-map', '[v]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', outm]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print('clip ->', outm if r.returncode == 0 else f'FAILED {r.stderr[-300:]}')
