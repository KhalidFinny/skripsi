# Hpoc & Penjajaran Paper POC-ABS — plan

> **Status:** selesai, 2026-10-13. Kesimpulan: Hpoc (fitur M paper yang dibuang
> kode kita) membawa informasi komplementer — combo global z(mean_m)+z(hpoc)
> F1 0,3343 vs baseline 0,3192, terpilih di kedua fold validasi subjek. Resep
> persis paper (seq/eksklusi/block5) gagal di 30 fps. `SPOT_SIGNAL` dibuka
> (default tak berubah); uji A/B sisi anxiety = langkah berikutnya (user).

- **Goal:** uji apakah sinyal berbasis Hpoc (nilai puncak POC — fitur M yang
  sebenarnya di paper Rosiani et al. 2020, yang selama ini dibuang kode kita)
  mengalahkan sinyal magnitude perpindahan untuk spotting, pada 4 konfigurasi
  (block 9/5 × acuan frame-0/berurutan), tervalidasi jujur A/B split subjek di
  CAS(ME)²; lalu kunci pemenang sebagai default pipeline + perbaiki penyimpangan
  FINAL.pdf bagian spotting.
- **Architecture:** video → ROI (dlib 68) → POC per blok → (posisi puncak,
  NILAI puncak) per blok → sinyal kandidat → deteksi apex/fase → evaluasi F1.
- **Tech Stack:** cache npz CAS(ME)² (`output/training/casme2_hpoc_signals`),
  resep deteksi baku dari audit_mag_agg_casme2.py.

## Must Not Forget

- Pemilihan konfigurasi spotting HANYA di CAS(ME)² — TIDAK menyentuh label/data
  uji anxiety (leak). Validasi = split subjek 2-fold (pilih di train, ukur di test).
- Resep deteksi untuk perbandingan sinyal DIPAKU sama dengan
  `audit_mag_agg_casme2.py` (savgol 3% adaptif, prominence rel 0,04,
  height=mean+std, top_k=5, ranking prominence, cutoff 0,3/0,5) supaya
  apple-to-apple dengan baseline mean_m F1 0,3192.
- Split LOSO per subjek terjadi SEBELUM preprocessing di runner LOSO — jangan dirusak.
- User yang menjalankan ulang pipeline anxiety penuh. Kita hanya menyiapkan
  default + temuan + (bila menang) plumbing env sinyal.
- Tidak menjalankan test/e2e pipeline anxiety tanpa diminta user.
- Update PROGRESS.md + HANDOFF.md di akhir.

## Issue Index

### high
- [01-hpoc-signal-audit](issues/01-high-hpoc-signal-audit.md) — bangun cache
  sinyal Hpoc (4 konfigurasi × 4 sinyal) + evaluasi F1 A/B vs baseline mean_m.

### medium
- [02-final-pdf-spotting-drift](issues/02-medium-final-pdf-spotting-drift.md) —
  tambahan koreksi FINAL.pdf: acuan frame-0 vs berurutan, smoother 5%→3%,
  float64→int, daftar ROI/blok usang, definisi M (menunggu hasil 01).
- [03-apply-winner](issues/03-medium-apply-winner.md) — bila ada pemenang
  tervalidasi: plumbing env sinyal ke pipeline + update koreksi + PROGRESS/HANDOFF.

## Target Architecture

```
POC per blok → per blok: (moved?, |V|, Hpoc)
   → sinyal kandidat per ROI: mean_m / frac_mov / hpoc_drop_mean / hpoc_drop_mov
   → mean antar ROI → resep deteksi baku → F1 + A/B split subjek
   → pemenang (bila ada) jadi default via env, tanpa mengubah perilaku lama
```
