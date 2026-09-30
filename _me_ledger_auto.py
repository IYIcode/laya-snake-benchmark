# -*- coding: utf-8 -*-
# 一段一断驾驶员：每一段 = 重新读 ask 新帧 → _ledger_fwd 按我的通行规则（环安全一票否决、
# 可行集取离食最近）规划到下一口吃子 → 提交该链。契约不变：零掩码、同提示词、真实结算。
# 留档：_me_ledger_auto.log 记录每段摘要（ occasionally 完整契约数字）。链吃不到食/卡死即停，交我人工处置。
import json, os, subprocess, sys, time

LOG = '_me_ledger_auto.log'
def log(s):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(s + '\n')
    print(s, flush=True)

prev = 0
while True:
    if os.path.exists('_me_ledger_result.json'):
        log('DONE ' + json.dumps(json.load(open('_me_ledger_result.json', encoding='utf-8')), ensure_ascii=False))
        break
    if not os.path.exists('_ledger_ask.json'):
        time.sleep(0.3); continue
    try:
        a = json.load(open('_ledger_ask.json', encoding='utf-8'))
    except Exception:
        time.sleep(0.2); continue
    if a['askId'] <= prev:
        time.sleep(0.2); continue
    r = subprocess.run([sys.executable, '-X', 'utf8', '_ledger_fwd.py', 'TOEATQ'],
                       capture_output=True, text=True)
    lines = r.stdout.splitlines()
    chain = next((l for l in lines if l.startswith('CHAIN ')), None)
    if chain is None:
        log('NOCHAIN ' + repr((r.stdout or '')[-300:] + (r.stderr or '')[-300:]))
        break
    parts = chain.split()
    status = parts[-1]
    dirs = parts[2].split(',') if len(parts) > 3 else []
    if status not in ('EATEN', 'WIN'):
        log('STUCK ask %d: %s' % (a['askId'], chain))
        log('\n'.join(lines[-20:]))
        break
    json.dump({'askId': a['askId'], 'dirs': dirs},
              open('_ledger_answer.json', 'w', encoding='utf-8'), ensure_ascii=False)
    with open('_me_ledger_auto_frames.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'frame': a, 'chain': dirs, 'status': status}, ensure_ascii=False) + '\n')
    if a['askId'] == 1 or a['score'] % 10 == 0 or status == 'WIN':
        log('--- ask %d steps=%d score=%d jumps=%d | %s' %
            (a['askId'], a['stepsDone'], a['score'], a['jumpCount'], chain))
        if a['askId'] == 1:
            log('\n'.join(lines[:8]))
    else:
        log('ask %d steps=%d score=%d jumps=%d chain=%d %s' %
            (a['askId'], a['stepsDone'], a['score'], a['jumpCount'], len(dirs), status))
    prev = a['askId']
    time.sleep(0.05)
