#!/usr/bin/env python3
"""PALETTE ANCHOR (candidate fix component, 2026-10-03): turn a card's authored palette text
("cerulean plasma, pearl-grey cells, lilac wall tiling, ink gloom") into per-channel
(mean, std) target stats = the colour_match reference, instead of the phase's own first frame
(which is already drifted). Colour words resolve through a small house table + xkcd/CSS
names; non-colour words are ignored; dark words (ink/void/soot/jet) weight the dark end.
Mixture weights: each phrase (comma-separated) is one swatch; the FIRST word of a phrase that
resolves to a colour is its colour; unresolved phrases contribute nothing."""
import re
import numpy as np

HOUSE = {  # words the catalog uses that xkcd/css lack (sRGB 0-255)
    'ink': (12, 12, 22), 'void': (6, 6, 12), 'soot': (22, 20, 20), 'sooty': (22, 20, 20),
    'jet': (10, 10, 12), 'sable': (18, 14, 14), 'obsidian': (14, 12, 18), 'unlit': (8, 8, 10),
    'charcoal': (40, 40, 44), 'tar': (18, 16, 14), 'char': (26, 22, 20), 'black': (8, 8, 10),
    'brass': (181, 148, 70), 'ember': (210, 80, 30), 'vermilion': (227, 66, 52),
    'pewter': (140, 142, 150), 'pearl': (228, 224, 218), 'pearl-grey': (190, 190, 196),
    'chalk': (236, 234, 226), 'bone': (226, 218, 196), 'garnet': (115, 20, 40),
    'oxblood': (90, 20, 24), 'verdigris': (67, 179, 174), 'cinnabar': (227, 66, 52),
    'honey': (235, 170, 60), 'moon': (210, 214, 230), 'moon-silver': (200, 206, 222),
    'moon-teal': (120, 200, 200), 'moon-white': (240, 242, 248), 'ash': (160, 158, 150),
    'acid': (190, 255, 60), 'absinthe': (160, 220, 60), 'chartreuse': (160, 230, 50),
    'milk': (240, 238, 230), 'milk-pale': (236, 234, 224), 'ivory': (240, 234, 210),
    'storm-slate': (80, 90, 105), 'slate': (90, 100, 115), 'opal': (214, 226, 230),
    'ice': (200, 230, 245), 'ice-blue': (180, 220, 245), 'tea-brown': (120, 80, 40),
    'tannin': (120, 70, 30), 'rust': (170, 70, 30), 'umber': (99, 68, 36), 'ochre': (204, 140, 40),
    'copper': (184, 115, 51), 'gold': (230, 190, 60), 'amber': (240, 170, 40),
    'cobalt': (30, 70, 190), 'cerulean': (40, 130, 220), 'lilac': (200, 162, 230),
    'violet': (140, 60, 200), 'indigo': (60, 40, 140), 'teal': (0, 128, 128),
    'turquoise': (64, 224, 208), 'jade': (0, 168, 107), 'viridian': (64, 130, 109),
    'emerald': (40, 180, 90), 'olive': (120, 120, 40), 'sulphur': (230, 220, 60),
    'sulfur': (230, 220, 60), 'saffron': (244, 196, 48), 'mustard': (210, 170, 40),
    'magenta': (230, 40, 200), 'fuchsia': (240, 60, 200), 'cerise': (222, 49, 99),
    'rose': (230, 120, 150), 'pink': (240, 150, 190), 'plum': (120, 40, 90),
    'maroon': (110, 20, 40), 'crimson': (200, 20, 50), 'scarlet': (230, 30, 30),
    'silver': (200, 204, 212), 'white': (245, 245, 245), 'grey': (140, 140, 140),
    'gray': (140, 140, 140), 'cream': (245, 235, 205), 'sapphire': (30, 60, 200),
    'sea-glass': (150, 220, 200), 'blue-white': (220, 235, 255), 'blue': (50, 90, 220),
    'green': (50, 160, 70), 'red': (220, 40, 40), 'orange': (240, 130, 30), 'yellow': (245, 220, 50),
}
_XK = None
def _xkcd():
    global _XK
    if _XK is None:
        import matplotlib.colors as mc
        _XK = {k[5:]: tuple(int(v.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) for k, v in mc.XKCD_COLORS.items()}
        for k, v in mc.CSS4_COLORS.items():
            _XK.setdefault(k, tuple(int(v.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)))
    return _XK

MODS = {'pale': 0.35, 'deep': -0.25, 'dark': -0.35, 'cold': 0, 'warm': 0, 'hot': 0.1, 'bright': 0.15,
        'faint': 0.3, 'burnt': -0.2, 'molten': 0.1, 'electric': 0.1, 'milk': 0.4, 'moon': 0.3}

def word_rgb(w):
    w = w.lower().strip()
    if w in HOUSE: return HOUSE[w]
    xk = _xkcd()
    if w in xk: return xk[w]
    if '-' in w:                      # 'rust-orange', 'violet-glass': blend resolvable parts
        parts = [word_rgb(p) for p in w.split('-')]
        parts = [p for p in parts if p]
        if parts: return tuple(int(np.mean([p[i] for p in parts])) for i in range(3))
    return None

def phrase_rgb(phrase):
    """First colour word in the phrase, lightened/darkened by its modifiers."""
    words = re.findall(r"[a-z]+(?:-[a-z]+)*", phrase.lower())
    rgb, mod = None, 0.0
    for w in words:
        if w in MODS and rgb is None: mod += MODS[w]
        elif rgb is None:
            rgb = word_rgb(w)
    if rgb is None: return None
    rgb = np.array(rgb, float)
    if mod > 0: rgb = rgb + (255 - rgb) * min(0.8, mod)
    elif mod < 0: rgb = rgb * (1 + max(-0.6, mod))
    return tuple(int(x) for x in np.clip(rgb, 0, 255))

def swatch_stats(palette, w=64):
    """-> ((mR,mG,mB), (sR,sG,sB)) of a synthetic swatch: each resolvable phrase an equal
    stripe. None if nothing resolves."""
    cols = [phrase_rgb(p) for p in re.split(r",|\bon\b|\bover\b|\bunder\b|\bthrough\b", palette or '')]
    cols = [c for c in cols if c]
    if not cols: return None
    arr = np.array(cols, float)
    return tuple(arr.mean(0)), tuple(arr.std(0) + 28.0)   # +floor: a swatch has no texture

if __name__ == '__main__':
    import json, sys, glob, collections
    sys.path.insert(0, '/mnt/c/Users/Phil/zoomer/scripts'); import pipeline as pl
    n = res = 0; miss = collections.Counter()
    for name in pl.journey_names():
        try: s = json.load(open(pl.journey_path(name), encoding='utf-8'))
        except Exception: continue
        for r in s.get('registers', []):
            pal = r.get('palette') or ''
            if not pal: continue
            n += 1
            for p in re.split(r",|\bon\b|\bover\b", pal):
                if phrase_rgb(p) is None and p.strip(): miss[p.strip().lower()] += 1
            if swatch_stats(pal): res += 1
    print(f'cards with palette {n}, resolvable {res} ({100*res/n:.0f}%)')
    print('unresolved phrases (top 40):', miss.most_common(40))
    for pal in ('cerulean plasma, pearl-grey cells, lilac wall tiling, ink gloom', 'violet haze, white core point, jet void',
                'burning copper pairs, lilac ribbon walls, cerulean murk'):
        print(pal, '->', swatch_stats(pal))


def swatch_image(palette, w=576, h=1024, seed=0):
    """A soft colour-field reference for IP-Adapter: the card's resolved phrase colours as
    broad diagonal bands, heavily blurred with a little grain (composition-free — only the
    palette is there to transfer). None if nothing resolves."""
    from PIL import Image, ImageFilter
    cols = [phrase_rgb(p) for p in re.split(r",|\bon\b|\bover\b|\bunder\b|\bthrough\b", palette or '')]
    cols = [c for c in cols if c]
    if not cols:
        return None
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (xx / w * 0.6 + yy / h) / 1.6                    # diagonal ramp 0..1
    t = (t + 0.08 * rng.standard_normal((h, w)).astype(np.float32)) % 1.0
    idx = np.minimum((t * len(cols)).astype(int), len(cols) - 1)
    arr = np.array(cols, np.float32)[idx]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w * 0.06))
    grain = Image.effect_noise((w, h), 48).convert("RGB")
    return Image.blend(im, grain, 0.08)


