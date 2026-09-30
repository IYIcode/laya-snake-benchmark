# -*- coding: utf-8 -*-
# 一手一看：等 askId >= 指定号，然后只打印契约内容（盘面文本、loopAhead三数、四选项cyc）+账本。
import json, sys, time, os
want = int(sys.argv[1])
a = None
for _ in range(900):
    if os.path.exists('_me_ledger_result.json'):
        print('DONE', open('_me_ledger_result.json', encoding='utf-8').read().replace('\n', ' '))
        sys.exit(0)
    a = json.load(open('_ledger_ask.json', encoding='utf-8'))
    if a['askId'] >= want:
        break
    time.sleep(0.1)
p = a['payload']; s = p['state']
print('ask %d | step %d | score %d | jumpCount %d | 剩余 %ds' % (a['askId'], a['stepsDone'], a['score'], a['jumpCount'], a['remaining']))
print('\n'.join(s['grid']))
la = s['loopAhead']
print('foodAhead=%s bodyAhead=%s bodyGoAhead=%s' % (la['foodAhead'], la['bodyAhead'], la['bodyGoAhead']))
for k, v in p['criteria'].items():
    print(k, v)
