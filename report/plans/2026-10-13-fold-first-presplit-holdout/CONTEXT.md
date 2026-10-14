# CONTEXT — Fold-first pre-split + holdout evaluation

## Problem

Khalid's directive: the train/val/test split must happen **at the start, before
spotting**, so the pipeline structurally cannot see a test person "in the
middle", plus retry the roi25_reg config.

Verified state of the current pipeline (`run_pipeline_v3.sh`):

- The LOSO split in `run_loso.py` is already person-disjoint (56 normalized
  persons) and imputer/scaler/balancing are fit on train only. Spotting and
  feature extraction are per-video/per-clip with per-person self-referential
  baselines (neutral.png, per-video mean+std thresholds). **No information
  flows from a test person's videos into training features today** — the
  protocol is already leak-free in the mathematical sense.
- What is missing is the *structural* guarantee: spotting runs once over all
  560 raw videos (all 56 persons) before any split exists, and all tuning
  decisions (config, descriptors) were chosen by looking at pooled 56-person
  LOSO results. That is protocol-level test peeking that an examiner can
  attack.

Expected metric movement from this change: ~none (there is no leak to fix).
The value is demonstrability ("11 orang tidak pernah dibaca sampai evaluasi
akhir") and one truly untouched holdout number.

## Fix

1. **Pre-split (new stage 0, optional)**: assign the 56 persons to train pool
   (44) vs holdout test (12) **stratified by label pair** (tinggi-both 24,
   changed 18, rendah-both 14 → 5+4+3), fixed seed, written to
   `output/presplit/{split.csv,train_persons.txt,test_persons.txt}` before
   anything else runs.
2. **Spotting include-filter**: `SPOT_INCLUDE_PERSONS=<file>` env in
   `process_spotting_pipeline.py` — persons not in the file are never read.
3. **Holdout eval (new stage 8, only when pre-split active)**: after the
   normal stages 1–7 finish on the 44-person train pool, run spotting +
   extraction + temporal features on the 12 holdout persons, combine with the
   train-pool feature table, and train ONE final model with
   `run_loso.py --test-persons-file` (single fold: test = 12 holdout persons,
   val/train = the 44 pool persons). That fold's checkpoint is the final,
   deliverable model.
4. roi25 A/B is already supported via
   `--config experiments/configs/tabr_loso_roi25_reg.toml`; document it.

## Architecture Now

```
                    output/presplit/split.csv  (seed-fixed, stratified)
                     |                          \
        44 train persons                    12 holdout persons
             |                                   (tidak disentuh)
   stage 1 spotting (include-filter)               |
   stage 2-7: fitur -> gate -> LOSO 44 fold        |
             |                                     |
             +-------------> stage 8 <-------------+
                    spotting 12 orang (resep sama,
                    tanpa fit apapun) -> fitur ->
                    combine -> 1 fold final
                    (test=12, val/train=44) ->
                    model final + satu angka jujur
```

## Key Files

- `scripts/split_persons_presplit.py` — NEW: tahap 0.
- `scripts/process_spotting_pipeline.py` — env `SPOT_INCLUDE_PERSONS`.
- `scripts/run_loso.py` — arg `--test-persons-file` (single-fold mode).
- `scripts/combine_feature_tables.py` — NEW: gabung 2 pkl fitur temporal.
- `scripts/run_pipeline_v3.sh` — stage 0 + stage 8 di mode `V3_PRESPLIT=1`.

## Important Behavior Changes

- Default run (tanpa `V3_PRESPLIT=1`) TIDAK berubah: `SPOT_INCLUDE_PERSONS`
  kosong = semua video diproses seperti sekarang.
- Dengan `V3_PRESPLIT=1`: LOSO berjalan atas 44 orang (bukan 56), dan ada
  stage 8 evaluasi holdout 12 orang.

## Tests

- Tidak ada test baru (kontrak: no tests kecuali diminta). Verifikasi =
  py_compile + `--dry-run` + cek filter pada listing kering.

## Known Notes

- 12 orang test = 24 sesi → satu angka dengan CI lebar. Itu memang realitas
  N kecil; LOSO-44 tetap dipakai untuk tuning dan pelaporan kedua.
- Re-spotting per fold (versi tanpa-kontak paling ketat) tidak feasibel:
  ~50 menit x 56 fold ≈ 47 jam. Pre-split level dataset dipilih.
