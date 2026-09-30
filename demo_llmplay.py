# -*- coding: utf-8 -*-
"""模型选手对局引擎：棋盘按「契约选项」格式上报给模型（与 laya_bridge.py INSTRUCTIONS 同口径），
模型回复 UP/DOWN/LEFT/RIGHT，引擎记录完整轨迹 + 每步决策到达时间（= 模型响应速度）。"""
import json, sys, time
ST = 'laya-demo-llmplay-state.json'
GW = GH = 12
DIRS = {'UP': (0,-1), 'DOWN': (0,1), 'LEFT': (-1,0), 'RIGHT': (1,0)}
KN = ['UP','DOWN','LEFT','RIGHT']

def mulberry32(seed):
    a = {'v': seed}
    def f():
        a['v'] = (a['v'] + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a['v'] ^ (a['v'] >> 15)) * (1 | (a['v'] ^ (a['v'] >> 15)))) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | (t ^ (t >> 7)))) & 0xFFFFFFFF) ^ (t ^ (t >> 14))
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return f

def load():
    with open(ST, encoding='utf-8') as f: return json.load(f)
def save(s):
    with open(ST, 'w', encoding='utf-8') as f: json.dump(s, f, ensure_ascii=False)

def flood(head, blocked):
    b = set(blocked); seen = {head}; stack = [head]; n = 0
    while stack:
        x, y = stack.pop(); n += 1
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            p = (x+dx, y+dy)
            if 0 <= p[0] < GW and 0 <= p[1] < GH and p not in b and p not in seen:
                seen.add(p); stack.append(p)
    return n

def danger_of(cell, blocked):
    x, y = cell; c = 0
    for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
        p = (x+dx, y+dy)
        if not (0 <= p[0] < GW and 0 <= p[1] < GH) or p in blocked: c += 1
    return c

def view(s):
    """按契约格式上报：12 行字符串盘面 + 每方向选项事实（与模型训练时看到的一致）"""
    snake, food = [tuple(p) for p in s['snake']], tuple(s['food'])
    g = [['0']*GW for _ in range(GH)]
    for x, y in snake[1:]: g[y][x] = '1'
    g[food[1]][food[0]] = '3'
    g[snake[0][1]][snake[0][0]] = '2'
    opts = {}
    hx, hy = snake[0]
    for d in KN:
        dx, dy = DIRS[d]; nx, ny = hx+dx, hy+dy
        if not (0 <= nx < GW and 0 <= ny < GH) or (nx,ny) in snake[1:]:
            opts[d] = 'BLOCKED'
        else:
            land = (nx,ny) == food
            blocked = set(snake[1:]) if not land else set(snake[1:])  # 不吃时尾巴将移动，保守按不动算
            ns = [(nx,ny)] + snake
            if not land: ns = ns[:-1]
            sp = flood((nx,ny), ns[1:])
            opts[d] = f"fd={abs(nx-food[0])+abs(ny-food[1])} sp={sp} dg={danger_of((nx,ny), set(snake[1:]))}"
    return {'board': [''.join(r) for r in g], 'head': [hx,hy], 'food': [food[0],food[1]],
            'opts': opts, 'len': len(snake)}

def init():
    rng = mulberry32(20260929)
    perm = [(x,y) for y in range(GH) for x in range(GW)]
    for i in range(len(perm)-1, 0, -1):
        j = int(rng()*(i+1)); perm[i], perm[j] = perm[j], perm[i]
    s = {'snake': [[6,6],[5,6],[4,6]], 'perm': perm, 'ptr': 0, 'steps': 0, 'score': 0,
         'alive': True, 'cause': None, 't0': time.time(), 'last_arrive': None, 'log': []}
    s['food'] = list(s['perm'][0]); s['ptr'] = 1
    save(s); print_step(s, first=True)

def print_step(s, first=False, extra=''):
    v = view(s)
    print(f"STEP {s['steps']} | 吃 {s['score']} | 长 {v['len']} | {'开局' if first else '存活'}")
    print('\n'.join(v['board']))
    for d in KN: print(f"  {d:5s} {v['opts'][d]}")
    print(f"食物在 {v['food']}，头在 {v['head']}")
    if extra: print(extra)

def decide(direction):
    if direction not in KN: print('无效指令'); return
    s = load()
    if not s['alive']: print('对局已结束'); return
    now = time.time()
    latency = None if s['last_arrive'] is None else now - s['last_arrive']
    s['last_arrive'] = now
    snake, food = [tuple(p) for p in s['snake']], tuple(s['food'])
    v = view(s)
    record = {'step': s['steps']+1, 'head': list(v['head']), 'food': list(v['food']),
              'board': v['board'], 'opts': dict(v['opts']), 'choice': direction,
              'latency_s': round(latency, 3) if latency is not None else None,
              'elapsed_s': round(now - s['t0'], 2)}
    hx, hy = snake[0]; dx, dy = DIRS[direction]; nx, ny = hx+dx, hy+dy
    eat = (nx,ny) == food
    body = snake if eat else snake[:-1]
    dead = not (0 <= nx < GW and 0 <= ny < GH) or (nx,ny) in body
    if dead:
        s['alive'] = False
        s['cause'] = f'第{s["steps"]+1}步撞向 {direction}：{"墙" if not (0<=nx<GW and 0<=ny<GH) else "自己身体"}'
        record.update({'ate': False, 'dead': True, 'snake': [list(p) for p in snake]})
    else:
        ns = [(nx,ny)] + snake
        if eat: s['score'] += 1
        else: ns = ns[:-1]
        s['snake'] = [list(p) for p in ns]; s['steps'] += 1
        record.update({'ate': eat, 'dead': False, 'snake': [list(p) for p in ns],
                       'len': len(ns), 'score': s['score']})
        while s['ptr'] < len(s['perm']) and tuple(s['perm'][s['ptr']]) in set(map(tuple, s['snake'])):
            s['ptr'] += 1
        s['food'] = list(s['perm'][s['ptr']]) if s['ptr'] < len(s['perm']) else None
    s['log'].append(record)
    save(s)
    print(f"记录：第 {record['step']} 步选择 {direction}，决策间隔 "
          f"{('—' if latency is None else f'{latency*1000:.0f} ms')}")
    if dead:
        print_final(s)
    else:
        print_step(s, extra=f"→ 吃到食物！下一条在 {s['food']}" if record['ate'] else '')

def stop():
    s = load()
    s['alive'] = False; s['cause'] = '主动收兵（demo 结束）'
    s['log'].append({'step': s['steps']+1, 'stop': True, 'head': s['snake'][0],
                     'snake': s['snake'], 'latency_s': None, 'elapsed_s': round(time.time()-s['t0'],2)})
    save(s); print_final(s)

def print_final(s):
    lat = [r['latency_s'] for r in s['log'] if r.get('latency_s') is not None]
    lat.sort()
    med = lat[len(lat)//2] if lat else 0
    tot = time.time() - s['t0']
    n = s['steps']
    print('='*56)
    print(f"终局：吃 {s['score']} 食物 · {n} 步 · 最长身长 {max((r.get('len',3) for r in s['log']), default=3)}")
    print(f"结局：{s['cause']}")
    print(f"总耗时 {tot:.1f}s · 平均每步 {tot/max(n,1):.2f}s · 决策间隔中位 {med*1000:.0f} ms")
    print('='*56)

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'
    if cmd == 'init': init()
    elif cmd == 'decide' and len(sys.argv) > 2: decide(sys.argv[2].upper())
    elif cmd == 'stop': stop()
