# -*- coding: utf-8 -*-
"""v2 进化版：BFS 路径规划老师 + DAgger 自主进化训练。

为什么 v1 容易撞死：老师只是"当前三格打分"（贪心），从不看通往食物的整条路径，
也几乎不进入长蛇后期状态 → 模型学不到"trap"意识。
v2 老师策略（经典蛇类强策略）：
  1) BFS 找通往食物的最短安全路径（尾巴格视为可进入，因为会腾出来）；
  2) 吃完后要还有逃生空间（flood ≥ 蛇长）才真的去吃，否则放弃；
  3) 吃不了就"苟活"：在安全方向里挑可达空间最大的（等于甩尾）。
DAgger 进化循环（每代）：当前模型自己跑 → 模型走过的每个状态让老师补标注
→ 混入新老师数据 → 继续训练 → 评测 → 存档 laya_snake_v2_genN/。
每代评测结果打印成对照表，方便录视频时讲"进化轨迹"。

跑法：
  python laya_finetune_snake_v2.py --probe-teacher          # 只测老师上限（不需要 GPU 训练）
  python laya_finetune_snake_v2.py --rounds 3               # 完整进化（先停掉 laya_bridge 腾显存）
  python laya_finetune_snake_v2.py --eval-only laya_snake_v2_gen2
"""
import argparse, json, os, random, shutil, sys, time
from collections import deque

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import numpy as np
import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import laya_finetune_snake as L

GW, GH, DIRS, NEIGH = L.GW, L.GH, L.DIRS, L.NEIGH


# ── BFS 路径规划老师 ──────────────────────────────────────────────────────────
def bfs_path(head, food, occ):
    """最短路径格序列（从下一步到食物）。occ=禁止进入格集合。无路返回 None。"""
    start, goal = tuple(head), tuple(food)
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        for d in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = (c[0] + d[0], c[1] + d[1])
            if 0 <= nb[0] < GW and 0 <= nb[1] < GH and nb not in occ and nb not in prev:
                prev[nb] = c
                if nb == goal:
                    path = []
                    cur = nb
                    while cur != start:
                        path.append(cur)
                        cur = prev[cur]
                    return path[::-1]
                q.append(nb)
    return None


def follow_path(snake, food, path):
    """逐步模拟沿 path 走到食物（尾巴会腾的格子可以进）。返回吃完后的蛇身；撞了就 None。"""
    s = [list(x) for x in snake]
    for i, cell in enumerate(path):
        cell = list(cell)
        ate = (i == len(path) - 1)
        blocked = {tuple(b) for b in (s if ate else s[:-1])}
        if tuple(cell) in blocked:
            return None
        s = [cell] + s
        if not ate:
            s.pop()
    return s


def teacher_move(head, food, snake, facing, cands):
    """确定性老师。返回 {'dir':..,'mode':'path'|'survive'} 或 None（无路可走）。"""
    safe = [c for c in cands if c["safe"]]
    occ = {tuple(s) for s in snake[:-1]}                            # 尾格下一步会腾出来
    path = bfs_path(head, food, occ)
    if path:
        res = follow_path(snake, food, path)
        nxt = tuple(path[0])
        c = next((c for c in safe
                  if (head[0] + DIRS[c["dir"]][0], head[1] + DIRS[c["dir"]][1]) == nxt), None)
        if res is not None and c is not None:
            nh = res[0]
            sp_after = L.flood(nh[0], nh[1], res)                   # 吃完后还有多大天地
            if sp_after >= len(res) or len(res) <= 4:               # 吃完仍能活 → 去吃
                return {"dir": c["dir"], "mode": "path"}
    if not safe:
        return None
    best = max(safe, key=lambda c: (c["sp"], -c["dc"], -c["fd"]))   # 苟活/甩尾：空间优先
    return {"dir": best["dir"], "mode": "survive"}


def drive(rng, tm, cands, eps=0.08):
    """真正开出去的动作：eps 概率随机换一个安全动作。只扰动轨迹增加状态覆盖，不改标注。"""
    if eps and rng.random() < eps:
        safe = [c for c in cands if c["safe"]]
        if len(safe) > 1:
            return rng.choice(safe)["dir"]
    return tm["dir"]


def _record(samples, head, food, snake, facing, cands, teach_dir, rng):
    order = cands[:]
    rng.shuffle(order)
    if teach_dir not in [c["dir"] for c in order]:
        return
    samples.append({
        "state": {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                  "body": [list(s) for s in snake], "food": list(food), "facing": facing},
        "criteria": L.criteria_from(order),
        "label": [c["dir"] for c in order].index(teach_dir),
    })


