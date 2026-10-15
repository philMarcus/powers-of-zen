#!/bin/bash
# BEFORE / AFTER of the pre-roll pickup with an audible CLICK on every bar line (Phil: "I would like to see a
# before/after of the music fix"). Left = today's pre-roll (valdes_blow v2 frames 128..223, cards 4-6), right =
# the pickup arm's frames; 12 fps; a 1 kHz click (60 ms) at t = 0, 2.667, 5.333, 8.0 s = frames 128/160/192/224
# (the bar lines; 160 and 192 are the staged handoffs); looped x3.
# usage: beat_clip.sh <arm_frames_dir> [out.mp4]
cd /mnt/c/Users/Phil/zoomer
FF="/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe"
A=$(wslpath -w output/valdes_blow/v2/build/frames)
B=$(wslpath -w "$1")
OUT=${2:-review/lab/beat_before_after.mp4}
mkdir -p review/lab
O=$(wslpath -w "$OUT")
N=96   # frames 128..223
"$FF" -y -loglevel error \
  -framerate 12 -start_number 128 -i "$A\\%05d.png" \
  -framerate 12 -start_number 128 -i "$B\\%05d.png" \
  -f lavfi -i "aevalsrc=0.5*sin(2*PI*1000*t)*lt(mod(t\,2.6666667)\,0.06):s=48000:d=8" \
  -filter_complex "[0:v]trim=end_frame=$N,setpts=PTS-STARTPTS,scale=432:768[a];[1:v]trim=end_frame=$N,setpts=PTS-STARTPTS,scale=432:768[b];[a][b]hstack=inputs=2,loop=loop=2:size=$N:start=0[v];[2:a]aloop=loop=2:size=384000[au]" \
  -map "[v]" -map "[au]" -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac -b:a 128k -shortest "$O"
echo "clip -> $OUT"
