# -*- coding: utf-8 -*-
"""Laya 贪吃蛇 「环契约」训练 —— 老师 = 哈密顿环保险策略(laya-snake-feature.html 实测 141 通关)
输入契约 v2(环): 短规则+环规则(不截断) + 0/1/2/3 棋盘 + state 附 loopAhead 三事实 + 每选项坐标事实+cyc
  loopAhead: foodAhead=头沿环到食物的前进距离, bodyAhead=到最近身体(含尾), bodyGoAhead=不含尾
  选项: "(x,y) free|vacating|body|wall, NEARER/FARTHER/SAME, cyc=N"  N=落点相对头的前进环步数
  判据(规则文本给, 结论不给): 不吃的走法须 cyc<=min(bodyGoAhead,foodAhead)-... 老师用 m1/m2 精确版
用法:
  python _rlcd_cycle.py gen   --run _rlcd/run3 --games-t 6 --games-r 15
  python _rlcd_cycle.py train --run _rlcd/run3 --epochs 3
  python _rlcd_cycle.py eval  --run _rlcd/run3 --games 4 --cap 6000
  python _rlcd_cycle.py dagger --run _rlcd/run3 --rounds 2 --games 6
"""
import argparse, json, math, os, random, sys, time
import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import load_file, save_file

GW = GH = 12
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
ORDER = ['UP', 'DOWN', 'LEFT', 'RIGHT']

# ── 环序号(梳形哈密顿环, 与页面 cidx 一致) ──────────────────────────────
def cidx(x, y):
    if y == 0: return 0 if x == 0 else 133 + (11 - x)
    start = 1 + 11 * x
    return start + (y - 1) if x % 2 == 0 else start + (11 - y)

def loop_ahead(snake, food):
    """返回 (df, m1, m2): 头沿环前进到食物/最近身体(含尾)/最近身体(不含尾) 的距离"""
    hi = cidx(*snake[0])
    D = lambda p: (cidx(*p) - hi) % 144
    df = D(food); m1 = 144; m2 = 144
    for i in range(1, len(snake)):
        dd = D(snake[i])
        if i < len(snake) - 1: m2 = min(m2, dd)
        m1 = min(m1, dd)
    return df, m1, m2

# ── 契约 v2 ────────────────────────────────────────────────────────────
SHORT = ("Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. "
         "Row 0 top, row 11 bottom. UP=row-1, DOWN=row+1, LEFT=col-1, RIGHT=col+1. "
         "The 144 cells also form one closed loop (loopAhead in the state gives loop distances from the head: "
         "bodyAhead = steps forward to the nearest body cell counting the tail, bodyGoAhead = same but excluding "
         "the tail cell (it vacates unless you eat this move), foodAhead = steps forward to the food). "
         "Each option lists its landing cell facts and cyc = its forward loop steps from the head. "
         "A move is loop-safe if it does not pass your body or the food on the loop: when the move does not eat, "
         "cyc <= bodyGoAhead-1 and cyc <= foodAhead; when the move eats the food, cyc <= bodyAhead-1. "
         "Never pick a wall or body landing. Among loop-safe moves prefer the one closest to the food.")

def grid_rows(snake, food):
    g = [['0'] * GW for _ in range(GH)]
    for i, (x, y) in enumerate(snake):
        g[y][x] = '2' if i == 0 else '1'
    g[food[1]][food[0]] = '3'
    return [''.join(r) for r in g]

def state_of(snake, food):
    df, m1, m2 = loop_ahead(snake, food)
    return {'game': 'snake', 'board': '12x12', 'grid': grid_rows(snake, food),
            'loopAhead': {'foodAhead': df, 'bodyAhead': m1, 'bodyGoAhead': m2}}

def land_of(nx, ny, snake, food):
    if not (0 <= nx < GW and 0 <= ny < GH): return 'wall'
    if (nx, ny) in snake[:-1] or ((nx, ny) == snake[-1] and food == (nx, ny)): return 'body'
    if (nx, ny) == snake[-1]: return 'vacating'
    return 'free'

