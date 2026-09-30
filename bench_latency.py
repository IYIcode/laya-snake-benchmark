# -*- coding: utf8 -*-
"""Benchmark where the decision-loop latency goes and which knobs help.

GPU forward (batch=1, realistic snake question, 60 runs each unless noted):
  A) fp32 weights + bf16 autocast   (current bridge config)
  B) bf16 weights (act_head kept fp32), no autocast
  C) fp32 weights + fp16 autocast
  D) torch.compile + bf16 autocast  (compile once, then time)
Token budget: full 242-token sequence vs short instructions (bf16 autocast).
HTTP: sequential /decide with vs without keep-alive (if bridge is up).
Reports p50/p90 in ms. Each config guarded so a failure doesn't abort the run.
"""
import json, os, statistics, sys, time

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
from laya import Agent
from laya.common import build_sequence, collate_items
import laya_finetune_snake as L

HERE = os.path.dirname(os.path.abspath(__file__))
N = 60

def prep(agent, state, criteria):
    q = {"t": "choice", "ins": L.INSTRUCTIONS, "crit": criteria}
    seq, markers = build_sequence(agent.tok, state, q, agent.cfg["max_len"], agent.cfg["head_max_len"])
    return collate_items([[{"ids": seq, "markers": markers, "qtype": 0}]], agent.tok.pad_token_id)

def run_once(fn):
    fn()

def timeit(label, fn, n=N):
    try:
        for _ in range(8):
            fn()
        ts = []
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            torch.cuda.synchronize()
            ts.append((time.perf_counter() - t0) * 1000)
        ts.sort()
        print(f"  {label:<44} p50={statistics.median(ts):6.1f}ms p90={ts[int(n*0.9)]:6.1f}ms min={ts[0]:5.1f}", flush=True)
        return statistics.median(ts)
    except Exception as e:
        print(f"  {label:<44} FAILED: {type(e).__name__}: {str(e)[:110]}", flush=True)
        return None

def fwd(model, b, dev, autocast=None):
    def go():
        args = (b["input_ids"].to(dev), b["attention_mask"].to(dev),
                b["marker_pos"].to(dev), b["marker_mask"].to(dev), b["qtype"].to(dev))
        if autocast:
            with torch.autocast(device_type="cuda", dtype=autocast):
                model(*args)
        else:
            model(*args)
    return go

def main():
    print("loading ft agent...", flush=True)
    ag = Agent(os.path.join(HERE, "laya_snake_ft"), device="cuda")
    state = {"game":"snake","board":"12x12","head":[6,6],"body":[[6,6],[5,6],[4,6]],"food":[9,3],"facing":"RIGHT"}
    cands = L.decide([6,6],[9,3],[[6,6],[5,6],[4,6]],"RIGHT")
    crit = L.criteria_from(cands)
    b = prep(ag, state, crit)
    dev = ag.device
    model = ag.model
    print(f"seq len = {b['input_ids'].shape[1]} tokens", flush=True)

    print("\n== GPU forward latency ==", flush=True)
    timeit("A fp32 + bf16 autocast (current)", fwd(model, b, dev, torch.bfloat16))

    try:
        m2 = ag.model.bfloat16()
        m2.act_head.float()
        timeit("B bf16 weights, act_head fp32, no autocast", fwd(m2, b, dev))
    finally:
        model.float()

    timeit("C fp32 + fp16 autocast", fwd(model, b, dev, torch.float16))

    # D: torch.compile
    try:
        cm = torch.compile(model)
        print("  compiling (this can take a couple of minutes)...", flush=True)
        t0 = time.perf_counter()
        fwd(cm, b, dev, torch.bfloat16)()
        torch.cuda.synchronize()
        print(f"  compile took {time.perf_counter()-t0:.0f}s", flush=True)
        timeit("D torch.compile + bf16 autocast", fwd(cm, b, dev, torch.bfloat16))
    except Exception as e:
        print(f"  D torch.compile FAILED: {type(e).__name__}: {str(e)[:110]}", flush=True)

    print("\n== token budget effect (bf16 autocast) ==", flush=True)
    short = L.INSTRUCTIONS
    L.INSTRUCTIONS = "Choose the snake's next direction. Options list foodDist (lower better), space (higher safer), danger (lower safer). Avoid BLOCKED."
    b2 = prep(ag, state, crit)
    print(f"  short-instruction seq len = {b2['input_ids'].shape[1]}", flush=True)
    timeit("E short template + bf16 autocast", fwd(model, b2, dev, torch.bfloat16))
    L.INSTRUCTIONS = short
    timeit("F full template control", fwd(model, b, dev, torch.bfloat16))

    # batch-of-3: does one call for all candidates beat 3 calls? (bridge currently 1 call)
    print("\n== misc ==", flush=True)
    try:
        # bf16 autocast + compile combined
        timeit("G compile + bf16 autocast (rerun post-warm)", fwd(cm, b, dev, torch.bfloat16))
    except Exception:
        pass

    print("\n== HTTP latency (needs bridge on :8890) ==", flush=True)
    try:
        import urllib.request
        url = "http://127.0.0.1:8890/decide"
        body = json.dumps({"state": state, "criteria": crit}).encode()
        ts = []
        for _ in range(20):
            t0 = time.perf_counter()
            req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                r.read()
            ts.append((time.perf_counter() - t0) * 1000)
        print(f"  H HTTP no-keepalive  p50={statistics.median(ts):.1f}ms max={max(ts):.1f}", flush=True)
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", 8890)
        ts = []
        for _ in range(20):
            t0 = time.perf_counter()
            conn.request("POST", "/decide", body, {"Content-Type": "application/json", "Connection": "keep-alive"})
            conn.getresponse().read()
            ts.append((time.perf_counter() - t0) * 1000)
        conn.close()
        print(f"  I HTTP keep-alive    p50={statistics.median(ts):.1f}ms max={max(ts):.1f}", flush=True)
    except Exception as e:
        print("  bridge not reachable:", e, flush=True)

if __name__ == "__main__":
    main()
