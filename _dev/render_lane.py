# -*- coding: utf-8 -*-
"""渲染「五路贪吃蛇实况」段落（1280x720 @25fps）：
   ① 未训练 Laya 撞墙实测重放   ② 微调 Laya 400 手真实桥接日志回放
   ③ 环契约+跨身计数 吃 141 格实录食物   ④ 环保险算法现场真跑   ⑤ 通用 Agent 141 真实回放
   聚光灯按 _dev/lane_timeline.json（=旁白逐句时长）切换，声画同步。

   用法：
     python _dev/render_lane.py --preview 5,11,17,22      # 只出几张预览图（不建帧目录）
     python _dev/render_lane.py                           # 全量渲染到 _ppt_video4/lane_frames/
"""
import json, math, pathlib, sys, time

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lane_config import PIECES, FPS, TAIL  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "_ppt_video4" / "lane_frames"
PREVIEW = ROOT / "_dev"
TL = json.load(open(HERE / "lane_timeline.json", encoding="utf-8"))
TOTAL = TL["total"]
NFRAMES = int(math.ceil(TOTAL * FPS))

# ── 配色（与 laya-ppt.html / laya-snake-cockpit.html 同源） ──
BG = (11, 14, 20)
PANEL = (18, 23, 34)
PANEL_HI = (25, 33, 50)
LINE = (35, 43, 58)
FG = (232, 237, 245)
DIM = (139, 151, 171)
DIM2 = (108, 120, 140)
GOLD = (240, 180, 41)
GREEN = (62, 207, 142)
RED = (239, 91, 91)
BLUE = (90, 167, 240)
DARK = (13, 17, 25)

LANE_COL = [RED, BLUE, GREEN, GREEN, GREEN]
LANE_HEAD = [(255, 205, 205), FG, FG, FG, FG]
LANE_TITLE = ["未训练 Laya", "微调 Laya", "环契约 + 计数", "环保险算法", "通用 Agent（我）"]
LANE_SUB = ["裸棋盘 · 0 分 ×23 局", "小抄特征 · 均分 59.8", "模型 · 141 通关", "纯代码 · 141 通关", "我 · 141 通关"]
LANE_TAG = [("实测重放", RED), ("真日志回放 · 1×", BLUE), ("实录食物 · 示意走位", GOLD),
            ("现场真跑 · 1× 速度", GREEN), ("真实回放 · 1×", GREEN)]

# ── 底部字幕（与旁白逐句对齐） ──
CAPTIONS = {
    "L00": ("五路选手 · 同台实况：五道全是动的",
            "同一考场 12×12、同一食物流 ｜ ①实测重放 ②桥接日志回放 ③实录食物（示意走位）④现场真跑 ⑤真实回放"),
    "L01": ("①未被训练的 Laya：四个方向概率几乎均匀，每步 argmax 都是 UP",
            "23 局全部 0 分，第 6–7 步撞顶墙——换种子、换食物，不换死法"),
    "L02": ("②微调 Laya：2026-09-26 桥接日志 400 手原件，290 手可重建蛇身",
            "小抄字符串、原始概率、掩码后概率全部是当年原件，逐手回放"),
    "L03": ("③环契约 + 跨身计数（零掩码）：吃 seed1002 通关局 141 格实录食物原序",
            "食物坐标/顺序/起点/首食为档案原件；该局逐手方向当年未留档，走位为环保险现场规划的示意"),
    "L04": ("④几十行环保险算法：此刻真跑，环不等式一票否决",
            "12 个种子全部 141 通关，不用 GPU、不用数据（画面 1× 正常速度）"),
    "L05": ("⑤通用 Agent（我）：同契约同种子，141 真实通关局 4370 步逐手回放",
            "351 秒全盘吃满、0 跨身；每段第一帧都是我当时真读到的输入原文"),
    "L06": ("同一考场、同一食物流 —— 模型道不造假",
            "没有逐手档案的部分我们明说是示意，绝不用动画冒充推理"),
}
LANE_OF_PIECE = {p["id"]: p["lane"] for p in TL["pieces"]}
WIN = {p["id"]: (p["start"], p["end"]) for p in TL["pieces"]}


