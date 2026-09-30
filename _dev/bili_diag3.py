# -*- coding: utf-8 -*-
"""测 upos 合片（finish）的正确姿势：带不带 X-Upos-Auth、parts 传什么。"""
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
VIDEO = ROOT / "laya-ppt-3分钟.mp4"


def call(method, url, data=None, headers=None, timeout=180):
    h = {"User-Agent": UA, "Cookie": COOKIE, "Connection": "close",
         "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode()


size = VIDEO.stat().st_size
fname = VIDEO.name
q = urllib.parse.urlencode({"name": fname, "size": size, "r": "upos", "profile": "ugcfx/bup",
                            "ssl": "0", "version": "2.14.0", "build": "2140000",
                            "buvid": CK.get("buvid3", ""), "biz_id": "0", "web_location": "0.0.0.0"})
_, body = call("GET", "https://member.bilibili.com/preupload?" + q)
pre = json.loads(body)
endpoint = pre["endpoint"]
endpoint = ("https:" + endpoint) if endpoint.startswith("//") else endpoint
path = "/" + pre["upos_uri"].split("://", 1)[1]
auth, chunk, biz = pre["auth"], int(pre["chunk_size"]), pre["biz_id"]
chunks = max(1, -(-size // chunk))
blob = VIDEO.read_bytes()[:chunk]

_, body = call("POST", f"{endpoint}{path}?uploads&output=json&profile=ugcfx/bup"
                       f"&filesize={size}&partsize={chunk}&biz_id={biz}&chunk_size={chunk}",
               data=b"", headers={"X-Upos-Auth": auth})
upload_id = json.loads(body)["upload_id"]

st, b = call("PUT", f"{endpoint}{path}?partNumber=1&uploadId={upload_id}&chunk=1&chunks={chunks}"
                    f"&size={len(blob)}&start=0&end={len(blob)}&total={size}",
             data=blob, headers={"Content-Type": "application/octet-stream", "X-Upos-Auth": auth})
print(f"分片 PUT → {st} {b[:60]}")

fin = (f"{endpoint}{path}?output=json&name={urllib.parse.quote(fname)}"
       f"&profile=ugcfx/bup&uploadId={upload_id}&biz_id={biz}")
variants = [
    ("① auth + parts[etag='']", {"X-Upos-Auth": auth, "Content-Type": "application/json"},
     json.dumps({"parts": [{"partNumber": 1, "eTag": ""}]}).encode()),
    ("② auth + parts[]", {"X-Upos-Auth": auth, "Content-Type": "application/json"},
     json.dumps({"parts": []}).encode()),
    ("③ auth + 无 body", {"X-Upos-Auth": auth}, b""),
]
for name, hdr, payload in variants:
    st, b = call("POST", fin, data=payload, headers=hdr)
    print(f"合片 {name}: status={st}  {b[:160]}")
    if st == 200 and b'OK' in b:
        print("   ✅ 可用：", name)
        break
