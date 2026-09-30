# -*- coding: utf-8 -*-
"""① 把 _ppt_video4/lane_frames/*.png 编成无音轨视频
   ② 把 _ppt_audio4/lane/L0x.mp3 按 lane_timeline.json 的时序（前置留白/句间停顿/末尾定格）拼成一条音轨
   产物：_ppt_video4/lane_v.mp4 、_ppt_video4/lane_a.wav
"""
import json, pathlib, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lane_config import FPS  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "_ppt_video4"
FRAMES = OUT / "lane_frames"
LANE_AUDIO = ROOT / "_ppt_audio4" / "lane"
TMP = OUT / "_audio_parts"
TL = json.load(open(HERE / "lane_timeline.json", encoding="utf-8"))
TOTAL = TL["total"]


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(" ".join(str(a) for a in args))
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(1)
    return r


def dur(fn):
    return float(run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(fn)]).stdout.strip())


# ── ① 视频 ──
n_frames = len(list(FRAMES.glob("f*.png")))
print(f"帧数 {n_frames}（{n_frames / FPS:.2f}s）", flush=True)
run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS),
     "-start_number", "0", "-i", str(FRAMES / "f%05d.png"),
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
     "-r", str(FPS), str(OUT / "lane_v.mp4")])
print("lane_v.mp4  %.2fs" % dur(OUT / "lane_v.mp4"), flush=True)

# ── ② 音轨 ──
if TMP.exists():
    shutil.rmtree(TMP)
TMP.mkdir(parents=True)
sil = {}
for name, d in (("lead", TL["lead"]), ("pause", TL["pause"]), ("tail", TL["tail"])):
    p = TMP / f"{name}.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{d:.3f}", "-c:a", "pcm_s16le", str(p)])
    sil[name] = p

parts = [sil["lead"]]
for i, pc in enumerate(TL["pieces"]):
    src = LANE_AUDIO / f"{pc['id']}.mp3"
    p = TMP / f"{pc['id']}.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(p)])
    parts.append(p)
    if i < len(TL["pieces"]) - 1:
        parts.append(sil["pause"])
parts.append(sil["tail"])

lst = TMP / "list.txt"
lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
     "-i", str(lst), "-c", "copy", str(OUT / "lane_a.wav")])
a_dur = dur(OUT / "lane_a.wav")
print(f"lane_a.wav  {a_dur:.2f}s  (时间轴 {TOTAL:.2f}s，差 {a_dur - TOTAL:+.3f}s)", flush=True)
for pc in TL["pieces"]:
    print(f"   {pc['id']}  {pc['start']:6.2f} → {pc['end']:6.2f}  ({pc['dur']:.2f}s) lane={pc['lane']}")
