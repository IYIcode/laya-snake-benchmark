# -*- coding: utf-8 -*-
# 底模 rescue 对照：同一无训练 laya，输入信息量逐级加大，看"给依据"能不能替代训练。
# arm advice : 契约小抄之外，直接列出本步环安全的方向（依据喂到嘴边）
# arm answer : 直接写出"本步应该选哪个方向"（结论喂到脸上，测最低要求"听话"）
import json, urllib.request, random
from _rlcd_cycle import (GW, GH, DIRS, ORDER, compact, state_of, place_food, step_snake, SHORT)
from _prompt_to_win import loop_safe

BRIDGE = 'http://127.0.0.1:8890'
MAX_STEPS = 2000

def best_dirs(snake, food):
    safe = [d for d in ORDER if loop_safe(snake, food, d)]
    if not safe: return [], None
    hx, hy = snake[0]
    def rank(d):
        dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
        return abs(nx - food[0]) + abs(ny - food[1])
    d0 = sorted(safe, key=rank)[0]
    return safe, d0

def play(seed, arm):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]
    food = place_food(rng, snake)
    eaten = 0; steps = 0; cause = 'cap'
    for steps in range(MAX_STEPS):
        safe, d0 = best_dirs(snake, food)
        instr = SHORT
        if arm == 'advice':
            instr += (" Additional basis for THIS state: the safe moves right now are "
                      + (', '.join(safe) if safe else 'NONE') + ". Choose one of them.")
        elif arm == 'answer':
            instr += (" The correct move for THIS exact state is " + (d0 if d0 else 'RIGHT') + ". Pick it.")
        crit = {d: compact(snake, food, d) for d in ORDER}
        req = {'model': 'laya', 'state': state_of(snake, food), 'instructions': instr, 'criteria': crit}
        r = urllib.request.Request(BRIDGE + '/decide', json.dumps(req).encode(), {'Content-Type': 'application/json'})
        choice = json.load(urllib.request.urlopen(r))['choice']
        snake, died, ate = step_snake(snake, food, choice)
        if died: cause = 'wall/body'; break
        if ate:
            eaten += 1
            food = place_food(rng, snake)
            if food is None: cause = 'WIN 通关'; break
    return {'seed': seed, 'arm': arm, 'model': 'laya', 'food': eaten, 'cause': cause, 'steps': steps}

if __name__ == '__main__':
    out = []
    for arm in ('advice', 'answer'):
        for s in (1000, 1001, 1002):
            r = play(s, arm); out.append(r)
            print('FINAL', arm, 'seed', r['seed'], 'food', r['food'], r['cause'], 'steps', r['steps'], flush=True)
    json.dump(out, open('_prompt_base_rescue.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
