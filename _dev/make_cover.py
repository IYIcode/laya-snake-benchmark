# -*- coding: utf-8 -*-
"""生成 B 站投稿封面（1920×1080，16:9）：五路实况画面 + 底部渐变压暗 + 标题大字。

产物：_dev/bili_cover.png
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_dev" / "final_check" / "v3_tableau.png"      # 五路同屏定格（来自成片抽帧）
OUT = ROOT / "_dev" / "bili_cover.png"
W, H = 1920, 1080
FG = (232, 237, 245)
GOLD = (240, 180, 41)
DIM = (170, 182, 200)

F_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 86)
F_SUB = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 46)
F_TAG = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 32)


def gradient_mask():
    m = Image.new("L", (1, H))
    for y in range(H):
        t = max(0.0, (y - H * 0.42) / (H * 0.58))       # 下方 58% 逐渐压暗
        m.putpixel((0, y), int(235 * min(1.0, t ** 0.85)))
    return m.resize((W, H))


def main():
    src = Image.open(SRC).convert("RGB")
    # 只取"页头 + 五块棋盘"这一段（y 0..540），放大铺满上半部分，下半部分留干净暗底写字
    top = src.crop((0, 0, src.width, 540)).resize((W, 810), Image.LANCZOS)
    im = Image.new("RGB", (W, H), (6, 9, 14))
    im.paste(top, (0, 0))
    d = ImageDraw.Draw(im)

    d.rounded_rectangle([86, 852, 92, 912], 3, fill=GOLD)
    d.text((116, 838), "Jev 的平替 Laya，能否干活？", font=F_TITLE, fill=FG)
    d.text((118, 944), "一条贪吃蛇：从 0 分到 141 分通关", font=F_SUB, fill=GOLD)
    d.text((120, 1012), "五路选手同台实况 · 全部数字来自真跑日志", font=F_TAG, fill=DIM)

    im.save(OUT)
    print(f"→ {OUT.relative_to(ROOT)}  {im.size[0]}×{im.size[1]}")


if __name__ == "__main__":
    main()
