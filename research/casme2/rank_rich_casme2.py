#!/usr/bin/env python
"""Perbandingan jujur di SEMUA video CAS(ME)^2: kandidat PUNCAK vs JENDELA.

Memakai cache sinyal kaya (`rich_signals_casme2.py`), jadi cepat dan tidak
menghitung ulang POC. Fitur per kandidat IDENTIK dengan `window_spot_casme2.py`
(mean/std/max/range/slope per ROI x sinyal), yang berbeda hanya CARA memilih
kandidat:
  - 'peak'   : hanya di sekitar puncak (detektor yang dipakai pipeline)
  - 'window' : setiap titik dengan langkah `stride`

Tujuannya memisahkan dua hal yang sebelumnya tercampur: apakah yang gagal
pemilihan kandidat, atau fiturnya.

PENTING: hasil subset kecil TERBUKTI tidak stabil (window=16 memberi AUC 0,71
pada 20 video tapi 0,60 pada 86). Karena itu skrip ini selalu memakai semua
video yang ada di cache dan tidak menyediakan `--limit`.

Cara pakai:
    .venv/bin/python scripts/rank_rich_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import rich_signals_casme2 as rich  # noqa: E402
import window_spot_casme2 as win  # noqa: E402

DEFAULT_OUT = ROOT / 'output/training/rank_rich_casme2'


def peak_centers(sig: dict[str, np.ndarray], size: int) -> np.ndarray:
    """Titik tengah kandidat = puncak mean_m tiap ROI (detektor yang sama)."""
    centers = []
    for key, arr in sig.items():
        if not key.endswith('__mean_m'):
            continue
        a = np.asarray(arr, dtype=float)
        if len(a) < 10:
            continue
        pk, _ = find_peaks(a, distance=1, height=a.mean() + a.std(),
                           prominence=max(0.04 * (a.max() - a.min()), 0.005))
        centers.extend(int(i) for i in pk)
    if not centers:
        return np.array([], dtype=int)
    return np.unique(np.clip(np.asarray(centers), 0, len(next(iter(sig.values()))) - 1))


def build_peak_rows(video: str, sig: dict[str, np.ndarray], gt: list[dict],
                    size: int) -> pd.DataFrame:
    """Fitur jendela yang SAMA seperti window_spot, tapi hanya di titik puncak."""
    centers = peak_centers(sig, size)
    if centers.size == 0:
        return pd.DataFrame()
    half = size // 2
    n = len(next(iter(sig.values())))
    cols: dict[str, np.ndarray] = {}
    for key, arr in sig.items():
        a = np.asarray(arr, dtype=float)
        # vektor: mean/std/max/range/slope pada jendela di sekitar puncak
        means, stds, maxs, rngs, slopes = [], [], [], [], []
        for c in centers:
            lo, hi = max(0, int(c) - half), min(n, int(c) + half)
            s = a[lo:hi]
            if s.size == 0:
                means.append(np.nan); stds.append(np.nan); maxs.append(np.nan)
                rngs.append(np.nan); slopes.append(0.0)
                continue
            mid = s.size // 2
            means.append(float(s.mean())); stds.append(float(s.std()))
            maxs.append(float(s.max())); rngs.append(float(s.max() - s.min()))
            slopes.append(float(s[mid:].mean() - s[:mid].mean()) if mid else 0.0)
        cols[f'{key}__mean'] = np.asarray(means)
        cols[f'{key}__std'] = np.asarray(stds)
        cols[f'{key}__max'] = np.asarray(maxs)
        cols[f'{key}__range'] = np.asarray(rngs)
        cols[f'{key}__slope'] = np.asarray(slopes)
    d = pd.DataFrame(cols)
    d['video'] = video
    d['center'] = centers
    d['label'] = [int(any(x['onset'] <= int(c) <= x['offset'] for x in gt)) for c in centers]
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', type=Path, default=rich.DEFAULT_CACHE)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--window', type=int, default=32)
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}

    frames = []
    for v in sorted(gt_by_video):
        sig = rich.load(rich.cache_file(args.cache_dir, v))
        if sig is None:
            continue
        d = build_peak_rows(v, sig, gt_by_video[v], args.window)
        if not d.empty:
            frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    meta = ['video', 'center', 'label']
    cols = [c for c in d.columns if c not in meta]
    X = d[cols].to_numpy(float)
    y = d['label'].to_numpy()
    g = d['video'].to_numpy()
    print(f'kandidat PUNCAK: {len(d)} ({len(d)/d.video.nunique():.0f}/video) | '
          f'positif {y.sum()} ({y.mean():.4f}) | fitur {len(cols)} | video {d.video.nunique()}')

    oof = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, g):
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_depth=3)
        m.fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    auc = roc_auc_score(y, oof)
    print(f'AUC = {auc:.4f}')

    order = np.argsort(-oof)
    ys = y[order]
    rows = []
    for budget in (3.6, 20, 40, 80, 160, 320):
        k = int(budget * d.video.nunique())
        if k >= len(ys):
            break
        tp = int(ys[:k].sum()); prec = tp / k; rec = tp / y.sum()
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append({'budget': budget, 'precision': prec, 'recall': rec, 'f1': f1})
        print(f'  budget {budget:5.1f}/video: P={prec:.4f} R={rec:.4f} F1={f1:.4f}')

    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    best = max(rows, key=lambda r: r['f1'])
    print(f'\nF1 terbaik (puncak, fitur kaya, SEMUA video) = {best["f1"]:.4f} @ {best["budget"]}/video')
    print(f'Keluaran: {args.out}/summary.csv')


if __name__ == '__main__':
    main()
