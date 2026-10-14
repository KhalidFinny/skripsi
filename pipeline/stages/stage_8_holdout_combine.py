#!/usr/bin/env python3
"""combine_feature_tables.py — Gabung tabel fitur train-pool + holdout (fold-first).

Dipakai stage 8 pipeline v3: fitur temporal dari 44 orang train pool digabung
dengan fitur temporal 12 orang holdout (diekstrak dengan resep IDENTIK) menjadi
satu tabel untuk `run_loso.py --test-persons-file`.

Validasi keras:
  - kolom HARUS identik (nama DAN urutan) — beda urutan berarti resep/versi
    ekstraksi berbeda dan tabel tidak boleh digabung diam-diam;
  - orang (kolom `participant`) antar sumber HARUS disjoint — tumpang tindih
    berarti pre-split bocor.
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--inputs', type=str, nargs='+', required=True,
                    help='pkl fitur, urutan bebas (minimal 2)')
    ap.add_argument('--output', type=str, required=True)
    args = ap.parse_args()

    if len(args.inputs) < 2:
        sys.exit('GAGAL: butuh minimal 2 tabel untuk digabung.')

    frames = []
    seen_people: set[str] = set()
    ref_cols = None
    for path in args.inputs:
        df = pd.read_pickle(path)
        cols = list(df.columns)
        if ref_cols is None:
            ref_cols = cols
        elif cols != ref_cols:
            beda = [c for c in cols if c not in set(ref_cols)]
            sys.exit(
                f'GAGAL: kolom {path} tidak identik dengan sumber pertama '
                f'({len(cols)} vs {len(ref_cols)} kolom; contoh beda: {beda[:5]}). '
                f'Ekstraksi ulang dengan resep yang sama.'
            )
        people = set(df['participant'].unique())
        overlap = people & seen_people
        if overlap:
            sys.exit(
                f'GAGAL: {len(overlap)} orang muncul di lebih dari satu sumber '
                f'(contoh: {sorted(overlap)[:5]}). Pre-split bocor — periksa '
                f'split.csv dan SPOT_INCLUDE_PERSONS.'
            )
        seen_people |= people
        print(f'  {path}: {len(df)} baris, {len(people)} orang')
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    out.to_pickle(args.output)
    print(f'Tertulis: {args.output} — {len(out)} baris, {len(seen_people)} orang, '
          f'{len(ref_cols)} kolom')


if __name__ == '__main__':
    main()
