#!/usr/bin/env python3
"""novelty_audit — measure catalog repetitiveness + realm coverage for the overseer.

The midnight refill embeds `--brief` output in the coordinator prompt so "what's overused /
what's missing" is DATA, not vibes (Phil 2026-08-13). Full mode is the human report.

Axes (see journeys/REALMS.md for the formalism):
  * band coverage — cards per scale band; under-built bands are where novelty is cheap
  * realm fidelity — living parents must go cellular in -4..-6 and molecular in -6..-8.5
    (the continuation rule); generic lattices there are the catalog's biggest repetition
  * motif overuse — content words appearing in most journeys (the pale-X-on-dark-Y monoculture)
  * scene population — human-scale ecosystem cards naming >=3 distinct inhabitant kinds
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as pl  # noqa: E402

BANDS = [(-16, -12, "subnuclear"), (-12, -8.5, "atomic"), (-8.5, -6, "molecular"),
         (-6, -3.5, "cellular"), (-3.5, -1.5, "mm-creature"), (-1.5, 1.5, "human"),
         (1.5, 4.5, "landscape"), (4.5, 9, "planetary"), (9, 14, "stellar"),
         (14, 22, "galactic"), (22, 27, "cosmic-web")]

CELL_W = re.compile(r"\b(cells?|membranes?|organelles?|nucle(us|i)|mitochond|cytoplasm|"
                    r"vesicles?|cilia|flagell|ribosom|amoeb|diatom|plankton|microbe|"
                    r"bacteri|algae|spores?|chloroplast|chromosom|neuron|capillar)\b", re.I)
MOL_W = re.compile(r"\b(molecul|proteins?|helix|helices|dna|rna|polymer|lipid|enzyme|"
                   r"amino|peptide|ribosom|collagen|cellulose|capsid|microtubule)\b", re.I)
LIFE_W = re.compile(r"\b(moths?|fish|birds?|herons?|beetles?|jell(y|ies)|whales?|butterfl|"
                    r"bees?|snails?|frogs?|coral|anemone|moss|lichen|fern|leaf|leaves|"
                    r"flower|tree|forest|garden|reef|kelp|fungi|mushroom|plankton|pollen|"
                    r"feather|wing|gill|bone|shell)\b", re.I)
ORGANISM_KINDS = re.compile(r"\b(fish|crabs?|urchins?|anemones?|gobies|shrimp|snails?|"
                            r"beetles?|ants?|bees?|moths?|butterfl\w*|birds?|herons?|"
                            r"gulls?|owls?|frogs?|newts?|lizards?|ferns?|mosses|moss|"
                            r"lichens?|fungi|mushrooms?|kelp|corals?|sponges?|worms?|"
                            r"spiders?|dragonfl\w*|minnows?|tadpoles?|grazers?|deer|"
                            r"foxes|voles?|jays?|finch\w*)\b", re.I)
STOP = set("""a an the of in on and to with over under through across into from at by for
its their is are was were be been very each every all no not this that these those it as
out up down far near seen lit one two like them there where when while just still""".split())


def band(e):
    for lo, hi, name in BANDS:
        if lo <= e < hi:
            return name
    return "off-scale"


def load_cards():
    specs, cards = {}, []
    for name in sorted(pl.journey_names()):
        s = json.loads(pl.journey_path(name).read_text(encoding="utf-8"))
        if not (s.get("registers") and "scene" in s["registers"][0]):
            continue
        specs[name] = s
        for r in s["registers"]:
            if isinstance(r.get("exp"), (int, float)):
                cards.append({"j": name, "exp": r["exp"], "band": band(r["exp"]),
                              "text": (r.get("scene", "") + " " + r.get("target", ""))})
    return specs, cards


def analyze():
    specs, cards = load_cards()
    bc = Counter(c["band"] for c in cards)
    # fidelity: journeys with LIVING upper cards whose deep cards never go cellular/molecular
    broken_bio = []
    for j, s in specs.items():
        jc = [c for c in cards if c["j"] == j]
        living = any(LIFE_W.search(c["text"]) for c in jc if c["exp"] > -3.5)
        deep = [c for c in jc if -8.5 <= c["exp"] < -3.5]
        if living and deep and not any(CELL_W.search(c["text"]) or MOL_W.search(c["text"])
                                       for c in deep):
            broken_bio.append(j)
    mol_cards = [c for c in cards if c["band"] in ("molecular", "atomic")]
    mol_ok = sum(1 for c in mol_cards if MOL_W.search(c["text"]))
    # motif monoculture
    df = Counter()
    for j in specs:
        seen = set()
        for c in cards:
            if c["j"] == j:
                seen.update(w for w in re.findall(r"[a-z]+", c["text"].lower())
                            if w not in STOP and len(w) > 3)
        for w in seen:
            df[w] += 1
    overused = [(w, n) for w, n in df.most_common(40) if n >= len(specs) * 0.55][:15]
    # population: human-band cards naming >=3 organism kinds
    hum = [c for c in cards if c["band"] == "human"]
    pop = sum(1 for c in hum if len(set(m.group(0).lower()
              for m in ORGANISM_KINDS.finditer(c["text"]))) >= 3)
    return specs, cards, bc, broken_bio, (mol_ok, len(mol_cards)), overused, (pop, len(hum))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", action="store_true", help="compact report for the refill prompt")
    a = ap.parse_args()
    specs, cards, bc, broken_bio, (mok, mtot), overused, (pop, hum) = analyze()

    lines = []
    lines.append(f"CATALOG NOVELTY REPORT — {len(specs)} journeys, {len(cards)} cards")
    order = {name: i for i, (_, _, name) in enumerate(BANDS)}
    cov = "  band coverage: " + " · ".join(
        f"{name} {bc.get(name, 0)}" for _, _, name in BANDS)
    lines.append(cov)
    under = [name for _, _, name in BANDS if bc.get(name, 0) < len(specs) * 0.35]
    lines.append(f"  UNDER-BUILT bands (novelty is cheap here): {', '.join(under)}")
    lines.append(f"  molecular machinery: {mok}/{mtot} molecular/atomic cards show any "
                 f"(REALMS.md molecular band is the emptiest spectacular realm)")
    lines.append(f"  broken continuation (living dive, no cellular/molecular interior): "
                 f"{', '.join(broken_bio) or 'none'}")
    lines.append("  overused words (in >55% of journeys — avoid leaning on these): "
                 + ", ".join(w for w, _ in overused))
    lines.append(f"  populated ecosystem cards (>=3 named kinds) at human scale: {pop}/{hum}")
    # PLANET MOTIF (Phil 2026-10-04: "the planet looks very similar in a lot of videos — a grey
    # cloud hurricane pair"): the card AFTER a planet-class target is the world the plate paints;
    # count how many of them are storm/cloud worlds and name the unused planetary archetypes
    _storm = re.compile(r"storm|cyclone|hurricane|spiral|cloud", re.I)
    _pl_cards, _pl_storm = 0, 0
    for j, s in specs.items():
        regs = s["registers"]; m = len(regs)
        for i, r in enumerate(regs):
            nxt = regs[(i + 1) % m]
            if pl.is_planet_card(r, nxt):
                _pl_cards += 1
                if _storm.search(nxt.get("scene", "")):
                    _pl_storm += 1
    if _pl_cards:
        lines.append(f"  PLANET MOTIF: {_pl_storm}/{_pl_cards} planet cards are storm/cloud-spiral worlds — "
                     "a pair of grey hurricanes is now the house planet; draw the planetary band's OTHER "
                     "archetypes (REALMS.md 10^4.5-10^9: ringed, ice-moon geysers, lava crack-veins, "
                     "cratered highlands, night-side city lights, aurora oval, polar cap, tiger bush, "
                     "open-cell cloud honeycomb, lava-lake eye) and name the world's COLOUR")
    # STAGE VARIETY (2026-10-05): the kits the auto-stager would draw for the catalog's micro
    # cards and the per-journey looks — so the refill can see a monoculture forming
    try:
        sys.path.insert(0, str(pl.ROOT / "engine"))
        import stage as _stage
        from collections import Counter as _C
        kits, looks = _C(), _C()
        for j, s in specs.items():
            looks[s.get("stage_look") or _stage.draw_look(s.get("scaffold_name") or s.get("name") or j)] += 1
            for r in s["registers"]:
                sg = _stage.suggest_stage(r, seed_key=s.get("name") or j)
                if sg:
                    kits[sg["kit"] + ("/" + sg["variant"] if sg.get("variant") else "")] += 1
        lines.append("  STAGE kits over the catalog: " + ", ".join(f"{k} {n}" for k, n in kits.most_common()))
        lines.append("  STAGE looks per journey: " + ", ".join(f"{k} {n}" for k, n in looks.most_common())
                     + " (a journey may set `stage_look`; a card may set `stage: {kit, look}`)")
    except Exception as e:  # the audit must never fail on the stage module
        lines.append(f"  STAGE variety: n/a ({e})")
    print("\n".join(lines))
    if not a.brief:
        print("\nper-band journey lists:")
        for _, _, name in BANDS:
            js = sorted({c['j'] for c in cards if c['band'] == name})
            print(f"  {name:12} ({bc.get(name, 0):3}): {', '.join(js[:14])}"
                  + (" …" if len(js) > 14 else ""))


if __name__ == "__main__":
    main()
