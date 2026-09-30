# -*- coding: utf-8 -*-
"""扫随机蛇局，找一步 flood 与两拍 flood2 判定不一致（尤其"一步看是袋、两步看不袋"）的状态，
输出 JSON 供页面 JS 重放，逐格比对移植正确性。"""
import json, random

GW = GH = 12
DIRS = ((0, 1), (0, -1), (1, 0), (-1, 0))

def is_safe(x, y, b):
    return 0 <= x < GW and 0 <= y < GH and [x, y] not in b

def flood(sx, sy, b):
    occ = {tuple(s) for s in b}
    seen = {(sx, sy)}
    q = [(sx, sy)]
    c = 0
    while q:
        x, y = q.pop(0)
        c += 1
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            k = (nx, ny)
            if 0 <= nx < GW and 0 <= ny < GH and k not in seen and k not in occ:
                seen.add(k)
                q.append((nx, ny))
    return c

def flood2(head, snake, dx, dy):
    nh = [head[0] + dx, head[1] + dy]
    body_after = [nh] + [list(s) for s in snake[:-1]]
    walls_next = body_after[:-1]
    best = 0
    for ddx, ddy in DIRS:
        cx, cy = nh[0] + ddx, nh[1] + ddy
        if is_safe(cx, cy, walls_next):
            best = max(best, flood(cx, cy, walls_next))
    return best

random.seed(7)
found = []
for trial in range(4000 if __name__ == "__main__" else 0):
    L = random.choice([8, 12, 16, 20, 26, 34])
    x, y = random.randrange(2, 10), random.randrange(2, 10)
    snake = [[x, y]]
    for _ in range(L):
        opts = [[snake[-1][0] + d[0], snake[-1][1] + d[1]] for d in DIRS]
        opts = [o for o in opts if is_safe(o[0], o[1], snake)]
        if not opts:
            break
        snake.append(random.choice(opts))
    snake.reverse()  # head first
    head = snake[0]
    if len(snake) < 6:
        continue
    walls = snake[:-1]
    for dx, dy in DIRS:
        nx, ny = head[0] + dx, head[1] + dy
        if not is_safe(nx, ny, walls):
            continue
        sp1 = flood(nx, ny, walls)
        sp2 = flood2(head, snake, dx, dy)
        pk = len(snake) + 2
        if (sp1 < pk <= sp2) or (sp2 < pk <= sp1) or abs(sp1 - sp2) >= 8:
            fx, fy = random.choice([(c[0], c[1]) for c in
                [(0, 0), (11, 0), (0, 11), (11, 11), (5, 0), (0, 5), (11, 5), (5, 11)]])
            found.append({
                "snake": snake, "dir": {"x": dx, "y": dy},
                "food": [fx, fy], "sp1": sp1, "sp2": sp2, "len": len(snake),
            })
            break
    if len(found) >= 6:
        break

if __name__ == "__main__":
    print(json.dumps(found[:6], ensure_ascii=False))