def piece_at(t):
    """返回当前生效的旁白句 id（含末尾定格：沿用最后一句）"""
    cur = TL["pieces"][0]["id"]
    for p in TL["pieces"]:
        if t >= p["start"]:
            cur = p["id"]
    return cur


# ══════════════════════ 引擎（逐字对齐 laya-snake-cockpit.html） ══════════════════════
GW = GH = 12
KN = ["UP", "DOWN", "LEFT", "RIGHT"]
DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}


def mulberry32(a):
    st = {"a": a & 0xFFFFFFFF}

    def rnd():
        st["a"] = (st["a"] + 0x6D2B79F5) & 0xFFFFFFFF
        a2 = st["a"]
        t = (a2 ^ (a2 >> 15)) * (1 | a2) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) & 0xFFFFFFFF ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rnd


def step_snake(snake, food, d):
    hx, hy = snake[0]
    dx, dy = DIRS[d]
    nx, ny = hx + dx, hy + dy
    eat = (nx == food[0] and ny == food[1])
    body = snake if eat else snake[:-1]
    if nx < 0 or nx >= GW or ny < 0 or ny >= GH:
        return snake, True, False
    if any(s[0] == nx and s[1] == ny for s in body):
        return snake, True, False
    ns = [[nx, ny]] + [list(s) for s in snake]
    if not eat:
        ns.pop()
    return ns, False, eat


def land_of(nx, ny, snake, food):
    if nx < 0 or nx >= GW or ny < 0 or ny >= GH:
        return "wall"
    tail = snake[-1]
    eat = (nx == food[0] and ny == food[1])
    if any(s[0] == nx and s[1] == ny for s in snake[1:-1]):
        return "body"
    if len(snake) > 1 and nx == tail[0] and ny == tail[1]:
        return "body" if eat else "vacating"
    return "free"


def cidx(x, y):
    if y == 0:
        return 0 if x == 0 else 133 + (11 - x)
    s = 1 + 11 * x
    return s + (y - 1) if x % 2 == 0 else s + (11 - y)


_CIDX = [[cidx(x, y) for x in range(GW)] for y in range(GH)]


def loop_ahead(snake, food):
    hi = _CIDX[snake[0][1]][snake[0][0]]
    def D(p):
        return (_CIDX[p[1]][p[0]] - hi) % 144
    m1 = m2 = 144
    for i in range(1, len(snake)):
        dd = D(snake[i])
        if i < len(snake) - 1 and dd < m2:
            m2 = dd
        if dd < m1:
            m1 = dd
    return {"foodAhead": D(food), "bodyAhead": m1, "bodyGoAhead": m2}


def loop_safe(snake, food, d):
    hx, hy = snake[0]
    nx, ny = hx + DIRS[d][0], hy + DIRS[d][1]
    land = land_of(nx, ny, snake, food)
    if land in ("wall", "body"):
        return False
    cd = (_CIDX[ny][nx] - _CIDX[hy][hx]) % 144
    la = loop_ahead(snake, food)
    eat = (nx == food[0] and ny == food[1])
    return cd <= la["bodyAhead"] - 1 if eat else (cd <= la["bodyGoAhead"] - 1 and cd <= la["foodAhead"])


def cyc_of(snake, d):
    hx, hy = snake[0]
    nx, ny = hx + DIRS[d][0], hy + DIRS[d][1]
    if not (0 <= nx < GW and 0 <= ny < GH):
        return None                      # 出界方向：环上没有落点（照 JS 里会算出垃圾数，这里显式给“—”）
    return (_CIDX[ny][nx] - _CIDX[hy][hx]) % 144


def flood_from(snake, land):
    occ = {(p[0], p[1]) for p in snake}
    occ.discard((land[0], land[1]))
    occ.discard((snake[-1][0], snake[-1][1]))
    seen = {(land[0], land[1])}
    q = [land]
    n = 1
    while q:
        x, y = q.pop(0)
        for k in KN:
            a, b = x + DIRS[k][0], y + DIRS[k][1]
            if a < 0 or a >= GW or b < 0 or b >= GH or (a, b) in seen or (a, b) in occ:
                continue
            seen.add((a, b))
            q.append([a, b])
            n += 1
    return n


def grid_rows(snake, food):
    g = [["0"] * GW for _ in range(GH)]
    for i, s in enumerate(snake):
        g[s[1]][s[0]] = "2" if i == 0 else "1"
    g[food[1]][food[0]] = "3"
    return ["".join(r) for r in g]


