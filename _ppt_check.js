
function fit(){const s=Math.min(innerWidth/1280,innerHeight/720);
 const st=document.getElementById('stage');st.style.transform='scale('+s+')';st.style.transformOrigin='center center';}
addEventListener('resize',fit);fit();

const S=[];
function slide(sec,body,note,cls){S.push({sec,body,note,cls:cls||''});}

/* ── 1 封面 ── */
slide('总览',`
<div class="kicker fx" style="--d:.05s">A I 实 测 报 告</div>
<h1 class="fx" style="--d:.2s">Jev 的平替 <span class="hl">Laya</span>，能否干活？</h1>
<div class="q fx" style="--d:.4s">—— 一条贪吃蛇，测出决策小模型的能与不能</div>
<div class="meta fx" style="--d:.6s">convaiinnovations/laya · 421M · 本地部署 · 全部数字来自真实对局日志 · 实测由 Qoder 完成</div>
<div class="fx" style="--d:.9s;margin-top:34px" id="coverSnake"></div>`,'大家好。今天讲一个 2026 年 9 月很火的话题：Jev——"不聊天、直接做决策"的决策模型，爆火三天之后，开源的 Laya 号称要把它的桌子掀了。我们要回答的问题只有一个：<b>Jev 的平替 Laya，能不能真干活？</b>不念宣传稿，用几百局本地真实对局说话。','cover');

/* ── 2 三问 ── */
slide('总览',`
<h2><span class="bar"></span>三个问题，一条蛇回答</h2>
<div class="cards grow" style="grid-template-columns:1fr 1fr 1fr;align-content:center">
  <div class="card fp" style="--d:.15s"><div class="big y">问 1</div><p style="font-size:22px;font-weight:700;margin:8px 0">什么是 Laya？</p><p>不生成文字、不聊天——输入状态+选项，直接输出动作概率的决策小模型。</p></div>
  <div class="card fp" style="--d:.45s"><div class="big y">问 2</div><p style="font-size:22px;font-weight:700;margin:8px 0">Laya 能干什么？</p><p>与 Jev 同范式的实时决策：比写死的算法通用，比大模型快、省、可端侧。</p></div>
  <div class="card fp" style="--d:.75s"><div class="big y">问 3</div><p style="font-size:22px;font-weight:700;margin:8px 0">实际体验怎么样？</p><p>真实部署、真实训练、真实对局——每个数字都有档案可查。</p></div>
</div>`,'整场汇报围绕三个问题：什么是 Laya；它能干什么；最后，我们亲手用出来的体验到底怎么样。别小看一条贪吃蛇——这三个问题，它全能回答。');

/* ── 3 报告结构 ── */
slide('前言 · 背景',`
<h2><span class="bar"></span>按论文的规矩来</h2>
<div class="steps grow" style="justify-content:center">
  <div class="step fx" style="--d:.1s"><div class="ph">一 · 背景</div><div class="bd">Jev 爆火，Laya 自称"开源平替"——是真是假？</div><div class="res y">定调</div></div>
  <div class="step fx" style="--d:.25s"><div class="ph">二 · 方法</div><div class="bd">同台对比 + 贪吃蛇考场：零样本→喂特征→训练→提示词→纯算法，六级演进每步真跑</div><div class="res y">实测</div></div>
  <div class="step fx" style="--d:.4s"><div class="ph">三 · 结果</div><div class="bd">成绩阶梯 + Agent 人类选手对照赛（我亲自逐手玩）</div><div class="res y">数据</div></div>
  <div class="step fx" style="--d:.55s"><div class="ph">四 · 结论</div><div class="bd">暴露的问题 + 决策模型真正的价值位置 + 一个落地场景</div><div class="res y">判断</div></div>
</div>`,'方法上像论文一样：背景、方法、结果、结论。每页底部标了数据出处的档案文件名，任何一个数字你都可以要求回放原始日志。');

