# -*- coding: utf-8 -*-
# 实验：把环安全"计算公式"本身交给模型，不做代码判定/BLOCKED 前缀/桥接清零。
#   模型仍能看到公式(SHORT instructions)与全部比较数字(state.loopAhead 三数 + 每选项 cyc)，
#   但没有任何东西替它否决方向 —— argmax 选什么就走什么，撞墙/撞身/困死真实结算。
# arm formula: criteria=原始 compact(无 BLOCKED) —— "公式发给模型，你自己算"
# arm masked : criteria=加 BLOCKED 前缀 —— 现状(对照, 已知 4/4 141)
# 诊断量: obey% = 模型所选方向满足 loop_safe 不等式的比例(逐步统计, 比得分更直接回答"听没听公式")
import json, urllib.request, random, sys, os
from _rlcd_cycle import (GW, GH, DIRS, ORDER, cidx, loop_ahead, land_of, compact,
                         state_of, place_food, step_snake, SHORT)
from _prompt_to_win import loop_safe

BRIDGE = 'http://127.0.0.1:8890'
MAX_STEPS = 20000

# formula_calc 臂：在训练契约 SHORT 后追加显式"逐步自己比"的指令（仍是规则/事实，无 BLOCKED 无结论）
CALC_TAIL = (" Before you choose, CHECK each option yourself: read its cyc, read bodyGoAhead and foodAhead "
             "from the state, and verify the inequality: if this move eats, cyc must be at most bodyAhead-1; "
             "otherwise cyc must be at most bodyGoAhead-1 AND at most foodAhead. An option failing its check "
             "is unavailable to you. Among the options that pass, pick the one closest to the food.")
# 用户的"时间感"假设：stepsSinceFood 进 state，规则里说明这个数字与死圈的关系，模型自己权衡，零掩码
HINT_TAIL = (" The state also carries stepsSinceFood = how many steps you have gone without eating. "
             "A small value means you are reaching food normally. A LARGE value (over 100) means you are "
             "stuck circling and will keep circling forever unless you change behavior: while it is large, "
             "refuse any move whose cyc is greater than bodyGoAhead (that jumps across your own body on the "
             "loop and is what created the circle); follow the loop toward foodAhead instead. As "
             "stepsSinceFood grows, this avoidance becomes more important than getting closer to the food.")
# hintA：把"拒绝跳身"从"数值大时才生效"升级为全程规则（死因数据：首违多发生在 sfs 很小的早期）
HINT_TAIL_A = (" The state also carries stepsSinceFood = how many steps you have gone without eating. "
               "A rule that applies at EVERY step, small or large: never pick a move whose cyc is greater than "
               "bodyGoAhead - such a move jumps across your own body on the loop, and it is the trap that ends "
               "games. When stepsSinceFood is large (over 100) you are already circling: hug the loop toward "
               "foodAhead until you eat. As stepsSinceFood grows, avoiding those jump moves matters more than "
               "getting closer to the food.")
# hintB：后果框架——一次跳身＝身体散出环外、再也回不了环（真实死因），把禁忌绑定到"蛇会死"
HINT_TAIL_B = (" The state also carries stepsSinceFood = how many steps you have gone without eating. "
               "Every move whose cyc is greater than bodyGoAhead jumps across your own body on the loop. "
               "In your own finished games, picking one such move at any point - even early, even when "
               "stepsSinceFood is small - is what later killed the snake: after a single jump the body "
               "scatters off the loop and getting back on it becomes impossible. So treat cyc greater than "
               "bodyGoAhead as forbidden at every step, no matter how close it looks to the food. "
               "When stepsSinceFood is large you are already circling: hug the loop toward foodAhead until you eat.")
J_TAIL = (" The state also carries jumpCount = how many times earlier in THIS game you already picked a move "
          "whose cyc was greater than bodyGoAhead, i.e. jumped across your own body on the loop. Every one of "
          "those jumps makes the game harder to finish: your goal is to finish the game with jumpCount = 0.")
S_TAIL = (" The state also carries bodyScatter = how many separate pieces your body is broken into along the "
          "loop (a snake sitting cleanly on the loop has bodyScatter = 1). Each jump across your body raises "
          "bodyScatter and pieces you off the loop; keeping bodyScatter low is what lets you keep circling safely.")
INSTR = {'formula': SHORT, 'formula_calc': SHORT + CALC_TAIL, 'masked': SHORT,
         'timer': SHORT, 'timer_sticky': SHORT, 'hint': SHORT + HINT_TAIL,
         'hintA': SHORT + HINT_TAIL_A, 'hintB': SHORT + HINT_TAIL_B,
         'hintNum': SHORT,
         'hintJ': SHORT + HINT_TAIL + J_TAIL,
         'hintS': SHORT + HINT_TAIL + S_TAIL,
         'hintJumpOnly': SHORT + J_TAIL,
         'hintJS': SHORT + HINT_TAIL + J_TAIL + S_TAIL}

