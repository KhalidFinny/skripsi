# Konteks — Hpoc & penjajaran paper POC-ABS (Rosiani et al. 2020)

Permintaan user (2026-10-13, lanjutan): "spotting dan apeks more deep dive more —
lihat Bu Ullas Rosiani's paper, she said it can be more than optical flow where it
had its own magnitude for the spotting. We need the most optimized magnitude OR
ANY OTHER config or method of spotting. Find more of them. She said there is many
spotting methods and how to find the apeks. Don't focus on POC or TabR (pakai TabR
resmi). Focus ONLY on the spotting, and see the problems from the skripsi
(FINAL.pdf) where we can fix some stuff."

## Sumber kunci

- Paper: Rosiani, U.D., Choirina, P., Muna, N., Mulyanto, E., Sumpeno, S.,
  Purnomo, M.H. (2020). "A Novel Approach on Motion Estimation for
  Micro-Expression Recognition Using Phase Only Correlation with All Block Search
  (POC-ABS)". IJIES 13(6), 545-559. DOI 10.22266/ijies2020.1231.48. Teks lengkap
  sudah dibaca.
- Temuan sebelumnya (plan 2026-10-13-spotting-magnitude-deepdive): bottleneck
  spotting = SNR sinyal POC integer pada data 30 fps (15 nilai diskrit, 57,8%
  blok statis); mean_m agregasi terbaik (F1 0,3192); baseline frame-0 menang.

## Divergensi paper vs implementasi kita (hasil baca penuh)

1. **M paper = nilai puncak POC (Hpoc), BUKAN |V| = sqrt(X²+Y²).** Bukti di
   paper: contoh blok 28 dengan XB=2, YB=2 punya MB28 = 0,46 — nilai itu sama
   dengan "highest POC value 0,4687" yang ditampilkan, bukan 2,83. Kode kita
   (`features_extraction/vektor.py:37`) menghitung `val_max` lalu membuangnya.
2. **Acuan paper = frame berurutan** (img(f) vs img(f±1), Algoritma 1 baris 4).
   Kita pakai frame-0 (menang audit pada 30 fps karena displacement terkuantisasi).
   Hpoc tidak terkuantisasi → acuan berurutan layak diuji ulang untuk sinyal Hpoc.
3. **Block size terbaik paper = 5×5** (disapu 5–25; KNN 95,6% / SVM 94,3% di
   CASME II 200 fps). Kita pakai 9 (dipilih untuk saturasi displacement).
4. **Blok tanpa gerak DIKECUALIKAN dari fitur** ("matching results from blocks
   which have no motion are not used"). Kita memakai semua blok dalam mean.
5. **Pvector (Eq. 6) = rasio blok bergerak per ROI** — ada di kita sebagai
   frac_mov/motion_count (lemah sebagai sinyal tunggal, tapi itu di block 9 abs).
6. Apex paper: jumlah panah MV naik onset→apex lalu turun (apex = puncak jumlah
   MV) — sejalan dengan deteksi puncak kita.
7. Angka 94,3%/95,6% paper = klasifikasi frame-level 10-fold CV di CASME II,
   BUKAN LOSO dan bukan spotting F1 — tidak sebanding dengan angka kita.

Catatan metode spotting lain yang disebut paper (untuk konteks BAB II):
MDMD (Wang et al. 2017), spatio-temporal strain (Shreve), facial strain
(Liong 2016), FHOFO (Happy & Routray), BMA SAD+OF (Muna 2017, 85,07%).
