#!/usr/bin/env bash
# Download ACE-Step 1.5 ComfyUI-format files (ungated) into ComfyUI model folders.
set -e
M=/mnt/c/Users/Phil/ComfyUI/ComfyUI/models
BASE=https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/main
mkdir -p "$M/diffusion_models" "$M/text_encoders" "$M/vae"
dl(){ echo ">>> $2"; curl -L -C - --retry 5 --retry-delay 5 -o "$1" "$2"; }
dl "$M/diffusion_models/acestep_v1.5_turbo.safetensors"  "$BASE/split_files/diffusion_models/acestep_v1.5_turbo.safetensors"
dl "$M/text_encoders/qwen_0.6b_ace15.safetensors"        "$BASE/split_files/text_encoders/qwen_0.6b_ace15.safetensors"
dl "$M/text_encoders/qwen_1.7b_ace15.safetensors"        "$BASE/split_files/text_encoders/qwen_1.7b_ace15.safetensors"
dl "$M/vae/ace_1.5_vae.safetensors"                      "$BASE/split_files/vae/ace_1.5_vae.safetensors"
echo "=== ACE-Step 1.5 download complete ==="
ls -lh "$M/diffusion_models/acestep_v1.5_turbo.safetensors" "$M/text_encoders/qwen_0.6b_ace15.safetensors" "$M/text_encoders/qwen_1.7b_ace15.safetensors" "$M/vae/ace_1.5_vae.safetensors"
