#!/usr/bin/env bash
set -e
cd <REPO>
GAP=0.8
LEAD=0.6
> _ppt_video/list.txt
for n in $(seq -w 1 17); do
  dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 _ppt_audio/p${n}.mp3)
  if [ "$n" = "01" ]; then G=$(awk "BEGIN{printf \"%.3f\", $GAP+$LEAD}"); else G=$GAP; fi
  T=$(awk "BEGIN{printf \"%.3f\", $dur+$G}")
  if [ "$n" = "01" ]; then AF="adelay=${LEAD}00|${LEAD}00,apad=pad_dur=${GAP},aresample=44100"; else AF="apad=pad_dur=${GAP},aresample=44100"; fi
  ffmpeg -y -hide_banner -loglevel error -loop 1 -framerate 25 -t "$T" -i _ppt_video/slide${n}.png -i _ppt_audio/p${n}.mp3 \
    -af "$AF" -ac 2 -ar 44100 \
    -map 0:v -map 1:a -c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -t "$T" _ppt_video/seg${n}.mp4
  echo "file 'seg${n}.mp4'" >> _ppt_video/list.txt
  echo "seg${n} T=$T"
done
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i _ppt_video/list.txt -c copy "laya-ppt-女声配音.mp4"
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "laya-ppt-女声配音.mp4"
