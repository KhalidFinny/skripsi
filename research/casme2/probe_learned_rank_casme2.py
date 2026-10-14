#!/usr/bin/env python
"""Uji apakah PEMBELAJAR (bukan skor handcrafted) bisa memisahkan puncak ekspresi.

Temuan sebelumnya: tidak ada skor handcrafted (nilai, prominence, z, lebar,
dukungan antar-ROI) yang memisahkan puncak ekspresi dari ~700 puncak gerak lain.
Menaikkan ambang justru MEMPERBURUK peringkat ekspresi (0,044 -> 0,219), jadi
ekspresi bukan puncak terkuat.

Skrip ini menguji hipotesis berikutnya: informasi pembeda ADA, tapi tidak
tertangkap skor sederhana -- perlu kombinasi fitur yang dipelajari.

Fitur per kandidat (dari cache sinyal, jadi cepat):
  - nilai sinyal 5 ROI pada frame puncak (dinormalkan per ROI)
  - nilai 5 ROI pada frame sekitar (konteks temporal: -15, -7, +7, +15)
  - statistik lokal: z, prominence relatif, lebar, dukungan antar-ROI

Evaluasi: GroupKFold per VIDEO (model tidak pernah lihat video uji), lalu AUC.

Cara pakai:
    .venv/bin/python scripts/probe_learned_rank_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
from apex import ApexSmoother  # noqa: E402


def build_candidates(video: str, sig: dict[str, list[float]], gt: list[dict]) -> pd.DataFrame:
    """Satu baris per kandidat puncak, dengan fitur multi-ROI + label."""
    smooth = {r: np.asarray(ApexSmoother.smooth(s), dtype=float) for r, s in sig.items()}
    rois = sorted(smooth)
    peaks = {}
    for r in rois:
        sm = smooth[r]
        pk, _ = find_peaks(sm, distance=1, height=sm.mean() + sm.std(),
                           prominence=max(0.04 * (sm.max() - sm.min()), 0.005))
        peaks[r] = pk
    rows = []
    for r in rois:
        sm = smooth[r]
        mu, sd = sm.mean(), sm.std()
        rng = sm.max() - sm.min() + 1e-9
        for i in peaks[r]:
            feat = {'video': video, 'roi': r, 'frame': int(i) + 1}
            # nilai 5 ROI pada puncak + konteks temporal
            for off in (0, -15, -7, 7, 15):
                j = int(np.clip(i + off, 0, len(sm) - 1))
                for r2 in rois:
                    a2 = smooth[r2]
                    feat[f'{r2}@{off}'] = float(a2[min(j, len(a2) - 1)])
            feat['z'] = float((sm[i] - mu) / sd) if sd > 0 else 0.0
            feat['prom_rel'] = float((sm[i] - sm[max(0, i - 15):i + 16].min()) / rng)
            lo, hi = max(0, i - 25), min(len(sm), i + 26)
            feat['local_z'] = float((sm[i] - sm[lo:hi].mean()) / (sm[lo:hi].std() + 1e-9))
            feat['slope_in'] = float(sm[i] - sm[max(0, i - 7)])
            feat['slope_out'] = float(sm[min(len(sm) - 1, i + 7)] - sm[i])
            # dukungan antar-ROI
            n = 0
            for r2 in rois:
                if r2 == r or len(peaks[r2]) == 0:
                    continue
                if np.min(np.abs(peaks[r2] - i)) <= 10:
                    n += 1
            feat['sup'] = n
            feat['label'] = int(any(x['onset'] <= feat['frame'] <= x['offset'] for x in gt))
            rows.append(feat)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/learned_rank_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    frames = []
    for v in sorted(gt_by_video):
        cp = bench.cache_path(bench.DEFAULT_SIGNAL_CACHE, Path(v))
        sig = bench.load_cached_signals(cp) if cp else None
        if sig:
            frames.append(build_candidates(v, sig, gt_by_video[v]))
    d = pd.concat(frames, ignore_index=True)
    feat_cols = [c for c in d.columns if c not in ('video', 'roi', 'frame', 'label')]
    print(f'kandidat: {len(d)} | positif: {d.label.sum()} ({d.label.mean():.4f}) '
          f'| fitur: {len(feat_cols)} | video: {d.video.nunique()}')

    X = d[feat_cols].to_numpy(dtype=float)
    y = d['label'].to_numpy()
    groups = d['video'].to_numpy()
    gkf = GroupKFold(n_splits=5)

    models = {
        'logistic': make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight='balanced')),
        'gbdt': HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_depth=3),
    }
    rows = []
    for name, model in models.items():
        oof = np.zeros(len(y))
        for tr, te in gkf.split(X, y, groups):
            model.fit(X[tr], y[tr])
            oof[te] = model.predict_proba(X[te])[:, 1]
        auc = roc_auc_score(y, oof)
        # berapa positif yang masuk 1% skor teratas?
        thr = np.percentile(oof, 99)
        top = oof >= thr
        prec = y[top].mean() if top.any() else float('nan')
        rec = y[top].sum() / y.sum()
        rows.append({'model': name, 'auc': auc, 'prec_at_top1pct': prec, 'recall_at_top1pct': rec})
        print(f'  {name:9s}: AUC={auc:.4f} | pada 1% skor teratas: precision={prec:.4f} '
              f'recall={rec:.4f}', flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    d[['video', 'roi', 'frame', 'label']].assign(score=oof).to_csv(args.out / 'candidates.csv', index=False)
    print(f'\nKeluaran: {args.out}/')
    print('Bacaan: AUC 0,5 = tidak ada informasi pembeda. Bandingkan precision@top1% '
          '(0,00058 = tebak acak, karena hanya 0,058% kandidat yang ekspresi).')


if __name__ == '__main__':
    main()