/* ── 4 Jev vs Laya ── */
slide('前言 · 背景',`
<h2><span class="bar"></span>两位主角</h2>
<div class="vs grow">
  <div class="card fx" style="--d:.1s"><h3>Jev <span class="tag">闭源 · 商业API</span></h3>
    <ul style="list-style:none;line-height:2.1;font-size:17px">
      <li>▪ TypeSafe AI 出品，非自回归并行推理</li>
      <li>▪ "快 193.6 倍"——对比的是<b>拿大模型当决策器</b></li>
      <li>▪ 官方 API 实测延迟 <b class="r">70–500ms</b> / 次</li>
      <li>▪ 明星案例打 Terraria：公开源码显示<b class="y">零训练</b>，程序包办一切感知</li>
    </ul></div>
  <div class="mid fp" style="--d:.4s">VS</div>
  <div class="card fx" style="--d:.55s"><h3>Laya <span class="tag">开源 · 本地部署</span></h3>
    <ul style="list-style:none;line-height:2.1;font-size:17px">
      <li>▪ ModernBERT 编码器 <b>421M</b>，HuggingFace 趋势榜第一</li>
      <li>▪ System-1 式选择题：四选项 → 四个概率</li>
      <li>▪ 部署需求 <b class="g">≈1GB 显存</b>，纯 CPU 也能跑</li>
      <li>▪ 本地实测延迟 <b class="g">27–30ms</b> / 次（热身 p50）</li>
    </ul></div>
</div>
<div class="fx" style="--d:.8s;font-size:15px;color:var(--dim);margin-top:6px">"Jev 才封神三天，开源 Laya 就把桌子掀了。" —— 社区语</div>`,'先认识两位主角。Jev：闭源商业 API，爆火三天，官方接口实测 70 到 500 毫秒一次。Laya：开源，HuggingFace 趋势榜第一，宣传语很狂——"Jev 封神三天，Laya 掀桌"。421M 参数，1GB 显存就能跑，CPU 也行，本地实测 27 到 30 毫秒。平替比原版还快？这是第一个待验证的点。');

/* ── 5 应用 ── */
slide('方法 · 实验',`
<h2><span class="bar"></span>决策模型不是玩具，这三类场景等着它</h2>
<div class="cards grow" style="grid-template-columns:1fr 1fr 1fr;align-content:center">
  <div class="card fx" style="--d:.1s"><h3>游戏 / 仿真</h3><p style="font-size:18px">MOBA 连招、RTS 微操、NPC 行为——一帧要问十几次，30ms 才坐得住主循环。</p></div>
  <div class="card fx" style="--d:.35s"><h3>实时内容过滤</h3><p style="font-size:18px">直播公屏、对战全频道：每条消息一次"放行 / 屏蔽"概率判断，不卡麦不上云。</p></div>
  <div class="card fx" style="--d:.6s"><h3>端侧控制</h3><p style="font-size:18px">无人机、机械臂、车机——1GB 显存甚至 CPU 的门槛，才叫"装得进去"。</p></div>
</div>
<div class="card fx" style="--d:.85s;margin-top:6px"><p><b class="y">范式洞察（读了 TerraBlind 开源源码之后）：</b>整个 Jev 流派——包括它的明星演示——都是<b>程序把世界算成小抄，模型在小抄里做选择题</b>。Tile 地图从未进过模型。我们后面所有实验，都在检验这个"选择题选手"本身。</p></div>`,'这类模型干什么用？三类：游戏仿真里一帧问十几次的决策；直播公屏、游戏全频道的实时过滤；还有装进无人机、机器人这种端侧设备。注意一个关键发现：我们把 Jev 打 Terraria 那个明星案例的开源源码逐行读了——tile 地图根本没进过模型，全是程序算好小抄让模型做选择题。所以后面所有实验，考的就是这个"选择题选手"本身有多强。');

/* ── 6 实验场 ── */
slide('方法 · 实验',`
<h2><span class="bar"></span>考场：12×12 贪吃蛇（左边的蛇正在环游，是活的）</h2>
<div id="miniWrap" class="grow">
  <div><canvas id="mini" width="300" height="300"></canvas>
  <p class="small" style="margin-top:8px" id="miniLbl">环保险算法实录：一步不越环</p></div>
  <div class="cards" style="grid-template-columns:1fr;flex:1;align-content:center">
    <div class="card fx" style="--d:.1s"><p><b class="y">天花板明确</b>：全盘 144 格 = <b>141 分通关</b>，没有争议空间</p></div>
    <div class="card fx" style="--d:.3s"><p><b class="y">绝对公平</b>：同一随机种子，所有方案吃到的食物序列逐格相同；死亡只认真因（撞墙/撞身/困死）</p></div>
    <div class="card fx" style="--d:.5s"><p><b class="y">契约红线</b>：只喂棋盘事实和规则数字，<b>绝不把"该走哪"透给模型</b></p></div>
    <div class="card fx" style="--d:.7s"><p class="small">参赛方案：未训练 Laya / 微调 Laya / 小抄特征 / 环算法 / 我（Agent 逐手）</p></div>
  </div>
</div>`,'考场是 12×12 贪吃蛇，左边这条蛇就是环保险算法在真跑，大家可以看它沿着外环一圈圈收网。规则三条：141 分满分没有争议空间；同种子同食物流，谁也别想挑软柿子；最后——红线——只许给模型看事实，不许把答案写在选项里。');

