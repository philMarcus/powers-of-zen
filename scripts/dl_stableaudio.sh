#!/usr/bin/env bash
# Download Stable Audio Open 1.0 (gated) into ComfyUI folders. Waits for ACE-Step
# download to finish first so it doesn't split bandwidth from tonight's priority.
set -e
M=/mnt/c/Users/Phil/ComfyUI/ComfyUI/models
TOK=$(sed -n '1p' /mnt/c/Users/Phil/zoomer/scripts/huggingface_token.txt)
VAE_DONE="$M/vae/ace_1.5_vae.safetensors"
echo "waiting for ACE-Step download to complete..."
for i in $(seq 1 240); do [ -f "$VAE_DONE" ] && [ $(stat -c%s "$VAE_DONE" 2>/dev/null||echo 0) -gt 300000000 ] && break; sleep 15; done
echo "ACE-Step done (or timed out) — starting Stable Audio Open"
BASE=https://huggingface.co/stabilityai/stable-audio-open-1.0/resolve/main
dl(){ echo ">>> $2"; curl -L -C - --retry 5 --retry-delay 5 -H "Authorization: Bearer $TOK" -o "$1" "$2"; }
dl "$M/checkpoints/stable_audio_open_1.0.safetensors" "$BASE/model.safetensors"
dl "$M/text_encoders/t5_base_stableaudio.safetensors" "$BASE/text_encoder/model.safetensors"
echo "=== Stable Audio Open download complete ==="
ls -lh "$M/checkpoints/stable_audio_open_1.0.safetensors" "$M/text_encoders/t5_base_stableaudio.safetensors"
