# -*- coding: utf-8 -*-
"""三组实验: 1)短规则下P1跟随closer吗 2)模型有没有最小绑定能力 3)槽位结构对照"""
import numpy as np
from laya import Agent
from laya.agent import build_sequence
import _opt_eval as E

agent = Agent("convaiinnovations/laya", device="cpu")

SHORT = ("Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. "
         "Row 0 top, row 11 bottom. UP=row-1, DOWN=row+1, LEFT=col-1, RIGHT=col+1. "
         "Pick the option whose description best matches moving safely toward the food.")

def probs(state, instructions, crit):
    q = agent._to_internal({"type":"choice","instructions":instructions,"criteria":crit})
    seq, markers = build_sequence(agent.tok, state, q, 512, 192)
    assert len(markers)==4, "选项被截!"
    j = agent.system_one(state, {"action":{"type":"choice","instructions":instructions,"criteria":crit}})
    return j["answers"]["action"]["probabilities"]

snake=[(6,6),(5,6),(4,6)]
DIRS=['UP','DOWN','LEFT','RIGHT']

print("== 实验2: 最小绑定能力测试. 三个选项文字相同, 只有一个是 '@@ go to the food @@' ==")
for target in DIRS:
    crit={d:('@@ go to the food @@' if d==target else 'just a cell') for d in DIRS}
    st={'game':'snake','board':'12x12','grid':E.grid_rows(snake,(6,9))}
    p=probs(st, SHORT, crit)
    win=max(p,key=p.get)
    print(f"  标记放 {target:5s} -> 模型选 {win:5s} {'跟随' if win==target else '不跟'}  " + str({k:round(v,2) for k,v in p.items()}))

print()
print("== 实验1: 短规则+紧凑坐标选项, closer 跟随食物位置吗 ==")
def compact(snake,food,d):
    hx,hy=snake[0]; dx,dy=E.DIRS[d]; nx,ny=hx+dx,hy+dy
    land='wall' if not(0<=nx<12 and 0<=ny<12) else ('body' if (nx,ny) in snake[:-1] else 'free')
    dn=abs(nx-food[0])+abs(ny-food[1]); dc=abs(hx-food[0])+abs(hy-food[1])
    rel='NEARER' if dn<dc else ('FARTHER' if dn>dc else 'SAME')
    return f"({nx},{ny}) {land} {rel}"
for food in [(6,3),(6,9),(2,6),(9,6)]:
    crit={d:compact(snake,food,d) for d in DIRS}
    want=[d for d in DIRS if 'NEARER' in crit[d]][0]
    st={'game':'snake','board':'12x12','grid':E.grid_rows(snake,food)}
    p=probs(st, SHORT, crit)
    win=max(p,key=p.get)
    print(f"  食物{food} NEARER在{want} -> 模型选 {win} {'跟' if win==want else '不跟'}  " + str({k:round(v,2) for k,v in p.items()}))
