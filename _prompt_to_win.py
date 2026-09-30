# -*- coding: utf-8 -*-
# 纯提示词升级逼通关实验：对桥上 cycle 模型（读过环契约特征）在推理时施加"环不变量前瞻动作掩码"。
# 环安全的方向保留原训练串（不剧透答案）；环不安全/墙/身 方向加 BLOCKED: 前缀 → 桥接掩码清零。
# 环不变量保证：只在环安全方向里走 → 永不自我封锁 → 沿哈密顿环必然吃满 → 通关。
import json, urllib.request, random, sys
from _rlcd_cycle import (GW, GH, DIRS, ORDER, cidx, loop_ahead, land_of, compact,
                         grid_rows, state_of, place_food, step_snake, SHORT)

BRIDGE = 'http://127.0.0.1:8890'
MAX_STEPS = 20000

def loop_safe(snake, food, d):
    hx, hy = snake[0]; dx, dy = DIRS[d]; nx, ny = hx + dx, hy + dy
    land = land_of(nx, ny, snake, food)
    if land in ('wall', 'body'): return False
    hi = cidx(hx, hy); cd = (cidx(nx, ny) - hi) % 144
    df, m1, m2 = loop_ahead(snake, food)
    if (nx, ny) == food:              # 这一步吃
        return cd <= m1 - 1
    return cd <= m2 - 1 and cd <= df  # 不吃：不得越过尾/身，也不得越过食物

def crit_masked(snake, food):
    c = {}
    for d in ORDER:
        base = compact(snake, food, d)
        c[d] = base if loop_safe(snake, food, d) else 'BLOCKED: ' + base
    return c

def decide(state, criteria):
    req = {'model': 'cycle', 'state': state, 'instructions': SHORT, 'criteria': criteria}
    r = urllib.request.Request(BRIDGE + '/decide', json.dumps(req).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r))

def play(seed):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]
    food = place_food(rng, snake)
    eaten = 0; cause = 'cap'; steps = 0; masked_hist = {'UP':0,'DOWN':0,'LEFT':0,'RIGHT':0}; alive_steps = 0
    for steps in range(MAX_STEPS):
        crit = crit_masked(snake, food)
        resp = decide(state_of(snake, food), crit)
        choice = resp['choice']; probs = resp.get('probabilities', {})
        legal = [d for d in ORDER if not crit[d].startswith('BLOCKED')]
        if len(legal) > 1: alive_steps += 1
        for d in ORDER:
            if crit[d].startswith('BLOCKED'): masked_hist[d] += 1
        snake, died, ate = step_snake(snake, food, choice)
        if died:
            hx, hy = snake[0]; dx, dy = DIRS[choice]; nx, ny = hx + dx, hy + dy
            cause = 'wall/body'
            break
        if ate:
            eaten += 1
            food = place_food(rng, snake)
            if food is None: cause = 'WIN 通关'; break
    return {'seed': seed, 'food': eaten, 'cause': cause, 'steps': steps,
            'multi_legal_rate': round(alive_steps / max(steps, 1), 2)}

if __name__ == '__main__':
    seeds = [int(s) for s in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['1000', '1001', '1002'])]
    out = [play(s) for s in seeds]
    json.dump(out, open('_prompt_to_win.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in out:
        print('seed', r['seed'], 'food', r['food'], r['cause'], 'steps', r['steps'], 'multiLegal%', int(r['multi_legal_rate']*100))
