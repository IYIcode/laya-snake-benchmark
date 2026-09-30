# -*- coding: utf-8 -*-
"""身体坐标依赖探针：小抄字符串完全不动，只改 state.body——
A) 真蛇身（对照）  B) body 只剩蛇头  C) 蛇身换成另一条随机路径（占用格不同、几何假）。
模型若真在读棋盘坐标，B/C 的概率分布/选择应当明显漂移；若纹丝不动＝行动确实"全靠小抄"。
走 8891 桥接（掩码按 criteria 字符串生效，三条件一致，漂移只可能来自 state）。"""
import json, random, urllib.request
import laya_finetune_snake as L
from _tune import make_crit_fn, GW, GH, DIRS

BRIDGE = "http://127.0.0.1:8891/decide"

def decide(state, crit):
    req = urllib.request.Request(BRIDGE, data=json.dumps(
        {"model": "v5", "state": state, "criteria": crit}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req))
    return d["choice"], d["probabilities"]

crit_fn = make_crit_fn("fdpen6")

def fake_body(rng, head, ln):
    cells = {tuple(head)}
    body = [list(head)]
    for _ in range(ln - 1):
        opts = [[body[-1][0] + d[0], body[-1][1] + d[1]] for d in DIRS.values()
                if 0 <= body[-1][0] + d[0] < GW and 0 <= body[-1][1] + d[1] < GH
                and (body[-1][0] + d[0], body[-1][1] + d[1]) not in cells]
        if not opts:
            break
        p = rng.choice(opts)
        cells.add(tuple(p))
        body.append(p)
    while len(body) < ln:
        c = [rng.randrange(GW), rng.randrange(GH)]
        if tuple(c) not in cells:
            cells.add(tuple(c)); body.append(c)
    return body

results = []
for seed in (3001, 3005):
    rng = random.Random(seed)
    snake, food, facing = L.rand_start(rng)
    head = snake[0]
    probes = 0
    for step in range(20000):
        if probes >= 15:
            break
        crit, meta = crit_fn(head, food, snake, facing)
        if all(not m["safe"] for m in meta.values()):
            break
        state = {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                 "body": [list(s) for s in snake], "food": list(food), "facing": facing}
        if len(snake) >= 25 and step % 40 == 0:
            probes += 1
            fa, ca = decide(state, crit)
            sb = {**state, "body": [list(head)]}
            fb, cb = decide(sb, crit)
            sc = {**state, "body": fake_body(random.Random(seed * 97 + step), head, len(snake))}
            fc, cc = decide(sc, crit)
            mad_b = sum(abs(ca[k] - cb[k]) for k in ca) / len(ca)
            mad_c = sum(abs(ca[k] - cc[k]) for k in ca) / len(ca)
            results.append({"seed": seed, "step": step, "ln": len(snake),
                            "true": ca, "p_choice": round(ca[fa], 3),
                            "headonly": fb, "flip_b": fa != fb, "mad_b": round(mad_b, 3),
                            "fake": fc, "flip_c": fa != fc, "mad_c": round(mad_c, 3)})
        choice, probs = decide(state, crit)
        m = meta[choice]
        if not m["safe"]:
            break
        dx, dy = DIRS[choice]
        ate = [head[0] + dx, head[1] + dy] == list(food)
        head, snake = L.step_move(head, snake, choice, ate)
        facing = choice
        if ate:
            food = L.new_food(rng, head, snake)

print(json.dumps(results, ensure_ascii=False, indent=1))
if results:
    n = len(results)
    print(f"N={n}  flip(只剩头)={sum(r['flip_b'] for r in results)/n:.0%}"
          f"  flip(假蛇身)={sum(r['flip_c'] for r in results)/n:.0%}"
          f"  meanMAD 只剩头={sum(r['mad_b'] for r in results)/n:.3f}"
          f"  假蛇身={sum(r['mad_c'] for r in results)/n:.3f}")
