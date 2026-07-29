#!/usr/bin/env python3
"""Powers of Zen — custom music generation via ComfyUI's native ACE-Step 1.5 nodes.

Reuses the same ComfyUI API that engine/dive.py drives for images (no extra service,
no standalone torch env). Builds the ACE-Step 1.5 *turbo* text-to-music graph
(UNETLoader -> ModelSamplingAuraFlow(shift=3) -> KSampler steps=8/cfg=1 euler/simple),
generates an instrumental bed matched to a journey's mood, and writes an .mp3/.flac.

Muxing into the video (with loop-seam fades and optional phase-dynamic volume) is done
by scripts/score.py, which calls generate() here.

Usage:
  python3 engine/music.py night_bloom --duration 27 --out output/music/night_bloom.flac
  python3 engine/music.py --tags "ambient, dreamy" --bpm 90 --key "A minor" --duration 27 \
                          --out output/music/test.flac
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

COMFY = "http://localhost:8188"
ROOT = Path(__file__).resolve().parent.parent

# Per-journey music direction. tags = genre/instrumentation/mood (ACE-Step reads these);
# lyrics "[inst]" keeps it instrumental. bpm/key shape the groove. Keep them atmospheric
# and hypnotic — these are beds under a silent-friendly visual, not songs.
PRESETS = {
    "night_bloom": {
        "tags": ("ambient electronic, bioluminescent, ethereal dream pop, hypnotic, "
                 "glassy synth arpeggio, warm analog pads, deep sub bass pulse, "
                 "soft mallet plucks, nocturnal, underwater shimmer, oddly satisfying, "
                 "cinematic, slow hypnotic build, spacious reverb, instrumental, no vocals"),
        "bpm": 90, "key": "A minor",
    },
    # generic fallback used for any journey without a preset
    "_default": {
        "tags": ("ambient electronic, hypnotic, cinematic, ethereal pads, arpeggiated "
                 "synth, deep sub bass, oddly satisfying, spacious reverb, slow build, "
                 "instrumental, no vocals"),
        "bpm": 90, "key": "A minor",
    },
}


def build_workflow(tags, bpm, key, duration, seed, steps=8, lyrics="[inst]",
                   prefix="zen_music/track"):
    """ACE-Step 1.5 turbo text-to-music graph in ComfyUI API format.
    Mirrors the bundled `audio_ace_step_1_5_split` template exactly."""
    return {
        "unet": {"class_type": "UNETLoader",
                 "inputs": {"unet_name": "acestep_v1.5_turbo.safetensors",
                            "weight_dtype": "default"}},
        "clip": {"class_type": "DualCLIPLoader",
                 "inputs": {"clip_name1": "qwen_0.6b_ace15.safetensors",
                            "clip_name2": "qwen_1.7b_ace15.safetensors",
                            "type": "ace"}},
        "vae": {"class_type": "VAELoader",
                "inputs": {"vae_name": "ace_1.5_vae.safetensors"}},
        "shift": {"class_type": "ModelSamplingAuraFlow",
                  "inputs": {"model": ["unet", 0], "shift": 3.0}},
        "pos": {"class_type": "TextEncodeAceStepAudio1.5",
                "inputs": {"clip": ["clip", 0], "tags": tags, "lyrics": lyrics,
                           "seed": seed, "bpm": bpm, "duration": float(duration),
                           "timesignature": "4", "language": "en", "keyscale": key,
                           "generate_audio_codes": True, "cfg_scale": 2.0,
                           "temperature": 0.85, "top_p": 0.9, "top_k": 0, "min_p": 0.0}},
        "neg": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["pos", 0]}},
        "latent": {"class_type": "EmptyAceStep1.5LatentAudio",
                   "inputs": {"seconds": float(duration), "batch_size": 1}},
        "sample": {"class_type": "KSampler",
                   "inputs": {"seed": seed, "steps": steps, "cfg": 1.0,
                              "sampler_name": "euler", "scheduler": "simple",
                              "denoise": 1.0, "model": ["shift", 0],
                              "positive": ["pos", 0], "negative": ["neg", 0],
                              "latent_image": ["latent", 0]}},
        "decode": {"class_type": "VAEDecodeAudio",
                   "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveAudio",
                 "inputs": {"audio": ["decode", 0], "filename_prefix": prefix}},
    }


def run_workflow(wf, timeout=600):
    """Queue an audio workflow, wait, return (audio_bytes, filename)."""
    r = requests.post(f"{COMFY}/prompt", json={"prompt": wf}, timeout=30)
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=30).json()
        if pid in h:
            status = h[pid].get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error: {json.dumps(status)[:2000]}")
            for node in h[pid].get("outputs", {}).values():
                for a in node.get("audio", []):
                    v = requests.get(f"{COMFY}/view", params={
                        "filename": a["filename"], "subfolder": a.get("subfolder", ""),
                        "type": a.get("type", "output")}, timeout=120)
                    v.raise_for_status()
                    return v.content, a["filename"]
        time.sleep(0.5)
    raise TimeoutError(f"music workflow {pid} did not finish in {timeout}s")


def generate(journey=None, tags=None, bpm=None, key=None, duration=27.0, seed=31,
             steps=8, out=None):
    """Generate a track. Journey pulls a preset; explicit tags/bpm/key override it."""
    spec = PRESETS.get(journey or "", PRESETS["_default"])
    tags = tags or spec["tags"]
    bpm = bpm or spec["bpm"]
    key = key or spec["key"]
    prefix = f"zen_music/{journey or 'track'}"
    wf = build_workflow(tags, bpm, key, duration, seed, steps=steps, prefix=prefix)
    print(f"♪ generating {duration:.1f}s | {bpm}bpm {key} | seed {seed} steps {steps}\n"
          f"  tags: {tags[:90]}...")
    t0 = time.time()
    audio, fname = run_workflow(wf)
    print(f"  done in {time.time() - t0:.0f}s -> {fname} ({len(audio)/1e6:.1f} MB)")
    if out:
        outp = Path(out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_bytes(audio)
        print(f"  saved {outp}")
        return str(outp)
    return audio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journey", nargs="?", help="journey name (pulls a preset)")
    ap.add_argument("--tags"); ap.add_argument("--bpm", type=int)
    ap.add_argument("--key"); ap.add_argument("--duration", type=float, default=27.0)
    ap.add_argument("--seed", type=int, default=31); ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or f"output/music/{a.journey or 'track'}_{a.seed}.flac"
    generate(journey=a.journey, tags=a.tags, bpm=a.bpm, key=a.key, duration=a.duration,
             seed=a.seed, steps=a.steps, out=str(ROOT / out) if not Path(out).is_absolute() else out)


if __name__ == "__main__":
    main()
