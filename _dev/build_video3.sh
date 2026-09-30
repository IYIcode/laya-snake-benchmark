#!/usr/bin/env bash
set -e
cd <REPO>
GAP=0.8
LEAD=0.6
MAP="1:1 2:4 3:6 4:7 5:10 6:11 7:15 8:16 9:17"
mkdir -p _ppt_video3
> _ppt_video3/list.txt
for pair in $MAP; do
  n=${pair%%:*}; s=${pair##*:}
  nn=$(printf "%02d" "$n"); ss=$(printf "%02d" "$s")
  dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 _ppt_audio3/q${nn}.mp3)
  if [ "$n" = "1" ]; then G=$(awk "BEGIN{printf \"%.3f\", $GAP+$LEAD}"); else G=$GAP; fi
  T=$(awk "BEGIN{printf \"%.3f\", $dur+$G}")
  if [ "$n" = "1" ]; then AF="adelay=${LEAD}00|${LEAD}00,apad=pad_dur=${GAP},aresample=44100"; else AF="apad=pad_dur=${GAP},aresample=44100"; fi
  ffmpeg -y -hide_banner -loglevel error -loop 1 -framerate 25 -t "$T" -i _ppt_video/slide${ss}.png -i _ppt_audio3/q${nn}.mp3 \
    -af "$AF" -ac 2 -ar 44100 \
    -map 0:v -map 1:a -c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -t "$T" _ppt_video3/seg${nn}.mp4
  echo "file 'seg${nn}.mp4'" >> _ppt_video3/list.txt
  echo "seg${nn} (slide ${ss}) T=$T"
done
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i _ppt_video3/list.txt -c copy "laya-ppt-3分钟.mp4"
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "laya-ppt-3分钟.mp4"
