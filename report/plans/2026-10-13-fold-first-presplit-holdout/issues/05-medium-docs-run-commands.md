# 05 — Docs + run commands (medium)

## Current Problem

PROGRESS.md / HANDOFF.md belum memuat desain fold-first; user butuh perintah
final untuk dijalankan sendiri (kontrak: user yang menjalankan pipeline
panjang).

## Target

- PROGRESS.md: entri "2026-10-13 (fold-first)" — desain, alasan (jaminan
  struktural, BUKAN perbaikan bocor: tidak ada bocor yang ditemukan), dan
  hasil setelah user menjalankan (placeholder "menunggu run").
- HANDOFF.md: cara menjalankan mode presplit + membaca hasil.
- Pesan final ke user berisi perintah:

```bash
# run utama fold-first (config compact default)
V3_PRESPLIT=1 ./scripts/run_pipeline_v3.sh --fresh

# A/B roi25_reg (kapasitas besar) — SETELAH run pertama selesai
V3_PRESPLIT=1 V3_FEAT_TAG=poc_abs_roi_signals_v3_roi25 \
  LOSO_DATASET=convat_apex_anxiety_loso_roi25_reg_roi25run \
  ./scripts/run_pipeline_v3.sh --config experiments/configs/tabr_loso_roi25_reg.toml
```

(Catatan: A/B roi25 hanya butuh stage 6-8 ulang — stage 1-5 identik karena
fitur sama; dokumentasikan `--from 6` + dataset name berbeda supaya fold
lama tidak tertimpa.)

## Done Criteria

- [ ] PROGRESS.md + HANDOFF.md ter-update
- [ ] Perintah final jelas, termasuk cara membaca summary holdout
