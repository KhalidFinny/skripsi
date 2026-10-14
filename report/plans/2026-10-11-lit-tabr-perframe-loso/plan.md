# Plan — Kembali ke Pipeline Asli: LitTabR Per-Frame dengan LOSO Bersih

> **Status:** Direncanakan — 2026-10-11.

## Goal

Mengevaluasi dan memperbaiki metode ASLI proposal (BAB III skripsinew):
fitur POC-ABS per-frame → flatten → TabR kustom (`src/TabR.py`, Lightning +
FAISS + context freezing), dengan protokol LOSO 56 fold yang bersih, menggantikan
jalur resmi-TabR di atas fitur agregat subjek yang gagal (test 47,62% vs
baseline 55,36%, overfit 168/168 fold-seed).

## Architecture

```
poc_abs_run2_full.pkl (63.413 baris frame, 60 fitur, 5 ROI)
   └─ per fold (56, subjek-disjoint):
        train = frame semua subjek lain (~27k baris, after-only)
        val   = 20% subjek train (disjoint) → early stopping jujur
        test  = frame subjek holdout
        preprocess: SimpleImputer(mean)+StandardScaler fit di train
        context FAISS: train saja, diseimbangkan per label
        model: LitTabR d=128 m=4 freeze@6, batch 128, lr 3e-4, ≤50 epoch,
               EarlyStopping(val_loss, patience 10)
        keputusan subjek = mean prob frame ≥ 0,5
```

## Tech Stack

Python 3.12 (.venv), pytorch_lightning 2.6, faiss, torch cu128 (GTX 1650 Ti).

## Must Not Forget

- **POC-ABS + TabR wajib** (constraint dosen) — yang diubah rezim data dan
  modelnya, bukan metodenya.
- **Jangan** menimpa hasil lama: output ke `output/training/lit_tabr_perframe_*`.
- **Tidak ada kebocoran**: subjek test keluar dari train, val, DAN context
  FAISS (proposal: "data uji … tidak dilibatkan dalam proses pelatihan maupun
  pembentukan context").
- Dokumen dan komentar kode dalam Bahasa Indonesia (konvensi repo).
- `src/TabR.py` punya bug laten: param `freeze_context_epo` vs
  `hparams.freeze_context_epoch` → AttributeError di epoch 0. Wajib diperbaiki.
- Jangan commit/push; jangan jalankan test/e2e di luar perintah user.

## Issue Index

**Critical**
- [01 — Runner LOSO LitTabR per-frame](issues/01-critical-lit-tabr-loso-runner.md)
- [02 — Smoke 3 fold: mekanik + anti-bocor](issues/02-critical-smoke-3-fold.md)

**High**
- [03 — Full run after-only 56 fold × 1 seed](issues/03-high-full-run-after.md)

**Medium**
- [04 — 3 seed + varian both-sessions + dokumen](issues/04-medium-seeds-variants-docs.md)

## Priority Order

01 → 02 → 03 → 04. Setiap issue harus hijau sebelum lanjut.

## Validation Commands

```bash
.venv/bin/python scripts/run_loso_lit_tabr.py --help
.venv/bin/python scripts/run_loso_lit_tabr.py --folds 0 1 2 --tag smoke
.venv/bin/python scripts/run_loso_lit_tabr.py --tag after_s1 --seeds 1
```

## Done Criteria

- [ ] Runner LOSO LitTabR jalan, resume per fold, metrik per fold tersimpan.
- [ ] Smoke 3 fold: nol kebocoran (subjek test tidak ada di train/val/context).
- [ ] Hasil full 56 fold: accuracy subjek vs baseline mayoritas 55,36%,
      MCC, AUC, BA — dilaporkan apa adanya, dibandingkan dengan 47,62% (jalur
      agregat) dan 74% bocor (notebook asli, tidak boleh diklaim).
- [ ] PROGRESS.md + HANDOFF.md diperbarui.
