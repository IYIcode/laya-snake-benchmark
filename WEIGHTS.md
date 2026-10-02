# 微调权重（GitHub Release：`weights-v1`）

**下载页**：<https://github.com/IYIcode/laya-snake-benchmark/releases/tag/weights-v1>

> ⚠️ `github.com` 在中国大陆常被阻断，下载资产需要自备代理。仓库里的档案与页面已发布到
> GitHub Pages，可直接在线体验，无需权重。

权重没放进 Git 仓库（单文件 1.57GB，超过 GitHub 的 100MB 限制），而是作为 **Release 资产**发布。

## 一、资产清单

| 资产 | 体积 | 说明 |
|---|---|---|
| `laya_snake_ft__model.safetensors` | 1.57 GB | 监督微调（SFT）基座：ModernBERT-large 编码器 + 2 层决策头 |
| `laya_snake_v2_gen5__model.safetensors` | 1.57 GB | 第 5 代：**纯强化学习（REINFORCE，无老师）**，以 gen3 为起点 |
| `laya_snake_v3_grid__model.safetensors` | 1.57 GB | 网格版：直接吃全盘 0/1/2/3 数字阵的实验 |
| `laya_snake_v2_gen4__model.safetensors` | 1.57 GB | 第 4 代（残局数据实验，未晋升） |
| `laya_snake_v2_gen3__model.safetensors` | 1.57 GB | 第 3 代：**champion**（蒸馏自手写 BFS 老师） |
| `laya_snake_v2_gen2__model.safetensors` | 1.57 GB | 第 2 代 |
| `laya_snake_v2_gen1__model.safetensors` | 1.57 GB | 第 1 代（基线） |
| `checkpoints-configs.zip` | 4.5 MB | **所有 checkpoint 的非权重文件**（34 个）：`encoder/config.json`、`rl_agent_config.json`、`evolution_meta.json`、`tokenizer/tokenizer.json` 等 |

权重是 **fp32**（421M 参数 ≈ 1.57GB）；桥接服务用 bf16 加载时显存约 1GB 级别。

## 二、各代成绩（来自各自的 `evolution_meta.json`）

| checkpoint | 代次 | 成绩（食物数/局） | 备注 |
|---|---|---|---|
| `laya_snake_v2_gen1` | gen1 | 17.0 | 同配方同老师的对照组起点 |
| `laya_snake_v2_gen2` | gen2 | — | 老师均值 54.67 |
| `laya_snake_v2_gen3` | gen3 | **32.125**（champion） | 蒸馏阶段最佳 |
| `laya_snake_v2_gen4` | gen4 | 27.5（4 局） | "deep 残局数据反而变差，未晋升" |
| `laya_snake_v2_gen5` | gen5-rl | **best_mean 40.75** | 纯 RL（+1.0/食物，-2.0/撞死），无老师 |
| `laya_snake_v3_grid` | v3 网格版 | 28.125 | 全盘 0123 矩阵输入实验；对照 gen1=17.0 |
| `laya_snake_ft` | SFT 基座 | — | 后续所有代的起点 |

> 注意口径：这些是**食物数/局**（10 局或 4 局均分），和视频里小抄阶梯那一套
> （36 / 39 / 43.1 / 48.8 / 59.8，10 局均值，见 `_tune_runs/`）不是同一组实验——
> 那一套是"程序算特征 + 微调"的配方对比，用的是另一条训练线。

## 三、怎么组装成一个可加载的 checkpoint

```bash
unzip checkpoints-configs.zip                                  # 得到 7 个目录的配置
mv laya_snake_v2_gen5__model.safetensors laya_snake_v2_gen5/model.safetensors
```

装好后布局（与 `laya_bridge.py` 的自动发现逻辑一致）：

```
laya_snake_v2_gen5/
├── model.safetensors              ← 从 Release 下载后改名
├── encoder/config.json
├── rl_agent_config.json
├── evolution_meta.json
└── tokenizer/
    ├── tokenizer.json
    └── tokenizer_config.json
```

## 四、加载方式

本仓库的桥接脚本会自动扫描"含 `model.safetensors` 的目录"并挂载：

```bash
python laya_bridge.py            # 见 laya_bridge.py 第 62–113 行的模型发现逻辑
```

手动加载的关键片段（摘自 `_nb_train.py`）：

```python
from transformers import AutoTokenizer
from safetensors.torch import load_file
tok = AutoTokenizer.from_pretrained(os.path.join(model_dir, "tokenizer"))
weights = load_file(os.path.join(model_dir, "model.safetensors"))
model.load_state_dict(weights, strict=True)
```

- 编码器底座：`answerdotai/ModernBERT-large`（见 `rl_agent_config.json` 的 `encoder` 字段）
- 结构：`max_len 512`、`head_max_len 192`、`max_prefixes 6`、2 层决策头、bf16 推理
- 原始模型：`convaiinnovations/laya`（本项目是在它基础上微调的，请一并遵循其许可）

## 五、没传什么

- `_rlcd/`（约 4GB）：训练过程的中间 run（含 smoke/checkpoint_latest），非最终产物
- `_ppt_video*/`、`_ppt_audio*/`：视频流水线中间素材，可由脚本重新生成
- 含本机路径的运行期日志

需要以上任何一项，开 issue 即可。
