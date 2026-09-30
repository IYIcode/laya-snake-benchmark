# -*- coding: utf-8 -*-
"""B 站扫码登录：生成二维码 + 轮询确认，成功后把 cookies 存到 _dev/bili_cookies.json

用法：python _dev/bili_login.py          # 后台跑，扫码成功后自动结束
"""
import http.cookiejar
import json
import pathlib
import time
import urllib.request

import qrcode

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
COOKIE_FILE = ROOT / "_dev" / "bili_cookies.json"
QR_FILE = ROOT / "_dev" / "bili_qr.png"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get(url, referer="https://www.bilibili.com/"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    with opener.open(req, timeout=20) as r:
        return r.read()


def main():
    gen = json.loads(get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate"))
    if gen.get("code") != 0:
        print("生成二维码失败:", gen)
        return
    qk = gen["data"]["qrcode_key"]
    url = gen["data"]["url"]
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color=(11, 14, 20), back_color="white").save(QR_FILE)
    print(f"QR 已生成 → {QR_FILE}", flush=True)
    print(f"二维码内容: {url}", flush=True)
    print("请用 B 站手机客户端扫码并确认登录（180 秒内有效）", flush=True)

    deadline = time.time() + 180
    last = None
    while time.time() < deadline:
        try:
            d = json.loads(get(f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qk}"))
        except Exception as e:
            print("轮询异常:", e, flush=True)
            time.sleep(3)
            continue
        code = d.get("data", {}).get("code")
        msg = d.get("data", {}).get("message")
        if code != last:
            print(f"轮询: code={code} {msg}", flush=True)
            last = code
        if code == 0:
            cookies = {c.name: c.value for c in jar}
            if "buvid3" not in cookies:                      # 补 buvid3/buvid4，投稿接口需要
                try:
                    spi = json.loads(get("https://api.bilibili.com/x/frontend/finger/spi"))["data"]
                    cookies["buvid3"], cookies["buvid4"] = spi["b_3"], spi["b_4"]
                except Exception as e:
                    print("取 buvid 失败（可忽略）:", e, flush=True)
            COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=1), encoding="utf-8")
            print("LOGIN OK →", COOKIE_FILE, flush=True)
            print("cookies:", ", ".join(sorted(cookies)), flush=True)
            return
        time.sleep(2)
    print("二维码已过期，请重跑本脚本", flush=True)


if __name__ == "__main__":
    main()
