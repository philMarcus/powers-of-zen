"""ECHO CUT-OUT arms strip + numbers (2026-10-14). valdes_blow cards 6-8: v1 (nightly 10-12, echo words only) /
D (relief + half-lit = tonight's nightly) / A (cut-out hero) / B (hero + half the spheres) + A's stage layer;
lepidolite_halo_var card 6: v3 (relief) / C (cut-out) + C's stage layer. Latest vN of each arm dir.
usage: cutout_strip.py [out.png]"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
Z = '/mnt/c/Users/Phil/zoomer'


def latest(d):
    vs = sorted(glob.glob(f'{d}/v*'), key=lambda p: int(os.path.basename(p)[1:]))
    return vs[-1] + '/build' if vs else None


def detail(p):
    im = Image.open(p).convert('L').resize((288, 512))
    a = np.asarray(im, np.float32); b = np.asarray(im.filter(ImageFilter.GaussianBlur(3)), np.float32)
    return float(np.abs(a - b).mean())


def sat(p):
    a = np.asarray(Image.open(p).convert('RGB').resize((144, 256)), np.float32) / 255
    mx, mn = a.max(-1), a.min(-1)
    return float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean())


sets = [
    ('valdes_blow', f'{Z}/output/valdes_blow/v1/build', 'v1 words',
     [('D relief', latest(f'{Z}/output/valdes_blow_platelive_cutout_d')),
      ('A cut-out hero', latest(f'{Z}/output/valdes_blow_platelive_cutout_a')),
      ('B cut-out hero+field', latest(f'{Z}/output/valdes_blow_platelive_cutout_b'))],
     [('k6 polysome_spiral TUBES · echo "a black right whale and calf"', 192, 223),
      ('k7 sulfur_atom LATTICE · echo "a cream callosity"', 224, 255),
      ('k8 dijet TRACKS · echo "a coiled protein chain"', 256, 287)]),
    ('lepidolite_halo_var', f'{Z}/output/lepidolite_halo_var/v3/build', 'v3 relief',
     [('C cut-out hero+field', latest(f'{Z}/output/lepidolite_halo_var_platelive_cutout_c'))],
     [('k6 lepidolite_layers LATTICE · echo "a lilac mica crystal"', 192, 223)]),
]
rows = []
for j, base, blbl, arms, cards in sets:
    for lbl, a, z in cards:
        ks = list(range(a, z + 1, 4))[:8]
        rows.append((f'{j} {blbl} · {lbl}', base + '/frames', ks, None))
        for al, ad in arms:
            if ad:
                rows.append((f'{al} · {lbl}', ad + '/frames', ks, None))
        # the stage-layer row comes from the arm with the most saved stage images (a killed arm
        # has a handful, and the nearest-file lookup would show its frames for every card)
        have = [(len(glob.glob(f'{ad}/stage/*_stage.png')), al, ad) for al, ad in arms if ad]
        if have:
            _, al, ad = max(have)
            rows.append((f'{al} STAGE LAYER · {lbl}', ad + '/stage', ks, '_stage'))
W, H = 150, 266
im = Image.new('RGB', (8 * W, len(rows) * (H + 16)), (8, 8, 10))
dr = ImageDraw.Draw(im)
for r, (lbl, d, ks, suf) in enumerate(rows):
    for c, k in enumerate(ks):
        p = f'{d}/{k:05d}{suf or ""}.png'
        if not os.path.exists(p) and suf:
            cands = sorted(glob.glob(f'{d}/*_stage.png'))
            if cands:
                p = min(cands, key=lambda q: abs(int(os.path.basename(q)[:5]) - k))
        if os.path.exists(p):
            im.paste(Image.open(p).convert('RGB').resize((W, H)), (c * W, r * (H + 16) + 16))
    dr.text((3, r * (H + 16) + 2), f'{lbl} f{ks[0]}..{ks[-1]}', fill=(235, 235, 235))
out = sys.argv[1] if len(sys.argv) > 1 else f'{Z}/scratchpad/orange/cutout_strip.png'
im.save(out); print('strip ->', out)
print('\nper card: mean fine detail (|high-pass|) and saturation')
for j, base, blbl, arms, cards in sets:
    for lbl, a, z in cards:
        line = [lbl[:22]]
        for name, d in [(blbl, base)] + [(al, ad) for al, ad in arms if ad]:
            ps = [f'{d}/frames/{k:05d}.png' for k in range(a, z + 1) if os.path.exists(f'{d}/frames/{k:05d}.png')]
            if ps:
                line.append(f'{name}: detail {np.mean([detail(p) for p in ps]):.2f} sat {np.mean([sat(p) for p in ps]):.2f} (n={len(ps)})')
        print(' | '.join(line))
