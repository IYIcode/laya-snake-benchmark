# -*- coding: utf-8 -*-
"""upos 分片 PUT 403 的修法验证：给分片请求补上 X-Upos-Auth / profile 等参数。"""
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CK = json.loads((ROOT / "_dev" / "bili_cookies.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE = "; ".join(f"{k}={v}" for k, v in CK.items())
VIDEO = ROOT / "laya-ppt-3分钟.mp4"


def call(method, url, data=None, headers=None, timeout=120):
    h = {"User-Agent": UA, "Cookie": COOKIE,
         "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, str(e).encode()


size = VIDEO.stat().st_size
fname = VIDEO.name
q = urllib.parse.urlencode({"name": fname, "size": size, "r": "upos", "profile": "ugcfx/bup",
                            "ssl": "0", "version": "2.14.0", "build": "2140000",
                            "buvid": CK.get("buvid3", ""), "biz_id": "0", "web_location": "0.0.0.0"})
_, _, body = call("GET", "https://member.bilibili.com/preupload?" + q)
pre = json.loads(body)
endpoint = pre["endpoint"]
endpoint = ("https:" + endpoint) if endpoint.startswith("//") else endpoint
path = "/" + pre["upos_uri"].split("://", 1)[1]
auth, chunk, biz = pre["auth"], int(pre["chunk_size"]), pre["biz_id"]
chunks = max(1, -(-size // chunk))
blob = VIDEO.read_bytes()[:chunk]

init = (f"{endpoint}{path}?uploads&output=json&profile=ugcfx/bup"
        f"&filesize={size}&partsize={chunk}&biz_id={biz}&chunk_size={chunk}")
st, _, body = call("POST", init, data=b"", headers={"X-Upos-Auth": auth})
upload_id = json.loads(body)["upload_id"]
print(f"init ok  upload_id={upload_id}")

base = (f"{endpoint}{path}?partNumber=1&uploadId={upload_id}&chunk=1&chunks={chunks}"
        f"&size={len(blob)}&start=0&end={len(blob)}&total={size}")

variants = [
    ("① 带 X-Upos-Auth", base, {"X-Upos-Auth": auth, "Content-Type": "application/octet-stream"}),
    ("② 带 auth + profile 参数", base + "&profile=ugcfx/bup",
     {"X-Upos-Auth": auth, "Content-Type": "application/octet-stream"}),
    ("③ 带 auth + profile + output", base + "&profile=ugcfx/bup&output=json",
     {"X-Upos-Auth": auth, "Content-Type": "application/octet-stream"}),
    ("④ 不带 Cookie，只带 auth", base, {"X-Upos-Auth": auth, "Content-Type": "application/octet-stream"}),
]
for name, url, hdr in variants:
    if name.startswith("④"):
        hdr = dict(hdr)
    st, hd, b = call("PUT", url, data=blob, headers=hdr)
    etag = hd.get("Etag") or hd.get("ETag")
    print(f"{name}: status={st} etag={etag}  body={b[:90]}")
    if st == 200:
        print("   ✅ 这个姿势可用；URL 形态:", url[:120])
        break