def compact(snake, food, d):
    hx, hy = snake[0]; dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
    land = land_of(nx, ny, snake, food)
    dn = abs(nx - food[0]) + abs(ny - food[1]); dc = abs(hx - food[0]) + abs(hy - food[1])
    rel = 'NEARER to food' if dn < dc else ('FARTHER from food' if dn > dc else 'SAME distance')
    if land == 'wall': return f"({nx},{ny}) wall, {rel}"
    hi = cidx(hx, hy); cd = (cidx(nx, ny) - hi) % 144
    return f"({nx},{ny}) {land}, {rel}, cyc={cd}"

def crit_of(snake, food):
    return {d: compact(snake, food, d) for d in ORDER}

# ── 环境 ───────────────────────────────────────────────────────────────
def place_food(rng, snake):
    occ = set(snake)
    free = [(x, y) for x in range(GW) for y in range(GH) if (x, y) not in occ]
    return rng.choice(free) if free else None

def step_snake(snake, food, d):
    hx, hy = snake[0]; dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
    eat = (nx, ny) == food
    body = snake if eat else snake[:-1]
    if not (0 <= nx < GW and 0 <= ny < GH): return snake, True, False
    if (nx, ny) in body: return snake, True, False
    ns = [(nx, ny)] + list(snake)
    if not eat: ns.pop()
    return ns, False, eat

def flood_space(head, blocked):
    seen = {head}; stack = [head]; b = set(blocked); n = 0
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
        (x, y), dd = q.popleft()
        for dx, dy in DIRS.values():
            p = (x + dx, y + dy)
            if not (0 <= p[0] < GW and 0 <= p[1] < GH) or p in b or p in seen: continue
            if p == food: return dd + 1
            seen.add(p); q.append((p, dd + 1))
    return None

# ── 老师: 四特征+环保险(与页面 analyze 完全一致), 输出每方向分 ─────────
def teacher_scores(snake, food):
    if food is None: return [-1000.0] * 4
    hx, hy = snake[0]; hi = cidx(hx, hy)
    D = lambda p: (cidx(*p) - hi) % 144
    df, m1, m2 = loop_ahead(snake, food)
    cands = []
    for i, d in enumerate(ORDER):
        nx, ny = hx + DIRS[d][0], hy + DIRS[d][1]
        land = land_of(nx, ny, snake, food)
        if land in ('wall', 'body'): cands.append(None); continue
        eat = (nx, ny) == food
        ns = [(nx, ny)] + list(snake)
        if not eat: ns.pop()
        sp = flood_space(ns[0], ns[1:])
        reach = eat or bfs_dist(ns[0], food, ns[1:]) is not None
        cd = D((nx, ny))
        allow = (df <= m1 - 1) if eat else (1 <= cd <= min(m2 - 1, df))
        ok = sp >= len(ns) * 1.2
        dn = abs(nx - food[0]) + abs(ny - food[1])
        rel = 0 if dn < df_dummy(snake, food) else (2 if dn > df_dummy(snake, food) else 1)
        cands.append(dict(i=i, allow=allow, ok=ok, reach=reach, rel=rel, dn=dn, sp=sp))
    legal = [c for c in cands if c]
    if not legal: return [-1000.0] * 4
    base = [c for c in legal if c['allow']] or legal
    tiers = [[c for c in base if c['ok'] and c['reach']], [c for c in base if c['ok']],
             [c for c in base if c['reach']], base]
    tk = next(k for k, t in enumerate(tiers) if t)
    pool = sorted(tiers[tk], key=lambda c: (c['rel'], c['dn'], -c['sp']))
    rank = {c['i']: r for r, c in enumerate(pool)}
    out = []
    for i in range(4):
        c = cands[i]
        if c is None: out.append(-1000.0)
        elif not c['allow']: out.append(-30.0)
        else: out.append(100.0 - (tk - tiers.index(base if base is c and False else tiers[tk])) * 0 - 12 * tk - rank.get(i, 9) * 3)
    return out

