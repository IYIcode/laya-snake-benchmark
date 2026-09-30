# -*- coding: utf-8 -*-
# 前瞻核对器：从当前 ask 状态出发，沿我拟的方向序列逐步展开，打印每一步的契约数字
# （loopAhead 三数 + 每选项 cyc + 提示词里那条不等式是否成立 + 吃/死/犯规），供我提交队列前自查。
# 只算不裁决——方向和取舍全是我给的；这里没有任何掩码/BLOCKED。
import json, sys
from _rlcd_cycle import GW, GH, DIRS, ORDER, cidx, land_of, loop_ahead, compact, step_snake
from _prompt_to_win import loop_safe
from _me_vs_laya import SEED, perm_stream, make_assign, js_mulberry32

a = json.load(open('_ledger_ask.json', encoding='utf-8'))
snake = [tuple(p) for p in a['snake']]
food = tuple(a['food'])
n_jump = a['jumpCount']
step = a['stepsDone']
ref = [snake]
if a.get('mode') == 'free':
    # 剧院同款空格随机：重建 rng 流并空烧已消费的 score+1 次，保证与引擎逐位一致
    def free_assign():
        occ = {tuple(p) for p in ref[0]}
        free = [(x, y) for y in range(GH) for x in range(GW) if (x, y) not in occ]
        if not free:
            return None
        return free[int(_rng() * len(free))]
    _rng = js_mulberry32(SEED)
    for _ in range(a['score'] + 1):
        _rng()
    assign = free_assign
    pp = [0]
else:
    perm = perm_stream(SEED)
    pp = [a['pp']]
    assign = make_assign(ref, perm, pp)
    # 注意: ask 里 food 已被当前 pp 指向消费过，重放 assign 前先回退一格保持流一致
    pp[0] -= 1

def auto_pick(snake, food):
    """我公示过的通行策略：环安全不等式一票否决；可行集中取离食最近，
       平手取环上前进度(cyc)更大者（一手一断第24手公开修订的规则）。"""
    hd = cidx(snake[0][0], snake[0][1])
    cands = []
    for k in ORDER:
        nx = snake[0][0] + DIRS[k][0]; ny = snake[0][1] + DIRS[k][1]
        if land_of(nx, ny, snake, food) in ('wall', 'body'):
            continue
        cd = abs(nx - food[0]) + abs(ny - food[1])
        cyc = (cidx(nx, ny) - hd) % 144
        cands.append((k, cd, cyc, loop_safe(snake, food, k)))
    safe = [c for c in cands if c[3]]
    pool = safe if safe else cands
    return min(pool, key=lambda c: (c[1], -c[2]))[0]

arg = sys.argv[1] if len(sys.argv) > 1 else '20'
dirs = None
to_eat = arg.startswith('TOEAT')
quiet = arg == 'TOEATQ'
if to_eat:
    n_auto = 400   # 上限护栏：400 手还吃不到就报告失败
elif arg.isdigit():
    dirs = None
    n_auto = int(arg)
else:
    n_auto = 0
    dirs = list(sys.argv[1:])

eaten = False
chain = []
step = a['stepsDone']
while True:
    if dirs is not None:
        if not dirs: break
        d = dirs.pop(0)
    else:
        if n_auto <= 0: break
        n_auto -= 1
        d = auto_pick(snake, food)
    if d not in DIRS:
        print('BAD DIR', d); break
    df, m1, m2 = loop_ahead(snake, food)
    sf = loop_safe(snake, food, d)
    if not quiet or not chain or not sf:
        print('== step %d dir=%s head=(%d,%d) len=%d food=(%d,%d) | foodAhead=%d bodyAhead=%d bodyGoAhead=%d jumps=%d'
              % (step + 1, d, snake[0][0], snake[0][1], len(snake), food[0], food[1], df, m1, m2, n_jump))
        for k in ORDER:
            nx = snake[0][0] + DIRS[k][0]; ny = snake[0][1] + DIRS[k][1]
            mark = '<= 我选' if k == d else ''
            print('   %-5s %s | 不等式:%s%s' % (k, compact(snake, food, k),
                  'PASS' if loop_safe(snake, food, k) else 'FAIL(=跨身)', mark))
    if not sf: n_jump += 1
    snake, died, ate = step_snake(snake, food, d)
    ref[0] = snake; step += 1
    chain.append(d)
    if died:
        print('   >>> 撞死，对局结束 (step %d)' % step); break
    if ate:
        food = assign()
        if food is None:
            print('   >>> WIN 吃满 (step %d)' % step); eaten = True; break
        if to_eat:
            eaten = True
            print('   >>> 本链终点：此手吃子，新食物', list(food)); break
print('CHAIN %d %s %s' % (len(chain), ','.join(chain), 'EATEN' if eaten else ('WIN' if food is None else 'NOEAT')))
print('-- 计划尾部状态: steps=%d score=%d jumps=%d (未含本局早前账)' % (step, a['score'], n_jump))