def rollout_teacher(n_target, seed, cap=1500, deep_preplay=False):
    """老师亲自开车收集状态；episode 结束条件：死或达到步数上限。
    deep_preplay：先让老师无记录地吃到随机 15~45 个，再从残局开始采样
    （纯新手局数据全是短蛇状态，模型遇到长蛇就懵 → 后期状态覆盖不足）。"""
    rng = random.Random(seed)
    samples, ep_foods = [], []
    while len(samples) < n_target:
        snake, food, facing = L.rand_start(rng)
        head = snake[0]
        eaten = 0
        pre_target = rng.randint(15, 45) if deep_preplay else 0
        pre = 0
        while pre < pre_target:
            cands = L.decide(head, food, snake, facing)
            tm = teacher_move(head, food, snake, facing, cands)
            if tm is None:
                break
            ate = [head[0] + DIRS[tm["dir"]][0], head[1] + DIRS[tm["dir"]][1]] == list(food)
            head, snake = L.step_move(head, snake, tm["dir"], ate)
            facing = tm["dir"]
            if ate:
                pre += 1
                food = L.new_food(rng, head, snake)
        for _ in range(cap):
            cands = L.decide(head, food, snake, facing)
            tm = teacher_move(head, food, snake, facing, cands)
            if tm is None:
                break
            _record(samples, head, food, snake, facing, cands, tm["dir"], rng)
            if len(samples) >= n_target:
                break
            ex = drive(rng, tm, cands)                              # 开出去的可带随机扰动
            ate = [head[0] + DIRS[ex][0], head[1] + DIRS[ex][1]] == list(food)
            head, snake = L.step_move(head, snake, ex, ate)
            facing = ex
            if ate:
                eaten += 1
                food = L.new_food(rng, head, snake)
        ep_foods.append(eaten)
    return samples[:n_target], ep_foods


def rollout_model_then_label(agent, n_target, seed, cap=1500, deep_preplay=False):
    """DAgger：模型自己开车（会撞），走过的每个状态都由老师补正确标注。
    deep_preplay：先由老师开到残局（长蛇），再换学生接管 → 纠偏发生在真正危险的局面。"""
    rng = random.Random(seed)
    samples, ep_foods, modes = [], [], {"path": 0, "survive": 0}
    while len(samples) < n_target:
        snake, food, facing = L.rand_start(rng)
        head = snake[0]
        eaten = 0
        pre = rng.randint(10, 40) if deep_preplay else 0
        while pre > 0:
            cands = L.decide(head, food, snake, facing)
            tm = teacher_move(head, food, snake, facing, cands)
            if tm is None:
                break
            ate = [head[0] + DIRS[tm["dir"]][0], head[1] + DIRS[tm["dir"]][1]] == list(food)
            head, snake = L.step_move(head, snake, tm["dir"], ate)
            facing = tm["dir"]
            if ate:
                pre -= 1
                food = L.new_food(rng, head, snake)
        for _ in range(cap):
            cands = L.decide(head, food, snake, facing)
            crit = L.criteria_from(cands)
            state = {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                     "body": [list(s) for s in snake], "food": list(food), "facing": facing}
            ch, _p = L.model_decide(agent.model, agent.tok, agent.cfg, state, crit)
            tm = teacher_move(head, food, snake, facing, cands)
            if tm is None:
                break
            modes[tm["mode"]] += 1
            _record(samples, head, food, snake, facing, cands, tm["dir"], rng)  # 老师标注（含致命状态→纠偏样本）
            if len(samples) >= n_target:
                break
            c = next(x for x in cands if x["dir"] == ch)
            if not c["safe"]:
                break                                          # 学生自己撞了 → 本局结束，下局重来
            ate = [head[0] + DIRS[ch][0], head[1] + DIRS[ch][1]] == list(food)
            head, snake = L.step_move(head, snake, ch, ate)
            facing = ch
            if ate:
                eaten += 1
                food = L.new_food(rng, head, snake)
        ep_foods.append(eaten)
    return samples[:n_target], ep_foods, modes


