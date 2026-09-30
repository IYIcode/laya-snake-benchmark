// 离线调参：③号道追食蛇策略，目标=吃满 seed1002 档案 141 格且 0 死亡
const GW=12,GH=12,KN=['UP','DOWN','LEFT','RIGHT'],DIRS={UP:[0,-1],DOWN:[0,1],LEFT:[-1,0],RIGHT:[1,0]};
function cidx(x,y){if(y===0)return x===0?0:133+(11-x);const s=1+11*x;return(x%2===0)?s+(y-1):s+(11-y);}
function landOf(nx,ny,snake,food){if(nx<0||nx>=GW||ny<0||ny>=GH)return'wall';
 const tail=snake[snake.length-1];const eat=nx===food[0]&&ny===food[1];
 if(snake.slice(1,-1).some(s=>s[0]===nx&&s[1]===ny))return'body';
 if(snake.length>1&&nx===tail[0]&&ny===tail[1])return eat?'body':'vacating';return'free';}
function loopAhead(snake,food){const hi=cidx(snake[0][0],snake[0][1]);
 const D=p=>((cidx(p[0],p[1])-hi)%144+144)%144;let m1=144,m2=144;
 for(let i=1;i<snake.length;i++){const dd=D(snake[i]);if(i<snake.length-1&&dd<m2)m2=dd;if(dd<m1)m1=dd;}
 return{foodAhead:D(food),bodyAhead:m1,bodyGoAhead:m2};}
function loopSafe(snake,food,d){const[hx,hy]=snake[0],[dx,dy]=DIRS[d];const nx=hx+dx,ny=hy+dy;
 const land=landOf(nx,ny,snake,food);if(land==='wall'||land==='body')return false;
 const hi=cidx(hx,hy),cd=((cidx(nx,ny)-hi)%144+144)%144;
 const la=loopAhead(snake,food),df=la.foodAhead,m1=la.bodyAhead,m2=la.bodyGoAhead;
 const eat=nx===food[0]&&ny===food[1];return eat?cd<=m1-1:(cd<=m2-1&&cd<=df);}
function stepSnake(snake,food,d){const[hx,hy]=snake[0],[dx,dy]=DIRS[d];const nx=hx+dx,ny=hy+dy;
 const eat=nx===food[0]&&ny===food[1];const body=eat?snake:snake.slice(0,-1);
 if(nx<0||nx>=GW||ny<0||ny>=GH)return[snake,true,false];
 if(body.some(s=>s[0]===nx&&s[1]===ny))return[snake,true,false];
 const ns=[[nx,ny],...snake];if(!eat)ns.pop();return[ns,false,eat];}
function flood(snake,land){ // 落点后从该格出发的可达空格数（蛇身按移动后计算）
 const occ=new Set(snake.map(p=>p[0]+','+p[1]));occ.delete(land[0]+','+land[1]);occ.delete(snake[snake.length-1][0]+','+snake[snake.length-1][1]);
 const seen=new Set([land[0]+','+land[1]]);const q=[land];let n=1;
 while(q.length){const[x,y]=q.shift();for(const k of KN){const a=x+DIRS[k][0],b=y+DIRS[k][1];const key=a+','+b;
  if(a<0||a>=GW||b<0||b>=GH||seen.has(key)||occ.has(key))continue;seen.add(key);q.push([a,b]);n++;}}
 return n;}
const FD=require('../_jumpfood_1002.json').foods;
function run(mode){
 let snake=[[6,6],[5,6],[4,6]],k=0,steps=0,jumps=0;
 while(k<FD.length){const food=FD[k];
  const[hx,hy]=snake[0];
  const cands=KN.filter(d=>{const l=landOf(hx+DIRS[d][0],hy+DIRS[d][1],snake,food);return l!=='wall'&&l!=='body';});
  const safe=cands.filter(d=>loopSafe(snake,food,d));
  const cycOf=d=>((cidx(hx+DIRS[d][0],hy+DIRS[d][1])-cidx(hx,hy))%144+144)%144;
  let pool;
  if(mode==='greedy'){pool=safe.length?safe:cands;}
  else if(mode==='hybrid'){ // 蛇长了改循环：只走环序下一格（cyc 最小），绝不围死
   if(snake.length>60&&safe.length){pool=[safe.sort((a,b)=>cycOf(a)-cycOf(b))[0]];}
   else{const roomy=safe.filter(d=>flood(snake,[hx+DIRS[d][0],hy+DIRS[d][1]])>=snake.length);
        pool=roomy.length?roomy:(safe.length?safe:cands);}}
  else if(mode==='hybrid40'){
   if(snake.length>40&&safe.length){pool=[safe.sort((a,b)=>cycOf(a)-cycOf(b))[0]];}
   else{const roomy=safe.filter(d=>flood(snake,[hx+DIRS[d][0],hy+DIRS[d][1]])>=snake.length);
        pool=roomy.length?roomy:(safe.length?safe:cands);}}
  if(!pool.length)return{died:true,at:k,steps,jumps};
  const pick=(mode.startsWith('hybrid')&&snake.length>50)?pool[0]:pool.sort((a,b)=>{
   const da=Math.abs(hx+DIRS[a][0]-food[0])+Math.abs(hy+DIRS[a][1]-food[1]);
   const db=Math.abs(hx+DIRS[b][0]-food[0])+Math.abs(hy+DIRS[b][1]-food[1]);
   return da-db||cycOf(b)-cycOf(a);})[0];
  if(!loopSafe(snake,food,pick))jumps++;
  const[ns,died,ate]=stepSnake(snake,food,pick);
  if(died)return{died:true,at:k,steps,jumps};
  snake=ns;steps++;if(ate)k++;
 }
 return{died:false,at:FD.length,steps,jumps};
}
console.log('greedy   :',JSON.stringify(run('greedy')));
console.log('hybrid60 :',JSON.stringify(run('hybrid')));
console.log('hybrid40 :',JSON.stringify(run('hybrid40')));