# ══════════════════════ 五条赛道的逐帧状态 ══════════════════════
REP = json.load(open(ROOT / "_cockpit_replay.json", encoding="utf-8"))
JF = json.load(open(ROOT / "_jumpfood_1002.json", encoding="utf-8"))
MY = json.load(open(ROOT / "_myrun_data.json", encoding="utf-8"))


def sim_zs():
    """① 未训练：每步 argmax=UP，第 7 步撞顶墙"""
    snake = [[2, 6], [1, 6], [0, 6]]
    food = [6, 5]
    states = [(snake, False)]
    for _ in range(7):
        snake, died, _eat = step_snake(snake, food, "UP")
        states.append((snake, died))
        if died:
            break
    return states


def sim_cyc():
    """③ 环契约道：环保险现场规划，追 seed1002 档案的 141 格食物原序"""
    FD = [list(f) for f in JF["foods"]]
    st = {"snake": [[6, 6], [5, 6], [4, 6]], "food": FD[0], "k": 0,
          "steps": 0, "jumps": 0, "dead": False, "won": False}
    rec = []
    while not st["dead"] and not st["won"] and st["steps"] < 30000:
        hx, hy = st["snake"][0]
        cands = [d for d in KN if land_of(hx + DIRS[d][0], hy + DIRS[d][1], st["snake"], st["food"]) not in ("wall", "body")]
        safe = [d for d in cands if loop_safe(st["snake"], st["food"], d)]
        if len(st["snake"]) > 40 and safe:
            pool = [sorted(safe, key=lambda d: cyc_of(st["snake"], d))[0]]
        else:
            roomy = [d for d in safe if flood_from(st["snake"], [hx + DIRS[d][0], hy + DIRS[d][1]]) >= len(st["snake"])]
            pool = roomy or safe or cands
        if not pool:
            st["dead"] = True
            break
        pick = sorted(pool, key=lambda d: (abs(hx + DIRS[d][0] - st["food"][0]) + abs(hy + DIRS[d][1] - st["food"][1]),
                                           -cyc_of(st["snake"], d)))[0]
        if not loop_safe(st["snake"], st["food"], pick):
            st["jumps"] += 1
        ns, died, ate = step_snake(st["snake"], st["food"], pick)
        st["snake"], st["dead"], st["steps"] = ns, died, st["steps"] + 1
        if died:
            break
        if ate:
            st["k"] += 1
            if st["k"] >= len(FD):
                st["won"] = True
            else:
                st["food"] = FD[st["k"]]
        rec.append({"snake": [list(p) for p in st["snake"]], "food": list(st["food"]), "k": st["k"],
                    "steps": st["steps"], "jumps": st["jumps"], "won": st["won"], "pick": pick})
    return rec


def sim_algo():
    """④ 环保险算法：现场真跑（seed 1000，与驾驶舱页一致）"""
    rng = mulberry32(1000)
    st = {"snake": [[6, 6], [5, 6], [4, 6]], "score": 0, "steps": 0, "jumps": 0,
          "dead": False, "won": False}

    def place_free():
        free = [[x, y] for y in range(GH) for x in range(GW)
                if not any(p[0] == x and p[1] == y for p in st["snake"])]
        return free[int(rng() * len(free))] if free else None

    st["food"] = place_free()
    rec = []
    while not st["dead"] and not st["won"] and st["steps"] < 30000:
        cands = [d for d in KN if land_of(st["snake"][0][0] + DIRS[d][0], st["snake"][0][1] + DIRS[d][1], st["snake"], st["food"]) not in ("wall", "body")]
        safe = [d for d in cands if loop_safe(st["snake"], st["food"], d)]
        pool = safe or cands
        hx, hy = st["snake"][0]
        pick = sorted(pool, key=lambda d: abs(hx + DIRS[d][0] - st["food"][0]) + abs(hy + DIRS[d][1] - st["food"][1]))[0]
        if not loop_safe(st["snake"], st["food"], pick):
            st["jumps"] += 1
        safe_now = [d for d in KN if loop_safe(st["snake"], st["food"], d)]   # 判断表＝本步下手前的事实
        ns, died, ate = step_snake(st["snake"], st["food"], pick)
        st["snake"], st["dead"], st["steps"] = ns, died, st["steps"] + 1
        if died:
            break
        if ate:
            st["score"] += 1
            f = place_free()
            if f is None:
                st["won"] = True
            else:
                st["food"] = f
        rec.append({"snake": [list(p) for p in st["snake"]], "food": list(st["food"]),
                    "score": st["score"], "steps": st["steps"], "jumps": st["jumps"],
                    "pick": pick, "safe": safe_now, "won": st["won"]})
    return rec


