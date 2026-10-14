# 02 — Smoke 3 fold: mekanik + anti-bocor

**Severity:** critical

## Current Problem

Runner baru (issue 01) belum terbukti: split benar, tidak ada kebocoran,
context FAISS terbentuk, freeze jalan, metrik masuk akal, resume bekerja.

## Target

Jalankan 3 fold pertama (`--folds 0 1 2 --tag smoke`) dan verifikasi:

1. Assert anti-bocor lolos di ketiga fold (participant test tidak muncul di
   train/val/context).
2. Context size > 0 dan seimbang per label; FAISS terbentuk.
3. Training benar-benar berjalan: epoch > 0, train_loss turun dari awal,
   val_loss tercatat; freeze terjadi di epoch 6 (cek log/checkpoint).
4. `metrics.json` per fold berisi keempat metrik; prob subjek dalam [0,1].
5. Resume: jalankan ulang perintah yang sama → 3 fold dilewati (DONE).
6. Waktu per fold tercatat → estimasi honest untuk full run (issue 03).
   Kalau > 5 menit/fold, turunkan max_epochs atau pakai subset frame per
   subjek dan CATAT keputusannya.

## Required Design

- Tag `smoke` → output terpisah, boleh dihapus setelah hijau.
- Tidak ada perubahan desain di tahap ini; kalau ada bug, kembali ke issue 01.

## Tests

Perintah: `.venv/bin/python scripts/run_loso_lit_tabr.py --folds 0 1 2 --tag smoke`

## Done Criteria

- [x] 3 fold selesai tanpa error: anti-bocor lolos, ctx ~17-19k seimbang,
  epoch 12 (freeze@6 tercapai), metrics.json lengkap, prob dalam [0,1].
- [x] Resume teruji (3 fold `lewati (DONE)`); collect menghasilkan summary.md.
- [x] Estimasi waktu: ~65-75 detik/fold (GTX 1650 Ti) → full ~70 menit;
  tercatat di PROGRESS.md.
