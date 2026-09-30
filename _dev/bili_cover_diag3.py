# -*- coding: utf-8 -*-
"""最后一轮：① 封面接口多路径/多请求头矩阵；② 用错误 tid 安全探测投稿接口是否可用。"""
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


def req(method, url, data=None, headers=None, timeout=60):
    h = {"User-Agent": UA, "Cookie": COOKIE, "Connection": "close",
         "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
    if headers:
        h.update(headers)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method), timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def cover_body(with_csrf_field=True, field="cover"):
    boundary = uuid.uuid4().hex
    blob = JPG.read_bytes()
    body = ((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
             f'filename="{JPG.name}"\r\nContent-Type: image/jpeg\r\n\r\n').encode() + blob)
    if with_csrf_field:
        body += (f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="csrf"\r\n\r\n'
                 f'{CK["bili_jct"]}\r\n').encode()
    body += f"--{boundary}--\r\n".encode()
    return boundary, body


csrf = CK["bili_jct"]
print("=== 封面接口矩阵 ===")
paths = ["/x/vu/web/cover/up", "/x/vu/web/cover/v2/up", "/x/vu/web/cover/upload", "/x/vu/archive/cover/up"]
combos = [("带 csrf 字段", True, False), ("不带 csrf 字段", False, False), ("带 csrf 字段 + XRW", True, True)]
for p in paths:
    for label, with_field, xrw in combos:
        b, body = cover_body(with_field)
        hd = {"Content-Type": f"multipart/form-data; boundary={b}"}
        if xrw:
            hd["X-Requested-With"] = "XMLHttpRequest"
            hd["Origin"] = "https://member.bilibili.com"
        st, txt = req("POST", f"https://member.bilibili.com{p}?csrf={csrf}&t={int(time.time()*1000)}",
                      data=body, headers=hd)
        ok = '"code":0' in txt
        print(f"{p:26s} {label:18s} → {st} {txt[:90]}")
        if ok:
            print("   ✅ 封面成功:", json.loads(txt)["data"]["url"])
            raise SystemExit(0)

print("\n=== 投稿接口安全探测（tid=99999，不会发布）===")
payload = {
    "copyright": 1, "source": "", "tid": 99999,
    "title": "probe", "cover": "", "desc": "probe", "tag": "probe",
    "videos": [{"filename": "probe.mp4", "title": "P1", "desc": "", "cid": 0}],
    "no_reprint": 1, "open_elec": 1, "human_type2": 0,
    "up_close_danmaku": False, "up_close_reply": False, "up_close_dynamic": False,
    "dolby": 0, "lossless_music": 0, "interactive": 0, "act_reserve_create": 0, "aid": 0,
}
st, txt = req("POST", f"https://member.bilibili.com/x/vu/web/add/v3?t={int(time.time()*1000)}&csrf={csrf}",
              data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
print(f"add/v3 → {st} {txt[:300]}")
