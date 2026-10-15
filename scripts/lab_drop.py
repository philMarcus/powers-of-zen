#!/usr/bin/env python3
"""Drop a lab file (clip / strip / sheet) into review/lab/ for the dashboard's 🧪 Lab tab (Phil 2026-10-15: "I can't
open the review folder while I'm at work on my laptop... a lab tab where you can drop current files for review").
Whole videos keep going to Video Review; this is for side-by-sides, strips and sheets.
usage: lab_drop.py <file> --title "..." [--note "..."]      copy + list (newest first)
       lab_drop.py --remove <name>                            drop an entry from the list (file kept)
       lab_drop.py --list                                     print the manifest (incl. Phil's verdicts)"""
import sys, json, shutil, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "review" / "lab"
MAN = LAB / "lab.json"


def load():
    try:
        return json.loads(MAN.read_text(encoding="utf-8"))
    except Exception:
        return []


def save(entries):
    LAB.mkdir(parents=True, exist_ok=True)
    tmp = MAN.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(MAN)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--title", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--remove")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    entries = load()
    if a.list:
        for e in entries:
            print(f"{e['added']}  {e['file']:36s} {e.get('title','')}" + (f"\n      VERDICT: {e['verdict']}" if e.get("verdict") else ""))
        return
    if a.remove:
        entries = [e for e in entries if e["file"] != a.remove]
        save(entries); print(f"removed {a.remove} from the list"); return
    if not a.file:
        ap.error("a file (or --list / --remove) is required")
    src = Path(a.file)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        sys.exit(f"no such file: {src}")
    LAB.mkdir(parents=True, exist_ok=True)
    dst = LAB / src.name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    entries = [e for e in entries if e["file"] != dst.name]
    entries.insert(0, {"file": dst.name, "title": a.title or dst.stem, "note": a.note,
                       "added": time.strftime("%Y-%m-%d %H:%M"), "kind": "video" if dst.suffix.lower() in (".mp4", ".webm", ".mov") else "image"})
    save(entries)
    print(f"lab <- {dst.name}  ({a.title})")


if __name__ == "__main__":
    main()
