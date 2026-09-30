# -*- coding: utf-8 -*-
"""封面上传：加 wbi 签名 / Origin 等组合再试。"""
import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
JPG = ROOT / "_dev" / "bili_cover.jpg"
if not JPG.exists():
    Image.open(ROOT / "_dev" / "bili_cover.png").convert("RGB").save(JPG, quality=92)

MIXIN_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
             33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
             26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
             20, 34, 44, 52]


def raw_get(url, referer="https://www.bilibili.com/"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": COOKIE, "Referer": referer})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


nav = raw_get("https://api.bilibili.com/x/web-interface/nav")
wbi = nav["data"]["wbi_img"]
img_key = wbi["img_url"].rsplit("/", 1)[1].split(".")[0]
sub_key = wbi["sub_url"].rsplit("/", 1)[1].split(".")[0]
raw = img_key + sub_key
mixin_key = "".join(raw[i] for i in MIXIN_TAB)[:32]
print("img_key =", img_key[:12], "…  mixin_key =", mixin_key[:12], "…")


def sign(params):
    p = dict(params)
    p["wts"] = int(time.time())
    items = sorted(p.items())
    clean = [(k, "".join(c for c in str(v) if c not in "!'()*")) for k, v in items]
    q = urllib.parse.urlencode(clean)
    p["w_rid"] = hashlib.md5((q + mixin_key).encode()).hexdigest()
    return urllib.parse.urlencode(sorted(p.items()))


def post_cover(url, field="cover", origin=False):
    boundary = uuid.uuid4().hex
    blob = JPG.read_bytes()
    body = ((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
             f'filename="{JPG.name}"\r\nContent-Type: image/jpeg\r\n\r\n').encode()
            + blob
            + (f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="csrf"\r\n\r\n'
               f'{CK["bili_jct"]}\r\n').encode()
            + f"--{boundary}--\r\n".encode())
    h = {"User-Agent": UA, "Cookie": COOKIE, "Connection": "close",
         "Content-Type": f"multipart/form-data; boundary={boundary}",
         "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
    if origin:
        h["Origin"] = "https://member.bilibili.com"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method="POST"), timeout=90) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


csrf = CK["bili_jct"]
base = "https://member.bilibili.com/x/vu/web/cover/up"
tests = [
    ("① Origin", f"{base}?csrf={csrf}", "cover", True),
    ("② wbi 签名", f"{base}?{sign({'csrf': csrf})}", "cover", False),
    ("③ wbi + Origin", f"{base}?{sign({'csrf': csrf})}", "cover", True),
    ("④ wbi + 字段 file", f"{base}?{sign({'csrf': csrf})}", "file", True),
]
for name, url, field, origin in tests:
    st, body = post_cover(url, field, origin)
    print(f"{name}: status={st}  {body[:200]}")
    if st == 200 and '"code":0' in body:
        print("   ✅ 封面可用：", name)
        print("   URL:", json.loads(body).get("data", {}).get("url"))
        break
