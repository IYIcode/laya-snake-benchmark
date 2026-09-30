# -*- coding: utf-8 -*-
"""收尾探测：① 封面再试 3 种写法（csrf 在前 / PNG / 无 filename）；② 用真文件名 + 错 tid 探测投稿接口。"""
import json
import pathlib
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
csrf = CK["bili_jct"]


def req(method, url, data=None, headers=None, timeout=90):
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


def make(order="file-first", img="jpg", filename=True):
    b = uuid.uuid4().hex
    p = ROOT / "_dev" / ("bili_cover.png" if img == "png" else "bili_cover.jpg")
    blob = p.read_bytes()
    ctype = "image/png" if img == "png" else "image/jpeg"
    fn = f'filename="{p.name}"' if filename else ""
    filepart = (f'--{b}\r\nContent-Disposition: form-data; name="cover"; {fn}\r\n'
                f'Content-Type: {ctype}\r\n\r\n').encode() + blob + b"\r\n"
    csrfpart = (f'--{b}\r\nContent-Disposition: form-data; name="csrf"\r\n\r\n{csrf}\r\n').encode()
    body = (csrfpart + filepart if order == "csrf-first" else filepart + csrfpart) + f"--{b}--\r\n".encode()
    return b, body


print("=== 封面再试 ===")
for label, kw in [("csrf 在前 + JPEG", dict(order="csrf-first")),
                  ("PNG 原图", dict(img="png")),
                  ("无 filename", dict(filename=False))]:
    b, body = make(**kw)
    st, txt = req("POST", f"https://member.bilibili.com/x/vu/web/cover/up?csrf={csrf}",
                  data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    print(f"{label:16s} → {st} {txt[:110]}")
    if '"code":0' in txt:
        print("   ✅", json.loads(txt)["data"]["url"])
        break

print("\n=== 投稿接口探测（真文件名 + tid=99999，不会发布）===")
payload = {
    "copyright": 1, "source": "", "tid": 99999,
    "title": "probe", "cover": "", "desc": "probe", "tag": "probe",
    "videos": [{"filename": "n260930tx2f9868av9vxy42dk4siio6f.mp4", "title": "P1", "desc": "", "cid": 0}],
    "no_reprint": 1, "open_elec": 1, "human_type2": 0,
    "up_close_danmaku": False, "up_close_reply": False, "up_close_dynamic": False,
    "dolby": 0, "lossless_music": 0, "interactive": 0, "act_reserve_create": 0, "aid": 0,
}
st, txt = req("POST", f"https://member.bilibili.com/x/vu/web/add/v3?t={int(time.time()*1000)}&csrf={csrf}",
              data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
print(f"add/v3 → {st} {txt[:300]}")
