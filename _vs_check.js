
const BRIDGE='http://127.0.0.1:8890';
const GW=12,GH=12,N=40;
const DIRS=[{n:'UP',x:0,y:-1},{n:'DOWN',x:0,y:1},{n:'LEFT',x:-1,y:0},{n:'RIGHT',x:1,y:0}];
const CN={UP:'上',DOWN:'下',LEFT:'左',RIGHT:'右'};
const isSafe=(x,y,b)=>x>=0&&y>=0&&x<GW&&y<GH&&!b.some(s=>s[0]===x&&s[1]===y);
function flood(sx,sy,b){const occ=new Set(b.map(s=>s[0]+','+s[1])),seen=new Set([sx+','+sy]),q=[[sx,sy]];let c=1;
  while(q.length){const[x,y]=q.pop();for(const[dx,dy]of[[0,1],[0,-1],[1,0],[-1,0]]){const nx=x+dx,ny=y+dy,k=nx+','+ny;
    if(nx>=0&&ny>=0&&nx<GW&&ny<GH&&!seen.has(k)&&!occ.has(k)){seen.add(k);q.push([nx,ny]);c++;}}}return c;}
function decide(b){const[hx,hy]=b.snake[0];const out=[];
  for(const d of DIRS){if(d.n===({UP:'DOWN',DOWN:'UP',LEFT:'RIGHT',RIGHT:'LEFT'})[b.facing])continue;
    const nx=hx+d.x,ny=hy+d.y;
    if(!isSafe(nx,ny,b.snake)){out.push({dir:d.n,x:d.x,y:d.y,safe:false,fd:0,sp:0,dc:4,s:-999});continue;}
    const fd=Math.abs(nx-b.food[0])+Math.abs(ny-b.food[1]),sp=flood(nx,ny,b.snake);
    let dc=0;for(const[ddx,ddy]of[[0,1],[0,-1],[1,0],[-1,0]])if(!isSafe(nx+ddx,ny+ddy,b.snake))dc++;
    let s=-2*fd+0.5*sp-3*dc;if(sp<b.snake.length)s-=50;
    out.push({dir:d.n,x:d.x,y:d.y,safe:true,fd,sp,dc,s});}
  return out;}
const critOf=cs=>{const o={};for(const c of cs)o[c.dir]=c.safe?`foodDist=${c.fd} space=${c.sp} danger=${c.dc}`:'BLOCKED: hits wall or body; foodDist=0 space=0 danger=4';return o;};
// 确定性食物/起点：同一 (场,第k个) 两边坐标一致
function h4(a,b,c,d){let x=(a*374761393+b*1103515245+c*2147483647+d*650983)>>>0;x=(x^(x>>>13));x=(x*1103515245)>>>0;x=(x^(x>>>16))>>>0;return x;}
function detPlace(seed,round,k,snake){for(let att=0;att<99;att++){const gx=h4(seed,round,k*7+att,1)%GW,gy=h4(seed,round,k*7+att,2)%GH;
  if(!snake.some(s=>s[0]===gx&&s[1]===gy))return[gx,gy];}return[0,0];}
function detStart(seed,round){const back={UP:[0,1],DOWN:[0,-1],LEFT:[1,0],RIGHT:[-1,0]};
  const dirs=['UP','DOWN','LEFT','RIGHT'];const facing=dirs[h4(seed,round,3,3)%4];
  const hx=2+h4(seed,round,4,4)%(GW-4),hy=2+h4(seed,round,5,5)%(GH-4);
  const b=back[facing];return{snake:[[hx,hy],[hx+b[0],hy+b[1]],[hx+b[0]*2,hy+b[1]*2]],facing};}

function mkBoard(key,sel,model){return{key,sel,model,snake:[[6,6],[5,6],[4,6]],food:[9,3],facing:'RIGHT',
  score:0,steps:0,foodK:0,alive:true,ms:0,msN:0,lastProb:null,cause:'—',scores:[]};}
const A=mkBoard('A'),B=mkBoard('B');
const boards=[A,B];
let matchSeed=Math.floor(Math.random()*1e6),matchNo=1,running=true,pending=false,timer=null,results=[];

async function api(path,body){const ctl=new AbortController();const to=setTimeout(()=>ctl.abort(),5000);
  try{const r=await fetch(BRIDGE+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:ctl.signal}:{signal:ctl.signal});
    return await r.json();}finally{clearTimeout(to);}}
