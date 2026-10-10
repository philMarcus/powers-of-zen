#!/usr/bin/env python3
"""STAGE SAMENESS INDEX + BOARD (2026-10-10).
Per-card features from mid-card frames of every stage-era render on disk; nearest-neighbour
distances within staged cards (other journeys), within unstaged cards (other journeys), and
across; per-kit tightness. Boards: one frame per staged card grouped by kit, and an equal-size
unstaged sample. Usage: python3 scratchpad/orange/stage_sameness.py [--tag label]"""
import json, glob, sys, os, random
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
ROOT = '/mnt/c/Users/Phil/zoomer'
TAG = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'baseline'
ONLY = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None

def card_spans(r):
    cf = r.get('card_frames') or []
    spans, a = [], 0
    for n in cf:
        spans.append((a, a + n)); a += n
    return spans

def features(path):
    im = Image.open(path).convert('RGB').resize((144, 256), Image.BILINEAR)
    a = np.asarray(im, np.float32) / 255.0
    hsv = np.asarray(im.convert('HSV'), np.float32) / 255.0
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    hist, _ = np.histogram(h, bins=12, range=(0, 1), weights=s); hist = hist / (hist.sum() + 1e-6)
    g = a.mean(-1)
    sx = ndimage.sobel(g, 0); sy = ndimage.sobel(g, 1); edge = np.hypot(sx, sy)
    lap = ndimage.laplace(g)
    thr = g > (g.mean() + 0.5 * g.std())
    lab, n = ndimage.label(thr)
    sizes = np.bincount(lab.ravel())[1:] if n else np.array([1.0])
    bh, _ = np.histogram(np.log10(sizes + 1), bins=6, range=(0, 4.5)); bh = bh / (bh.sum() + 1e-6)
    thumb = np.asarray(im.convert('L').resize((5, 9), Image.BILINEAR), np.float32).ravel() / 255.0
    f = {'hue': hist, 'tone': np.array([s.mean(), v.mean(), v.std(), s.std()]),
         'edge': np.array([edge.mean(), edge.std(), lap.var() * 50, (edge > 0.3).mean()]),
         'blob': np.concatenate([bh, [np.log10(n + 1) / 3]]), 'thumb': thumb}
    return f

cards = []   # dict(journey, run, card, kit, look, staged, frames)
for rj in sorted(glob.glob(f'{ROOT}/output/*/v*/run.json')):
    try: r = json.load(open(rj))
    except Exception: continue
    name = rj.split('/')[-3]
    if ONLY and name not in ONLY: continue
    if '_platelive' in name or name.endswith('_mini') or '_zt' in name or '_orange' in name: continue
    sc = r.get('stage_cards') or []
    if not sc: continue
    fdir = os.path.join(os.path.dirname(rj), 'build', 'frames')
    if not os.path.isdir(fdir): continue
    kits = {k[0]: (k[1], k[2] if len(k) > 2 else None) for k in (r.get('stage_kits') or [])}
    staged = {}
    for c, a, b in sc:
        staged[c] = (a, b)
    spans = card_spans(r)
    # unstaged cards = render-order spans not covered by a staged span
    covered = [(a, b) for a, b in staged.values()]
    for i, (a, b) in enumerate(spans):
        if any(not (b <= ca or a >= cb) for ca, cb in covered): continue
        cards.append(dict(journey=name, run=rj, card=f'r{i}', kit='-', look='-', staged=False, span=(a, b)))
    for c, (a, b) in staged.items():
        kit, look = kits.get(c, ('?', None))
        cards.append(dict(journey=name, run=rj, card=f'k{c}', kit=kit, look=look, staged=True, span=(a, b)))

# features: 3 frames per card at 30/55/80 %
keep = []
for c in cards:
    a, b = c['span']; fs = []
    for t in (0.30, 0.55, 0.80):
        p = os.path.join(os.path.dirname(c['run']), 'build', 'frames', f'{int(a + t * (b - a)):05d}.png')
        if os.path.exists(p): fs.append(p)
    if len(fs) < 2: continue
    F = [features(p) for p in fs]
    c['feat'] = {k: np.mean([f[k] for f in F], 0) for k in F[0]}
    c['mid'] = fs[1] if len(fs) > 1 else fs[0]
    keep.append(c)