WARM = re.compile(r"\b(gold|golden|amber|umber|ochre|orange|copper|brass|bronze|rust|rusty|ember|"
                  r"honey|saffron|mustard|tangerine|apricot|sulphur|sulfur|citrine|caramel|tan|"
                  r"peach|coral|vermilion|scarlet|crimson|garnet|maroon|oxblood|cinnabar|red|"
                  r"burnt|molten|fire|flame|blazing|incandescent)\b", re.I)
COOL = re.compile(r"\b(blue|cobalt|cerulean|sapphire|indigo|navy|teal|turquoise|cyan|verdigris|"
                  r"jade|emerald|viridian|green|lime|chartreuse|absinthe|olive|violet|lilac|lavender|"
                  r"purple|plum|magenta|fuchsia|cerise|rose|pink|ice|ice-blue|moon|silver|pewter|"
                  r"slate|steel|opal|sea-glass)\b", re.I)


def warm_cool(palette):
    """(warm word count, cool word count) in an authored palette."""
    return len(WARM.findall(palette or "")), len(COOL.findall(palette or ""))


def negative_for(palette):
    """Palette-conditional negative: fight the chain's warm attractor ONLY where the card
    authored no warm hue at all (a card that asks for copper or amber keeps them). Mirror
    for cool so an all-warm card isn't pulled teal. '' when the palette is mixed."""
    w, c = warm_cool(palette)
    if c and not w:
        return "orange, amber, gold, copper, rust, orange and teal colour grading"
    if w and not c:
        return "teal, cyan, blue, violet, orange and teal colour grading"
    return ""


