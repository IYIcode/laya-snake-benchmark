const fs=require('fs');
globalThis.location={search:''};globalThis.Worker=function(){this.onmessage=null;};
const src=fs.readFileSync('laya-snake-pk.html','utf8').match(/<script>([\s\S]*)<\/script>/)[1];
// 只用纯逻辑段（环境 + 两个本地选手 + perm 食物），eval 到 '// ── 选手 3/4/5' 之前
const code=src.slice(0,src.indexOf('// ── 选手 3/4/5'));
eval(code);
// perm 食物逻辑（和页面 newMatch/assignFood/nextFood 一致）
let perm=[];
function seedPerm(seed){perm=[];for(let y=0;y<GH;y++)for(let x=0;x<GW;x++)perm.push([x,y]);
  const r=mulberry32(seed);for(let i=perm.length-1;i>0;i--){const j=Math.floor(r()*(i+1));[perm[i],perm[j]]=[perm[j],perm[i]];}}
function assign(L){const occ=new Set(L.snake.map(s=>s[0]+','+s[1]));
  while(L.ptr<perm.length&&occ.has(perm[L.ptr][0]+','+perm[L.ptr][1]))L.ptr++;
  L.food=L.ptr<perm.length?perm[L.ptr]:null;}

const CAP=6000,STARVE=300,GW=12,GH=12;
const pols={rule3:(s,f)=>rule3Pick(s,f),bfs:(s,f)=>bfsPick(s,f,null),rand:(s,f,r)=>["UP","DOWN","LEFT","RIGHT"][Math.floor(r()*4)]};
let viol=0,offBoard=0,games=0;
for(let m=1;m<=400&&viol===0;m++){
  seedPerm((m*9301+49297)%233280);
  for(const pname of ['rule3','bfs','rand']){
    const r=mulberry32(m*131+7);
    let snake=[[6,6],[5,6],[4,6]],ptr=0,food=null,starve=0,score=0;
    assign0();function assign0(){const occ=new Set(snake.map(s=>s[0]+','+s[1]));
      while(ptr<perm.length&&occ.has(perm[ptr][0]+','+perm[ptr][1]))ptr++;food=ptr<perm.length?perm[ptr]:null;}
    for(let st=0;st<CAP&&starve<STARVE&&food;st++){
      // INVARIANT: 食物绝不在蛇身上
      if(snake.some(s=>s[0]===food[0]&&s[1]===food[1])){viol++;console.log('FOOD-ON-BODY',pname,'game',m,'step',st,'food',food,'len',snake.length);break;}
      // INVARIANT: 食物在界内
      if(food[0]<0||food[0]>=GW||food[1]<0||food[1]>=GH){offBoard++;break;}
      const d=pols[pname](snake,food,r);if(!d)break;
      const[ns,died,ate]=stepSnake(snake,food,d);
      if(died)break;snake=ns;
      if(ate){score++;starve=0;ptr++;assign0();}else starve++;
    }
    games++;
  }
}
console.log(viol===0&&offBoard===0?('PASS  food-never-on-body · '+games+' 局跑完 · 0 违规'):('FAIL viol='+viol+' offBoard='+offBoard));
