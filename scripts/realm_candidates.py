#!/usr/bin/env python3
"""Generate realm-reference CANDIDATE images for the IP-Adapter library (Phil curates).

Prompts come from journeys/REALMS.md archetypes, phrased as immersive FIELDS/environments
(a lone centered object is hard to dive through — the 2026-08-02 close-up lesson applies to
refs too); a few deliberate [object] refs are generated for target moments and tagged in
the filename. Writes output/realm_refs/candidates/<band>/<slug>_s<seed>.png.

Usage: python3 scripts/realm_candidates.py [--per 3]  (seeds per archetype, default 2)
"""
import argparse
import sys
import time
from pathlib import Path

import requests

COMFY = "http://localhost:8188"
CFG = 2.0
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "realm_refs" / "candidates"
TAIL = ("glittering specular highlights, iridescent sparkle, vivid complementary colour "
        "contrast, jewel-bright accents, ultra-detailed")
# v2 (Phil's library review 2026-08-13): the composition SCAFFOLD leads every env prompt —
# camera inside, many instances at stochastic depths, big soft occluder crossing the frame
# edge, far ranks into depth fog. No borrowed horizons for interior realms.
SCAFFOLD = ("the view from deep inside, surrounded on all sides, countless {things} "
            "scattered at random depths and sizes, one enormous {thing} passing close by "
            "the camera softly out of focus and cut off by the frame edge, the rest "
            "receding into darkness and depth fog")
NEG = ("text, watermark, logo, blurry, low quality, person, people, human figure, "
       "photo, photograph, realistic, centered product shot, single object, table, "
       "display stand, pedestal, museum, sky, horizon, ground plane, landscape, "
       "specimen photography")

# v2 iteration set — reviewed archetypes rebuilt on the scaffold (kept v1 keepers: cristae,
# mesophyll, diatom_plaza non-table takes, deadwood_city, tidepool_city)
V2 = [
    ("cellular", "wide_capillary2", "deep inside a dark vessel, countless glossy red discs drifting suspended at random depths, one enormous red disc drifting close past the camera softly blurred and cut by the frame edge, dim teal glow far below, cells tumbling in slow current, no ground, no walls visible nearby"),
    ("cellular", "wide_neuron_web", "suspended inside a vast dark web of glowing neurons, dozens of branching dendrite trees connected by thin luminous threads in every direction, one huge blurred dendrite branch crossing the near foreground, tiny synapse sparks flickering at random junctions, the network receding into violet depth fog"),
    ("cellular", "wide_diatom_drift", "adrift among hundreds of ornate glass diatom shells of many different shapes floating at random depths in dark water, one huge pillbox diatom drifting close past the camera softly out of focus, the swarm thinning into deep teal darkness below"),
    ("mineral", "wide_selenite_within", "deep inside a crystal cavern, giant water-clear selenite blades crossing at every angle overhead and below, one massive blurred blade edge cutting across the near foreground, blades receding rank after rank into cold blue darkness, no floor visible"),
    ("mineral", "wide_opal_within", "deep inside precious opal, an endless three-dimensional field of packed glassy micro-spheres glowing with spectral fire between them, spheres drifting past close to the camera softly blurred, the packed field receding into warm darkness"),
    ("atomic", "wide_lattice2", "suspended inside an endless natural crystal lattice, glowing atom nodes in slightly imperfect ranks joined by faint light, a huge blurred node passing close by the camera, rows receding into deep indigo fog in every direction, one row bent around a glowing defect"),
    ("human_eco", "wide_vent_far", "a deep-sea plain with several hydrothermal vent chimneys at different distances venting mineral smoke, swarms of shrimp and ghost fish drifting between them, tube worm colonies crowding each chimney, one blurred shrimp swarm passing close to the camera, abyssal darkness beyond"),
    ("mm", "wide_moss_drift", "inside a towering moss jungle seen from between the stalks, dozens of translucent moss towers hung with glass water droplets at every depth, a huge blurred droplet lens passing close by the camera, a tardigrade lumbering far below, green-gold light failing into darkness"),
]

