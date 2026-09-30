# 逐条验证清单

本文件把视频/PPT 里的每个数字，对应到仓库里的**原始档案**或**可运行代码**，并给出自查命令。
证据强度分三档：

- 🟢 **原始档案**：仓库里有逐局/逐手记录，可复算
- 🟡 **可运行实现**：没有归档结果，但代码/页面可以当场跑出来
- 🔴 **仅有汇总记录**：结果来自训练或评测日志，未随仓库打包（给出文件名，需要可开 issue 索取）

---

## 1. 零样本：23 局全 0 分 🟢

```bash
python -c "import json;d=json.load(open('_prompt_ab.json',encoding='utf-8'));[print(x['name'],'mean_food=',x['mean_food'],'causes=',x['causes'],'compliant=',x['compliant']) for x in d]"
```

存档为 6 种提示词写法各 6 局。**所有写法的 `mean_food` 都是 0.0**，死因在撞墙/咬身之间。
另见 `_prompt_base_rescue.json`（"把答案透给它"的对照，最好也只有 5.5 分）。

---

## 2. 小抄阶梯：36.0 → 39.0 → 43.1 → 48.8 → 59.8 🟢

```bash
python _dev/summarize_tune_runs.py
```

`_tune_runs/*.json` 每个文件是一级配方、10 局、固定种子 3001–3010，含逐局 `steps`/`food`/`cause`/
`analysis.death_labels` 以及逐手 `traj`：

| 文件 | 配方 | mean |
|---|---|---|
| `baseline.json` | 三特征基线（距离/空间/危险） | **36.0** |
| `trap.json` | + 死口袋警告 | **39.0** |
| `fdpen.json` | + 食物距离惩罚 | **43.1** |
| `look2.json` | + 两步洪水视野（观众提的点子） | **48.8** |
| `fdpen6.json` | 终版配方 | **59.8** |

同目录另有 `fdpen2/3/4/5.json`（44.1 / 43.1 / 36.1 / 46.8）、`legend.json`（35.5）、`traplegend.json`（37.6）等中间尝试。
**手写 BFS 老师 53 分**为同种子对照，见 `_tune_runs/legend.json` 的注释与 `_prompt_to_win.json` 对照说明。

---

## 3. 裸棋盘限时训练 44.2 🔴

标为 🔴：`44.2` 来自 1 小时 SFT 的评测日志，**日志未随仓库打包**（含本机路径，已列入 `.gitignore`）。
训练脚本在本仓库，可自行复跑：`laya_finetune_snake*.py`、`_sft_fast.py`、`_nb_train.py`、`_dev/make_audio4.py` 之外的训练链见 `_doc_finetune.md`。
需要原始评测日志可以开 issue。

---

## 4. 环保险算法 141、12 个种子全通关 🟡

不依赖任何模型，**当场可跑**：

```bash
python _rlcd_snake.py            # 或直接打开 laya-snake-cockpit.html 的 ④ 号道看它真跑
```

环不等式实现见 `_rlcd_cycle.py`（`loopSafe` / `loopAhead` / `cycOf`），
与页面 JS 版本逐字对齐；`_cycle_port_cases.json` 是 40 个跨语言一致性用例（Python ↔ JS 逐字节对齐）。

---

## 5. 模型 + 跨身计数：141 通关 🟢（但口径要修正）

```bash
python -c "import json;print(json.load(open('_jumpfood_1002.json',encoding='utf-8')))"
```

`_jumpfood_1002.json`：seed 1002，**141 格吃满、4592 步**、`obey_rate: 1.0`、**`jumps: 2`**。

⚠️ **已知口径问题（务必看）**

1. **"全程零违规"不准确**。档案里 `jumps: 2` —— 这一局有 2 步跨身。
   `obey_rate: 1.0` 是 `round(n_obey/n_step, 3)` 的结果：2/4593 ≈ 0.00044，四舍五入后就是 1.0。
   正确表述：「4592 步通关，环不等式遵守率 **99.96%**（4592 步中 2 步跨身）」。
   视频/PPT 那一句"最好一局 4592 步全程零违规"应据此更正。
