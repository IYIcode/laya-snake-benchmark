# -*- coding: utf-8 -*-
"""调教循环：gen5 权重固定，改的是"喂给它的特征/规则文本"。
用法: python -X utf8 _tune.py <variant>  (baseline|trap|legend|traplegend)
每局逐步记录特征+概率，写 _tune_runs/<variant>.json，控制台只打 ASCII 摘要。"""
import sys, os, json, random, itertools
import torch
import laya_finetune_snake as L
from laya.common import build_sequence, collate_items
from laya import Agent

GW, GH, DIRS, OPP = L.GW, L.GH, L.DIRS, L.OPP
SEEDS = list(range(3001, 3011))   # 所有变体同种子，公平对比
MAX_STEPS = 20000   # 不限步数：12×12 棋盘上蛇必然终局（无路可走），到不了这个上限

LEGEND = (" Note on the option metrics: danger=4 minus the straight-line runway in that "
          "direction (danger 3-4 means only 0-1 free cells left before wall/body). "
          "space is the flood-fill room from the cell you would land on; landing where "
          "space is smaller than the snake length means a sealed pocket and certain death "
          "a few steps later. Balance: seek food, but never enter a pocket.")

def is_safe(x, y, b):
    return 0 <= x < GW and 0 <= y < GH and [x, y] not in b

def flood(sx, sy, b):
    occ = {tuple(s) for s in b}
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

def flood2(head, snake, dx, dy):
    """两拍前瞻：模拟走完 (dx,dy) 落到 nh 后（蛇尾腾空一步，未吃到），
    下一步能去的所有邻格各自 flood，取最大可达区。看见"袋会不会被自己走开"。"""
    nh = [head[0] + dx, head[1] + dy]
    body_after = [nh] + [list(s) for s in snake[:-1]]      # 落子后的蛇（尾已腾空）
    walls_next = body_after[:-1]                            # 再走一步时又腾出一格蛇尾
    best = 0
    for ddx, ddy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        cx, cy = nh[0] + ddx, nh[1] + ddy
        if is_safe(cx, cy, walls_next):
            best = max(best, flood(cx, cy, walls_next))
    return best

def make_crit_fn(danger_mode):
    def crit(head, food, snake, facing):
        walls = [list(s) for s in snake[:-1]]
        ln = len(snake)
        o, meta = {}, {}
        for n, (dx, dy) in DIRS.items():
            nx, ny = head[0] + dx, head[1] + dy
            fd = abs(nx - food[0]) + abs(ny - food[1])
            run, rx, ry = 0, nx, ny
            while is_safe(rx, ry, walls):
                run += 1
                rx += dx
                ry += dy
            rev = n == OPP[facing]
            safe = is_safe(nx, ny, walls) and not rev
            if not safe:
                sp = 0
            elif danger_mode in ("look2", "fdpen6"):
                sp = flood2(head, snake, dx, dy)     # 两拍前瞻的"空间"：看得见尾腾空后袋开不开
            else:
                sp = flood(nx, ny, walls)
            meta[n] = {"fd": fd, "sp": sp, "run": run, "safe": safe, "rev": rev}
            if not safe:
                o[n] = ("BLOCKED: reverses into the snake neck; foodDist=0 space=0 danger=4"
                        if rev else "BLOCKED: hits wall or body; foodDist=0 space=0 danger=4")
            else:
                d = max(0, 4 - run)
                fdv = fd
                pocket = sp < ln + 2
                if danger_mode in ("trap", "fdpen", "fdpen2", "fdpen3", "fdpen4", "fdpen5", "look2", "fdpen6") and pocket:
                    d = min(4, d + 2)
                # fdpen: 口袋告警注入模型最强的信任通道 foodDist（legend 实验证明它只读数字）
                if danger_mode == "fdpen" and pocket:
                    fdv = fd + 8
                if danger_mode == "fdpen2" and pocket:
                    fdv = fd + 15
                # fdpen3: 强惩罚但 fd=0（这一步就吃到）免罚——防止模型被吓到不敢吃、绕圈饿着永生
                if danger_mode == "fdpen3" and pocket:
                    fdv = fd + 15 if fd > 0 else 0
                # look2: fdpen3 全套规则，只是 space/口袋判定换成两拍前瞻（用户"下下步"设想）
                if danger_mode == "look2" and pocket:
                    fdv = fd + 15 if fd > 0 else 0
                # fdpen4: 再加"开阔地免惊"——非口袋(sp≥身长+2,可拐弯逃生)时 danger 封顶1，
                # 修复实测误判：贴墙但大开区里 run=1→danger=3 把模型吓得放弃 fd=0 的稳吃食
                if danger_mode == "fdpen4":
                    if pocket:
                        fdv = fd + 15 if fd > 0 else 0
                    d = min(d, 1) if not pocket else d
                # fdpen5: fdpen4 的教训(全局封顶危险=36.1崩)→只做外科手术：
                # 仅"这一步就吃(fd=0)且非口袋"时 danger 压到≤1，专治贴墙稳吃被放弃
                if danger_mode == "fdpen5":
                    if pocket:
                        fdv = fd + 15 if fd > 0 else 0
                    elif fd == 0:
                        d = min(d, 1)
                # fdpen6: 合体——space 用两拍前瞻(look2) + 吃食格 danger 豁免(fdpen5)
                if danger_mode == "fdpen6":
                    if pocket:
                        fdv = fd + 15 if fd > 0 else 0
                    elif fd == 0:
                        d = min(d, 1)
                o[n] = f"foodDist={fdv} space={sp} danger={d}"
        return o, meta
    return crit

