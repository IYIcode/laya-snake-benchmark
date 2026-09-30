# -*- coding: utf-8 -*-
# 同种子 20260929、同食物序列(mulberry32+PERM, 与 JS 引擎逐位一致)、同 400 步上限的选手对比。
#   laya   : cycle 模型 + 纯提示词 jumpCount 配方(hintJumpOnly, 零掩码), 决策走 8890 桥
#   patrol : 程序化环巡检(恒选环安全且离食最近) —— 规则上限参照
#   qoder  : 读 _me_game2.json(真人逐手回放日志)按手重放, 用于核对食物流一致
import json, os, sys, urllib.request
from _rlcd_cycle import GW, GH, DIRS, ORDER, cidx, compact, state_of, step_snake
from _prompt_to_win import loop_safe
import _prompt_formula as PF

SEED = 20260929
CAP = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 400
ARM = sys.argv[1] if len(sys.argv) > 1 else 'laya'

def js_mulberry32(seed):
    state = [seed & 0xFFFFFFFF]
    def rng():
        s = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        state[0] = s
        t = ((s ^ (s >> 15)) * (1 | s)) & 0xFFFFFFFF
        im = ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF
        t2 = ((t + im) & 0xFFFFFFFF) ^ t
        return ((t2 ^ (t2 >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rng

def perm_stream(seed):
    rng = js_mulberry32(seed)
    cells = [(x, y) for y in range(GH) for x in range(GW)]
    for i in range(len(cells) - 1, 0, -1):
        j = int(rng() * (i + 1))
        cells[i], cells[j] = cells[j], cells[i]
    return cells

def make_assign(snake_ref, perm, pp_ref):
    def assign():
        occ = {tuple(p) for p in snake_ref[0]}
        while pp_ref[0] < len(perm) and tuple(perm[pp_ref[0]]) in occ:
            pp_ref[0] += 1
        if pp_ref[0] >= len(perm):
            return None
        pp_ref[0] += 1
        return perm[pp_ref[0] - 1]
    return assign

def flood_free(head, body_set):
    seen = {tuple(head)}; st = [list(head)]; n = 0
    while st:
        x, y = st.pop(); n += 1
        for k in ORDER:
            p, q = x + DIRS[k][0], y + DIRS[k][1]
            if 0 <= p < GW and 0 <= q < GH and (p, q) not in seen and (p, q) not in body_set:
                seen.add((p, q)); st.append([p, q])
    return n

def run(arm):
    perm = perm_stream(SEED)
    snake = [(6, 6), (5, 6), (4, 6)]
    snake_ref = [snake]
    pp = [0]
    assign = make_assign(snake_ref, perm, pp)
    food = assign()
    score = 0; steps = 0; n_jump = 0; cause = '封顶%d' % CAP
    my_moves = None
    if arm == 'qoder':
        my_moves = json.load(open('_me_game2.json', encoding='utf-8'))['moves']
    log = []
    for steps in range(CAP):
        if arm == 'laya':
            st = PF.state_of(snake, food)
            st['jumpCount'] = n_jump
            crit = {d: compact(snake, food, d) for d in ORDER}
            resp = PF.decide(st, crit, 'hintJumpOnly')
            choice = resp['choice']
        elif arm == 'patrol':
            best = None
            for d in ORDER:
                if not loop_safe(snake, food, d):
                    continue
                nx, ny = snake[0][0] + DIRS[d][0], snake[0][1] + DIRS[d][1]
                cd = abs(nx - food[0]) + abs(ny - food[1])
                if best is None or cd < best[1]:
                    best = (d, cd)
            choice = best[0] if best else next(iter([d for d in ORDER
                     if land_free(snake, food, d)]), ORDER[0])
        elif arm == 'qoder':
            rec = next((m for m in my_moves if m['step'] == steps + 1), None)
            if rec is None:
                cause = '我的对局已结束'
                steps = my_moves[-1]['step'] - 1
                break
            choice = rec['dir']
        if not loop_safe(snake, food, choice):
            n_jump += 1
        snake, died, ate = step_snake(snake, food, choice)
        snake_ref[0] = snake
        log.append({'step': steps + 1, 'dir': choice, 'food': list(food), 'ate': bool(ate), 'jump': n_jump})
        if died:
            cause = '撞墙撞身'; break
        if ate:
            score += 1
            food = assign()
            if food is None:
                cause = 'WIN 吃满'; break
    return {'arm': arm, 'seed': SEED, 'food': score, 'steps': steps, 'cause': cause,
            'jumps': n_jump, 'pp': pp[0]}

def land_free(snake, food, d):
    nx, ny = snake[0][0] + DIRS[d][0], snake[0][1] + DIRS[d][1]
    return land_of2(nx, ny, snake, food) not in ('wall', 'body')

def land_of2(nx, ny, snake, food):
    from _rlcd_cycle import land_of
    return land_of(nx, ny, snake, food)

if __name__ == '__main__':
    out = run(ARM)
    fn = '_me_vs_laya_%s.json' % ARM
    json.dump(out, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('FINAL', out)
