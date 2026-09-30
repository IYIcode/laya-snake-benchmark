# 模型选手对局 · 完整记录

引擎：demo_llmplay.py（契约选项格式上报）· 玩家：Qwen（逐方向决策）
食物序列种子：20260929

## 终局

吃到 **7** 食物 · **82** 步 · 最长身长 **10**
结局：第83步撞向 DOWN：墙
翻车：第83步：该LEFT转向上口食物(6,6)时多按了一次DOWN，撞上底墙

## 速度记录

轮内单步间隔：中位 **34 ms**（范围 28–54 ms）
轮间思考时间：185s / 193s / 196s / 197s / 199s / 216s / 224s / 394s / 755s
说明：每轮把下一段路径批量决策；轮内单步间隔 ~30-40ms，轮间为模型推理时间

## 逐步决策

| 步 | 头→选 | 食物 | 四方向契约选项 | 备注 | 轮内间隔 |
|---|---|---|---|---|---|
| 1 | [6, 6]→**DOWN** | [0, 8] | UP:fd=9 sp=142 dg=0  DOWN:fd=7 sp=142 dg=0  LEFT:BLOCKED  RIGHT:fd=9 sp=142 dg=0 |  | — |
| 2 | [6, 7]→**LEFT** | [2, 7] | UP:BLOCKED  DOWN:fd=5 sp=142 dg=0  LEFT:fd=3 sp=142 dg=1  RIGHT:fd=5 sp=142 dg=0 |  | 35 ms |
| 3 | [5, 7]→**LEFT** | [2, 7] | UP:fd=4 sp=142 dg=1  DOWN:fd=4 sp=142 dg=0  LEFT:fd=2 sp=142 dg=0  RIGHT:BLOCKED |  | 30 ms |
| 4 | [4, 7]→**LEFT** | [2, 7] | UP:fd=3 sp=142 dg=0  DOWN:fd=3 sp=142 dg=0  LEFT:fd=1 sp=142 dg=0  RIGHT:BLOCKED |  | 28 ms |
| 5 | [3, 7]→**LEFT** | [2, 7] | UP:fd=2 sp=142 dg=0  DOWN:fd=2 sp=142 dg=0  LEFT:fd=0 sp=141 dg=0  RIGHT:BLOCKED | 🍃 吃到 | 754719 ms |
| 6 | [2, 7]→**LEFT** | [0, 4] | UP:fd=4 sp=141 dg=0  DOWN:fd=6 sp=141 dg=0  LEFT:fd=4 sp=141 dg=0  RIGHT:BLOCKED |  | 185029 ms |
| 7 | [1, 7]→**LEFT** | [0, 4] | UP:fd=3 sp=141 dg=0  DOWN:fd=5 sp=141 dg=0  LEFT:fd=3 sp=141 dg=1  RIGHT:BLOCKED |  | 30 ms |
| 8 | [0, 7]→**UP** | [0, 4] | UP:fd=2 sp=141 dg=1  DOWN:fd=4 sp=141 dg=1  LEFT:BLOCKED  RIGHT:BLOCKED |  | 32 ms |
| 9 | [0, 6]→**UP** | [0, 4] | UP:fd=1 sp=141 dg=1  DOWN:BLOCKED  LEFT:BLOCKED  RIGHT:fd=3 sp=141 dg=1 |  | 29 ms |
| 10 | [0, 5]→**UP** | [0, 4] | UP:fd=0 sp=140 dg=1  DOWN:BLOCKED  LEFT:BLOCKED  RIGHT:fd=2 sp=141 dg=0 | 🍃 吃到 | 51 ms |
| 11 | [0, 4]→**RIGHT** | [11, 8] | UP:fd=16 sp=140 dg=1  DOWN:BLOCKED  LEFT:BLOCKED  RIGHT:fd=14 sp=140 dg=0 |  | 193305 ms |
| 12 | [1, 4]→**RIGHT** | [11, 8] | UP:fd=15 sp=140 dg=0  DOWN:fd=13 sp=140 dg=1  LEFT:BLOCKED  RIGHT:fd=13 sp=140 dg=0 |  | 33 ms |
| 13 | [2, 4]→**RIGHT** | [11, 8] | UP:fd=14 sp=140 dg=0  DOWN:fd=12 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=12 sp=140 dg=0 |  | 33 ms |
| 14 | [3, 4]→**RIGHT** | [11, 8] | UP:fd=13 sp=140 dg=0  DOWN:fd=11 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=11 sp=140 dg=0 |  | 30 ms |
| 15 | [4, 4]→**RIGHT** | [11, 8] | UP:fd=12 sp=140 dg=0  DOWN:fd=10 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=10 sp=140 dg=0 |  | 30 ms |
| 16 | [5, 4]→**RIGHT** | [11, 8] | UP:fd=11 sp=140 dg=0  DOWN:fd=9 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=9 sp=140 dg=0 |  | 29 ms |
| 17 | [6, 4]→**RIGHT** | [11, 8] | UP:fd=10 sp=140 dg=0  DOWN:fd=8 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=8 sp=140 dg=0 |  | 32 ms |
| 18 | [7, 4]→**RIGHT** | [11, 8] | UP:fd=9 sp=140 dg=0  DOWN:fd=7 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=7 sp=140 dg=0 |  | 196608 ms |
| 19 | [8, 4]→**RIGHT** | [11, 8] | UP:fd=8 sp=140 dg=0  DOWN:fd=6 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=6 sp=140 dg=0 |  | 32 ms |
| 20 | [9, 4]→**RIGHT** | [11, 8] | UP:fd=7 sp=140 dg=0  DOWN:fd=5 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=5 sp=140 dg=0 |  | 35 ms |
| 21 | [10, 4]→**RIGHT** | [11, 8] | UP:fd=6 sp=140 dg=0  DOWN:fd=4 sp=140 dg=0  LEFT:BLOCKED  RIGHT:fd=4 sp=140 dg=1 |  | 29 ms |
| 22 | [11, 4]→**DOWN** | [11, 8] | UP:fd=5 sp=140 dg=1  DOWN:fd=3 sp=140 dg=1  LEFT:BLOCKED  RIGHT:BLOCKED |  | 47 ms |
| 23 | [11, 5]→**DOWN** | [11, 8] | UP:BLOCKED  DOWN:fd=2 sp=140 dg=1  LEFT:fd=4 sp=140 dg=1  RIGHT:BLOCKED |  | 30 ms |
| 24 | [11, 6]→**DOWN** | [11, 8] | UP:BLOCKED  DOWN:fd=1 sp=140 dg=1  LEFT:fd=3 sp=140 dg=0  RIGHT:BLOCKED |  | 31 ms |
| 25 | [11, 7]→**DOWN** | [11, 8] | UP:BLOCKED  DOWN:fd=0 sp=139 dg=1  LEFT:fd=2 sp=140 dg=0  RIGHT:BLOCKED | 🍃 吃到 | 31 ms |
| 26 | [11, 8]→**DOWN** | [2, 5] | UP:BLOCKED  DOWN:fd=13 sp=139 dg=1  LEFT:fd=11 sp=139 dg=0  RIGHT:BLOCKED |  | 223789 ms |
| 27 | [11, 9]→**LEFT** | [2, 5] | UP:BLOCKED  DOWN:fd=14 sp=139 dg=1  LEFT:fd=12 sp=139 dg=0  RIGHT:BLOCKED |  | 52 ms |
| 28 | [10, 9]→**LEFT** | [2, 5] | UP:fd=11 sp=139 dg=1  DOWN:fd=13 sp=139 dg=0  LEFT:fd=11 sp=139 dg=0  RIGHT:BLOCKED |  | 34 ms |
| 29 | [9, 9]→**LEFT** | [2, 5] | UP:fd=10 sp=139 dg=0  DOWN:fd=12 sp=139 dg=0  LEFT:fd=10 sp=139 dg=0  RIGHT:BLOCKED |  | 32 ms |
| 30 | [8, 9]→**LEFT** | [2, 5] | UP:fd=9 sp=139 dg=0  DOWN:fd=11 sp=139 dg=0  LEFT:fd=9 sp=139 dg=0  RIGHT:BLOCKED |  | 31 ms |
| 31 | [7, 9]→**LEFT** | [2, 5] | UP:fd=8 sp=139 dg=0  DOWN:fd=10 sp=139 dg=0  LEFT:fd=8 sp=139 dg=0  RIGHT:BLOCKED |  | 33 ms |
| 32 | [6, 9]→**LEFT** | [2, 5] | UP:fd=7 sp=139 dg=0  DOWN:fd=9 sp=139 dg=0  LEFT:fd=7 sp=139 dg=0  RIGHT:BLOCKED |  | 30 ms |
| 33 | [5, 9]→**LEFT** | [2, 5] | UP:fd=6 sp=139 dg=0  DOWN:fd=8 sp=139 dg=0  LEFT:fd=6 sp=139 dg=0  RIGHT:BLOCKED |  | 30 ms |
| 34 | [4, 9]→**LEFT** | [2, 5] | UP:fd=5 sp=139 dg=0  DOWN:fd=7 sp=139 dg=0  LEFT:fd=5 sp=139 dg=0  RIGHT:BLOCKED |  | 32 ms |
| 35 | [3, 9]→**LEFT** | [2, 5] | UP:fd=4 sp=139 dg=0  DOWN:fd=6 sp=139 dg=0  LEFT:fd=4 sp=139 dg=0  RIGHT:BLOCKED |  | 32 ms |
| 36 | [2, 9]→**LEFT** | [2, 5] | UP:fd=3 sp=139 dg=0  DOWN:fd=5 sp=139 dg=0  LEFT:fd=5 sp=139 dg=0  RIGHT:BLOCKED |  | 38 ms |
| 37 | [1, 9]→**UP** | [2, 5] | UP:fd=4 sp=139 dg=0  DOWN:fd=6 sp=139 dg=0  LEFT:fd=6 sp=139 dg=1  RIGHT:BLOCKED |  | 31 ms |
| 38 | [1, 8]→**UP** | [2, 5] | UP:fd=3 sp=139 dg=0  DOWN:BLOCKED  LEFT:fd=5 sp=139 dg=1  RIGHT:fd=3 sp=139 dg=1 |  | 31 ms |
| 39 | [1, 7]→**UP** | [2, 5] | UP:fd=2 sp=139 dg=0  DOWN:BLOCKED  LEFT:fd=4 sp=139 dg=1  RIGHT:fd=2 sp=139 dg=0 |  | 30 ms |
| 40 | [1, 6]→**UP** | [2, 5] | UP:fd=1 sp=139 dg=0  DOWN:BLOCKED  LEFT:fd=3 sp=139 dg=1  RIGHT:fd=1 sp=139 dg=0 |  | 32 ms |
| 41 | [1, 5]→**RIGHT** | [2, 5] | UP:fd=2 sp=139 dg=0  DOWN:BLOCKED  LEFT:fd=2 sp=139 dg=1  RIGHT:fd=0 sp=138 dg=0 | 🍃 吃到 | 393562 ms |
| 42 | [2, 5]→**RIGHT** | [7, 9] | UP:fd=10 sp=138 dg=0  DOWN:fd=8 sp=138 dg=1  LEFT:BLOCKED  RIGHT:fd=8 sp=138 dg=0 |  | 196137 ms |
| 43 | [3, 5]→**RIGHT** | [7, 9] | UP:fd=9 sp=138 dg=0  DOWN:fd=7 sp=138 dg=0  LEFT:BLOCKED  RIGHT:fd=7 sp=138 dg=0 |  | 32 ms |
| 44 | [4, 5]→**RIGHT** | [7, 9] | UP:fd=8 sp=138 dg=0  DOWN:fd=6 sp=138 dg=0  LEFT:BLOCKED  RIGHT:fd=6 sp=138 dg=0 |  | 35 ms |
| 45 | [5, 5]→**RIGHT** | [7, 9] | UP:fd=7 sp=138 dg=0  DOWN:fd=5 sp=138 dg=0  LEFT:BLOCKED  RIGHT:fd=5 sp=138 dg=0 |  | 32 ms |
| 46 | [6, 5]→**RIGHT** | [7, 9] | UP:fd=6 sp=138 dg=0  DOWN:fd=4 sp=138 dg=0  LEFT:BLOCKED  RIGHT:fd=4 sp=138 dg=0 |  | 31 ms |
| 47 | [7, 5]→**DOWN** | [7, 9] | UP:fd=5 sp=138 dg=0  DOWN:fd=3 sp=138 dg=0  LEFT:BLOCKED  RIGHT:fd=5 sp=138 dg=0 |  | 37 ms |
| 48 | [7, 6]→**DOWN** | [7, 9] | UP:BLOCKED  DOWN:fd=2 sp=138 dg=0  LEFT:fd=4 sp=138 dg=1  RIGHT:fd=4 sp=138 dg=0 |  | 33 ms |
| 49 | [7, 7]→**DOWN** | [7, 9] | UP:BLOCKED  DOWN:fd=1 sp=138 dg=0  LEFT:fd=3 sp=138 dg=0  RIGHT:fd=3 sp=138 dg=0 |  | 35 ms |
| 50 | [7, 8]→**DOWN** | [7, 9] | UP:BLOCKED  DOWN:fd=0 sp=137 dg=0  LEFT:fd=2 sp=138 dg=0  RIGHT:fd=2 sp=138 dg=0 | 🍃 吃到 | 33 ms |
| 51 | [7, 9]→**LEFT** | [3, 0] | UP:BLOCKED  DOWN:fd=14 sp=137 dg=0  LEFT:fd=12 sp=137 dg=0  RIGHT:fd=14 sp=137 dg=0 |  | 216330 ms |
| 52 | [6, 9]→**LEFT** | [3, 0] | UP:fd=11 sp=137 dg=1  DOWN:fd=13 sp=137 dg=0  LEFT:fd=11 sp=137 dg=0  RIGHT:BLOCKED |  | 38 ms |
| 53 | [5, 9]→**LEFT** | [3, 0] | UP:fd=10 sp=137 dg=0  DOWN:fd=12 sp=137 dg=0  LEFT:fd=10 sp=137 dg=0  RIGHT:BLOCKED |  | 40 ms |
| 54 | [4, 9]→**LEFT** | [3, 0] | UP:fd=9 sp=137 dg=0  DOWN:fd=11 sp=137 dg=0  LEFT:fd=9 sp=137 dg=0  RIGHT:BLOCKED |  | 35 ms |
| 55 | [3, 9]→**UP** | [3, 0] | UP:fd=8 sp=137 dg=0  DOWN:fd=10 sp=137 dg=0  LEFT:fd=10 sp=137 dg=0  RIGHT:BLOCKED |  | 40 ms |
| 56 | [3, 8]→**UP** | [3, 0] | UP:fd=7 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=9 sp=137 dg=0  RIGHT:fd=9 sp=137 dg=1 |  | 34 ms |
| 57 | [3, 7]→**UP** | [3, 0] | UP:fd=6 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=8 sp=137 dg=0  RIGHT:fd=8 sp=137 dg=0 |  | 54 ms |
| 58 | [3, 6]→**UP** | [3, 0] | UP:fd=5 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=7 sp=137 dg=0  RIGHT:fd=7 sp=137 dg=0 |  | 36 ms |
| 59 | [3, 5]→**UP** | [3, 0] | UP:fd=4 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=6 sp=137 dg=0  RIGHT:fd=6 sp=137 dg=0 |  | 35 ms |
| 60 | [3, 4]→**UP** | [3, 0] | UP:fd=3 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=5 sp=137 dg=0  RIGHT:fd=5 sp=137 dg=0 |  | 37 ms |
| 61 | [3, 3]→**UP** | [3, 0] | UP:fd=2 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=4 sp=137 dg=0  RIGHT:fd=4 sp=137 dg=0 |  | 35 ms |
| 62 | [3, 2]→**UP** | [3, 0] | UP:fd=1 sp=137 dg=0  DOWN:BLOCKED  LEFT:fd=3 sp=137 dg=0  RIGHT:fd=3 sp=137 dg=0 |  | 36 ms |
| 63 | [3, 1]→**UP** | [3, 0] | UP:fd=0 sp=136 dg=1  DOWN:BLOCKED  LEFT:fd=2 sp=137 dg=0  RIGHT:fd=2 sp=137 dg=0 | 🍃 吃到 | 35 ms |
| 64 | [3, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:BLOCKED  LEFT:fd=20 sp=136 dg=1  RIGHT:fd=18 sp=136 dg=1 |  | 198972 ms |
| 65 | [4, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=17 sp=136 dg=1  LEFT:BLOCKED  RIGHT:fd=17 sp=136 dg=1 |  | 37 ms |
| 66 | [5, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=16 sp=136 dg=0  LEFT:BLOCKED  RIGHT:fd=16 sp=136 dg=1 |  | 36 ms |
| 67 | [6, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=15 sp=136 dg=0  LEFT:BLOCKED  RIGHT:fd=15 sp=136 dg=1 |  | 35 ms |
| 68 | [7, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=14 sp=136 dg=0  LEFT:BLOCKED  RIGHT:fd=14 sp=136 dg=1 |  | 34 ms |
| 69 | [8, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=13 sp=136 dg=0  LEFT:BLOCKED  RIGHT:fd=13 sp=136 dg=1 |  | 36 ms |
| 70 | [9, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=12 sp=136 dg=0  LEFT:BLOCKED  RIGHT:fd=12 sp=136 dg=1 |  | 37 ms |
| 71 | [10, 0]→**RIGHT** | [11, 11] | UP:BLOCKED  DOWN:fd=11 sp=136 dg=0  LEFT:BLOCKED  RIGHT:fd=11 sp=136 dg=2 |  | 35 ms |
| 72 | [11, 0]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=10 sp=136 dg=1  LEFT:BLOCKED  RIGHT:BLOCKED |  | 33 ms |
| 73 | [11, 1]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=9 sp=136 dg=1  LEFT:fd=11 sp=136 dg=1  RIGHT:BLOCKED |  | 36 ms |
| 74 | [11, 2]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=8 sp=136 dg=1  LEFT:fd=10 sp=136 dg=0  RIGHT:BLOCKED |  | 35 ms |
| 75 | [11, 3]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=7 sp=136 dg=1  LEFT:fd=9 sp=136 dg=0  RIGHT:BLOCKED |  | 34 ms |
| 76 | [11, 4]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=6 sp=136 dg=1  LEFT:fd=8 sp=136 dg=0  RIGHT:BLOCKED |  | 35 ms |
| 77 | [11, 5]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=5 sp=136 dg=1  LEFT:fd=7 sp=136 dg=0  RIGHT:BLOCKED |  | 42 ms |
| 78 | [11, 6]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=4 sp=136 dg=1  LEFT:fd=6 sp=136 dg=0  RIGHT:BLOCKED |  | 37 ms |
| 79 | [11, 7]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=3 sp=136 dg=1  LEFT:fd=5 sp=136 dg=0  RIGHT:BLOCKED |  | 34 ms |
| 80 | [11, 8]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=2 sp=136 dg=1  LEFT:fd=4 sp=136 dg=0  RIGHT:BLOCKED |  | 36 ms |
| 81 | [11, 9]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=1 sp=136 dg=1  LEFT:fd=3 sp=136 dg=0  RIGHT:BLOCKED |  | 34 ms |
| 82 | [11, 10]→**DOWN** | [11, 11] | UP:BLOCKED  DOWN:fd=0 sp=135 dg=2  LEFT:fd=2 sp=136 dg=0  RIGHT:BLOCKED | 🍃 吃到 | 32 ms |
| 83 | [11, 11]→**DOWN** 💥 | [6, 6] | UP:BLOCKED  DOWN:BLOCKED  LEFT:fd=9 sp=135 dg=1  RIGHT:BLOCKED | 撞死（墙/身体） | — |