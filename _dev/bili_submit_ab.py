# -*- coding: utf-8 -*-
"""投稿字段 A/B：全部 tid=99999（不会发布），看哪种字段形态不再报 21001。"""
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
ST = json.loads((ROOT / "_dev" / "bili_upload_state.json").read_text(encoding="utf-8"))
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HDR = {"User-Agent": UA, "Cookie": COOKIE, "Connection": "close",
       "Referer": "https://member.bilibili.com/platform/upload/video/frame",
       "Origin": "https://member.bilibili.com", "Accept": "application/json, text/plain, */*",
       "Accept-Language": "zh-CN,zh;q=0.9", "Content-Type": "application/json; charset=UTF-8"}
FN = ST["filename"]          # 例如 laya-ppt-3分钟（不带扩展名）
COVER = ST["cover"]


def base(**over):
    p = {
        "copyright": 1, "source": "", "tid": 99999, "cover": COVER,
        "title": "probe", "desc_format_id": 0, "desc": "probe",
        "desc_v2": [{"raw_text": "probe", "biz_id": "", "type": 1}],
        "dynamic": "", "subtitle": {"open": 0, "lan": ""},
        "tag": "probe", "videos": [{"filename": FN, "title": "probe", "desc": ""}],
        "dtime": None,
    }
    p.update(over)
    return p


variants = [
    ("① 现状（filename 无扩展名）", base()),
    ("② filename 带 .mp4", base(videos=[{"filename": FN + ".mp4", "title": "probe", "desc": ""}])),
    ("③ videos 带 cid", base(videos=[{"filename": FN, "title": "probe", "desc": "", "cid": 0}])),
    ("④ 加 no_reprint/open_elec", base(no_reprint=1, open_elec=1, human_type2=0)),
    ("⑤ 去掉 desc_v2/subtitle", {k: v for k, v in base().items() if k not in ("desc_v2", "subtitle")}),
    ("⑥ 只留最小字段", {"copyright": 1, "tid": 99999, "cover": COVER, "title": "probe",
                        "desc": "probe", "tag": "probe",
                        "videos": [{"filename": FN, "title": "probe", "desc": ""}]}),
]

for label, payload in variants:
    url = f"https://member.bilibili.com/x/vu/web/add?csrf={CK['bili_jct']}&t={int(time.time()*1000)}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=HDR, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"{label}: 200 {r.read().decode('utf-8','replace')[:180]}")
    except urllib.error.HTTPError as e:
        print(f"{label}: HTTP {e.code} {e.read().decode('utf-8','replace')[:140]}")
    except Exception as e:
        print(f"{label}: 失败 {e}")
