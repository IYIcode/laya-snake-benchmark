
function fit(){const s=Math.min(innerWidth/1280,innerHeight/720);const st=document.getElementById('stage');
 st.style.transform='scale('+s+')';st.style.transformOrigin='center center';}
addEventListener('resize',fit);fit();

/* ── 引擎原语（与剧院/io 页逐字对齐） ── */
const GW=12,GH=12,KN=['UP','DOWN','LEFT','RIGHT'],DIRS={UP:[0,-1],DOWN:[0,1],LEFT:[-1,0],RIGHT:[1,0]};
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function stepSnake(snake,food,d){const[hx,hy]=snake[0],[dx,dy]=DIRS[d];const nx=hx+dx,ny=hy+dy;
 const eat=nx===food[0]&&ny===food[1];const body=eat?snake:snake.slice(0,-1);
 if(nx<0||nx>=GW||ny<0||ny>=GH)return[snake,true,false];
 if(body.some(s=>s[0]===nx&&s[1]===ny))return[snake,true,false];
 const ns=[[nx,ny],...snake];if(!eat)ns.pop();return[ns,false,eat];}
function gridRows(snake,food){const g=Array.from({length:GH},()=>Array(GW).fill('0'));
 snake.forEach((s,i)=>{g[s[1]][s[0]]=i===0?'2':'1';});g[food[1]][food[0]]='3';return g.map(r=>r.join(''));}
function landOf(nx,ny,snake,food){if(nx<0||nx>=GW||ny<0||ny>=GH)return'wall';
 const tail=snake[snake.length-1];const eat=nx===food[0]&&ny===food[1];
 if(snake.slice(1,-1).some(s=>s[0]===nx&&s[1]===ny))return'body';
 if(snake.length>1&&nx===tail[0]&&ny===tail[1])return eat?'body':'vacating';return'free';}
function cidx(x,y){if(y===0)return x===0?0:133+(11-x);const s=1+11*x;return(x%2===0)?s+(y-1):s+(11-y);}
function loopAhead(snake,food){const hi=cidx(snake[0][0],snake[0][1]);
 const D=p=>((cidx(p[0],p[1])-hi)%144+144)%144;let m1=144,m2=144;
 for(let i=1;i<snake.length;i++){const dd=D(snake[i]);if(i<snake.length-1&&dd<m2)m2=dd;if(dd<m1)m1=dd;}
 return{foodAhead:D(food),bodyAhead:m1,bodyGoAhead:m2};}
function loopSafe(snake,food,d){const[hx,hy]=snake[0],[dx,dy]=DIRS[d];const nx=hx+dx,ny=hy+dy;
 const land=landOf(nx,ny,snake,food);if(land==='wall'||land==='body')return false;
 const hi=cidx(hx,hy),cd=((cidx(nx,ny)-hi)%144+144)%144;
 const la=loopAhead(snake,food),df=la.foodAhead,m1=la.bodyAhead,m2=la.bodyGoAhead;
 const eat=nx===food[0]&&ny===food[1];return eat?cd<=m1-1:(cd<=m2-1&&cd<=df);}
function cycOf(snake,d){const hi=cidx(snake[0][0],snake[0][1]),nx=snake[0][0]+DIRS[d][0],ny=snake[0][1]+DIRS[d][1];return((cidx(nx,ny)-hi)%144+144)%144;}
function cycCrit(snake,food,jc){const[hx,hy]=snake[0],hi=cidx(hx,hy),c={};
 for(const d of KN){const[dx,dy]=DIRS[d];const nx=hx+dx,ny=hy+dy;const land=landOf(nx,ny,snake,food);
 const dn=Math.abs(nx-food[0])+Math.abs(ny-food[1]),dc=Math.abs(hx-food[0])+Math.abs(hy-food[1]);
 const rel=dn<dc?'NEARER to food':(dn>dc?'FARTHER from food':'SAME distance');
 c[d]=land==='wall'?`(${nx},${ny}) wall, ${rel}`:`(${nx},${ny}) ${land}, ${rel}, cyc=${((cidx(nx,ny)-hi)%144+144)%144}`;}
 return c;}
