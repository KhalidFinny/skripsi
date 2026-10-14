"""Bangun cache tabel fitur (pkl) dari xlsx + verifikasi bit-identik.

run_loso.py/collect_loso_results.py memakai cache ini kalau ada, jadi baca tabel
turun dari ~32 detik (openpyxl) jadi <1 detik.

Kenapa pkl dan bukan csv: round-trip float lewat csv tidak bit-identik
(pandas menulis/membaca desimal -> beda 1-2 ULP, terbukti saat dites), sedangkan
pickle menyimpan float64 apa adanya. Fitur harus identik dgn xlsx supaya hasil
run tidak bergantung dari cache mana yang dipakai.

Contoh:
    .venv/bin/python pipeline/stages/stage_3_cache.py
    .venv/bin/python pipeline/stages/stage_3_cache.py \
        --xlsx experiments/features/apex/poc_abs_roi_signals_neutral.xlsx \
        --pkl experiments/features/apex/poc_abs_roi_signals_neutral_full.pkl
"""

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX = ROOT / 'experiments/features/apex/poc_abs_roi_signals.xlsx'
DEFAULT_PKL = ROOT / 'experiments/features/apex/poc_abs_roi_signals_full.pkl'


def main() -> None:
    parser = argparse.ArgumentParser(description='Bangun cache pkl dari tabel fitur xlsx.')
    parser.add_argument('--xlsx', type=Path, default=DEFAULT_XLSX)
    parser.add_argument('--pkl', type=Path, default=None,
                        help='Default: <xlsx> dengan suffix _full.pkl.')
    args = parser.parse_args()

    xlsx = args.xlsx
    pkl = args.pkl or xlsx.with_name(f'{xlsx.stem}_full.pkl')
    if not xlsx.exists():
        raise SystemExit(f'Tabel fitur tidak ditemukan: {xlsx}')

    t = time.time()
    dx = pd.read_excel(xlsx)
    print(f'xlsx: {dx.shape} in {time.time() - t:.1f}s')
    dx.to_pickle(pkl)
    print(f'wrote {pkl.name}: {pkl.stat().st_size / 1e6:.1f} MB')

    t = time.time()
    dp = pd.read_pickle(pkl)
    print(f'pkl : {dp.shape} in {time.time() - t:.2f}s')

    assert list(dx.columns) == list(dp.columns), 'kolom beda'
    assert dx.shape == dp.shape, 'shape beda'
    for c in dx.columns:
        if pd.api.types.is_numeric_dtype(dx[c]):
            a = dx[c].to_numpy(dtype=np.float64)
            b = dp[c].to_numpy(dtype=np.float64)
            assert np.array_equal(a, b, equal_nan=True), f'kolom numerik {c} tidak identik'
        else:
            assert (dx[c].astype(str) == dp[c].astype(str)).all(), f'kolom {c} tidak identik'
    print(f'IDENTIK bit-per-bit: {len(dx.columns)} kolom, {dx.shape[0]} baris')


if __name__ == '__main__':
    main()