def df_dummy(snake, food):
    hx, hy = snake[0]
    return abs(hx - food[0]) + abs(hy - food[1])

T_SOFT = 1.2
def gold_dist(scores):
    m = max(scores)
    e = [math.exp((s - m) / T_SOFT) for s in scores]
    z = sum(e)
    return [v / z for v in e]

def teacher_pick(scores, rng, temp_explore=False):
    top = max(scores)
    best = [i for i, s in enumerate(scores) if s >= top - 1e-9]
    # 探索只在环安全集(s>0)内随机 —— 环不变量下任何环安全走法都不会致死, 数据还多样
    if temp_explore and rng.random() < 0.10:
        safe = [i for i, s in enumerate(scores) if s > 0]
        if safe: return ORDER[rng.choice(safe)]
    return ORDER[rng.choice(best)]

# ── 造数据 ─────────────────────────────────────────────────────────────
def build_item(agent, snake, food):
    from laya.common import build_sequence, QTYPES
    crit = crit_of(snake, food)
    q = {"t": "choice", "ins": SHORT, "crit": crit}
    seq, markers = build_sequence(agent.tok, state_of(snake, food), q, 512, 256)
    if len(markers) != 4: return None
    sc = teacher_scores(snake, food)
    return {"ids": seq, "markers": markers, "qtype": QTYPES["choice"],
            "target": gold_dist(sc), "label": max(range(4), key=lambda i: sc[i])}

def roll_game(agent, policy, rng, cap, label_fn):
    """policy: 'teacher' | 'random' | 'model'; 标签永远来自环老师"""
    snake = [(6, 6), (5, 6), (4, 6)]; food = place_food(rng, snake)
    eaten = 0; cause = 'timeout'; items = []
    for st in range(cap):
        if food is None: cause = 'win'; break
        it = label_fn(agent, snake, food)
        if it: items.append(it)
        if policy == 'teacher':
            ch = teacher_pick(teacher_scores(snake, food), rng, temp_explore=True)
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
    return items, eaten, cause

