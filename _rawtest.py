# -*- coding: utf-8 -*-
import json, urllib.request, re
rules = re.search(r'const RULES="(.*?)";', open('laya-snake-raw.html', encoding='utf-8').read()).group(1)
rows = [['0']*12 for _ in range(12)]
rows[6][2] = '2'; rows[6][1] = '1'; rows[6][0] = '1'; rows[5][9] = '3'
st = {'game': 'snake', 'board': '12x12', 'grid': [''.join(r) for r in rows]}
req = {'model': 'laya', 'state': st, 'instructions': rules,
       'criteria': {'UP': 'move one cell up (row-1)', 'DOWN': 'move one cell down (row+1)',
                    'LEFT': 'move one cell left (col-1)', 'RIGHT': 'move one cell right (col+1)'}}
r = urllib.request.Request('http://127.0.0.1:8890/decide', json.dumps(req).encode(),
                           {'Content-Type': 'application/json'})
j = json.load(urllib.request.urlopen(r))
print('choice =', j.get('choice'))
print('probs  =', {k: round(v, 3) for k, v in (j.get('probabilities') or {}).items()})
print('ms     =', j.get('ms'), '| error =', j.get('error'))
