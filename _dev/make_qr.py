# -*- coding: utf-8 -*-
"""生成 Qoder 邀请链接二维码（白底深色模块，模块整数倍缩放保证锐利）。

   产物：
     _ppt_imgs/qoder_qr.png          360px —— 给 laya-ppt.html 第 17 页用
     _ppt_video4/qoder_qr_135.png    135px —— 给视频第 17 页合成用（45 模块 × 3px）
"""
import pathlib

import qrcode
from PIL import Image, ImageDraw
from qrcode.constants import ERROR_CORRECT_Q

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://qoder.cn/activities?referral_code=Ykkr49CgiCQpI8fijiiXU4MdTVt8Z4uX"
FG = (11, 14, 20)          # 深色模块（贴近 PPT 底色，白底上依然高对比）
BG = (255, 255, 255)


def matrix():
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=2, box_size=1)
    qr.add_data(URL)
    qr.make(fit=True)
    return qr.get_matrix()


def render(m, scale):
    n = len(m)
    im = Image.new("RGB", (n * scale, n * scale), BG)
    d = ImageDraw.Draw(im)
    for y, row in enumerate(m):
        for x, v in enumerate(row):
            if v:
                d.rectangle([x * scale, y * scale, x * scale + scale - 1, y * scale + scale - 1], fill=FG)
    return im


if __name__ == "__main__":
    m = matrix()
    n = len(m)
    print(f"URL {len(URL)} 字符 → QR {n}×{n} 模块（含 2 模块静默区，ECC=Q）")
    out1 = ROOT / "_ppt_imgs" / "qoder_qr.png"
    out2 = ROOT / "_ppt_video4" / "qoder_qr_135.png"
    render(m, 8).save(out1)          # 45×8 = 360px
    render(m, 3).save(out2)          # 45×3 = 135px
    for p in (out1, out2):
        im = Image.open(p)
        print(f"  {p.relative_to(ROOT)}  {im.size[0]}×{im.size[1]}")
