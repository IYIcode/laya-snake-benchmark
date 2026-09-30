# -*- coding: utf-8 -*-
"""对 _port_check_out.json 的状态算 Python 版 fdpen6 判据字符串，供与页面 JS 逐字比对。"""
import json
from _port_check import is_safe, flood, flood2, GW, GH

DIRS = [{'x': 0, 'y': -1, 'n': 'UP'}, {'x': 0, 'y': 1, 'n': 'DOWN'},
        {'x': -1, 'y': 0, 'n': 'LEFT'}, {'x': 1, 'y': 0, 'n': 'RIGHT'}]

states = json.load(open('_port_check_out.json', encoding='utf-8'))
out = []
for e in states:
    snake, food, facing = e['snake'], e['food'], e['dir']
    walls = snake[:-1]
    ln = len(snake)
    pk = ln + 2
    crit = {}
    for d in DIRS:
        nx, ny = snake[0][0] + d['x'], snake[0][1] + d['y']
        rev = (d['x'] == -facing['x'] and d['y'] == -facing['y'])
        if not (is_safe(nx, ny, walls) and not rev):
            crit[d['n']] = ('BLOCKED: reverses into the snake neck; foodDist=0 space=0 danger=4'
                            if rev else 'BLOCKED: hits wall or body; foodDist=0 space=0 danger=4')
            continue
        fd = abs(nx - food[0]) + abs(ny - food[1])
        run = 0
        rx, ry = nx, ny
        while is_safe(rx, ry, walls):
            run += 1
            rx += d['x']
            ry += d['y']
        sp2 = flood2(snake[0], snake, d['x'], d['y'])
        pocket = sp2 < pk
        dd = min(4, max(0, 4 - run) + (2 if pocket else 0))
        if not pocket and fd == 0:
            dd = min(dd, 1)
        fdv = fd + 15 if (pocket and fd > 0) else fd
        crit[d['n']] = f"foodDist={fdv} space={sp2} danger={dd}"
    out.append({'len': ln, 'food': food, 'dir': facing, 'crit': crit})
print(json.dumps(out, ensure_ascii=False, indent=1))
