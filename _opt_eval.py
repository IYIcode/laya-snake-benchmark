# -*- coding: utf-8 -*-
# 对照实验: P0=静态中性选项(现状)  vs  P1=坐标+接近+落点性质(用户方案)
import json, urllib.request, random, re, sys

RULES = re.search(r'const RULES="(.*?)";', open('laya-snake-raw.html', encoding='utf-8').read()).group(1)
GW, GH, STEPS = 12, 12, 220
DIRS = {'UP': (0,-1), 'DOWN': (0,1), 'LEFT': (-1,0), 'RIGHT': (1,0)}

def grid_rows(snake, food):
    g = [['0']*GW for _ in range(GH)]
    for i,(x,y) in enumerate(snake): g[y][x] = '2' if i==0 else '1'
    g[food[1]][food[0]] = '3'
    return [''.join(r) for r in g]

def place_food(rng, snake):
    occ = set(snake)
    free = [(x,y) for x in range(GW) for y in range(GH) if (x,y) not in occ]
    return rng.choice(free) if free else None

P0 = {d: f'move one cell {d.lower()} (row{"+1" if d=="DOWN" else "-1" if d=="UP" else ""}{"" if d in "UD" else ",col"+("-1" if d=="LEFT" else "+1")})' for d in DIRS}
P0 = {'UP':'move one cell up (row-1)','DOWN':'move one cell down (row+1)','LEFT':'move one cell left (col-1)','RIGHT':'move one cell right (col+1)'}

def p1_text(snake, food, d):
    hx,hy = snake[0]; dx,dy = DIRS[d]; nx,ny = hx+dx, hy+dy
    if not (0<=nx<GW and 0<=ny<GH): land = 'wall'
    elif (nx,ny) in snake[:-1] or ((nx,ny)==snake[-1] and (nx,ny)==food): land = 'body'
    elif (nx,ny)==snake[-1]: land = 'vacating'
    else: land = 'empty'
    d_now = abs(hx-food[0])+abs(hy-food[1])
    d_new = abs(nx-food[0])+abs(ny-food[1])
    near = 'closer to food' if d_new<d_now else ('farther from food' if d_new>d_now else 'same distance from food')
    return f'head moves to ({ny},{nx}), {land} there, {near}'

def decide(model, snake, food, criteria):
    req = {'model': model, 'state': {'game':'snake','board':'12x12','grid':grid_rows(snake,food)},
           'instructions': RULES, 'criteria': criteria}
    r = urllib.request.Request('http://127.0.0.1:8890/decide', json.dumps(req).encode(), {'Content-Type':'application/json'})
    j = json.load(urllib.request.urlopen(r))
    return j['probabilities'], j['choice']

def play(model, arm, seed):
    rng = random.Random(seed)
    snake = [(6,6),(5,6),(4,6)]; food = place_food(rng, snake); eaten = 0; cause = 'timeout'
    for step in range(STEPS):
        crit = P0 if arm=='P0' else {d: p1_text(snake,food,d) for d in DIRS}
        try: probs, choice = decide(model, snake, food, crit)
        except Exception as e: cause = f'http {e}'; break
        dx,dy = DIRS[choice]; nx,ny = snake[0][0]+dx, snake[0][1]+dy
        eat = (nx,ny)==food
        body = snake if eat else snake[:-1]
        if not (0<=nx<GW and 0<=ny<GH): cause='wall'; break
        if (nx,ny) in body: cause='body'; break
        snake.insert(0,(nx,ny))
        if eat: eaten+=1; food=place_food(rng,snake)
        else: snake.pop()
    return eaten, cause, step

if __name__ == '__main__':
    for arm in ['P0','P1']:
        res = [play('laya', arm, 1000+i) for i in range(8)]
        tot = sum(r[0] for r in res)
        print(arm, '每局食物:', [r[0] for r in res], '均值 %.1f' % (tot/8), '| 死因:', [r[1] for r in res])