# (band, slug, prompt) — env-phrased unless slug has 'obj_' prefix
ARCHETYPES = [
    ("cellular", "mesophyll", "inside a vast cathedral of stacked translucent green plant cells, chloroplasts drifting within each cell, walls receding in every direction"),
    ("cellular", "cristae", "deep inside a mitochondrion, endless folded cristae membrane canyons glowing amber and teal"),
    ("cellular", "diatom_plaza", "a wide plaza crowded with ornate diatom glass shells of many shapes, radial pores, deep dark water beyond"),
    ("cellular", "neuron_forest", "a dense forest of branching neurons strung with glowing synapse lights, deep space between the branches"),
    ("cellular", "cell_division", "a vast cell interior mid-division, chromosome ribbons drawn apart by glowing spindle fiber ropes"),
    ("cellular", "capillary_river", "inside a capillary river packed with glossy red blood cells flowing single file between pale vessel walls"),
    ("cellular", "cilia_field", "an endless rippling field of iridescent cilia waving in synchronized waves under dark water"),
    ("molecular", "ribbon_canyon", "a canyon landscape whose cliff walls are folded protein ribbons, looping coiled strata in many colors receding to the horizon"),
    ("molecular", "dna_gorge", "a gorge spanned by enormous glowing DNA double-helix bridges, luminous base-pair rungs, several helices receding into darkness"),
    ("molecular", "membrane_sea", "a rolling sea made of two layers of packed glossy spheres, giant glowing protein turbines embedded through the surface"),
    ("molecular", "microtubule_hall", "a hall of parallel glowing microtubule columns receding into the dark, tiny walker machines climbing them"),
    ("molecular", "obj_ribosome", "one colossal ribosome machine of lumpy interlocked subunits assembling a glowing chain, seen from below against darkness"),
    ("atomic", "lattice_gallery", "inside an endless crystal lattice gallery, glowing atom nodes in perfect ranks joined by light struts, corridors receding every direction"),
    ("atomic", "grain_boundary", "a canyon where two vast crystal lattices meet at an angle, their glowing atom rows clashing along the boundary wall"),
    ("mm", "moss_jungle", "a jungle of towering moss stalks and glass water droplets, a tardigrade lumbering between trunks"),
    ("mm", "snow_growth", "a plain of interlocking snowflakes growing arm by arm, hexagonal crystal spears branching in the blue dark"),
    ("human_eco", "tidepool_city", "a tide pool metropolis teeming with anemones, hermit crabs, urchins, darting gobies and kelp, dark water above"),
    ("human_eco", "kelp_traffic", "inside a towering kelp forest with schools of fish streaming between golden fronds, shafts of deep blue light"),
    ("human_eco", "deadwood_city", "a fallen log city crowded with shelf fungi, moss meadows, beetle galleries and snail traffic, dark forest beyond"),
    ("human_eco", "vent_colony", "a deep-sea hydrothermal vent chimney crowded with tube worms, ghost crabs and shrimp swarms in mineral smoke"),
    ("mineral", "bismuth_terraces", "a terrain of rainbow bismuth hopper terraces, iridescent stairstep canyons receding to the horizon"),
    ("mineral", "opal_field", "inside precious opal, a field of packed glass micro-spheres flashing spectral fire between them"),
    ("mineral", "selenite_forest", "a forest of giant water-clear selenite crystal blades crossing at angles, cave darkness beyond"),
    ("galactic", "lensing_arcs", "a black sky field of warped gravitational lensing arcs bending galaxy light around an unseen mass"),
]


def wf(prompt, seed, prefix):
    return {
        "ck": {"class_type": "CheckpointLoaderSimple",
               "inputs": {"ckpt_name": "dreamshaperXL.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode",
                "inputs": {"clip": ["ck", 1], "text": f"{prompt}, {TAIL}"}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["ck", 1], "text": NEG}},
        "lat": {"class_type": "EmptyLatentImage",
                "inputs": {"width": 832, "height": 1152, "batch_size": 1}},
        "smp": {"class_type": "KSampler",
                "inputs": {"seed": seed, "steps": 12, "cfg": CFG, "sampler_name": "dpmpp_sde",
                           "scheduler": "karras", "denoise": 1.0, "model": ["ck", 0],
                           "positive": ["pos", 0], "negative": ["neg", 0],
                           "latent_image": ["lat", 0]}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["smp", 0], "vae": ["ck", 2]}},
        "sav": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0],
                                                     "filename_prefix": prefix}},
    }


def run_one(band, slug, prompt, seed):
    d = OUT / band
    d.mkdir(parents=True, exist_ok=True)
    r = requests.post(f"{COMFY}/prompt",
                      json={"prompt": wf(prompt, seed, f"realm_cand/{band}_{slug}")},
                      timeout=30)
    if r.status_code >= 400:
        print(f"{band}/{slug} REJECTED: {r.text[:200]}")
        return False
    prid = r.json()["prompt_id"]
    for _ in range(240):
        h = requests.get(f"{COMFY}/history/{prid}", timeout=30).json()
        if prid in h:
            for node in h[prid].get("outputs", {}).values():
                for im in node.get("images", []):
                    v = requests.get(f"{COMFY}/view", params={
                        "filename": im["filename"], "subfolder": im.get("subfolder", ""),
                        "type": im.get("type", "output")}, timeout=60)
                    (d / f"{slug}_s{seed}.png").write_bytes(v.content)
                    return True
        time.sleep(1)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=2, help="seeds per archetype")
    ap.add_argument("--v2", action="store_true", help="run the v2 scaffold iteration set")
    ap.add_argument("--cfg", type=float, default=3.0, help="cfg for v2 (negatives need >2)")
    a = ap.parse_args()
    t0 = time.time()
    n = 0
    todo = V2 if a.v2 else ARCHETYPES
    global CFG
    CFG = a.cfg if a.v2 else 2.0
    for band, slug, prompt in todo:
        for i in range(a.per):
            ok = run_one(band, slug, prompt, 4000 + 97 * i + hash(slug) % 900)
            n += bool(ok)
            print(f"[{n}] {band}/{slug} s{i} {'ok' if ok else 'FAIL'}", flush=True)
    requests.post(f"{COMFY}/free", json={"unload_models": True, "free_memory": True},
                  timeout=10)
    print(f"{n} candidates in {(time.time()-t0)/60:.1f} min -> {OUT}")


if __name__ == "__main__":
    main()
