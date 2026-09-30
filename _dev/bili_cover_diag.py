# -*- coding: utf-8 -*-
"""封面上传诊断：试 PNG / JPEG / 另一域名 / 带 ts，打印完整返回。"""
import json
import pathlib
import urllib.error
import urllib.request
import uuid

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
SRC = ROOT / "_dev" / "bili_cover.png"
JPG = ROOT / "_dev" / "bili_cover.jpg"
Image.open(SRC).convert("RGB").save(JPG, quality=92)
print("JPEG:", JPG.stat().st_size // 1024, "KB   PNG:", SRC.stat().st_size // 1024, "KB")


def post_multipart(url, path, field="cover"):
    boundary = uuid.uuid4().hex
    blob = path.read_bytes()
    ctype = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
            f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n').encode()
    mid = (f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="csrf"\r\n\r\n'
           f'{CK["bili_jct"]}\r\n').encode()
    body = head + blob + mid + f"--{boundary}--\r\n".encode()
    h = {"User-Agent": UA, "Cookie": COOKIE, "Connection": "close",
         "Content-Type": f"multipart/form-data; boundary={boundary}",
         "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


import time  # noqa: E402

csrf = CK["bili_jct"]
tests = [
    ("① member + PNG", f"https://member.bilibili.com/x/vu/web/cover/up?csrf={csrf}", SRC),
    ("② member + JPEG", f"https://member.bilibili.com/x/vu/web/cover/up?csrf={csrf}", JPG),
    ("③ member + JPEG + ts", f"https://member.bilibili.com/x/vu/web/cover/up?ts={int(time.time()*1000)}&csrf={csrf}", JPG),
    ("④ api 域名 + JPEG", f"https://api.bilibili.com/x/vu/web/cover/up?csrf={csrf}", JPG),
    ("⑤ member + JPEG（字段名 img）", f"https://member.bilibili.com/x/vu/web/cover/up?csrf={csrf}", JPG),
]
for name, url, path in tests:
    if name.startswith("⑤"):
        st, body = post_multipart(url, path, field="img")
    else:
        st, body = post_multipart(url, path)
    print(f"{name}: status={st}  {body[:220]}")
