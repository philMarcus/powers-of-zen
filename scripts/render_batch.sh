#!/usr/bin/env bash
# Thin wrapper kept for muscle memory — the batch now lives in scripts/night_batch.py
# (auto-picks from the journey queue when called with no args; pass journey names to
# render exactly those). Same per-journey flow: render -> queue_review -> caption.
cd "$(dirname "$0")/.." && exec python3 scripts/night_batch.py "$@"
