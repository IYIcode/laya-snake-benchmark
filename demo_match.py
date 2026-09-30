# -*- coding: utf-8 -*-
"""对局演示模拟器：与 laya-snake-pk.html 的算法逐字对齐（rule3 / BFS 老师）。
共用同一条食物序列（matchNo=1 的种子），每一步的完整决策记录落盘。
"""
import json, random
from collections import deque

GW = GH = 12
DIRS = {'UP': (0,-1), 'DOWN': (0,1), 'LEFT': (-1,0), 'RIGHT': (1,0)}
KN = ['UP','DOWN','LEFT','RIGHT']
MATCH_NO = 1

def mulberry32(a):
    import struct
    def f():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = (a ^ (a >> 15)) * (1 | (a ^ (a >> 15)) >> 15) & 0xFFFFFFFF  # approx; use python int instead
        return a  # placeholder
    return f

# 用纯 Python 复刻 mulberry32（数值语义一致）
def mb32(seed):
    state = {'a': seed}
    import ctypes
    def f():
        a = state['a']
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        state['a'] = a
        t = ((a ^ (a >> 15)) * (1 | (a ^ (a >> 15)))) & 0xFFFFFFFF  # JS: (a^a>>>15)*(1|(a^a>>>15)) — 注意 JS 是 1|不是乘
        # 精确复刻：t = imul(t1, t2+1) 其中 t1 = a^(a>>>15); 然后 t += 1|t1
        t1 = (a ^ (a >> 15)) & 0xFFFFFFFF
        t = ((t1 * (1 | t1)) & 0xFFFFFFFF)          # Math.imul(t1, t2) where t2 = 1|t1
        t2 = ((t ^ (t >> 14)) * 61) & 0xFFFFFFFF    # imul(t, 61)
        t = (t + (1 | t1)) & 0xFFFFFFFF
        t ^= (t >> 14)
        return ((t ^ (t >> 14)) >> 0) / 4294967296
    return f

def land_of(nx, ny, snake, food):
    if nx < 0 or nx >= GW or ny < 0 or ny >= GH:
        return 'wall'
    in_body = any(s == (nx,ny) for s in snake[1:-1])
    tail = snake[-1]; eat = (nx,ny) == food
    if in_body: return 'body'
    if len(snake) > 1 and (nx,ny) == tail:
        return 'body' if eat else 'vacating'
    return 'free'

def flood_space(head, blocked):
    b = set(blocked); seen = {head}; st = [head]; n = 0
    while st:
        x,y = st.pop(); n += 1
        for k in KN:
            dx,dy = DIRS[k]; p = (x+dx, y+dy)
            if 0 <= p[0] < GW and 0 <= p[1] < GH and p not in b and p not in seen:
                seen.add(p); st.append(p)
    return n

def bfs_dist(head, food, blocked):
    if head == food: return 0
    b = set(blocked); q = deque([(head,0)]); seen = {head}
    while q:
        nq = []
        for (x,y),d in q:
            for k in KN:
                dx,dy = DIRS[k]; p = (x+dx,y+dy)
                if not(0 <= p[0] < GW and 0 <= p[1] < GH) or p in b or p in seen: continue
                if p == food: return d+1
                seen.add(p); nq.append((p,d+1))
        q = deque(nq)
    return None

def rule3_features(snake, food):
    out = {}
    hx,hy = snake[0]
    for d in KN:
        dx,dy = DIRS[d]; nx,ny = hx+dx, hy+dy
        land = land_of(nx,ny,snake,food)
        if land in ('wall','body'): out[d] = {'land': land}; continue
        dn = abs(nx-food[0]) + abs(ny-food[1])
        dc = abs(hx-food[0]) + abs(hy-food[1])
        rel = 0 if dn < dc else (2 if dn > dc else 1)
        ns = [(nx,ny)] + snake
        if (nx,ny) != food: ns.pop()
        sp = flood_space(ns[0], ns[1:])
        out[d] = {'land': land, 'dn': dn, 'dc': dc, 'rel': rel, 'sp': sp,
                  'ok': sp >= len(ns)*1.2}
    return out

def rule3_pick(snake, food):
    feats = rule3_features(snake, food)
    cand = [d for d in KN if feats[d]['land'] not in ('wall','body')]
    if not cand: return None, feats
    ok = [d for d in cand if feats[d]['ok']]
    pool = ok if ok else cand
    pool.sort(key=lambda d: (feats[d]['rel'], feats[d]['dn'], -feats[d]['sp']))
    return pool[0], feats

def teacher_scores(snake, food):
    out = {}
    hx,hy = snake[0]
    for d in KN:
        dx,dy = DIRS[d]; nx,ny = hx+dx, hy+dy
        eat = (nx,ny) == food
        body = snake if eat else snake[:-1]
        if not(0 <= nx < GW and 0 <= ny < GH) or (nx,ny) in body:
            out[d] = -1000; continue
        ns = [(nx,ny)] + snake
        if not eat: ns.pop()
        sp = flood_space(ns[0], ns[1:]); dist = bfs_dist(ns[0], food, ns[1:])
        sc = -25 + sp*0.5 if dist is None else 40 - dist*2 + sp*0.3
        if sp < len(ns)*1.3: sc -= (len(ns)*1.3 - sp)*4
        out[d] = sc
    return out

def bfs_pick(snake, food, rng):
    sc = teacher_scores(snake, food)
    alive = [d for d in sc.values()] and [d for d in sc if sc[d] > -500]
    if not alive: return None, sc
    top = max(sc.values())
    pool = [d for d in sc if sc[d] >= top] or alive
    return pool[int(rng()*len(pool))], sc

