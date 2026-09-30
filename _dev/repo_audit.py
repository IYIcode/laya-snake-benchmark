# -*- coding: utf-8 -*-
"""估算「按 .gitignore 之后仓库会包含什么」：文件数、总体积、最大的几个文件。"""
import fnmatch
import pathlib

ROOT = pathlib.Path(".")
IGNORE_DIRS = {"_graveyard", "_rlcd", "__pycache__", "_ppt_video", "_ppt_video3", "_ppt_video4",
               "_ppt_audio", "_ppt_audio3", "_ppt_audio4", "vibe_images", "_ppt_shots", "_shots",
               "_pkgs", "_dev/_pkgs", "_dev/_pylibs", "_dev/_biliup_src", "_dev/biliup",
               "_dev/frame", "_dev/lane_frames", "_dev/slide6_frames", "_dev/final_check"}
IGNORE_GLOBS = ["*.safetensors", "*.bin", "*.pt", "*.ckpt", "*.onnx", "*.zstd", "*.wav", "*.mp3",
                "_dev/lane_preview_*.png", "_dev/slide6_preview_*.png", "_dev/bili_*.log",
                "_dev/bili_*.json", "_dev/*.log", "bridge*.log", "static_*.log", "evolve_v2*.log",
                "rl_gen5*.log", "*.pyc", ".DS_Store", "Thumbs.db", "_dev/cdp_test.png",
                "_dev/slide6_board_crop.png", "_dev/chrome_shot.png", "_dev/audio4_durations.json"]
KEEP = {"laya-ppt-3分钟.mp4"}

files = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if any(rel == d or rel.startswith(d + "/") for d in IGNORE_DIRS):
        continue
    if rel in KEEP:
        files.append((rel, p.stat().st_size))
        continue
    if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(p.name, g) for g in IGNORE_GLOBS):
        continue
    files.append((rel, p.stat().st_size))

files.sort(key=lambda x: -x[1])
total = sum(s for _, s in files)
print(f"入库文件数: {len(files)}   合计 {total/1024/1024:.1f} MB")
print("最大的 12 个:")
for rel, s in files[:12]:
    print(f"  {s/1024/1024:8.2f} MB  {rel}")
print("关键档案是否在库:")
for k in ["_myrun_data.json", "_cockpit_replay.json", "_jumpfood_1002.json", "_prompt_ab.json",
          "_me_ledger_result.json", "_recent_log.json", "laya-snake-cockpit.html",
          "laya-ppt-3分钟.mp4", "README.md", "VERIFY.md", "index.html",
          "_dev/summarize_tune_runs.py", "_tune_runs/fdpen6.json"]:
    print(f"  {'✅' if any(r == k for r, _ in files) else '❌'} {k}")
