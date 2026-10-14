# CONTEXT — Spotting Magnitude Deep Dive

## Problem

Semua perbaikan model (official/custom TabR, fitur rise, agregasi, LOSO jujur)
mentok di 41–54% vs baseline mayoritas 57,14%. Sinyal hulu (spotting) adalah
tuas yang belum pernah di-deep-dive definisinya: magnitude per blok POC-ABS
dikuantisasi kasar (pergeseran integer, rentang 0..~5,66 untuk block 9), lalu
di-**mean** ke seluruh blok ROI — padahal micro-expression hanya menggerakkan
beberapa blok. Mean atas mayoritas blok diam = sinyal ekspresi terdilusi noise.

Audit sebelumnya (report/findings/audit-spotting-casme2.md) menguji max_m /
motion_count **dengan resep deteksi LAMA** (window tetap 7, ranking nilai) —
mean_m menang di sana, tapi belum pernah diuji ulang dengan resep deteksi BARU
(3% adaptif + prominence ranking). `cutoff_ratio` 0,3→0,5 sudah terbukti
menaikkan F1 ketat (0,149→0,179) tapi BELUM diterapkan. Pecipta POC-ABS
(Rosiani 2020) melaporkan POC-ABS mengungguli optical flow — jadi plafon
metode belum tercapai; yang salah kemungkinan besar definisi/agregasi
magnitude-nya, bukan POC-nya.

## Fix

1. Karakterisasi magnitude per blok di CAS(ME)²: kuantisasi, saturasi ±4px
   (mode ABS), dilusi mean (fraksi blok bergerak saat GT ekspresi vs baseline).
2. Sweep definisi sinyal (mean / max / top-k% / count / tertimbang) ×
   cutoff_ratio (0,3 / 0,5) dengan resep deteksi BARU, dipilih di paruh subjek A,
   divalidasi di paruh B.
3. Kunci pemenang sebagai default pipeline; dokumentasikan.
4. Koreksi FINAL.pdf: block 7→9, 3→5 ROI, parameter deteksi yang drift
   (doc: distance 5/prominence 0.5; kode: distance 1/prominence rel 0,04),
   protokol split lama (GroupShuffleSplit 33/11/12 + ensemble) → LOSO 56-fold,
   angka 75,79%/58% (leaky) → 54,46% LOSO (jujur).

## Architecture Now

```
video → dlib 68 landmark → 5 ROI → POC-ABS 9×9 vs frame-0
      → magnitude per blok (integer, 0..5,66)
      → AGREGASI (di-sweep) → sinyal global
      → savgol 3% adaptif → prominence ranking, height=mean+std
      → find_phase cutoff_ratio (di-sweep) → event
```

## Key Files

- `features_extraction/poc.py`, `vektor.py`, `quadran.py` — sumber magnitude per blok
- `apex/apex_smoother.py`, `apex/apex_phase.py` — deteksi (resep baru sudah di sini)
- `scripts/process_spotting_pipeline.py` — pipeline spotting (SPOT_* env)
- `scripts/eval_spotting_casme2.py` — benchmark ground truth CAS(ME)²
- `output/training/casme2_rich_signals/*.npz` — cache 86 video: mean_m, max_m,
  motion_count, mean_x, mean_y, angle_R per ROI
- `output/training/spotting_casme2_signals/*.npz` — cache mean_m per ROI

## Important Behavior Changes

Default spotting (agregasi/cutoff) akan berubah sesuai pemenang sweep → semua
klip event + tabel fitur harus diregenerasi oleh user setelah default dikunci.

## Tests

Tidak ada (kontrak: test hanya atas permintaan). Validasi = F1 CAS(ME)² dengan
protokol split subjek A/B seperti audit sebelumnya.

## Validation Done

(belum — diisi saat eksekusi)

## Known Notes

- Leak check: split LOSO per subjek terjadi sebelum preprocessing di kedua
  runner (run_loso.py:654-662, run_loso_lit_tabr.py:141-145). subject_standardize
  memakai statistik subjek itu sendiri (tanpa label) — bukan kebocoran label,
  dan bukan default.
- Sweep agregasi terbatas pada sinyal yang ada di cache kaya; definisi baru
  (top-k%, tertimbang korelasi) butuh re-hitung POC untuk sampel video —
  dilakukan di isu 01 sebagai bukti konsep sebelum sweep penuh.
