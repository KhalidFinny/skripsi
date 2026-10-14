# 03 — Fitur temporal ROI onset→apex→offset

**Severity:** high

## Current Problem

25 fitur ROI25 semuanya ringkasan statis pada satu frame
(`*_mean_m`, `*_max_m`, `*_mean_abs_x`, `*_mean_abs_y`, `*_motion_count`),
dihitung per frame di `scripts/extract_features_poc_abs.py:325-333`. Dinamika
gerakan mikro (naik dari onset ke apex, turun ke offset) hilang, padahal itu
inti micro-expression (TPAMI ME survey 2022; keluarga fitur MDMO/LMP).

Tabel per-frame sudah memuat lintasan tiap ROI per event (`frame` 2..N untuk
tiap `event_clip`), tapi belum pernah diringkas jadi deskriptor temporal.

## Target

Script baru `scripts/build_temporal_features.py` yang membaca tabel per-frame
dan menulis tabel fitur baru berisi 25 fitur lama + deskriptor temporal per
ROI. File lama tidak diubah.

## Required Design

- Input default `experiments/features/apex/poc_abs_roi_signals_full.pkl`
  (fallback xlsx), output default
  `experiments/features/apex/poc_abs_roi_signals_temporal.pkl` (+ `.xlsx`).
- Kelompokkan per `event_clip` (satu event = satu lintasan onset→offset),
  urut `frame`.
- Untuk tiap ROI dan sinyal dasar (`mean_m`, `mean_abs_x`, `mean_abs_y`,
  `motion_count`), hitung dari lintasan itu:
  `_peak` (nilai maksimum), `_ttp` (indeks puncak / panjang, 0..1),
  `_rise` (kemiringan naik: (peak - first) / idx_peak),
  `_fall` (kemiringan turun: (last - peak) / (n - 1 - idx_peak)),
  `_auc` (trapesium ternormalisasi panjang).
- `_max_m` tidak dipakai sebagai sinyal dasar (tersensor di 4.243); tetap
  dibuang seperti sekarang.
- Baris keluaran = 1 baris per frame tetap dipertahankan (supaya
  `run_loso.py` tidak perlu diubah), kolom temporal di-*broadcast* ke semua
  frame event itu.
- Kolom meta tidak berubah; kolom fitur lama tetap ada.
- Argumen: `--input`, `--output`, `--no-xlsx`.
- Deterministik, tanpa dependensi baru (pandas/numpy saja).

## Tests

- Parse AST dan `--help`.
- Jalankan script pada pkl nyata (ringan, tanpa training) lalu cek: jumlah
  baris sama dengan input, kolom temporal bertambah, tidak ada NaN di kolom
  temporal, jumlah `event_clip` sama.

## Done Criteria

- [ ] `scripts/build_temporal_features.py` ada dan jalan.
- [ ] Output berisi kolom temporal per ROI.
- [ ] Tabel fitur lama tidak tersentuh.
- [ ] Jumlah baris output = jumlah baris input.
