# -*- coding: utf-8 -*-
"""投稿前自检：确认登录身份 + 拉取 B 站分区表核对 tid。"""
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())


def get(url, referer="https://member.bilibili.com/"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": COOKIE, "Referer": referer})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


nav = get("https://api.bilibili.com/x/web-interface/nav", "https://www.bilibili.com/")
d = nav.get("data", {})
print(f"登录状态 code={nav.get('code')}  isLogin={d.get('isLogin')}")
if d.get("isLogin"):
    print(f"  昵称={d.get('uname')}  mid={d.get('mid')}  等级={d.get('level_info',{}).get('current_level')}  硬币={d.get('money')}")
    print(f"  大会员={d.get('vipStatus')}  实名/手机: nav 不含，投稿接口会校验")

try:
    tl = get(f"https://member.bilibili.com/x/vupre/web/topic/type/list?ts={int(time.time()*1000)}")
    print("分区表 code=", tl.get("code"))
    found = []

    def walk(nodes, path=""):
        for n in nodes or []:
            name = n.get("name") or n.get("typename") or ""
            nid = n.get("id") or n.get("tid")
            cur = f"{path}/{name}"
            if n.get("children"):
                walk(n["children"], cur)
            else:
                found.append((nid, cur))

    walk(tl.get("data", []))
    for nid, p in found:
        if any(k in p for k in ("计算机", "科学", "科技", "数码", "编程", "软件")):
            print(f"  tid={nid}  {p}")
except Exception as e:
    print("分区表拉取失败（可忽略，用默认 188）:", e)
