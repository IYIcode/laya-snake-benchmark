# -*- coding: utf-8 -*-
"""限时快跑：环契约纯 CE 监督微调（老师软标签取 argmax 当硬标签）。
停机按秒预算：python _sft_fast.py --budget 2500
结束后写 _rlcd/run3/final/（含 temperature.json 校准）。评测/挂载交给后续命令。
"""
import argparse, json, os, random, time
import torch
import torch.nn.functional as F
from _rlcd_cycle import state_of, crit_of, SHORT, load_agent, collate_train_batch, save_ckpt, fit_one_temp, ORDER

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', default='_rlcd/run3')
    ap.add_argument('--base', default='convaiinnovations/laya')
    ap.add_argument('--budget', type=int, default=2500, help='训练秒预算')
    ap.add_argument('--n-items', dest='n_items', type=int, default=12000)
    ap.add_argument('--micro', type=int, default=8)
    ap.add_argument('--lr-enc', dest='lr_enc', type=float, default=5e-5)
    ap.add_argument('--lr-head', dest='lr_head', type=float, default=2e-4)
    args = ap.parse_args()
    t_start = time.time()
    device = torch.device('cuda')
    ag = load_agent(args.base)
    import huggingface_hub, os.path as op
    mdir = args.base if op.isdir(args.base) else huggingface_hub.snapshot_download(args.base)
    model = ag.model.to(device)
    cfg = ag.cfg; cfg['max_len'] = 512; cfg['head_max_len'] = 256

    items = torch.load(op.join(args.run, 'items.pt'), weights_only=False)
    random.Random(7).shuffle(items)
    calib = items[:300]; train_items = items[300:args.n_items]
    print(f'SFT {len(train_items)} items (hard label=argmax(teacher soft)), budget {args.budget}s', flush=True)

    pad = ag.tok.pad_token_id
    opt = torch.optim.AdamW([
        {'params': [p for n, p in model.named_parameters() if 'encoder.' in n], 'lr': args.lr_enc},
        {'params': [p for n, p in model.named_parameters() if 'encoder.' not in n], 'lr': args.lr_head},
    ], weight_decay=0.01)
    scaler = torch.amp.GradScaler('cuda', enabled=True)
    torch.manual_seed(11); random.Random(11).shuffle(train_items)
    model.train(); ptr = 0; step = 0; losses = []
    while True:
        if ptr + args.micro > len(train_items):
            random.Random(step).shuffle(train_items); ptr = 0
        chunk = train_items[ptr:ptr + args.micro]; ptr += args.micro
        b = collate_train_batch(chunk, pad)
        b = {k: v.to(device) for k, v in b.items()}
        with torch.autocast('cuda', dtype=torch.float16):
            logits, act = model(b['input_ids'], b['attention_mask'], b['marker_pos'], b['marker_mask'], b['qtype'])
        logits = logits.float(); mask = b['marker_mask']
        hard = b['target'].argmax(-1)                       # 老师软分布 argmax = 硬标签
        lmask = mask.gather(1, hard.unsqueeze(1)).squeeze(1) # 标签位必须是有效 marker
        lp = torch.log_softmax(logits.masked_fill(~mask, -1e4), -1)
        nll = -lp.gather(1, hard.unsqueeze(1)).squeeze(1)
        loss = nll[lmask.bool()].mean() if lmask.any() else 0.0 * logits.sum()
        scaler.scale(loss).backward(); scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True)
        step += 1; losses.append(float(loss))
        if step % 50 == 0:
            el = time.time() - t_start
            print(f'step{step} {el:.0f}s/{args.budget}s loss={sum(losses[-50:])/50:.4f} '
                  f'acc={float((hard==logits.masked_fill(~mask,-1e4).argmax(-1)).float().mean()):.3f}', flush=True)
            if el > args.budget: break
    print(f'train done: {step} steps {time.time()-t_start:.0f}s', flush=True)

    # 温度校准(300 条留出) + 落盘 final/
    model.eval(); preds = []
    with torch.no_grad():
        for i in range(0, len(calib), 16):
            ch = calib[i:i+16]; cb = collate_train_batch(ch, pad); cb = {k: v.to(device) for k, v in cb.items()}
            with torch.autocast('cuda', dtype=torch.float16):
                l, _ = model(cb['input_ids'], cb['attention_mask'], cb['marker_pos'], cb['marker_mask'], cb['qtype'])
            l = l.float().cpu().numpy()
            for ri, it in enumerate(ch):
                kk = len(it['markers']); preds.append((it['qtype'], l[ri, :kk], it['target']))
    temps = [1.0, 1.0, 1.0]
    for qt in range(3):
        sel = [(z, t) for q, z, t in preds if q == qt]
        if sel: temps[qt] = fit_one_temp(sel)
    final = os.path.join(args.run, 'final')
    save_ckpt(model, mdir, final)
    json.dump({'choice': temps[0], 'score': temps[1], 'noul': temps[2]}, open(os.path.join(final, 'temperature.json'), 'w'), indent=2)
    json.dump({'gen': 'cycle-sft-fast', 'mean': None, 'rep': 'cycle',
               'note': f'限时CE SFT {step}步/{args.budget}s预算, 硬标签=老师argmax'},
              open(os.path.join(final, 'evolution_meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'SAVED {final} temps={temps} total={time.time()-t_start:.0f}s', flush=True)

if __name__ == '__main__':
    main()
