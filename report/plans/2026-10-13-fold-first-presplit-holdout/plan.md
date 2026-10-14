# Plan — Fold-first pre-split + holdout evaluation

> **Status:** done (implementasi + verifikasi dry-run) — 2026-10-13. Menunggu user menjalankan pipeline.

- **Goal:** split train/val/test per orang terjadi SEBELUM spotting; evaluasi akhir pada 12 orang yang tidak pernah dibaca pipa.
- **Architecture:** pre-split (stage 0) → pipeline v3 biasa di train pool (44 orang) → stage 8 holdout eval (12 orang).
- **Tech Stack:** bash pipeline + Python (pandas), venv `.venv`.

## Must Not Forget

- Default run TANPA `V3_PRESPLIT=1` harus bit-identik dengan perilaku sekarang (filter kosong = no-op).
- Penamaan orang HARUS memakai `normalize_participant_key` (strip `_[0-9]+$`) — sama dengan `extract_features_poc_abs.py`.
- `--test-persons-file` di run_loso memakai mesin fold yang sama (imputer/scaler fit train only; val scan `has_both_labels`).
- Dataset name untuk holdout = `${LOSO_DATASET}_holdout` supaya tidak menimpa exp LOSO-44.
- Tidak menjalankan pipeline panjang / e2e — user yang menjalankan. Verifikasi kami = py_compile + dry-run.
- Jangan push/commit tanpa perintah.

## Issue Index

### Critical
- [01 — Pre-split script](issues/01-critical-presplit-script.md)
- [02 — Spotting include-filter](issues/02-critical-spotting-include-filter.md)

### High
- [03 — run_loso --test-persons-file](issues/03-high-loso-test-persons-file.md)
- [04 — Pipeline stage 0 + stage 8 + combine](issues/04-high-pipeline-stage0-stage8.md)

### Medium
- [05 — Docs: PROGRESS/HANDOFF + run commands (incl. roi25 A/B)](issues/05-medium-docs-run-commands.md)

## Target Architecture

Lihat CONTEXT.md → "Architecture Now".

## Priority Order

1. 01 → 02 (pre-split + filter adalah fondasi)
2. 03 → 04 (single-fold lalu wiring pipeline)
3. 05 (dokumentasi)

## Validation Commands

```bash
.venv/bin/python -m py_compile scripts/split_persons_presplit.py scripts/combine_feature_tables.py scripts/run_loso.py scripts/process_spotting_pipeline.py
.venv/bin/python scripts/split_persons_presplit.py --raw-root "/run/media/finny/New Volume/dataset/anxiety_raw" --out output/presplit --dry-run
V3_PRESPLIT=1 ./scripts/run_pipeline_v3.sh --dry-run
```

## Rollout Plan

- [x] Plan ditulis
- [x] 01 pre-split — dry-run: 56 orang, strata 24/18/14, holdout 12 (5+4+3), seed 42 deterministik
- [x] 02 include-filter — terverifikasi di tree nyata: 560 video = 440 train + 120 holdout, 0 tak dikenal
- [x] 03 single-fold — `--test-persons-file` di run_loso.py (fold_defs; mode lama bit-identik); py_compile + --help OK
- [x] 04 wiring stage 0/8 — `bash -n` OK; dry-run default = 7 stage tanpa presplit (bit-identik); dry-run V3_PRESPLIT=1 = stage 0-8 benar
- [x] 05 docs
- [x] Serah-temin: perintah run ke user

## Done Criteria

- [ ] `V3_PRESPLIT=1 ./scripts/run_pipeline_v3.sh --fresh` menjalankan: split → spotting 44 orang → LOSO 44 → holdout eval 12 orang, tanpa menyentuh video 12 orang sebelum stage 8 (terbukti di log stage 1: "INCLUDE_PERSONS: 440 video diproses, 120 dilewati"). **Menunggu run user.**
- [x] Default run tanpa V3_PRESPLIT tetap 7 stage, tanpa filter (dry-run bit-identik).
- [ ] Satu model final + metrik holdout tertulis di `output/training/${LOSO_DATASET}_holdout/`. **Menunggu run user.**
