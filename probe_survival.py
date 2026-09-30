# -*- coding: utf-8 -*-
import os, random
import laya_finetune_snake as L
from laya import Agent
HERE = os.path.dirname(os.path.abspath(__file__))
ag = Agent(os.path.join(HERE, "laya_snake_ft"), device="cuda")
model, tok, cfg = ag.model, ag.tok, ag.cfg

def run_game(rng, max_steps):
    snake, food, facing = L.rand_start(rng)
    head = snake[0]
    eaten = 0
    died = False
    for _ in range(max_steps):
        cands = L.decide(head, food, snake, facing)
        crit = L.criteria_from(cands)
        state = {"game":"snake","board":f"{L.GW}x{L.GH}","head":list(head),
                 "body":[list(s) for s in snake],"food":list(food),"facing":facing}
        chosen,_ = L.model_decide(model, tok, cfg, state, crit)
        c = next(x for x in cands if x["dir"]==chosen)
        if not c["safe"]:
            died = True; break
        ate = [head[0]+L.DIRS[chosen][0], head[1]+L.DIRS[chosen][1]] == list(food)
        head, snake = L.step_move(head, snake, chosen, ate)
        facing = chosen
        if ate:
            eaten += 1
            food = L.new_food(rng, head, snake)
    return eaten, len(snake), died

for cap in (400, 1500):
    rng = random.Random(cap)
    res = [run_game(rng, cap) for _ in range(8)]
    foods = [r[0] for r in res]; lens=[r[1] for r in res]; deaths=sum(1 for r in res if r[2])
    print(f"cap={cap}: foods={foods} mean={sum(foods)/8:.1f} | finalLen={lens} maxlen={max(lens)} | died={deaths}/8")