def collect(agent, policy, n_games, seed, cap, stride=1):
    rng = random.Random(seed); allit = []; stats = []
    for g in range(n_games):
        items, eaten, cause = roll_game(agent, policy, rng, cap, build_item)
        if stride > 1:
            keep = {i for i in rng.sample(range(len(items)), max(1, len(items) // stride))}
            items = [it for k, it in enumerate(items) if k in keep]
        allit += items; stats.append((eaten, cause))
        print(f'  {policy} g{g+1}: food={eaten} {cause} items={len(items)}', flush=True)
    return allit, stats

# ── 训练(与 _rlcd_snake 同配方) ────────────────────────────────────────
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
    return Agent(path, device=device)

def save_ckpt(model, mdir, dst):
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

def train(args):
    from laya.common import proper_reward, QTYPES
    run = args.run
    device = torch.device("cuda")
    ag = load_agent(args.base)
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

    MICRO, ACCUM, GRP = args.micro, args.accum, 4
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
        save_ckpt(model, mdir, os.path.join(run, "checkpoint_latest"))
        print(f"=== epoch {ep+1}/{args.epochs} done, loss={run_loss/max(1,n_b):.4f}, {time.time()-t0:.0f}s ===", flush=True)

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
        json.dump({"gen": args.tag, "mean": None, "rep": "cycle",
                   "note": "环契约: 网格+loopAhead事实+cyc选项, 老师=哈密顿环保险(141)"}, f, ensure_ascii=False, indent=2)
    print("calibrated temps:", temps, "-> saved final/", flush=True)

# ── 评测 ───────────────────────────────────────────────────────────────
def evaluate(args):
    run = args.run
    path = args.model or (os.path.join(run, "final") if os.path.exists(os.path.join(run, "final", "model.safetensors"))
                          else os.path.join(run, "checkpoint_latest"))
    if not os.path.exists(os.path.join(path, "model.safetensors")): sys.exit("no ckpt")
    ag = load_agent(path)
    results = []
    for seed0 in [int(s) for s in args.seeds.split(',')]:
        rng = random.Random(seed0); detail = []
        for g in range(args.games):
            _, eaten, cause = roll_game(ag, 'model', rng, args.cap, lambda a, s, f: None)
            detail.append((eaten, cause))
        mean = sum(d[0] for d in detail) / len(detail)
        results.append((seed0, mean, detail))
        print(f"seed{seed0}: 均值 {mean:.1f}  明细 {detail}", flush=True)
    best = max(r[1] for r in results)
    with open(os.path.join(run, "eval.json"), "w") as f:
        json.dump({"results": [[s, m, d] for s, m, d in results]}, f, ensure_ascii=False, indent=2)

# ── DAgger ─────────────────────────────────────────────────────────────
def dagger(args):
    run = args.run
    path = os.path.join(run, "final") if os.path.exists(os.path.join(run, "final", "model.safetensors")) \
        else os.path.join(run, "checkpoint_latest")
    ag = load_agent(path)
    items = torch.load(os.path.join(run, "items.pt"), weights_only=False)
    for rd in range(args.rounds):
        new, stats = collect(ag, 'model', args.games, args.seed + 97 * (rd + 1), args.cap, stride=args.stride)
        print(f'dagger round {rd+1}: model stats {stats} → +{len(new)} items', flush=True)
        items += new
        random.Random(args.seed + rd).shuffle(items)
        items = items[:args.maxitems]
        torch.save(items, os.path.join(run, 'items.pt'))
        class TA: pass
        t = TA(); t.run = run; t.epochs = args.epochs_rt; t.base = args.base; t.tag = f"cycle-d{rd+2}"
        train(t)

# ── CLI ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gen', 'train', 'eval', 'dagger'])
    ap.add_argument('--run', default='_rlcd/run3')
    ap.add_argument('--base', default='convaiinnovations/laya')
    ap.add_argument('--model', default=None)
    ap.add_argument('--games-t', type=int, default=6)
    ap.add_argument('--games-r', type=int, default=15)
    ap.add_argument('--seed', type=int, default=555)
    ap.add_argument('--stride', type=int, default=4)
    ap.add_argument('--maxitems', type=int, default=40000)
    ap.add_argument('--epochs', type=int, default=3)
    ap.add_argument('--micro', type=int, default=8)
    ap.add_argument('--accum', type=int, default=8)
    ap.add_argument('--epochs-rt', dest='epochs_rt', type=int, default=2)
    ap.add_argument('--rounds', type=int, default=2)
    ap.add_argument('--games', type=int, default=6)
    ap.add_argument('--cap', type=int, default=6000)
    ap.add_argument('--seeds', default='1000,1001')
    ap.add_argument('--tag', default='cycle-r3')
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    if a.cmd == 'gen':
        ag = load_agent(a.base, device='cuda')
        allit = []
        it, st = collect(ag, 'teacher', a.games_t, a.seed, a.cap, stride=1)
        print('teacher:', st, flush=True); allit += it
        it, st = collect(ag, 'random', a.games_r, a.seed + 1, 240, stride=2)
        print('random:', st, flush=True); allit += it
        random.Random(a.seed).shuffle(allit)
        allit = allit[:a.maxitems]
        torch.save(allit, os.path.join(a.run, 'items.pt'))
        print('saved', len(allit), 'items →', a.run)
    elif a.cmd == 'train':
        train(a)
    elif a.cmd == 'eval':
        evaluate(a)
    else:
        dagger(a)
