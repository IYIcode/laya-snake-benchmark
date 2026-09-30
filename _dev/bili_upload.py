# -*- coding: utf-8 -*-
"""B 站投稿：upos 分片上传 + 封面上传 + 提交稿件（纯 urllib，无第三方依赖）。

    python _dev/bili_upload.py --video laya-ppt-3分钟.mp4 --cover _dev/bili_cover.png \
        --title "…" --desc-file _dev/bili_desc.txt --tag "…" --tid 188 [--no-submit]

--no-submit 时只做到「上传文件 + 传封面」，不提交稿件（可以先用它验证链路）。
"""
import argparse
import json
import math
import os
import pathlib
import time
import urllib.parse
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


class Bili:
    def __init__(self, cookies):
        self.ck = cookies
        self.cookie = "; ".join(f"{k}={v}" for k, v in cookies.items())

    def call(self, method, url, data=None, headers=None, tries=3):
        h = {"User-Agent": UA, "Cookie": self.cookie, "Connection": "close",
             "Referer": "https://member.bilibili.com/platform/upload/video/frame"}
        if headers:
            h.update(headers)
        last = None
        for attempt in range(1, tries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=h, method=method)
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r, r.read()
            except urllib.error.HTTPError:
                raise                                  # HTTP 错误带响应体，直接抛给上层判断
            except Exception as e:                     # 连接被重置/超时 → 换新连接重试
                last = e
                print(f"    [网络抖动] {type(e).__name__}: {e}  → 重试 {attempt}/{tries - 1}")
                time.sleep(1.5)
        raise RuntimeError(f"请求失败({method} {url[:90]}): {last}")

    # ── 1. 预上传：拿到 upos 域名 / 路径 / 鉴权 / 分片大小 ──
    def preupload(self, fname, size):
        q = urllib.parse.urlencode({
            "name": fname, "size": size, "r": "upos", "profile": "ugcfx/bup",
            "ssl": "0", "version": "2.14.0", "build": "2140000",
            "buvid": self.ck.get("buvid3", ""), "biz_id": "0", "web_location": "0.0.0.0"})
        _, body = self.call("GET", "https://member.bilibili.com/preupload?" + q)
        d = json.loads(body)
        if not d.get("OK"):
            raise RuntimeError(f"preupload 失败: {d}")
        endpoint = d["endpoint"]
        if endpoint.startswith("//"):
            endpoint = "https:" + endpoint
        path = "/" + d["upos_uri"].split("://", 1)[1]
        print(f"  endpoint={endpoint}\n  upos_uri={d['upos_uri']}\n  分片={d.get('chunk_size')} 字节  biz_id={d.get('biz_id')}")
        return endpoint, path, d["auth"], int(d.get("chunk_size") or 8 * 1024 * 1024), d.get("biz_id", 0)

    # ── 2~4. 初始化 → 逐片 PUT → 结束 ──
    def upload_file(self, video):
        fname = os.path.basename(video)
        size = os.path.getsize(video)
        endpoint, path, auth, chunk, biz = self.preupload(fname, size)
        chunks = max(1, math.ceil(size / chunk))

        init = (f"{endpoint}{path}?uploads&output=json&profile=ugcfx/bup"
                f"&filesize={size}&partsize={chunk}&biz_id={biz}&chunk_size={chunk}")
        _, body = self.call("POST", init, data=b"", headers={"X-Upos-Auth": auth})
        upload_id = json.loads(body)["upload_id"]
        print(f"  upload_id={upload_id}  共 {chunks} 片")

        etags = []
        with open(video, "rb") as f:
            for i in range(1, chunks + 1):
                start = (i - 1) * chunk
                end = min(start + chunk, size)
                f.seek(start)
                blob = f.read(end - start)
                put = (f"{endpoint}{path}?partNumber={i}&uploadId={upload_id}&chunk={i}"
                       f"&chunks={chunks}&size={len(blob)}&start={start}&end={end}&total={size}")
                r, _ = self.call("PUT", put, data=blob,
                                 headers={"Content-Type": "application/octet-stream",
                                          "X-Upos-Auth": auth})   # 少这个头会 403 AccessDenied
                etag = ""
                for k, v in r.headers.items():
                    if k.lower() == "etag":
                        etag = v.strip('"')
                etags.append(etag)
                print(f"  片 {i}/{chunks}  {len(blob)/1048576:.2f} MB  状态={r.status}  etag={etag[:16] or '(无)'}")

        fin = (f"{endpoint}{path}?output=json&name={urllib.parse.quote(fname)}"
               f"&profile=ugcfx/bup&uploadId={upload_id}&biz_id={biz}")
        ok = False
        for payload in (json.dumps({"parts": [{"partNumber": i + 1, "eTag": e} for i, e in enumerate(etags)]}),
                        json.dumps({"parts": []})):
            _, body = self.call("POST", fin, data=payload.encode(),
                                headers={"Content-Type": "application/json", "X-Upos-Auth": auth})
            print(f"  合片: {body[:140]}")
            if b'"OK":1' in body or b"MULTIPART" in body.upper():
                ok = True
                break
        if not ok:
            raise RuntimeError("合片失败，见上面返回")
        return os.path.splitext(fname)[0]          # 投稿时 videos[].filename 要「不带扩展名」

    # ── 5. 封面（照 biliup 的实现：裁成 16:10，base64 data URI，普通表单提交）──
    def upload_cover(self, cover):
        import base64
        import io
        from PIL import Image
        with Image.open(cover) as im:
            im = im.convert("RGB")
            x, y = im.size
            if x / y > 1.6:                       # 目标比例 16:10
                d = x - y * 1.6
                im = im.crop((int(d / 2), 0, int(x - d / 2), y))
            else:
                d = y - x * 10 / 16
                im = im.crop((0, int(d / 2), x, int(y - d / 2)))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=92)
        data = urllib.parse.urlencode({
            "cover": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
            "csrf": self.ck["bili_jct"]}).encode()
        _, body = self.call("POST", "https://member.bilibili.com/x/vu/web/cover/up",
                            data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        d = json.loads(body)
        if d.get("code") != 0 or not d.get("data"):
            raise RuntimeError(f"封面上传失败: {d}")
        print(f"  封面 URL: {d['data']['url']}")
        return d["data"]["url"]

    # ── 6. 提交稿件（/x/vu/web/add，字段照 biliup 的 Data 结构）──
    def submit(self, fname, cover_url, title, desc, tag, tid, copyright_=1):
        payload = {
            "copyright": copyright_, "source": "", "tid": int(tid),
            "cover": cover_url, "title": title[:80], "desc_format_id": 0,
            "desc": desc, "desc_v2": [{"raw_text": desc, "biz_id": "", "type": 1}],
            "dynamic": "", "subtitle": {"open": 0, "lan": ""},
            "tag": tag, "videos": [{"filename": fname, "title": title[:80], "desc": ""}],
            "dtime": None,
        }
        url = f"https://member.bilibili.com/x/vu/web/add?csrf={self.ck['bili_jct']}"
        _, body = self.call("POST", url, data=json.dumps(payload).encode(),
                            headers={"Content-Type": "application/json"})
        d = json.loads(body)
        if d.get("code") != 0:
            raise RuntimeError(f"提交失败: {d}")
        a = d["data"]
        print(f"  投稿成功！aid={a.get('aid')}  bvid={a.get('bvid')}")
        print(f"  https://www.bilibili.com/video/{a.get('bvid')}")
        return a

    # ── 安全探测：用错 tid 提交，验证除分区外的字段都被接受 ──
    def probe(self, fname, cover_url, title, desc, tag):
        try:
            self.submit(fname, cover_url, title, desc, tag, 99999)
            print("  ⚠ 探测居然成功了（不应该）")
        except RuntimeError as e:
            print(f"  探测结果: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--cover", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--desc-file", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--tid", default="188")
    ap.add_argument("--cookies", default=str(ROOT / "_dev" / "bili_cookies.json"))
    ap.add_argument("--no-submit", action="store_true")
    ap.add_argument("--probe", action="store_true", help="先用错 tid 安全探测提交字段是否被接受")
    a = ap.parse_args()

    ck = json.loads(pathlib.Path(a.cookies).read_text(encoding="utf-8"))
    b = Bili(ck)
    print("① 上传视频文件 …")
    fname = b.upload_file(str(ROOT / a.video))
    print("② 上传封面 …")
    cover_url = b.upload_cover(str(ROOT / a.cover))
    if a.no_submit:
        print("已跳过提交（--no-submit）。文件名:", fname, "封面:", cover_url)
        (ROOT / "_dev" / "bili_upload_state.json").write_text(
            json.dumps({"filename": fname, "cover": cover_url}, ensure_ascii=False, indent=1), encoding="utf-8")
        return
    desc = pathlib.Path(a.desc_file).read_text(encoding="utf-8")
    if a.probe:
        print("③ 安全探测（tid=99999）…")
        b.probe(fname, cover_url, a.title, desc, a.tag)
    print("④ 提交稿件 …")
    b.submit(fname, cover_url, a.title, desc, a.tag, a.tid)


if __name__ == "__main__":
    main()
