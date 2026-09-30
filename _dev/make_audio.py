import asyncio, re, sys, pathlib
import edge_tts

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "laya-ppt-讲稿.md"
OUT = ROOT / "_ppt_audio"
OUT.mkdir(exist_ok=True)
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+10%"

text = SRC.read_text(encoding="utf-8")
# 只取 17 页正文，丢掉「备用答疑弹药」
text = text.split("---\n### 备用答疑弹药")[0]

pages = {}
for m in re.finditer(r"^## 第 (\d+) 页.*?$(.*?)(?=^## 第 |\Z)", text, re.M | re.S):
    n = int(m.group(1))
    body = m.group(2)
    body = re.sub(r"^>.*$", "", body, flags=re.M)          # 舞台提示行
    body = body.replace("（", "(").replace("）", ")")
    body = re.sub(r"\([^)]*?操作提示[^)]*?\)", "", body)
    body = re.sub(r"\([^)]*?\)", "", body)                   # 去掉所有括注舞台提示
    body = body.replace("**", "")
    body = re.sub(r"#[^\n]*", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    if body:
        pages[n] = body

async def gen(n, t):
    fn = OUT / f"p{n:02d}.mp3"
    await edge_tts.Communicate(t, VOICE, rate=RATE).save(str(fn))
    print(f"p{n:02d} {len(t)}字 -> {fn.name}", flush=True)

async def main():
    await asyncio.gather(*(gen(n, t) for n, t in sorted(pages.items())))

missing = [i for i in range(1, 18) if i not in pages]
if missing:
    sys.exit(f"缺页: {missing}")
asyncio.run(main())
print("完成: 17 段")