VARIANTS = {
    "baseline":    {"danger": "base",    "ins": None},
    "trap":        {"danger": "trap",    "ins": None},
    "fdpen":       {"danger": "fdpen",   "ins": None},
    "fdpen2":      {"danger": "fdpen2",  "ins": None},
    "fdpen3":      {"danger": "fdpen3",  "ins": None},
    "fdpen4":      {"danger": "fdpen4",  "ins": None},
    "fdpen5":      {"danger": "fdpen5",  "ins": None},
    "look2":       {"danger": "look2",   "ins": None},
    "fdpen6":      {"danger": "fdpen6",  "ins": None},
    "legend":      {"danger": "base",    "ins": LEGEND},
    "traplegend":  {"danger": "trap",    "ins": LEGEND},
}

@torch.no_grad()
def infer(agent, state, crit, ins):
    keys = list(crit.keys())
    q = {"t": "choice", "ins": (L.INSTRUCTIONS + (ins or "")), "crit": crit}
    seq, markers = build_sequence(agent.tok, state, q,
                                  agent.cfg.get("max_len", 512), agent.cfg.get("head_max_len", 192))
    if len(markers) != len(keys):
        raise RuntimeError("options overflow head budget")
    b = collate_items([[{"ids": seq, "markers": markers, "qtype": 0}]], agent.tok.pad_token_id)
    device = agent.device
    with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
        logits, _ = agent.model(b["input_ids"].to(device), b["attention_mask"].to(device),
                               b["marker_pos"].to(device), b["marker_mask"].to(device),
                               b["qtype"].to(device))
    z = logits[0, :len(keys)].float()
    bucket = "choice:3-5"
    t_scale = float(agent.cfg.get("temperature_by_options", {}).get(bucket, 1.0))
    p = torch.softmax(z / max(1e-3, t_scale), -1)
    probs = {k: float(v) for k, v in zip(keys, p)}
    safe_keys = [k for k in keys if not crit[k].startswith("BLOCKED")]
    if not safe_keys:
        return None, probs
    tot = sum(probs[k] for k in safe_keys) or 1e-9
    masked = {k: (probs[k] / tot if k in safe_keys else 0.0) for k in keys}
    return max(masked, key=masked.get), probs

