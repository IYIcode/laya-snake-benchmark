# -*- coding: utf-8 -*-
"""P1(坐标选项)下模型真正看到的序列, 检查截断; 顺带对比 P0"""
import re
from laya import Agent
from laya.agent import build_sequence
import _opt_eval as E

agent = Agent("convaiinnovations/laya", device="cpu")
snake=[(6,6),(5,6),(4,6)]; food=(6,9)
state={'game':'snake','board':'12x12','grid':E.grid_rows(snake,food)}
p1={d: E.p1_text(snake,food,d) for d in ['UP','DOWN','LEFT','RIGHT']}

for tag, crit in [("P1坐标", p1), ("P0中性", E.P0)]:
    q = agent._to_internal({"type":"choice","instructions":E.RULES,"criteria":crit})
    seq, markers = build_sequence(agent.tok, state, q, 512, 192)
    text = agent.tok.decode(seq, skip_special_tokens=False)
    print(f"== {tag} == tokens={len(seq)} markers={markers}")
    for d,t in crit.items():
        ok = '在场完整' if t in text else '!!被截/变形!!'
        print(f"  {d:5s} {ok}")
    if tag=="P1坐标":
        open('_dbg_p1_seq.txt','w',encoding='utf-8').write(text)
print("---- P1 完整序列存 _dbg_p1_seq.txt, 末200字: ----")
print(text[-200:])
