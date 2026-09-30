# -*- coding: utf-8 -*-
import random
import laya_finetune_snake as L
def run_teacher(rng, max_steps):
    snake, food, facing = L.rand_start(rng)
    head = snake[0]; eaten = 0; died=False
    for _ in range(max_steps):
        cands = L.decide(head, food, snake, facing)
        best = max(cands, key=lambda c:c["s"])          # 贪心按分
        safe_best = max([c for c in cands if c["safe"]], key=lambda c:c["s"], default=None)
        if safe_best is None: died=True; break
        chosen = safe_best["dir"]
        if not safe_best["safe"]: died=True; break
        ate=[head[0]+L.DIRS[chosen][0],head[1]+L.DIRS[chosen][1]]==list(food)
        head,snake=L.step_move(head,snake,chosen,ate); facing=chosen
        if ate: eaten+=1; food=L.new_food(rng,head,snake)
    return eaten,len(snake),died
rng=random.Random(1500)
res=[run_teacher(rng,1500) for _ in range(8)]
f=[r[0] for r in res];l=[r[1] for r in res];d=sum(1 for r in res if r[2])
print(f"TEACHER(启发式规则,cap=1500): foods={f} mean={sum(f)/8:.1f} maxlen={max(l)} died={d}/8")
