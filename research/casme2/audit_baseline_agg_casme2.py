#!/usr/bin/env python
"""AUDIT GABUNGAN: acuan POC (abs vs seq) x agregasi (global vs per-ROI).

Melanjutkan `baseline_probe_casme2.py`. Cache-nya menyimpan sinyal per ROI untuk
5 acuan: abs, seq, lag10, lag30, lag60. Skrip ini mengevaluasi "apex precision@K"
untuk DUA cara agregasi:

  global   : rata-rata antar 5 ROI -> satu sinyal (cara NOTEBOOK ASLI)
  per_roi  : tiap ROI dideteksi sendiri (cara pipeline SEKARANG)

Kombinasi (seq + global) = konfigurasi notebook asli, sejauh yang bisa diuji
tanpa mengubah block_size/ukuran target.

Cara pakai:
    .venv/bin/python scripts/audit_baseline_agg_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import baseline_probe_casme2 as probe  # noqa: E402
import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexSmoother  # noqa: E402


def peaks_ranked(signal: np.ndarray, adaptive: bool) -> np.ndarray:
    """Puncak (indeks sinyal) diurutkan menurun menurut nilai."""
    sm = ApexSmoother.smooth(signal.tolist()) if adaptive else signal
    sm = np.asarray(sm, dtype=float)
    if len(sm) < 10:
        return np.array([], dtype=int)
    pk, _ = find_peaks(sm, distance=1)
    if len(pk) == 0:
        return np.array([], dtype=int)
    return pk[np.argsort(-sm[pk])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', type=Path, default=probe.DEFAULT_CACHE)
    ap.add_argument('--tolerance', type=int, default=10)
    ap.add_argument('--adaptive', action='store_true',
                    help='pakai smoother adaptif ASLI (5%%, clamp 31) bukan tetap 7')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_baseline_agg_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    videos = sorted(gt_by_video)
    regions = list(spot.config.regions)

    sig_cache: dict[str, dict] = {}
    for v in videos:
        s = probe.load(probe.cache_file(args.cache_dir, v))
        if s is not None:
            sig_cache[v] = s
    print(f'video dengan cache: {len(sig_cache)}')
    if not sig_cache:
        raise SystemExit('cache kosong: jalankan baseline_probe_casme2.py dulu')

    rows = []
    print(f"\n{'acuan':7s} {'agregasi':9s} {'puncak/video':>12s} "
          f"{'P@1':>7s} {'P@2':>7s} {'P@5':>7s} {'P@10':>7s} {'P@20':>7s}")
    for mode in probe.MODES:
        for agg in ('global', 'per_roi'):
            per_k = {k: [] for k in (1, 2, 5, 10, 20)}
            n_peaks = 0
            n_gt = 0
            n_video = 0
            for v, sig in sig_cache.items():
                g = gt_by_video[v]
                keys = [f'{mode}__{r}' for r in regions if f'{mode}__{r}' in sig]
                if not keys:
                    continue
                n_video += 1
                if agg == 'global':
                    n = min(len(sig[k]) for k in keys)
                    arr = np.mean([np.asarray(sig[k][:n], dtype=float) for k in keys], axis=0)
                    ranked = peaks_ranked(arr, args.adaptive)
                    n_peaks += len(ranked)
                    if len(ranked) == 0:
                        continue
                    for x in g:
                        n_gt += 1
                        dist = np.abs((ranked + 1) - x['apex'])
                        hit = np.flatnonzero(dist <= args.tolerance)
                        first = int(hit[0]) if hit.size else -1
                        for k in per_k:
                            per_k[k].append(1 if 0 <= first < k else 0)
                else:
                    for key in keys:
                        ranked = peaks_ranked(np.asarray(sig[key], dtype=float), args.adaptive)
                        n_peaks += len(ranked)
                        if len(ranked) == 0:
                            continue
                        for x in g:
                            n_gt += 1
                            dist = np.abs((ranked + 1) - x['apex'])
                            hit = np.flatnonzero(dist <= args.tolerance)
                            first = int(hit[0]) if hit.size else -1
                            for k in per_k:
                                per_k[k].append(1 if 0 <= first < k else 0)
            r = {'baseline': mode, 'agg': agg, 'peaks_per_video': n_peaks / max(1, n_video),
                 'n_gt': n_gt, **{f'P@{k}': float(np.mean(v)) if v else float('nan')
                                  for k, v in per_k.items()}}
            rows.append(r)
            print(f"{mode:7s} {agg:9s} {r['peaks_per_video']:12.0f} {r['P@1']:7.4f} "
                  f"{r['P@2']:7.4f} {r['P@5']:7.4f} {r['P@10']:7.4f} {r['P@20']:7.4f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Audit acuan x agregasi pada CAS(ME)^2', '',
             f'- toleransi apex: +/-{args.tolerance} frame',
             f'- smoother: {"ADAPTIF asli (5%, clamp 31)" if args.adaptive else "tetap 7 (sekarang)"}',
             '',
             '`seq` + `global` = konfigurasi notebook spotting ASLI. '
             '`abs` + `per_roi` = pipeline sekarang.',
             '',
             '| acuan | agregasi | puncak/video | P@1 | P@2 | P@5 | P@10 | P@20 |',
             '|---|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['baseline']} | {r['agg']} | {r['peaks_per_video']:.0f} | "
                     f"{r['P@1']:.4f} | {r['P@2']:.4f} | {r['P@5']:.4f} | "
                     f"{r['P@10']:.4f} | {r['P@20']:.4f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
