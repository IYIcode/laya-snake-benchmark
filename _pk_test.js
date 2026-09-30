const fs=require('fs');
const html=fs.readFileSync('laya-snake-pk.html','utf8');
const src=html.match(/<script>([\s\S]*)<\/script>/)[1];
// 只取函数定义部分（到 bridgePick 之前），跳过 DOM/主循环
const cut=src.indexOf('// ── 赛道');
eval(src.slice(0,cut));
// 快速冒烟：本地跑 N 局 rule3 / bfs，220 步封顶
function playLocal(pick,cap,seed){let rng=mulberry32(seed);let snake=[[6,6],[5,6],[4,6]];
  // 用 bfs 预演生成公共食物序列
  let sim=[[6,6],[5,6],[4,6]],q=[];
  let s2=mulberry32(seed+777);
  while(q.length<cap){const f=placeFood(s2,sim);q.push(f);const d=bfsPick(s