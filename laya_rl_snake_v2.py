# -*- coding: utf-8 -*-
"""gen5：纯强化学习（REINFORCE / 蒙特卡洛回报），无老师。

思路（就是用户说的"每次死亡经验为下次提供建议"）：
  1) 模型自己按概率开车（采样，带温度 τ，会走弯路也会撞）；
  2) 每步记回报 G_t = 从现在起还能吃到的食物数 × γ^Δ - 撞死惩罚（γ<1：越近的步越贴奖）；
  3) 一轮收集几十局 → 全体回报标准化成优势 A → 截断策略梯度（PPO 式）：
     高分轨迹里的动作被强化、自杀轨迹里的被抑制，且概率比超出 ±20% 就不再给梯度；
  4) 更新后贪心评测，超过冠军就存档。起点权重 = gen3 冠军（SFT+DAgger 打底），
     RL 阶段直接把"吃食物"作为唯一目标，不模仿任何老师。

实测教训（v1.0 纯 REINFORCE 跑崩：21.5 → 12.0，第二遍更新把策略拽飞、12/12 撞死）：
  v1.1 加固三件套 = PPO 概率比截断（±clip 之外不再收梯度）
               + 自我模仿锚（本批优势>0 的样本加 CE，好棋焊牢防遗忘，仍然无老师）
               + 更保守的学习率/单遍更新。

跑法（先停 laya_bridge 腾显存）：
  python laya_rl_snake_v2.py --rounds 3
"""
import argparse, json, os, random, sys, time

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import laya_finetune_snake as L

GW, GH, DIRS = L.GW, L.GH, L.DIRS


def _log(x):
    print(x, flush=True)


# ── 采样一个动作（同时拿到可直接训练用的 item，避免重复分词）────────────────────
def sample_step(agent, state, crit, temp):
    from laya.common import build_sequence, collate_items
    keys = list(crit.keys())
    q = {"t": "choice", "ins": L.INSTRUCTIONS, "crit": crit}
    seq, markers = build_sequence(agent.tok, state, q,
                                  agent.cfg.get("max_len", 512), agent.cfg.get("head_max_len", 192))
    if len(markers) != len(keys):
        return None, None, None
    b = collate_items([[{"ids": seq, "markers": markers, "qtype": 0}]], agent.tok.pad_token_id)
    device = agent.device
    with torch.no_grad(), torch.autocast(device_type="cuda", dtype=torch.bfloat16):
        logits, _ = agent.model(b["input_ids"].to(device), b["attention_mask"].to(device),
                                b["marker_pos"].to(device), b["marker_mask"].to(device),
                                b["qtype"].to(device))
    z = logits[0, :len(keys)].float()
    bucket = "choice:2" if len(keys) == 2 else ("choice:3-5" if len(keys) <= 5 else "choice:6-10")
    t_scale = float(agent.cfg.get("temperature_by_options", {}).get(bucket, 1.0))
    p = torch.softmax(z / max(1e-3, t_scale) / temp, -1)
    idx = int(torch.multinomial(p, 1).item())
    item = {"ids": seq, "markers": markers, "qtype": 0, "label": idx}
    return idx, item, float(p[idx].log())          # old_logp：行为策略(含探索温度)下的概率