const CYCLE_RULES="Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. ... Each option lists its landing cell facts and cyc = its forward loop steps from the head. A move is loop-safe if it does not pass your body or the food on the loop: when the move does not eat, cyc <= bodyGoAhead-1 and cyc <= foodAhead; when the move eats, cyc <= bodyAhead-1.";
const JUMP_TAIL="The state also carries jumpCount = how many times earlier in THIS game you already picked a move whose cyc was greater than bodyGoAhead ... your goal is to finish the game with jumpCount = 0.";
const RAW_GRID=["000000000000","000000000000","000000000000","000000000000","000000000000","000000300000","112000000000","000000000000","000000000000","000000000000","000000000000","000000000000"];
function drawGridRows(rows){const ctx=boardCtx,C=320/12;ctx.fillStyle='#0d1119';ctx.fillRect(0,0,320,320);
 ctx.strokeStyle='#1c2432';for(let i=1;i<12;i++){ctx.beginPath();ctx.moveTo(i*C,0);ctx.lineTo(i*C,320);ctx.moveTo(0,i*C);ctx.lineTo(320,i*C);ctx.stroke();}
 for(let y=0;y<12;y++)for(let x=0;x<12;x++){const ch=rows[y][x];
  if(ch==='1'){ctx.fillStyle='#3ecf8e';ctx.fillRect(x*C+2,y*C+2,C-4,C-4);}
  if(ch==='2'){ctx.fillStyle='#e8edf5';ctx.fillRect(x*C+2,y*C+2,C-4,C-4);}
  if(ch==='3'){ctx.fillStyle='#f0b429';ctx.beginPath();ctx.arc(x*C+C/2,y*C+C/2,7,0,7);ctx.fill();}}}
function drawSnake(snake,food){drawGridRows(gridRows(snake,food));}
const boardCtx=document.getElementById('board').getContext('2d');

/* ── 五条赛道 ── */
const TABS=[
 {id:'zs',   t:'① 未训练模型 · 裸棋盘',   s:'<i class="r">0 分 ×23局</i>'},
 {id:'fd',   t:'② 微调模型 · 小抄特征',   s:'<i>14.8→59.8</i>'},
 {id:'cyc',  t:'③ 微调模型 · 环契约+跨身计数', s:'<i class="y">141 通关</i>'},
 {id:'algo', t:'④ 纯代码算法 · 环保险',   s:'<i class="g">141 · 现场真跑</i>'},
 {id:'me',   t:'⑤ 通用 Agent · 我逐段决策', s:'<i class="g">141 · 真实回放</i>'}];
const tabsEl=document.getElementById('tabs');
TABS.forEach(tb=>{const b=document.createElement('button');b.innerHTML='<b>'+tb.t+'</b>'+tb.s;b.dataset.id=tb.id;
 b.onclick=()=>mount(tb.id);tabsEl.appendChild(b);});

let stopLive=null;
function mount(id){stopLive&&stopLive();stopLive=null;
 document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('on',b.dataset.id===id));
 ({zs:mountZs,fd:mountFd,cyc:mountCyc,algo:mountAlgo,me:mountMe})[id]();}

/* ── ① 零样本 ── */
function mountZs(){
 who('决策者：<b>未训练的 Laya 底模</b>（convaiinnovations/laya，421M）。没有算法代劳、没有训练，只有它读提示词。');
 left(`<h4>它每一步收到的真实输入 <span>（桥接日志原文，解码全档案 _model_input.txt）</span></h4>
 <pre class="mono">[指令] You are driving a snake in a 12x12 grid game. The board is given as 12 rows of 12 characters: '0' empty cell, '1' snake body, '2' snake head, '3' food. … Choose the direction that leads the head toward the food while staying alive: never step into a wall or into a '1' body cell.

[选项] UP: move one cell up (row-1)   DOWN: …   LEFT: …   RIGHT: …
        <span class="k">← 四个光秃秃的方向，没有小抄</span>

[状态] {"game":"snake","board":"12x12","grid":
 ["000000000000","…","000000300000","112000000000","…"]}</pre>
 <h4 style="margin-top:12px">它的真实输出概率（同帧，实测）</h4>
 ${probRows([['上 UP',39,'0.39'],['下 DOWN',22,'0.22'],['左 LEFT',19,'0.19'],['右 RIGHT',19,'0.19']],0)}`);
 rightStatic(RAW_GRID,['得分 <b class="r">0.0</b>（23 局平均）','存活 <b>6–7 步</b> 即撞墙','"上"永远概率最高——语料词先验']);
 talk('第一道：没训练的 Laya 直接上场。输入就是棋盘数字阵加四个光秃秃的方向。23 局全 0 分——概率条几乎均匀，"上"字最高，它没读棋盘，在复读词先验。六种提示词写法、把答案透给它：最好 5.5 分，照样撞死。');}

