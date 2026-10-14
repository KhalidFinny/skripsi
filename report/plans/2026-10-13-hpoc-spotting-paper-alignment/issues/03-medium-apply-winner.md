# 03 — Kunci pemenang sebagai default pipeline (bila tervalidasi)

**Severity:** medium
**Status:** selesai (2026-10-13)

## Hasil

Mengikuti preseden SPOT_CUTOFF (pemenang CAS(ME)² dibuka sebagai OPSI, default
tidak diubah sampai uji A/B sisi anxiety):

- `SPOT_SIGNAL=mean_m|hpoc|combo` di `process_spotting_pipeline.py` —
  mean_m default, terverifikasi bit-identik dengan perilaku lama (max|diff|=0,0
  pada 1 video vs cache lama). hpoc/combo menghitung komponen (mean_m,
  hpoc_drop_mean) dari array POC yang sama (tidak ada POC tambahan).
- combo diterapkan di level global (tervalidasi) untuk mode global_mean, dan
  per-ROI (varian lebih lemah, terdokumentasi) untuk mode roi_signals.
- `run_pipeline_v3.sh` meneruskan `V3_SPOT_SIGNAL`.
- Uji A/B user: `V3_SPOT_SIGNAL=combo ./scripts/run_pipeline_v3.sh --fresh`.

## Masalah

Bila isu 01 menemukan sinyal/konfigurasi yang mengalahkan mean_m b9abs secara
stabil di validasi A/B, pipeline spotting harus bisa memakainya TANPA mengubah
perilaku default yang lama (pola env seperti SPOT_CUTOFF / SPOT_ABS).

## Yang dikerjakan (hanya bila ada pemenang)

1. Tambah plumbing env di `scripts/process_spotting_pipeline.py`, mis.
   `SPOT_SIGNAL=mean_m|hpoc_drop_mean|hpoc_drop_mov` dan `SPOT_BLOCK=9|5`,
   default = perilaku sekarang. Sinyal Hpoc perlu nilai puncak per blok —
   ubah `compute_roi_magnitudes` untuk menghitung dari array POC langsung
   (pola `block_stats` di audit_hpoc_casme2.py).
2. Propagasi env di `scripts/run_pipeline_v3.sh` (pola V3_SPOT_CUTOFF).
3. Perbarui `report/findings/koreksi-final-pdf.md` (definisi M, block size,
   acuan) dan `report/findings/magnitude-deepdive.md` (bagian verdict baru).
4. Update PROGRESS.md + HANDOFF.md + status plan.

## Kriteria selesai

- Default pipeline tidak berubah tanpa env; dengan env, sinyal pemenang dipakai.
- Tidak ada angka performa anxiety yang diklaim sebelum user menjalankan ulang
  pipeline penuh.
