# -*- coding: utf-8 -*-
"""Laya 贪吃蛇 RLCD 训练 —— 官方配方( notebooks/train_ddp.py + docs/finetune_browser_agent.md )
输入契约(定稿): 短规则(不截断) + 0/1/2/3 棋盘 state + 每选项"落点坐标+free/body/wall+NEARER/FARTIER"
老师(BFS)只产标签, 绝不进输入。
用法:
  python _rlcd_snake.py gen   --out _rlcd/run1 --games-t 60 --games-r 30 --games-p 40
  python _rlcd_snake.py train --in _rlcd/run1 --epochs 3
  python _rlcd_snake.py eval  --in _rlcd/run1 --games 8
"""
import argparse, json, math, os, random, sys, time
import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import load_file, save_file

GW = GH = 12
MAXSTEPS = 220
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
ORDER = ['UP', 'DOWN', 'LEFT', 'RIGHT']

# ── 契约(和 _opt_eval2.py / 页面完全一致) ────────────────────────────────
SHORT = ("Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. "
         "Row 0 top, row 11 bottom. UP=row-1, DOWN=row+1, LEFT=col-1, RIGHT=col+1. "
         "Pick the direction that moves the head toward the food without dying.")

def grid_rows(snake, food):
    g = [['0'] * GW for _ in range(GH)]
    for i, (x, y) in enumerate(snake):
        g[y][x] = '2' if i == 0 else '1'
    g[food[1]][food[0]] = '3'
    return [''.join(r) for r in g]

def state_of(snake, food):
    return {'game': 'snake', 'board': '12x12', 'grid': grid_rows(snake, food)}

def compact(snake, food, d):
    hx, hy = snake[0]; dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
    if not (0 <= nx < GW and 0 <= ny < GH): land = 'wall'
    elif (nx, ny) in snake[:-1] or ((nx, ny) == snake[-1] and food == (nx, ny)): land = 'body'
    elif (nx, ny) == snake[-1]: land = 'vacating'
    else: land = 'free'
    dn = abs(nx - food[0]) + abs(ny - food[1]); dc = abs(hx - food[0]) + abs(hy - food[1])
    rel = 'NEARER to food' if dn < dc else ('FARTHER from food' if dn > dc else 'SAME distance')
    return f"({nx},{ny}) {land}, {rel}"

def crit_of(snake, food):
    return {d: compact(snake, food, d) for d in ORDER}

# ── 环境 ───────────────────────────────────────────────────────────────
def place_food(rng, snake):
    occ = set(snake)
    free = [(x, y) for x in range(GW) for y in range(GH) if (x, y) not in occ]
    return rng.choice(free) if free else None

def step_snake(snake, food, d):
    """返回 (new_snake, died, ate)"""
    hx, hy = snake[0]; dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
    eat = (nx, ny) == food
    body = snake if eat else snake[:-1]
    if not (0 <= nx < GW and 0 <= ny < GH): return snake, True, False
    if (nx, ny) in body: return snake, True, False
    ns = [(nx, ny)] + list(snake)
    if not eat: ns.pop()
    return ns, False, eat

# ── BFS 老师(只出标签) ─────────────────────────────────────────────────
def flood_space(head, blocked):
    seen = {head}; stack = [head]; b = set(blocked)
    n = 0
    while stack:
        x, y = stack.pop(); n += 1
        for dx, dy in DIRS.values():
            p = (x + dx, y + dy)
            if 0 <= p[0] < GW and 0 <= p[1] < GH and p not in b and p not in seen:
                seen.add(p); stack.append(p)
    return n

def bfs_dist(head, food, blocked):
    from collections import deque
    b = set(blocked)
    if head == food: return 0
    q = deque([(head, 0)]); seen = {head}
    while q:
        (x, y), d = q.popleft()
        for dx, dy in DIRS.values():
            p = (x + dx, y + dy)
            if not (0 <= p[0] < GW and 0 <= p[1] < GH) or p in b or p in seen: continue
            if p == food: return d + 1
            seen.add(p); q.append((p, d + 1))
    return None

def teacher_scores(snake, food):
    """每个方向的老师分。撞死 -1000; 能到食物按距离, 不能按空间; 空间不足重罚(防自围)。"""
    out = []
    for d in ORDER:
        hx, hy = snake[0]; dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
        eat = (nx, ny) == food
        body = snake if eat else snake[:-1]
        if not (0 <= nx < GW and 0 <= ny < GH) or (nx, ny) in body:
            out.append(-1000.0); continue
        ns = [(nx, ny)] + list(snake)
        if not eat: ns.pop()
        space = flood_space(ns[0], ns[1:])
        dist = bfs_dist(ns[0], food, ns[1:])
        if dist is None:
            sc = -25.0 + space * 0.5
        else:
            sc = 40.0 - dist * 2.0 + space * 0.3
        if space < len(ns) * 1.3:
            sc -= (len(ns) * 1.3 - space) * 4.0
        out.append(sc)
    return out

