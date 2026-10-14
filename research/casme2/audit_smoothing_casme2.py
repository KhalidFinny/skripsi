#!/usr/bin/env python
"""AUDIT: apakah perubahan smoothing (dan ROI/block_size) merusak spotting?

Perubahan yang ditemukan vs backup 2026-08-25:
  1. apex_smoother: 5% panjang sinyal (clamp 31)  ->  TETAP 7 frame
  2. roi_config: mata_kiri = range(17,22)+range(36,42) (alis+mata)  ->  range(36,42) (mata saja)
  3. roi_config: block_size 7  ->  9

Skrip ini menguji (1) memakai cache sinyal yang sudah ada (murah), lalu mengukur
"apex precision@K": proporsi apex GT yang punya puncak dalam +/-10 frame di
antara K puncak teratas ROI menurut nilai sinyal. Ini mengukur apakah puncak
ekspresi bisa diperingkat cukup tinggi, tanpa bergantung pada ambang.

Cara pakai:
    .venv/bin/python scripts/audit_smoothing_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks, savgol_filter

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
import rich_signals_casme2 as rich  # noqa: E402


def smooth_current(sig: np.ndarray) -> np.ndarray:
    """Perilaku sekarang: window tetap 7 (min dengan panjang sinyal)."""
    w = min(7, len(sig))
    if w % 2 == 0:
        w -= 1
    if w < 3 or w >= len(sig):
        return sig
    return savgol_filter(sig, window_length=w, polyorder=min(2, w - 1))


def smooth_original(sig: np.ndarray) -> np.ndarray:
    """Perilaku ASLI: 5% panjang sinyal, clamp [5, 31]."""
    w = int(len(sig) * 0.05)
    if w % 2 == 0:
        w += 1
    w = max(5, min(w, 31))
    if w >= len(sig):
        return sig
    return savgol_filter(sig, window_length=w, polyorder=min(3, w - 1))


def smooth_fixed(sig: np.ndarray, window: int) -> np.ndarray:
    w = window
    if w % 2 == 0:
        w += 1
    if w < 3 or w >= len(sig):
        return sig
    return savgol_filter(sig, window_length=w, polyorder=min(3, w - 1))


def evaluate(frames: list, gt_by_video: dict, smooth_fn, tol: int) -> dict:
    per_k = {k: [] for k in (1, 2, 5, 10, 20)}
    n_gt = 0
    n_peaks = 0
    for v, sig in frames:
        g = gt_by_video[v]
        for roi in spot.config.regions:
            key = f'{roi}__mean_m'
            if key not in sig:
                continue
            sm = np.asarray(smooth_fn(np.asarray(sig[key], dtype=float)), dtype=float)
            if len(sm) < 10:
                continue
            pk, _ = find_peaks(sm, distance=1)
            n_peaks += len(pk)
            if len(pk) == 0:
                continue
            ranked = pk[np.argsort(-sm[pk])]
            for x in g:
                n_gt += 1
                dist = np.abs((ranked + 1) - x['apex'])
                hit = np.flatnonzero(dist <= tol)
                first = int(hit[0]) if hit.size else -1
                for k in per_k:
                    per_k[k].append(1 if 0 <= first < k else 0)
    return {'n_gt': n_gt,
            'peaks_per_video': n_peaks / max(1, len(frames)),
            **{f'P@{k}': float(np.mean(v)) if v else float('nan') for k, v in per_k.items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tolerance', type=int, default=10)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_smoothing_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    frames = []
    for v in sorted(gt_by_video):
        sig = rich.load(rich.cache_file(rich.DEFAULT_CACHE, v))
        if sig is not None:
            frames.append((v, sig))
    print(f'video dengan cache sinyal: {len(frames)}')

    variants = [
        ('sekarang: tetap 7', smooth_current),
        ('ASLI: 5% clamp 31', smooth_original),
        ('tetap 15', lambda s: smooth_fixed(s, 15)),
        ('tetap 31', lambda s: smooth_fixed(s, 31)),
    ]
    rows = []
    print(f"\n{'varian':22s} {'puncak/video':>12s} {'P@1':>7s} {'P@2':>7s} "
          f"{'P@5':>7s} {'P@10':>7s} {'P@20':>7s}")
    for name, fn in variants:
        r = evaluate(frames, gt_by_video, fn, args.tolerance)
        rows.append({'variant': name, **r})
        print(f"{name:22s} {r['peaks_per_video']:12.0f} {r['P@1']:7.4f} {r['P@2']:7.4f} "
              f"{r['P@5']:7.4f} {r['P@10']:7.4f} {r['P@20']:7.4f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Audit smoothing pada CAS(ME)^2', '',
             f'- toleransi apex: +/-{args.tolerance} frame',
             f'- n GT: {rows[0]["n_gt"]}',
             '',
             '`P@K` = proporsi apex GT yang punya puncak dalam K puncak teratas ROI. '
             'Acak ~ K / puncak_per_video.',
             '',
             '| varian | puncak/video | P@1 | P@2 | P@5 | P@10 | P@20 |',
             '|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f'| {r["variant"]} | {r["peaks_per_video"]:.0f} | {r["P@1"]:.4f} | '
                     f'{r["P@2"]:.4f} | {r["P@5"]:.4f} | {r["P@10"]:.4f} | {r["P@20"]:.4f} |')
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