def sim_me():
    """⑤ 通用 Agent：4370 步真实通关局逐手回放"""
    snake = [list(p) for p in MY["start"]]
    foods = [list(f) for f in MY["foods"]]
    food = foods[0]
    score = 0
    rec = []
    for i, d in enumerate(MY["dirs"]):
        ns, died, ate = step_snake(snake, food, d)
        snake, dead = ns, died
        if ate:
            score += 1
            food = foods[score] if score < len(foods) else food
        rec.append({"snake": [list(p) for p in snake], "food": list(food), "score": score,
                    "steps": i + 1, "dead": died, "won": score >= len(foods)})
        if died:
            break
    return rec


print("模拟五条赛道 …", flush=True)
T0 = time.time()
ST_ZS = sim_zs()
ST_CYC = sim_cyc()
ST_ALGO = sim_algo()
ST_ME = sim_me()
print(f"  ①死亡重放 {len(ST_ZS)-1} 步 ｜ ③示意规划 {len(ST_CYC)} 步 (吃到 {ST_CYC[-1]['k']}/141, 跨身 {ST_CYC[-1]['jumps']}) "
      f"｜ ④真跑 {len(ST_ALGO)} 步 (得分 {ST_ALGO[-1]['score']}, 跨身 {ST_ALGO[-1]['jumps']}) "
      f"｜ ⑤回放 {len(ST_ME)} 步 (得分 {ST_ME[-1]['score']})  [{time.time()-T0:.1f}s]", flush=True)

# 速度完全对齐驾驶舱页 HTML 的默认步速，并对齐到 25fps 的整数帧（画面 1×，不做任何加速）
# ③ HTML 默认 35ms/步 → 40ms（每帧一步）；④ 70ms → 80ms、⑤ 60ms → 80ms、② 90ms → 80ms（每 2 帧一步）
STEP_FRAMES = {"fd": 2, "cyc": 1, "algo": 2, "me": 2}
SPEED_NOTE = {
    "fd": "画面 1×（80ms/手，对齐驾驶舱页）",
    "cyc": "画面 1×（40ms/步，对齐驾驶舱页）",
    "algo": "画面 1×（80ms/步，对齐驾驶舱页）",
    "me": "画面 1×（80ms/步，对齐驾驶舱页）",
}
ZS_STEP_F, ZS_HOLD_F = 11, 20          # ①：460ms/步（11 帧）+ 死亡定格 0.8s，与驾驶舱页一致
print("  画面 1× 正常速度：" + "  ".join(f"{k}={v*40}ms/步" for k, v in STEP_FRAMES.items()), flush=True)


def state_at(f, t):
    """返回 5 条赛道在第 f 帧的状态"""
    # ① 撞墙循环
    cyc = 7 * ZS_STEP_F + ZS_HOLD_F
    f2 = f % cyc
    s = min(f2 // ZS_STEP_F, 7)
    snake1, dead1 = ST_ZS[s]
    # ② 真实桥接日志回放（1× 正常速度）
    i2 = min(f // STEP_FRAMES["fd"], len(REP["frames"]) - 1)
    # ③④⑤ 各自按驾驶舱页的默认步速推进（1×，整数帧）
    i3 = min(f // STEP_FRAMES["cyc"], len(ST_CYC) - 1)
    i4 = min(f // STEP_FRAMES["algo"], len(ST_ALGO) - 1)
    i5 = min(f // STEP_FRAMES["me"], len(ST_ME) - 1)
    return {"zs": (snake1, dead1, s), "fd": (i2, REP["frames"][i2]),
            "cyc": (i3, ST_CYC[i3]), "algo": (i4, ST_ALGO[i4]), "me": (i5, ST_ME[i5])}


# ══════════════════════ 绘制 ══════════════════════
FONTS = {
    "title": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 29),
    "sub": ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 14),
    "ptitle": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 14),
    "psub": ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 11),
    "tag": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 10),
    "badge": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 15),
    "score": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 15),
    "mono": ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 11),
    "monob": ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 11),
    "note": ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 11),
    "noteb": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 11),
    "cap": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 21),
    "capsub": ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13),
    "win": ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 17),
}