/* ── ② 小抄微调 ── */
function mountFd(){
 who('决策者：<b>微调后的 Laya</b>（gen5 谱系）。感知由程序包办：距离/空间/危险度算成"小抄"塞进选项。');
 left(`<h4>它每一步收到的真实输入 <span>（桥接 /log 实录帧，死因证据帧）</span></h4>
 <pre class="mono">[状态] {"game":"snake","head":[1,2],"body":[…54节…],"food":[0,2],"facing":"UP"}

[选项] UP:   <span class="k">foodDist=0  space=84  danger=3</span>  <span class="r">← 吃到食物，安全，p=0.281</span>
 DOWN: foodDist=2  space=84  danger=<span class="no">0</span>       <span class="y">← 落点贴墙被读成危险，p=0.370 胜出</span>
 LEFT/RIGHT: BLOCKED（转向/撞身 → 概率清零）</pre>
 <h4 style="margin-top:10px">这一帧它放弃了嘴边的食物，绕路后困死——催生最终配方 fdpen6</h4>
 <div id="ladder"></div>`);
 rightChart();
 talk('第二道：程序替它看棋盘——离食距离、剩余空间、危险度算成小抄，再微调。v1 只有 14.8 分，死因撞墙加咬身；这页日志就是现场证据：嘴边食物 0.281 输给一个贴墙方向 0.370。之后小抄一轮轮加预测：口袋警告、距离惩罚、两步洪水视野，一路 36→39→43→49→59.8，反超手写老师 53。铁律：改文字输出逐字节不变，只有数字动得了它。');}

/* ── ③ 环契约+跨身计数 ── */
function mountCyc(){
 const snake=[[6,6],[5,6],[4,6]],food=[11,4];
 const state={game:'snake',board:'12x12',grid:gridRows(snake,food),loopAhead:loopAhead(snake,food),jumpCount:0};
 const crit=cycCrit(snake,food,0);
 who('决策者：<b>环契约微调模型</b> + 一个额外数字。输入契约一字不改，state 里多一个"跨身计数"——本局已几次抄近路跨过自己身体，目标保持 0。');
 left(`<h4>第 0 步真实输入（与桥端逐字节 parity 验证过，seed1002）</h4>
 <pre class="mono">[指令节选] ${CYCLE_RULES.slice(0,150)}…
  <span class="k">+ jumpCount 说明句（J_TAIL 原文）</span>

[状态] ${JSON.stringify(state.loopAhead)} , jumpCount=0

[选项]</pre>
 ${['UP','DOWN','LEFT','RIGHT'].map(d=>'<div class="optrow"><span class="dn">'+d+'</span>　'+crit[d]+'</div>').join('')}
 <p class="mono" style="color:var(--dim);margin-top:6px">红线：只喂落点事实 + 环距离数字，从不点名"该走哪"；零掩码时四向概率原样取 argmax。</p>`);
 rightStatic(state.grid,['<b class="y">9 局 4 胜</b>通关 141','最好一局 4592 步<b>零违规</b>','加环掩码后 4/4 稳定通关','同提示词未训练底模：0分@2步']);
 talk('第三道，也是高光：训练契约一字不动、零掩码、零代码代答，只在输入里加一个数字——跨身计数。模型自己读这个数字、自己收敛：9 局赢 4 局通关 141，最好一局 4592 步全程零违规；加环安全掩码 4/4 稳定。对照：同一份提示词给没训练的底座，0 分、第 2 步撞死。记住：提示词是能力的开关，训练才是电路。');}

