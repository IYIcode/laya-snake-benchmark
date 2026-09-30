# -*- coding: utf-8 -*-
"""还原模型每步真正看到的完整输入（用 laya 库自身的拼装函数解码 token）。"""
import re, json, torch
from laya import Agent
src = open('laya-snake-raw.html', encoding='utf-8').read()
rules = re.search(r'const RULES="(.*?)";', src).group(1)
opts = {"UP": "move one cell up (row-1)", "DOWN": "move one cell down (row+1)",
        "LEFT": "move one cell left (col-1)", "RIGHT": "move one cell right (col+1)"}
rows = [['0']*12 for _ in range(12)]
rows[6][2] = '2'; rows[6][1] = '1'; rows[6][0] = '1'; rows[5][9] = '3'
state = {"game": "snake", "board": "12x12", "grid": ["".join(r) for r in rows]}
q = {"action": {"type": "choice", "instructions": rules, "criteria": opts}}
agent = Agent("convaiinnovations/laya", device="cpu")
from laya.agent import build_sequence
seq = build_sequence(agent.tok, state, q, 512, 192)
ids = seq["input_ids"]
text = agent.tok.decode(ids, skip_special_tokens=False)
open("_model_input.txt", "w", encoding="utf-8").write(text)
print("tokens =", len(ids), "| chars =", len(text), "->  _model_input.txt")
