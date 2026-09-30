# -*- coding: utf-8 -*-
"""找出能过 WAF 的投稿请求头（全部用 tid=99999，绝不会发布）。"""
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
STATE = json.loads((ROOT / "_dev" / "bili_upload_state.json").read_text(encoding="utf-8"))
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

payload = {
    "copyright": 1, "source": "", "tid": 99999, "cover": STATE["cover"],
    "title": "probe", "desc_format_id": 0, "desc": "probe",
    "desc_v2": [{"raw_text": "probe", "biz_id": "", "type": 1}],
    "dynamic": "", "subtitle": {"open": 0, "lan": ""},
    "tag": "probe", "videos": [{"filename": STATE["filename"], "title": "probe", "desc": ""}],
    "dtime": None,
}
body = json.dumps(payload).encode()

VARIANTS = [
    ("① 极简（仅 UA+Cookie）", "https://member.bilibili.com/x/vu/web/add", {"User-Agent": CHROME_UA}),
    ("② + Referer www", "https://member.bilibili.com/x/vu/web/add",
     {"User-Agent": CHROME_UA, "Referer": "https://www.bilibili.com/"}),
    ("③ 完整浏览器头", "https://member.bilibili.com/x/vu/web/add",
     {"User-Agent": CHROME_UA, "Referer": "https://member.bilibili.com/platform/upload/video/frame",
      "Origin": "https://member.bilibili.com", "Accept": "application/json, text/plain, */*",
      "Accept-Language": "zh-CN,zh;q=0.9", "Content-Type": "application/json; charset=UTF-8"}),
    ("④ v3 接口 + 完整头", "https://member.bilibili.com/x/vu/web/add/v3",
     {"User-Agent": CHROME_UA, "Referer": "https://member.bilibili.com/platform/upload/video/frame",
      "Origin": "https://member.bilibili.com", "Accept": "application/json, text/plain, */*",
      "Accept-Language": "zh-CN,zh;q=0.9", "Content-Type": "application/json; charset=UTF-8"}),
]

for label, url, hdr in VARIANTS:
    full = {"Cookie": COOKIE, "Connection": "close", **hdr}
    full.setdefault("Content-Type", "application/json")
    u = f"{url}?csrf={CK['bili_jct']}&t={int(time.time()*1000)}"
    req = urllib.request.Request(u, data=body, headers=full, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode("utf-8", "replace")
            print(f"{label}: {r.status} {txt[:200]}")
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        print(f"{label}: HTTP {e.code} {txt[:160]}")
    except Exception as e:
        print(f"{label}: 失败 {e}")
