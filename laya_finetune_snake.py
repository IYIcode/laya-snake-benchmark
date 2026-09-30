# -*- coding: utf-8 -*-
"""Fine-tune the REAL Laya model (convaiinnovations/laya, english checkpoint, 421M ModernBERT)
to play snake, mirroring laya-snake-demo.html's decision heuristic EXACTLY
(same decide(): 3 candidates, -2/+0.5/-3 weights, -50 trap penalty, -999 blocked).

Pipeline:
  1. Generate (state -> argmax action) labeled samples from heuristic rollouts on a 12x12 board.
     Each sample is a Laya "choice" question whose criteria embed foodDist / space / danger,
     with randomized option order (kills positional bias).
  2. Full fine-tune DecisionModel (encoder lr 2e-5, heads lr 1e-4), bf16 autocast, CE loss.
  3. Evaluate greedy games (food eaten) after every epoch with the real model.
  4. Save a local checkpoint dir loadable by laya.Agent(path) offline.

Run:  python laya_finetune_snake.py [--samples 2400] [--epochs 3] [--batch 8]
"""
import argparse, json, os, random, shutil, sys, time

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import torch
import torch.nn.functional as F

GW, GH = 12, 12
DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
OPP = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
W_FD, W_SP, W_DZ = -2.0, 0.5, -3.0  # same values the demo scene 4 shows
NEIGH = ((0, 1), (0, -1), (1, 0), (-1, 0))

INSTRUCTIONS = (
    "Pick the direction the snake should move next so it reaches the food and stays alive. "
    "The state gives head position, body segments (head first), food position and facing. "
    "Exactly three options are the legal-looking directions (the reverse of facing is excluded). "
    "Each option describes the cell the head would enter: "
    "foodDist = Manhattan distance from that cell to the food; "
    "space = free cells reachable from that cell by flood fill (bigger is safer); "
    "danger = how many of that cell's four neighbors are wall or snake body; "
    "an option marked BLOCKED would run into a wall or the body right away and must never be chosen."
)


# ── domain logic: exact mirror of the demo's isSafe/flood/decide ──────────────
def is_safe(x, y, snake):
    if not (0 <= x < GW and 0 <= y < GH):
        return False
    return [x, y] not in snake


def flood(sx, sy, snake):
    occ = {tuple(s) for s in snake}
    seen = {(sx, sy)}
    q = [(sx, sy)]
    while q:
        x, y = q.pop()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < GW and 0 <= ny < GH and (nx, ny) not in seen and (nx, ny) not in occ:
                seen.add((nx, ny))
                q.append((nx, ny))
    return len(seen)


def decide(head, food, snake, facing):
    """Mirror of demo decide(): 3 candidates (facing excluded), exact metrics & score."""
    head, food = tuple(head), tuple(food)
    cands = []
    for d, (dx, dy) in DIRS.items():
        if d == OPP[facing]:
            continue
        nx, ny = head[0] + dx, head[1] + dy
        if not is_safe(nx, ny, snake):
            cands.append({"dir": d, "fd": 0, "sp": 0, "dc": 4, "s": -999.0, "safe": False})
            continue
        fd = abs(nx - food[0]) + abs(ny - food[1])
        sp = flood(nx, ny, snake)
        dc = sum(1 for ddx, ddy in NEIGH if not is_safe(nx + ddx, ny + ddy, snake))
        s = W_FD * fd + W_SP * sp + W_DZ * dc
        if sp < len(snake):
            s -= 50.0
        cands.append({"dir": d, "fd": fd, "sp": sp, "dc": dc, "s": s, "safe": True})
    return cands


def criteria_from(cands):
    return {
        c["dir"]: (f"foodDist={c['fd']} space={c['sp']} danger={c['dc']}" if c["safe"]
                   else "BLOCKED: hits wall or body; foodDist=0 space=0 danger=4")
        for c in cands
    }


def step_move(head, snake, action, ate):
    dx, dy = DIRS[action]
    nh = [head[0] + dx, head[1] + dy]
    nb = ([nh] + [list(s) for s in snake]) if ate else ([nh] + [list(s) for s in snake[:-1]])
    return nh, nb


def new_food(rng, head, snake):
    while True:
        f = [rng.randint(0, GW - 1), rng.randint(0, GH - 1)]
        if f != list(head) and f not in snake:
            return f


