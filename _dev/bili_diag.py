# -*- coding: utf-8 -*-
"""诊断 upos 分片上传：先小包 PUT，再大包 PUT，定位是「网络拦大请求」还是「协议问题」。"""
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


def call(method, url, data=None, headers=None, timeout=60, show_url=False):
    h = {"User-Agent": UA, "Cookie": COOKIE,
         "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
    if headers:
        h.update(headers)
    if show_url:
        print(f"  {method} {url[:150]}")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()
    except Exception as e:
        return None, None, str(e)


size = VIDEO.stat().st_size
fname = VIDEO.name
print(f"文件 {fname}  {size/1048576:.2f} MB")

# 1) 预上传
q = urllib.parse.urlencode({"name": fname, "size": size, "r": "upos", "profile": "ugcfx/bup",
                            "ssl": "0", "version": "2.14.0", "build": "2140000",
                            "buvid": CK.get("buvid3", ""), "biz_id": "0", "web_location": "0.0.0.0"})
st, _, body = call("GET", "https://member.bilibili.com/preupload?" + q)
pre = json.loads(body)
endpoint = pre["endpoint"]
endpoint = ("https:" + endpoint) if endpoint.startswith("//") else endpoint
path = "/" + pre["upos_uri"].split("://", 1)[1]
auth, chunk, biz = pre["auth"], int(pre["chunk_size"]), pre["biz_id"]
print(f"preupload OK: {endpoint}  分片 {chunk}")

# 2) 主机可达性
st, hd, b = call("GET", endpoint + "/", timeout=20)
print(f"GET {endpoint}/ → status={st}  {str(b)[:80]}")

# 3) 初始化
chunks = max(1, -(-size // chunk))
init = (f"{endpoint}{path}?uploads&output=json&profile=ugcfx/bup"
        f"&filesize={size}&partsize={chunk}&biz_id={biz}&chunk_size={chunk}")
st, _, body = call("POST", init, data=b"", headers={"X-Upos-Auth": auth})
print(f"init → status={st}  {body[:100]}")
upload_id = json.loads(body)["upload_id"]

# 4) 小包 PUT（1KB）—— 判断 PUT 本身通不通
probe = b"\0" * 1024
u = (f"{endpoint}{path}?partNumber=1&uploadId={upload_id}&chunk=1&chunks={chunks}"
     f"&size={len(probe)}&start=0&end={len(probe)}&total={size}")
st, hd, b = call("PUT", u, data=probe, headers={"Content-Type": "application/octet-stream"})
print(f"小包 PUT(1KB) → status={st}  etag={hd.get('Etag') if hd else None}  {str(b)[:80]}")

# 5) 大包 PUT（真实分片）—— 判断是否大请求被拦
blob = VIDEO.read_bytes()[:chunk]
u2 = (f"{endpoint}{path}?partNumber=1&uploadId={upload_id}&chunk=1&chunks={chunks}"
      f"&size={len(blob)}&start=0&end={len(blob)}&total={size}")
st, hd, b = call("PUT", u2, data=blob, headers={"Content-Type": "application/octet-stream"}, timeout=180)
print(f"大包 PUT({len(blob)/1048576:.2f}MB) → status={st}  etag={hd.get('Etag') if hd else None}  {str(b)[:120]}")
