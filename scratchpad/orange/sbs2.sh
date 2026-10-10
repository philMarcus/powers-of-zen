#!/bin/bash
# side-by-side review cut: plain (left) | staged (right), same seed so frames align.
# usage: sbs.sh <plain_divein.mp4> <staged_divein.mp4> <out.mp4>
FF="/mnt/c/Users/Phil/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe"
L1="${4:-plain}"; L2="${5:-staged}"; A=$(wslpath -w "$1"); B=$(wslpath -w "$2"); O=$(wslpath -w "$3")
"$FF" -y -loglevel error -i "$A" -i "$B" -filter_complex \
 "[0:v]scale=540:960,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='$L1':x=12:y=12:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5[l];[1:v]scale=540:960,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='$L2':x=12:y=12:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5[r];[l][r]hstack=inputs=2[v]" \
 -map "[v]" -an -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "$O" && echo "-> $3"