def rollout(agent, episodes, cap, temp, seed, r_food, death_pen, gamma):
    """自己开车收集 (item, old_logp, 回报G)。G = 该步之后吃到的食物折现和 - 撞死惩罚。"""
    rng = random.Random(seed)
    items, oldlps, rets, eps_stat = [], [], [], []
    model = agent.model
    model.eval()
    for e in range(episodes):
        snake, food, facing = L.rand_start(rng)
        head = snake[0]
        ep, eaten, died = [], 0, False
        for _ in range(cap):
            cands = L.decide(head, food, snake, facing)
            crit = L.criteria_from(cands)
            state = {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                     "body": [list(s) for s in snake], "food": list(food), "facing": facing}
            idx, item, lp = sample_step(agent, state, crit, temp)
            if item is None:
                break
            ch = list(crit.keys())[idx]
            ep.append((item, lp, 0.0))                  # reward 挂在"吃到那一步"
            c = next(x for x in cands if x["dir"] == ch)
            if not c["safe"]:
                died = True
                ep[-1] = (ep[-1][0], ep[-1][1], -death_pen)   # 撞死惩罚记在选择它的那一步
                break
            ate = [head[0] + DIRS[ch][0], head[1] + DIRS[ch][1]] == list(food)
            head, snake = L.step_move(head, snake, ch, ate)
            facing = ch
            if ate:
                eaten += 1
                ep[-1] = (ep[-1][0], ep[-1][1], float(r_food))
                food = L.new_food(rng, head, snake)
        # 折扣回报 G_t（从后往前累加）
        G, g = [], 0.0
        for _it, _lp, r in reversed(ep):
            g = r + gamma * g
            G.append(g)
        G.reverse()
        for (it, lpv, _r), gv in zip(ep, G):
            items.append(it)
            oldlps.append(lpv)
            rets.append(gv)
        eps_stat.append({"food": eaten, "len": len(snake), "cause": "撞死" if died else "timeout"})
        _log(f"  局{e+1}/{episodes}: 吃{eaten} 长{len(snake)} {'撞死' if died else '步数上限'} "
             f"(累计样本 {len(items)})")
    return items, oldlps, rets, eps_stat


# ── 策略梯度更新（unfreeze-6 + 边界 detach，和 SFT 同一省显存配方）─────────────
def set_trainable(agent, unfreeze):
    model = agent.model
    for p in model.encoder.parameters():
        p.requires_grad_(False)
    enc_layers = None
    for m in model.encoder.modules():
        if isinstance(m, torch.nn.ModuleList) and len(m) >= unfreeze:
            enc_layers = m
            break
    nl = len(enc_layers)
    tail = nl - unfreeze
    for l in list(enc_layers)[tail:]:
        for p in l.parameters():
            p.requires_grad_(True)
    enc_layers[tail].register_forward_pre_hook(lambda mod, inp: (inp[0].detach(),) + tuple(inp[1:]))
    enc_tail = [p for l in list(enc_layers)[tail:] for p in l.parameters()]
    head_params = [p for n2, p in model.named_parameters()
                   if not n2.startswith("encoder.") and p.requires_grad]
    return enc_tail, head_params


