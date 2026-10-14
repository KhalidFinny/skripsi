#!/usr/bin/env python
"""DEEP DIVE: sapu panjang window smoothing + validasi split subjek.

Latar: `audit_peak_rank_casme2.py` menemukan DUA tuas pada resep asli notebook:
  - window smoothing lebih panjang (generasi 1: 28 tetap; generasi 2: 5% clamp 31)
    -> pipeline sekarang memakai 7 tetap
  - peringkat puncak menurut PROMINENCE (generasi 1), bukan NILAI
    -> pipeline sekarang memakai nilai

Skrip ini:
  1. Menyapu panjang window (tetap & persentase) x peringkat x top_k di SELURUH
     86 video, untuk melihat bentuk kurvanya.
  2. Memvalidasi konfigurasi teratas dengan SPLIT SUBJEK 2-fold: konfigurasi
     dipilih di satu paruh subjek, diukur di paruh lainnya (dan sebaliknya).
     Ini menutup jebakan "memilih parameter di data uji".

Cara pakai:
    .venv/bin/python scripts/audit_window_sweep_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from audit_peak_rank_casme2 import detect  # noqa: E402

WINDOWS = ['fix7', 'fix15', 'fix21', 'fix28', 'fix35', 'fix41', 'pct3', 'pct5', 'pct8']


def make_smoother(name: str):
    def fn(sig: np.ndarray) -> np.ndarray:
        n = len(sig)
        if name.startswith('fix'):
            w = int(name[3:])
        else:
            w = int(n * int(name[3:]) / 100)
        if w % 2 == 0:
            w += 1
        w = max(5, min(w, n - 1 if n % 2 == 0 else n - 2))
        if w < 4 or w >= n:
            return sig
        po = 2 if w <= 7 else (3 if w <= 15 else 4)
        return savgol_filter(sig, w, po)
    return fn


def load_data():
    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    out = {}
    for v, g in gt_by.items():
        p = bench.cache_path(bench.DEFAULT_SIGNAL_CACHE, Path(v))
        s = bench.load_cached_signals(p) if p else None
        if s:
            glob = np.nan_to_num(np.asarray(spot.build_global_signal(s), dtype=float), nan=0.0)
            if len(glob) >= 10:
                out[v] = (glob, g)
    return out


def score(prepared: dict, smooth_fn, ranking: str, top_k: int, k_std: float) -> dict:
    tp = fp = fn = ndet = 0
    for g, gt in prepared.values():
        sm = np.asarray(smooth_fn(g), dtype=float)
        h = float(sm.mean() + k_std * sm.std())
        det = detect(sm, top_k, h, ranking)
        ndet += len(det)
        p, f, f_ = bench.match_events(gt, det, 0)
        tp += len(p); fp += len(f); fn += len(f_)
    sc = bench.scores(tp, fp, fn)
    return {'precision': sc['precision'], 'recall': sc['recall'], 'f1': sc['f1'],
            'det_per_video': ndet / max(1, len(prepared))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--k-std', type=float, default=1.0)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_window_sweep_casme2')
    args = ap.parse_args()

    data = load_data()
    print(f'video: {len(data)}')
    subjects = sorted({Path(v).parent.name for v in data})
    print(f'subjek: {len(subjects)}')

    # ---- 1. sapu window di seluruh 86 video ----
    rows = []
    print(f"\n{'window':8s} {'ranking':11s} {'top_k':>6s} {'P':>7s} {'R':>7s} {'F1':>7s}")
    for wname in WINDOWS:
        sfn = make_smoother(wname)
        sm_cache = {v: np.asarray(sfn(g), dtype=float) for v, (g, _) in data.items()}
        for ranking in ('value', 'prominence'):
            for top_k in (5, 8):
                tp = fp = fn = ndet = 0
                for v, (_, gt) in data.items():
                    sm = sm_cache[v]
                    h = float(sm.mean() + args.k_std * sm.std())
                    det = detect(sm, top_k, h, ranking)
                    ndet += len(det)
                    p, f, f_ = bench.match_events(gt, det, 0)
                    tp += len(p); fp += len(f); fn += len(f_)
                sc = bench.scores(tp, fp, fn)
                rows.append({'window': wname, 'ranking': ranking, 'top_k': top_k,
                             'precision': sc['precision'], 'recall': sc['recall'],
                             'f1': sc['f1'], 'det_per_video': ndet / max(1, len(data))})
                print(f"{wname:8s} {ranking:11s} {top_k:6d} {sc['precision']:7.4f} "
                      f"{sc['recall']:7.4f} {sc['f1']:7.4f}", flush=True)
    df = pd.DataFrame(rows).sort_values('f1', ascending=False)

    # ---- 2. validasi split subjek 2-fold ----
    subj_parity = {s: i % 2 for i, s in enumerate(subjects)}
    folds = {
        'A_train/B_test': ({v: d for v, d in data.items() if subj_parity[Path(v).parent.name] == 0},
                           {v: d for v, d in data.items() if subj_parity[Path(v).parent.name] == 1}),
        'B_train/A_test': ({v: d for v, d in data.items() if subj_parity[Path(v).parent.name] == 1},
                           {v: d for v, d in data.items() if subj_parity[Path(v).parent.name] == 0}),
    }
    val_rows = []
    print("\n=== validasi split subjek (pilih di train, ukur di test) ===")
    for fname, (train, test) in folds.items():
        best = None
        for wname in WINDOWS:
            sfn = make_smoother(wname)
            for ranking in ('value', 'prominence'):
                for top_k in (5, 8):
                    r = score(train, sfn, ranking, top_k, args.k_std)
                    if best is None or r['f1'] > best[0]:
                        best = (r['f1'], wname, ranking, top_k)
        _, wname, ranking, top_k = best
        test_r = score(test, make_smoother(wname), ranking, top_k, args.k_std)
        val_rows.append({'fold': fname, 'picked_window': wname, 'picked_ranking': ranking,
                         'picked_top_k': top_k, 'train_f1': best[0],
                         'test_f1': test_r['f1'], 'test_precision': test_r['precision'],
                         'test_recall': test_r['recall'], 'n_train': len(train), 'n_test': len(test)})
        print(f"{fname}: pilih {wname}/{ranking}/k{top_k} (train F1 {best[0]:.4f}) "
              f"-> test F1 {test_r['f1']:.4f} (P {test_r['precision']:.4f} R {test_r['recall']:.4f})")

    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / 'sweep_full.csv', index=False)
    pd.DataFrame(val_rows).to_csv(args.out / 'validation_split.csv', index=False)
    lines = ['# Sapu window + validasi split subjek — CAS(ME)^2', '',
             f'k_std = {args.k_std}, toleransi 0 frame, agregasi global.', '',
             '## 15 teratas (seluruh 86 video)', '',
             '| window | ranking | top_k | precision | recall | F1 | det/video |',
             '|---|---|---|---|---|---|---|']
    for _, r in df.head(15).iterrows():
        lines.append(f"| {r['window']} | {r['ranking']} | {int(r['top_k'])} | {r['precision']:.4f} | "
                     f"{r['recall']:.4f} | {r['f1']:.4f} | {r['det_per_video']:.1f} |")
    lines += ['', '## Validasi split subjek 2-fold', '',
              '| fold | window terpilih | ranking | top_k | train F1 | test F1 | test P | test R |',
              '|---|---|---|---|---|---|---|---|']
    for r in val_rows:
        lines.append(f"| {r['fold']} | {r['picked_window']} | {r['picked_ranking']} | {int(r['picked_top_k'])} | "
                     f"{r['train_f1']:.4f} | {r['test_f1']:.4f} | {r['test_precision']:.4f} | {r['test_recall']:.4f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
