// CDP smoke test: launch headless Chrome, navigate, screenshot 1280x720
import { spawn } from 'node:child_process';
import fs from 'node:fs';

const CHROME = 'C:\\Users\\IYI\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9333;
const UDD = 'C:\\Users\\IYI\\Documents\\Qoder\\2026-09-25\\6c9fe21d\\_dev\\.chrome-profile';

const child = spawn(CHROME, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${UDD}`,
  '--no-first-run', '--no-default-browser-check',
  '--window-size=1280,720',
  '--hide-scrollbars',
  '--force-device-scale-factor=1',
  '--allow-file-access-from-files',
  '--disable-extensions',
  'about:blank',
], { stdio: 'ignore', detached: true, windowsHide: true });
child.unref();
console.log('spawned pid', child.pid);

async function waitVersion(ms = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return await r.json();
    } catch {}
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error('devtools not up');
}

const ver = await waitVersion();
console.log('browser:', ver['Browser']);

let list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
let target = list.find(t => t.type === 'page');
console.log('targets:', list.map(t => t.type + ':' + t.url).join(', '));
if (!target) throw new Error('no page target');

const ws = new WebSocket(target.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

await send('Page.enable');
await send('Runtime.enable');
const html = `<!doctype html><meta charset=utf-8><body style="margin:0;background:#0b0e14">
<canvas id=c width=200 height=200></canvas>
<script>const x=document.getElementById('c').getContext('2d');x.fillStyle='#3ecf8e';x.fillRect(20,20,160,160);
x.fillStyle='#f0b429';x.font='28px "Microsoft YaHei"';x.fillText('贪吃蛇 141',20,120);document.title='OK';</script>`;
const url = 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
await send('Page.navigate', { url });
await new Promise(r => setTimeout(r, 1200));
const r = await send('Runtime.evaluate', { expression: 'document.title', returnByValue: true });
console.log('title =', JSON.stringify(r.result?.result?.value));
const shot = await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: 1280, height: 720, scale: 1 }, captureBeyondViewport: false });
if (!shot.result?.data) { console.log('SHOT FAIL', JSON.stringify(shot).slice(0, 500)); process.exit(1); }
fs.writeFileSync('_dev/cdp_test.png', Buffer.from(shot.result.data, 'base64'));
console.log('screenshot bytes', Buffer.from(shot.result.data, 'base64').length);
ws.close();
try { process.kill(child.pid); } catch {}
