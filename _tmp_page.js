
const BRIDGE='http://127.0.0.1:8890', GW=12, GH=12, N=40;
const DIRS={UP:[0,-1],DOWN:[0,1],LEFT:[-1,0],RIGHT:[1,0]}, CN={UP:'上',DOWN:'下',LEFT:'左',RIGHT:'右'};
// 与训练脚本 _rlcd_snake.py 逐字一致的契约
const RULES="Snake game, 12 rows of 12 chars: '0' empty, '1' body, '2' head, '3' food. Row 0 top, row 11 bottom. UP=row-1, DOWN=row+1, LEFT=col-1, RIGHT=col+1. Pick the direction that moves the head toward the food without dying.";
let snake, food, score, steps, alive, pend, gen=0, force=null, running=true;
let msSum=0, msN=0, games=0, foodSum=0, MODEL='rlcd';

// 选项文字 = 落点坐标 + 落点性质 + 距食物变化（和 Python compact() 完全一致）
async function api(path,body){const r=await fetch(BRIDGE+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});return r.json();}
function randFood(){const free=[];for(let x=0;x<GW;x++)for(let y=0;y<GH;y++)if(!snake.some(s=>s[0]===x&&s[1]===y))free.push([x,y]);return free[Math.floor(Math.random()*free.length)];}
function resetGame(){gen++;force=null;snake=[[2,6],[1,6],[0,6]].map(s=>[...s]);score=0;steps=0;alive=true;pend=false;
  food=randFood();ui();draw();setCause('—');document.getElementById('log').innerHTML='';log('','── 新开局 ──');}
function gridRows(){const g=Array.from({length:GH},()=>Array(GW).fill('0'));
  snake.forEach((s,i)=>{if(i===0)g[s[1]][s[0]]='2';else g[s[1]][s[0]]='1';});g[food[1]][food[0]]='3';return g.map(r=>r.join(''));}

async function step(){
  if(!alive||!running)return;
  const myGen=gen;
  const state={game:'snake',board:'12x12',grid:gridRows()};
  const crit={UP:optText('UP'),DOWN:optText('DOWN'),LEFT:optText('LEFT'),RIGHT:optText('RIGHT')};
  document.getElementById('gridView').textContent=gridRows().join('\n');
  document.getElementById('optsView').textContent='↑ 棋盘原文    ↓ 四选项原文\n'+Object.entries(crit).map(([d,t])=>`${CN[d]}: ${t}`).join('\n');
  let j;
  try{ j=await api('/decide',{model:MODEL,state,instructions:RULES,criteria:crit}); }
  catch(e){ log('died','桥接离线/超时：'+e); setTimeout(step,800); return; }
  if(myGen!==gen)return;
  const p=j.probabilities||j.raw_probabilities||{};
  for(const d of ['UP','LEFT','RIGHT','DOWN']){
    document.getElementById('p'+d[0].toLowerCase()).textContent=((p[d]??0)*100).toFixed(0)+'%';
    document.getElementById('b'+d[0].toLowerCase()).classList.remove('pick','manual');}
  let dir=force; const manual=!!dir;
  if(!dir)dir=j.choice; force=null;
  document.getElementById('b'+dir[0].toLowerCase()).classList.add(manual?'manual':'pick');
  msSum+=(j.ms||0); msN++; steps++;
  const nh=[snake[0][0]+DIRS[dir][0], snake[0][1]+DIRS[dir][1]];
  const eat=nh[0]===food[0]&&nh[1]===food[1];
  const body=eat?snake:snake.slice(0,-1);
  const wall=nh[0]<0||nh[0]>=GW||nh[1]<0||nh[1]>=GH;
  const hit=body.some(s=>s[0]===nh[0]&&s[1]===nh[1]);
  const pct=['UP','DOWN','LEFT','RIGHT'].map(d=>`${CN[d]}${((p[d]??0)*100).toFixed(0)}`).join(' ');
  log(manual?'man':'', `#${steps} ${manual?'【人工】':''}${j.choice}(${pct}) ${j.ms?.toFixed(0)}ms`);
  if(wall||hit){ die(wall?'撞墙':'撞身'); return; }
  snake.unshift(nh);
  if(eat){ score++; food=randFood(); log('ate',`吃到！+1（共 ${score}）`); } else snake.pop();
  ui(); draw(); setTimeout(step, +document.getElementById('pace').value);
}
function die(c){alive=false;setCause(c);games++;foodSum+=score;
  log('died',`☠ ${c}，本局 ${score} 食物 / ${steps} 步`);ui();draw();
  setTimeout(()=>{ if(running) resetGame(), step(); },1600);}
function draw(){const cv=document.getElementById('cv'),g=cv.getContext('2d');
  g.fillStyle='#0d0d20';g.fillRect(0,0,cv.width,cv.height);
  g.strokeStyle='#1a1a30';for(let i=0;i<=GW;i++){g.beginPath();g.moveTo(i*N+.5,0);g.lineTo(i*N+.5,GH*N);g.stroke();g.beginPath();g.moveTo(0,i*N+.5);g.lineTo(GW*N,i*N+.5);g.stroke();}
  g.fillStyle='#e33';const[fx,fy]=food;g.fillRect(fx*N+6,fy*N+6,N-12,N-12);
  snake.forEach((s,i)=>{g.fillStyle=i===0?(alive?'#4dd2ff':'#888'):(alive?'#1f8fb8':'#556');g.fillRect(s[0]*N+2,s[1]*N+2,N-4,N-4);});
  if(!alive){g.fillStyle='#f55';g.font='28px sans-serif';g.fillText('☠ '+document.getElementById('cause').textContent,GW*N/2-70,GH*N/2);}}
function ui(){const s=id=>document.getElementById(id);s('score').textContent=score;s('len').textContent=snake.length;s('step').textContent=steps;
  s('ms').textContent=msN?(msSum/msN).toFixed(1):'—';s('games').textContent=games;s('avg').textContent=games?(foodSum/games).toFixed(1):'—';}
function setCause(c){document.getElementById('cause').textContent=c;}
function log(cls,txt){const el=document.getElementById('log');const d=document.createElement('div');d.className=cls;d.textContent=txt;el.prepend(d);while(el.children.length>60)el.lastChild.remove();}
function toggle(){running=!running;document.getElementById('btnRun').textContent=running?'暂停':'继续';if(running&&alive&&!pend){pend=true;step();}else if(running&&!alive){resetGame();step();}}
document.getElementById('pace').oninput=e=>document.getElementById('paceV').textContent=e.target.value;
function setEng(c,t){const el=document.getElementById('engine');el.className=c;el.textContent=t;}

(async()=>{try{const h=await api('/health');if(!h.ok)throw 0;
    const want=new URLSearchParams(location.search).get('model');
    if(want&&h.models[want])MODEL=want; else if(!h.models[MODEL])MODEL=Object.keys(h.models)[0];
    setEng('ok',`模型 [${MODEL}] 在线 · ${h.models[MODEL].model}`);}
  catch(e){setEng('bad','桥接离线：先运行 laya_bridge.py');}
  resetGame(); pend=true; step();})();
