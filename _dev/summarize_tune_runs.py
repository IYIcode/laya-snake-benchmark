# -*- coding: utf-8 -*-
"""汇总 _tune_runs/*.json 的均分与局数（供 README / VERIFY 引用，避免手抄出错）。"""
import glob
import json
import pathlib

rows = []
for f in sorted(glob.glob("_tune_runs/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    games = d.get("games") or []
    causes = {}
    for g in games:
        causes[g.get("cause")] = causes.get(g.get("cause"), 0) + 1
    rows.append((pathlib.Path(f).name, d.get("variant"), d.get("mean"), len(games),
                 sorted({g.get("seed") for g in games}), causes))

print(f"{'文件':16s} {'variant':12s} {'mean':>6s} {'局数':>4s}  死因")
for name, variant, mean, n, seeds, causes in rows:
    print(f"{name:16s} {str(variant):12s} {str(mean):>6s} {n:>4d}  {causes}")
print()
print("seeds 范围示例:", rows[-1][4][:4], "…", rows[-1][4][-2:] if rows else "")
