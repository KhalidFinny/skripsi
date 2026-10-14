# 01 — Runner LOSO LitTabR per-frame

**Severity:** critical

## Current Problem

Tidak ada cara mengevaluasi metode asli (LitTabR per-frame) dengan protokol
LOSO. `scripts/run_loso.py` hanya melayani TabR resmi lewat
`third_party/tabular-dl-tabr-official`, dan metode asli hanya pernah jalan di
notebook dengan split bocor. Bonus bug: `src/TabR.py:26` mendefinisikan param
`freeze_context_epo`, tapi `on_train_epoch_start` (baris 128) membaca
`self.hparams.freeze_context_epoch` → AttributeError saat epoch 0 mulai.

## Target

`scripts/run_loso_lit_tabr.py` yang menjalankan LOSO 56 fold atas tabel
per-frame, memakai `LitTabR` dari `src/TabR.py`, dengan resep asli:

1. Baca `--features` (default `experiments/features/apex/poc_abs_run2_full.pkl`).
2. Filter `--phases` (default `after`; nilai lain: `before after`).
3. Fitur = 60 kolom sinyal (semua kolom setelah 13 kolom meta, pola yang sama
   dengan `run_loso.py`); target = `label` (anxiety_tinggi=1, rendah=0).
4. Per fold (subjek holdout ke-i, urutan terurut):
   - train = semua frame subjek lain; test = frame subjek holdout.
   - val = 20% subjek train (stratified label subjek, seed fold) — BUKAN frame
     acak (resep notebook bocor di sini; kita perbaiki).
   - Assert: participant test ∉ train, ∉ val, dan (otomatis) ∉ context.
   - SimpleImputer(mean) + StandardScaler fit di train, transform val/test.
   - Context = `balance_context_by_label(train)` (fungsi yang sama dengan
     notebook, di-inline ke runner; tidak ada cap — ~22k baris OK untuk
     IndexFlatL2).
   - LitTabR: in_dim=60, d=128, m=4, encoder_blocks=0, dropout=0.1, lr=3e-4,
     freeze_context_epoch=6, batch 128, max_epochs 50,
     EarlyStopping(monitor val_loss, patience 10), accelerator gpu.
   - Metrik fold: acc frame, acc subjek (mean prob ≥ 0,5), prob mean, n epoch
     terlatih, best val_loss. Simpan `fold_XXX/{metrics.json,DONE.json}`.
5. Setelah semua fold: agregat → accuracy subjek, baseline mayoritas, MCC,
   AUC (dari prob subjek), balanced accuracy, confusion; tulis `summary.md`.
6. Resume: fold dengan DONE.json dilewati; `--force` mengulang;
   `--folds 0 1 2` subset; `--seeds N` (default 1, seed = RANDOM_SEED + s).
7. Fix `src/TabR.py`: samakan nama param dengan hook
   (`freeze_context_epoch: int = 6`). Cari juga pemakaian lain nama lama.

## Required Design

- Bahasa Indonesia untuk log/dok, gaya mengikuti `scripts/run_loso.py`.
- Output root: `output/training/lit_tabr_perframe_{phases}_{tag}/`.
- Tidak menyentuh `run_pipeline_v3.sh`, `run_loso.py`, atau hasil lama.
- `num_workers=0` di DataLoader (mesin ini RAM-nya sesak; 8 worker × 56 fold
  berisiko — dan batch kecil jadi tidak butuh).
- Hapus print per-epoch dari hook freeze/rebuild context di `src/TabR.py`
  (56 fold × 50 epoch × 2 print = log banjir) — ganti `self.log` atau diam.

## Tests

- `.venv/bin/python scripts/run_loso_lit_tabr.py --help` jalan.
- `py_compile` semua berkas yang diubah/dibuat.
- Instansiasi `LitTabR(in_dim=60, freeze_context_epoch=6)` + 1 step manual
  training_step dengan context kecil buatan → tanpa AttributeError.

## Done Criteria

- [x] Runner ada dan `--help` jalan (`scripts/run_loso_lit_tabr.py`).
- [x] Bug `freeze_context_epo`: ternyata berkas aslinya SUDAH memakai
  `freeze_context_epo` (verifikasi hex dump; laporan awal salah karena stale
  replay di tool layer). Yang benar-benar diperbaiki: freeze sekarang melekat
  (guard `ctx_frozen` di `on_validation_epoch_start`) + context jadi buffer.
- [x] Assert anti-bocor ada di dalam loop fold (train/val/context diperiksa).
