# -*- coding: utf-8 -*-
"""下载 biliup-rs 的 Windows 版二进制到 _dev/biliup/（用于投稿上传）。

    python _dev/get_biliup.py
"""
import json
import pathlib
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "_dev" / "biliup"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}


def main():
    api = "https://api.github.com/repos/biliup/biliup-rs/releases/latest"
    rel = json.load(urllib.request.urlopen(urllib.request.Request(api, headers=UA), timeout=30))
    print("latest:", rel["tag_name"])
    assets = [(a["name"], a["browser_download_url"], a["size"]) for a in rel["assets"]]
    for n, _u, s in assets:
        print(f"  {n}  {s/1024:.0f} KB")
    win = [a for a in assets if "windows" in a[0].lower() or "win" in a[0].lower()]
    if not win:
        print("没找到 Windows 资产")
        return
    name, url, _ = win[0]
    DEST.mkdir(parents=True, exist_ok=True)
    zpath = DEST / name
    print("下载", name, "…")
    urllib.request.urlretrieve(url, zpath)
    if name.endswith(".zip"):
        with zipfile.ZipFile(zpath) as z:
            z.extractall(DEST)
            print("解压:", ", ".join(z.namelist()))
    print("完成 →", DEST)


if __name__ == "__main__":
    main()