let modelsAvail=[];
async function probe(){try{const j=await api('/health');if(!j.ok)throw 0;setEng('ok','桥接在线 · '+(j.default||''));
  const names=Object.keys(j.models||{});
  if(JSON.stringify(names)!==JSON.stringify(modelsAvail)){modelsAvail=names;
    for(const[sel,tagEl,b,pk]of[[document.getElementById('selA'),document.getElementById('tagA'),A,'a'],[document.getElementById('selB'),document.getElementById('tagB'),B,'b']]){
      sel.innerHTML=names.map(n=>`<option value="${n}">${n} · ${(j.models[n].model||'').slice(0,18)}</option>`).join('');
      const qp=new URLSearchParams(location.search).get(pk);           // ?a=v2&b=v5 直接摆对阵
      const want=(qp&&names.includes(qp)&&!b._manual)?qp
        :b===A?(names.find(n=>/v1|gen1$|old/i.test(n))||names[0]):(names.find(n=>/v2|gen/i.test(n)&&!/gen1$/.test(n))||names[names.length-1]);
      sel.value=want;b.model=want;tagEl.textContent=j.models[want].model;}}
}catch(e){setEng('bad','桥接离线 · 重启 laya_bridge.py');}}
function setEng(c,t){const el=document.getElementById('engine');el.className=c;el.textContent=t;}
document.getElementById('selA').onchange=e=>{A.model=e.target.value;A._manual=1;newMatch();};
document.getElementById('selB').onchange=e=>{B.model=e.target.value;B._manual=1;newMatch();};

function newMatch(){matchNo++;endScheduled=false;for(const b of boards){const st=detStart(matchSeed,matchNo);
  b.snake=st.snake;b.facing=st.facing;b.food=detPlace(matchSeed,matchNo,0,b.snake);b.foodK=0;
  b.score=0;b.steps=0;b.alive=true;b.cause='—';b.ms=0;b.msN=0;b.lastProb=null;
  document.getElementById('log'+b.key).innerHTML='';logRow(b,'forced',`── 第 ${matchNo} 场开始（同一食物序列）──`);}
  draw();ui();}
function logRow(b,cls,txt){const el=document.getElementById('log'+b.key);const d=document.createElement('div');
  d.className=cls;d.textContent=txt;el.prepend(d);while(el.children.length>40)el.lastChild.remove();}

async function step(b){
  if(!b.alive)return;
  const m=matchNo;
  const cands=decide(b);
  if(cands.every(c=>!c.safe)){b.alive=false;b.cause='无路可走';logRow(b,'died',`#${b.steps} 无路可走，本局结束（${b.score} 食物）`);return;}
  let j;try{j=await api('/decide',{model:b.model,state:{game:'snake',board:`${GW}x${GH}`,head:[...b.snake[0]],body:b.snake.map(s=>[...s]),food:[...b.food],facing:b.facing},criteria:critOf(cands)});}
  catch(e){setEng('bad','桥接离线 · 重启 laya_bridge.py');return;}
  if(m!==matchNo)return;   // 等响应期间已重开新局：丢弃过期决策
  if(!j||j.error||!j.choice){logRow(b,'died','决策失败: '+(j&&j.error||'?'));return;}
  b.steps++;b.ms=(b.ms*b.msN+j.ms)/(b.msN+1);b.msN++;b.lastProb=j.probabilities;b.lastChoice=j.choice;
  const c=cands.find(x=>x.dir===j.choice);
  const pct=j.probabilities&&j.probabilities[j.choice]?(j.probabilities[j.choice]*100).toFixed(0)+'%':'—';
  if(!c||!c.safe){b.alive=false;b.cause='撞死';logRow(b,'died',`#${b.steps} "${j.choice}"(${CN[j.choice]}) ${pct} → 撞了自己，本局结束（${b.score} 食物）`);return;}
  const nh=[b.snake[0][0]+c.x,b.snake[0][1]+c.y];
  b.snake=[nh,...b.snake];
  if(nh[0]===b.food[0]&&nh[1]===b.food[1]){b.score++;b.foodK++;b.food=detPlace(matchSeed,matchNo,b.foodK,b.snake);
    logRow(b,'food',`#${b.steps} "${j.choice}"(${CN[j.choice]}) ${pct} ${j.ms.toFixed(0)}ms 🎉吃! 第${b.score}个`);}
  else{b.snake.pop();
    if(b.steps%5===0||b.steps<6)logRow(b,'',`#${b.steps} "${j.choice}"(${CN[j.choice]}) ${pct} ${j.ms.toFixed(0)}ms`);}}

