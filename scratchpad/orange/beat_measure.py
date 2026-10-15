"""Where does a handoff FLIP relative to the beat? For each bar line B: the frame at which the picture is
nearer the NEW world (mean of B+8..B+11) than the OLD (mean of B-22..B-19). 0 = the downbeat, 12 f = 1 s.
usage: beat_measure.py <frames_dir> <frames_per_card> <bar,bar,...> [label]"""
import sys, os, numpy as np
from PIL import Image
d, fpc, bars = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(',')]
lbl = sys.argv[4] if len(sys.argv) > 4 else d
def load(k):
    p = f'{d}/{k:05d}.png'
    return np.asarray(Image.open(p).convert('RGB').resize((48, 86)), np.float32) / 255 if os.path.exists(p) else None
out = []
for B in bars:
    if load(B + 11) is None or load(B - 22) is None: continue
    A = np.mean([load(k) for k in range(B - 22, B - 18)], 0); Z = np.mean([load(k) for k in range(B + 8, B + 12)], 0)
    prog = []
    for f in range(B - 18, B + 9):
        x = load(f); da, dz = np.abs(x - A).mean(), np.abs(x - Z).mean(); prog.append(da / max(da + dz, 1e-6))
    sm = np.convolve(prog, np.ones(3) / 3, mode='same'); w = np.arange(-18, 9)
    idx = int(np.argmax(sm >= 0.5)) if (sm >= 0.5).any() else len(sm) - 1
    out.append(int(w[idx])); print(f'{lbl}: bar {B} flips at {w[idx]:+d} f ({w[idx]/12:+.2f} s)   progress -18..+8 /3f: ' + ' '.join(f'{v:.2f}' for v in sm[::3]))
if out: print(f'{lbl}: mean flip {np.mean(out):+.1f} f ({np.mean(out)/12:+.2f} s) over {out}')
