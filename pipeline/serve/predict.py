#!/usr/bin/env python
"""Inferensi: muat model final, prediksi anxiety untuk baris fitur baru.

Memakai artefak dari `scripts/train_final_model.py` (output/final_model/).
Input = tabel fitur dengan format yang sama seperti data training (pkl/xlsx).
Output = per baris: prob anxiety_tinggi + keputusan + keyakinan, dan ringkasan.

Cara pakai:
    .venv/bin/python scripts/predict.py --features <tabel.pkl>
    .venv/bin/python scripts/predict.py --features <tabel.pkl> --out hasil.csv
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import warnings, logging
warnings.filterwarnings('ignore')
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)
logging.getLogger('lightning.pytorch').setLevel(logging.ERROR)

FINAL_DIR = ROOT / 'output/final_model'


def main() -> None:
    ap = argparse.ArgumentParser(description='Prediksi anxiety memakai model final.')
    ap.add_argument('--features', type=Path, required=True, help='tabel fitur (pkl/xlsx)')
    ap.add_argument('--model-dir', type=Path, default=FINAL_DIR)
    ap.add_argument('--threshold', type=float, default=0.5)
    ap.add_argument('--out', type=Path, default=None, help='simpan hasil ke csv')
    args = ap.parse_args()

    prep = joblib.load(args.model_dir / 'preprocessor.joblib')
    feature_cols = prep['feature_cols']
    ctx = np.load(args.model_dir / 'context.npz')
    ctx_x = torch.tensor(ctx['ctx_x'], dtype=torch.float32)
    ctx_y = torch.tensor(ctx['ctx_y'], dtype=torch.long)
    meta = json.loads((args.model_dir / 'meta.json').read_text())

    from tabr.TabR import LitTabR
    # Muat bobot langsung (bukan load_from_checkpoint) supaya tidak bentrok
    # dengan ctx_k/ctx_y yang ikut tersimpan: ctx diisi dari context.npz.
    ckpt = torch.load(args.model_dir / 'model.ckpt', map_location='cpu', weights_only=False)
    state = {k: v for k, v in ckpt['state_dict'].items()
             if not k.startswith(('ctx_k', 'ctx_y'))}
    model = LitTabR(in_dim=len(feature_cols))
    model.load_state_dict(state, strict=False)
    model.eval()
    model.set_default_context(ctx_x, ctx_y)
    model.set_preprocessor(prep['imputer'], prep['scaler'], feature_cols)

    df = pd.read_pickle(args.features) if args.features.suffix == '.pkl' \
        else pd.read_excel(args.features)
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise SystemExit(f'kolom fitur hilang di input: {missing[:5]}'
                         + (f' (+{len(missing) - 5} lagi)' if len(missing) > 5 else ''))

    pred, prob = model.predict_from_df(df, threshold=args.threshold)

    hasil = pd.DataFrame({'prob_anxiety_tinggi': prob.round(4)})
    hasil['keputusan'] = np.where(pred == 1, 'ANXIETY TINGGI', 'ANXIETY RENDAH')
    hasil['keyakinan'] = np.maximum(prob, 1 - prob).round(4)
    for col in ('participant', 'phase', 'question', 'frame'):
        if col in df.columns:
            hasil.insert(0, col, df[col].values)

    print(f'baris diprediksi: {len(hasil)}')
    print(f'  ANXIETY TINGGI: {(pred == 1).sum()} ({(pred == 1).mean() * 100:.1f}%)')
    print(f'  ANXIETY RENDAH: {(pred == 0).sum()} ({(pred == 0).mean() * 100:.1f}%)')
    print(f'  prob rata-rata: {prob.mean():.3f}')
    print(hasil.head(12).to_string(index=False))

    if 'participant' in hasil.columns:
        ringkas = (hasil.groupby('participant')['prob_anxiety_tinggi']
                   .agg(['mean', 'count']).round(4))
        ringkas['keputusan'] = np.where(ringkas['mean'] >= args.threshold,
                                        'ANXIETY TINGGI', 'ANXIETY RENDAH')
        print(f'\nringkasan per subjek ({len(ringkas)}):')
        print(ringkas.to_string())

    if args.out:
        hasil.to_csv(args.out, index=False)
        print(f'\ndisimpan: {args.out}')


if __name__ == '__main__':
    main()