# ── 评测（带死因统计）─────────────────────────────────────────────────────────
def evaluate_v2(agent, games=4, seed=2024, max_steps=800):
    rng = random.Random(seed)
    results = []
    for _g in range(games):
        snake, food, facing = L.rand_start(rng)
        head = snake[0]
        eaten = 0
        cause = "timeout"
        for _ in range(max_steps):
            cands = L.decide(head, food, snake, facing)
            crit = L.criteria_from(cands)
            state = {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                     "body": [list(s) for s in snake], "food": list(food), "facing": facing}
            ch, _p = L.model_decide(agent.model, agent.tok, agent.cfg, state, crit)
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
    return results


# ── 训练一个阶段 ──────────────────────────────────────────────────────────────
def train_stage(agent, samples, args, epochs, tag):
    from laya.common import build_sequence, collate_items
    items = [it for it in (L.make_item(agent, s, build_sequence, collate_items) for s in samples) if it]
    print(f"  [{tag}] train items={len(items)} epochs={epochs}", flush=True)
    model, device = agent.model, agent.device
    for p in model.encoder.parameters():
        p.requires_grad_(False)
    enc_layers = None
    for m in model.encoder.modules():
        if isinstance(m, torch.nn.ModuleList) and len(m) >= args.unfreeze_layers:
            enc_layers = m
            break
    nl = len(enc_layers)
    tail = nl - args.unfreeze_layers
    for l in list(enc_layers)[tail:]:
        for p in l.parameters():
            p.requires_grad_(True)
    enc_layers[tail].register_forward_pre_hook(lambda mod, inp: (inp[0].detach(),) + tuple(inp[1:]))
    enc_tail = [p for l in list(enc_layers)[tail:] for p in l.parameters()]
    head_params = [p for n2, p in model.named_parameters()
                   if not n2.startswith("encoder.") and p.requires_grad]
    opt = torch.optim.AdamW([{"params": head_params, "lr": args.lr_head},
                             {"params": enc_tail, "lr": args.lr_enc, "weight_decay": 0.01}])
    n_steps = epochs * ((len(items) + args.batch - 1) // args.batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[args.lr_head, args.lr_enc],
                                                total_steps=n_steps + 10)
    rng = random.Random(int(time.time()) & 0xffff)
    step, t0 = 0, time.time()
    for ep in range(epochs):
        model.train()
        perm = list(range(len(items)))
        rng.shuffle(perm)
        run = cnt = 0.0
        accs = []
        for i in range(0, len(items), args.batch):
            batch = [items[j] for j in perm[i:i + args.batch]]
            b = collate_items([batch], agent.tok.pad_token_id)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                logits, _ = model(b["input_ids"].to(device), b["attention_mask"].to(device),
                                  b["marker_pos"].to(device), b["marker_mask"].to(device),
                                  b["qtype"].to(device))
            loss = F.cross_entropy(logits, b["label"].to(device))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            run += float(loss); cnt += 1; step += 1
            if step % 25 == 0:
                acc = float((logits.argmax(-1) == b["label"].to(device)).float().mean())
                accs.append(acc)
                print(f"    {tag} ep{ep} {step}/{n_steps} loss={run/cnt:.4f} acc={acc:.2f} "
                      f"{time.time()-t0:.0f}s", flush=True)
    model.eval()
    return step


