#!/usr/bin/env python3
"""POC: can Florence-2 localize the object we want to zoom into? Runs caption_to_phrase_grounding
on real render frames and saves Florence's annotated output (boxes drawn) so we can eyeball whether
it reliably finds "the planet" / "one animal" etc. First run downloads the Florence-2 weights.

Usage: python3 scripts/florence_probe.py <journey_model_dir> <query> <frame> [frame ...]
"""
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "engine")
import dive  # noqa: E402
from PIL import Image  # noqa: E402

COMFY = dive.COMFY
MODEL = "microsoft/Florence-2-base-ft"
OUT = Path("/tmp/claude-0/-mnt-c-Users-Phil-zoomer/bcbde943-89be-485d-a581-0eb08e40ff22/scratchpad/florence")
OUT.mkdir(parents=True, exist_ok=True)


def submit(wf):
    data = json.dumps({"prompt": wf}).encode()
    r = urllib.request.urlopen(urllib.request.Request(COMFY + "/prompt", data,
                                                      {"Content-Type": "application/json"}), timeout=30)
    return json.loads(r.read())["prompt_id"]


def wait(pid, timeout=600):
    end = time.time() + timeout
    while time.time() < end:
        try:
            h = json.load(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=10))
        except Exception:
            h = {}
        if pid in h and h[pid].get("outputs"):
            return h[pid]
        time.sleep(2)
    return None


def fetch_image(im):
    url = (f"{COMFY}/view?filename={urllib.parse.quote(im['filename'])}"
           f"&subfolder={urllib.parse.quote(im.get('subfolder',''))}&type={im['type']}")
    return urllib.request.urlopen(url, timeout=30).read()


def workflow(img_name, query):
    return {
        "load": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "flm": {"class_type": "DownloadAndLoadFlorence2Model",
                "inputs": {"model": MODEL, "precision": "fp16"}},
        "run": {"class_type": "Florence2Run",
                "inputs": {"image": ["load", 0], "florence2_model": ["flm", 0],
                           "text_input": query, "task": "caption_to_phrase_grounding",
                           "fill_mask": True, "keep_model_loaded": True,
                           "max_new_tokens": 512, "num_beams": 3, "do_sample": False,
                           "output_mask_select": "", "seed": 1}},
        "save": {"class_type": "SaveImage",
                 "inputs": {"images": ["run", 0], "filename_prefix": "florence_poc"}},
    }


def main():
    src = Path(sys.argv[1]); query = sys.argv[2]; frames = [int(x) for x in sys.argv[3:]]
    print(f"Florence-2 ({MODEL}) grounding '{query}' on {len(frames)} frame(s) from {src}\n")
    for fi in frames:
        p = src / f"{fi:05d}.png"
        if not p.exists():
            print(f"  frame {fi}: MISSING {p}"); continue
        name = dive.upload_image(Image.open(p).convert("RGB"), f"flprobe_{fi}.png")
        t0 = time.time()
        hist = wait(submit(workflow(name, query)))
        if not hist:
            print(f"  frame {fi}: no result (timeout)"); continue
        outs = hist["outputs"]
        # text output (caption/data) — dump whatever the Florence2Run node returned
        txt = ""
        for nid, o in outs.items():
            for key in ("caption", "data", "text", "string"):
                if key in o:
                    v = o[key]
                    txt = v[0] if isinstance(v, list) and v else str(v)
        # annotated image
        saved = None
        for nid, o in outs.items():
            if o.get("images"):
                b = fetch_image(o["images"][0])
                saved = OUT / f"frame{fi:05d}_{query.replace(' ','_')}.png"
                saved.write_bytes(b)
        print(f"  frame {fi:>3} ({time.time()-t0:4.0f}s): boxes/data = {txt[:120] or '(none in history)'}")
        if saved:
            print(f"           annotated -> {saved}")


if __name__ == "__main__":
    main()