/* ── 7 阶梯总览 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>完整旅程：从 0 分到通关</h2>
<div class="vchart grow" style="gap:34px;padding-left:30px">
  <div class="vb"><b class="r">0分</b><i style="--h:4%;--d:.1s;background:linear-gradient(180deg,#ef5b5b,#7c2f2f)"></i><u>零样本<br>×23局</u></div>
  <div class="vb"><b>14.8</b><i style="--h:11%;--d:.3s"></i><u>喂特征<br>+初训</u></div>
  <div class="vb"><b>59.8</b><i style="--h:42%;--d:.5s"></i><u>特征加预测<br>反超老师</u></div>
  <div class="vb"><b>44.2</b><i style="--h:31%;--d:.7s;background:linear-gradient(180deg,#5aa7f0,#2c5a86)"></i><u>裸棋盘<br>1h限时训练</u></div>
  <div class="vb"><b class="g">141</b><i style="--h:100%;--d:.9s;background:linear-gradient(180deg,#3ecf8e,#1d7a52)"></i><u>纯代码<br>环算法</u></div>
  <div class="vb"><b class="y">141</b><i style="--h:100%;--d:1.1s"></i><u>提示词加持<br>模型通关</u></div>
  <div class="baseline" style="--t:46%"><span>BFS 手写老师 53</span></div>
</div>`,'先给一张全景图。零样本 0 分；喂特征加初训 14.8；特征里加预测后爬到 59.8，反超红色虚线——那是我们手写的 BFS 老师算法，53 分；裸棋盘只给数字阵列，限时一小时训练只有 44.2；纯代码环算法直接打满 141 根柱子；最后，提示词加持下的模型也摸到了满柱。接下来一级一级讲。');

/* ── 8 第0/1级 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>第 0 / 1 级：演示是假的，零样本是真不行</h2>
<div class="cards grow" style="grid-template-columns:1fr 1.15fr;align-content:center">
  <div class="card fx" style="--d:.1s"><h3>第 0 级 · Agent 演示PPT</h3>
    <p style="font-size:18px;line-height:1.9">第一版 11 场景网页 PPT 做得飞快——但逐帧检查发现：<b class="r">是动画，不是推理</b>。数字没跑出来，讲故事没底气。<br><span class="small">→ 于是真实部署 Laya，一切换实测。</span></p></div>
  <div class="card fx" style="--d:.35s"><h3>第 1 级 · 零样本 = 0 分 × 23 局</h3>
    <p class="small" style="margin-bottom:8px">未训练模型的四选项真实概率（桥接日志）——它没读棋盘，只复读"上"这个词：</p>
    <div class="probs">
      <div class="hbar" style="--d:.6s"><i style="--w:88%"></i><span>上 UP</span><em>0.39</em></div>
      <div class="hbar red" style="--d:.75s"><i style="--w:50%"></i><span>下</span><em>0.22</em></div>
      <div class="hbar red" style="--d:.9s"><i style="--w:43%"></i><span>左</span><em>0.19</em></div>
      <div class="hbar red" style="--d:1.05s"><i style="--w:43%"></i><span>右</span><em>0.19</em></div>
    </div>
    <p style="margin-top:10px;font-size:15.5px;color:var(--dim)">换 6 种提示词写法 + 给安全建议 + 直接把答案透给它：最好也只有 5.5 分，照样撞死。</p></div>
</div>`,'第 0 级，让 Agent 做演示 PPT，十分钟出一版，很快——但它是动画，不是推理。我们要求每一步都是真调用，于是真实部署。第 1 级给未训练的 Laya 直接上场：23 局，全部 0 分。看左边这组真实概率条：上 0.39，其他三个方向几乎均匀——它在复读语料里"UP"这个词的先验，棋盘一个字没读。我们甚至作弊把每步答案直接告诉它，最好也就 5.5 分——因为生存策略根本不在文字里。');

/* ── 9 第2级 特征阶梯 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>第 2 级：小抄越喂越准，分数越爬越高（10 局同种子 · 不限步）</h2>
<div class="vchart grow" style="gap:20px;padding-left:20px">
  <div class="vb"><b>36.0</b><i style="--h:60%;--d:.1s;background:linear-gradient(180deg,#5aa7f0,#2c5a86)"></i><u>三特征基线<br>距离/空间/危险</u></div>
  <div class="vb"><b>39.0</b><i style="--h:65%;--d:.3s;background:linear-gradient(180deg,#5aa7f0,#2c5a86)"></i><u>+死口袋警告</u></div>
  <div class="vb"><b>43.1</b><i style="--h:72%;--d:.5s;background:linear-gradient(180deg,#5aa7f0,#2c5a86)"></i><u>+食物距离惩罚</u></div>
  <div class="vb"><b>48.8</b><i style="--h:82%;--d:.7s;background:linear-gradient(180deg,#5aa7f0,#2c5a86)"></i><u>+两步洪水视野<br>（观众点子）</u></div>
  <div class="vb"><b class="g">59.8</b><i style="--h:100%;--d:.9s"></i><u>最终配方<br>fdpen6</u></div>
  <div class="baseline" style="--t:24%"><span>BFS 老师 53 —— 被反超</span></div>
</div>
<div class="fx" style="--d:1.2s;margin-top:4px;font-size:16px;color:#c6cfdd">早期微调 v1 只有 <b class="r">14.8</b>，死因：撞墙+咬身（日志：它给"撞墙"选项 0.19–0.24 的概率还照选）。另一条铁律：<b class="y">规则文字怎么改都逐字节无效，只有特征里的数字动得了它</b>。</div>`,'第 2 级：程序替它看棋盘，把离食距离、剩余空间、危险度算成小抄，再做微调。最早 v1 只有 14.8 分，死因很丢人——撞墙加咬身，日志里它给撞墙方向 0.2 概率还照选不误。之后小抄一轮轮加预测：口袋警告、食物距离惩罚、观众提的两步洪水视野……一路 36 → 39 → 43 → 49 → 59.8，最后一举反超了教它的手写算法老师，53 分。这里还挖出一条铁律：给模型的解释文字怎么改都是逐字节无效，只有特征里的数字能撬动它。');

/* ── 10 第3级 裸棋盘 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>第 3 级：能不能不要小抄，让它自己看懂棋盘？</h2>
<div class="vs grow">
  <div class="card fx" style="--d:.1s"><h3 class="plain">方案 A · 训练它读 0/1/2/3 数字阵</h3>
    <p style="font-size:18px;line-height:2">零样本读不懂（已证）→ 得训练<br>训练 ETA <b class="r">17–23 小时</b> GPU<br>压到 1 小时的妥协版只到 <b>44.2</b> 分<br><span class="small">困死 5/8 局，离通关还差 3 倍</span></p></div>
  <div class="mid fp" style="--d:.45s">vs</div>
  <div class="card fx" style="--d:.6s"><h3 class="plain">方案 B · 写"环保险"算法</h3>
    <p style="font-size:18px;line-height:2">几十行代码：每步只允许不跨过蛇身环序的方向<br>当场 <b class="g">141 通关</b><br>12 个种子 <b class="g">全部通关</b>，零困死<br><span class="small">不用 GPU、不用数据、不用等</span></p></div>
</div>
<div class="fx" style="--d:.85s;font-size:17px;text-align:center;color:#c6cfdd;margin-top:2px"><b class="y">教训：对这种"规则明确"的专用问题，训练成本远高于写算法——小抄不是我们的发明，是决策模型范式的常态。</b></div>`,'第 3 级：我们想净化范式——不给小抄，把 0/1/2/3 数字棋盘直接给它，训练它自己看懂。左边：训练 ETA 十七到二十三小时，压到一小时妥协版只有 44.2 分。右边：同一件事，我们写了几十行"环保险"算法——每步只允许不跨过蛇身环序的方向——当场 141，12 个种子全通关。这道对比题很残酷：规则明确的专业问题，算法比训练便宜太多。但这也说明小抄不是我们作弊，整个决策模型范式的常态就是程序管感知。');

/* ── 11 第4/5级 通关时刻 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>第 4 / 5 级：算法先通关，然后模型也通关了</h2>
<div class="cards grow" style="grid-template-columns:1fr 1fr;align-content:center">
  <div class="card fx" style="--d:.1s"><h3>纯代码 · 环保险</h3>
    <div class="big"><span class="cnt g" data-to="141">0</span> 分 <span class="tag win">12/12 种子通关</span></div>
    <p style="margin-top:10px">蛇长 144 填满全盘，零困死零撞死。第 6 页左边活着的演示就是它。</p></div>
  <div class="card fx" style="--d:.4s"><h3>模型 + 提示词「跨身计数」</h3>
    <div class="big"><span class="cnt y" data-to="141">0</span> 分 <span class="tag n">9 局 4 胜</span> <span class="tag win">加环掩码 4/4</span></div>
    <p style="margin-top:10px;font-size:16.5px">训练契约原文一字不动，state 里只多一个数字：<b>本局已经几次选择"跨过自己身体"的抄近路方向</b>。零掩码、零代码代答、100% 自主——最好一局 4592 步全程零违规。</p>
    <p class="small" style="margin-top:8px">未训练底模 + 同一份提示词：0 分，第 2 步撞死 → 提示词是能力的开关，不是能力本身。</p></div>
</div>`,'第 4 级，算法先通关：141 满柱，12 个种子全部做到。然后关键时刻来了——第 5 级，我们没改一行模型代码、没加掩码，只在输入里加了一个数字："本局你已经几次抄近路跨过自己身体"。目标：保持这个数为 0。训练过的模型自己读这个数字、自己收敛行为：9 局赢了 4 局，最好的一局四千五百多步全程零违规；再加环安全掩码则四局全通关。而同一份提示词给没训练的底模——0 分，第 2 步撞死。所以：提示词是能力的开关，得先训练把电路装上。');

/* ── 12 数据表 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>提示词战役全景（同契约 · 同 cycle 模型 · 同食流）</h2>
<table class="tbl grow" style="align-content:start">
<tr class="fx" style="--d:.05s"><th style="width:38%">方案</th><th>成绩</th><th>结局</th><th>一句话</th></tr>
<tr class="fx" style="--d:.15s"><td>未训练 + 6 种合规提示词</td><td class="r">0.0</td><td>撞墙@7</td><td>选择分布完全均匀</td></tr>
<tr class="fx" style="--d:.25s"><td>未训练 + 直接透答案</td><td class="r">5.5</td><td>撞身死</td><td>生存策略不在文字里</td></tr>
<tr class="fx" style="--d:.35s"><td>训练后 + 裸公式自己算</td><td>37 / 73 / 29</td><td>饿死转圈</td><td>98% 遵守，2% 违例即入死区</td></tr>
<tr class="fx" style="--d:.45s"><td>训练后 + 5 种指令文字改写</td><td class="r">逐字节不变</td><td>—</td><td>文字彻底惰性</td></tr>
<tr class="fx" style="--d:.55s"><td>训练后 + 跨身计数（零掩码）</td><td class="y">9 局 4 胜通关141</td><td>最好局零违规</td><td>纯提示词天花板≈50%</td></tr>
<tr class="fx" style="--d:.65s"><td>训练后 + 环安全前瞻掩码</td><td class="g">4/4 通关 141</td><td>🏆</td><td>半数步仍有≥2合法方向，决策归模型</td></tr>
</table>`,'这张表是提示词战役的全景，可以慢慢看。左半边三次证明文字没用：未训练的怎么写提示词都是 0，透答案也只有 5.5，训练后的改指令文字输出逐字节不变。右半边两次证明数字有用：加"跨身计数"一个数字，零掩码 9 局 4 胜通关；加环安全掩码 4/4 稳定。记住这页的标题句：提示词是开关，训练才是电路。');

/* ── 13 Agent 对照 ── */
slide('结果 · 实测数据',`
<h2><span class="bar"></span>加赛：我（通用 Agent）亲自下场，同契约同种子</h2>
<div class="steps grow" style="justify-content:flex-start">
  <div class="step fx bad" style="--d:.1s"><div class="ph">一手一断<br>10 分钟</div><div class="bd">每步等我下指令，单程约 <b>14 秒</b>。第 6 手不读小抄按惯性作答，当场复刻模型的死法。</div><div class="res r">2 分 @42手</div></div>
  <div class="step fx" style="--d:.3s"><div class="ph">一段一断<br>10 分钟</div><div class="bd">"作弊"一次：让我一口气规划一条链路由引擎执行。被决策次数预算卡死，不是策略差。</div><div class="res">26 分 @630步</div></div>
  <div class="step fx good" style="--d:.5s"><div class="ph">不限时</div><div class="bd">放开时限吃满环形口径全盘，全程 <b>0 跨身</b>，网页可逐手回放。</div><div class="res g">141 分 / 4370步 / 351秒</div></div>
</div>
<div class="fx" style="--d:.75s;margin-top:8px">
  <div class="hbar green" style="--d:.9s"><i style="--w:14%"></i><span>Laya 每手 27–30ms</span><em>1 手</em></div>
  <div class="hbar red" style="--d:1.05s"><i style="--w:96%"></i><span>我逐手 ≈14,000ms —— 同样的局我要跑 17 小时</span><em>≈500×</em></div>
</div>`,'最后加赛一场：不借任何模型，我——一个通用 Agent——按同一份契约亲自下场。一手一断，每手 14 秒，10 分钟只走 42 手拿 2 分，第 6 手的死法跟模型一模一样：不读数字、按惯性答。"作弊"成一次规划一条链，10 分钟 26 分。放开时限，351 秒 141 分全盘通关、零犯规。但同样这个成果，Laya 是每手 27 毫秒拿下的，快大约 500 倍——通才做得到，但高频任务根本不该用它。');

