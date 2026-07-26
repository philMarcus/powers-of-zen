#!/usr/bin/env bash
# Re-render repaired journeys; deposit primary cut into review/ and dive-in
# cut into review_divein/ as each completes.
cd "$(dirname "$0")/.."
render() {
  local j=$1; shift
  local suffix=""
  [ "$2" = "ds" ] && suffix="_ds"
  python3 engine/dive.py "journeys/$j.json" "$@" || { echo "!!! FAILED $j$suffix"; return; }
  local v=$(ls -d "output/$j$suffix"/v* 2>/dev/null | sort -V | tail -1)
  local f="$v/$j$suffix.mp4"
  if [ -f "$f" ]; then
    cp "$f" "review/$j$suffix.mp4"
    cp "$v/$j${suffix}_divein.mp4" "review_divein/$j${suffix}_divein.mp4" 2>/dev/null
    printf "%-24s %6.1f MB   rendered %s   (%s)  [refreshed]\n" "$j$suffix.mp4" \
      "$(echo "scale=1; $(stat -c %s "$f")/1048576" | bc)" \
      "$(stat -c %y "$f" | cut -c6-16)" "$(basename "$v")" >> review/MANIFEST.txt
    echo ">>> review/$j$suffix.mp4 updated"
  fi
}
render cosmic_scales
render cartographer
render mineral_heart
render night_bloom
render cosmic_scales --model ds
render cartographer --model ds
render mineral_heart --model ds
render night_bloom --model ds
render snowfall --model ds
echo "=== re-renders complete ==="