let endScheduled=false;
function checkMatchEnd(){if(endScheduled)return;
  if(boards.every(b=>!b.alive)&&A.steps>0){endScheduled=true;   // 只许排一次重开，防连环 reset 闪烁
  const r={m:matchNo,a:A.score,b:B.score,w:A.score===B.score?'平局':(A.score>B.score?'旧版胜':'新版胜')};
  results.unshift(r);if(results.length>30)results.pop();renderScore();setTimeout(newMatch,1800);}}

function renderScore(){const el=document.getElementById('rows');
  el.innerHTML=results.length?results.slice(0,12).map(r=>
    `<div>第${r.m}场: <span class="${r.w==='新版胜'?'win':r.w==='旧版胜'?'lose':'tie'}">${r.a} : ${r.b}</span> ${r.w}</div>`).join(''):'';
  const avg=k=>{const xs=results.map(r=>r[k]);return xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:0;};
  const ma=avg('a'),mb=avg('b'),tot=Math.max(1,ma+mb);
  document.getElementById('bars').innerHTML=
    `<div class="bar"><i style="width:${ma/tot*100}%;background:#e07"></i><span>旧版 ${ma.toFixed(1)}</span></div>
     <div class="bar"><i style="width:${mb/tot*100}%;background:#0c6"></i><span>新版 ${mb.toFixed(1)}</span></div>`;}

function drawBoard(b){const cv=document.getElementById('cv'+b.key),g=cv.getContext('2d');
  g.fillStyle='#0d0d20';g.fillRect(0,0,cv.width,cv.height);
  g.strokeStyle='#1a1a30';for(let i=0;i<=GW;i++){g.beginPath();g.moveTo(i*N+.5,0);g.lineTo(i*N+.5,GH*N);g.stroke();g.beginPath();g.moveTo(0,i*N+.5);g.lineTo(GW*N,i*N+.5);g.stroke();}
  g.fillStyle='#f55';const[fx,fy]=b.food;g.fillRect(fx*N+6,fy*N+6,N-12,N-12);
  b.snake.forEach((s,i)=>{g.fillStyle=b.key==='A'?(i?`rgba(224,0,119,${1-i*0.02})`:'#fff'):(i?`rgba(0,204,102,${1-i*0.02})`:'#fff');
    g.fillRect(s[0]*N+1.5,s[1]*N+1.5,N-3,N-3);});
  if(!b.alive){g.fillStyle='rgba(0,0,0,.55)';g.fillRect(0,0,cv.width,cv.height);g.fillStyle='#f66';g.font='bold 30px sans-serif';g.textAlign='center';g.fillText('💀 结束',cv.width/2,cv.height/2);}}
function draw(){for(const b of boards){drawBoard(b);
  const pb=document.getElementById('pick'+b.key);
  if(b.lastProb){const ks=Object.keys(b.lastProb);pb.innerHTML=ks.map(k=>
    `<span style="margin-right:12px;color:${k===b.lastChoice?'#fff':'#666'};border-bottom:3px solid ${(b.lastProb[k]||0)*100>40?(b.key==='A'?'#e07':'#0c6'):'#333'}">${k} ${((b.lastProb[k]||0)*100).toFixed(0)}%</span>`).join('')
    +` <span style="color:#556">${b.model}</span>`;}else pb.textContent='';}}
function ui(){for(const b of boards){document.getElementById('score'+b.key).textContent=b.score;
  document.getElementById('len'+b.key).textContent=b.snake.length;
  document.getElementById('step'+b.key).textContent=b.steps;
  document.getElementById('ms'+b.key).textContent=b.msN?b.ms.toFixed(0):'—';
  document.getElementById('cause'+b.key).textContent=b.cause;}}

async function tick(){if(!running||pending)return;pending=true;
  await step(A);await step(B);   // 串行：GPU 锁本来就会排队，串行更稳
  draw();ui();checkMatchEnd();pending=false;}

document.getElementById('btnRun').onclick=e=>{running=!running;e.target.textContent=running?'⏸ 暂停':'▶ 继续';};
document.getElementById('btnNew').onclick=()=>newMatch();
const sp=document.getElementById('speed');sp.oninput=()=>{document.getElementById('paceV').textContent=sp.value+'ms';setLoop();};
function setLoop(){clearInterval(timer);timer=setInterval(tick,+sp.value);}

(async()=>{await probe();setInterval(probe,4000);newMatch();setLoop();})();
// 键盘：空格暂停
addEventListener('keydown',e=>{if(e.key===' '){e.preventDefault();document.getElementById('btnRun').click();}});
