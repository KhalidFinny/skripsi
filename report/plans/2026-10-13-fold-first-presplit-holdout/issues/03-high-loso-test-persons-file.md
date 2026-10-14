# 03 — run_loso --test-persons-file (high)

## Current Problem

`run_loso.py` hanya punya mode LOSO: fold i → test = `participants[i]`
(1 orang). Untuk evaluasi holdout butuh SATU fold dengan test = 12 orang
sekaligus, train/val dari 44 sisanya.

## Target

Argumen baru `--test-persons-file <txt>`:

- Bila diset: abaikan loop 56 fold; jalankan TEPAT SATU fold (`fold_000`):
  - `test_parts` = isi file (divalidasi: semua ada di kolom `participant`,
    kalau tidak → SystemExit dengan daftar yang hilang).
  - `rest` = participants - test_parts; val/train via scan
    `GroupShuffleSplit` + `has_both_labels` yang sudah ada (tanpa perubahan).
  - Semua langkah downstream identik (imputer/scaler fit train, aggregate,
    balance, config, seeds, DONE.json/run_sha1 resume).
- `--fold` dan `--test-persons-file` saling eksklusif.

## Required Design

- Refactor minimal: ekstrak tubuh fold jadi fungsi `run_one_fold(df,
  feature_cols, test_parts, fold_idx, ...)` yang dipanggil dari kedua mode —
  jangan duplikasi 100+ baris.
- DONE.json menyimpan `test_subjects` (list) supaya collect bisa membaca.
- `collect_loso_results.py` iterasi `fold_*` generik — cukup pastikan
  `test_split.csv` tetap tertulis (sudah per fold).

## Tests

- py_compile bersih.
- Dry sense-check: mode lama (tanpa arg baru) tidak menyentuh path kode baru
  (branch hanya aktif bila arg diset).

## Done Criteria

- [ ] Single-fold berjalan atas 12 test persons (verifikasi lewat log
  "subjek train=33 val=11 test=12" kira-kira)
- [ ] Mode LOSO lama tidak berubah
- [ ] DONE.json + test_split.csv tertulis
