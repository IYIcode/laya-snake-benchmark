# -*- coding: utf8 -*-
"""Post-optimization re-measure: HTTP /decide latency (keep-alive) + behavioral sanity.

1) 30 sequential keep-alive /decide calls -> p50/p90/max
2) play one greedy 120-step game through the bridge -> food eaten (proves bf16 path decides like before)
"""
import http.client, json, os, random, statistics, sys, time

import laya_finetune_snake as L

def api(conn, path, body=None):
    conn.request("POST" if body else "GET", path,
                 json.dumps(body).encode() if body else None,
                 {"Content-Type": "application/json"})
    r = conn.getresponse()
    return json.loads(r.read().decode())

def main():
    conn = http.client.HTTPConnection("127.0.0.1", 8890, timeout=10)
    h = api(conn, "/health")
    print("health:", h, flush=True)

    state = {"game":"snake","board":"12x12","head":[6,6],"body":[[6,6],[5,6],[4,6]],"food":[9,3],"facing":"RIGHT"}
    crit = L.criteria_from(L.decide([6,6],[9,3],[[6,6],[5,6],[4,6]],"RIGHT"))
    body = {"state": state, "criteria": crit}
    ts = []
    for i in range(30):
        t0 = time.perf_counter()
        j = api(conn, "/decide", body)
        ts.append((time.perf_counter() - t0) * 1000)
        if i == 0:
            print("first:", {k: j[k] for k in ("choice", "ms")}, "probs:", {k: round(v, 3) for k, v in j["probabilities"].items()}, flush=True)
    ts.sort()
    print(f"HTTP keep-alive x30: p50={statistics.median(ts):.1f}ms p90={ts[int(27)]:.1f}ms max={ts[-1]:.1f}ms", flush=True)

    # behavioral game
    rng = random.Random(7)
    snake = [[6,6],[5,6],[4,6]]; food = [9,3]; facing = "RIGHT"; eaten = 0
    for steps in range(1, 121):
        cands = L.decide(snake[0], food, snake, facing)
        crit = L.criteria_from(cands)
        st = {"game":"snake","board":"12x12","head":list(snake[0]),"body":[list(s) for s in snake],"food":list(food),"facing":facing}
        j = api(conn, "/decide", {"state": st, "criteria": crit})
        ch = j["choice"]
        c = next(x for x in cands if x["dir"] == ch)
        if not c["safe"]:
            print(f"game: died at step {steps}, ate {eaten}, len {len(snake)}", flush=True)
            break
        dx, dy = L.DIRS[ch]
        ate = [snake[0][0] + dx, snake[0][1] + dy] == food
        _, snake = L.step_move(snake[0], snake, ch, ate)
        facing = ch
        if ate:
            eaten += 1
            food = L.new_food(rng, snake[0], snake)
    else:
        print(f"game: survived 120 steps, ate {eaten}, len {len(snake)}", flush=True)

if __name__ == "__main__":
    main()
