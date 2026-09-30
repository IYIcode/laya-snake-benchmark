# -*- coding: utf-8 -*-
"""重建 3 分钟视频：在「第 4/5 级 · 通关时刻」(slide 11) 之后插入
   「五路选手 · 同台实况」动画段（讲稿第 12 页 驾驶舱），并收紧段间停顿。

   与 _dev/build_video3.sh 的差别：
     - 配音换成 _ppt_audio4/q01..q09（语速 +20%，为插入新段腾出时间）
     - 段间停顿 GAP 0.8s → 0.25s
     - 新增一段真视频（_ppt_video4/lane_v.mp4 + lane_a.wav），其余仍用 _ppt_video/slide*.png
"""
import pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_ppt_video4"
AUDIO = ROOT / "_ppt_audio4"
SLIDES = ROOT / "_ppt_video"
GAP = 0.25
LEAD = 0.50
TAIL_LAST = 3.00      # 最后一段多停 3 秒：让邀请二维码在屏幕上留够扫码时间

# (类型, 音频序号, 幻灯片号[, 覆盖图片名])  —— clip 段为真视频（考场页活棋盘 / 五路实况）
# lane 段插在 slide 11 与 15 之间（讲稿第 12 页 驾驶舱）；最后一段换成带二维码的合成页
MAP = [("slide", 1, 1), ("slide", 2, 4), ("clip", 3, 6, "slide6_v.mp4"), ("slide", 4, 7),
       ("slide", 5, 10), ("slide", 6, 11), ("clip", None, 12, "lane_v.mp4"),
       ("slide", 7, 15), ("slide", 8, 16), ("slide", 9, 17, "slide17_invite.png")]
FINAL = ROOT / "laya-ppt-3分钟.mp4"
BACKUP = ROOT / "_ppt_video3" / "_v1_laya-ppt-3min.mp4"


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("FAILED:", " ".join(str(a) for a in args))
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(1)
    return r


def dur(fn):
    return float(run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(fn)]).stdout.strip())


if FINAL.exists() and not BACKUP.exists():
    BACKUP.parent.mkdir(exist_ok=True)
    shutil.copy2(FINAL, BACKUP)
    print("原片已备份 →", BACKUP.relative_to(ROOT), flush=True)

OUT.mkdir(exist_ok=True)
lst = OUT / "list.txt"
lst.write_text("", encoding="utf-8")
total = 0.0
for i, (kind, n, slide, *rest) in enumerate(MAP, start=1):
    seg = OUT / f"seg{i:02d}.mp4"
    audio = OUT / "lane_a.wav" if n is None else AUDIO / f"q{n:02d}.mp3"
    a_dur = dur(audio)
    is_last = (i == len(MAP))
    pad = GAP + (TAIL_LAST if is_last else 0.0)
    T = a_dur + pad + (LEAD if i == 1 else 0.0)
    if kind == "slide":
        img = (OUT / rest[0]) if rest else (SLIDES / f"slide{slide:02d}.png")
        af = (f"adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad=pad_dur={pad},aresample=44100"
              if i == 1 else f"apad=pad_dur={pad},aresample=44100")
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-loop", "1", "-framerate", "25", "-t", f"{T:.3f}",
             "-i", str(img), "-i", str(audio),
             "-af", af, "-ac", "2", "-ar", "44100", "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
             "-r", "25", "-c:a", "aac", "-b:a", "128k", "-t", f"{T:.3f}", str(seg)])
    else:
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(OUT / rest[0]), "-i", str(audio),
             "-filter_complex",
             f"[0:v]tpad=stop_mode=clone:stop_duration=2,setpts=PTS-STARTPTS,fps=25[v];"
             f"[1:a]apad=pad_dur={pad},aresample=44100,"
             f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
             "-t", f"{T:.3f}", str(seg)])
    got = dur(seg)
    total += got
    with open(lst, "a", encoding="utf-8") as fh:
        fh.write(f"file 'seg{i:02d}.mp4'\n")
    label = f"slide{slide:02d}" if kind == "slide" else f"{rest[0][:-4]}(动画)"
    print(f"seg{i:02d}  {label:>16}  音轨 {a_dur:6.2f}s → 片段 {got:6.2f}s", flush=True)

print(f"片段合计 {total:.2f}s", flush=True)
run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
     "-i", str(lst), "-c", "copy", str(FINAL)])
print(f"成片 {FINAL.name}  {dur(FINAL):.2f}s  ({dur(FINAL)//60:.0f}:{dur(FINAL)%60:04.1f})")
