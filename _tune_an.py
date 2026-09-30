# -*- coding: utf-8 -*-
"""读 _tune_runs/<variant>.json，输出死因分布 + 模型与启发式分歧帧 top。
用法: python -X utf8 _tune_an.py baseline [trap ...]"""
import sys, json
from collections import Counter

for name in sys.argv[1:] or ["baseline"]:
    d = json.load(open(f"_tune_runs/{name}.json", encoding="utf-8"))
    games = d["games"]
    print(f"\n=== {name}  mean={d['mean']:.2f}  games={[g['food'] for g in games]}")
    lab = Counter()
    dis = 0
    examples = []
    for g in games:
        for l in g["analysis"]["death_labels"]:
            lab[l] += 1
        if g["analysis"]["heur_disagree"] == "本有更优":
            dis += 1
            for fr in reversed(g["traj"]):
                ch = fr.get("choice")
                if not ch:
                    continue
                safe = {k: v for k, v in fr["meta"].items() if v["safe"]}
                best = max(safe, key=lambda k: -2 * safe[k]["fd"] + 0.5 * safe[k]["sp"] + safe[k]["run"])
                if best != ch:
                    examples.append({"seed": g["seed"], "step": fr["step"], "ln": fr["ln"],
                                     "f": fr["f"], "h": fr["h"], "food": g["food"],
                                     "chosen": {k: fr["meta"][ch][k] for k in ("fd", "sp", "run")},
                                     "p_chosen": fr["probs"].get(ch),
                                     "best": {k: fr["meta"][best][k] for k in ("fd", "sp", "run")},
                                     "p_best": fr["probs"].get(best), "dir": [ch, best]})
                    break
    print("死因标签:", dict(lab), f"| 本有更优的局数: {dis}/{len(games)}")
    for e in examples[:6]:
        print(" 分歧帧 seed=%s step=%s ln=%s 选%s%s p=%.2f 优%s%s p=%.2f | food=%s" % (
            e["seed"], e["step"], e["ln"], e["dir"][0], e["chosen"], e["p_chosen"],
            e["dir"][1], e["best"], e["p_best"], e["food"]))
    # 每步死前最后3帧的danger/sp读数分布
    near = []
    for g in games:
        for fr in g["traj"][-3:]:
            if fr.get("choice") and fr["meta"][fr["choice"]]["safe"]:
                m = fr["meta"][fr["choice"]]
                near.append((m["fd"], min(m["sp"], 30), m["run"]))
    print("死前三步所选格 (fd, sp≤30, run) 样本数:", len(near))
    print(" 其中 run<=1:", sum(1 for x in near if x[2] <= 1), "| sp<ln+2 比例见标签'入袋'")