def loop_segments(snake):
    idx = {cidx(*p) for p in snake}
    if len(idx) >= 144: return 1
    pairs = sum(1 for i in idx if (i + 1) % 144 in idx)
    return max(len(idx) - pairs, 1)

MODEL = os.environ.get('PF_MODEL', 'cycle')  # 对照实验：PF_MODEL=laya 换成未训练底模，提示词一字不改

def decide(state, criteria, arm):
    req = {'model': MODEL, 'state': state, 'instructions': INSTR[arm], 'criteria': criteria}
    r = urllib.request.Request(BRIDGE + '/decide', json.dumps(req).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r))

def play(seed, arm, T=300):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]
    food = place_food(rng, snake)
    eaten = 0; cause = 'cap'; steps = 0; n_step = 0; n_obey = 0
    first_break = None
    since_food = 0; rescue = False; n_rescue_on = 0; rescue_steps = 0; auto_steps = 0; n_jump = 0
    for steps in range(MAX_STEPS):
        if arm in ('timer', 'timer_sticky') and since_food >= T and not rescue:
            rescue = True; n_rescue_on += 1
        crit = {}; masked_now = False
        for d in ORDER:
            base = compact(snake, food, d)
            ok = loop_safe(snake, food, d)
            if (arm == 'masked' or (arm in ('timer', 'timer_sticky') and rescue)) and not ok:
                base = 'BLOCKED: ' + base
            crit[d] = base
        if arm in ('masked', 'timer', 'timer_sticky'):
            legal = [d for d in ORDER if not crit[d].startswith('BLOCKED')]
            if not legal:  # 环掩码过 restrictive（违约后身体散布环上）→ 退到只掩物理死格
                crit = {d: (compact(snake, food, d) if land_of(snake[0][0]+DIRS[d][0], snake[0][1]+DIRS[d][1], snake, food) not in ('wall','body')
                            else 'BLOCKED: ' + compact(snake, food, d)) for d in ORDER}
                legal = [d for d in ORDER if not crit[d].startswith('BLOCKED')]
                if not legal:  # 全物理死局 → 放开由模型自选（真困死）
                    crit = {d: compact(snake, food, d) for d in ORDER}
            masked_now = any(v.startswith('BLOCKED') for v in crit.values())
        if rescue: rescue_steps += 1
        else: auto_steps += 1
        st = state_of(snake, food)
        if arm.startswith('hint') and arm != 'hintJumpOnly': st['stepsSinceFood'] = since_food
        if arm in ('hintJ', 'hintJumpOnly', 'hintJS'): st['jumpCount'] = n_jump
        if arm in ('hintS', 'hintJS'): st['bodyScatter'] = loop_segments(snake)
        resp = decide(st, crit, arm)
        choice = resp['choice']
        n_step += 1
        obey = loop_safe(snake, food, choice)
        if obey: n_obey += 1
        else: n_jump += 1
        if not obey and first_break is None and arm != 'masked':
            first_break = {'step': steps, 'food': eaten, 'choice': choice,
                           'opt': crit[choice]}
        snake, died, ate = step_snake(snake, food, choice)
        if died:
            cause = 'wall/body'; break
        if ate:
            eaten += 1; since_food = 0
            if arm != 'timer_sticky': rescue = False
            food = place_food(rng, snake)
            if food is None: cause = 'WIN 通关'; break
        else:
            since_food += 1
        if steps % 300 == 0:
            print('  %s seed%d eaten %d len %d step %d obey%% %.2f rescue_on=%d rescue_steps=%d' %
                  (arm, seed, eaten, len(snake), steps, 100.0 * n_obey / max(n_step, 1),
                   n_rescue_on, rescue_steps), flush=True)
    return {'seed': seed, 'arm': arm, 'food': eaten, 'cause': cause, 'steps': steps,
            'obey_rate': round(n_obey / max(n_step, 1), 3), 'first_rule_break': first_break,
            'rescue_activations': n_rescue_on, 'rescue_steps': rescue_steps,
            'auto_rate': round(auto_steps / max(n_step, 1), 3)}

if __name__ == '__main__':
    arm = sys.argv[1] if len(sys.argv) > 1 else 'formula'
    seeds = [int(s) for s in (sys.argv[2].split(',') if len(sys.argv) > 2 else ['1000', '1001', '1002'])]
    T = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    out = [play(s, arm, T) for s in seeds]
    fn = '_prompt_formula_%s%s.json' % (arm, '' if MODEL=='cycle' else '_'+MODEL)
    json.dump(out, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in out:
        print('FINAL %s seed %d food %d %s steps %d obey%% %.1f auto%% %.1f rescue x%d first_break %s' %
              (r['arm'], r['seed'], r['food'], r['cause'], r['steps'],
               100 * r['obey_rate'], 100 * r.get('auto_rate', 0), r.get('rescue_activations', 0),
               r['first_rule_break']), flush=True)
