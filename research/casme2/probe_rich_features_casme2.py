#!/usr/bin/env python
"""Uji tuas terakhir: fitur per-kandidat LEBIH KAYA dari sekadar magnitudo.

Skor handcrafted dan pembelajar atas magnitudo 5 ROI sama-sama mentok di
F1 ~0,20 (Iterasi 4.46). Satu tuas fitur belum diuji: pipeline sudah menghitung
BANYAK sinyal per ROI (magnitudo, arah bertanda X/Y, koherensi sudut), bukan
cuma magnitudo. Skrip ini menghitung sinyal-sinyal itu untuk sebagian video,
lalu mengulang uji pembelajar.

Hipotesis: arah (mean_x/mean_y) dan koherensi sudut (angle_R) membedakan
ekspresi emosional dari gerakan lain (mis. bicara/menelan), sehingga AUC
naik dari 0,67 dan F1 melewati 0,20.

Cara pakai:
    .venv/bin/python scripts/probe_rich_features_casme2.py --videos 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
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
import stage_1_spotting as spot  # noqa: E402
from apex import ApexSmoother  # noqa: E402
from features.poc import POC  # noqa: E402
from features.quadran import Quadran  # noqa: E402
from features.vektor import Vektor  # noqa: E402

SIGNALS = ('mean_m', 'max_m', 'motion_count', 'mean_x', 'mean_y', 'angle_R')


def rich_signals(video: Path) -> dict[str, dict[str, list[float]]]:
    """{roi: {signal: nilai per frame}} vs acuan frame-0 (POC-ABS)."""
    cap = cv2.VideoCapture(str(video))
    grays, lms = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grays.append(g)
        lms.append(spot.detect_landmarks(g, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR))
    cap.release()
    regions = spot.config.regions
    out = {r: {s: [] for s in SIGNALS} for r in regions}
    if lms[0] is None:
        return out
    for i in range(1, len(grays)):
        clm = lms[i]
        for r, idx in regions.items():
            vals = None
            if clm is not None:
                try:
                    a = spot.extract_region(grays[0], lms[0], idx)
                    c = spot.extract_region(grays[i], clm, idx)
                    if a.size and c.size:
                        tw, th = spot.config.target_size[r]
                        poc = POC(cv2.resize(a, (tw, th)), cv2.resize(c, (tw, th)), spot.config.block_size)
                        q = Quadran(Vektor(poc.getPOC(), spot.config.block_size).getVektor()).getQuadran()
                        m = np.array([float(x[4]) for x in q], float)
                        xs = np.array([float(x[1]) for x in q], float)
                        ys = np.array([float(x[2]) for x in q], float)
                        mv = m > 0
                        if mv.any():
                            th_ = np.arctan2(ys[mv], xs[mv])
                            c_, s_ = float(np.mean(np.cos(th_))), float(np.mean(np.sin(th_)))
                        else:
                            c_, s_ = 0.0, 0.0
                        vals = {
                            'mean_m': float(m.mean()) if m.size else np.nan,
                            'max_m': float(m.max()) if m.size else np.nan,
                            'motion_count': float(mv.mean()) if m.size else np.nan,
                            'mean_x': float(xs.mean()) if xs.size else np.nan,
                            'mean_y': float(ys.mean()) if ys.size else np.nan,
                            'angle_R': float(np.hypot(c_, s_)),
                        }
                except Exception:
                    vals = None
            for s in SIGNALS:
                out[r][s].append(vals[s] if vals else np.nan)
    for r in out:
        for s in out[r]:
            out[r][s] = spot._interpolate_signal(out[r][s])
    return out


def build(video: str, sig: dict, gt: list[dict]) -> pd.DataFrame:
    smooth = {r: {s: np.asarray(ApexSmoother.smooth(v), float) for s, v in d.items()} for r, d in sig.items()}
    rois = sorted(smooth)
    peaks = {}
    for r in rois:
        sm = smooth[r]['mean_m']
        pk, _ = find_peaks(sm, distance=1, height=sm.mean() + sm.std(),
                           prominence=max(0.04 * (sm.max() - sm.min()), 0.005))
        peaks[r] = pk
    rows = []
    for r in rois:
        for i in peaks[r]:
            f = int(i) + 1
            feat = {'video': video, 'roi': r, 'frame': f}
            for r2 in rois:
                for s in SIGNALS:
                    a = smooth[r2][s]
                    feat[f'{r2}_{s}'] = float(a[min(i, len(a) - 1)])
                    lo, hi = max(0, i - 20), min(len(a), i + 21)
                    feat[f'{r2}_{s}_z'] = float((a[i] - a[lo:hi].mean()) / (a[lo:hi].std() + 1e-9))
            n = sum(1 for r2 in rois if r2 != r and len(peaks[r2]) and np.min(np.abs(peaks[r2] - i)) <= 10)
            feat['sup'] = n
            feat['label'] = int(any(x['onset'] <= f <= x['offset'] for x in gt))
            rows.append(feat)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--videos', type=int, default=15)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/rich_rank_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    vids = sorted(gt_by_video)[:args.videos]
    spot.init_worker(str(bench.PREDICTOR))

    frames = []
    for i, v in enumerate(vids, 1):
        d = build(v, rich_signals(Path(v)), gt_by_video[v])
        frames.append(d)
        print(f'  [{i}/{len(vids)}] {Path(v).name}: kandidat={len(d)} positif={int(d.label.sum())}', flush=True)
    d = pd.concat(frames, ignore_index=True)
    cols = [c for c in d.columns if c not in ('video', 'roi', 'frame', 'label')]
    X = d[cols].to_numpy(float); y = d['label'].to_numpy(); g = d['video'].to_numpy()
    print(f'\nkandidat={len(d)} positif={y.sum()} ({y.mean():.4f}) fitur={len(cols)}')

    oof = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, g):
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_depth=3)
        m.fit(X[tr], y[tr]); oof[te] = m.predict_proba(X[te])[:, 1]
    auc = roc_auc_score(y, oof)
    print(f'gbdt AUC (fitur kaya) = {auc:.4f}   [pembanding magnitudo-5-ROI: 0,6706]')

    order = np.argsort(-oof); ys = y[order]
    best = (0, 0.0)
    for budget in (3.6, 10, 20, 40, 80, 160):
        k = int(budget * len(vids))
        if k >= len(ys):
            break
        tp = ys[:k].sum(); prec = tp / k; rec = tp / y.sum()
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
        if f1 > best[1]:
            best = (budget, f1)
        print(f'  budget {budget:5.1f}/video: precision={prec:.4f} recall={rec:.4f} F1={f1:.4f}')
    print(f'\nF1 terbaik (fitur kaya) = {best[1]:.4f} pada {best[0]}/video '
          f'[pembanding magnitudo: 0,2047]')

    args.out.mkdir(parents=True, exist_ok=True)
    d[['video', 'roi', 'frame', 'label']].assign(score=oof).to_csv(args.out / 'candidates.csv', index=False)
    print(f'Keluaran: {args.out}/candidates.csv')


if __name__ == '__main__':
    main()