/* ── ④ 环保险算法（现场真跑） ── */
function mountAlgo(){
 const st={snake:[[6,6],[5,6],[4,6]],food:null,pp:0,jumps:0,steps:0,score:0,dead:false,won:false,rng:mulberry32(1000),speed:70};
 st.food=placeFree(st);
 let auto=null,paused=false;
 who('决策者：<b>几十行代码</b>。没有任何模型调用——每步只做一次环不等式检查，可行集中挑离食物最近的。');
 rightBoard(st);
 function placeFree(s){const free=[];for(let y=0;y<12;y++)for(let x=0;x<12;x++)
   if(!s.snake.some(p=>p[0]===x&&p[1]===y))free.push([x,y]);
  return free.length?free[Math.floor(s.rng()*free.length)]:null;}
 function tick(){
  if(st.dead||st.won)return;
  const cands=[];for(const d of KN){const land=landOf(st.snake[0][0]+DIRS[d][0],st.snake[0][1]+DIRS[d][1],st.snake,st.food);
    if(land!=='wall'&&land!=='body')cands.push(d);}
  const safe=cands.filter(d=>loopSafe(st.snake,st.food,d));
  const pool=safe.length?safe:cands;
  const pick=pool.sort((a,b)=>(Math.abs(st.snake[0][0]+DIRS[a][0]-st.food[0])+Math.abs(st.snake[0][1]+DIRS[a][1]-st.food[1]))-(Math.abs(st.snake[0][0]+DIRS[b][0]-st.food[0])+Math.abs(st.snake[0][1]+DIRS[b][1]-st.food[1])))[0];
  if(!loopSafe(st.snake,st.food,pick))st.jumps++;
  st.snake=applyStep(st,pick);
  st.steps++;
  if(st.ate){st.score++;st.food=placeFree(st);if(!st.food){st.won=true;}}
  if(st.dead)showWin(false,st);
  if(st.won)showWin(true,st);
  renderAlgo(pick,safe);
 }
 function applyStep(s,d){const[ns,died,ate]=stepSnake(s.snake,s.food,d);s.dead=died;s.ate=ate;return ns;}
 function renderAlgo(pick,safe){
  const la=loopAhead(st.snake,st.food);
  document.getElementById('left').innerHTML=`<h4>没有模型调用 <span>（这一步代码算给"自己"看的全部事实）</span></h4>
  <pre class="mono">环序头指针 hi=cidx(头)   bodyGoAhead=<span class="k">${la.bodyGoAhead}</span>  foodAhead=<span class="k">${la.foodAhead}</span>  bodyAhead=${la.bodyAhead}
<span class="k">伪代码</span>：对每个方向 d：落点非墙非身 且（不吃时 cyc≤bodyGoAhead-1 且 cyc≤foodAhead；吃时 cyc≤bodyAhead-1）
        → 可行；可行集中取离食物最近，平手取环上前进量大的。</pre>
  ${KN.map(d=>{const ok=loopSafe(st.snake,st.food,d);const cd=cycOf(st.snake,d);
   return '<div class="optrow'+(d===pick?' pick':'')+'"><span class="dn">'+d+'</span>　cyc='+cd+'　'+
   (ok?'<span style="color:var(--green)">PASS 环安全</span>':'<span style="color:var(--red)">FAIL 越环/撞'+(landOf(st.snake[0][0]+DIRS[d][0],st.snake[0][1]+DIRS[d][1],st.snake,st.food)==='wall'?'墙':'身')+'</span>')+
   (d===pick?'　<b class="y">← 本步执行</b>':'')+'</div>';}).join('')}
  <p class="mono" style="color:var(--dim);margin-top:6px">步 ${st.steps} · 跨身 ${st.jumps} · 12 种子实测全部 141 通关（本页现场是 seed 1000）</p>`;
  drawSnake(st.snake,st.food);stat(st);
  if(st.won||st.dead){showWin(st.won,st);}
 }
 const ctl=document.getElementById('ctl');
 ctl.innerHTML=`<button id="bP">⏸ 暂停</button><button id="bS">⏭ 单步</button><button id="bR">↻ 重开</button>
 <span class="lb">速度</span><input id="sp" type="range" min="8" max="120" value="70">`;
 document.getElementById('bP').onclick=e=>{paused=!paused;e.target.textContent=paused?'▶ 继续':'⏸ 暂停'};
 document.getElementById('bS').onclick=()=>tick();
 document.getElementById('bR').onclick=()=>{st.snake=[[6,6],[5,6],[4,6]];st.score=0;st.steps=0;st.jumps=0;st.dead=false;st.won=false;st.rng=mulberry32(1000);st.food=placeFree(st);hideWin();renderAlgo(KN[0],[]);};
 document.getElementById('sp').oninput=e=>{st.speed=+e.target.value;restart();};
 function restart(){if(auto)clearInterval(auto);auto=setInterval(()=>{if(!paused&&!st.dead&&!st.won)tick();},st.speed);}
 renderAlgo(KN[0],[]);tick();restart();
 stopLive=()=>{if(auto)clearInterval(auto);};
 talk('第四道：几十行代码的环保险算法，左边是它每一步的真实判断表（环不等式一票否决），右边正在真跑。12 个种子全部 141 通关，不用 GPU、不用数据、当场生效——这就是"训练一小时不如算法一行"的那道残酷对比。');}