# ---- hue-aware transfer (Reinhard 2001, lαβ space) ------------------------------------
_RGB2LMS = np.array([[0.3811, 0.5783, 0.0402], [0.1967, 0.7244, 0.0782], [0.0241, 0.1288, 0.8444]])
_LMS2LAB = np.array([[1 / np.sqrt(3), 0, 0], [0, 1 / np.sqrt(6), 0], [0, 0, 1 / np.sqrt(2)]]) @ \
    np.array([[1, 1, 1], [1, 1, -2], [1, -1, 0]])
_LAB2LMS = np.linalg.inv(_LMS2LAB)
_LMS2RGB = np.linalg.inv(_RGB2LMS)


def _to_lab(rgb01):
    lms = np.log10(np.maximum(rgb01 @ _RGB2LMS.T, 1e-4))
    return lms @ _LMS2LAB.T


def _from_lab(lab):
    lms = 10 ** (lab @ _LAB2LMS.T)
    return lms @ _LMS2RGB.T


def swatch_lab_stats(palette, seed=0):
    """(mean, std) in lαβ of the palette's swatch image (small render). None if unresolvable."""
    im = swatch_image(palette, 96, 160, seed=seed)
    if im is None:
        return None
    lab = _to_lab(np.asarray(im, np.float32).reshape(-1, 3) / 255.0)
    return lab.mean(0), lab.std(0) + 1e-3


def transfer_lab(img, target, strength):
    """Pull a PIL image's lαβ mean/std `strength` of the way toward target=(mean, std).
    Luminance (l) is matched only half as hard as the chroma axes (α, β): the goal is the
    palette's HUE balance, not its brightness. Returns a PIL image."""
    from PIL import Image
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    h, w, _ = a.shape
    lab = _to_lab(a.reshape(-1, 3))
    m, s = lab.mean(0), lab.std(0) + 1e-3
    tm, ts = target
    k = np.array([0.5 * strength, strength, strength])
    gain = 1 + k * (ts / s - 1)
    out = (lab - m) * gain + m + k * (tm - m)
    rgb = _from_lab(out).reshape(h, w, 3)
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
