# -*- coding: utf-8 -*-
"""P1c: 短规则(不截断) + 紧凑坐标选项, 8局; 全部走桥接8890"""
import json, urllib.request, random
import _opt_eval as E

SHORT = ("Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. "
         "Row 0 top, row 11 bottom. UP=row-1, DOWN=row+1, LEFT=col-1, RIGHT=col+1. "
         "Pick the direction that moves the head toward the food without dying.")

def compact(snake, food, d):
    hx,hy=snake[0]; dx,dy=E.DIRS[d]; nx,ny=hx+dx,hy+dy
    land='wall' if not(0<=nx<12 and 0<=ny<12) else ('body' if (nx,ny) in snake[:-1] else 'free')
    dn=abs(nx-food[0])+abs(ny-food[1]); dc=abs(hx-food[0])+abs(hy-food[1])
    rel='NEARER to food' if dn<dc else ('FARTHER from food' if dn>dc else 'SAME distance')
    return f"({nx},{ny}) {land}, {rel}"

def play(arm, seed):
    rng=random.Random(seed); snake=[(6,6),(5,6),(4,6)]; food=E.place_food(rng,snake)
    eaten=0; cause='timeout'; wallstep=0
    for step in range(E.STEPS):
        crit = {d:f"move one cell {d.lower()}" for d in E.DIRS} if arm=='P0s' else {d:compact(snake,food,d) for d in E.DIRS}
        req={'model':'laya','state':{'game':'snake','board':'12x12','grid':E.grid_rows(snake,food)},
             'instructions':SHORT,'criteria':crit}
        r=urllib.request.Request('http://127.0.0.1:8890/decide',json.dumps(req).encode(),{'Content-Type':'application/json'})
        j=json.load(urllib.request.urlopen(r)); ch=j['choice']
        dx,dy=E.DIRS[ch]; nx,ny=snake[0][0]+dx,snake[0][1]+dy; eat=(nx,ny)==food
        body=snake if eat else snake[:-1]
        if not(0<=nx<12 and 0<=ny<12): cause,wallstep='wall',step; break
        if (nx,ny) in body: cause,wallstep='body',step; break
        snake.insert(0,(nx,ny))
        if eat: eaten+=1; food=E.place_food(rng,snake)
        else: snake.pop()
    return eaten,cause,wallstep

for arm in ['P0s','P1c']:
    res=[play(arm,1000+i) for i in range(8)]
    print(arm,'食物:',[r[0] for r in res],'均值 %.1f'%(sum(r[0] for r in res)/8),'| 死因@步:',[f"{r[1]}@{r[2]}" for r in res])
