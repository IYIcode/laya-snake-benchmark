# -*- coding: utf-8 -*-
# 把 _myrun_data.json 内嵌进重放页（幂等：标记块整体替换），使 file:// 双击打开也能跑。
import json, re

HTML = 'laya-snake-myrun.html'
data = json.load(open('_myrun_data.json', encoding='utf-8'))
block = ('<script id="embed-data">window.__MYRUN__='
         + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';</script>')
h = open(HTML, encoding='utf-8').read()
if '<script id="embed-data">' in h:
    h = re.sub(r'<script id="embed-data">.*?</script>', block, h, count=1, flags=re.S)
else:
    h = h.replace('<div id="stage">', block + '\n<div id="stage">', 1)
open(HTML, 'w', encoding='utf-8').write(h)
print('EMBED OK, html bytes', len(h.encode('utf-8')))
