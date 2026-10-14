#!/usr/bin/env python
"""LOSO LitTabR per-frame — metode ASLI proposal (skripsinew BAB III), protokol bersih.

Metode asli: fitur POC-ABS per-frame -> flatten -> balancing + imputer + scaler
-> TabR kustom (src/TabR.py: Lightning + FAISS + context freezing). Angka lama
metode ini (~74%) berasal dari holdout kecil (n_external=2 subjek/kelas) dengan
split val level-frame (bocor dalam-subjek), jadi TIDAK pernah dievaluasi bersih.

Skrip ini menjalankan metode yang sama dengan protokol LOSO 56 fold:
- test  = semua frame milik 1 subjek holdout
- val   = 20% SUBJEK train (subjek-disjoint -> early stopping jujur)
- train = frame dari subjek tersisa (diseimbangkan per kelas level subjek,
  seperti resep notebook asli, tapi tanpa membuang subjek test)
- context FAISS = HANYA dari train (proposal: data uji tidak dilibatkan dalam
  pelatihan MAUPUN pembentukan context)
- keputusan level subjek = mean probabilitas frame >= 0.5

Pembanding sah: headline pipeline agregat (test 47,62%, baseline 55,36%).
Pembanding TIDAK SAH: 74% notebook lama (split bocor).

Contoh:
    .venv/bin/python scripts/run_loso_lit_tabr.py --folds 0 1 2 --tag smoke
    .venv/bin/python scripts/run_loso_lit_tabr.py --tag after_s1 --seeds 1
    .venv/bin/python scripts/run_loso_lit_tabr.py --phases before after --tag both_s1
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
import warnings
from pathlib import Path

# Terminal bersih: hanya progress bar + ringkasan fold. Peringatan Lightning /
# sklearn yang tidak actionable disaring di sini.
warnings.filterwarnings('ignore')
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)
logging.getLogger('lightning.pytorch').setLevel(logging.ERROR)
logging.getLogger('faiss.loader').setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning.loggers import CSVLogger
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

DEFAULT_FEATURES = ROOT / 'experiments/features/apex/poc_abs_run2_full.pkl'
RANDOM_SEED = 72
LABEL_MAP = {'anxiety_rendah': 0, 'anxiety_tinggi': 1}
META_COLS = [
    'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
    'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path',
    'frame', 'target', 'event_id',
]


def balance_context_by_label(X: torch.Tensor, y: torch.Tensor):
    """Resep asli notebook: context seimbang per label (min count per kelas)."""
    idx0 = (y == 0).nonzero(as_tuple=True)[0]
    idx1 = (y == 1).nonzero(as_tuple=True)[0]
    n = min(len(idx0), len(idx1))
    idx0 = idx0[torch.randperm(len(idx0))[:n]]
    idx1 = idx1[torch.randperm(len(idx1))[:n]]
    idx = torch.cat([idx0, idx1])
    idx = idx[torch.randperm(len(idx))]
    return X[idx], y[idx]


def balance_subjects_by_label(subj_labels: pd.Series, seed: int) -> list[str]:
    """Downsample daftar subjek per kelas ke jumlah minimum (resep asli:
    `prepare_balanced_subject_data_from_csv`), tapi di dalam fold train."""
    rng = random.Random(seed)
    grouped = {lab: sorted(subj_labels[subj_labels == lab].index) for lab in subj_labels.unique()}
    n_min = min(len(v) for v in grouped.values())
    chosen = []
    for lab, subjs in grouped.items():
        subjs = subjs.copy()
        rng.shuffle(subjs)
        chosen.extend(subjs[:n_min])
    return sorted(chosen)


def run_fold(
    df: pd.DataFrame,
    feature_cols: list[str],
    subject: str,
    train_subjects: list[str],
    subj_labels: pd.Series,
    fold_dir: Path,
    args,
    seed: int,
) -> dict:
    pl.seed_everything(seed, workers=True)
    rng = random.Random(seed)

    df_test = df[df['participant'] == subject]
    assert not df_test.empty, f'subjek {subject} tidak punya baris'

    # balancing level subjek di dalam train (resep asli, tanpa menyentuh test)
    if args.balance_subjects:
        kept = balance_subjects_by_label(subj_labels[train_subjects], seed)
    else:
        kept = sorted(train_subjects)

    # val = 20% subjek train (disjoint), stratified label subjek
    kept_labels = subj_labels[kept]
    by_label = {lab: sorted(kept_labels[kept_labels == lab].index) for lab in kept_labels.unique()}
    val_subjects = []
    for lab, subjs in by_label.items():
        subjs = subjs.copy()
        rng.shuffle(subjs)
        n_val = max(1, int(round(len(subjs) * args.val_size)))
        val_subjects.extend(subjs[:n_val])
    val_subjects = sorted(val_subjects)
    tr_subjects = sorted(set(kept) - set(val_subjects))

    # anti-bocor: subjek test tidak boleh ada di mana pun selain test
    assert subject not in tr_subjects and subject not in val_subjects

    df_train = df[df['participant'].isin(tr_subjects)]
    df_val = df[df['participant'].isin(val_subjects)]

    imputer = SimpleImputer(strategy='mean')
    scaler = StandardScaler()
    X_train_np = scaler.fit_transform(imputer.fit_transform(df_train[feature_cols]))
    X_val_np = scaler.transform(imputer.transform(df_val[feature_cols]))
    X_test_np = scaler.transform(imputer.transform(df_test[feature_cols]))

    X_train = torch.tensor(X_train_np, dtype=torch.float32)
    y_train = torch.tensor(df_train['target'].values, dtype=torch.long)
    X_val = torch.tensor(X_val_np, dtype=torch.float32)
    y_val = torch.tensor(df_val['target'].values, dtype=torch.long)
    X_test = torch.tensor(X_test_np, dtype=torch.float32)
    y_test = df_test['target'].values

    ctx_x, ctx_y = balance_context_by_label(X_train, y_train)
    assert len(ctx_x) > 0 and ctx_x.shape[0] == ctx_y.shape[0]

    from tabr.TabR import LitTabR
    from tabr.data_module import TabRDataModule

    dm = TabRDataModule(
        X_train, y_train, X_val, y_val, ctx_x, ctx_y, ctx_x, ctx_y,
        batch_size=args.batch_size, num_workers=0,
    )
    model = LitTabR(
        in_dim=len(feature_cols), num_classes=2, d=128, m=args.m,
        encoder_blocks=0, dropout=0.1, lr=args.lr,
        freeze_context_epoch=args.freeze_epoch,
    )
    # context awal sebelum fit (deterministik, tidak bergantung sanity val steps)
    model.set_context(ctx_x, ctx_y)

    trainer = pl.Trainer(
        max_epochs=args.max_epochs,
        accelerator=args.device,
        devices=1,
        logger=CSVLogger(save_dir=str(fold_dir), name='logs'),
        callbacks=[EarlyStopping(monitor='val_loss', patience=args.patience, mode='min')],
        enable_progress_bar=True,
        enable_model_summary=False,
        num_sanity_val_steps=0,
        log_every_n_steps=25,
    )
    t0 = time.time()
    trainer.fit(model, datamodule=dm)
    train_seconds = time.time() - t0

        # eval: context dari encoder akhir
    model.eval()
    model.set_context(ctx_x, ctx_y)
    device = next(model.parameters()).device

    def prob_of(X: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            logits = model(X.to(device))
            return torch.softmax(logits, dim=1)[:, 1].cpu().numpy()

    # train dihitung TANPA self-leak (query = context): model.train() membuat
    # forward membuang kolom tetangga pertama, sehingga angkanya adil.
    model.train()
    train_prob = prob_of(X_train)
    model.eval()

    prob = prob_of(X_test)
    val_prob = prob_of(X_val)

    train_acc = float(accuracy_score(df_train['target'].values, (train_prob >= 0.5).astype(int)))
    val_acc = float(accuracy_score(y_val.numpy(), (val_prob >= 0.5).astype(int)))
    frame_acc = float(accuracy_score(y_test, (prob >= 0.5).astype(int)))
    subject_prob = float(prob.mean())
    subject_true = int(y_test[0])
    subject_pred = int(subject_prob >= 0.5)

    # ringkasan per fold yang mudah dibaca (Indonesia)
    yakin = 'TINGGI' if subject_true == 1 else 'RENDAH'
    tebak = 'TINGGI' if subject_pred == 1 else 'RENDAH'
    cocok = 'BENAR' if subject_pred == subject_true else 'SALAH'
    ringkas = (
        f"\n┌─ FOLD {subject} ─ {cocok}\n"
        f"│  asli {yakin:6s} | prediksi {tebak:6s} (yakin {subject_prob * 100:5.1f}%)\n"
        f"│  akurasi: train {train_acc * 100:5.1f}% | val {val_acc * 100:5.1f}% | test {frame_acc * 100:5.1f}%\n"
        f"│  gap train-test {abs(train_acc - frame_acc) * 100:5.1f} poin | epoch {int(trainer.current_epoch + 1):2d} | {time.time() - t0:4.0f}s\n"
        f"└{'─' * 60}"
    )
    print(ringkas, flush=True)

    metrics = {
        'subject': subject,
        'subject_true': subject_true,
        'subject_prob': subject_prob,
        'subject_pred': subject_pred,
        'subject_correct': int(subject_pred == subject_true),
        'n_frames_test': int(len(df_test)),
        'frame_acc': frame_acc,
        'train_acc': train_acc,
        'val_acc': val_acc,
        'n_train_rows': int(len(df_train)),
        'n_val_subjects': int(len(val_subjects)),
        'n_train_subjects': int(len(tr_subjects)),
        'ctx_size': int(len(ctx_x)),
        'epochs_trained': int(trainer.current_epoch + 1),
        'train_seconds': round(train_seconds, 1),
        'seed': seed,
    }
    fold_dir.mkdir(parents=True, exist_ok=True)
    (fold_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    (fold_dir / 'DONE.json').write_text(json.dumps({'seed': seed}))
    return metrics


def collect(out_root: Path, subjects: list[str], seeds: list[int], subject_true_map: dict) -> None:
    rows = []
    for i, s in enumerate(subjects):
        for seed in seeds:
            p = out_root / f'fold_{i:03d}' / f'seed_{seed}' / 'metrics.json'
            if p.exists():
                rows.append(json.loads(p.read_text()))
    if not rows:
        print('belum ada fold selesai')
        return

    y_true = np.array([subject_true_map[r['subject']] for r in rows])
    y_pred = np.array([r['subject_pred'] for r in rows])
    y_prob = np.array([r['subject_prob'] for r in rows])
    # baseline mayoritas: prediksi kelas mayoritas dari seluruh subjek (LOSO:
    # mayoritas train konstan per fold, nilainya sama)
    n1 = sum(subject_true_map.values())
    baseline = max(n1, len(subject_true_map) - n1) / len(subject_true_map)

    acc = float(accuracy_score(y_true, y_pred))
    ba = float(balanced_accuracy_score(y_true, y_pred))
    mcc = float(matthews_corrcoef(y_true, y_pred))
    try:
        auc = float(roc_auc_score(y_true, y_prob))
    except ValueError:
        auc = float('nan')
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    per_seed = {}
    for seed in seeds:
        rs = [r for r in rows if r['seed'] == seed]
        if not rs:
            continue
        yt = np.array([subject_true_map[r['subject']] for r in rs])
        yp = np.array([r['subject_pred'] for r in rs])
        per_seed[seed] = float(accuracy_score(yt, yp))

    epochs = [r['epochs_trained'] for r in rows]
    early = sum(1 for e in epochs if e < 10)

    train_accs = [r['train_acc'] for r in rows if 'train_acc' in r]
    val_accs = [r['val_acc'] for r in rows if 'val_acc' in r]
    test_accs = [r['frame_acc'] for r in rows]

    lines = [
        '# Ringkasan LOSO LitTabR per-frame (metode asli, protokol bersih)',
        '',
        f'- baris hasil: {len(rows)} (subjek x seed)',
        f'- subjek: {len(subject_true_map)} | kelas 1 (tinggi): {n1} | baseline mayoritas: {baseline * 100:.2f}%',
        '',
        '## Akurasi (persen)',
        '',
        '| | train | val | test |',
        '|---|---|---|---|',
        f'| rata-rata frame | {np.mean(train_accs) * 100:.1f}% | {np.mean(val_accs) * 100:.1f}% | {np.mean(test_accs) * 100:.1f}% |',
        f'| **level subjek (keputusan akhir)** | | | **{acc * 100:.2f}%** |',
        f'| baseline mayoritas | | | {baseline * 100:.2f}% |',
        '',
        'Cara baca: train jauh di atas test = hafalan; val ~50% = pemilihan epoch',
        'nyaris acak; test level subjek vs baseline = wasit akhir.',
        '',
        '## Metrik lain level subjek (pooled)',
        '',
        '| metrik | nilai |',
        '|---|---|',
        f'| balanced accuracy | {ba:.4f} |',
        f'| MCC | {mcc:.4f} |',
        f'| AUC | {auc:.4f} |',
        '',
        '## Accuracy level subjek per seed',
        '',
        '| seed | accuracy |',
        '|---|---|',
        *[f'| {s} | {a * 100:.2f}% |' for s, a in sorted(per_seed.items())],
        '',
        f'mean ± std: {np.mean(list(per_seed.values())) * 100:.2f}% ± {np.std(list(per_seed.values())) * 100:.2f}%' if len(per_seed) > 1 else '(1 seed)',
        '',
        '## Confusion matrix (pooled, baris=true)',
        '',
        f'- TN {cm[0, 0]} | FP {cm[0, 1]}',
        f'- FN {cm[1, 0]} | TP {cm[1, 1]}',
        '',
        '## Kesehatan training',
        '',
        f'- epoch terlatih: mean {np.mean(epochs):.1f}, median {int(np.median(epochs))}',
        f'- fold berhenti < 10 epoch: {early}/{len(epochs)}',
        '',
        '## Pembanding',
        '',
        '- pipeline agregat (LOSO bersih yang sama): test 47,62%, MCC -0,1037, AUC 0,3978',
        '- baseline mayoritas: 55,36%',
        '- notebook asli ~74%: TIDAK SAH (holdout 4 subjek + val level-frame bocor)',
        '',
    ]
    (out_root / 'summary.md').write_text('\n'.join(lines))
    print('\n'.join(lines[:22]))


def main() -> None:
    parser = argparse.ArgumentParser(description='LOSO LitTabR per-frame (metode asli).')
    parser.add_argument('--features', type=Path, default=DEFAULT_FEATURES)
    parser.add_argument('--phases', nargs='+', default=['after'], choices=['before', 'after'])
    parser.add_argument('--folds', nargs='*', type=int, default=None, help='subset indeks fold (default: semua)')
    parser.add_argument('--seeds', type=int, default=1, help='jumlah seed per fold')
    parser.add_argument('--tag', default='after_s1')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--device', default='cuda', choices=['cuda', 'cpu'])
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--max-epochs', type=int, default=50)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--freeze-epoch', type=int, default=6)
    parser.add_argument('--m', type=int, default=4)
    parser.add_argument('--patience', type=int, default=10)
    parser.add_argument('--val-size', type=float, default=0.2)
    parser.add_argument('--balance-subjects', action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    df = pd.read_pickle(args.features)
    df = df[df['phase'].isin(args.phases)].copy()
    df['target'] = df['label'].map(LABEL_MAP)
    assert df['target'].notna().all(), 'ada label di luar LABEL_MAP'
    feature_cols = [c for c in df.columns if c not in META_COLS]
    print(f'baris: {len(df)} | fitur: {len(feature_cols)} | fase: {args.phases}')

    subjects = sorted(df['participant'].unique())
    # label subjek = modus target (after-only: pasti satu nilai per subjek)
    subj_labels = df.groupby('participant')['target'].agg(lambda s: int(s.mode().iloc[0]))
    subject_true_map = subj_labels.to_dict()

    out_root = ROOT / 'output/training' / f'lit_tabr_perframe_{args.tag}'
    out_root.mkdir(parents=True, exist_ok=True)

    fold_ids = args.folds if args.folds else range(len(subjects))
    seeds = list(range(args.seeds))
    n_done = 0
    for i in fold_ids:
        subject = subjects[i]
        for seed in seeds:
            fold_dir = out_root / f'fold_{i:03d}' / f'seed_{seed}'
            if (fold_dir / 'DONE.json').exists() and not args.force:
                print(f'fold {i:03d} seed {seed}: lewati (DONE)')
                continue
            train_subjects = [s for s in subjects if s != subject]
            t0 = time.time()
            m = run_fold(df, feature_cols, subject, train_subjects, subj_labels,
                         fold_dir, args, RANDOM_SEED + seed)
            n_done += 1
            ok = '✓' if m['subject_correct'] else '✗'
            print(f"fold {i:03d} seed {seed} [{ok}] {subject[:28]:28s} "
                  f"prob {m['subject_prob']:.3f} frame_acc {m['frame_acc'] * 100:5.1f}% "
                  f"epoch {m['epochs_trained']:2d} ctx {m['ctx_size']} "
                  f"({time.time() - t0:.0f}s)")

    collect(out_root, subjects, seeds, subject_true_map)
    print(f'selesai. {n_done} fold-seed dilatih. summary: {out_root}/summary.md')


if __name__ == '__main__':
    main()
