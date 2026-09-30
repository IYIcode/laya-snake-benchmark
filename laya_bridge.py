# -*- coding: utf-8 -*-
"""HTTP bridge exposing one or MORE versions of the REAL Laya snake model.

Endpoints (CORS wide-open, localhost only by convention):
  GET  /health  -> {"ok":true,"default":"v1","models":{"v1":{"model":...,"warm_ms":...}, ...}}
  POST /decide  -> body {"model":"v2"(optional),"state":{...},"criteria":{"UP":"...",...}}
                   reply {"choice":"UP","probabilities":{...},"ms":28.1,"model":"v2","tag":...}

Multi-model lets the versus page (laya-snake-versus.html) race training generations
side by side. Usage:
  python laya_bridge.py --model v1=laya_snake_ft --model v2=laya_snake_v2_gen3
With no --model args it auto-discovers v1=laya_snake_ft and v2=latest laya_snake_v2_genN.
"""
import argparse, json, os, sys, threading, time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {}            # name -> {"agent":..., "tag":str, "lock":threading.Lock, "warm_ms":float}
ORDER = []             # load order; ORDER[0] is the default when caller says no model

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

HB_STATE = {"game": "snake", "board": "12x12", "head": [6, 6],
            "body": [[6, 6], [5, 6], [4, 6]], "food": [9, 3], "facing": "RIGHT"}
HB_CRIT = {"UP": "foodDist=4 space=40 danger=0",
           "RIGHT": "foodDist=6 space=40 danger=0",
           "DOWN": "foodDist=8 space=40 danger=2"}

import collections
DEC_LOG = collections.deque(maxlen=400)   # GET /log?n=30 → 真实决策流水（含原始/遮罩概率）


def to_grid_state(st):
    """坐标 state -> 0/1/2/3 全盘矩阵 state（v3-grid 系模型训练时吃的是矩阵）。
    网页端不用改：桥接按模型 meta 里的 rep=grid 自动翻译。"""
    gw, gh = (int(x) for x in str(st.get("board", "12x12")).lower().split("x"))
    g = [["0"] * gw for _ in range(gh)]
    for seg in st["body"][1:]:
        x, y = int(seg[0]), int(seg[1])
        if 0 <= y < gh and 0 <= x < gw:
            g[y][x] = "1"
    g[int(st["food"][1])][int(st["food"][0])] = "3"
    g[int(st["head"][1])][int(st["head"][0])] = "2"
    return {"game": "snake", "board": st.get("board", "12x12"),
            "grid": ["".join(r) for r in g], "facing": st["facing"]}


def load_one(name, src):
    from laya import Agent
    import torch
    path = src if os.path.isabs(src) else os.path.join(HERE, src)
    local = os.path.exists(os.path.join(path, "model.safetensors"))
    real = path if local else src
    print(f"[bridge] {name}: loading {real} ...", flush=True)
    agent = Agent(real, device="cuda")
    # bench_latency.py: bf16 weights (act_head stays fp32) beats fp32+autocast 28.9 vs 33.8ms
    agent.model.bfloat16()
    agent.model.act_head.float()
    agent.dtype = torch.bfloat16   # agent.system_one autocasts with cfg amp_dtype (fp16) otherwise
    # per-model meta: tag for UI, rep=grid → this model reads the 0/1/2/3 board matrix,
    # so /decide translates the page's coordinate state on the fly (pages stay unchanged)
    rep, tag = None, ("laya-snake-ft (421M ModernBERT)" if local else "laya-english zero-shot") + f" [{name}]"
    if local:
        meta_path = os.path.join(path, "evolution_meta.json")
        if os.path.exists(meta_path):
            try:
                m = json.load(open(meta_path, encoding="utf-8"))
                mean = (m.get("this") or {}).get("mean", m.get("mean", m.get("best_mean")))
                if m.get("gen") and mean is not None:
                    tag = f"{m['gen']} 平均{float(mean):.1f}食物/局"
                rep = m.get("rep")
            except Exception:
                pass
    hb_state = to_grid_state(HB_STATE) if rep == "grid" else HB_STATE
    # warm-up: dummy question, then a REALISTIC snake sequence shape so the browser's
    # first /decide doesn't pay a one-time ~180ms CUDA/shape penalty
    q0 = {"action": {"type": "choice", "instructions": "warm up",
                     "criteria": {"A": "x", "B": "y"}}}
    agent.system_one({"warm": 1}, q0)
    t0 = time.perf_counter()
    agent.system_one({"warm": 1}, q0)
    rq = {"action": {"type": "choice", "instructions": INSTRUCTIONS, "criteria": HB_CRIT}}
    for _ in range(3):
        agent.system_one(hb_state, rq)
    # also warm the raw-grid shape (0/1/2/3 board pages send ~257-token grid states)
    rq_raw = {"action": {"type": "choice", "instructions": INSTRUCTIONS,
                         "criteria": {"UP": "move up one cell", "DOWN": "move down one cell",
                                      "LEFT": "move left one cell", "RIGHT": "move right one cell"}}}
    for _ in range(2):
        agent.system_one(to_grid_state(HB_STATE), rq_raw)
    warm = round((time.perf_counter() - t0) * 1000, 1)
    MODELS[name] = {"agent": agent, "tag": tag, "rep": rep,
                    "lock": threading.Lock(), "warm_ms": warm}
    print(f"[bridge] {name}: ready device=cuda warm_ms={warm} rep={rep} tag={tag}", flush=True)


