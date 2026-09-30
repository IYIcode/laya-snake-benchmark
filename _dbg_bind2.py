# -*- coding: utf-8 -*-
"""自然短语绑定测试: 只改一个选项的短语, 看概率动没动、动对没有"""
from laya import Agent
import _opt_eval as E

agent = Agent("convaiinnovations/laya", device="cpu")
SHORT = ("Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. "
         "Row 0 top, row 11 bottom. UP=row-1, DOWN=row+1, LEFT=col-1, RIGHT=col+1. "
         "Pick the direction that moves the head toward the food without dying.")
snake=[(6,6),(5,6),(4,6)]; food=(6,3)   # 食物在正上方3格
st={'game':'snake','board':'12x12','grid':E.grid_rows(snake,food)}

def run(tag, crit):
    j=agent.system_one(st,{"a":{"type":"choice","instructions":SHORT,"criteria":crit}})
    p=j["answers"]["a"]["probabilities"]; win=max(p,key=p.get)
    print(f"{tag:58s} -> {win:5s} " + str({k:round(v,2) for k,v in p.items()}))

base={d:f"move one cell {d.lower()}" for d in ['UP','DOWN','LEFT','RIGHT']}
run("T0 全中性(基准)", base)
for d in ['UP','DOWN','LEFT','RIGHT']:
    c=dict(base); c[d]=f"move one cell {d.lower()}, toward the food"
    run(f"T1 只有{d}带 'toward the food'", c)
for d in ['UP','DOWN','LEFT','RIGHT']:
    c=dict(base); c[d]=f"move one cell {d.lower()}, the wall is right there"
    run(f"T2 只有{d}带 'the wall is right there'", c)
for d in ['UP','DOWN','LEFT','RIGHT']:
    c=dict(base); c[d]=f"move one cell {d.lower()}, the food is right there"
    run(f"T3 只有{d}带 'the food is right there'", c)