def rl_update(agent, items, oldlps, advs, temp, args, tag):
    """PPO 截断的蒙特卡洛策略梯度 + 自我模仿锚。
    - 截断：概率比 ratio 只允许偏离采样策略 ±clip%，第 2 遍更新不再能越改越偏；
    - 自我模仿(teacher-free)：本批里优势>0 的样本额外加一份交叉熵，把"好棋"焊牢，防遗忘。"""
    from laya.common import collate_items
    model, device = agent.model, agent.device
    tcfg = agent.cfg.get("temperature_by_options", {})
    enc_tail, head_params = set_trainable(agent, args.unfreeze_layers)
    opt = torch.optim.AdamW([{"params": head_params, "lr": args.lr_head},
                             {"params": enc_tail, "lr": args.lr_enc, "weight_decay": 0.01}])
    n = len(items)
    n_steps = args.passes * ((n + args.batch - 1) // args.batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[args.lr_head, args.lr_enc],
                                                total_steps=n_steps + 10)
    rng = random.Random(int(time.time()) & 0xffff)
    step, t0 = 0, time.time()
    for ep in range(args.passes):
        model.train()
        perm = list(range(n))
        rng.shuffle(perm)
        run = cnt = ce_run = ratio_hi = 0.0
        for i in range(0, n, args.batch):
            bb = perm[i:i + args.batch]
            batch = [items[j] for j in bb]
            a = torch.tensor([advs[j] for j in bb], device=device)
            old = torch.tensor([oldlps[j] for j in bb], device=device)
            # 每个样本按选项数取库里自带的温度桶，再除探索温度 → 与采样时同分布
            ts = torch.tensor([float(tcfg.get("choice:2" if len(it["markers"]) == 2 else "choice:3-5", 1.0))
                               for it in batch], device=device)[:, None]
            b = collate_items([batch], agent.tok.pad_token_id)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                logits, _ = model(b["input_ids"].to(device), b["attention_mask"].to(device),
                                  b["marker_pos"].to(device), b["marker_mask"].to(device),
                                  b["qtype"].to(device))
            lf = logits.float()
            lab = b["label"].to(device)
            lp_t = torch.log_softmax(lf / ts.clamp_min(1e-3) / temp, -1).gather(1, lab[:, None]).squeeze(1)
            ratio = (lp_t - old).exp()
            s1 = ratio * a
            s2 = ratio.clamp(1 - args.clip, 1 + args.clip) * a
            pg = -torch.minimum(s1, s2).mean()                        # PPO 截断目标
            pos = a > 0
            ce = F.cross_entropy(lf[pos], lab[pos]) if bool(pos.any()) else lf.sum() * 0
            ent = -(torch.softmax(lf, -1) * torch.log_softmax(lf, -1)).sum(-1).mean()
            loss = pg + args.sil * ce - args.ent * ent
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            run += float(loss.detach()); ce_run += float(ce.detach())
            ratio_hi += float((ratio.detach() > 1 + args.clip).float().mean()); cnt += 1; step += 1
            if step % 25 == 0:
                _log(f"    {tag} ep{ep} {step}/{n_steps} loss={run/cnt:+.4f} sil={ce_run/cnt:.3f} "
                     f"截断率={ratio_hi/cnt:.2f} 熵={float(ent.detach()):.3f} {time.time()-t0:.0f}s")
    model.eval()
    return step


