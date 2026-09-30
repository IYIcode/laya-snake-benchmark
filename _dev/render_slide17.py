# -*- coding: utf-8 -*-
"""把「邀请二维码 + 邀请链接」合成进视频用的第 17 页截图。

与 laya-ppt.html 第 17 页改动保持一致：
  · 底部欢迎行改成「欢迎扫码或点链接注册试用 Qoder —— 让我能多蹬一会儿」，下面补一行完整链接
  · 右图（phone_night.png，截图里位于 x918..1167 / y126..612）右下角贴二维码白卡
    （HTML 里是 position:absolute;right:8px;bottom:10px;width:147px;padding:6px，即 135px 码 + 6px 白边）
产物：_ppt_video4/slide17_invite.png
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "_ppt_video" / "slide17.png"
QR = ROOT / "_ppt_video4" / "qoder_qr_135.png"
OUT = ROOT / "_ppt_video4" / "slide17_invite.png"
URL = "https://qoder.cn/activities?referral_code=Ykkr49CgiCQpI8fijiiXU4MdTVt8Z4uX"

BG = (11, 14, 20)
FG = (232, 237, 245)
GOLD = (240, 180, 41)
BLUE = (90, 167, 240)

IMG_RECT = (918, 126, 1167, 612)      # 右图（phone_night.png）在截图中的位置
CARD = 147                            # 白卡 147 = 135 码 + 6×2 白边
INSET_R, INSET_B = 8, 10              # 与 HTML 的 right/bottom 一致

F_TXT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 21)
F_BOLD = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 21)
F_MONO = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 15)


def main():
    im = Image.open(BASE).convert("RGB")
    d = ImageDraw.Draw(im)

    # 1) 抹掉旧欢迎行（"…邀请码 u9nr6jcf…"）
    d.rectangle([30, 606, 910, 692], fill=BG)

    # 2) 新欢迎行 + 链接行
    x, y = 40, 617
    for txt, font, col in (("欢迎扫码或点链接注册试用 ", F_TXT, FG),
                           ("Qoder", F_BOLD, GOLD),
                           (" —— 让我能多蹬一会儿", F_TXT, FG)):
        d.text((x, y), txt, font=font, fill=col)
        x += d.textlength(txt, font=font)
    d.text((40, 650), URL, font=F_MONO, fill=BLUE)

    # 3) 右图右下角贴二维码白卡
    x1, y1, x2, y2 = IMG_RECT
    cx2, cy2 = x2 - INSET_R, y2 - INSET_B
    cx1, cy1 = cx2 - CARD, cy2 - CARD
    d.rounded_rectangle([cx1 + 3, cy1 + 5, cx2 + 3, cy2 + 5], 12, fill=(4, 6, 9))     # 淡阴影
    d.rounded_rectangle([cx1, cy1, cx2, cy2], 12, fill=(255, 255, 255))
    qr = Image.open(QR).convert("RGB")
    im.paste(qr, (cx1 + 6, cy1 + 6))
    im.save(OUT)
    print(f"→ {OUT.relative_to(ROOT)}   二维码白卡 {CARD}×{CARD} @ ({cx1},{cy1})   链接行 x40..{40 + int(d.textlength(URL, font=F_MONO))}")


if __name__ == "__main__":
    main()