/* ── ⑤ Agent·我（真实 141 通关局逐手回放） ── */
let MY=null;
function mountMe(){
 who('决策者：<b>我（通用 Agent）</b>——不借任何模型、同契约同种子（20260929），不限时一段一断打出的真实 141 通关局。左侧是我当时每段开帧读到的输入原文。');
 const box=document.getElementById('left');
 if(!MY){box.innerHTML='<h4>正在装载真实对局档案 _myrun_data.json …</h4>';
  fetch('_myrun_data.json').then(r=>r.json()).then(d=>{MY=d;startMe();},()=>{box.innerHTML='<h4 class="r">档案读取失败：请用 http://127.0.0.1:8895 打开本页</h4>';});
  rightBoard({snake:[[6,6],[5,6],[4,6]],food:[6,1],score:0,steps:0,jumps:0,dead:false,won:false});return;}
 startMe();
 function segOf(steps){let k=0;for(let i=0;i<MY.segs.length;i++)if(MY.segs[i].stepsAtAsk<=steps)k=i;return k;}
 function startMe(){
  const st={snake:MY.start.map(p=>[p[0],p[1]]),food:MY.foods[0],score:0,steps:0,jumps:0,dead:false,won:false,speed:60};
  rightBoard(st);
  let auto=null,paused=false,seg=-1;
  function render(){
   const si=segOf(st.steps),sg=MY.segs[si];
   if(si!==seg){seg=si;}
   const chain=sg.chain||MY.dirs.slice(sg.stepsAtAsk,sg.stepsAtAsk+30);
   const done=st.steps-sg.stepsAtAsk;
   document.getElementById('left').innerHTML=`<h4>第 ${sg.askId} 段 · 我开帧读到的输入原文 <span>（ask 时刻真实载荷，导出时逐字节校验过）</span></h4>
   <pre class="mono">开帧局面：蛇头(${sg.head[0]},${sg.head[1]}) 身长${sg.len} 食物(${sg.food[0]},${sg.food[1]})
 loopAhead：${JSON.stringify(sg.loopAhead)}   jumpCount=${sg.jumpCount}   已得 ${sg.score} 分
<span class="k">四选项原文（cyc=环上前进度）</span></pre>
   ${['UP','DOWN','LEFT','RIGHT'].map(d=>'<div class="optrow"><span class="dn">'+d+'</span>　'+(sg.criteria[d]||'')+'</div>').join('')}
   <pre class="mono" style="margin-top:8px"><span class="k">我提交的动作链</span>（一口气 ${chain.length} 手，引擎逐手执行）
${chain.map((d,i)=>'<span class="'+(i<done?'ok':(i===done?'k no':''))+'">'+(i<done?'✔':(i===done?'▶':'·'))+'</span>').join(' ')}</pre>
   <p class="mono" style="color:var(--dim);margin-top:4px">我的策略公示：环不等式一票否决 → 可行集取离食最近 → 平手取环上前进度大。吃到即停链、重读棋盘再规划下一段。</p>`;
   drawSnake(st.snake,st.food);stat(st);
  }
  function tick(){
   if(st.dead||st.won)return;
   const d=MY.dirs[st.steps];const la=st;
   const[ns,died,ate]=stepSnake(st.snake,st.food,d);st.snake=ns;st.dead=died;st.steps++;
   if(died)st.won=false;
   if(ate){st.score++;if(st.score>=MY.foods.length){st.won=true;showWin(true,st);}else st.food=MY.foods[st.score];}
   render();if(st.dead)showWin(false,st);
  }
  const ctl=document.getElementById('ctl');
  ctl.innerHTML=`<button id="bP">⏸ 暂停</button><button id="bS">⏭ 单步</button>
  <button id="bN">⟫ 跳到下一段</button><button id="bF">⚡ 快进100步</button>
  <span class="lb">速度</span><input id="sp" type="range" min="8" max="200" value="60">`;
  document.getElementById('bP').onclick=e=>{paused=!paused;e.target.textContent=paused?'▶ 继续':'⏸ 暂停'};
  document.getElementById('bS').onclick=()=>tick();
  document.getElementById('bN').onclick=()=>{const nx=MY.segs[segOf(st.steps)+1];if(nx)while(st.steps<nx.stepsAtAsk&&!st.dead&&!st.won)tick();};
  document.getElementById('bF').onclick=()=>{for(let i=0;i<100&&!st.dead&&!st.won;i++)tick();};
  document.getElementById('sp').oninput=e=>{st.speed=+e.target.value;restart();};
  function restart(){if(auto)clearInterval(auto);auto=setInterval(()=>{if(!paused&&!st.dead&&!st.won)tick();},st.speed);}
  render();restart();stopLive=()=>{if(auto)clearInterval(auto);};
  talk('第五道是我本人：不借模型，同契约同种子，一段一断打出的 141 真实通关局，4370 步 351 秒零跨身，档案逐手可回放。左边每一段的第一帧就是我当时真读到的输入原文——吃到食物我就停链重读棋盘再规划。一手一断我只拿 2 分（每手 14 秒），链式规划放开时限才摸到满分：同样成果 Laya 每手 27 毫秒，快 500 倍——这就是决策模型存在的理由。');
 }
}