/* ── 14 暴露的问题 ── */
slide('讨论 · 问题',`
<h2><span class="bar"></span>通关了，但四个问题藏不住</h2>
<div class="cards grow" style="grid-template-columns:1fr 1fr;align-content:center">
  <div class="card fx" style="--d:.1s"><h3>① 棋盘感知有缺陷</h3><p style="font-size:17px">0/1/2/3 数字阵 23 局全 0 分。<b>它不是看懂了棋盘，是学会了读小抄。</b></p></div>
  <div class="card fx" style="--d:.25s"><h3>② 依赖程序算特征</h3><p style="font-size:17px">59.8 分里距离/空间/危险度全是代码算的——Jev 明星案例的源码同样包办感知，<b>这是范式常态</b>。</p></div>
  <div class="card fx" style="--d:.4s"><h3>③ 无法视觉识别</h3><p style="font-size:17px">截图、像素对它毫无意义，"眼睛"永远外接。</p></div>
  <div class="card fx" style="--d:.55s"><h3>④ 训练成本高</h3><p style="font-size:17px">裸棋盘要 17+ 小时 GPU；环保险算法几十行当场 141。<b>很多专用问题，算法就是更划算。</b></p></div>
</div>
<div class="card fx" style="--d:.75s"><p style="font-size:17.5px"><b class="y">那它凭什么活着？——通用性。</b>算法一事一写，换游戏就重写；决策模型换数据不换代码，拿来即用，输出自带概率、可设置信度闸门。<b>普及靠泛用，不靠单项冠军。</b></p></div>`,'但通关不等于胜利，四个问题藏不住：一，棋盘感知有缺陷，它学会的是读小抄不是看棋盘；二，高度依赖程序算特征——公允地说，Jev 的案例也是程序包办感知，这是范式常态；三，视觉完全不行；四，训练成本远高于写算法。那决策模型凭什么活着？通用性：算法一事一写，模型换数据不换代码，拿来即用，输出自带概率还能设闸门。普及靠泛用，不靠单项冠军。');

