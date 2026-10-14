#!/usr/bin/env python
"""AUDIT F1: agregasi global (cara notebook ASLI) vs per-ROI (cara pipeline SEKARANG).

Memakai cache sinyal magnitude yang sudah ada (`spotting_casme2_signals/`) dan
fungsi pencocokan milik `eval_spotting_casme2.py`, jadi F1-nya langsung
sebanding dengan angka benchmark yang sudah dilaporkan (F1 0.2006).

Cara pakai:
    .venv/bin/python scripts/audit_agg_f1_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402


def detect_global(roi_signals: dict[str, list[float]], params: spot.DetectParams) -> list[dict]:
    """Deteksi dari SATU sinyal (mean antar ROI) -- cara notebook asli."""
    mags = spot.build_global_signal(roi_signals)
    if not mags:
        return []
    _sm, events, _meta = spot.detect_events(mags, params)
    return [{
        'onset': spot.signal_index_to_frame_index(e['onset_signal']),
        'apex': spot.signal_index_to_frame_index(e['apex_signal']),
        'offset': spot.signal_index_to_frame_index(e['offset_signal']),
        'region': 'global',
    } for e in events]


def run(signals_map: dict, gt_df, tol: int, params: spot.DetectParams, mode: str) -> dict:
    all_pairs, all_fp, all_fn = [], [], []
    detect = detect_global if mode == 'global' else bench.detect_from_signals
    for video_path, (signals, gt) in signals_map.items():
        det = detect(signals, params)
        pairs, fp, fn = bench.match_events(gt, det, tol)
        all_pairs.extend((video_path, d, g) for d, g in pairs)
        all_fp.extend((video_path, d) for d in fp)
        all_fn.extend((video_path, g) for g in fn)
    overall = bench.scores(len(all_pairs), len(all_fp), len(all_fn))
    n_gt_micro = int((gt_df['expr_type'] == 'micro').sum())
    tp_micro = sum(1 for _, _, g in all_pairs if g['expr_type'] == 'micro')
    fn_micro = sum(1 for _, g in all_fn if g['expr_type'] == 'micro')
    rec_micro = tp_micro / (tp_micro + fn_micro) if (tp_micro + fn_micro) else float('nan')
    return {**overall, 'det_per_video': (len(all_pairs) + len(all_fp)) / max(1, len(signals_map)),
            'recall_micro': rec_micro, 'n_gt_micro': n_gt_micro}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', type=Path, default=bench.DEFAULT_SIGNAL_CACHE)
    ap.add_argument('--tolerance', type=int, default=0)
    ap.add_argument('--top-k', type=int, nargs='+', default=[1, 2, 5, 10])
    ap.add_argument('--prom-rel', type=float, default=0.04)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_agg_f1_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    signals_map = {}
    for v, g in gt_by_video.items():
        p = bench.cache_path(args.cache_dir, Path(v))
        sig = bench.load_cached_signals(p) if p else None
        if sig:
            signals_map[v] = (sig, g)
    print(f'video dengan cache: {len(signals_map)}')

    rows = []
    print(f"\n{'agregasi':9s} {'top_k':>6s} {'P':>7s} {'R':>7s} {'F1':>7s} {'R_micro':>8s} {'det/video':>10s}")
    for mode in ('global', 'per_roi'):
        for k in args.top_k:
            params = spot.DetectParams(top_k=k, prom_rel=args.prom_rel)
            r = run(signals_map, gt, args.tolerance, params, mode)
            rows.append({'agg': mode, 'top_k': k, **r})
            print(f"{mode:9s} {k:6d} {r['precision']:7.4f} {r['recall']:7.4f} "
                  f"{r['f1']:7.4f} {r['recall_micro']:8.4f} {r['det_per_video']:10.1f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Audit agregasi (F1) pada CAS(ME)^2', '',
             f'- toleransi: {args.tolerance} frame | prom_rel: {args.prom_rel}',
             '- `global` = mean antar ROI (cara notebook asli); `per_roi` = cara pipeline sekarang.',
             '',
             '| agregasi | top_k | precision | recall | F1 | recall micro | det/video |',
             '|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['agg']} | {r['top_k']} | {r['precision']:.4f} | {r['recall']:.4f} | "
                     f"{r['f1']:.4f} | {r['recall_micro']:.4f} | {r['det_per_video']:.1f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
