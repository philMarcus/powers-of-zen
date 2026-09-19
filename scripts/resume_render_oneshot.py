#!/usr/bin/env python3
"""ONE-SHOT: re-enable nightly renders after a single manually-skipped night, then delete
its own scheduled task. Created 2026-09-04 (Phil freed ComfyUI for another project for one
night; only the 09-05 01:30 render was skipped). Safe to delete after it fires."""
import subprocess, sys
sys.path.insert(0, "scripts")
import pipeline as pl
jd = pl.jload(); jd["settings"]["render_paused"] = False; pl.jsave(jd)
pl.telem("batch_resume", detail="one-shot auto-resume after skipped night 2026-09-05")
print("render_paused -> False")
subprocess.run(["schtasks.exe", "/Delete", "/TN", "PowersOfZen-render-resume", "/F"])
