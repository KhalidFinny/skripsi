#!/usr/bin/env python
"""DEEP DIVE notebook: uji resep ASLI dari notebook vs resep sekarang.

Temuan dari notebook (backup 2026-08-25):

  Generasi 1 `micro_expression_spotting.ipynb`:
      savgol window TETAP 28, polyorder 3
      find_peaks(prominence=0)  -> TANPA height
      peringkat puncak = PROMINENCE, ambil MAX_PEAKS = 3
      onset/offset: cutoff 0.20 dari min GLOBAL

  Generasi 2 `micro_expression_spotting_v2.ipynb` (+ varian Casme):
      ApexSmoother adaptif 5% clamp 31
      find_top_k_apex(k=0/5, height=mean+std)
      peringkat puncak = NILAI sinyal
      onset/offset: find_phase cutoff 0.30 (local valley)

  Generasi 3 `process_all_datasets.ipynb` = generasi 2 tapi agregasi global
      (inilah yang direplikasi pipeline sekarang).

Jadi pipeline sekarang memakai resep generasi 2/3 (height + peringkat nilai).
Notebook generasi 1 memakai TANPA height + peringkat prominence + top 3.

Skrip ini menyapu: smoother x height x peringkat x top_k, diukur F1 dengan
protokol benchmark. Tujuan: cari resep terbaik, termasuk resep generasi 1.

Cara pakai:
    .venv/bin/python scripts/audit_peak_rank_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_prominences, savgol_filter

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexPhase  # noqa: E402


def smooth_current(sig: np.ndarray) -> np.ndarray:
    w = min(7, len(sig))
    if w % 2 == 0:
        w -= 1
    if w < 3 or w >= len(sig):
        return sig
    return savgol_filter(sig, w, min(2, w - 1))


def smooth_original(sig: np.ndarray) -> np.ndarray:
    w = int(len(sig) * 0.05)
    if w % 2 == 0:
        w += 1
    w = max(5, min(w, 31))
    if w >= len(sig):
        return sig
    po = 2 if w <= 7 else (3 if w <= 15 else 4)
    return savgol_filter(sig, w, po)


def smooth_fixed28(sig: np.ndarray) -> np.ndarray:
    """Generasi 1: window tetap 28, polyorder 3."""
    w = 28
    if w >= len(sig):
        w = len(sig) - 1 if len(sig) % 2 == 0 else len(sig) - 2
        if w % 2 == 0:
            w -= 1
    if w < 4:
        return sig
    return savgol_filter(sig, w, 3)


SMOOTHERS = {'now7': smooth_current, 'orig_5pct': smooth_original, 'gen1_28': smooth_fixed28}


def detect(sm: np.ndarray, top_k: int, height: float | None, ranking: str) -> list[dict]:
    det = ApexPhase(distance_threshold=1, prominence_threshold=0.0, cutoff_ratio=0.3)
    kwargs = dict(distance=1)
    if height is not None:
        kwargs['height'] = height
    if ranking == 'prominence':
        # Generasi 1: find_peaks(prominence=0), peringkat menurut prominence
        pk, props = find_peaks(sm, **kwargs)
        if len(pk) == 0:
            return []
        prom = props.get('prominences')
        if prom is None:
            prom = peak_prominences(sm, pk)[0]
        order = np.argsort(-prom)[:top_k]
        ap = sorted(pk[i] for i in order)
    else:
        pk, _ = find_peaks(sm, **kwargs)
        pk = det.merge_nearby_peaks(sm.tolist(), pk.tolist(), merge_distance=10)
        if not pk:
            return []
        ap = sorted(sorted(pk, key=lambda p: sm[p], reverse=True)[:top_k])
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
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_peak_rank_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    prepared = {}
    for v, g in gt_by.items():
        p = bench.cache_path(bench.DEFAULT_SIGNAL_CACHE, Path(v))
        s = bench.load_cached_signals(p) if p else None
        if s:
            glob = np.asarray(spot.build_global_signal(s), dtype=float)
            if len(glob) >= 10:
                prepared[v] = (glob, g)
    print(f'video: {len(prepared)}')

    rows = []
    for sname, sfn in SMOOTHERS.items():
        sm_cache = {v: np.asarray(sfn(np.nan_to_num(g, nan=0.0)), dtype=float)
                    for v, (g, _) in prepared.items()}
        for ranking in ('value', 'prominence'):
            for kstd in (None, 0.0, 1.0, 2.0):
                for top_k in (3, 5, 8, 10):
                    tp = fp = fn = ndet = 0
                    for v, (_, g) in prepared.items():
                        sm = sm_cache[v]
                        h = None if kstd is None else float(sm.mean() + kstd * sm.std())
                        det = detect(sm, top_k, h, ranking)
                        ndet += len(det)
                        p, f, f_ = bench.match_events(g, det, 0)
                        tp += len(p); fp += len(f); fn += len(f_)
                    sc = bench.scores(tp, fp, fn)
                    rows.append({'smoother': sname, 'ranking': ranking,
                                 'k_std': kstd, 'top_k': top_k,
                                 'precision': sc['precision'], 'recall': sc['recall'],
                                 'f1': sc['f1'], 'det_per_video': ndet / max(1, len(prepared))})
        print(f'  {sname}: selesai', flush=True)

    df = pd.DataFrame(rows).sort_values('f1', ascending=False)
    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Resep puncak: notebook asli vs sekarang — CAS(ME)^2', '',
             'Toleransi 0 frame, agregasi global.', '',
             '`k_std=None` = TANPA height (resep generasi 1). '
             '`ranking=prominence` = resep generasi 1.', '',
             '## 20 teratas menurut F1', '',
             '| smoother | ranking | k_std | top_k | precision | recall | F1 | det/video |',
             '|---|---|---|---|---|---|---|---|']
    for _, r in df.head(20).iterrows():
        ks = 'None' if pd.isna(r['k_std']) else f"{r['k_std']:.1f}"
        lines.append(f"| {r['smoother']} | {r['ranking']} | {ks} | {int(r['top_k'])} | "
                     f"{r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} | {r['det_per_video']:.1f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')
    print(df.head(12).to_string(index=False))


if __name__ == '__main__':
    main()