cards = keep
print(f'[{TAG}] cards: {len(cards)} ({sum(c["staged"] for c in cards)} staged, '
      f'{sum(not c["staged"] for c in cards)} unstaged) from {len({c["journey"] for c in cards})} renders')

# z-score per group, equal group weight
groups = ['hue', 'tone', 'edge', 'blob', 'thumb']
X = {g: np.array([c['feat'][g] for c in cards]) for g in groups}
Z = []
for g in groups:
    x = X[g]; z = (x - x.mean(0)) / (x.std(0) + 1e-6); Z.append(z / np.sqrt(z.shape[1]))
Z = np.concatenate(Z, 1)
D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1))
J = np.array([c['journey'] for c in cards]); S = np.array([c['staged'] for c in cards])
K = np.array([c['kit'] for c in cards])

def nn(mask_a, mask_b):
    """mean/median nearest-neighbour distance from set a into set b, other journeys only."""
    out = []
    for i in np.where(mask_a)[0]:
        m = mask_b & (J != J[i]); m[i] = False
        if m.any(): out.append(D[i, m].min())
    return (np.mean(out), np.median(out), len(out)) if out else (np.nan, np.nan, 0)

def nn_sub(mask_a, mask_b, n_to, draws=25):
    """like nn() but the target set is SUBSAMPLED to n_to cards (NN distance shrinks with set
    size, so staged (63) vs unstaged (192) must be compared at equal set size)."""
    rng = np.random.default_rng(1); ms, mds, cnt = [], [], 0
    idx_b = np.where(mask_b)[0]
    for _ in range(draws):
        sub = np.zeros_like(mask_b); sub[rng.choice(idx_b, size=min(n_to, len(idx_b)), replace=False)] = True
        src = mask_a & sub if mask_a is mask_b else mask_a
        m, md, cnt = nn(src, sub); ms.append(m); mds.append(md)
    return (float(np.mean(ms)), float(np.mean(mds)), cnt)
n_st = int(S.sum())
rows = [('staged -> staged (other journeys)', nn(S, S)),
        ('unstaged -> unstaged, SUBSAMPLED to the staged count', nn_sub(~S, ~S, n_st)),
        ('unstaged -> unstaged (all 192)', nn(~S, ~S)),
        ('staged -> unstaged', nn(S, ~S)),
        ('unstaged -> staged', nn(~S, S))]
print(f'\n[{TAG}] nearest-neighbour distance (lower = more alike):')
for lbl, (m, md, n) in rows: print(f'  {lbl:40s} mean {m:5.2f}  median {md:5.2f}  n {n}')
print(f'\n[{TAG}] within-kit NN (staged, other journeys, same kit):')
for kit in sorted(set(K[S])):
    m, md, n = nn(S & (K == kit), S & (K == kit)); print(f'  {kit:10s} mean {m:5.2f} median {md:5.2f} n {n}')
# per-group contribution: which feature group makes staged cards alike?
print(f'\n[{TAG}] per-group staged/unstaged NN ratio (<1 = staged more alike in that group):')
off = 0
for g in groups:
    w = X[g].shape[1]; Zg = Z[:, off:off + w]; off += w
    Dg = np.sqrt(((Zg[:, None, :] - Zg[None, :, :]) ** 2).sum(-1))
    def nng(ma):
        o = []
        for i in np.where(ma)[0]:
            m = ma & (J != J[i]); m[i] = False
            if m.any(): o.append(Dg[i, m].min())
        return np.mean(o)
    print(f'  {g:6s} staged {nng(S):5.2f}  unstaged {nng(~S):5.2f}  ratio {nng(S)/nng(~S):4.2f}')