W, H = 1280, 720
PX0, PY0, PW, PH, PGAP = 23, 78, 237, 528, 12
BOARD, CELL = 204, 17
BX_OFF, BY_OFF = 16, 78
BLINK = True


def tw(d, s, f):
    return d.textlength(s, font=f)


def fit(d, s, f, maxw):
    if tw(d, s, f) <= maxw:
        return s
    while s and tw(d, s + "…", f) > maxw:
        s = s[:-1]
    return s + "…"


def wrap(d, s, f, maxw, maxlines=2):
    lines, cur = [], ""
    for ch in s:
        if tw(d, cur + ch, f) > maxw and cur:
            lines.append(cur)
            cur = ch
            if len(lines) == maxlines:
                break
        else:
            cur += ch
    if len(lines) < maxlines and cur:
        lines.append(cur)
    if len(lines) == maxlines:
        rest = "".join(lines)
        if tw(d, rest, f) < tw(d, s, f):          # 有截断
            lines[-1] = fit(d, lines[-1] + "…", f, maxw)
    return lines[:maxlines]


def board_img(state, lane):
    """把一面棋盘画到 204x204"""
    im = Image.new("RGB", (BOARD, BOARD), DARK)
    d = ImageDraw.Draw(im)
    for i in range(1, 12):
        d.line([(i * CELL, 0), (i * CELL, BOARD)], fill=(28, 36, 50))
        d.line([(0, i * CELL), (BOARD, i * CELL)], fill=(28, 36, 50))
    snake, food = state
    for k in range(len(snake) - 1, 0, -1):
        x, y = snake[k]
        c = LANE_COL[lane] if k % 4 else tuple(int(v * 0.72) for v in LANE_COL[lane])
        d.rectangle([x * CELL + 2, y * CELL + 2, x * CELL + CELL - 3, y * CELL + CELL - 3], fill=c)
    hx, hy = snake[0]
    d.rectangle([hx * CELL + 1, hy * CELL + 1, hx * CELL + CELL - 2, hy * CELL + CELL - 2], fill=LANE_HEAD[lane])
    fx, fy = food
    d.ellipse([fx * CELL + CELL / 2 - 5.5, fy * CELL + CELL / 2 - 5.5,
               fx * CELL + CELL / 2 + 5.5, fy * CELL + CELL / 2 + 5.5], fill=GOLD)
    return im


def bars(d, x, y, rows, w=178):
    """概率条：rows = [(label, pct, text, hi)]"""
    for label, pct, txt, hi in rows:
        col = GOLD if hi else (58, 67, 86)
        d.text((x, y), label, font=FONTS["note"], fill=FG if hi else DIM)
        d.text((x + w - tw(d, txt, FONTS["monob"]), y - 1), txt, font=FONTS["monob"], fill=col)
        d.rounded_rectangle([x, y + 14, x + w, y + 22], 4, fill=(26, 34, 49))
        if pct > 0:
            d.rounded_rectangle([x, y + 14, x + max(6, w * pct), y + 22], 4, fill=col)
        y += 25
    return y