def greedy_eval(agent, games, seed, max_steps):
    from laya_finetune_snake_v2 import evaluate_v2
    return evaluate_v2(agent, games=games, seed=seed, max_steps=max_steps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", default="laya_snake_v2_gen3", help="起点权重目录")
    ap.add_argument("--out", default="laya_snake_v2_gen5")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--episodes", type=int, default=12, help="每轮收集局数")
    ap.add_argument("--cap", type=int, default=400, help="每局步数上限")
    ap.add_argument("--temp", type=float, default=1.4, help="采样温度（探索强度）")
    ap.add_argument("--r-food", type=float, default=1.0)
    ap.add_argument("--death-pen", type=float, default=2.0)
    ap.add_argument("--gamma", type=float, default=0.995)
    ap.add_argument("--max-samples", type=int, default=4000, help="每轮训练样本上限（均匀子采样）")
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--unfreeze-layers", type=int, default=6)
    ap.add_argument("--lr-enc", type=float, default=5e-6)
    ap.add_argument("--lr-head", type=float, default=2e-5)
    ap.add_argument("--ent", type=float, default=0.005)
    ap.add_argument("--clip", type=float, default=0.2, help="PPO 概率比截断幅度")
    ap.add_argument("--sil", type=float, default=0.3, help="自我模仿锚权重（优势>0 样本的 CE）")
    ap.add_argument("--eval-games", type=int, default=8)
    ap.add_argument("--eval-steps", type=int, default=800)
    ap.add_argument("--eval-only", default=None)
    ap.add_argument("--save-always", default=None, metavar="DIR",
                    help="每轮更新后把当前权重存进 DIR（最新版预览用，独立于冠军存档）")
    args = ap.parse_args()

    from laya import Agent
    start = args.resume if os.path.isabs(args.resume) else os.path.join(HERE, args.resume)
    _log(f"[{time.strftime('%H:%M:%S')}] 加载起点权重 {start} (cuda)...")
    agent = Agent(start, device="cuda")
    agent.model.eval()

    if args.eval_only:
        r = greedy_eval(agent, args.eval_games, 2024, args.eval_steps)
        _log("EVAL " + json.dumps(r, ensure_ascii=False))
        return

    base = greedy_eval(agent, args.eval_games, 2024, args.eval_steps)
    best = sum(x["food"] for x in base) / len(base)
    _log(f"起点贪心评测: 平均 {best:.1f} 食物/局  " + str([x["food"] for x in base]))

    history = [{"gen": os.path.basename(start), "mean": best, "detail": base}]
    rng = random.Random(4321)
    for rd in range(args.rounds):
        t0 = time.time()
        _log(f"[{time.strftime('%H:%M:%S')}] ── 第 {rd+1}/{args.rounds} 轮 RL：收集 {args.episodes} 局"
             f"（τ={args.temp}）──")
        items, oldlps, rets, stat = rollout(agent, args.episodes, args.cap, args.temp,
                                            rng.randint(0, 10**8), args.r_food, args.death_pen, args.gamma)
        mean_ep = sum(s["food"] for s in stat) / len(stat)
        deaths = sum(1 for s in stat if s["cause"] == "撞死")
        _log(f"  采样局均吃 {mean_ep:.1f}，撞死 {deaths}/{args.episodes}，样本 {len(items)}，"
             f"用时 {time.time()-t0:.0f}s")
        if len(items) > args.max_samples:                   # 均匀子采样控制更新成本
            keep = sorted(rng.sample(range(len(items)), args.max_samples))
            items = [items[i] for i in keep]
            oldlps = [oldlps[i] for i in keep]
            rets = [rets[i] for i in keep]
        t = torch.tensor(rets)
        advs = ((t - t.mean()) / (t.std() + 1e-6)).tolist() # 优势标准化
        _log(f"[{time.strftime('%H:%M:%S')}] PPO 截断更新 {args.passes} passes (clip={args.clip} sil={args.sil})...")
        rl_update(agent, items, oldlps, advs, args.temp, args, f"rl{rd+1}")
        r = greedy_eval(agent, args.eval_games, 2024, args.eval_steps)
        mean = sum(x["food"] for x in r) / len(r)
        _log(f"  更新后贪心评测: 平均 {mean:.1f} 食物/局  " + str([x["food"] for x in r]))
        history.append({"gen": f"rl-round{rd+1}", "mean": mean, "detail": r})
        if args.save_always:                              # 每轮都存最新版，供网页预览（不管涨跌）
            sd = args.save_always if os.path.isabs(args.save_always) else os.path.join(HERE, args.save_always)
            L.save_checkpoint(agent.model, agent, sd)
            with open(os.path.join(sd, "evolution_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"gen": f"gen5-latest-第{rd+1}轮", "mode": "RL v1.1 最新预览",
                           "mean": mean, "detail": r, "base": os.path.basename(start)},
                          f, ensure_ascii=False, indent=1)
            _log(f"  最新版已存 {sd}（第 {rd+1} 轮，平均 {mean:.1f}）")
        if mean > best:
            best = mean
            L.save_checkpoint(agent.model, agent, args.out if os.path.isabs(args.out)
                              else os.path.join(HERE, args.out))
            with open(os.path.join(HERE, args.out, "evolution_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"gen": "gen5-rl", "mode": "纯强化学习(REINFORCE，无老师)",
                           "base": os.path.basename(start), "reward": f"+{args.r_food}/食物 -{args.death_pen}/撞死",
                           "best_mean": best, "history": history}, f, ensure_ascii=False, indent=1)
            _log(f"  ✓ 新高！已存档 {args.out}（平均 {best:.1f}）")

    _log("\n进化轨迹：")
    for h in history:
        _log(f"  {h['gen']:<18} 平均 {h['mean']:.1f} 食物/局")


if __name__ == "__main__":
    main()
