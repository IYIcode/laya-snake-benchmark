# -*- coding: utf-8 -*-
# 导出「我」的一段一断通关局重放数据：逐手方向 + 每段读帧载荷，并在 Python 端整局重放校验
# （复现 result 的 food/steps/0跨身/cause，且每段吃子后新食物 == 下一帧 ask 里 food，才落盘）。
# 支持两种口径：single=单趟预洗牌（占位作废）；free=剧院同款空格随机（真·填满 144 格）。
import json
from _rlcd_cycle import GW, GH, DIRS, compact, step_snake
from _prompt_to_win import loop_safe
from _me_vs_laya import SEED, perm_stream, make_assign, js_mulberry32

MODE = json.load(open('_me_ledger_result.json', encoding='utf-8')).get('mode', 'single')
frames = [json.loads(l)['frame'] for l in open('_me_ledger_auto_frames.jsonl', encoding='utf-8')]
chains = [json.loads(l)['chain'] for l in open('_me_ledger_auto_frames.jsonl', encoding='utf-8')]
dirs = [e['dir'] for e in json.load(open('_me_ledger_log.json', encoding='utf-8'))]
res = json.load(open('_me_ledger_result.json', encoding='utf-8'))
assert len(frames) == len(chains) and len(dirs) == res['steps'], (len(frames), len(dirs), res)

snake = [(6, 6), (5, 6), (4, 6)]
ref = [snake]; pp = [0]
if MODE == 'free':
    rng = [js_mulberry32(SEED)]
    def assign():
        occ = {tuple(p) for p in ref[0]}
        free = [(x, y) for y in range(GH) for x in range(GW) if (x, y) not in occ]
        if not free:
            return None
        return free[int(rng[0]() * len(free))]
else:
    perm = perm_stream(SEED)
    assign = make_assign(ref, perm, pp)
food = assign()
score = 0; n_jump = 0; cause = '未完'; segs = []; di = 0
for i, (a, ch) in enumerate(zip(frames, chains)):
    assert [tuple(p) for p in a['snake']] == snake and tuple(a['food']) == food, i
    assert a['jumpCount'] == n_jump and a['score'] == score and a['stepsDone'] == di, i
    segs.append({'askId': a['askId'], 'stepsAtAsk': di, 'score': score, 'jumpCount': n_jump,
                 'food': list(food), 'head': list(a['snake'][0]), 'len': len(snake),
                 'loopAhead': a['payload']['state']['loopAhead'],
                 'criteria': a['payload']['criteria'], 'chain': ch})
    for d in ch:
        if not loop_safe(snake, food, d): n_jump += 1
        snake, died, ate = step_snake(snake, food, d)
        ref[0] = snake; di += 1
        assert DIRS[d] and not died
        if ate:
            score += 1
            food = assign()
            if food is None:
                cause = 'WIN 全盘吃满' if MODE == 'free' else 'WIN 食流耗尽(单趟口径)'; break
    if cause != '未完': break
assert di == len(dirs) and score == res['food'] and n_jump == 0 and cause == res['cause'], \
    (di, score, n_jump, cause, res)
out = {'mode': MODE, 'seed': SEED, 'board': [GW, GH], 'start': [[6, 6], [5, 6], [4, 6]],
       'dirs': dirs, 'segs': segs, 'result': res,
       'foods': [[s['food'][0], s['food'][1]] for s in segs]}
json.dump(out, open('_myrun_data.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('PARITY OK', MODE, res, 'segs', len(segs), 'bytes', len(json.dumps(out, ensure_ascii=False)))
