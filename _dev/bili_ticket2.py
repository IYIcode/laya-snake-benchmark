# -*- coding: utf-8 -*-
"""再试 bili_ticket（POST/GET 两种）+ 封面 + 投稿探测，一把跑完给结论。"""
import hashlib
import hmac
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def req(method, url, data=None, headers=None, cookies=None, timeout=90):
    ck = dict(cookies or CK)
    h = {"User-Agent": UA, "Cookie": "; ".join(f"{k}={v}" for k, v in ck.items()),
         "Connection": "close", "Referer": "https://www.bilibili.com/"}
    if headers:
        h.update(headers)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method), timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


ticket_ok = False
for label, method, body in (("POST 空 JSON", "POST", b"{}"), ("GET", "GET", None)):
    ts = int(time.time())
    hexsign = hmac.new(b"XgwSnGZ1p", f"ts{ts}".encode(), hashlib.sha256).hexdigest()
    url = ("https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
           f"?key_id=ec02&hexsign={hexsign}&context%5Bts%5D={ts}&csrf={CK['bili_jct']}")
    hd = {"Content-Type": "application/json"} if method == "POST" else {}
    st, txt = req(method, url, data=body, headers=hd)
    print(f"GenWebTicket({label}) → {st} {txt[:160]}")
    try:
        d = json.loads(txt)
        if d.get("code") == 0:
            CK["bili_ticket"] = d["data"]["ticket"]
            CK["bili_ticket_expires"] = str(d["data"]["created_at"] + d["data"]["ttl"])
            (ROOT / "_dev" / "bili_cookies.json").write_text(json.dumps(CK, ensure_ascii=False, indent=1), encoding="utf-8")
            ticket_ok = True
            print("   ✅ 拿到 bili_ticket，长度", len(CK["bili_ticket"]))
            break
    except Exception:
        pass

# 封面（带 ticket，如果拿到）
b = uuid.uuid4().hex
img = ROOT / "_dev" / "bili_cover.jpg"
blob = img.read_bytes()
body = ((f'--{b}\r\nContent-Disposition: form-data; name="cover"; filename="{img.name}"\r\n'
         f'Content-Type: image/jpeg\r\n\r\n').encode() + blob
        + (f'\r\n--{b}\r\nContent-Disposition: form-data; name="csrf"\r\n\r\n{CK["bili_jct"]}\r\n').encode()
        + f"--{b}--\r\n".encode())
st, txt = req("POST", f"https://member.bilibili.com/x/vu/web/cover/up?csrf={CK['bili_jct']}",
              data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}",
                                  "Referer": "https://member.bilibili.com/platform/upload/video/frame"})
print(f"封面上传（ticket={'有' if ticket_ok else '无'}）→ {st} {txt[:160]}")

# 投稿探测
payload = {
    "copyright": 1, "source": "", "tid": 99999, "title": "probe", "cover": "", "desc": "probe",
    "tag": "probe", "videos": [{"filename": "n260930tx2f9868av9vxy42dk4siio6f.mp4", "title": "P1", "desc": "", "cid": 0}],
    "no_reprint": 1, "open_elec": 1, "human_type2": 0, "up_close_danmaku": False,
    "up_close_reply": False, "up_close_dynamic": False, "dolby": 0, "lossless_music": 0,
    "interactive": 0, "act_reserve_create": 0, "aid": 0,
}
st, txt = req("POST", f"https://member.bilibili.com/x/vu/web/add/v3?t={int(time.time()*1000)}&csrf={CK['bili_jct']}",
              data=json.dumps(payload).encode(),
              headers={"Content-Type": "application/json",
                       "Referer": "https://member.bilibili.com/platform/upload/video/frame"})
print("add/v3 探测 →", st, txt[:300])