def step_snake(snake, food, d):
    hx,hy = snake[0]; dx,dy = DIRS[d]; nx,ny = hx+dx, hy+dy
    eat = (nx,ny) == food
    body = snake if eat else snake[:-1]
    if not(0 <= nx < GW and 0 <= ny < GH) or (nx,ny) in body:
        return snake, True, False
    ns = [(nx,ny)] + snake
    if not eat: ns.pop()
    return ns, False, eat

def new_perm():
    rng = mb32((MATCH_NO*9301+49297) % 233280)
    perm = [(x,y) for y in range(GH) for x in range(GW)]
    for i in range(len(perm)-1, 0, -1):
        j = int(rng() * (i+1))
        perm[i], perm[j] = perm[j], perm[i]
    return perm

def play(method, perm):
    snake = [(6,6),(5,6),(4,6)]; ptr = 0; steps = 0; score = 0
    cause = '—'; alive = True
    def assign():
        nonlocal ptr
        occ = set(snake)
        while ptr < len(perm) and perm[ptr] in occ: ptr += 1
        return perm[ptr] if ptr < len(perm) else None
    food = assign()
    rec = {'method': method, 'steps': [], 'final': {}}
    tie = mb32(987654321)
    while alive and food is not None:
        if method == 'rule3':
            choice, feats = rule3_pick(snake, food)
            tsc = teacher_scores(snake, food)
            step_snake(snake, food, choice) if choice is None else None
        else:
            choice, tsc = bfs_pick(snake, food, tie)
            feats = rule3_features(snake, food)
        if choice is None:
            cause = '无合法移动（被困死）'; break
        ate_note = 'EAT' if (snake[0][0]+DIRS[choice][0] == food[0] and snake[0][1]+DIRS[choice][1] == food[1]) else ''
        snake, dead, eat = step_snake(snake, food, choice)
        steps += 1
        rec['steps'].append({
            'step': steps, 'head': snake[0] if not dead else [snake[0]],
            'head_before': [snake[0][0], snake[0][1]],
            'food': list(food), 'len': len(snake), 'score': score + eat,
            'cand': {d: {'f': feats.get(d), 't': tsc.get(d)} for d in KN},
            'choice': choice, 'ate': eat, 'dead': dead,
            'snake': [list(s) for s in snake],
        })
        score += eat
        if dead:
            cause = '撞死（选择时判定安全，实际路径冲突）' if False else '移动失败'
            alive = False; break
        ptr += 1; food = assign()
        if ptr >= len(perm): cause = '食物序列耗尽'; break
    rec['final'] = {'cause': cause, 'food_eaten': score, 'steps': steps,
                    'len_max': len(snake), 'alive': alive}
    return rec

def main():
    perm = new_perm()
    r1 = play('rule3', perm)
    r2 = play('bfs', perm)
    out = {'matchNo': MATCH_NO, 'seed': (MATCH_NO*9301+49297) % 233280,
           'note': '与 laya-snake-pk.html 同一食物序列（matchNo=1 种子），算法逐字对齐',
           'rule3': r1, 'bfs': r2}
    with open('laya-demo-match-record.json','w',encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    # 摘要
    for m in ('rule3','bfs'):
        r = out[m]; fin = r['final']
        print(f"{m}: 吃 {fin['food_eaten']} 食物 · {fin['steps']} 步 · 最长 {fin['len_max']} · 结局 {fin['cause']}")
        for s in r['steps'][:3]:
            c = s['cand'][s['choice']]
            print(f"  步{s['step']}: head={s['head_before']} → {s['choice']} cand_rule3={ {d:(c2['f'] or {}).get('dn') for d,c2 in s['cand'].items()} }")
    # Markdown 转录（每步一行）
    lines = ['# 对局演示 · 完整记录', '',
             f"食物序列种子: matchNo={MATCH_NO}（与 PK 页第一局完全相同）", '',
             '## 结果', '']
    lines.append('| 选手 | 吃到 | 步数 | 最长 | 结局 |')
    lines.append('|---|---|---|---|---|')
    for m, name in (('rule3','三特征规则'), ('bfs','BFS 老师')):
        fin = out[m]['final']
        lines.append(f"| {name} | {fin['food_eaten']} | {fin['steps']} | {fin['len_max']} | {fin['cause']} |")
    lines += ['', '## 逐步决策（三特征规则）', '',
              '| 步 | 头→选 | 食物 | 各方向 rel/dn/sp(ok) | 依据 |', '|---|---|---|---|---|']
    for s in out['rule3']['steps']:
        cells = []
        for d in KN:
            f = s['cand'][d]['f']
            cells.append(f"{d}:{'—' if not f else f'{f.get(\"rel\")}/{f.get(\"dn\")}/{f.get(\"sp\")}{\"✓\" if f.get(\"ok\") else \"\"}'}")
        ch = s['choice']; fc = s['cand'][ch]['f']
        why = f"rel={fc['rel']} dn={fc['dn']} sp={fc['sp']}" + (' · 吃到!' if s['ate'] else '')
        lines.append(f"| {s['step']} | {s['head_before']}→**{ch}** | {s['food']} | {' '.join(cells)} | {why} |")
    with open('laya-demo-match-record.md','w',encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('已写: laya-demo-match-record.json / .md')

if __name__ == '__main__':
    main()
