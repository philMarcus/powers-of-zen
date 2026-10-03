#!/usr/bin/env python3
"""STAGE LAB step 1 — the brand pass: a kit frame (pixels + depth from engine/stage.py) through
ONE img2img at denoise 0.30 / 0.45 / 0.60, with the real card's prompt + deck, with and without
the stage's own depth as the ControlNet. Gate: the structure reads as itself (a lattice, a
nucleus), not beads in mortar, at the denoise we would run in the chain (~0.30-0.45).
usage: stage_lab.py <out_dir>      (GPU: ComfyUI must be idle)"""
import io, json, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path('/mnt/c/Users/Phil/zoomer')
sys.path.insert(0, str(ROOT / 'engine')); sys.path.insert(0, str(ROOT / 'scripts'))
import dive, stage, style as _style, pipeline as pl  # noqa: E402

CASES = [  # (journey, card name, kit builder) — v2 builder cases take the card's palette
    ('kelp_dynamo', 'spore_cells', lambda s, pal=None: stage.build_card_stage_v2({"kit": "tissue", "cell": 0.22}, pal or 'emerald discs, ivory cell walls, indigo gloom', [1.0857] * 30, (0.6, 0.55), 576, 1024, seed=4)),
    ('vernal_clutch', 'atom_fog', lambda s, pal=None: stage.build_card_stage_v2({"kit": "fog", "lobes": 2}, pal or 'moon-teal haze, rust-orange core point, ink dark', [1.0857] * 30, (0.6, 0.55), 576, 1024, seed=4)),
    ('abyssal_chandelier', 'enzyme_turbines', lambda s, pal=None: stage.build_card_stage_v2({"kit": "tubes", "pdb": "4HHB", "n_copies": 12}, pal or 'cobalt-violet ropes, amber cross-links, glassy grain', [1.0857] * 30, (0.6, 0.55), 576, 1024, seed=4)),
    ('anvil_country', 'ice_lattice', lambda s: stage.kit_lattice(s, 'hex', spacing=0.5, radius=0.06, seed=5,
                                                                 colors=((0.75, 0.95, 0.85), (1, 1, 1)))),
    ('cobalt_rookery', 'calcite_lattice', lambda s: stage.kit_lattice(s, 'rhombo', spacing=0.48, seed=9,
                                                                      colors=((0.85, 0.9, 1.0), (0.4, 0.5, 0.9)))),
    ('sunspot_archipelago', 'nucleus_droplet', lambda s: stage.kit_nucleus(s, seed=11, colors=((0.9, 0.3, 0.25), (0.95, 0.9, 0.8)))),
    ('cork_dehesa', 'carbon_atom', lambda s: stage.kit_lattice(s, 'diamond', spacing=0.6, radius=0.07, seed=7,
                                                               colors=((0.6, 0.8, 1.0), (0.6, 0.8, 1.0)))),
]
DENS = (0.30, 0.45, 0.60)


def card(journey, name):
    spec = json.load(open(pl.journey_path(journey), encoding='utf-8'))
    reg = next((r for r in spec['registers'] if r['name'] == name), None)
    if reg is None:
        reg = next(r for r in spec['registers'] if r.get('exp', 0) <= -8)
    sfx, _, sname = _style.resolve(spec)
    pal = reg.get('palette')
    prompt = f"moving through {reg.get('scene')}, {sfx}" + (f", {pal} colors" if pal else '')
    return reg, prompt, sname


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cfg = {**dive.DEFAULTS, **dive.MODEL_PRESETS['ds']}
    rows = []
    for journey, cname, build in CASES:
        reg, prompt, sname = card(journey, cname)
        import inspect
        if 'pal' in inspect.signature(build).parameters:
            st = build(None, reg.get('palette'))          # v2 kits build their own Stage
        else:
            st = build(stage.Stage([1.045] * 30, [(0.6, 0.55)] * 30))
        rgb, dep = st.frame_images(12)
        rgb.save(out / f'{journey}_{cname}_stage.png'); dep.save(out / f'{journey}_{cname}_depth.png')
        ref = dive.upload_image(rgb, f'zoomer_stage_{journey}.png')
        ctl = dive.upload_image(dep, f'zoomer_stage_{journey}_d.png')
        tiles = [rgb]
        labels = ['stage']
        for den in DENS:
            for cn in (0.0, 0.45):
                t0 = time.time()
                wf = dive.build_workflow(cfg, prompt, 1234, init_image=ref, denoise=den,
                                         ctrl_image=ctl if cn else None, cn_strength=cn, depth_preproc=None)
                im = Image.open(io.BytesIO(dive.run_workflow(wf))).convert('RGB')
                im.save(out / f'{journey}_{cname}_d{den:.2f}_cn{cn:g}.png')
                tiles.append(im); labels.append(f'den {den:.2f} cn {cn:g}')
                print(f'{journey}/{cname} den {den} cn {cn}: {time.time() - t0:.1f}s', flush=True)
        rows.append((f'{journey}/{cname} [{sname}]', tiles, labels))
    tw, th = 180, 320
    sheet = Image.new('RGB', (tw * 7, (th + 14) * len(rows)), (15, 15, 15)); dr = ImageDraw.Draw(sheet)
    for r, (title, tiles, labels) in enumerate(rows):
        y = r * (th + 14); dr.text((4, y), title, fill=(255, 255, 0))
        for c, (im, lab) in enumerate(zip(tiles, labels)):
            t = im.copy(); t.thumbnail((tw, th)); sheet.paste(t, (c * tw, y + 14)); dr.text((c * tw + 3, y + 16), lab, fill=(255, 255, 255))
    name_ = 'brand_pass_sheet2.png' if len(sys.argv) > 2 else 'brand_pass_sheet.png'
    sheet.save(out / name_); print('->', out / name_)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'output' / 'stage_lab')