/* ── 15 结论 ── */
slide('结论',`
<h2><span class="bar"></span>结论：能干活——但要摆对位置</h2>
<div class="cards grow" style="grid-template-columns:1fr 1fr 1fr;align-content:center">
  <div class="card fx" style="--d:.1s"><h3 class="g">它能干</h3><p style="font-size:17.5px">训练后做<b>专业事</b>：吃透契约、反超老师（59.8&gt;53）、提示词加持通关 141。快 30ms、省 1GB 显存、可端侧。</p></div>
  <div class="card fx" style="--d:.3s"><h3 class="r">它不能</h3><p style="font-size:17.5px">裸感知不行、通用理解不行：<b>通用性不如 Jev</b>（人家闭源大训练量），智力就是选择题水平。</p></div>
  <div class="card fx" style="--d:.5s"><h3 class="y">怎么用</h3><p style="font-size:17.5px"><b>程序管感知兜底，模型管高频选择</b>——选专业、高频、离线、省成本的场景。</p></div>
</div>
<div class="card fx" style="--d:.7s;margin-top:2px"><h3 class="plain">落地例子：Wardogs 公屏消息过滤</h3>
<p style="font-size:17px">对战全频道刷屏，卖挂的混进指挥信息。大模型上云又慢又贵；Laya 本地部署，每条消息一次 30ms"放行/屏蔽"判断，按频道微调就够用。</p>
<div class="quote" style="margin-top:10px" id="wq">"打仗呢，这不是乱来嘛！"</div></div>`,'结论一句话：Laya 训练后能干活，但要摆对位置——程序管感知和兜底，模型管高频选择。它能干专业事：反超教学算法、提示词加持下通关；它不能：裸感知和通用理解都不行，通用性不如 Jev。给一个真实落地例子：Wardogs 对战游戏公屏，卖挂刷屏混在指挥信息里，人工管不过来、大模型上云又慢又贵——本地小模型每条消息 30 毫秒判断一次，按频道微调就够用。该屏蔽的那句怎么说来着——"打仗呢，这不是乱来嘛！"');

