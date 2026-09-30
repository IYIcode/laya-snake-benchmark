# -*- coding: utf-8 -*-
"""核对 B 站分区 tid（用排行榜/热门接口反查分区名，避免传错分区）。"""
import json
import urllib.request

CK = json.load(open("_dev/bili_cookies.json", encoding="utf-8"))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
H = {"User-Agent": UA, "Cookie": "; ".join(f"{k}={v}" for k, v in CK.items()),
     "Referer": "https://www.bilibili.com/"}


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25) as r:
        return json.loads(r.read())


for rid in (188, 201, 36, 95, 4):
    try:
        d = get(f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all")
        lst = (d.get("data") or {}).get("list") or []
        if lst:
            print(f"rid={rid}: {len(lst)} 条视频，分区名 = {lst[0].get('tname')}   例：{lst[0].get('title')[:30]}")
        else:
            print(f"rid={rid}: code={d.get('code')} {d.get('message')}（空）")
    except Exception as e:
        print(f"rid={rid}: 失败 {e}")

try:
    pop = get("https://api.bilibili.com/x/web-interface/popular?ps=30&pn=1")
    seen = {}
    for v in (pop.get("data") or {}).get("list") or []:
        seen[(v.get("tid"), v.get("tname"))] = seen.get((v.get("tid"), v.get("tname")), 0) + 1
    print("热门样本分区:", dict(list(seen.items())[:12]))
except Exception as e:
    print("热门接口失败:", e)