def rand_start(rng):
    facing = rng.choice(list(DIRS))
    dx, dy = DIRS[facing]
    for _ in range(200):
        hx, hy = rng.randint(2, GW - 3), rng.randint(2, GH - 3)
        snake = [[hx, hy], [hx - dx, hy - dy], [hx - dx * 2, hy - dy * 2]]
        if all(0 <= s[0] < GW and 0 <= s[1] < GH for s in snake):
            return snake, new_food(rng, snake[0], snake), facing
    return None


# ── sample generation ─────────────────────────────────────────────────────────
def gen_samples(n_target, seed=7):
    rng = random.Random(seed)
    samples = []
    while len(samples) < n_target:
        st = rand_start(rng)
        if st is None:
            continue
        snake, food, facing = st
        head = snake[0]
        eaten = 0
        for _ in range(150):
            cands = decide(head, food, snake, facing)
            best_s = max(c["s"] for c in cands)
            if best_s <= -998:  # every option is death: no valid label
                break
            tied = [c for c in cands if c["s"] == best_s]
            target = rng.choice(tied)
            order = cands[:]
            rng.shuffle(order)
            crit = criteria_from(order)
            samples.append({
                "state": {"game": "snake", "board": f"{GW}x{GH}",
                          "head": list(head), "body": [list(s) for s in snake],
                          "food": list(food), "facing": facing},
                "criteria": crit,
                "label": [c["dir"] for c in order].index(target["dir"]),
            })
            if len(samples) >= n_target:
                break
            chosen = target if rng.random() < 0.8 else rng.choice(cands)
            nxt = [head[0] + DIRS[chosen["dir"]][0], head[1] + DIRS[chosen["dir"]][1]]
            ate = nxt == list(food)
            if not chosen["safe"]:
                break
            head, snake = step_move(head, snake, chosen["dir"], ate)
            facing = chosen["dir"]
            if ate:
                eaten += 1
                food = new_food(rng, head, snake)
                if eaten >= 6:
                    break
    return samples[:n_target]


# ── real-model inference (single choice question) ────────────────────────────
@torch.no_grad()
def model_decide(model, tok, cfg, state, criteria):
    from laya.common import build_sequence, collate_items
    keys = list(criteria.keys())
    q = {"t": "choice", "ins": INSTRUCTIONS, "crit": criteria}
    seq, markers = build_sequence(tok, state, q, cfg.get("max_len", 512), cfg.get("head_max_len", 192))
    if len(markers) != len(keys):
        raise RuntimeError("options overflow head budget")
    b = collate_items([[{"ids": seq, "markers": markers, "qtype": 0}]], tok.pad_token_id)
    device = next(model.parameters()).device
    with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
        logits, _act = model(b["input_ids"].to(device), b["attention_mask"].to(device),
                             b["marker_pos"].to(device), b["marker_mask"].to(device),
                             b["qtype"].to(device))
    z = logits[0, :len(keys)].float()
    bucket = "choice:2" if len(keys) == 2 else ("choice:3-5" if len(keys) <= 5 else "choice:6-10")
    t_scale = float(cfg.get("temperature_by_options", {}).get(bucket, 1.0))
    p = torch.softmax(z / max(1e-3, t_scale), -1)
    return keys[int(p.argmax())], {k: round(float(v), 4) for k, v in zip(keys, p)}


def make_item(agent, s, build_sequence, collate_items):
    q = {"t": "choice", "ins": INSTRUCTIONS, "crit": s["criteria"]}
    seq, markers = build_sequence(agent.tok, s["state"], q,
                                  agent.cfg.get("max_len", 512), agent.cfg.get("head_max_len", 192))
    if len(markers) != len(s["criteria"]):
        return None
    return {"ids": seq, "markers": markers, "qtype": 0, "label": s["label"]}


# ── greedy evaluation driven purely by the real model ─────────────────────────
def evaluate(model, tok, cfg, games=6, seed=99, max_steps=400):
    rng = random.Random(seed)
    results = []
    for _g in range(games):
        st = rand_start(rng)
        snake, food, facing = st
        head = snake[0]
        eaten = 0
        for _ in range(max_steps):
            cands = decide(head, food, snake, facing)
            crit = criteria_from(cands)
            state = {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                     "body": [list(s) for s in snake], "food": list(food), "facing": facing}
            chosen, _probs = model_decide(model, tok, cfg, state, crit)
            c = next(x for x in cands if x["dir"] == chosen)
            if not c["safe"]:
                break
            ate = [head[0] + DIRS[chosen][0], head[1] + DIRS[chosen][1]] == list(food)
            head, snake = step_move(head, snake, chosen, ate)
            facing = chosen
            if ate:
                eaten += 1
                food = new_food(rng, head, snake)
        results.append(eaten)
    return results