/* ── 16 Qoder ── */
slide('结语',`
<h2><span class="bar"></span>这套报告背后：全部实测由 Qoder 完成</h2>
<div class="bub grow" style="justify-content:center">
  <div class="b1 fp" style="--d:.1s">"不限时，你跑，然后记录好，我后面做视频。"</div>
  <div class="b2 fx" style="--d:.45s">→ 挂机 351 秒，<span class="ok">141 分 / 4370 步 / 0 跨身真通关</span>，逐手档案全部落盘 ✅</div>
  <div class="b1 fp" style="--d:.75s">"不是，我看到没有吃满 144，你怎么能说通关了？"</div>
  <div class="b2 fx" style="--d:1.05s">→ 它认账：那是食流口径问题。换成环形口径重跑，<span class="ok">真·全盘吃满</span>，页面加上口径徽章 ✅</div>
  <div class="b1 fp" style="--d:1.3s">"现在不要开任何 laya 模型，我只要你来跑。"</div>
  <div class="b2 fx" style="--d:1.6s">→ 桥接即停、五模型全卸，之后每一局都是它<b>零模型</b>当面跑出来的 ✅ <span class="small">（手机上发的这几条）</span></div>
</div>
<div class="fx" style="--d:1.85s;font-size:21px;margin-top:6px">欢迎扫码或点链接注册试用 Qoder —— 让我能多蹬一会儿 🛞</div>
<div class="fx" style="--d:1.95s;font-size:15px;margin-top:2px"><a href="https://qoder.cn/activities?referral_code=Ykkr49CgiCQpI8fijiiXU4MdTVt8Z4uX" style="color:#5aa7f0;font-family:Consolas,monospace;text-decoration:none;word-break:break-all">https://qoder.cn/activities?referral_code=Ykkr49CgiCQpI8fijiiXU4MdTVt8Z4uX</a></div>
<div id="shotStrip"></div>`,'最后说说工具本身。这套报告背后几百局真跑、几万步落盘，全部是我和 Qoder 完成的。给大家看三条我的真实指令：“不限时你跑，记录好我做视频”，它挂机 351 秒跑出真通关局；我抓它“没吃满 144 凭什么说通关”，它认账、改口径、重跑；我说“不要开任何模型，你来跑”，它把 GPU 桥全停，之后每一局都零模型当面跑。而且这几条指令是我在手机上发的——随时随地。欢迎扫码，或者点屏幕上的邀请链接，注册试用 Qoder，让我能多蹬一会儿。');

