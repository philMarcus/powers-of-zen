#!/usr/bin/env python3
"""Generate mascot cast concept art via FLUX-schnell.

Canon (Phil, 2026-07-23): single subtle rhyming names; unified glossy-orb style,
big round Simpsons eyes, icon-of-scale not literal; names never shown on screen.
Refinements round 2: Adam = multi-nucleon core + electron bead on ring; Clark more
nebulous; new Tina (DNA/molecule); Belle bigger nucleus; Lee = hairy orb; human
level = incandescent-bulb orb (proposed name: Newman, rhymes with human).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
from dive import DEFAULTS, build_workflow, run_workflow  # noqa: E402

CFG = {**DEFAULTS,
       "checkpoint": "FLUX1\\flux1-schnell-fp8.safetensors",
       "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple",
       "width": 768, "height": 768, "negative": ""}

STYLE = ("cute minimal mascot character design, smooth rounded glossy body, "
         "the exact same face on every character: two big round white cartoon eyes "
         "with small black pupils looking slightly upward, and one single tiny simple "
         "curved mouth, no other facial features, no eyebrows, no eyelids, "
         "tiny stubby limbs, friendly and curious, centered, plain dark background "
         "with soft glow, unified toy-like character design sheet, high quality")

CAST = {
    "clark_quark": "a nebulous particle creature, a soft amorphous cloud of glowing energy wisps with three faint brighter lobes drifting inside",
    "adam_atom": "a translucent round glassy body with a small cluster of glossy blue and white proton and neutron spheres glowing at its center, encircled by one luminous tilted electron orbit ring carrying a single small bright glowing electron bead",
    "tina_dna": "a translucent rounded capsule body with a clearly double-stranded glowing DNA double helix inside, two intertwined strands connected by little rungs like a twisted ladder",
    "belle_cell": "a translucent round jelly body with one large pronounced glowing nucleus and small softly glowing organelles floating around it",
    "lee_flea": "a round orb creature covered in soft fine fuzzy hair with two tiny antennae, animal-like",
    "newman_human": "a warm glowing incandescent light bulb creature, bulb-shaped body with a rounded glass top narrowing to a small screw base at the bottom, a soft golden filament glowing inside, clearly a made object",
    "dora_flora": "a round flower-face orb creature ringed by soft glowing sunflower petals like a daisy, with two tiny leaf feet",
    "kitty_city": "a round orb creature whose surface is made of tiny glowing skyscraper windows and rooftops, with two small tower-shaped ears",
    "janet_planet": "a small satin-banded planet body with elegant tilted rings",
    "lamar_star": "a radiant round star orb with a warm corona glow and soft flare points",
    "maxie_galaxy": "a round orb creature swirled with luminous spiral arms of tiny stars around a bright glowing core",
    "amos_cosmos": "a deep dark round orb containing a glowing web of cosmic filaments and tiny distant galaxies",
}

base = Path(__file__).resolve().parent.parent / "output" / "mascots"
n = 1 + max([int(d.name[1:]) for d in base.glob("r[0-9]*") if d.name[1:].isdigit()],
            default=3)
out = base / f"r{n}"
out.mkdir(parents=True, exist_ok=True)
print(f"[mascot] round {n} -> {out}", flush=True)

only = sys.argv[1:] or list(CAST)
for name in only:
    for letter, seed in (("a", 7), ("b", 8), ("c", 9)):
        wf = build_workflow(CFG, f"{CAST[name]}, {STYLE}", seed)
        png = run_workflow(wf)
        p = out / f"{name}_{letter}.png"
        p.write_bytes(png)
        print(f"[mascot] {p.name}", flush=True)