def play(agent, seed, crit_fn, ins):
    rng = random.Random(seed)
    snake, food, facing = L.rand_start(rng)
    head = snake[0]
    eaten = steps_log = 0
    traj = []
    for _ in range(MAX_STEPS):
        crit, meta = crit_fn(head, food, snake, facing)
        state = {"game": "snake", "board": f"{GW}x{GH}", "head": list(head),
                 "body": [list(s) for s in snake], "food": list(food), "facing": facing}
        frame = {"step": len(traj), "h": list(head), "f": list(food), "ln": len(snake),
                 "crit": crit, "meta": meta}
        if all(not m["safe"] for m in meta.values()):
            traj.append({**frame, "choice": None, "cause": "无路可走"})
            return eaten, len(traj), traj
        choice, probs = infer(agent, state, crit, ins)
        frame.update({"choice": choice, "probs": {k: round(v, 3) for k, v in probs.items()}})
        traj.append(frame)
        m = meta[choice]
        if not m["safe"]:
            return eaten, len(traj), traj   # 不该发生（已掩码）
        dx, dy = DIRS[choice]
        ate = [head[0] + dx, head[1] + dy] == list(food)
        head, snake = L.step_move(head, snake, choice, ate)
        facing = choice
        if ate:
            eaten += 1
            food = L.new_food(rng, head, snake)
    return eaten, len(traj), traj

def classify(traj):
    """最后一帧=死亡帧；回溯死前 3 步的选择特征给死法贴标签。"""
    last = traj[-1]
    if last.get("cause") == "无路可走" and last.get("choice") is None:
        tail = traj[-4:-1]
    else:
        tail = traj[-3:]
    labels = []
    for fr in tail:
        if not fr.get("choice"):
            continue
        m = fr["meta"][fr["choice"]]
        if m["sp"] < fr["ln"] + 2:
            labels.append("入袋")
        elif m["run"] <= 1:
            labels.append("短跑道")
    alt = "无更优"
    for fr in traj[-3:]:
        if not fr.get("choice"):
            continue
        best = max((k for k, v in fr["meta"].items() if v["safe"]),
                   key=lambda k: -2 * fr["meta"][k]["fd"] + 0.5 * fr["meta"][k]["sp"] + fr["meta"][k]["run"],
                   default=None)
        if best != fr["choice"]:
            alt = "本有更优"
            break
    return {"death_labels": labels or ["必然/长链"], "heur_disagree": alt}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    cfgv = VARIANTS[name]
    os.makedirs("_tune_runs", exist_ok=True)
    agent = Agent("_graveyard/laya_snake_v2_gen5", device="cuda")
    agent.model.eval()
    crit_fn = make_crit_fn(cfgv["danger"])
    games = []
    LBL = {"入袋": "POCKET", "短跑道": "SHORT-RUN", "必然/长链": "FORCED"}
    for s in SEEDS:
        eaten, nsteps, traj = play(agent, s, crit_fn, cfgv["ins"])
        an = classify(traj)
        last = traj[-1]
        cause = "STUCK" if last.get("cause") == "无路可走" else ("TIMEOUT" if nsteps >= MAX_STEPS else "MASKFAIL")
        tags = "/".join(LBL.get(x, x) for x in an["death_labels"]) or "-"
        heur = "BETTER-EXISTED" if an["heur_disagree"] == "本有更优" else "HEUR-AGREE"
        games.append({"seed": s, "food": eaten, "steps": nsteps, "cause": cause,
                      "analysis": an, "traj": traj})
        print(f"GAME seed={s} food={eaten} steps={nsteps} cause={cause} tags={tags} {heur}", flush=True)
    mean = sum(g["food"] for g in games) / len(games)
    print(f"VARIANT={name} MEAN={mean:.2f} GAMES={[g['food'] for g in games]}", flush=True)
    json.dump({"variant": name, "cfg": {"danger": cfgv["danger"], "legend": bool(cfgv["ins"])},
               "mean": mean, "games": games},
              open(f"_tune_runs/{name}.json", "w", encoding="utf-8"), ensure_ascii=False)
