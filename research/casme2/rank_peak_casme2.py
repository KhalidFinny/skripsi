#!/usr/bin/env python
"""Bandingkan strategi PERINGKAT puncak untuk spotting CAS(ME)^2.

Latar: benchmark (Iterasi 4.45) menunjukkan sinyal POC-ABS MEMANG memuncak di
lokasi ekspresi (persentil 0,988), tetapi ada ~125 puncak per ROI dan puncak
ekspresi hanya di peringkat ~17%. Jadi masalahnya PEMERINGKATAN, bukan ambang.

Skrip ini memakai cache sinyal yang sudah ada (tanpa hitung ulang POC), lalu
membandingkan beberapa skor puncak pada anggaran deteksi yang sama.

Cara pakai:
    .venv/bin/python scripts/rank_peak_casme2.py
    .venv/bin/python scripts/rank_peak_casme2.py --budget 3.6 --out output/training/rank_casme2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
from apex import ApexSmoother  # noqa: E402

DEFAULT_OUT = ROOT / 'output/training/rank_casme2'


def peak_table(sig: dict[str, list[float]]) -> pd.DataFrame:
    """Semua puncak kandidat per ROI + beberapa skor pembanding."""
    rows = []
    per_roi = {}
    for r, s in sig.items():
        sm = np.asarray(ApexSmoother.smooth(s), dtype=float)
        height = sm.mean() + sm.std()
        prom_abs = max(0.04 * (sm.max() - sm.min()), 0.005)
        pk, props = find_peaks(sm, distance=1, height=height, prominence=prom_abs, width=0)
        per_roi[r] = {'sm': sm, 'pk': pk, 'mu': sm.mean(), 'sd': sm.std()}
        for j, i in enumerate(pk):
            rows.append({
                'roi': r, 'frame': int(i) + 1, 'idx': int(i),
                'val': float(sm[i]),
                'prom': float(props['prominences'][j]),
                'width': float(props['widths'][j]),
                'z': float((sm[i] - sm.mean()) / sm.std()) if sm.std() > 0 else 0.0,
                'prom_rel': float(props['prominences'][j] / (sm.max() - sm.min() + 1e-9)),
            })
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    # Dukungan antar-ROI: berapa ROI lain punya puncak dalam +/-10 frame.
    peaks_by_roi = {r: per_roi[r]['pk'] for r in per_roi}
    sup = []
    for row in d.itertuples():
        n = 0
        for r2, pk2 in peaks_by_roi.items():
            if r2 == row.roi or len(pk2) == 0:
                continue
            if np.min(np.abs(pk2 - row.idx)) <= 10:
                n += 1
        sup.append(n)
    d['sup'] = sup
    # Skor gabungan: magnitudo relatif terhadap ROI, dikali dukungan antar-ROI.
    d['val_x_sup'] = d['prom_rel'] * (1 + d['sup'])
    return d


def rank_metrics(d: pd.DataFrame, gt: list[dict], budget: float, score: str) -> dict:
    """Pilih ~budget deteksi/video dengan skor tertentu, lalu hitung P/R/F1.

    `budget` = rata-rata deteksi per video. Diambil `ceil(budget)` teratas per
    video supaya anggaran antar skor sebanding.
    """
    k = max(1, int(round(budget)))
    tp = fp = 0
    matched_gt: set[int] = set()
    for _, vid in d.groupby('video'):
        top = vid.nlargest(k, score)
        for row in top.itertuples():
            hit = None
            for gi, g in enumerate(gt):
                if gi in matched_gt:
                    continue
                if g['onset'] <= row.frame <= g['offset']:
                    hit = gi
                    break
            if hit is None:
                fp += 1
            else:
                matched_gt.add(hit)
                tp += 1
    fn = len(gt) - tp
    p = tp / (tp + fp) if tp + fp else float('nan')
    r = tp / (tp + fn) if tp + fn else float('nan')
    f1 = 2 * p * r / (p + r) if p and r and not np.isnan(p) and not np.isnan(r) else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': p, 'recall': r, 'f1': f1}


def main() -> None:
    ap = argparse.ArgumentParser(description='Bandingkan skor peringkat puncak CAS(ME)^2.')
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--budget', type=float, default=3.6,
                    help='deteksi per video (default = kepadatan GT: 308/86)')
    ap.add_argument('--cache', type=Path, default=bench.DEFAULT_SIGNAL_CACHE)
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    print(f'GT: {len(gt)} ekspresi pada {len(gt_by_video)} video '
          f'| budget {args.budget:.1f} deteksi/video')

    frames = []
    for v in sorted(gt_by_video):
        cp = bench.cache_path(args.cache, Path(v))
        sig = bench.load_cached_signals(cp) if cp else None
        if not sig:
            print(f'  (tanpa cache, dilewati) {Path(v).name}')
            continue
        d = peak_table(sig)
        if d.empty:
            continue
        d['video'] = Path(v).name
        frames.append(d)
    allp = pd.concat(frames, ignore_index=True)
    print(f'puncak kandidat total: {len(allp)} '
          f'({len(allp) / len(gt_by_video):.0f} per video)')

    scores = ['val', 'prom', 'prom_rel', 'z', 'width', 'sup', 'val_x_sup']
    results = {}
    for sc in scores:
        tp = fp = 0
        for v, g in gt_by_video.items():
            sub = allp[allp.video == Path(v).name]
            if sub.empty:
                continue
            k = max(1, int(round(args.budget)))
            top = sub.nlargest(k, sc)
            used = set()
            for row in top.itertuples():
                hit = None
                for gi, x in enumerate(g):
                    if gi in used:
                        continue
                    if x['onset'] <= row.frame <= x['offset']:
                        hit = gi
                        break
                if hit is None:
                    fp += 1
                else:
                    used.add(hit)
                    tp += 1
        fn = len(gt) - tp
        p = tp / (tp + fp) if tp + fp else float('nan')
        r = tp / (tp + fn) if tp + fn else float('nan')
        f1 = 2 * p * r / (p + r) if p and r and not np.isnan(p) and not np.isnan(r) else 0.0
        results[sc] = {'tp': tp, 'fp': fp, 'fn': fn, 'precision': p, 'recall': r, 'f1': f1}

    args.out.mkdir(parents=True, exist_ok=True)
    lines = ['# Perbandingan skor peringkat puncak (CAS(ME)^2)', '',
             f'- puncak kandidat: {len(allp)} ({len(allp) / len(gt_by_video):.0f}/video)',
             f'- anggaran: {args.budget:.1f} deteksi/video (GT: {len(gt) / len(gt_by_video):.1f}/video)',
             '', '| skor | precision | recall | F1 | TP | FP | FN |', '|---|---|---|---|---|---|---|']
    for sc, m in sorted(results.items(), key=lambda kv: -kv[1]['f1']):
        lines.append(f'| {sc} | {m["precision"]:.4f} | {m["recall"]:.4f} | {m["f1"]:.4f} | '
                     f'{m["tp"]} | {m["fp"]} | {m["fn"]} |')
    lines += ['', 'Skor:',
              '- `val` = nilai sinyal mentah pada puncak (yang dipakai sekarang).',
              '- `prom` / `prom_rel` = prominence absolut / relatif terhadap rentang sinyal.',
              '- `z` = z-score puncak di dalam ROI-nya.',
              '- `width` = lebar puncak pada setengah prominence.',
              '- `sup` = jumlah ROI lain yang punya puncak dalam +/-10 frame.',
              '- `val_x_sup` = prominence relatif dikali (1 + sup).']
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print('\n' + '\n'.join(lines[5:]))
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()
