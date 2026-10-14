#!/usr/bin/env python
"""Baseline model sederhana di protokol LOSO yang SAMA dengan run_loso.py.

Kenapa ada (sebab #5 penurunan akurasi LOSO):
  Hanya TabR yang diuji. Di N kecil (56 subjek) dan fitur berdimensi rendah,
  literatur kecil-sampel menunjukkan model linear/tree sering mengalahkan
  deep learning (Grinsztiny et al. 2022; TabPFN Nature 2025). Tanpa pembanding,
  tidak diketahui apakah kegagalan berasal dari representasi atau dari model.

Protokol (identik dengan run_loso.py supaya perbandingannya apple-to-apple):
  - 56 fold, tiap fold test = 1 subjek.
  - val = 20% subjek sisa (RANDOM_SEED 72). Val TIDAK dipakai melatih model
    sederhana (tidak butuh early stopping); dipertahankan hanya supaya
    jumlah subjek train sama persis dengan yang dilihat TabR.
  - praproses sama: impute mean, VarianceThreshold, StandardScaler fit train,
    opsi --subject-norm.
  - metrik level subjek memakai helper yang sama dengan collect_loso_results.py.

Selain metrik, dijalankan permutation test level subjek (acak label antar
subjek) untuk menguji apakah ada sinyal di atas acak.

Contoh:
    .venv/bin/python pipeline/stages/stage_7_baseline.py
    .venv/bin/python pipeline/stages/stage_7_baseline.py --features experiments/features/apex/poc_abs_roi_signals_temporal.pkl
    .venv/bin/python pipeline/stages/stage_7_baseline.py --aggregate none --permutations 200
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from stage_7_collect import fmt, fmt_ci, subject_metrics  # noqa: E402
from stage_6_train_loso import (  # noqa: E402
    LABEL_MAP,
    RANDOM_SEED,
    aggregate_rows,
    balance_train_clips_by_label,
    has_both_labels,
    load_full_table,
    subject_standardize,
)

DEFAULT_OUT = ROOT / 'output' / 'training'


def build_models(seed: int) -> dict[str, Any]:
    return {
        'logistic': LogisticRegression(max_iter=2000, class_weight='balanced', random_state=seed),
        'gbdt': GradientBoostingClassifier(random_state=seed),
    }


def run_fold(df: pd.DataFrame, feature_cols: list[str], test_subject: str,
             participants: list[str], args) -> dict[str, float]:
    """Latih semua model untuk satu fold; kembalikan proba test per subjek."""
    rest = pd.Series([p for p in participants if p != test_subject])
    train_parts = None
    for rs in range(RANDOM_SEED, RANDOM_SEED + 500):
        gss = GroupShuffleSplit(n_splits=1, test_size=args.val_size, random_state=rs)
        tr_idx, va_idx = next(gss.split(rest, groups=rest))
        cand_tr, cand_va = rest.iloc[tr_idx], rest.iloc[va_idx]
        if has_both_labels(df, cand_tr) and has_both_labels(df, cand_va):
            train_parts = cand_tr
            break
    if train_parts is None:
        raise SystemExit(f'Fold {test_subject}: tidak ada split subjek-disjoint 2 kelas.')

    df_tr = df[df['participant'].isin(train_parts)].copy()
    df_test = df[df['participant'] == test_subject].copy()
    if args.subject_norm == 'subject':
        df_tr = subject_standardize(df_tr, feature_cols)
        df_test = subject_standardize(df_test, feature_cols)
    if args.aggregate != 'subject':
        df_tr = balance_train_clips_by_label(df_tr, seed=RANDOM_SEED)

    imputer = SimpleImputer(strategy='mean')
    scaler = StandardScaler()
    X_train = imputer.fit_transform(df_tr[feature_cols])
    X_test = imputer.transform(df_test[feature_cols])
    # Scale DULU, baru variance: pada nilai mentah ambang absolut 1e-4 menjadi
    # filter SKALA dan membuang fitur satuan-kecil yang sebenarnya bergerak
    # (lihat komentar yang sama di run_loso.py). Fitur yang bertahan identik
    # nilainya, karena StandardScaler bekerja per kolom.
    scaler.fit(X_train)
    X_train = scaler.transform(X_train)
    X_test = scaler.transform(X_test)
    if args.variance_threshold > 0:
        selector = VarianceThreshold(threshold=args.variance_threshold)
        X_train = selector.fit_transform(X_train)
        X_test = selector.transform(X_test)
    X_train = X_train.astype(np.float64)
    X_test = X_test.astype(np.float64)
    y_train = df_tr['target'].to_numpy(dtype=np.int64)

    out = {}
    for name, model in build_models(RANDOM_SEED).items():
        model.fit(X_train, y_train)
        out[name] = float(model.predict_proba(X_test)[:, 1].mean())
    return out


def permutation_test(labels: np.ndarray, scores: np.ndarray, n_perm: int, seed: int) -> dict[str, float]:
    """Uji acak level subjek: berapa sering akurasi label teracak >= akurasi nyata."""
    observed = accuracy_score(labels, (scores >= 0.5).astype(int))
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for i in range(n_perm):
        permuted = rng.permutation(labels)
        null[i] = accuracy_score(permuted, (scores >= 0.5).astype(int))
    hits = int((null >= observed).sum())
    return {
        'observed_accuracy': float(observed),
        'null_mean': float(null.mean()),
        'null_std': float(null.std()),
        'p_value': (1 + hits) / (1 + n_perm),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Baseline LOSO (logistik/GBDT) sebagai pembanding TabR.')
    parser.add_argument('--dataset', default='convat_apex_anxiety_loso_roi25_baseline')
    parser.add_argument('--features', type=Path, default=None,
                        help='tabel fitur alternatif (pkl/csv/xlsx); default = roi25')
    parser.add_argument('--aggregate', choices=['none', 'subject'], default='subject',
                        help="'subject' (default): 1 baris = 1 subjek (mean+std) -- unit label "
                             "yang benar di N=56. 'none': 1 baris = 1 frame.")
    parser.add_argument('--subject-norm', choices=['none', 'subject'], default='subject',
                        help="Normalisasi fitur per subjek (lihat run_loso.py). Default 'subject'.")
    parser.add_argument('--variance-threshold', type=float, default=1e-4)
    parser.add_argument('--val-size', type=float, default=0.2,
                        help='Fraksi subjek sisa untuk val; hanya untuk menyamakan jumlah '
                             'subjek train dengan run_loso.py (model sederhana tidak memakainya).')
    parser.add_argument('--permutations', type=int, default=200)
    parser.add_argument('--label-unit', choices=['person', 'session'], default='person')
    parser.add_argument('--drop-features', default=r'_max_m$')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if args.subject_norm == 'subject' and args.aggregate == 'subject':
        # Sama seperti run_loso.py: std subjek = 0 -> semua fitur jadi 0.
        args.subject_norm = 'none'
        print('subject-norm dimatikan: dengan --aggregate subject std subjek = 0.', flush=True)

    df, feature_cols = load_full_table(args.features)
    if args.label_unit == 'person':
        df = df[df['phase'] == 'after'].copy()
    if args.drop_features:
        pat = re.compile(args.drop_features)
        feature_cols = [c for c in feature_cols if not pat.search(c)]
    if args.aggregate != 'none':
        df, feature_cols = aggregate_rows(df, feature_cols, args.aggregate)

    participants = sorted(df['participant'].unique().tolist())
    print(f'Baris={len(df)} subjek={len(participants)} fitur={len(feature_cols)}')
    print(f'Kelas: {df["label"].value_counts().to_dict()}')
    print(f'aggregate={args.aggregate} | subject-norm={args.subject_norm} | '
          f'permutations={args.permutations}', flush=True)

    model_names = list(build_models(RANDOM_SEED))
    subject_rows = []
    for fold_idx, test_subject in enumerate(participants):
        scores = run_fold(df, feature_cols, test_subject, participants, args)
        true = int(df[df['participant'] == test_subject]['target'].iloc[0])
        for name, proba in scores.items():
            subject_rows.append({
                'model': name, 'subject': test_subject, 'proba': proba,
                'true': true, 'pred': int(proba >= 0.5),
            })
        if (fold_idx + 1) % 10 == 0:
            print(f'  {fold_idx + 1}/{len(participants)} fold', flush=True)

    per_subject = pd.DataFrame(subject_rows)
    out_dir = args.out / args.dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    per_subject.to_csv(out_dir / 'per_subject.csv', index=False)

    metrics_by_model = {}
    lines = [
        f'# Baseline LOSO - {args.dataset}',
        '',
        f'{len(participants)} fold (1 subjek/fold), protokol sama dengan run_loso.py. '
        f'Baris training = {args.aggregate}, normalisasi = {args.subject_norm}.',
        '',
        'Pembanding untuk TabR. Di N kecil, model linear/tree sering mengalahkan DL '
        '(Grinsztajn et al. 2022; TabPFN Nature 2025).',
        '',
        '## Level subjek (1 keputusan per subjek)',
        '',
        '| model | accuracy | 95% CI | sensitivity | specificity | PPV | NPV | baseline mayoritas |',
        '|---|---|---|---|---|---|---|---|',
    ]
    for name in model_names:
        m = subject_metrics(per_subject[per_subject['model'] == name])
        metrics_by_model[name] = dict(m)
        lines.append(
            f'| {name} | {m["accuracy"]:.4f} | '
            f'{fmt_ci(m["tp"] + m["tn"], m["n"])} | '
            f'{m["sensitivity"]:.4f} | {m["specificity"]:.4f} | '
            f'{m["ppv"]:.4f} | {m["npv"]:.4f} | {m["majority_baseline"]:.4f} |'
        )
    lines.append('')

    if args.permutations > 0:
        lines += ['## Permutation test level subjek', '',
                  f'{args.permutations} kali acak label antar subjek. '
                  'p kecil = akurasi tidak mungkin datang dari acak.', '',
                  '| model | akurasi | null mean ± std | p-value |', '|---|---|---|---|']
        for name in model_names:
            sub = per_subject[per_subject['model'] == name]
            pt = permutation_test(sub['true'].to_numpy(), sub['proba'].to_numpy(),
                                  args.permutations, RANDOM_SEED)
            metrics_by_model[name]['perm_p_value'] = pt['p_value']
            lines.append(f'| {name} | {pt["observed_accuracy"]:.4f} | '
                         f'{pt["null_mean"]:.4f} ± {pt["null_std"]:.4f} | {pt["p_value"]:.4f} |')
        lines.append('')

    lines += ['Catatan:',
              '- Model sederhana TIDAK memakai val; val hanya menyamakan jumlah subjek train dengan TabR.',
              '- Keluaran terpisah dari keluaran TabR; tidak menyentuh exp/tabr/.',
              '- File: summary.csv, per_subject.csv.']

    pd.DataFrame([{'model': name, **m} for name, m in metrics_by_model.items()]).to_csv(
        out_dir / 'summary.csv', index=False)
    (out_dir / 'summary.md').write_text('\n'.join(lines) + '\n')
    print('\n' + '\n'.join(lines))
    print(f'\nKeluaran: {out_dir}')


if __name__ == '__main__':
    main()
