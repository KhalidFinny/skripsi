#!/usr/bin/env python
"""DIAGNOSTIK representasi fitur POC-ABS.

Menjawab tiga pertanyaan sebelum mengubah apa pun:

1. CEILING: fitur mana (kalau ada) yang punya AUC lintas-subjek > 0,6?
   Kalau tidak ada satu pun, masalahnya bukan representasi.
2. WITHIN-SUBJECT: untuk 18 subjek yang labelnya BERUBAH antar sesi, fitur mana
   yang beda sistematis? (uji berpasangan, bebas confound identitas)
3. SESI: apakah memakai KEDUA sesi (before+after, 112 baris) menolong, atau
   justru bocor karena fase?

Cara pakai:
    .venv/bin/python scripts/audit_feature_representation.py \
        --features experiments/features/apex/poc_abs_roi_signals_v3fixed_poc_temporal.pkl
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

META = {'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
        'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path',
        'frame', 'target', 'event_id'}


def auc_score(y: np.ndarray, x: np.ndarray) -> float:
    """AUC satu fitur (Mann-Whitney), arah-agnostik dikembalikan apa adanya."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    y, x = y[ok], x[ok]
    if len(np.unique(y)) < 2:
        return float('nan')
    r = pd.Series(x).rank().to_numpy()
    n1 = int((y == 1).sum())
    n0 = int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return float('nan')
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def max_abs_auc(y: np.ndarray, X: np.ndarray) -> float:
    """|AUC-0.5| terbesar di antara semua kolom."""
    vals = [abs(auc_score(y, X[:, j]) - 0.5) for j in range(X.shape[1])]
    vals = [v for v in vals if not np.isnan(v)]
    return max(vals) if vals else float('nan')


def permutation_null(y: np.ndarray, X: np.ndarray, n_perm: int, rng: np.random.Generator) -> np.ndarray:
    """Null untuk statistik 'max |AUC-0.5|' dengan label diacak."""
    out = []
    for _ in range(n_perm):
        yp = rng.permutation(y)
        out.append(max_abs_auc(yp, X))
    return np.asarray(out)


