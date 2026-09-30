# -*- coding: utf-8 -*-
"""生成 3 分钟视频的配音：
   1) q01..q09 —— 原有 9 段话术，语速由 +10% 提到 +20%（压缩总时长，给新段腾时间）
   2) L00..L06 —— 新增“五路贪吃蛇实况”段落的逐句旁白（每句对应一条赛道，便于画面聚光灯精确对齐）
"""
import asyncio, pathlib, json, subprocess
import edge_tts

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_ppt_audio4"
LANE = OUT / "lane"
OUT.mkdir(exist_ok=True)
LANE.mkdir(exist_ok=True)
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+20%"

# ── 原有 9 段（文案与 _dev/make_audio3.py 完全一致，只改语速） ──
SCRIPT = [
(1, 1, "大家好。今天用一局贪吃蛇，回答一个话题：Jev的平替、开源决策模型Laya，到底能不能干活？注意，今天不念宣传稿，屏幕上每个数字，背后都是一局局真跑出来的日志档案。"),
(2, 4, "先认识两位主角。Jev，闭源商业决策模型，官方接口实测延迟七十到五百毫秒一次。Laya，开源平替，四百二十一M参数的编码器，输入状态加选项，直接输出动作概率。我们本地实测二十七到三十毫秒一次，比正主还快，大约一GB显存就能跑。"),
(3, 6, "考场：十二乘十二贪吃蛇。第一，天花板客观，全盘填满就是一百四十一分，没有争议空间；第二，绝对公平，同一个随机种子，所有方案吃到的食物序列逐格相同；第三，红线：只喂棋盘事实和规则数字，绝不把该走哪透给模型。"),
(4, 7, "六级阶梯一眼看完：零样本，零分；喂特征加初步微调，十四点八；小抄里加入预测，一路爬到五十九点八，反超五十三分的手写算法老师；裸棋盘限时一小时训练，四十四点二；纯代码环算法，直接打满一百四十一；提示词加持下的训练模型，也摸到了一百四十一。"),
(5, 10, "最残酷的对比在这里：训练一个裸棋盘模型，压成一小时的妥协版，只有四十四点二分；而几十行代码写出的环保险算法，当场一百四十一通关，十二个种子全部通关，不要显卡、不要数据。教训：对规则明确的专用问题，训练远比写算法贵。"),
(6, 11, "但模型也有自己的高光：契约一字不改、零掩码、零代码代答，只在输入里多给一个数字，跨身计数。训练过的模型自己收敛行为：九局赢四局通关，最好一局四千五百九十二步零违规。同一份提示词给未训练的底座呢？零分，第二步就撞死。请记住：提示词是能力的开关，不是能力本身。"),
(7, 15, "通关不等于胜利，四个问题藏不住：它学会的是读小抄，不是看棋盘；特征全靠程序算；像素对它毫无意义；训练成本高。那决策模型凭什么活着？就凭两个字：通用。算法换游戏就重来，模型换数据不换代码。"),
(8, 16, "结论一句话：Laya训练后能干活，但要摆对位置：程序管感知和兜底，模型管高频选择。落地举个真实例子，对战游戏公屏刷屏，每条消息三十毫秒的放行屏蔽判断，按频道微调就够用。该屏蔽的那句台词怎么说来着——打仗呢，这不是乱来嘛！"),
(9, 17, "最后，这份报告背后：几百局真跑、一整天的结对，全部由Qoder完成，而且指令是在手机上发的。欢迎扫码，或者点屏幕上的邀请链接，注册试用Qoder。谢谢大家。"),
]

# ── 新增：五路贪吃蛇实况（L00 开场 + L01..L05 逐道点名 + L06 收尾） ──
from lane_config import PIECES as LANE_SCRIPT, LEAD, PAUSE, TAIL, FPS

async def gen(text, fn):
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(fn))

def dur(fn):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(fn)], capture_output=True, text=True)
    return float(out.stdout.strip())

async def main():
    jobs = []
    for n, _slide, t in SCRIPT:
        jobs.append(gen(t, OUT / f"q{n:02d}.mp3"))
    for name, _lane, t in LANE_SCRIPT:
        jobs.append(gen(t, LANE / f"{name}.mp3"))
    await asyncio.gather(*jobs)

asyncio.run(main())

total = 0.0
print("── 原有 9 段（+20%） ──")
for n, _slide, _t in SCRIPT:
    d = dur(OUT / f"q{n:02d}.mp3")
    total += d
    print(f"q{n:02d}  {d:6.2f}s")
sum9 = total
print(f"小计 {sum9:.2f}s")
print("── 五路赛道旁白（+20%） ──")
pieces, t = [], LEAD
for name, lane, _t in LANE_SCRIPT:
    d = dur(LANE / f"{name}.mp3")
    pieces.append({"id": name, "lane": lane, "dur": round(d, 3), "start": round(t, 3), "end": round(t + d, 3)})
    t += d + PAUSE
lane_total = t - LEAD - PAUSE
timeline = {"lead": LEAD, "pause": PAUSE, "tail": TAIL, "fps": FPS,
            "pieces": pieces, "total": round(t + TAIL, 3)}
for p in pieces:
    print(f"{p['id']}  {p['dur']:6.2f}s  [{p['start']:6.2f} → {p['end']:6.2f}]")
json.dump(timeline, open(ROOT / "_dev" / "lane_timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"q": {f"q{n:02d}": round(dur(OUT / f"q{n:02d}.mp3"), 3) for n, _, _ in SCRIPT}},
          open(ROOT / "_dev" / "audio4_durations.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"五路旁白小计 {lane_total:.2f}s → 该段总长 {timeline['total']:.2f}s")
print(f"预计全片 ≈ {sum9 + lane_total + 0.25*10 + 0.5:.2f}s")
print("完成")
