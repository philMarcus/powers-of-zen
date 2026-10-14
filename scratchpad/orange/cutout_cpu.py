# CPU check of the echo CUT-OUT: a lattice stage whose hero atom becomes a whale-shaped cut-out.
import sys, math, numpy as np
sys.path[:0] = ['engine']
import stage
from PIL import Image, ImageDraw
W, H = stage.W, stage.H
n = 96
zooms = [1.045] * n
anchor = (0.62, 0.40)
st = stage.build_card_stage('lattice', {'variant': 'cubic', 'radius': 0.055, 'spacing': 0.42}, zooms, anchor, W, H, seed=3)
# synthetic donor swatch: a whale-ish silhouette on black (body ellipse + tail + fin), lit from one side
im = Image.new('RGB', (768, 768), (0, 0, 0)); dr = ImageDraw.Draw(im)
dr.ellipse((150, 300, 560, 470), fill=(90, 110, 140))
dr.polygon([(540, 385), (660, 300), (700, 340), (640, 390), (700, 440), (660, 470)], fill=(80, 100, 130))
dr.polygon([(330, 310), (380, 220), (430, 310)], fill=(85, 105, 135))
dr.ellipse((150, 300, 560, 400), fill=(130, 150, 180))          # a lit back
im.save('/tmp/claude-0/-mnt-c-Users-Phil-zoomer/7ec3543c-682b-4baa-8210-314e137ad070/scratchpad/cutout_swatch.png')
# synthetic depth: nearer in the middle of the body (what DepthAnything would roughly give)
yy, xx = np.mgrid[0:768, 0:768].astype(np.float32)
d = np.exp(-(((xx - 360) / 220) ** 2 + ((yy - 385) / 90) ** 2)) * 0.6 + 0.2
lum = np.asarray(im.convert('L'), np.float32) / 255
d = np.where(lum > 0.05, d, 0.05)
for tag, dep, frac in (('dome', None, 0.0), ('depth', d, 0.0), ('depth_field', d, 0.5)):
    import copy
    s2 = copy.deepcopy(st)
    k = s2.set_echo_cutout(im, dep, frac=frac)
    print(tag, 'converted', k, 'hero', s2.cut_hero, 'from_depth', s2.cut_from_depth, 'mask px', int((s2.cut_mask > .5).sum()))
    tiles = []
    for f in (0, n // 2, n - 8, n - 1):
        col, dm = s2.frame(f)
        rgb = (np.clip(col, 0, 1) * 255).astype(np.uint8)
        dd = (np.clip(dm, 0, 1) * 255).astype(np.uint8)
        tiles.append(np.concatenate([rgb, np.repeat(dd[..., None], 3, -1)], 1))
    sheet = np.concatenate(tiles, 1)
    Image.fromarray(sheet).resize((sheet.shape[1] // 2, sheet.shape[0] // 2)).save(
        f'/tmp/claude-0/-mnt-c-Users-Phil-zoomer/7ec3543c-682b-4baa-8210-314e137ad070/scratchpad/cutout_cpu_{tag}.png')
print('ok')