def paired_effect(df: pd.DataFrame, cols: list[str], changed: list[str]) -> pd.DataFrame:
    """Selisih ternormalisasi antar sesi untuk subjek yang labelnya berubah."""
    rows = []
    for c in cols:
        diffs = []
        for p in changed:
            sub = df[df['participant'] == p]
            before = sub[sub['phase'] == 'before'][c]
            after = sub[sub['phase'] == 'after'][c]
            if len(before) == 0 or len(after) == 0:
                continue
            # sesi berlabel tinggi minus sesi berlabel rendah
            hi = before if sub[sub['phase'] == 'before']['label'].iloc[0] == 'anxiety_tinggi' else after
            lo = after if hi is before else before
            diffs.append(float(hi.mean() - lo.mean()))
        if diffs:
            d = np.asarray(diffs)
            rows.append({'feature': c, 'mean_diff': float(d.mean()),
                         'median_diff': float(np.median(d)),
                         'frac_positive': float((d > 0).mean()),
                         'abs_mean_diff': float(np.abs(d).mean())})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', type=Path, required=True)
    ap.add_argument('--aggregate', choices=['subject', 'session', 'event'], default='subject')
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()

    df = pd.read_pickle(args.features)
    cols = [c for c in df.columns if c not in META]
    print(f'{args.features.name}: {len(df)} baris, {len(cols)} fitur')

    # ---- 1. label per sesi ----
    lab = df.groupby(['participant', 'phase'])['label'].first().unstack()
    changed = lab[lab['before'] != lab['after']].index.tolist()
    print(f'subjek: {len(lab)} | label berubah antar sesi: {len(changed)}')
    print(f"  before tinggi: {(lab['before'] == 'anxiety_tinggi').sum()} | "
          f"after tinggi: {(lab['after'] == 'anxiety_tinggi').sum()}")

    # ---- 2. agregasi ----
    keys = {'subject': ['participant', 'phase'], 'session': ['participant', 'phase'],
            'event': ['participant', 'phase', 'event_clip']}[args.aggregate]
    agg = df.groupby(keys, dropna=False)[cols].agg(['mean', 'std'])
    agg.columns = [f'{c}_{s}' for c, s in agg.columns]
    agg = agg.reset_index()
    meta = df.groupby(keys, dropna=False).agg(label=('label', 'first'))
    agg = agg.merge(meta.reset_index(), on=keys, how='left')
    feat_cols = [c for c in agg.columns if c not in {'participant', 'phase', 'label'}]
    agg['y'] = (agg['label'] == 'anxiety_tinggi').astype(int)
    print(f'\nagregasi={args.aggregate}: {len(agg)} baris x {len(feat_cols)} fitur '
          f'({agg["phase"].nunique()} fase, {agg["participant"].nunique()} subjek)')

    # ---- 3. AUC lintas-subjek pada sesi AFTER (protokol pipeline), + null ----
    after = agg[agg['phase'] == 'after'].copy()
    after['y'] = (after['label'] == 'anxiety_tinggi').astype(int)
    X = after[feat_cols].to_numpy(dtype=float)
    X = np.nan_to_num(X, nan=0.0)
    y = after['y'].to_numpy()
    print(f'\n=== CEILING: AUC lintas-subjek, sesi after ({len(after)} subjek, '
          f'{int(y.sum())} positif, {len(feat_cols)} fitur) ===')

    aucs = pd.DataFrame({'feature': feat_cols})
    aucs['auc'] = [auc_score(y, X[:, j]) for j in range(len(feat_cols))]
    aucs['auc_dist'] = (aucs['auc'] - 0.5).abs()
    top_auc = aucs.sort_values('auc_dist', ascending=False).head(15)
    print('\n|AUC-0.5| teratas:')
    print(top_auc[['feature', 'auc']].to_string(index=False))

    obs_max = float(aucs['auc_dist'].max())
    rng = np.random.default_rng(0)
    null = permutation_null(y, X, 200, rng)
    p = float((null >= obs_max).mean())
    print(f'\nmax |AUC-0.5| observasi : {obs_max:.4f}')
    print(f'null (200 acak)         : {null.mean():.4f} ± {null.std():.4f} '
          f'(maks {null.max():.4f})')
    print(f'p-value                 : {p:.4f}   <-- kalau besar, AUC tinggi itu derau seleksi')
    print(f'AUC > 0,60: {(aucs["auc"] > 0.60).sum()} | AUC < 0,40: {(aucs["auc"] < 0.40).sum()}')

    # ---- 4. efek berpasangan (18 subjek berubah) ----
    print(f'\n=== WITHIN-SUBJECT: {len(changed)} subjek yang labelnya berubah ===')
    pe = paired_effect(df, cols, changed)
    pe['abs_mean_diff'] = pe['abs_mean_diff'].astype(float)
    # null: tanda selisih diacak
    base = pe.sort_values('abs_mean_diff', ascending=False)
    print('fitur dgn |selisih| terbesar (median lintas 18 subjek):')
    print(base.head(10)[['feature', 'median_diff', 'frac_positive']].to_string(index=False))
    n_conc = int((base['frac_positive'] >= 0.8333).sum())
    # null: P(>=15 dari 18 searah) untuk tanda acak = 0.0038 -> harapan 335*0.0038
    from scipy.stats import binom
    p_conc = float(binom.sf(14, 18, 0.5))
    print(f'\nfitur dgn frac_positive >= 0,83 (>=15/18 searah): {n_conc} / {len(base)}')
    print(f'  harapan acak = {len(base) * p_conc:.1f}  (P(>=15/18)={p_conc:.4f})')

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        aucs.sort_values('auc_dist', ascending=False).to_csv(args.out, index=False)
        base.to_csv(args.out.with_name(args.out.stem + '_paired.csv'), index=False)
        print(f'\nKeluaran: {args.out} (+ _paired.csv)')



if __name__ == '__main__':
    main()
