# -*- coding: utf-8 -*-
"""打几条真实 /decide 请求并把 /log 证据存成 UTF-8 JSON，供展示。"""
import json, urllib.request

def post(req):
    body = json.dumps(req).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:8890/decide", body,
                               {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))

def get(url):
    return json.load(urllib.request.urlopen(url))

INSTR_NOTE = ""
# 局面1：贴墙直冲食物（旧版会选撞墙方向的典型场景）
s1 = {"state": {"game": "snake", "board": "12x12", "head": [11, 5],
                "body": [[11, 5], [10, 5], [9, 5]], "food": [11, 2], "facing": "RIGHT"},
      "criteria": {"UP":   "foodDist=4 space=40 danger=1",
                   "DOWN": "BLOCKED: hits wall or body right away",
                   "LEFT": "foodDist=3 space=40 danger=0"}}
# 局面2：窄通道，贪吃会撞进死胡同
s2 = {"state": {"game": "snake", "board": "12x12", "head": [6, 6],
                "body": [[6, 6], [6, 5], [6, 4], [5, 4], [4, 4]], "food": [8, 6], "facing": "DOWN"},
      "criteria": {"LEFT":  "foodDist=8 space=2 danger=3",
                   "DOWN":  "BLOCKED: hits wall or body right away",
                   "RIGHT": "foodDist=6 space=30 danger=1",
                   "UP":    "foodDist=4 space=50 danger=0"}}
# 局面3：食物在正前方一步
s3 = {"state": {"game": "snake", "board": "12x12", "head": [5, 5],
                "body": [[5, 5], [4, 5], [3, 5]], "food": [6, 5], "facing": "RIGHT"},
      "criteria": {"UP":    "foodDist=7 space=40 danger=1",
                   "DOWN":  "foodDist=9 space=40 danger=1",
                   "RIGHT": "foodDist=0 space=40 danger=0"}}

shots = []
for model in ("v2", "v5"):
    for tag, req in (("贴墙冲食物", s1), ("死胡同陷阱", s2), ("食物正前方", s3)):
        r = post({**req, "model": model})
        shots.append({"model": model, "scene": tag, "reply": r})

log = get("http://127.0.0.1:8890/log?n=20")
out = {"health": get("http://127.0.0.1:8890/health"), "shots": shots, "log": log}
json.dump(out, open("_evidence.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OK", len(shots), "shots,", log["count"], "log entries")