def draw_panel(img, d, i, st, active):
    x, y = PX0 + i * (PW + PGAP), PY0
    d.rounded_rectangle([x, y, x + PW - 1, y + PH - 1], 14,
                        fill=PANEL_HI if active else PANEL,
                        outline=GOLD if active else LINE, width=2 if active else 1)
    # 序号徽章 + 标题 + 副标题
    col = LANE_COL[i]
    d.rounded_rectangle([x + 12, y + 12, x + 38, y + 38], 8, fill=col)
    d.text((x + 18 if i != 0 else x + 19, y + 15), "①②③④⑤"[i], font=FONTS["badge"], fill=(12, 15, 22))
    d.text((x + 46, y + 13), LANE_TITLE[i], font=FONTS["ptitle"], fill=FG)
    d.text((x + 46, y + 33), LANE_SUB[i], font=FONTS["psub"], fill=DIM)
    tag, tagc = LANE_TAG[i]
    twid = tw(d, tag, FONTS["tag"]) + 14
    d.rounded_rectangle([x + PW - 12 - twid, y + 48, x + PW - 12, y + 66], 6,
                        fill=(tagc[0] // 5, tagc[1] // 5, tagc[2] // 5), outline=tagc, width=1)
    d.text((x + PW - 12 - twid + 7, y + 51), tag, font=FONTS["tag"], fill=tagc)
    # 棋盘
    if i == 0:
        bstate = (st[0], [6, 5])
    elif i == 1:
        bstate = (st["body"], st["food"])
    else:
        bstate = (st["snake"], st["food"])
    overlay = None
    img.paste(board_img(bstate, i), (x + BX_OFF, y + BY_OFF))
    bx, by = x + BX_OFF, y + BY_OFF
    # 棋盘下方的信息区
    tx = x + 14
    tw_avail = PW - 28
    ly = by + BOARD + 12
    if i == 0:
        snake, dead, s = st
        d.text((tx, ly), f"第 {min(s,7)} 步", font=FONTS["noteb"], fill=FG)
        if dead:
            d.text((tx + 58, ly), "已撞顶墙", font=FONTS["noteb"], fill=RED)
        else:
            d.text((tx + 58, ly), "argmax = UP", font=FONTS["mono"], fill=GOLD)
        ly = bars(d, tx, ly + 22, [("上 UP", 0.39, "0.39", True), ("下 DOWN", 0.22, "0.22", False),
                                   ("左 LEFT", 0.19, "0.19", False), ("右 RIGHT", 0.19, "0.19", False)])
        d.text((tx, ly + 2), "23 局全部 0 分 · 死法一致", font=FONTS["note"], fill=RED)
        d.text((tx, ly + 19), "概率几乎均匀＝在复读语料先验", font=FONTS["note"], fill=DIM)
        if dead:
            overlay = ("撞顶墙 · 0 分", "第 7 步，局局如此", RED)
    elif i == 1:
        f = st
        d.text((tx, ly), f"实录第 {st_i2 + 1}/290 手", font=FONTS["noteb"], fill=FG)
        d.text((tx + 122, ly), f"切片 {f['seg']+1}/3", font=FONTS["mono"], fill=DIM)
        p = f["probs"][f["choice"]]
        d.text((tx, ly + 20), f"本手选择 {f['choice']}", font=FONTS["noteb"], fill=GOLD)
        d.text((tx + 104, ly + 21), "掩码后", font=FONTS["note"], fill=DIM)
        d.text((tx + 146, ly + 21), f"{p:.3f}", font=FONTS["monob"], fill=GOLD)
        d.text((tx, ly + 38), "原始概率", font=FONTS["note"], fill=DIM)
        d.text((tx + 56, ly + 39), f"raw {f['raw'][f['choice']]}", font=FONTS["mono"], fill=DIM)
        d.rounded_rectangle([tx, ly + 56, tx + tw_avail, ly + 70], 5, fill=(26, 34, 49))
        d.rounded_rectangle([tx, ly + 56, tx + max(8, tw_avail * min(1.0, p)), ly + 70], 5, fill=GOLD)
        for k, ln in enumerate(wrap(d, f["crit"][f["choice"]], FONTS["note"], tw_avail, 2)):
            d.text((tx, ly + 78 + k * 17), ln, font=FONTS["note"], fill=DIM)
        d.text((tx, ly + 116), "400 手桥接原档 · 小抄随步刷新", font=FONTS["note"], fill=BLUE)
        d.text((tx, ly + 133), SPEED_NOTE["fd"], font=FONTS["note"], fill=DIM2)
        if st_i2 >= len(REP["frames"]) - 1:
            overlay = ("290 手回放完毕", "桥接日志原件 · 逐手可查", BLUE)
    elif i == 2:
        kk = min(st_i3["k"], 141)
        d.text((tx, ly), f"食物 #{kk}/141", font=FONTS["noteb"], fill=FG)
        d.text((tx + 116, ly), f"步 {st_i3['steps']}", font=FONTS["mono"], fill=DIM)
        la = loop_ahead(st_i3["snake"], st_i3["food"])
        d.text((tx, ly + 20), f"身长 {len(st_i3['snake'])} · 跨身 {st_i3['jumps']}", font=FONTS["note"], fill=FG)
        d.text((tx, ly + 38), f"bodyGoAhead={la['bodyGoAhead']}", font=FONTS["mono"], fill=GOLD)
        d.text((tx, ly + 54), f"foodAhead={la['foodAhead']}  一票否决", font=FONTS["mono"], fill=GOLD)
        d.text((tx, ly + 74), "档案件：4592 步 / 零违规", font=FONTS["note"], fill=DIM)
        d.text((tx, ly + 91), "走位＝环保险现场规划（示意）", font=FONTS["note"], fill=GOLD)
        d.text((tx, ly + 108), SPEED_NOTE["cyc"], font=FONTS["note"], fill=DIM2)
        if st_i3["won"]:
            overlay = ("141 格吃满", "jumpCount 保持 0", GREEN)
    elif i == 3:
        d.text((tx, ly), "本步判断表" if not st_i4["won"] else "通关收尾", font=FONTS["noteb"], fill=FG)
        d.text((tx + 90, ly), f"步 {st_i4['steps']}", font=FONTS["mono"], fill=DIM)
        if st_i4["won"]:
            # 通关后不再显示终局那张“全盘皆 FAIL”的表（蛇已占满棋盘），改出结果摘要
            for k, (txt, col) in enumerate([("环不等式一票否决", GOLD), ("零掩码 · 零代码代答", DIM),
                                            ("12 种子全部 141 通关", GREEN), ("不用 GPU · 不用数据", DIM)]):
                d.text((tx, ly + 26 + k * 22), txt, font=FONTS["noteb"] if k == 2 else FONTS["note"], fill=col)
        else:
            yy = ly + 20
            for dd in KN:
                ok = dd in st_i4["safe"]
                cx = cyc_of(st_i4["snake"], dd)
                d.text((tx, yy), f"{dd:<5}", font=FONTS["mono"], fill=FG)
                d.text((tx + 44, yy), "cyc=—" if cx is None else f"cyc={cx:<3}", font=FONTS["mono"], fill=DIM)
                d.text((tx + 92, yy), "PASS" if ok else "FAIL", font=FONTS["monob"], fill=GREEN if ok else RED)
                d.text((tx + 122, yy), "环安全" if ok else "越环", font=FONTS["note"], fill=GREEN if ok else RED)
                if dd == st_i4["pick"]:
                    d.text((tx + 162, yy), "← 执行", font=FONTS["note"], fill=GOLD)
                yy += 17
            d.text((tx, yy + 6), f"得分 {st_i4['score']}/141 · 跨身 {st_i4['jumps']}", font=FONTS["noteb"], fill=FG)
            d.text((tx, yy + 24), "12 种子全部 141 · 无模型调用", font=FONTS["note"], fill=GREEN)
            d.text((tx, yy + 42), SPEED_NOTE["algo"], font=FONTS["note"], fill=DIM2)
        if st_i4["won"]:
            overlay = ("141 通关", f"{st_i4['steps']} 步 · 零跨身", GREEN)
        elif BLINK:
            d.circle((x + PW - 20, y + 24), 4, fill=RED)
    else:
        d.text((tx, ly), f"第 {st_i5['steps']}/4370 步", font=FONTS["noteb"], fill=FG)
        d.text((tx + 112, ly), f"跨身 0", font=FONTS["mono"], fill=GREEN)
        d.text((tx, ly + 20), f"得分 {st_i5['score']}/141 · 蛇长 {len(st_i5['snake'])}", font=FONTS["note"], fill=FG)
        seg_i = 0
        for k, sg in enumerate(MY["segs"]):
            if sg["stepsAtAsk"] <= st_i5["steps"]:
                seg_i = k
        sg = MY["segs"][seg_i]
        d.text((tx, ly + 38), f"第 {sg['askId']} 段 · 链长 {len(sg.get('chain') or [])} 手", font=FONTS["note"], fill=GOLD)
        d.text((tx, ly + 56), "同契约同种子（20260929）", font=FONTS["note"], fill=DIM)
        d.text((tx, ly + 74), "351 秒真通关 · 档案逐手可查", font=FONTS["note"], fill=DIM)
        d.text((tx, ly + 92), SPEED_NOTE["me"], font=FONTS["note"], fill=DIM2)
        if st_i5["won"]:
            overlay = ("141 全盘通关", "4370 步 · 0 跨身", GREEN)
    if overlay:
        txt, sub, col = overlay
        bx, by = x + BX_OFF, y + BY_OFF
        band = Image.new("RGBA", (BOARD, BOARD), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bd.rectangle([0, 62, BOARD, 142], fill=(10, 13, 20, 215))
        bd.text((BOARD / 2 - tw(bd, txt, FONTS["win"]) / 2, 76), txt, font=FONTS["win"], fill=col)
        bd.text((BOARD / 2 - tw(bd, sub, FONTS["note"]) / 2, 106), sub, font=FONTS["note"], fill=DIM)
        img.alpha_composite(band, (bx, by))


def render(f):
    t = f / FPS
    pid = piece_at(t)
    lane = LANE_OF_PIECE[pid]
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)    # 顶栏
    d.rounded_rectangle([23, 22, 30, 50], 4, fill=GOLD)
    d.text((42, 20), "五路选手 · 同台实况", font=FONTS["title"], fill=FG)
    d.text((42, 52), "讲稿第 12 页 · 驾驶舱：每个方法一条贪吃蛇，五道同时在跑", font=FONTS["sub"], fill=DIM)
    right = "12×12 同一考场 · 同种子同食物流 · 全部实况"
    d.text((W - 23 - tw(d, right, FONTS["sub"]), 26), right, font=FONTS["sub"], fill=DIM2)
    right2 = "①实测重放 ②真日志 ③④⑤141"
    d.text((W - 23 - tw(d, right2, FONTS["sub"]), 48), right2, font=FONTS["sub"], fill=DIM2)
    # 五块面板
    s = state_at(f, t)
    global st_i2, st_i3, st_i4, st_i5, BLINK
    BLINK = (f // 10) % 2 == 0
    st_i2 = s["fd"][0]
    st_i3 = s["cyc"][1]
    st_i4 = s["algo"][1]
    st_i5 = s["me"][1]
    for i in range(5):
        stt = [s["zs"], s["fd"][1], s["cyc"][1], s["algo"][1], s["me"][1]][i]
        draw_panel(img, d, i, stt, lane == i + 1)
    if lane:  # 聚光灯：非当前赛道压暗
        for i in range(5):
            if i + 1 != lane:
                x, y = PX0 + i * (PW + PGAP), PY0
                ov = Image.new("RGBA", (PW, PH), (6, 9, 14, 132))
                img.alpha_composite(ov, (x, y))
    # 底部字幕条
    cy = PY0 + PH + 12
    d.rounded_rectangle([23, cy, W - 24, cy + 78], 12, fill=(16, 21, 31), outline=LINE)
    head, sub = CAPTIONS[pid]
    d.text((40, cy + 12), fit(d, head, FONTS["cap"], W - 80), font=FONTS["cap"], fill=FG)
    d.text((40, cy + 44), fit(d, sub, FONTS["capsub"], W - 80), font=FONTS["capsub"], fill=DIM)
    # 进度点
    for i in range(5):
        cx = W - 60 - (4 - i) * 18
        on = (lane == i + 1)
        if lane == 0:
            d.ellipse([cx - 4, cy + 58, cx + 4, cy + 66], fill=(150, 118, 40))
        else:
            d.ellipse([cx - 4, cy + 58, cx + 4, cy + 66], fill=GOLD if on else (52, 61, 78))
    d.text((W - 190, cy + 54), f"{t:5.1f}s / {TOTAL:.1f}s", font=FONTS["mono"], fill=DIM2)
    return img.convert("RGB")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--preview":
        for ts in args[1].split(","):
            f = int(float(ts) * FPS)
            p = PREVIEW / f"lane_preview_{float(ts):04.1f}s.png"
            render(f).save(p)
            print("preview →", p.name, f"（旁白句 {piece_at(f/FPS)}）", flush=True)
        sys.exit(0)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for f in range(NFRAMES):
        render(f).save(OUT / f"f{f:05d}.png")
        if f % 100 == 0:
            print(f"  {f}/{NFRAMES}  {time.time()-t0:.1f}s", flush=True)
    print(f"共 {NFRAMES} 帧 → {OUT}  ({time.time()-t0:.1f}s)", flush=True)