def auto_discover():
    specs = []
    if os.path.exists(os.path.join(HERE, "laya_snake_ft", "model.safetensors")):
        specs.append(("v1", "laya_snake_ft"))
    gens = sorted([d for d in os.listdir(HERE)
                   if d.startswith("laya_snake_v2_gen") and
                   os.path.exists(os.path.join(HERE, d, "model.safetensors"))],
                  key=lambda d: int(d.replace("laya_snake_v2_gen", "") or 0))
    if gens:
        specs.append(("v2", gens[-1]))
    if not specs:
        specs.append(("v0", "convaiinnovations/laya"))
    return specs


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # responses set Content-Length -> safe keep-alive

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        # cache CORS preflight in the browser, else every /decide pays an extra round-trip
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            self._send(200, {"ok": bool(MODELS), "default": ORDER[0] if ORDER else None,
                             "models": {k: {"model": v["tag"], "device": "cuda",
                                            "warm_ms": v["warm_ms"]} for k, v in MODELS.items()}})
        elif self.path.startswith("/log"):
            # GET /log?n=30 -> 最近 n 条真实决策流水（含原始概率/遮罩后概率）
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            try:
                n = max(1, min(400, int(q.get("n", ["15"])[0])))
            except ValueError:
                n = 15
            self._send(200, {"ok": True, "count": len(DEC_LOG), "entries": list(DEC_LOG)[-n:]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/decide"):
            self._send(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            name = req.get("model") or (ORDER[0] if ORDER else None)
            entry = MODELS.get(name)
            if entry is None:
                self._send(400, {"error": f"unknown model {name!r}", "available": ORDER})
                return
            state = req["state"]
            criteria = req["criteria"]          # {action: description}
            if entry.get("rep") == "grid":
                state = to_grid_state(state)    # 矩阵版模型：服务端翻译，网页零改动
            keys = list(criteria.keys())
            if len(keys) == 1:
                # laya's act-head topk(2) crashes on a single option; forced move
                self._send(200, {"choice": keys[0], "probabilities": {keys[0]: 1.0},
                                 "ms": 0.0, "model": name, "tag": entry["tag"], "forced": True})
                return
            questions = {"action": {"type": "choice",
                                    "instructions": req.get("instructions") or INSTRUCTIONS,
                                    "criteria": criteria}}
            t0 = time.perf_counter()
            with entry["lock"]:                 # serialize GPU per model
                out = entry["agent"].system_one(state, questions)
            ms = round((time.perf_counter() - t0) * 1000, 1)
            a = out["answers"]["action"]
            raw = dict(a["probabilities"])
            # 动作遮罩：criteria 标了 BLOCKED 的选项概率清零后归一（库本来的 action mask 语义）。
            # 模型仍被真实询问、真实打分，只是不让它选中"物理上必死"的方向。
            blocked = {k for k, v in criteria.items() if "BLOCKED" in str(v)}
            probs, masked = raw, False
            if blocked & set(raw):
                left = {k: (0.0 if k in blocked else v) for k, v in raw.items()}
                s = sum(left.values())
                probs = {k: (v / s if s > 0 else 1.0 / len(raw) * (k not in blocked))
                         for k, v in left.items()}
                if s == 0:
                    ok = [k for k in raw if k not in blocked]
                    probs = {k: (1.0 / len(ok) if k in ok else 0.0) for k in raw}
                masked = True
            choice = max(probs, key=probs.get)
            DEC_LOG.append({"t": round(time.time(), 1), "model": name,
                            "head": state.get("head"), "food": state.get("food"),
                            "facing": state.get("facing"), "len": len(state.get("body", [])),
                            "criteria": criteria, "raw": {k: round(v, 4) for k, v in raw.items()},
                            "masked": masked,
                            "probs": {k: round(v, 4) for k, v in probs.items()},
                            "choice": choice, "ms": ms})
            self._send(200, {"choice": choice, "probabilities": probs,
                             "raw_probabilities": raw, "masked": masked,
                             "confidence": a["confidence"], "ms": ms,
                             "model": name, "tag": entry["tag"]})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        pass  # keep the console clean for demo day


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8890)
    ap.add_argument("--model", action="append", default=[],
                    help="name=path (repeatable), e.g. --model v1=laya_snake_ft --model v2=laya_snake_v2_gen3")
    args = ap.parse_args()
    specs = []
    for s in args.model:
        name, _, path = s.partition("=")
        if not path:
            name, path = "v1", name
        specs.append((name, path))
    if not specs:
        specs = auto_discover()
    for name, path in specs:
        load_one(name, path)
        ORDER.append(name)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[bridge] listening on http://127.0.0.1:{args.port} models={ORDER} (Ctrl+C to stop)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
