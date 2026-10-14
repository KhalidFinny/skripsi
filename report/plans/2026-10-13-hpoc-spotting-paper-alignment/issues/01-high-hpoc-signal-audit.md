# 01 — Audit sinyal Hpoc (fitur M paper yang dibuang)

**Severity:** high
**Status:** selesai (2026-10-13)

## Masalah

Kode kita menghitung nilai puncak POC per blok (`val_max` di
`features_extraction/vektor.py:37`) lalu membuangnya — hanya posisi puncak
yang dipakai. Padahal di paper Rosiani et al. (2020), fitur **M justru adalah
nilai puncak itu (Hpoc)**, bukan |V| (bukti: contoh MB28=0,46 dengan XB=2,
YB=2). Untuk data 30 fps, displacement terkuantisasi ke integer piksel
(bottleneck SNR yang sudah terukur), sedangkan Hpoc kontinu di (0,1] —
berpotensi membawa sinyal sub-piksel yang hilang.

## Yang dikerjakan

1. Skrip `scripts/audit_hpoc_casme2.py` (build + eval):
   - 4 konfigurasi: b9abs (block 9, frame-0 = pipeline), b5abs (block 5 paper,
     frame-0), b9seq (block 9, berurutan paper), b5seq (persis paper).
   - 4 sinyal per ROI: mean_m (baseline), frac_mov (Pvector paper),
     hpoc_drop_mean = mean(1−Hpoc) semua blok, hpoc_drop_mov = mean(1−Hpoc)
     blok bergerak saja (aturan eksklusi paper).
   - Magnitude dihitung langsung dari array POC (setara Vektor+Quadran,
     aturan ambiguitas sama — diverifikasi via rep_x/rep_y).
2. Build cache `output/training/casme2_hpoc_signals` untuk 86 video GT.
   Uji 2 video: sinyal sehat (tanpa NaN, kontinu, tidak konstan); ~0,078 s/frame
   per worker untuk 4 konfigurasi.
3. Eval: F1 gabungan + F1 ketat (IoU≥0,5) + validasi split subjek 2-fold,
   resep deteksi DIPAKU sama dengan audit_mag_agg_casme2.py.
   Baseline pembanding: mean_m F1 0,3192 / ketat ~0,14 (audit 2026-10-09/13).

## Hasil (2026-10-13)

- Tabel lengkap 16 kandidat × 2 cutoff: `output/training/audit_hpoc_casme2/README.md`.
- Pemenang: **combo global z(mean_m)+z(hpoc_drop_mean) F1 0,3343** vs baseline
  0,3192; A→B pilih combo (test 0,3262), B→A pilih hpoc b5 (test 0,3198) —
  kedua fold memilih keluarga Hpoc. Resep persis paper (seq, eksklusi blok
  diam) gagal; block 5 tidak diperlukan.
- Verdict lengkap: `report/findings/magnitude-deepdive.md` §7.