2. `_prompt_to_win.json` 里 seed 1002 是 **5166 步** —— 那是**另一个配方**（裸公式自己算）的同一局面，
   与 4592 不矛盾，但引用时要说清是哪个配方。
3. ③ 号道演示的走位是**示意**：seed1002 该局逐手方向当年只录了计数、没留方向档，
   页面里的蛇是按环保险策略现场规划来吃那 141 格实录食物的。食物坐标/顺序/起点/首食是档案原件，
   **走位不是模型当年的脚步**（页面已用金色标签标注）。

---

## 6. 我本人（通用 Agent）三个赛制 🟢

```bash
python -c "
import json,glob
for f in sorted(glob.glob('_me_ledger_result*.json')):
    print(f, json.load(open(f,encoding='utf-8')))
"
```

| 档案 | 结果 | 赛制 |
|---|---|---|
| `_me_ledger_result.json` | 141 分 / **4370 步** / 351 秒 / **0 跨身** | 不限时，一段一断 |
| `_me_ledger_result_600s.json` | 26 分 / 630 步 / 600 秒 | 一段一断，10 分钟限时 |
| `_me_ledger_result_single92.json` | 92 分 / 2173 步 / 451 秒 | 单趟食流口径（该口径上限 92） |

逐手回放数据：`_myrun_data.json`（4370 手方向 + 141 段原始载荷）、`_myrun_data_single92.json`；
原始帧日志：`_me_ledger_auto_frames*.jsonl`。
"一手一断 2 分 @42 手"见 `_me_ledger_log_600s.json`（该局第 6 手复刻了模型的死法）。

---

## 7. 驾驶舱 ② 号道：400 手真实桥接日志 🟢

```bash
python -c "import json;d=json.load(open('_cockpit_replay.json',encoding='utf-8'));print(len(d['frames']),'手 可重建蛇身');print(d['segmeta']);print(d['src'])"
```

- 原始日志：`_recent_log.json`（2026-09-26 v5 实录）
- 重建后：`_cockpit_replay.json`（290 手可整段重建蛇身；每手含 `crit` 小抄串、`probs`/`raw` 概率、`choice`、`ms`）
- 页面 `laya-snake-cockpit.html` 的 ② 号道逐手回放这份档案

---

## 8. 延迟 27–30ms/次（对比 Jev 官方 70–500ms） 🟡

```bash
python bench_http.py        # 本地桥接实测
python bench_latency.py
```

结果留档在 `bench_out.txt` / `bench_final.txt` / `bench_after.txt`。
`_evidence.json` 里还有桥接自检（模型版本、warm_ms 200–250ms 的首帧、以及若干真实决策样本）。

---

## 9. 视频与 PPT 的一致性 🟢

- 三分钟成片：`laya-ppt-3分钟.mp4`（3:17.1）—— 第 7 段"五路选手同台实况"由 `_dev/render_lane.py` 逐帧渲染，
  ⑤ 道用的是 `_myrun_data.json`，② 道用的是 `_cockpit_replay.json`，③ 道的食物流用的是 `_jumpfood_1002.json`
- 渲染脚本可复跑，参数与页面速度一致（①②③④⑤ = 440/80/40/80/80 ms 每步，画面 1×）
- ⚠️ 画面速度说明：三段模型/算法道在视频里**不跑完 141**（1× 速度下 23 秒跑不完），
  面板里写的是**档案结论**（141），不是"画面刚跑出来的结果"。这是刻意的，避免用快进冒充正常速度。

---

## 10. 没做到的（照实写）

- **没有视觉能力**：截图、像素对它毫无意义，"眼睛"永远外接。
- **依赖程序算特征**：59.8 分里每个数字都是代码算好的；这也是整个决策模型范式的常态
  （Jev 的 Terraria 明星案例源码里，tile 地图从未进过模型——见外部仓库 TerraBlind）。
- **训练成本高**：裸棋盘要 17+ 小时 GPU，而环保险算法几十行当场 141。
