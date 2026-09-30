# -*- coding: utf-8 -*-
"""v3 网格实验：用户的想法——把整个棋盘序列化成 0/1/2/3 矩阵喂给 Laya。

  0=空格  1=蛇身  2=蛇头  3=食物   （12 行，每行 12 个数字）

对照组 = gen1（v2 第一代）：同一 BFS 老师、同 1500 条、同 seed、同训练配方
（unfreeze-6，从原始 laya 底座训 3 epochs），唯一变量 = state 表示。
评测时额外记录 token 数 → 直接回答"矩阵会不会把延迟拖爆"。

跑法（GPU 与 gen5 RL 并发时会自动排队，无碍）：
  python -X utf8 laya_finetune_snake_v3_grid.py
"""
import argparse, json, os, random, sys, time

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import laya_finetune_snake as L
import laya_finetune_snake_v2 as V2

GW, GH, DIRS = L.GW, L.GH, L.DIRS


def grid_state(head, food, snake, facing):
    g = [["0"] * GW for _ in range(GH)]
    for (x, y) in snake[1:]:
        if 0 <= y < GH and 0 <= x < GW:
            g[y][x] = "1"
    g[food[1]][food[0]] = "3"
    g[head[1]][head[0]] = "2"
    return {"game": "snake", "board": f"{GW}x{GH}",
            "grid": ["".join(r) for r in g], "facing": facing}


def rollout_teacher_grid(n_target, seed, cap=1500):
    """与 V2.rollout_teacher 相同的循环，只把 _record 的 state 换成网格。"""
    rng = random.Random(seed)
    samples, ep_foods = [], []
    while len(samples) < n_target:
        snake, food, facing = L.rand_start(rng)
        head = snake[0]
        eaten = 0
        for _ in range(cap):
            cands = L.decide(head, food, snake, facing)
            tm = V2.teacher_move(head, food, snake, facing, cands)
            if tm is None:
                break
            order = cands[:]
            rng.shuffle(order)
            if tm["dir"] in [c["dir"] for c in order]:
                samples.append({
                    "state": grid_state(head, food, snake, facing),
                    "criteria": L.criteria_from(order),
                    "label": [c["dir"] for c in order].index(tm["dir"]),
                })
            if len(samples) >= n_target:
                break
            ex = V2.drive(rng, tm, cands)
            ate = [head[0] + DIRS[ex][0], head[1] + DIRS[ex][1]] == list(food)
            head, snake = L.step_move(head, snake, ex, ate)
            facing = ex
            if ate:
                eaten += 1
                food = L.new_food(rng, head, snake)
        ep_foods.append(eaten)
    return samples[:n_target], ep_foods


def evaluate_grid(agent, games=4, seed=2024, max_steps=800):
    """evaluate_v2 的网格表示版；附带统计 token 数与每步耗时。"""
    from laya.common import build_sequence
    rng = random.Random(seed)
    results, toks, mss = [], [], []
    for _g in range(games):
        snake, food, facing = L.rand_start(rng)
        head = snake[0]
        eaten, cause = 0, "timeout"
        for _ in range(max_steps):
            cands = L.decide(head, food, snake, facing)
            crit = L.criteria_from(cands)
            state = grid_state(head, food, snake, facing)
            q = {"t": "choice", "ins": L.INSTRUCTIONS, "crit": crit}
            n_tok = len(build_sequence(agent.tok, state, q, agent.cfg.get("max_len", 512),
                                       agent.cfg.get("head_max_len", 192))[0])
            toks.append(n_tok)
            t0 = time.time()
            ch, _p = L.model_decide(agent.model, agent.tok, agent.cfg, state, crit)
            mss.append((time.time() - t0) * 1000)
            c = next(x for x in cands if x["dir"] == ch)
            if not c["safe"]:
                cause = "撞死"
                break
            ate = [head[0] + DIRS[ch][0], head[1] + DIRS[ch][1]] == list(food)
            head, snake = L.step_move(head, snake, ch, ate)
            facing = ch
            if ate:
                eaten += 1
                food = L.new_food(rng, head, snake)
        results.append({"food": eaten, "len": len(snake), "cause": cause})
    import statistics as st
    print(f"  token/步: 中位 {st.median(toks):.0f}（对照组 v2 约 200）; "
          f"推理/步: 中位 {st.median(mss):.1f}ms", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1500)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--unfreeze-layers", type=int, default=6)
    ap.add_argument("--lr-enc", type=float, default=5e-5)
    ap.add_argument("--lr-head", type=float, default=2e-4)
    ap.add_argument("--games", type=int, default=8)
    ap.add_argument("--out", default="laya_snake_v3_grid")
    args = ap.parse_args()

    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] 生成网格表示数据 {args.samples} 条（BFS 老师，seed=7 同 gen1）...", flush=True)
    samples, ep_foods = rollout_teacher_grid(args.samples, seed=7)
    print(f"  -> {len(samples)} 条，老师局均 {sum(ep_foods)/len(ep_foods):.1f}，{time.time()-t0:.0f}s", flush=True)
    with open(os.path.join(HERE, "laya_snake_v3_grid_peek.json"), "w", encoding="utf-8") as f:
        json.dump(samples[:2], f, ensure_ascii=False, indent=1)
    print("  样例 state:", json.dumps(samples[0]["state"], ensure_ascii=False), flush=True)

    from laya import Agent
    print(f"[{time.strftime('%H:%M:%S')}] 加载原始 laya 底座（与 gen1 同起点）...", flush=True)
    agent = Agent("convaiinnovations/laya", device="cuda")
    agent.model.eval()

    print(f"[{time.strftime('%H:%M:%S')}] 训练 {args.epochs} epochs（unfreeze-6，同 gen1 配方）...", flush=True)
    V2.train_stage(agent, samples, args, args.epochs, "grid")

    print(f"[{time.strftime('%H:%M:%S')}] 评测 {args.games} 局（贪心，网格输入）...", flush=True)
    r = evaluate_grid(agent, games=args.games, seed=2024, max_steps=800)
    mean = sum(x["food"] for x in r) / len(r)
    print(f"  网格版结果: {r}", flush=True)
    print(f"  平均 {mean:.1f} 食物/局  ←→  对照：gen1(坐标清单) 同配方 4 局 = 17.0", flush=True)
    out = os.path.join(HERE, args.out)
    L.save_checkpoint(agent.model, agent, out)
    with open(os.path.join(out, "evolution_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"gen": "v3网格版", "mode": "全盘0123矩阵输入实验", "rep": "grid",
                   "mean": mean, "this": {"mean": mean},
                   "detail": r, "control": "gen1=17.0(4局,同配方同老师)"}, f,
                  ensure_ascii=False, indent=1)
    print(f"[{time.strftime('%H:%M:%S')}] 已存档 {args.out}", flush=True)


if __name__ == "__main__":
    main()
