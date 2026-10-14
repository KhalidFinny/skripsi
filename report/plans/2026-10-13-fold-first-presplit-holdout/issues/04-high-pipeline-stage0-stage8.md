# 04 — Pipeline stage 0 + stage 8 + combine (high)

## Current Problem

`run_pipeline_v3.sh` mulai langsung di spotting tanpa artefak split, dan
berhenti di collect LOSO. Tidak ada evaluasi holdout.

## Target

Mode opt-in `V3_PRESPLIT=1` (default: perilaku lama persis):

- **Stage 0 (baru, hanya mode presplit)**: jalankan
  `split_persons_presplit.py` → `output/presplit/` (skip kalau sudah ada,
  kecuali `--force`/`--fresh`).
- **Stage 1**: export `SPOT_INCLUDE_PERSONS=output/presplit/train_persons.txt`.
  Banner menyebut "44 orang train pool; 12 orang TIDAK dibaca".
- **Stage 8 (baru, hanya mode presplit, setelah stage 7)**:
  1. Spotting holdout: `SPOT_INCLUDE_PERSONS=test_persons.txt`,
     `SPOT_OUTPUT_ROOT=$OUT_ROOT_HOLDOUT` (default `output/apex_v2_holdout`),
     flag SPOT_* sama dengan stage 1 (resep identik, tanpa fit apapun).
  2. Ekstraksi fitur holdout → `${FEAT_TAG}_holdout.xlsx` (+ pkl cache).
  3. Temporal → `${FEAT_TAG}_holdout_poc_temporal${DESC_SUFFIX}.pkl`.
  4. `scripts/combine_feature_tables.py` (BARU): gabung pkl temporal train
     pool + holdout → `${FEAT_TAG}_combined${DESC_SUFFIX}.pkl`.
     Validasi: kolom identik (set + urutan), index di-reset, meta kolom sama.
  5. `run_loso.py --dataset ${LOSO_DATASET}_holdout --features combined.pkl
     --test-persons-file test_persons.txt` + argumen training yang sama
     dengan stage 6 (config/seeds/aggregate/label-unit/drop-features).
  6. `collect_loso_results.py --exp ${LOSO_DATASET}_holdout --features
     combined.pkl --row-unit subject`.
- `TOTAL_STAGES` jadi 8 pada mode presplit; `--stage/--from` tetap bekerja
  (stage 8 hanya ada di mode presplit).
- FRESH guard stage 1 berlaku juga untuk `$OUT_ROOT_HOLDOUT` (jangan hapus
  klip kalau driv mentah tidak ada).

## Required Design

- Env override: `V3_PRESPLIT_DIR` (default `output/presplit`),
  `V3_HOLDOUT_OUT_ROOT`, `V3_TEST_PEOPLE` (default 12), `V3_PRESPLIT_SEED`
  (default 42).
- Stage 8 TIDAK berjalan bila `V3_PRESPLIT` tidak diset.
- Log stage 8 menegaskan: "12 orang ini pertama kali dibaca SEKARANG".

## Tests

- `V3_PRESPLIT=1 ./scripts/run_pipeline_v3.sh --dry-run` mencetak rencana
  stage 0–8.
- `./scripts/run_pipeline_v3.sh --dry-run` (tanpa env) tetap 7 stage, tanpa
  menyebut presplit.

## Done Criteria

- [ ] Dry-run kedua mode benar
- [ ] combine_feature_tables py_compile + validasi kolom
- [ ] Dokumentasi pemakaian di header script
