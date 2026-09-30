# -*- coding: utf-8 -*-
# 决策位换成我：输入契约与 Laya 零掩码道(hintJumpOnly)逐字节相同（同一提示词文本、state、四选项 criteria、jumpCount），
# 无掩码、无 BLOCKED。时限由 argv[1] 给秒数，0/负数=不限时；犯规和死亡真实结算。
# 协议：队列耗尽→写 _ledger_ask.json（含完整 payload），轮询等我写 _ledger_answer.json {"askId":N,"dirs":[...]}。
import json, os, sys, time
from _rlcd_cycle import GW, GH, DIRS, ORDER, compact, step_snake
from _prompt_to_win import loop_safe
from _me_vs_laya import SEED, perm_stream, make_assign, js_mulberry32
import _prompt_formula as PF

LIMIT = float(sys.argv[1]) if len(sys.argv) > 1 else 600
if LIMIT <= 0: LIMIT = 1e9
MODE = sys.argv[2] if len(sys.argv) > 2 else 'single'   # single=单趟预洗牌(占位作废) free=剧院同款空格随机
ASK = '_ledger_ask.json'; ANS = '_ledger_answer.json'
RES = '_me_ledger_result.json'; LOGF = '_me_ledger_log.json'
SEG = '_me_ledger_segments.json'

def make_free_assign(rng_ref, snake_ref):
    """剧院/io 页 placeRandom 的逐位移植：行优先枚举空格，int(rng()*len) 取一。"""
    def assign():
        occ = {tuple(p) for p in snake_ref[0]}
        free = [(x, y) for y in range(GH) for x in range(GW) if (x, y) not in occ]
        if not free:
            return None
        return free[int(rng_ref[0]() * len(free))]
    return assign

def build_payload(snake, food, n_jump):
    st = PF.state_of(snake, food)
    st['jumpCount'] = n_jump
    crit = {d: compact(snake, food, d) for d in ORDER}
    return {'instructions': PF.INSTR['hintJumpOnly'], 'state': st, 'criteria': crit}

def main():
    t0 = time.time()
    snake = [(6, 6), (5, 6), (4, 6)]
    ref = [snake]; pp = [0]
    if MODE == 'free':
        rng = [js_mulberry32(SEED)]
        assign = make_free_assign(rng, ref)
    else:
        perm = perm_stream(SEED)
        assign = make_assign(ref, perm, pp)
    food = assign()
    score = 0; n_jump = 0; steps = 0; cause = '到点'; log = []; segs = []
    ask_id = 0; queue = []
    while True:
        if not queue:
            if time.time() - t0 > LIMIT: break
            ask_id += 1
            payload = build_payload(snake, food, n_jump)
            json.dump({'askId': ask_id, 'mode': MODE, 'stepsDone': steps, 'score': score, 'jumpCount': n_jump,
                       'pp': pp[0], 'rngDraws': (score + 1) if MODE == 'free' else 0,
                       'elapsed': round(time.time() - t0),
                       'remaining': round(LIMIT - (time.time() - t0)),
                       'snake': [list(p) for p in snake], 'food': list(food),
                       'payload': payload},
                      open(ASK, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            got = False
            while True:
                if time.time() - t0 > LIMIT:
                    cause = '10分钟到点(等待决策中)'; break
                if os.path.exists(ANS):
                    try:
                        a = json.load(open(ANS, encoding='utf-8'))
                    except Exception:
                        time.sleep(0.2); continue
                    if a.get('askId') == ask_id and isinstance(a.get('dirs'), list) and a['dirs']:
                        queue = [d for d in a['dirs'] if d in DIRS]; got = bool(queue)
                        segs.append({'askId': ask_id, 'stepsAtAsk': steps, 'score': score,
                                     'jumpCount': n_jump, 'dirs': queue})
                        json.dump(segs, open(SEG, 'w', encoding='utf-8'), ensure_ascii=False)
                        break
                time.sleep(0.15)
            if not got: break
        d = queue.pop(0)
        if not loop_safe(snake, food, d): n_jump += 1
        snake, died, ate = step_snake(snake, food, d)
        ref[0] = snake; steps += 1
        log.append({'step': steps, 'dir': d, 'ate': bool(ate), 'jump': n_jump})
        if died: cause = '撞墙撞身'; break
        if ate:
            score += 1
            json.dump(log, open(LOGF, 'w', encoding='utf-8'))
            food = assign()
            if food is None:
                cause = 'WIN 全盘吃满' if MODE == 'free' else 'WIN 食流耗尽(单趟口径)'; break
        if time.time() - t0 > LIMIT: cause = '10分钟到点'; break
    out = {'decider': '我(零掩码同契约)', 'mode': MODE, 'seed': SEED, 'food': score, 'steps': steps,
           'cause': cause, 'jumps': n_jump, 'pp': pp[0], 'elapsed': round(time.time() - t0)}
    json.dump(out, open(RES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(log, open(LOGF, 'w', encoding='utf-8'))
    print('FINAL', out)

if __name__ == '__main__':
    main()
