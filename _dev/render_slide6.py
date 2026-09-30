# -*- coding: utf-8 -*-
"""让「考场」页（slide06）左边那块小棋盘真的动起来。

laya-ppt.html 第 6 页标题写着"左边的蛇正在环游，是活的"，但那是一段 canvas 动画
（脚本末尾的 #mini 段：沿哈密顿环一步一格、150ms 一步、吃到食物加分长个儿）。
静态截图做成的视频里它是死的，所以这里把同一段逻辑（逐行照抄 HTML）重画出来，
再按原位置/原缩放合成回 slide06.png，逐帧输出。

    python _dev/render_slide6.py             # 全量渲染 + 编码 slide6_v.mp4
    python _dev/render_slide6.py --preview 3,8,15
"""
import json, math, pathlib, subprocess, sys, time

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

OUT = ROOT / "_ppt_video4"
FRAMES = OUT / "slide6_frames"
BASE = ROOT / "_ppt_video" / "slide06.png"
AUDIO = ROOT / "_ppt_audio4" / "q03.mp3"
GAP = 0.25
FPS = 25

# 原页里 #mini 画布的位置：border-box 300x300 画在 (40,230)，1px 边框+12px 圆角+border-box，
# 所以画布位图（300x300）被 CSS 缩放到 298x298，内容区从 (41,231) 开始。
BOX = (41, 231, 298)          # x, y, size
RADIUS = 11                   # 内侧圆角 = 12px - 1px 边框
C = 25                        # 画布里每格 25px（与 HTML 的 C=25 一致）

FONT_LBL = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)


def audio_duration():
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(AUDIO)], capture_output=True, text=True)
    return float(r.stdout.strip())


TOTAL = audio_duration() + GAP
NFRAMES = int(math.ceil(TOTAL * FPS))
STEP_S = 0.150                # HTML: setInterval(...,150)


def cidx(x, y):
    if y == 0:
        return 0 if x == 0 else 133 + (11 - x)
    s = 1 + 11 * x
    return s + (y - 1) if x % 2 == 0 else s + (11 - y)


CELLS = [None] * 144
for _y in range(12):
    for _x in range(12):
        CELLS[cidx(_x, _y)] = (_x, _y)


class Mini:
    """逐行对齐 HTML 的 #mini 动画状态机"""

    def __init__(self):
        self.head = 0
        self.length = 6
        self.score = 0
        self.food = (self.head + 20) % 144

    def step(self):
        self.head = (self.head + 1) % 144
        if self.head == self.food:
            self.score += 1
            self.length = min(self.length + 1, 60)
            while True:
                self.food = (self.food + 7 + self.score * 3) % 144
                if ((self.food - self.head) + 144) % 144 >= 6:
                    break
            if self.score >= 40:
                self.score = 0
                self.length = 6
        else:
            self.length = max(6, self.length)

    def draw(self):
        im = Image.new("RGB", (300, 300), (13, 17, 25))     # #0d1119
        d = ImageDraw.Draw(im)
        for i in range(1, 12):                              # 网格 #1c2432
            d.line([(i * C, 0), (i * C, 300)], fill=(28, 36, 50))
            d.line([(0, i * C), (300, i * C)], fill=(28, 36, 50))
        fx, fy = CELLS[self.food]                           # 食物 #f0b429，半径随 head 呼吸
        r = 8 + (self.head % 2)
        d.ellipse([fx * C + 12.5 - r, fy * C + 12.5 - r, fx * C + 12.5 + r, fy * C + 12.5 + r], fill=(240, 180, 41))
        for i in range(self.length - 1, 0, -1):             # 蛇身：尾一节 #2e86c8，其余 #3ecf8e
            bx, by = CELLS[(self.head - i + 144) % 144]
            d.rectangle([bx * C + 2, by * C + 2, bx * C + C - 4, by * C + C - 4],
                        fill=(46, 134, 200) if i == self.length - 1 else (62, 207, 142))
        hx, hy = CELLS[self.head]                           # 蛇头 #e8edf5
        d.rectangle([hx * C + 2, hy * C + 2, hx * C + C - 4, hy * C + C - 4], fill=(232, 237, 245))
        d.text((8, 292), f"得分 {self.score} · 长度 {self.length}",     # canvas fillText：y 是基线
               font=FONT_LBL, fill=(139, 151, 171), anchor="ls")
        return im


def mask():
    m = Image.new("L", (BOX[2], BOX[2]), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, BOX[2] - 1, BOX[2] - 1], RADIUS, fill=255)
    return m


def render_frame(base, mini, mask_img):
    board = mini.draw().resize((BOX[2], BOX[2]), Image.LANCZOS)
    im = base.copy()
    im.paste(board, (BOX[0], BOX[1]), mask_img)
    return im


def encode_video():
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS),
                    "-start_number", "0", "-i", str(FRAMES / "f%05d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), str(OUT / "slide6_v.mp4")], check=True)


if __name__ == "__main__":
    base = Image.open(BASE).convert("RGB")
    m = mask()
    args = sys.argv[1:]
    if args and args[0] == "--preview":
        for ts in args[1].split(","):
            t = float(ts)
            mini = Mini()
            for _ in range(int(t / STEP_S)):
                mini.step()
            p = HERE / f"slide6_preview_{t:04.1f}s.png"
            render_frame(base, mini, m).save(p)
            print(f"preview → {p.name}  得分 {mini.score} 长度 {mini.length} head {mini.head} food {mini.food}")
        sys.exit(0)

    FRAMES.mkdir(parents=True, exist_ok=True)
    mini = Mini()
    t0 = time.time()
    done = 0
    for f in range(NFRAMES):
        want = int((f / FPS) / STEP_S)
        while done < want:
            mini.step()
            done += 1
        render_frame(base, mini, m).save(FRAMES / f"f{f:05d}.png")
    print(f"{NFRAMES} 帧（{NFRAMES/FPS:.2f}s，音频 {audio_duration():.2f}s + 停顿 {GAP}）→ {FRAMES}  "
          f"({time.time()-t0:.1f}s)", flush=True)
    encode_video()
    print("slide6_v.mp4 已生成", flush=True)