# boards
def board(sel, path, title, by_kit=True):
    sel = sorted(sel, key=lambda c: (c['kit'], c['journey'])) if by_kit else sel
    tw, th, cols = 144, 256, 11
    rowsn = (len(sel) + cols - 1) // cols
    im = Image.new('RGB', (cols * tw, rowsn * (th + 18) + 24), (12, 12, 14)); dr = ImageDraw.Draw(im)
    dr.text((6, 5), title, fill=(230, 230, 230))
    for i, c in enumerate(sel):
        x, y = (i % cols) * tw, 24 + (i // cols) * (th + 18)
        im.paste(Image.open(c['mid']).convert('RGB').resize((tw, th)), (x, y))
        dr.text((x + 3, y + th + 2), f"{c['journey'][:13]} {c['kit']}/{c['look'] or ''}"[:24], fill=(200, 200, 200))
    im.save(path); print('board ->', path)
staged_cards = [c for c in cards if c['staged']]
board(staged_cards, f'{ROOT}/scratchpad/orange/stage_board_{TAG}.png', f'STAGED cards ({TAG}) — one mid-card frame each, grouped by kit')
random.seed(7); uns = random.sample([c for c in cards if not c['staged']], min(len(staged_cards), sum(not c['staged'] for c in cards)))
board(uns, f'{ROOT}/scratchpad/orange/unstaged_board_{TAG}.png', f'UNSTAGED cards ({TAG}) — equal-size random sample', by_kit=False)
json.dump({'tag': TAG, 'rows': {l: list(map(float, v[:2])) for l, v in rows}}, open(f'{ROOT}/scratchpad/orange/stage_sameness_{TAG}.json', 'w'))

# ---- ABSOLUTE TONE STATS (2026-10-10, after the boards): what the eye sees is tone + element
# scale, not geometry. Report sat / contrast / luminance / big-element share per group.
def tone_of(path):
    im = Image.open(path).convert('RGB').resize((144, 256), Image.BILINEAR)
    hsv = np.asarray(im.convert('HSV'), np.float32) / 255.0
    g = np.asarray(im.convert('L'), np.float32) / 255.0
    thr = g > (g.mean() + 0.5 * g.std()); lab, n = ndimage.label(thr)
    sizes = np.bincount(lab.ravel())[1:] if n else np.array([1.0])
    big = (sizes[sizes >= 200].sum() / max(1, sizes.sum())) if n else 0.0   # share of bright area in blobs >= 200 px (of 36864)
    return np.array([hsv[..., 1].mean(), g.std(), g.mean(), big, (hsv[..., 1] > 0.5).mean()])
T = np.array([tone_of(c['mid']) for c in cards])
names = ['sat', 'contrast', 'lum', 'big_share', 'vivid_px']
def rep(lbl, m):
    if m.sum() == 0: return
    t = T[m]; print(f'  {lbl:28s} n {m.sum():3d}  ' + '  '.join(f'{nm} {t[:, i].mean():.3f}' for i, nm in enumerate(names)))
print(f'\n[{TAG}] ABSOLUTE TONE (delivered mid-card frames):')
rep('UNSTAGED', ~S); rep('STAGED', S)
L = np.array([c['look'] or '-' for c in cards])
for lk in sorted(set(L[S])): rep(f'  look {lk}', S & (L == lk))
for kit in sorted(set(K[S])): rep(f'  kit {kit}', S & (K == kit))
# the stage LAYER itself (build/stage/NNNNN_stage.png) and the fed frame, where saved
st_rows, fed_rows = [], []
for c in cards:
    if not c['staged']: continue
    a, b = c['span']; f = int(a + 0.55 * (b - a)); d = os.path.join(os.path.dirname(c['run']), 'build', 'stage')
    for k in range(f, f + 4):
        p1, p2 = os.path.join(d, f'{k:05d}_stage.png'), os.path.join(d, f'{k:05d}_fed.png')
        if os.path.exists(p1): st_rows.append(tone_of(p1)); fed_rows.append(tone_of(p2)); break
if st_rows:
    for lbl, rows_ in (('STAGE LAYER (CG colour)', st_rows), ('FED FRAME (composite in)', fed_rows)):
        t = np.array(rows_); print(f'  {lbl:28s} n {len(t):3d}  ' + '  '.join(f'{nm} {t[:, i].mean():.3f}' for i, nm in enumerate(names)))
