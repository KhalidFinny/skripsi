#!/usr/bin/env python
"""ABLASI KELUARGA FITUR pada gerbang within-subject.

Konteks: pada tabel fitur v3fixed, AUC lintas-subjek tidak melewati derau seleksi
(p=0,385) dan gerbang within-subject hanya BA 0,639 (p=0,105). Sebelum mengubah
representasi, tanya dulu: keluarga fitur MANA yang membawa sisa sinyal itu?

Dua uji dipakai (keduanya dari stage_5_gate.py):
  - LOSO sesi mentah : 36 baris (18 subjek x 2 sesi)
  - LOSO selisih     : 18 baris (after - before), menghapus identitas eksak

Keluarga dipisah menurut jenis sinyalnya (12 sinyal x 5 ROI):
  magnitude : mean_m, max_m, mean_abs_x, mean_abs_y, motion_count
  arah      : mean_x, mean_y, mean_x_mov, mean_y_mov
  koherensi : angle_cos, angle_sin, angle_R

Cara pakai:
    .venv/bin/python scripts/audit_feature_family_casme2.py \
        --features experiments/features/apex/poc_abs_roi_signals_v3fixed_poc_temporal.pkl
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import stage_5_gate as gate  # noqa: E402

MAG = ('mean_m', 'max_m', 'mean_abs_x', 'mean_abs_y', 'motion_count')
DIR = ('mean_x', 'mean_y', 'mean_x_mov', 'mean_y_mov')
COH = ('angle_cos', 'angle_sin', 'angle_R')
DESC = ('peak', 'ttp', 'rise', 'fall', 'auc')


ROIS = ('mulut', 'mata_kiri', 'mata_kanan', 'alis_kiri', 'alis_kanan')


def signal_of(col: str) -> str | None:
    """Ambil nama sinyal dasar dari '<roi>_<signal>' atau '<roi>_<signal>_<desc>'."""
    for roi in ROIS:
        if col.startswith(roi + '_'):
            rest = col[len(roi) + 1:]
            for d in DESC:
                if rest.endswith('_' + d):
                    rest = rest[: -len(d) - 1]
                    break
            return rest
    return None


def families(cols: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {'SEMUA': list(cols)}
    for name, keys in (('magnitude', MAG), ('arah', DIR), ('koherensi', COH)):
        out[name] = [c for c in cols if signal_of(c) in keys]
    for d in DESC:
        out[f'desc:{d}'] = [c for c in cols if c.endswith(f'_{d}')]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', type=Path, required=True)
    ap.add_argument('--permutations', type=int, default=200)
    ap.add_argument('--only', nargs='+', default=None,
                    help='batasi ke keluarga tertentu (mis. desc:rise arah SEMUA)')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_feature_family')
    args = ap.parse_args()

    df = pd.read_pickle(args.features)
    if 'target' not in df.columns:
        df = df.copy()
        df['target'] = df['label'].map({'anxiety_rendah': 0, 'anxiety_tinggi': 1})
    meta_cols = {'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
                 'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path',
                 'frame', 'target', 'event_id', 'date'}
    all_cols = [c for c in df.columns
                if c not in meta_cols and pd.api.types.is_numeric_dtype(df[c])]
    fams = families(all_cols)
    if args.only:
        fams = {k: v for k, v in fams.items() if k in args.only}

    print(f'{args.features.name}: {len(df)} baris, {len(all_cols)} fitur\n')
    rows = []
    print(f"{'keluarga':16s} {'n':>4s} {'LOSO_sesi':>10s} {'p':>7s} "
          f"{'LOSO_selisih':>13s} {'p':>7s}")
    for name, cols in fams.items():
        if not cols:
            continue
        a = gate.within_subject_loso(df, cols, args.permutations)
        b = gate.within_subject_diff_loso(df, cols, args.permutations)
        rows.append({'family': name, 'n_features': len(cols),
                     'loso_session_ba': a['balanced_accuracy'], 'loso_session_p': a['p_value'],
                     'loso_diff_ba': b['balanced_accuracy'], 'loso_diff_p': b['p_value'],
                     'loso_diff_acc': b.get('accuracy'), 'loso_diff_mcc': b.get('mcc')})
        print(f"{name:16s} {len(cols):4d} {a['balanced_accuracy']:10.4f} {a['p_value']:7.4f} "
              f"{b['balanced_accuracy']:13.4f} {b['p_value']:7.4f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows).sort_values('loso_session_ba', ascending=False)
    out.to_csv(args.out / 'summary.csv', index=False)
    print(f'\nKeluaran: {args.out}/summary.csv')


if __name__ == '__main__':
    main()