/* ── 共用右栏 ── */
function who(h){document.getElementById('who').innerHTML=h;}
function probRows(rows,pickIdx){return rows.map((r,i)=>'<div style="font-size:13.5px;color:var(--dim)">'+r[0]+'</div><div class="pbar'+(i===pickIdx?'':' dim')+'"><i style="width:'+r[1]+'%"></i><span>'+r[2]+'</span></div>').join('');}
function rightStatic(grid,notes){document.getElementById('winMask').style.display='none';document.getElementById('ctl').innerHTML='';
 drawGridRows(grid);
 document.getElementById('rnotes').innerHTML=notes.map(n=>'· '+n).join('<br>');
 document.getElementById('stat').innerHTML='';}
function rightBoard(st){document.getElementById('winMask').style.display='none';
 document.getElementById('stat').innerHTML='';stat(st);}
function stat(st){document.getElementById('stat').innerHTML=
 `<div class="stat"><div class="v">${st.score}</div><div class="l">得分/141</div></div>
  <div class="stat"><div class="v">${st.steps}</div><div class="l">步数</div></div>
  <div class="stat"><div class="v">${st.snake.length}</div><div class="l">蛇长</div></div>
  <div class="stat"><div class="v" style="color:${st.jumps?'var(--red)':'var(--green)'}">${st.jumps}</div><div class="l">跨身</div></div>`;}
function showWin(won,st){const m=document.getElementById('winMask');m.style.display='flex';
 m.innerHTML=won?'🏆 141 全盘通关（'+st.steps+' 步）':'☠ 撞'+(st.dead?'墙/身':'死')+'（得分 '+st.score+'）';}
function hideWin(){document.getElementById('winMask').style.display='none';}
function rightChart(){document.getElementById('ctl').innerHTML='';document.getElementById('stat').innerHTML='';
 const rows=[['零样本 v0',0],['v1 初训',14.8],['三特征基线',36],['+口袋警告',39],['+距离惩罚',43.1],['+两步视野',48.8],['fdpen6 终版',59.8]];
 const c=document.getElementById('board');const ctx=c.getContext('2d');
 drawBoardChart(ctx);
 document.getElementById('rnotes').innerHTML='同种子 3001–3010 · 10 局贪心 · 不限步<br>BFS 手写老师 <b class="r">53</b> —— 被终版反超';}
function drawBoardChart(ctx){ctx.fillStyle='#0d1119';ctx.fillRect(0,0,320,320);
 const rows=[['零样本',0],['v1',14.8],['基线',36],['口袋',39],['惩罚',43.1],['视野',48.8],['fdpen6',59.8]];
 const W=320,H=320,pad=8,max=62;ctx.font='11px sans-serif';
 rows.forEach((r,i)=>{const y=pad+i*((H-40)/7);const w=(H-72)*(r[1]/max);
  ctx.fillStyle='#bcd';ctx.textAlign='right';ctx.fillText(r[0],78,y+13);
  ctx.fillStyle=i===6?'#f0b429':'#5aa7f0';ctx.fillRect(84,y+2,w,16);
  ctx.fillStyle='#e8edf5';ctx.textAlign='left';ctx.fillText(r[1],88+w,y+14);});
 const bl=84+(H-72)*(53/max);ctx.strokeStyle='#ef5b5b';ctx.setLineDash([5,4]);ctx.beginPath();ctx.moveTo(bl,pad);ctx.lineTo(bl,H-24);ctx.stroke();ctx.setLineDash([]);
 ctx.fillStyle='#ef5b5b';ctx.fillText('BFS 53',bl+3,pad+10);}
function left(h){document.getElementById('left').innerHTML=h;}

const p=new URLSearchParams(location.search);mount(p.get('m')||'algo');