def save_checkpoint(model, agent, outdir):
    from safetensors.torch import save_file
    os.makedirs(outdir, exist_ok=True)
    sd = {k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()}
    save_file(sd, os.path.join(outdir, "model.safetensors"), metadata={"format": "pt"})
    cfg = dict(agent.cfg)
    cfg["training"] = dict(cfg.get("training", {}))
    cfg["training"]["fine_tuned_for"] = "snake-12x12-argmax-demo"
    with open(os.path.join(outdir, "rl_agent_config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    try:
        from huggingface_hub import snapshot_download
        src = snapshot_download("convaiinnovations/laya", allow_patterns=["tokenizer/*", "encoder/*"])
    except Exception:
        glob_root = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub",
                                 "models--convaiinnovations--laya", "snapshots")
        src = max((os.path.join(glob_root, d) for d in os.listdir(glob_root)), key=os.path.getmtime)
    for sub in ("tokenizer", "encoder"):
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(outdir, sub), dirs_exist_ok=True)
    import laya.agent as A
    A._fix_tokenizer_config(outdir)
    print("  checkpoint saved:", sorted(os.listdir(outdir)), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=2400)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr-enc", type=float, default=2e-5)
    ap.add_argument("--lr-head", type=float, default=1e-4)
    ap.add_argument("--head-only", action="store_true",
                    help="freeze ModernBERT encoder, train only the decision heads (~3x faster, ~5x less VRAM)")
    ap.add_argument("--unfreeze-layers", type=int, default=0,
                    help="partial FT: train the LAST N encoder layers + heads, frozen prefix detached at the boundary (memory-saver)")
    ap.add_argument("--games", type=int, default=6)
    ap.add_argument("--skip-baseline", action="store_true", help="zero-shot already measured 0/0/0; skip re-eval")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "laya_snake_ft"))
    ap.add_argument("--eval-only", action="store_true", help="load OUT dir and evaluate only")
    ap.add_argument("--data-only", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] generating {args.samples} labeled samples (heuristic argmax)...", flush=True)
    samples = gen_samples(args.samples)
    print(f"  -> {len(samples)} samples, {time.time()-t0:.1f}s", flush=True)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "laya_snake_data_peek.json"),
              "w", encoding="utf-8") as f:
        json.dump(samples[:5], f, ensure_ascii=False, indent=1)
    if args.data_only:
        print(json.dumps(samples[0], ensure_ascii=False, indent=1))
        return

    from laya import Agent
    from laya.common import build_sequence, collate_items
    if args.eval_only:
        print(f"[{time.strftime('%H:%M:%S')}] loading fine-tuned checkpoint {args.out}...", flush=True)
        agent = Agent(args.out, device="cuda")
        res = evaluate(agent.model, agent.tok, agent.cfg, games=args.games, seed=2024)
        print(f"EVAL foods/game={res} mean={np.mean(res):.2f}", flush=True)
        return

    print(f"[{time.strftime('%H:%M:%S')}] loading REAL laya checkpoint (cuda)...", flush=True)
    agent = Agent("convaiinnovations/laya", device="cuda")
    model, tok, cfg = agent.model, agent.tok, agent.cfg
    print(f"  -> device={agent.device}, params={sum(p.numel() for p in model.parameters())/1e6:.1f}M, {time.time()-t0:.1f}s", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] zero-shot baseline eval (3 games)...", flush=True)
    model.eval()
    base = [0, 0, 0] if args.skip_baseline else evaluate(model, tok, cfg, games=3)
    print(f"  -> zero-shot foods/game: {base}  (why we fine-tune)", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] building training items...", flush=True)
    items = [it for it in (make_item(agent, s, build_sequence, collate_items) for s in samples) if it]
    print(f"  -> {len(items)} items; mean len={int(np.mean([len(i['ids']) for i in items]))}", flush=True)

    device = agent.device
    head_only = args.head_only
    groups = []
    if head_only:
        # 省显存模式：编码器不做反向（detach + requires_grad False），只训决策头
        model.encoder.requires_grad_(False)
        head_params = [p for n, p in model.named_parameters() if not n.startswith("encoder.") and p.requires_grad]
        print(f"  -> head-only: {sum(p.numel() for p in head_params)/1e6:.1f}M trainable params", flush=True)
        opt = torch.optim.AdamW(head_params, lr=args.lr_head, weight_decay=0.01)
    elif args.unfreeze_layers:
        # 部分微调：只放开编码器最后 N 层；在边界 detach，冻结前缀完全不建反向图
        for p in model.encoder.parameters():
            p.requires_grad_(False)
        enc_layers = None
        for m in model.encoder.modules():
            if isinstance(m, torch.nn.ModuleList) and len(m) >= args.unfreeze_layers:
                enc_layers = m
                break
        assert enc_layers is not None, "encoder layer ModuleList not found"
        L = len(enc_layers)
        tail = L - args.unfreeze_layers
        for l in list(enc_layers)[tail:]:
            for p in l.parameters():
                p.requires_grad_(True)
        enc_layers[tail].register_forward_pre_hook(
            lambda mod, inp: (inp[0].detach(),) + tuple(inp[1:]))
        enc_tail = [p for l in list(enc_layers)[tail:] for p in l.parameters()]
        head_params = [p for n, p in model.named_parameters() if not n.startswith("encoder.") and p.requires_grad]
        print(f"  -> partial FT: encoder layers {tail}..{L-1} ({sum(p.numel() for p in enc_tail)/1e6:.0f}M) "
              f"+ heads ({sum(p.numel() for p in head_params)/1e6:.0f}M); boundary detach at layer {tail}", flush=True)
        opt = torch.optim.AdamW([
            {"params": head_params, "lr": args.lr_head},
            {"params": enc_tail, "lr": args.lr_enc, "weight_decay": 0.01},
        ])
    else:
        enc_params, head_params = [], []
        for n, p in model.named_parameters():
            (enc_params if n.startswith("encoder.") else head_params).append(p)
        opt = torch.optim.AdamW([
            {"params": head_params, "lr": args.lr_head},
            {"params": enc_params, "lr": args.lr_enc, "weight_decay": 0.01},
        ])
    steps_per_ep = (len(items) + args.batch - 1) // args.batch
    n_steps = args.epochs * steps_per_ep
    if head_only:
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr_head, total_steps=n_steps + 10)
    else:
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[args.lr_head, args.lr_enc],
                                                    total_steps=n_steps + 10)

    pad_id = tok.pad_token_id
    rng = random.Random(1234)
    step = 0
    best = -1e9
    for ep in range(args.epochs):
        model.train()
        perm = list(range(len(items)))
        rng.shuffle(perm)
        run, cnt, accs = 0.0, 0, []
        for i in range(0, len(items), args.batch):
            batch = [items[j] for j in perm[i:i + args.batch]]
            b = collate_items([batch], pad_id)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                logits, _ = model(b["input_ids"].to(device), b["attention_mask"].to(device),
                                  b["marker_pos"].to(device), b["marker_mask"].to(device),
                                  b["qtype"].to(device), detach_encoder=head_only)
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
                print(f"[{time.strftime('%H:%M:%S')}] ep{ep} step{step}/{n_steps} loss={run/cnt:.4f} batchAcc={acc:.2f} elapsed={time.time()-t0:.0f}s", flush=True)
                run, cnt = 0.0, 0
        model.eval()
        res = evaluate(model, tok, cfg, games=args.games, seed=100 + ep)
        mean = float(np.mean(res))
        print(f"[{time.strftime('%H:%M:%S')}] EPOCH {ep} done. greedy foods/game={res} mean={mean:.2f} (train acc last≈{np.mean(accs):.2f})", flush=True)
        if mean >= best:
            best = mean
            save_checkpoint(model, agent, args.out)
            print(f"  -> saved best checkpoint (mean food {best:.2f})", flush=True)
        if best >= 3.0 and ep >= 1:
            print("  -> target reached (mean food >= 3), stopping early", flush=True)
            break

    print(f"[{time.strftime('%H:%M:%S')}] DONE. zero-shot={base} best mean food/game={best:.2f}, total {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
