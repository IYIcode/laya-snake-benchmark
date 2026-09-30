# -*- coding: utf-8 -*-
# 目标：不训练，只改提示词（指令措辞 / 状态形态 / 选项文本 / 键顺序），
# 看零样本 base laya 能否吃食物、逼近通关。所有"合规"arm 只给棋盘事实，绝不下"该走哪/会死"结论。
# 另设 1 个"对照·非合规"arm：把贪心方向伪装成标签喂给模型，用来分离"模型在读棋盘" vs "模型只会说 UP"。
import json, urllib.request, random, re

RULES = re.search(r'const RULES="(.*?)";', open('laya-snake-raw.html', encoding='utf-8').read()).group(1)
GW, GH, STEPS, NG = 12, 12, 300, 6
DIRS = {'UP': (0, -1), 'DOWN': (0, 1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
KN = ['UP', 'DOWN', 'LEFT', 'RIGHT']

def grid_rows(snake, food):
    g = [['0'] * GW for _ in range(GH)]
    for i, (x, y) in enumerate(snake):
        g[y][x] = '2' if i == 0 else '1'
    g[food[1]][food[0]] = '3'
    return [''.join(r) for r in g]

def place_food(rng, snake):
    occ = set(snake)
    free = [(x, y) for x in range(GW) for y in range(GH) if (x, y) not in occ]
    return rng.choice(free) if free else None

def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def greedy_dir(snake, food):
    # 使离食物曼哈顿距离最小的可行方向（仅用于对照arm与诊断，不喂给模型）
    hx, hy = snake[0]
    best = min(KN, key=lambda d: md((hx + DIRS[d][0], hy + DIRS[d][1]), food))
    return best

# ── 各 arm 的 (instructions, state, criteria) 构造 ──
def arm_A(snake, food):
    hx, hy = snake[0]; fx, fy = food
    ins = (f"You are driving a snake on a 12x12 grid, row 0 at top, col 0 at left. "
           f"The head is at (row {hy}, col {hx}). The food is at (row {fy}, col {fx}). "
           f"Pick the single direction that moves the head ONTO the food cell.")
    crit = {d: d for d in KN}
    return ins, {'game': 'snake', 'board': '12x12', 'grid': grid_rows(snake, food)}, crit

def arm_C(snake, food):
    fx, fy = food
    ins = (f"You are driving a snake on a 12x12 grid, row 0 top, col 0 left. "
           f"The food is located at (row {fy}, col {fx}). Each option is the cell the head moves into; "
           f"choose the option whose cell is the food cell.")
    hx, hy = snake[0]
    crit = {}
    for d in KN:
        nx, ny = hx + DIRS[d][0], hy + DIRS[d][1]
        crit[d] = f"head moves into (row {ny}, col {nx})"
    return ins, {'game': 'snake', 'board': '12x12', 'grid': grid_rows(snake, food)}, crit

def arm_D(snake, food):
    # 自我中心：给朝向，选项用前/左/右/后
    hx, hy = snake[0]; fx, fy = food
    ins = (f"You control a snake. It currently faces {FACE}. "
           f"Reply which way to move: FORWARD keeps the current heading, BACK reverses it, "
           f"LEFT/RIGHT turn 90 degrees. The head is at (row {hy}, col {hx}); the food is at (row {fy}, col {fx}).")
    crit = {'FORWARD': 'continue straight ahead', 'LEFT': 'turn left', 'RIGHT': 'turn right', 'BACK': 'turn around'}
    return ins, {'game': 'snake', 'board': '12x12', 'grid': grid_rows(snake, food)}, crit

FACE = 'RIGHT'  # 开局固定朝右
def egocentric_to_board(turn, facing):
    order = ['UP', 'RIGHT', 'DOWN', 'LEFT']  # 顺时针
    i = order.index(facing)
    if turn == 'FORWARD': return order[i]
    if turn == 'RIGHT': return order[(i + 1) % 4]
    if turn == 'LEFT': return order[(i - 1) % 4]
    if turn == 'BACK': return order[(i + 2) % 4]
    return None

def arm_E_relabel(snake, food):
    # 对照·非合规：把"离食物更近"的方向永远标成 UP（其余方向随意占 DOWN/LEFT/RIGHT），
    # 再把模型选的 UP 翻译回那个贪心方向。等于把答案藏进键顺序里——用来说明"通关"其实是我们在替它决定。
    g = greedy_dir(snake, food)
    others = [d for d in KN if d != g]
    lab = {'UP': g, 'DOWN': others[0], 'LEFT': others[1], 'RIGHT': others[2]}
    ins = RULES
    crit = {d: f"move one cell {d.lower()}" for d in KN}
    return ins, {'game': 'snake', 'board': '12x12', 'grid': grid_rows(snake, food)}, crit, lab

def cell_kind(snake, food, nx, ny):
    if not (0 <= nx < GW and 0 <= ny < GH): return 'WALL'
    if (nx, ny) == food: return 'FOOD'
    if (nx, ny) in snake[:-1]: return 'BODY'
    if (nx, ny) == snake[-1]: return 'TAIL-LEAVING'
    return 'empty'

def arm_F(snake, food):
    # 数字坐标 state（模型读得懂的形态）+ 每选项落点性质事实；问题点名食物坐标与"安全踩上食物"目标。
    hx, hy = snake[0]; fx, fy = food
    ins = (f"Snake on 12x12, row 0 top, col 0 left. Head at row {hy} col {hx}. "
           f"Food at row {fy} col {fx}. Body cells are listed in the state. "
           f"Choose the one direction that steps the head onto the FOOD cell; do not step onto a WALL or BODY cell.")
    crit = {d: f"cell row {hy + DIRS[d][1]} col {hx + DIRS[d][0]} is {cell_kind(snake, food, hx + DIRS[d][0], hy + DIRS[d][1])}"
            for d in KN}
    return ins, {'game': 'snake', 'board': '12x12', 'head': [hx, hy], 'food': [fx, fy],
                 'body': [[x, y] for x, y in snake[1:]]}, crit

def arm_G(snake, food):
    # 同 F，但把 FOOD 那一格排到选项最前，测纯位置/显著性能否撬动（键仍是四方向）。
    hx, hy = snake[0]; fx, fy = food
    ins, state, _ = arm_F(snake, food)
    kinds = {d: cell_kind(snake, food, hx + DIRS[d][0], hy + DIRS[d][1]) for d in KN}
    order = sorted(KN, key=lambda d: 0 if kinds[d] == 'FOOD' else (1 if kinds[d] in ('empty', 'TAIL-LEAVING') else 2))
    crit = {d: f"cell row {hy + DIRS[d][1]} col {hx + DIRS[d][0]} is {kinds[d]}" for d in order}
    return ins, state, crit

def arm_H(snake, food):
    # 同 F，但把 WALL/BODY 落点标 BLOCKED → 桥接动作掩码清零这些方向（只剪物理不可能，不透露食物在哪）。
    hx, hy = snake[0]; fx, fy = food
    ins, state, _ = arm_F(snake, food)
    crit = {}
    for d in KN:
        k = cell_kind(snake, food, hx + DIRS[d][0], hy + DIRS[d][1])
        if k in ('WALL', 'BODY'):
            crit[d] = f"BLOCKED: cell row {hy + DIRS[d][1]} col {hx + DIRS[d][0]} is {k}"
        else:
            crit[d] = f"cell row {hy + DIRS[d][1]} col {hx + DIRS[d][0]} is {k}"
    return ins, state, crit

ARMS = {'A_question': arm_A, 'C_coord_eq': arm_C, 'D_egocentric': arm_D,
        'F_coords_rich': arm_F, 'G_food_first': arm_G, 'H_masked': arm_H}

def decide(model, state, instructions, criteria):
    req = {'model': model, 'state': state, 'instructions': instructions, 'criteria': criteria}
    r = urllib.request.Request('http://127.0.0.1:8890/decide', json.dumps(req).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(r))

def step_apply(snake, food, choice_dir):
    hx, hy = snake[0]; dx, dy = DIRS[choice_dir]; nx, ny = hx + dx, hy + dy
    eat = (nx, ny) == food
    body = snake if eat else snake[:-1]
    if not (0 <= nx < GW and 0 <= ny < GH): return None, 'wall', eat
    if (nx, ny) in body: return None, 'body', eat
    snake.insert(0, (nx, ny))
    if eat: return snake, 'alive', True
    snake.pop(); return snake, 'alive', False

def play_compliant(name, builder, model='laya', seed=1000):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]; food = place_food(rng, snake); eaten = 0; cause = 'cap'
    facing = FACE
    steps = 0
    hit_greedy = tot = 0
    pick_hist = {d: 0 for d in KN}; top1_sum = 0.0
    for steps in range(STEPS):
        if name == 'D_egocentric':
            ins, state, crit = builder(snake, food)
            resp = decide(model, state, ins, crit)
            turn = resp['choice']; choice_dir = egocentric_to_board(turn, facing)
            if choice_dir is None: cause = 'badpick'; break
        else:
            ins, state, crit = builder(snake, food)
            resp = decide(model, state, ins, crit)
            choice_dir = resp['choice']
        probs = resp['probabilities']
        g = greedy_dir(snake, food)
        if choice_dir == g: hit_greedy += 1
        tot += 1
        pick_hist[choice_dir] = pick_hist.get(choice_dir, 0) + 1
        top1_sum += max(probs.values())
        facing = choice_dir
        snake, cause, ate = step_apply(snake, food, choice_dir)
        if cause != 'alive': break
        if ate:
            food = place_food(rng, snake); eaten += 1
            if food is None: cause = 'win'; break
    return {'arm': name, 'food': eaten, 'cause': cause, 'steps': steps,
            'greedy_acc': round(hit_greedy / max(tot, 1), 3), 'mean_top1': round(top1_sum / max(tot, 1), 3),
            'pick_hist': pick_hist}

def play_relabel(model='laya', seed=1000):
    rng = random.Random(seed)
    snake = [(6, 6), (5, 6), (4, 6)]; food = place_food(rng, snake); eaten = 0; cause = 'cap'; steps = 0
    for steps in range(STEPS):
        ins, state, crit, lab = arm_E_relabel(snake, food)
        resp = decide(model, state, ins, crit)
        choice_dir = lab.get(resp['choice'], resp['choice'])
        snake, cause, ate = step_apply(snake, food, choice_dir)
        if cause != 'alive': break
        if ate:
            food = place_food(rng, snake); eaten += 1
            if food is None: cause = 'win'; break
    return {'arm': 'E_relabel_CTRL', 'food': eaten, 'cause': cause, 'steps': steps}

if __name__ == '__main__':
    out = []
    for name, b in ARMS.items():
        games = [play_compliant(name, b, seed=1000 + i) for i in range(NG)]
        foods = [g['food'] for g in games]
        out.append({'name': name, 'compliant': True, 'mean_food': round(sum(foods) / len(foods), 2),
                    'foods': foods, 'causes': [g['cause'] for g in games],
                    'greedy_acc_mean': round(sum(g['greedy_acc'] for g in games) / len(games), 3),
                    'top1_mean': round(sum(g['mean_top1'] for g in games) / len(games), 3),
                    'sample_hist': games[0]['pick_hist']})
    eg = [play_relabel(seed=1000 + i) for i in range(NG)]
    efoods = [g['food'] for g in eg]
    out.append({'name': 'E_relabel_CTRL', 'compliant': False, 'note': '把贪心方向标成UP=答案透出，仅作诊断对照',
                'mean_food': round(sum(efoods) / len(efoods), 2), 'foods': efoods,
                'causes': [g['cause'] for g in eg]})
    json.dump(out, open('_prompt_ab.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('WROTE _prompt_ab.json arms=', len(out))
