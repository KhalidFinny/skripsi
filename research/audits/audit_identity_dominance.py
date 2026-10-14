#!/usr/bin/env python
"""Ukur DOMINASI IDENTITAS fitur POC-ABS.

"Dominasi identitas" = proporsi varians sebuah fitur yang dijelaskan oleh
perbedaan antar-orang (eta kuadrat dari ANOVA satu arah dengan grup = peserta).
> 0,5 berarti fitur lebih menyerupai "sidik jari orang" daripada kondisi.

Dipakai untuk membandingkan fitur lama (dari spotting yang rusak) vs fitur baru
(dari spotting yang diperbaiki). Lihat report/findings/audit-spotting-casme2.md.

Cara pakai:
    .venv/bin/python scripts/audit_identity_dominance.py \
        --features experiments/features/apex/poc_abs_roi_signals_v3_full.pkl
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

META = {'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
        'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path', 'frame'}


def eta_squared(values: np.ndarray, groups: np.ndarray) -> float:
    """Proporsi varians yang dijelaskan antar-grup (identitas)."""
    df = pd.DataFrame({'v': values, 'g': groups}).dropna()
    if df.empty:
        return float('nan')
    grand = df['v'].mean()
    ss_total = float(((df['v'] - grand) ** 2).sum())
    if ss_total <= 0:
        return float('nan')
    ss_between = float(sum(len(g) * (g['v'].mean() - grand) ** 2 for _, g in df.groupby('g')))
    return ss_between / ss_total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', type=Path, required=True)
    ap.add_argument('--group', default='participant', help='kolom grup (default peserta)')
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()

    df = pd.read_pickle(args.features)
    sig_cols = [c for c in df.columns if c not in META]
    print(f'{args.features.name}: {len(df)} baris, {len(sig_cols)} kolom sinyal')
    print(f'grup: {args.group} ({df[args.group].nunique()} unik)')

    rows = []
    for c in sig_cols:
        v = pd.to_numeric(df[c], errors='coerce')
        e = eta_squared(v.to_numpy(dtype=float), df[args.group].to_numpy())
        if not np.isnan(e):
            rows.append({'signal': c, 'eta_squared': e})
    out = pd.DataFrame(rows).sort_values('eta_squared', ascending=False)
    print(f'\nmedian dominasi identitas: {out["eta_squared"].median():.3f} '
          f'(n={len(out)} sinyal)')
    print('\n10 tertinggi:')
    print(out.head(10).to_string(index=False))
    print('\n10 terendah:')
    print(out.tail(10).to_string(index=False))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.out, index=False)
        print(f'\nKeluaran: {args.out}')


if __name__ == '__main__':
    main()