T_SOFT = 2.5
def gold_dist(scores):
    m = max(scores)
    e = [math.exp((s - m) / T_SOFT) for s in scores]
    z = sum(e)
    return [v / z for v in e]

# ── 采样造数据 ─────────────────────────────────────────────────────────
def build_item(agent, snake, food):
    from laya.common import build_sequence, render_options, QTYPES
    crit = crit_of(snake, food)
    q = {"t": "choice", "ins": SHORT, "crit": crit}
    seq, markers = build_sequence(agent.tok, state_of(snake, food), q, 512, 256)
    if len(markers) != 4:
        return None
    sc = teacher_scores(snake, food)
    tgt = gold_dist(sc)
    return {"ids": seq, "markers": markers, "qtype": QTYPES["choice"],
            "target": tgt, "label": max(range(4), key=lambda i: sc[i])}

def collect_rollouts(agent, policy, n_games, seed, cap=8):
    """policy: 'teacher'|'random'|'onpolicy'。状态用契约记录, 标签永远来自 BFS 老师。"""
    rng = random.Random(seed)
    items, stats = [], []
    for g in range(n_games):
        if policy == 'random' and g % 3 == 0: MAXS = 40   # 随机局基本秒死, 短跑多开几局换初盘负面样本
        else: MAXS = MAXSTEPS
        snake = [(6, 6), (5, 6), (4, 6)]; food = place_food(rng, snake)
        eaten = 0; cause = 'timeout'
        for _ in range(MAXS):
            sc = teacher_scores(snake, food)
            it = build_item(agent, snake, food)
            if it: items.append(it)
            if policy == 'teacher':
                top = max(sc)
                best = [i for i, s in enumerate(sc) if s >= top - 1e-9]
                alive = [i for i, s in enumerate(sc) if s > -500]
                ch = ORDER[rng.choice(best)] if rng.random() < 0.9 or not alive else ORDER[rng.choice(alive)]
            elif policy == 'random':
                ch = rng.choice(ORDER)
            else:
                j = agent.system_one(state_of(snake, food),
                                     {"a": {"type": "choice", "instructions": SHORT, "criteria": crit_of(snake, food)}})
                ch = j["answers"]["a"]["choice"]
            snake, died, eat = step_snake(snake, food, ch)
            if died: cause = 'died'; break
            if eat:
                eaten += 1; food = place_food(rng, snake)
        stats.append(eaten)
    return items, stats

# ── 官方 RLCD 训练循环(单卡版) ─────────────────────────────────────────
def collate_train_batch(items, pad_id):
    n, L = len(items), max(len(it["ids"]) for it in items)
    kmax = max(len(it["markers"]) for it in items)
    ids = torch.full((n, L), pad_id, dtype=torch.long)
    att = torch.zeros((n, L), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    target = torch.zeros((n, kmax), dtype=torch.float32)
    for i, it in enumerate(items):
        ids[i, :len(it["ids"])] = torch.tensor(it["ids"])
        att[i, :len(it["ids"])] = 1
        k = len(it["markers"])
        mpos[i, :k] = torch.tensor(it["markers"]); mmask[i, :k] = True
        target[i, :k] = torch.tensor(it["target"], dtype=torch.float32)
    return {"input_ids": ids, "attention_mask": att, "marker_pos": mpos,
            "marker_mask": mmask, "target": target,
            "qtype": torch.tensor([it["qtype"] for it in items]),
            "label": torch.tensor([it["label"] for it in items])}

def fit_one_temp(sel):
    if len(sel) < 10: return 1.0
    kmax = max(len(z) for z, _ in sel)
    Z = torch.full((len(sel), kmax), -1e4); T = torch.zeros((len(sel), kmax))
    for i, (z, t) in enumerate(sel):
        Z[i, :len(z)] = torch.tensor(z); T[i, :len(t)] = torch.tensor(t, dtype=torch.float32)
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)
    def closure():
        opt.zero_grad()
        loss = -(T * torch.log_softmax(Z / log_t.exp(), -1)).sum(-1).mean()
        loss.backward(); return loss
    opt.step(closure)
    return float(torch.clamp(log_t.exp(), 0.1, 10.0).item())

def load_agent(path, device="cuda"):
    from laya import Agent
    ag = Agent(path, device=device)
    return ag

