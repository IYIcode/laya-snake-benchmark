
const DIRS={UP:[0,-1],DOWN:[0,1],LEFT:[-1,0],RIGHT:[1,0]},GW=12,GH=12;
let snake,food;
function landOf(nx,ny){
  if(nx<0||nx>=GW||ny<0||ny>=GH)return 'wall';
  const eat=(nx===food[0]&&ny===food[1]);
  const bodyCells=eat?snake:snake.slice(0,-1);
  if(bodyCells.some(s=>s[0]===nx&&s[1]===ny))return 'body';
  if(!eat&&snake[snake.length-1][0]===nx&&snake[snake.length-1][1]===ny)return 'vacating';
  return 'free';}
function optText(d){
  const [dx,dy]=DIRS[d], nx=snake[0][0]+dx, ny=snake[0][1]+dy;
  const dn=Math.abs(nx-food[0])+Math.abs(ny-food[1]), dc=Math.abs(snake[0][0]-food[0])+Math.abs(snake[0][1]-food[1]);
  const rel=dn<dc?'NEARER to food':(dn>dc?'FARTHER from food':'SAME distance');
  return `(${nx},${ny}) ${landOf(nx,ny)}, ${rel}`;}
const cases=JSON.parse(require('fs').readFileSync('_eq_cases.json','utf8'));
for(const c of cases){snake=c.snake;food=c.food;
  for(const d of ['UP','DOWN','LEFT','RIGHT']){
    const j=optText(d);
    if(j!==c.py[d]){console.log('MISMATCH',d,'js='+j,'py='+c.py[d]);process.exit(1)}}}
console.log('ALL-MATCH',cases.length,'cases');
