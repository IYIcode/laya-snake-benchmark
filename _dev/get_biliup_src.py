# -*- coding: utf-8 -*-
"""从 PyPI 取 biliup 源码，打印它的封面上传 / 投稿提交实现（照抄参数，不安装整包）。"""
import json
import pathlib
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "_dev" / "_biliup_src"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}

meta = json.load(urllib.request.urlopen(urllib.request.Request(
    "https://pypi.org/pypi/biliup/json", headers=UA), timeout=30))
sdist = [u for u in meta["urls"] if u["packagetype"] == "sdist"][0]
print("sdist:", sdist["filename"], f'{sdist["size"]/1024:.0f} KB')
DEST.mkdir(parents=True, exist_ok=True)
tgz = DEST / sdist["filename"]
if not tgz.exists():
    urllib.request.urlretrieve(sdist["url"], tgz)
with tarfile.open(tgz) as t:
    t.extractall(DEST)
    names = t.getnames()
print("文件数:", len(names))
for n in names:
    if n.endswith(".py") and ("uploader" in n or "bili" in n):
        print("  ", n)
