// 在 DSH 会话日志（.zstd 压缩）里找 Qoder 推广/邀请链接
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const ROOT = 'C:\\Users\\IYI\\.dsh\\sessions';
const PATTERNS = [/u9nr6jcf/i, /referral[_a-z]*=[A-Za-z0-9_-]{4,}/i, /qoder\.com\/[^\s"'\\]{0,120}/i, /邀请码[^\n]{0,60}/g];

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.zstd')) out.push(p);
  }
  return out;
}

const files = walk(ROOT);
console.log('会话文件数:', files.length);
let hits = 0;
for (const f of files) {
  let txt;
  try {
    txt = zlib.zstdDecompressSync(fs.readFileSync(f)).toString('utf8');
  } catch (e) {
    console.log('  解压失败', path.basename(f), String(e).slice(0, 80));
    continue;
  }
  for (const re of PATTERNS) {
    re.lastIndex = 0;
    const m = txt.match(re);
    if (m) {
      hits++;
      for (const s of m.slice(0, 4)) {
        const i = txt.indexOf(s);
        console.log(`${path.basename(f)}  [${re.source}]  …${txt.slice(Math.max(0, i - 70), i + s.length + 70).replace(/\s+/g, ' ')}…`);
      }
    }
  }
}
console.log(hits ? `命中 ${hits} 处` : '没有找到任何 Qoder 链接/邀请码');