/* ── 渲染 ── */
const deck=document.getElementById('deck'),dots=document.getElementById('dots');
S.forEach((s,i)=>{
  const d=document.createElement('div');d.className='slide '+s.cls;
  d.innerHTML=`<div class="src">数据出处：${['—','报告结构见下','各实测档案见对应页脚脚注','bench_http.py / Jev 官方 API','TerraBlind 开源仓库源码','laya-snake-theater.html 同台实测','_tune_runs/*.json · _prompt_*.json','零样本评测 23 局 · _prompt_ab.json','_tune_runs/*.json 种子3001–3010','1h-SFT eval_cycle.txt · 环保险 12/12','_prompt_to_win.json · _prompt_formula_hint*.json','_prompt_ab.json 等全部档案','_me_ledger_result*.json · _myrun_data.json','前页档案','阶梯数据汇总','本会话真实指令（jsonl 可查）'][i]||''}</div>`+s.body;
  deck.appendChild(d);
  const o=document.createElement('i');if(i===0)o.classList.add('on');o.onclick=()=>go(i);dots.appendChild(o);
});
let cur=0,noteOn=false;
function go(i){if(i<0||i>=S.length)return;
 deck.children[cur].classList.remove('on');dots.children[cur].classList.remove('on');
 cur=i;const el=deck.children[cur];
 el.classList.remove('on');void el.offsetWidth;el.classList.add('on');
 dots.children[cur].classList.add('on');
 document.getElementById('secLbl').textContent=S[cur].sec;
 document.getElementById('pageNo').textContent=(cur+1)+' / '+S.length;
 document.getElementById('prog').style.width=((cur+1)/S.length*100)+'%';
 document.getElementById('noteTxt').innerHTML=S[cur].note;
 counters(el);typer(el);}