def train(args):
    from laya.common import proper_reward, QTYPES
    run = args.run
    device = torch.device("cuda")
    ag = load_agent(args.base)
    mdir = args.base if os.path.isdir(args.base) else __import__("huggingface_hub").snapshot_download(args.base)
    mdir = args.base if os.path.isdir(args.base) else __import__("huggingface_hub").snapshot_download(args.base)
    model = ag.model.to(device); model.train()
    cfg = ag.cfg
    cfg["max_len"] = 512; cfg["head_max_len"] = 256

    items = torch.load(os.path.join(run, "items.pt"), weights_only=False)
    order = list(range(len(items)))
    random.Random(20260922).shuffle(order)
    n_calib = min(400, len(items) // 10)
    calib = [items[i] for i in sorted(order[:n_calib])]
    train_items = [items[i] for i in sorted(order[n_calib:])]
    print(f"train {len(train_items)} items | calib {len(calib)} | epochs {args.epochs}", flush=True)

    MICRO, ACCUM, GRP = 8, 8, 4
    LR_ENC, LR_HEAD = 2.5e-5, 1.0e-4
    S0, S1 = 0.4, 0.1
    opt = torch.optim.AdamW([
        {"params": [p for n, p in model.named_parameters() if "encoder." in n], "lr": LR_ENC},
        {"params": [p for n, p in model.named_parameters() if "encoder." not in n], "lr": LR_HEAD},
    ], weight_decay=0.01)
    total_updates = max(1, (len(train_items) // (MICRO * ACCUM)) * args.epochs)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=total_updates, eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda", enabled=True)
    pad = ag.tok.pad_token_id
    t0 = time.time()
    for ep in range(args.epochs):
        random.seed(42 + ep); random.shuffle(train_items)
        model.train()
        prog = ep / max(1, args.epochs - 1); sigma = S0 + (S1 - S0) * prog
        opt.zero_grad(set_to_none=True)
        run_loss = n_b = 0
        for bi in range(0, len(train_items), MICRO):
            chunk = train_items[bi:bi + MICRO]
            if not chunk: continue
            b = collate_train_batch(chunk, pad)
            b = {k: v.to(device) for k, v in b.items()}
            with torch.autocast("cuda", dtype=torch.float16):
                logits, act = model(b["input_ids"], b["attention_mask"], b["marker_pos"], b["marker_mask"], b["qtype"])
            logits = logits.float(); mask = b["marker_mask"]
            k = mask.sum(-1, keepdim=True).float(); target = b["target"]
            eps = torch.randn((GRP,) + logits.shape, device=device) * sigma * mask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mask
            z = logits.detach().unsqueeze(0) + eps
            q = torch.softmax(z.masked_fill(~mask, -1e4), -1)
            with torch.no_grad():
                r = proper_reward(q, target.unsqueeze(0), b["qtype"], mask, w_sph=0.75, w_rps=1.0)
                adv = r - r.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sigma ** 2)
            loss_rl = -(adv * logp).mean()
            loss_ce = -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1)).sum(-1).mean()
            loss = (loss_rl + 1.0 * loss_ce) / ACCUM + 0.0 * act.sum()
            scaler.scale(loss).backward()
            run_loss += float(loss) * ACCUM; n_b += 1
            if n_b % ACCUM == 0 or bi + MICRO >= len(train_items):
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(opt); scaler.update(); sched.step()
                opt.zero_grad(set_to_none=True)
            if n_b % 100 == 0:
                print(f"  ep{ep+1} b{n_b}/{len(train_items)//MICRO} loss={run_loss/n_b:.4f} "
                      f"r={r.mean():.3f} ce={loss_ce:.3f} {time.time()-t0:.0f}s", flush=True)
        # 每 epoch 落盘(官方滚动 checkpoint)
        save_ckpt(model, mdir, os.path.join(run, "checkpoint_latest"))
        print(f"=== epoch {ep+1}/{args.epochs} done, loss={run_loss/max(1,n_b):.4f}, {time.time()-t0:.0f}s ===", flush=True)

    # 温度校准(留出集)
    model.eval(); preds = []
    with torch.no_grad():
        for ci in range(0, len(calib), 16):
            ch = calib[ci:ci + 16]; cb = collate_train_batch(ch, pad)
            cb = {k: v.to(device) for k, v in cb.items()}
            with torch.autocast("cuda", dtype=torch.float16):
                l, _ = model(cb["input_ids"], cb["attention_mask"], cb["marker_pos"], cb["marker_mask"], cb["qtype"])
            l = l.float().cpu().numpy()
            for r_i, it in enumerate(ch):
                kk = len(it["markers"]); preds.append((it["qtype"], l[r_i, :kk], it["target"]))
    temps = [1.0, 1.0, 1.0]
    for qt in range(3):
        sel = [(zz, tt) for q_type, zz, tt in preds if q_type == qt]
        if sel: temps[qt] = fit_one_temp(sel)
    final = os.path.join(run, "final")
    save_ckpt(model, mdir, final)
    with open(os.path.join(final, "temperature.json"), "w") as f:
        json.dump({"choice": temps[0], "score": temps[1], "noul": temps[2]}, f, indent=2)
    with open(os.path.join(final, "evolution_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"gen": "rlcd-contract", "mean": None, "rep": "contract",
                   "note": "短规则+棋盘+坐标事实选项, RLCD官方配方"}, f, ensure_ascii=False, indent=2)
    print("calibrated temps:", temps, "-> saved final/", flush=True)

