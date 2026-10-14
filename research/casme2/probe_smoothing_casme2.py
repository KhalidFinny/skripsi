#!/usr/bin/env python
"""Uji pengaruh PERATAAN TEMPORAL pada jumlah puncak & peringkat ekspresi.

Temuan: sinyal POC-ABS (acuan frame-0) berosilasi sangat kuat sehingga
menghasilkan ~623 puncak per video, padahal GT hanya ~3,6 ekspresi. Kalau
puncaknya sebagian besar derau, perataan lebih kuat seharusnya mengurangi
puncak palsu tanpa menghapus ekspresi (micro-expression CAS(ME)^2 ~13 frame
pada 30 fps).

Uji ini memakai cache sinyal (tanpa hitung ulang POC) dan hanya mengubah
perataan + ambang, jadi cepat.

Cara pakai:
    .venv/bin/python scripts/probe_smoothing_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402


def smooth(sig: np.ndarray, window: int, poly: int) -> np.ndarray:
    if window < 3 or window >= len(sig):
        return sig
    if window % 2 == 0:
        window -= 1
    return savgol_filter(sig, window_length=window, polyorder=min(poly, window - 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--windows', type=int, nargs='+', default=[7, 15, 25, 41])
    ap.add_argument('--height-k', type=float, nargs='+', default=[1.0, 2.0, 3.0],
                    help='ambang = mean + k*std')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/probe_smooth_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    sigs = {}
    for v in sorted(gt_by_video):
        cp = bench.cache_path(bench.DEFAULT_SIGNAL_CACHE, Path(v))
        s = bench.load_cached_signals(cp) if cp else None
        if s:
            sigs[v] = s
    print(f'video dgn sinyal cache: {len(sigs)} | GT: {len(gt)}')

    rows = []
    for win in args.windows:
        for hk in args.height_k:
            # kumpulkan puncak semua video dulu
            peaks = {}
            n_pk = 0
            for v, s in sigs.items():
                lst = []
                for r, sig in s.items():
                    sm = smooth(np.asarray(sig, float), win, 3)
                    pk, _ = find_peaks(sm, distance=1, height=sm.mean() + hk * sm.std())
                    lst += [(int(i) + 1, float(sm[i]), r) for i in pk]
                peaks[v] = lst
                n_pk += len(lst)
            # peringkat: berapa ekspresi punya puncak beririsan, dan peringkatnya
            rq, covered = [], 0
            for v, g in gt_by_video.items():
                lst = peaks.get(v, [])
                if not lst:
                    continue
                lst_sorted = sorted(lst, key=lambda x: -x[1])
                rank_of = {}
                for k, (f, val, r) in enumerate(lst_sorted):
                    rank_of.setdefault(f, k)
                for x in g:
                    cand = [(f, rank_of[f]) for f, val, r in lst
                            if x['onset'] - 6 <= f <= x['offset'] + 6]
                    if cand:
                        covered += 1
                        rq.append(min(k for _, k in cand) / max(1, len(lst)))
            rows.append({
                'window': win, 'height_k': hk,
                'peaks_per_video': n_pk / max(1, len(sigs)),
                'covered': covered, 'coverage': covered / len(gt),
                'median_rank_pct': float(np.median(rq)) if rq else float('nan'),
            })
            print(f"  win={win:3d} hk={hk:.1f}: puncak/video={n_pk/max(1,len(sigs)):7.1f} "
                  f"coverage={covered/len(gt):.3f} median_rank={np.median(rq) if rq else float('nan'):.3f}",
                  flush=True)

    d = pd.DataFrame(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    d.to_csv(args.out / 'summary.csv', index=False)
    print(f'\nKeluaran: {args.out}/summary.csv')
    print('\nBacaan: makin kecil median_rank_pct makin baik (0 = puncak ekspresi '
          'selalu peringkat 1). Perhatikan juga puncak/video -- kalau turun tanpa '
          'menurunkan coverage, derau berhasil dibuang.')


if __name__ == '__main__':
    main()