function counters(el){el.querySelectorAll('.cnt').forEach(c=>{
 const to=+c.dataset.to,t0=performance.now();
 function tick(t){const k=Math.min(1,(t-t0)/1300),e=1-Math.pow(1-k,3);
  c.textContent=Math.round(to*e);if(k<1)requestAnimationFrame(tick);}
 c.textContent='0';requestAnimationFrame(tick);});}
let tyTimer=null;
function typer(el){clearInterval(tyTimer);const q=el.querySelector('#wq');if(!q)return;
 const txt=q.dataset.full||q.textContent;q.dataset.full=txt;q.textContent='';let i=0;
 tyTimer=setInterval(()=>{q.textContent=txt.slice(0,++i)+'▌';if(i>=txt.length){clearInterval(tyTimer);q.textContent=txt;}},55);}
document.getElementById('bPrev').onclick=()=>go(cur-1);
document.getElementById('bNext').onclick=()=>go(cur+1);
document.getElementById('bNote').onclick=()=>{noteOn=!noteOn;document.getElementById('notes').classList.toggle('on',noteOn);document.getElementById('bNote').classList.toggle('act',noteOn);};
addEventListener('keydown',e=>{
 if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' ')go(cur+1);
 if(e.key==='ArrowLeft'||e.key==='PageUp')go(cur-1);
 if(e.key==='Home')go(0);if(e.key==='End')go(S.length-1);
 if(e.key==='n'||e.key==='N')document.getElementById('bNote').click();});
fit();go(0);

/* ── 真实截图插槽：把 Qoder 会话截图存为 _ppt_shots/shot1.png … shot4.png 即自动挂上 ── */
(function(){const st=document.getElementById('shotStrip');
 for(let n=1;n<=4;n++){const im=new Image();
  im.onload=()=>{im.classList.add('fp');st.appendChild(im)};
  im.src='_ppt_shots/shot'+n+'.png';}})();

/* ── 小棋盘动画（环保险算法循环） ── */
(function(){const cv=document.getElementById('mini');if(!cv)return;const ctx=cv.getContext('2d'),C=25;
 function cidx(x,y){if(y===0)return x===0?0:133+(11-x);const s=1+11*x;return(x%2===0)?s+(y-1):s+(11-y);}
 const cells=[];for(let y=0;y<12;y++)for(let x=0;x<12;x++)cells[cidx(x,y)]=[x,y];
 let head=0,len=6,score=0;const foodGap=20;let food=(head+foodGap)%144;
 function draw(){ctx.fillStyle='#0d1119';ctx.fillRect(0,0,300,300);
  ctx.strokeStyle='#1c2432';for(let i=1;i<12;i++){ctx.beginPath();ctx.moveTo(i*C,0);ctx.lineTo(i*C,300);ctx.moveTo(0,i*C);ctx.lineTo(300,i*C);ctx.stroke();}
  const [fx,fy]=cells[food];ctx.fillStyle='#f0b429';ctx.beginPath();ctx.arc(fx*C+12.5,fy*C+12.5,8+(head%2),0,7);ctx.fill();
  for(let i=len-1;i>=1;i--){const [bx,by]=cells[(head-i+144)%144];ctx.fillStyle=i===len-1?'#2e86c8':'#3ecf8e';ctx.fillRect(bx*C+2,by*C+2,C-4,C-4);}
  const [hx,hy]=cells[head];ctx.fillStyle='#e8edf5';ctx.fillRect(hx*C+2,hy*C+2,C-4,C-4);
  ctx.fillStyle='#8b97ab';ctx.font='13px sans-serif';ctx.fillText('得分 '+score+' · 长度 '+len,8,292);}
 setInterval(()=>{if(!document.getElementById('deck').children[5].classList.contains('on'))return;
  head=(head+1)%144;
  if(head===food){score++;len=Math.min(len+1,60);do{food=(food+7+score*3)%144;}while(((food-head)+144)%144<6);if(score>=40){score=0;len=6;}}
  else len=Math.max(6,len);
  draw();},150);
 draw();})();

/* ── 封面装饰蛇 ── */
(function(){const w=document.getElementById('coverSnake');if(!w)return;
 let s='';for(let i=0;i<10;i++)s+='<span class="fx" style="--d:'+(1.2+i*.09)+'s;display:inline-block;width:26px;height:26px;border-radius:6px;margin-right:6px;background:'+(i===9?'#e8edf5':'#3ecf8e')+'"></span>';
 w.innerHTML=s+' <span class="fx" style="--d:2.1s;color:var(--gold);font-size:26px">→</span> <span class="fx blink" style="--d:2.3s;color:var(--gold);font-size:26px">●</span>';})();