def save_ckpt(model, mdir, dst):
    """桥接可挂载布局: model.safetensors + encoder/ + tokenizer/ + rl_agent_config.json"""
    import shutil
    os.makedirs(dst, exist_ok=True)
    save_file({k: v.half().contiguous().cpu() for k, v in model.state_dict().items()},
              os.path.join(dst, "model.safetensors"))
    for sub in ("encoder", "tokenizer"):
        s = os.path.join(mdir, sub); d = os.path.join(dst, sub)
        if os.path.exists(s) and not os.path.exists(d): shutil.copytree(s, d)
    cfgf = os.path.join(mdir, "rl_agent_config.json")
    if os.path.exists(cfgf) and not os.path.exists(os.path.join(dst, "rl_agent_config.json")):
        shutil.copy2(cfgf, dst)

# ── 评测(定稿契约, argmax) ─────────────────────────────────────────────
def evaluate(args):
    run = args.run
    path = os.path.join(run, "final") if os.path.exists(os.path.join(run, "final", "model.safetensors")) \
        else os.path.join(run, "checkpoint_latest")
    if not os.path.exists(os.path.join(path, "model.safetensors")): path = "convaiinnovations/laya"
    ag = load_agent(path)
    # 契约推理不需要改动: state/criteria 每步都变 → 直调 system_one(带 lock 无并发)
    results = []
    for seed0 in [int(s) for s in args.seeds.split(',')]:
        rng = random.Random(seed0); tot = 0
        detail = []
        for g in range(args.games):
            snake = [(6, 6), (5, 6), (4, 6)]; food = place_food(rng, snake); eaten = 0; cause = 'timeout'; steps = 0
            for steps in range(1, args.cap + 1):
                j = ag.system_one(state_of(snake, food),
                                  {"a": {"type": "choice", "instructions": SHORT, "criteria": crit_of(snake, food)}})
                ch = j["answers"]["a"]["choice"]
                snake, died, eat = step_snake(snake, food, ch)
                if died: cause = 'died'; break
                if eat:
                    eaten += 1; food = place_food(rng, snake)
            tot += eaten; detail.append(eaten)
        mean = tot / args.games
        results.append((seed0, mean, detail))
        print(f"seed{seed0}: 均值 {mean:.1f} 食物/局  明细 {detail}", flush=True)
    best = max(r[1] for r in results)
    with open(os.path.join(run, "eval.json"), "w") as f:
        json.dump({"results": [[s, m] for s, m, _ in results]}, f, indent=2)

# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gen', 'train', 'eval'])
    ap.add_argument('--run', default='_rlcd/run1')
    ap.add_argument('--base', default='convaiinnovations/laya')
    ap.add_argument('--games-t', type=int, default=60)
    ap.add_argument('--games-r', type=int, default=30)
    ap.add_argument('--games-p', type=int, default=40)
    ap.add_argument('--seed', type=int, default=777)
    ap.add_argument('--epochs', type=int, default=3)
    ap.add_argument('--games', type=int, default=8)
    ap.add_argument('--seeds', default='1000,1001')
    ap.add_argument('--cap', type=int, default=MAXSTEPS)
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    if a.cmd == 'gen':
        ag = load_agent(a.base, device='cuda')
        allit = []
        it, st = collect_rollouts(ag, 'teacher', a.games_t, a.seed); allit += it
        print('teacher games food:', st, '→', len(it), 'items', flush=True)
        it, st = collect_rollouts(ag, 'random', a.games_r, a.seed + 1); allit += it
        print('random games →', len(it), 'items (多为撞墙/贴身负面状态)', flush=True)
        it, st = collect_rollouts(ag, 'onpolicy', a.games_p, a.seed + 2); allit += it
        print('on-policy →', len(it), 'items', flush=True)
        # 截上限防爆炸
        random.Random(a.seed).shuffle(allit)
        allit = allit[:26000]
        torch.save(allit, os.path.join(a.run, 'items.pt'))
        print('saved', len(allit), 'items →', a.run)
    elif a.cmd == 'train':
        train(a)
    else:
        evaluate(a)