def save_gen(agent, outdir, meta):
    L.save_checkpoint(agent.model, agent, outdir)
    with open(os.path.join(outdir, "evolution_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--teacher-samples", type=int, default=1500)
    ap.add_argument("--dagger-samples", type=int, default=900)
    ap.add_argument("--epochs-first", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--unfreeze-layers", type=int, default=6)
    ap.add_argument("--lr-enc", type=float, default=5e-5)
    ap.add_argument("--lr-head", type=float, default=2e-4)
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--eval-steps", type=int, default=800)
    ap.add_argument("--base", default="convaiinnovations/laya")
    ap.add_argument("--resume", default=None, help="继续从某个 gen 目录进化")
    ap.add_argument("--gen-offset", type=int, default=0, help="resume 时新存档的编号偏移（防覆盖）")
    ap.add_argument("--probe-teacher", action="store_true", help="只测老师策略上限（纯 CPU 快）")
    ap.add_argument("--deep", action="store_true", help="后期轮次：先开到残局（长蛇）再采样，补足后期状态")
    ap.add_argument("--eval-only", default=None)
    args = ap.parse_args()

    if args.probe_teacher:
        rng = random.Random(5)
        foods = []
        for g in range(6):
            snake, food, facing = L.rand_start(rng)
            head = snake[0]
            eaten = 0
            for _ in range(2000):
                cands = L.decide(head, food, snake, facing)
                tm = teacher_move(head, food, snake, facing, cands)
                if tm is None:
                    break
                ate = [head[0] + DIRS[tm["dir"]][0], head[1] + DIRS[tm["dir"]][1]] == list(food)
                head, snake = L.step_move(head, snake, tm["dir"], ate)
                facing = tm["dir"]
                if ate:
                    eaten += 1
                    food = L.new_food(rng, head, snake)
            foods.append(eaten)
        print(f"TEACHER(BFS+苟活) foods/game = {foods}  mean={np.mean(foods):.1f}", flush=True)
        return

    if args.eval_only:
        from laya import Agent
        ag = Agent(os.path.join(HERE, args.eval_only) if not os.path.isabs(args.eval_only) else args.eval_only,
                   device="cuda")
        res = evaluate_v2(ag, games=args.games, max_steps=args.eval_steps)
        print("EVAL", args.eval_only, res, flush=True)
        return

    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] 先测老师上限…", flush=True)
    trng = random.Random(5)
    tfoods = []
    for g in range(3):
        snake, food, facing = L.rand_start(trng)
        head = snake[0]
        eaten = 0
        for _ in range(2000):
            cands = L.decide(head, food, snake, facing)
            tm = teacher_move(head, food, snake, facing, cands)
            if tm is None:
                break
            ate = [head[0] + DIRS[tm["dir"]][0], head[1] + DIRS[tm["dir"]][1]] == list(food)
            head, snake = L.step_move(head, snake, tm["dir"], ate)
            facing = tm["dir"]
            if ate:
                eaten += 1
                food = L.new_food(trng, head, snake)
        tfoods.append(eaten)
    print(f"  老师(BFS) 3 局 = {tfoods} mean={np.mean(tfoods):.1f}（这是学生理论天花板）", flush=True)

    from laya import Agent
    start = os.path.join(HERE, args.resume) if args.resume else args.base
    print(f"[{time.strftime('%H:%M:%S')}] loading base agent: {start}", flush=True)
    agent = Agent(start, device="cuda")
    agent.model.eval()

    hist = []
    for r0 in range(1, args.rounds + 1):
        r = r0 + args.gen_offset
        tag = f"gen{r}"
        print(f"\n[{time.strftime('%H:%M:%S')}] ===== 进化第 {r} 代 =====", flush=True)
        if r == 1 and not args.resume:
            samples, ep_foods = rollout_teacher(args.teacher_samples, seed=11)
            print(f"  老师自采 {len(samples)} 条（每局吃到 {ep_foods[-6:]}…）", flush=True)
            epochs = args.epochs_first
        else:
            s1, ef, modes = rollout_model_then_label(agent, args.dagger_samples, seed=100 + r,
                                                     deep_preplay=args.deep)
            s2, _ = rollout_teacher(args.teacher_samples // 2, seed=200 + r, deep_preplay=args.deep)
            samples = s1 + s2
            random.Random(r).shuffle(samples)
            print(f"  DAgger {len(s1)} 条（学生走过的状态, 老师标注, 模式={modes}）+ 老师新数据 {len(s2)}", flush=True)
            epochs = args.epochs
        steps = train_stage(agent, samples, args, epochs, tag)
        res = evaluate_v2(agent, games=args.games, seed=2024 + r, max_steps=args.eval_steps)
        mean = float(np.mean([x["food"] for x in res]))
        hist.append({"gen": tag, "foods": [x["food"] for x in res], "mean": round(mean, 1),
                     "detail": res, "data": len(samples), "train_steps": steps})
        outdir = os.path.join(HERE, f"laya_snake_v2_gen{r}")
        save_gen(agent, outdir, {"gen": tag, "teacher_mean": float(np.mean(tfoods)),
                                 "history_prev": hist[:-1], "this": hist[-1],
                                 "recipe": {"unfreeze": args.unfreeze_layers, "lr_enc": args.lr_enc,
                                            "lr_head": args.lr_head, "epochs": epochs}})
        print(f"  [{tag}] foods/game={[x['food'] for x in res]} mean={mean:.1f} 用时 {time.time()-t0:.0f}s", flush=True)
        print("  ── 进化轨迹 ──", flush=True)
        for h in hist:
            print(f"    {h['gen']}: mean {h['mean']:5.1f}   {h['foods']}", flush=True)
    print("\nALL DONE", json.dumps(hist, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
