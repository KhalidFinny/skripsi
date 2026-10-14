#!/usr/bin/env python
"""DEEP DIVE: apakah sinyal didominasi DRIFT, dan apakah normalisasi lokal menolong?

Sinyal POC-ABS dengan acuan frame-0 mengukur pergeseran KUMULATIF dari awal
video. Di video panjang CAS(ME)^2 (median 77 detik) itu berarti sinyal memuat
ayunan lambat (kepala bergeser, postur berubah) yang puncaknya jauh lebih besar
dari micro-expression. Akibatnya puncak ekspresi kalah saat diambil top-K.

Skrip ini menguji beberapa transformasi sinyal (semua memakai cache yang sudah
ada) lalu mengukur F1 dengan protokol pencocokan milik benchmark:

  raw     : sinyal apa adanya (pembanding)
  hp      : high-pass  = sinyal - rata-rata bergerak (window W)
  zscore  : (sinyal - rata-rata bergerak) / simpangan bergerak
  deriv   : selisih antar frame
  ratio   : sinyal / rata-rata bergerak

Agregasi global (cara notebook asli), top_k diuji beberapa nilai.

Cara pakai:
    .venv/bin/python scripts/audit_signal_transform_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexSmoother  # noqa: E402


def moving_avg(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1:
        return x.copy()
    kernel = np.ones(w) / w
    pad = w // 2
    xp = np.pad(x, pad, mode='edge')
    return np.convolve(xp, kernel, mode='valid')[:len(x)]


def transform(x: np.ndarray, name: str, w: int) -> np.ndarray:
    if name == 'raw':
        return x
    if name == 'hp':
        return x - moving_avg(x, w)
    if name == 'zscore':
        m = moving_avg(x, w)
        s = np.sqrt(np.maximum(moving_avg((x - m) ** 2, w), 1e-9))
        return (x - m) / s
    if name == 'deriv':
        return np.abs(np.diff(x, prepend=x[0]))
    if name == 'ratio':
        m = moving_avg(x, w)
        return x / np.maximum(m, 1e-9)
    raise ValueError(name)


def detect(sig: np.ndarray, top_k: int) -> list[dict]:
    sm = np.asarray(ApexSmoother.smooth(sig.tolist()), dtype=float)
    h = float(sm.mean() + sm.std())
    det = spot.ApexPhase(distance_threshold=1, prominence_threshold=0.005, cutoff_ratio=0.3)
    ap = det.find_top_k_apex(sm.tolist(), k=top_k, height=h)
    ph = det.find_phase(sm.tolist(), ap) if ap else {}
    out = []
    for a in ap:
        p = ph.get(a)
        if p is None:
            continue
        if int(p['end'] - p['start']) < 2:
            continue
        out.append({'onset': spot.signal_index_to_frame_index(int(p['start'])),
                    'apex': spot.signal_index_to_frame_index(int(a)),
                    'offset': spot.signal_index_to_frame_index(int(p['end'])),
                    'region': 'global'})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--window', type=int, nargs='+', default=[31, 101, 301])
    ap.add_argument('--top-k', type=int, nargs='+', default=[1, 5, 10])
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_signal_transform_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    data = {}
    for v, g in gt_by.items():
        p = bench.cache_path(bench.DEFAULT_SIGNAL_CACHE, Path(v))
        s = bench.load_cached_signals(p) if p else None
        if s:
            data[v] = (s, g)
    print(f'video: {len(data)}')

    rows = []
    variants = [('raw', 1)] + [(t, w) for t in ('hp', 'zscore', 'ratio') for w in args.window] + [('deriv', 1)]
    print(f"\n{'transform':16s} {'top_k':>6s} {'P':>7s} {'R':>7s} {'F1':>7s} {'det/video':>10s}")
    for name, w in variants:
        for k in args.top_k:
            tp = fp = fn = 0
            ndet = 0
            for v, (s, g) in data.items():
                glob = np.asarray(spot.build_global_signal(s), dtype=float)
                if len(glob) < 10:
                    continue
                tr = transform(glob, name, w)
                det = detect(np.nan_to_num(tr, nan=0.0), k)
                ndet += len(det)
                pairs, f, f_ = bench.match_events(g, det, 0)
                tp += len(pairs); fp += len(f); fn += len(f_)
            sc = bench.scores(tp, fp, fn)
            rows.append({'transform': name, 'window': w, 'top_k': k,
                         'precision': sc['precision'], 'recall': sc['recall'], 'f1': sc['f1'],
                         'det_per_video': ndet / max(1, len(data))})
            tag = f'{name}' + (f'(w={w})' if name in ('hp', 'zscore', 'ratio') else '')
            print(f"{tag:16s} {k:6d} {sc['precision']:7.4f} {sc['recall']:7.4f} "
                  f"{sc['f1']:7.4f} {ndet/max(1,len(data)):10.1f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Audit transformasi sinyal pada CAS(ME)^2', '',
             'Agregasi global (cara notebook asli). Toleransi 0 frame.',
             '', '| transform | window | top_k | precision | recall | F1 | det/video |',
             '|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['transform']} | {r['window']} | {r['top_k']} | {r['precision']:.4f} | "
                     f"{r['recall']:.4f} | {r['f1']:.4f} | {r['det_per_video']:.1f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
