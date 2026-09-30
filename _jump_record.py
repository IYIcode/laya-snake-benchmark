# -*- coding: utf-8 -*-
# 录制「报错账」配方（hintJumpOnly：state 只加 jumpCount，无 stepsSinceFood）的通关局食物序列，
# 供演示页第 10 条赛道同序重放。默认 seed1002（实测 141 WIN 4592 步）。
import json, urllib.request, random, sys
from _rlcd_cycle import (GW, GH, DIRS, ORDER, compact, state_of, place_food, step_snake)
from _prompt_formula import INSTR, BRIDGE, MAX_STEPS
from _prompt_to_win import loop_safe

def play_record(seed):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]
    food = place_food(rng, snake)
    foods = [food]
    eaten = 0; cause = 'cap'; steps = 0; n_jump = 0; n_step = 0; n_obey = 0
    for steps in range(MAX_STEPS):
        crit = {d: compact(snake, food, d) for d in ORDER}
        st = state_of(snake, food); st['jumpCount'] = n_jump
        req = {'model': 'cycle', 'state': st, 'instructions': INSTR['hintJumpOnly'], 'criteria': crit}
        r = urllib.request.Request(BRIDGE + '/decide', json.dumps(req).encode(), {'Content-Type': 'application/json'})
        choice = json.load(urllib.request.urlopen(r))['choice']
        n_step += 1
        obey = loop_safe(snake, food, choice)
        n_obey += 1 if obey else 0
        if not obey: n_jump += 1
        snake, died, ate = step_snake(snake, food, choice)
        if died: cause = 'wall/body'; break
        if ate:
            eaten += 1
            food = place_food(rng, snake)
            if food is None: cause = 'WIN 通关'; break
            foods.append(food)
        if steps % 1500 == 0: print('  rec seed%d eaten %d step %d jumps %d' % (seed, eaten, steps, n_jump), flush=True)
    return {'seed': seed, 'food': eaten, 'cause': cause, 'steps': steps, 'jumps': n_jump,
            'obey_rate': round(n_obey / max(n_step, 1), 3), 'foods': foods}

if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1002
    r = play_record(seed)
    json.dump(r, open('_jumpfood_%d.json' % seed, 'w', encoding='utf-8'), ensure_ascii=False)
    print('DONE', r['seed'], r['food'], r['cause'], 'steps', r['steps'], 'jumps', r['jumps'], 'obey', r['obey_rate'], 'nfoods', len(r['foods']))
