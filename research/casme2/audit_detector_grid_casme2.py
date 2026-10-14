#!/usr/bin/env python
"""DEEP DIVE: grid parameter detektor pada sinyal global (cara notebook asli).

Yang disapu:
  - height  : mean + k*std, k = 0.0, 0.5, 1.0, 1.5, 2.0
  - ranking : 'value' (cara sekarang) vs 'prominence' (puncak paling menonjol
              secara lokal, bukan paling tinggi absolut)
  - top_k   : 3, 5, 8, 10, 15

Alasan: analisis sebelumnya menunjukkan puncak di dekat apex GT GUGUR oleh
height mean+std (49%) dan sisanya berperingkat ~0.23 (top-5 tidak menjangkau).
Jadi dua kandidat perbaikan: turunkan height, dan ubah kriteria peringkat.

Cara pakai:
    .venv/bin/python scripts/audit_detector_grid_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_prominences

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexPhase, ApexSmoother  # noqa: E402


def detect(sm: np.ndarray, top_k: int, height: float, ranking: str) -> list[dict]:
    det = ApexPhase(distance_threshold=1, prominence_threshold=0.005, cutoff_ratio=0.3)
    if ranking == 'value':
        ap = det.find_top_k_apex(sm.tolist(), k=top_k, height=height)
    else:
        pk, _ = find_peaks(sm, distance=1, prominence=0.005, height=height)
        pk = det.merge_nearby_peaks(sm.tolist(), pk.tolist(), merge_distance=10)
        if not pk:
            return []
        prom = peak_prominences(sm, pk)[0]
        order = np.argsort(-prom)
        ap = sorted([pk[i] for i in order[:top_k]])
    ph = det.find_phase(sm.tolist(), ap) if ap else {}
    out = []
    for a in ap:
        p = ph.get(a)
        if p is None or int(p['end'] - p['start']) < 2:
            continue
        out.append({'onset': spot.signal_index_to_frame_index(int(p['start'])),
                    'apex': spot.signal_index_to_frame_index(int(a)),
                    'offset': spot.signal_index_to_frame_index(int(p['end'])),
                    'region': 'global'})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--heights', type=float, nargs='+', default=[0.0, 0.5, 1.0, 1.5, 2.0])
    ap.add_argument('--top-k', type=int, nargs='+', default=[3, 5, 8, 10, 15])
    ap.add_argument('--rankings', nargs='+', default=['value', 'prominence'])
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_detector_grid_casme2')
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

    # sinyal global + smoothing sekali
    prepared = {}
    for v, (s, g) in data.items():
        glob = np.asarray(spot.build_global_signal(s), dtype=float)
        if len(glob) < 10:
            continue
        prepared[v] = (np.asarray(ApexSmoother.smooth(glob.tolist()), dtype=float), g)

    rows = []
    best = None
    print(f"\n{'ranking':11s} {'k_std':>5s} {'top_k':>6s} {'P':>7s} {'R':>7s} {'F1':>7s} {'det/video':>10s}")
    for ranking in args.rankings:
        for kstd in args.heights:
            for k in args.top_k:
                tp = fp = fn = ndet = 0
                for sm, g in prepared.values():
                    h = float(sm.mean() + kstd * sm.std())
                    det = detect(sm, k, h, ranking)
                    ndet += len(det)
                    p, f, f_ = bench.match_events(g, det, 0)
                    tp += len(p); fp += len(f); fn += len(f_)
                sc = bench.scores(tp, fp, fn)
                row = {'ranking': ranking, 'k_std': kstd, 'top_k': k,
                       'precision': sc['precision'], 'recall': sc['recall'], 'f1': sc['f1'],
                       'det_per_video': ndet / max(1, len(prepared))}
                rows.append(row)
                if best is None or sc['f1'] > best['f1']:
                    best = row
                print(f"{ranking:11s} {kstd:5.1f} {k:6d} {sc['precision']:7.4f} {sc['recall']:7.4f} "
                      f"{sc['f1']:7.4f} {ndet/max(1,len(prepared)):10.1f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).sort_values('f1', ascending=False)
    df.to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Grid detektor pada sinyal global — CAS(ME)^2', '',
             'Toleransi 0 frame. Semua memakai agregasi global (cara notebook asli).', '',
             '## 15 teratas menurut F1', '',
             '| ranking | k_std | top_k | precision | recall | F1 | det/video |',
             '|---|---|---|---|---|---|---|']
    for _, r in df.head(15).iterrows():
        lines.append(f"| {r['ranking']} | {r['k_std']:.1f} | {int(r['top_k'])} | {r['precision']:.4f} | "
                     f"{r['recall']:.4f} | {r['f1']:.4f} | {r['det_per_video']:.1f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f"\nTERBAIK: {best}")
    print(f'Keluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
