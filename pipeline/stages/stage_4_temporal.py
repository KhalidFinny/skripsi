#!/usr/bin/env python
"""Bangun fitur temporal onset->apex->offset dari tabel fitur POC-ABS per frame.

Masalah yang diselesaikan (sebab #2 penurunan akurasi LOSO):
  Tabel ROI25 hanya menyimpan ringkasan STATIS satu frame (`*_mean_m`,
  `*_mean_abs_x`, `*_mean_abs_y`, `*_motion_count`, dan sejak perbaikan
  arah: `*_mean_x`, `*_mean_y` yang BERTANDA). Dinamika gerakan mikro
  (naik dari onset ke apex, lalu turun ke offset) hilang, padahal itu inti
  micro-expression.

Cara kerja:
  Tiap `event_clip` adalah satu lintasan onset->offset (frame 1..N, hasil
  `save_event_clip_frames`). Untuk tiap ROI dan tiap sinyal dasar, script ini
  meringkas lintasan itu jadi 5 deskriptor:

    _peak : nilai maksimum lintasan
    _ttp  : waktu ke puncak, ternormalisasi 0..1 (argmax / (n-1))
    _rise : kemiringan naik  (peak - first) / idx_peak
    _fall : kemiringan turun (last - peak) / (n - 1 - idx_peak)
    _auc  : luas di bawah lintasan, ternormalisasi panjang (trapesium)

Baris keluaran = 1 baris per frame (sama seperti input, supaya run_loso.py
tidak perlu diubah); nilai temporal di-broadcast ke seluruh frame event itu.

Tabel fitur lama TIDAK diubah: keluaran ditulis ke berkas baru.

Contoh:
    .venv/bin/python pipeline/stages/stage_4_temporal.py
    .venv/bin/python pipeline/stages/stage_4_temporal.py --no-xlsx
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / 'experiments/features/apex/poc_abs_roi_signals_full.pkl'
FALLBACK_INPUT = ROOT / 'experiments/features/apex/poc_abs_roi_signals.xlsx'
DEFAULT_OUTPUT = ROOT / 'experiments/features/apex/poc_abs_roi_signals_temporal.pkl'

# Kunci satu event = satu lintasan. event_clip saja tidak cukup: nama
# `event_00014-00020` muncul di banyak sample berbeda.
EVENT_KEYS = ['phase', 'participant', 'question', 'clip', 'event_clip']
# Sinyal dasar per ROI. `*_max_m` sengaja tidak dipakai: nilainya tersensor di
# 3*sqrt(2) = 4.243 (perpindahan maksimum block_size 7).
# `mean_x`/`mean_y` = perpindahan BERTANDA (naik vs turun), melengkapi
# `mean_abs_x`/`mean_abs_y` yang membuang tanda. Urutan alternasi dari yang
# paling panjang supaya `mean_abs_x` tidak salah terbaca sebagai `mean_x`.
BASE_SIGNAL_RE = re.compile(
    r'^(?P<roi>.+)_(?P<signal>'
    r'mean_abs_x|mean_abs_y|motion_count|mean_m|'
    # E3: arah atas blok bergerak + sudut (rata-rata sirkular) + koherensi arah.
    # Ditaruh SEBELUM mean_x/mean_y; walau `$` sudah mengunci akhir string,
    # urutan panjang-dulu menghindari salah-urai kalau pola dilonggarkan nanti.
    r'mean_x_mov|mean_y_mov|angle_cos|angle_sin|angle_R|'
    r'mean_x|mean_y'
    r')$'
)
DESCRIPTORS = ('peak', 'ttp', 'rise', 'fall', 'auc')

# 5 ROI wajah (sama dengan features/roi_config.py). Dipakai untuk
# memisahkan kolom sinyal dasar dari kolom meta saat --only-descriptors.
ROIS = ('mulut', 'mata_kiri', 'mata_kanan', 'alis_kiri', 'alis_kanan')


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == '.pkl':
        return pd.read_pickle(path)
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path)
    return pd.read_excel(path)


def base_signals(feature_cols: list[str]) -> list[tuple[str, str]]:
    """Pasangan (kolom, roi) untuk tiap sinyal dasar yang cocok."""
    pairs = []
    for col in feature_cols:
        m = BASE_SIGNAL_RE.match(col)
        if m is not None:
            pairs.append((col, m.group('roi')))
    return pairs


def describe(values: np.ndarray) -> dict[str, float]:
    """5 deskriptor temporal dari satu lintasan (onset..offset)."""
    v = np.asarray(values, dtype=float)
    n = len(v)
    if n == 0:
        return {d: float('nan') for d in DESCRIPTORS}
    peak_idx = int(np.nanargmax(v)) if not np.isnan(v).all() else 0
    peak = float(v[peak_idx])
    last = float(v[-1])
    first = float(v[0])
    rise = (peak - first) / peak_idx if peak_idx > 0 else 0.0
    fall_span = (n - 1) - peak_idx
    fall = (last - peak) / fall_span if fall_span > 0 else 0.0
    auc = float(np.trapezoid(v)) / (n - 1) if n > 1 else 0.0
    ttp = peak_idx / (n - 1) if n > 1 else 0.0
    return {'peak': peak, 'ttp': ttp, 'rise': rise, 'fall': fall, 'auc': auc}


def build_event_descriptors(df: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """1 baris per event: kolom <signal>_<descriptor>."""
    records = []
    for key, sub in df.groupby(EVENT_KEYS, sort=False, dropna=False):
        sub = sub.sort_values('frame', kind='stable')
        row = dict(zip(EVENT_KEYS, key))
        for col, _roi in pairs:
            for name, value in describe(sub[col].to_numpy()).items():
                row[f'{col}_{name}'] = value
        records.append(row)
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description='Fitur temporal onset->apex->offset dari tabel POC-ABS per frame.')
    parser.add_argument('--input', type=Path, default=None,
                        help=f'tabel per-frame (pkl/csv/xlsx). Default: {DEFAULT_INPUT}')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT,
                        help=f'tabel keluaran (.pkl). Default: {DEFAULT_OUTPUT}')
    parser.add_argument('--no-xlsx', action='store_true',
                        help='jangan tulis salinan .xlsx di sebelah keluaran pkl')
    parser.add_argument('--descriptors', nargs='+', default=list(DESCRIPTORS),
                        choices=list(DESCRIPTORS),
                        help='deskriptor temporal yang dipakai (default: semua). '
                             'Audit 2026-10-10: `rise` saja paling informatif untuk '
                             'status kecemasan; menambah yang lain justru mengencerkan.')
    parser.add_argument('--only-descriptors', action='store_true',
                        help='keluarkan HANYA kolom kunci + deskriptor terpilih '
                             '(buang sinyal dasar per-frame). Dipakai untuk '
                             'representasi ramping, mis. --descriptors rise.')
    args = parser.parse_args()

    input_path = args.input
    if input_path is None:
        input_path = DEFAULT_INPUT if DEFAULT_INPUT.exists() else FALLBACK_INPUT
    if not input_path.exists():
        raise SystemExit(f'Tabel fitur tidak ditemukan: {input_path}')

    df = load_table(input_path)
    print(f'Input : {input_path} ({df.shape[0]} baris, {df.shape[1]} kolom)')

    pairs = base_signals(list(df.columns))
    if not pairs:
        raise SystemExit('Tidak ada sinyal dasar yang cocok; cek pola nama kolom.')
    rois = sorted({roi for _col, roi in pairs})
    print(f'Sinyal dasar: {len(pairs)} ({len(rois)} ROI x {len(pairs) // len(rois)} sinyal), '
          f'{len(args.descriptors)} deskriptor -> {len(pairs) * len(args.descriptors)} kolom baru')

    temporal = build_event_descriptors(df, pairs)
    if set(args.descriptors) != set(DESCRIPTORS):
        keep = [c for c in temporal.columns if c in EVENT_KEYS
                or any(c.endswith(f'_{d}') for d in args.descriptors)]
        temporal = temporal[keep]
        print(f'Deskriptor dibatasi ke {args.descriptors}: {len(keep) - len(EVENT_KEYS)} kolom')
    print(f'Event: {len(temporal)} lintasan')

    if args.only_descriptors:
        # Tetap 1 baris per FRAME (agregasi mean+std hilir tidak berubah), tapi
        # SEMUA sinyal dasar per-frame dibuang; hanya kunci + meta + deskriptor.
        # Jangan pakai `pairs` saja: BASE_SIGNAL_RE tidak mencocokkan `*_max_m`
        # (sinyal yang tidak punya deskriptor), jadi kolom itu akan tertinggal.
        roi_prefix = tuple(f'{roi}_' for roi in ROIS)
        signal_cols = {c for c in df.columns
                       if c.startswith(roi_prefix) and not any(c.endswith(f'_{d}') for d in DESCRIPTORS)}
        keep_df = [c for c in df.columns if c not in signal_cols]
        out = df[keep_df].merge(temporal, on=EVENT_KEYS, how='left', validate='many_to_one')
    else:
        out = df.merge(temporal, on=EVENT_KEYS, how='left', validate='many_to_one')
    new_cols = [c for c in temporal.columns if c not in EVENT_KEYS]
    if len(out) != len(df):
        raise SystemExit(f'Jumlah baris berubah: {len(df)} -> {len(out)}')
    if out[new_cols].isna().any().any():
        bad = out[new_cols].isna().any()
        raise SystemExit(f'Ada NaN di kolom temporal: {bad[bad].index.tolist()[:5]}')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_pickle(args.output)
    print(f'Keluaran: {args.output} ({out.shape[0]} baris, {out.shape[1]} kolom)')
    if not args.no_xlsx:
        xlsx_path = args.output.with_suffix('.xlsx')
        out.to_excel(xlsx_path, index=False)
        print(f'Keluaran: {xlsx_path}')
    print(f'Kolom baru: {len(new_cols)} (contoh: {new_cols[:5]})')


if __name__ == '__main__':
    main()
