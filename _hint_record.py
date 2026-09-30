# -*- coding: utf-8 -*-
# 记录 hint 臂 seed1004 通关局的完整食物序列（初始食物 + 每次进食后的新食物），
# 供剧院页「纯提示词」道做同序确定性重放。同时复核该局仍是 141 WIN。
import json, urllib.request, random
from _rlcd_cycle import (GW, GH, DIRS, ORDER, cidx, loop_ahead, land_of, compact,
                         state_of, place_food, step_snake, SHORT)
from _prompt_formula import INSTR, BRIDGE, MAX_STEPS

def play_record(seed):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]
    food = place_food(rng, snake)
    foods = [food]
    eaten = 0; cause = 'cap'; steps = 0; since_food = 0; n_step = 0; n_obey = 0
    from _prompt_to_win import loop_safe
    for steps in range(MAX_STEPS):
        crit = {d: compact(snake, food, d) for d in ORDER}
        st = state_of(snake, food); st['stepsSinceFood'] = since_food
        req = {'model': 'cycle', 'state': st, 'instructions': INSTR['hint'], 'criteria': crit}
        r = urllib.request.Request(BRIDGE + '/decide', json.dumps(req).encode(), {'Content-Type': 'application/json'})
        resp = json.load(urllib.request.urlopen(r))
        choice = resp['choice']
        n_step += 1; n_obey += 1 if loop_safe(snake, food, choice) else 0
        snake, died, ate = step_snake(snake, food, choice)
        if died: cause = 'wall/body'; break
        if ate:
            eaten += 1; since_food = 0
            food = place_food(rng, snake)
            if food is None: cause = 'WIN 通关'; break
            foods.append(food)
        else:
            since_food += 1
        if steps % 1500 == 0: print('  rec seed%d eaten %d step %d' % (seed, eaten, steps), flush=True)
    return {'seed': seed, 'food': eaten, 'cause': cause, 'steps': steps,
            'obey_rate': round(n_obey / max(n_step, 1), 3), 'foods': foods}

if __name__ == '__main__':
    r = play_record(1004)
    json.dump(r, open('_hint_foodseq_1004.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('DONE', r['seed'], r['food'], r['cause'], 'steps', r['steps'], 'obey', r['obey_rate'], 'nfoods', len(r['foods']))
