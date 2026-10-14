#!/usr/bin/env python
"""Latih model FINAL LitTabR di SEMUA data, simpan artefak yang bisa dipakai.

Ini beda dari LOSO (yang membuang model tiap fold demi evaluasi jujur). Di sini
seluruh 56 subjek dipakai untuk melatih SATU model final, lalu model + scaler +
imputer + context disimpan ke `output/final_model/` supaya bisa dimuat ulang
oleh `scripts/predict.py` untuk inferensi baris baru.

Yang disimpan (output/final_model/):
  model.ckpt      checkpoint Lightning (bobot + hyperparameter)
  preprocessor.joblib   imputer + scaler + daftar kolom fitur
  context.npz     context FAISS (ctx_x, ctx_y) dari data train
  meta.json       info training (n baris, fitur, akurasi train)

Cara pakai:
    .venv/bin/python scripts/train_final_model.py
    .venv/bin/python scripts/predict.py --features <tabel.pkl>

Model ini TIDAK dievaluasi di sini (evaluasi jujur = LOSO, sudah ada di
output/training/). Angka akurasi train di meta.json hanya indikator konvergensi,
BUKAN performa generalisasi.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import pytorch_lightning as pl
from pytorch_lightning.loggers import CSVLogger
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import warnings, logging
warnings.filterwarnings('ignore')
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)
logging.getLogger('lightning.pytorch').setLevel(logging.ERROR)

DEFAULT_FEATURES = ROOT / 'experiments/features/apex/poc_abs_run2_full.pkl'
OUT_DIR = ROOT / 'output/final_model'
RANDOM_SEED = 72
LABEL_MAP = {'anxiety_rendah': 0, 'anxiety_tinggi': 1}
META_COLS = [
    'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
    'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path',
    'frame', 'target', 'event_id',
]


def balance_context_by_label(X: torch.Tensor, y: torch.Tensor):
    idx0 = (y == 0).nonzero(as_tuple=True)[0]
    idx1 = (y == 1).nonzero(as_tuple=True)[0]
    n = min(len(idx0), len(idx1))
    idx0 = idx0[torch.randperm(len(idx0))[:n]]
    idx1 = idx1[torch.randperm(len(idx1))[:n]]
    idx = torch.cat([idx0, idx1])
    idx = idx[torch.randperm(len(idx))]
    return X[idx], y[idx]


def main() -> None:
    ap = argparse.ArgumentParser(description='Latih model final LitTabR di semua data.')
    ap.add_argument('--features', type=Path, default=DEFAULT_FEATURES)
    ap.add_argument('--phases', nargs='+', default=['after'], choices=['before', 'after'])
    ap.add_argument('--out', type=Path, default=OUT_DIR)
    ap.add_argument('--device', default='cuda', choices=['cuda', 'cpu'])
    ap.add_argument('--batch-size', type=int, default=128)
    ap.add_argument('--max-epochs', type=int, default=30)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--freeze-epoch', type=int, default=6)
    ap.add_argument('--m', type=int, default=4)
    args = ap.parse_args()

    pl.seed_everything(RANDOM_SEED, workers=True)

    df = pd.read_pickle(args.features)
    df = df[df['phase'].isin(args.phases)].copy()
    df['target'] = df['label'].map(LABEL_MAP)
    feature_cols = [c for c in df.columns if c not in META_COLS]
    print(f'melatih di {len(df)} baris, {len(feature_cols)} fitur, fase {args.phases}')

    imputer = SimpleImputer(strategy='mean')
    scaler = StandardScaler()
    X_np = scaler.fit_transform(imputer.fit_transform(df[feature_cols]))
    X = torch.tensor(X_np, dtype=torch.float32)
    y = torch.tensor(df['target'].values, dtype=torch.long)

    ctx_x, ctx_y = balance_context_by_label(X, y)

    from tabr.TabR import LitTabR
    from tabr.data_module import TabRDataModule

    # final: train = val = semua data (tidak ada holdout; evaluasi sudah lewat LOSO)
    dm = TabRDataModule(X, y, X, y, ctx_x, ctx_y, ctx_x, ctx_y,
                        batch_size=args.batch_size, num_workers=0)
    model = LitTabR(in_dim=len(feature_cols), num_classes=2, d=128, m=args.m,
                    encoder_blocks=0, dropout=0.1, lr=args.lr,
                    freeze_context_epoch=args.freeze_epoch)
    model.set_context(ctx_x, ctx_y)  # FAISS terbentuk sebelum fit

    args.out.mkdir(parents=True, exist_ok=True)
    trainer = pl.Trainer(
        max_epochs=args.max_epochs, accelerator=args.device, devices=1,
        logger=CSVLogger(save_dir=str(args.out), name='logs'),
        enable_progress_bar=True, enable_model_summary=False,
        num_sanity_val_steps=0, log_every_n_steps=25,
    )
    trainer.fit(model, datamodule=dm)

    # akurasi train (indikator konvergensi, BUKAN generalisasi)
    model.eval()
    model.set_context(ctx_x, ctx_y)
    device = next(model.parameters()).device
    with torch.no_grad():
        prob = torch.softmax(model(X.to(device)), dim=1)[:, 1].cpu().numpy()
    pred = (prob >= 0.5).astype(int)
    train_acc = float(accuracy_score(y.numpy(), pred))
    train_ba = float(balanced_accuracy_score(y.numpy(), pred))

    # simpan artefak
    ckpt = args.out / 'model.ckpt'
    trainer.save_checkpoint(str(ckpt))
    joblib.dump({'imputer': imputer, 'scaler': scaler, 'feature_cols': feature_cols},
                args.out / 'preprocessor.joblib')
    np.savez(args.out / 'context.npz',
             ctx_x=ctx_x.cpu().numpy(), ctx_y=ctx_y.cpu().numpy())
    meta = {
        'n_rows': int(len(df)), 'n_features': len(feature_cols),
        'phases': args.phases, 'train_acc': train_acc, 'train_balanced_acc': train_ba,
        'ctx_size': int(len(ctx_x)), 'label_map': LABEL_MAP,
        'config': {'d': 128, 'm': args.m, 'lr': args.lr, 'batch': args.batch_size,
                   'freeze_epoch': args.freeze_epoch, 'max_epochs': args.max_epochs},
    }
    (args.out / 'meta.json').write_text(json.dumps(meta, indent=2))

    print(f'\nSELESAI. train_acc {train_acc * 100:.1f}% | balanced {train_ba * 100:.1f}%')
    print(f'artefak: {args.out}/')
    print('  model.ckpt  preprocessor.joblib  context.npz  meta.json')
    print('catatan: train_acc adalah konvergensi, BUKAN performa generalisasi.')
    print('performa jujur ada di LOSO (output/training/).')


if __name__ == '__main__':
    main()
