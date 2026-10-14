# 05 — Probe sub-piksel POC + skala ROI + kegagalan landmark

**Severity:** high

## Current Problem

Temuan isu 01: bottleneck sinyal = kuantisasi integer (15 nilai diskret) dan
bukan agregasi. Tapi kuantisasi itu bukan batas metode — lokasi puncak korelasi
POC bisa diestimasi sub-piksel dengan interpolasi parabolik 3 titik di sekitar
puncak (standar pada literatur phase correlation), mengubah magnitude dari 15
nilai diskret menjadi kontinu. Belum pernah dicoba.

Dua masalah mekanisme lain yang belum diukur:
- **Skala ROI**: crop wajah di-resize ke ukuran tetap (mis. 48×32). Magnitude
  diukur dalam piksel hasil resize, jadi wajah yang menjauh/dekat kamera
  mengubah skala gerakan tanpa ada gerakan otot — noise struktural.
- **Kegagalan landmark**: frame tanpa deteksi dlib diisi interpolasi linier.
  Belum diketahui berapa % frame gagal dan di mana jatuhnya (kalau di sekitar
  apex, puncak bisa cacat).

## Target

Skrip `scripts/probe_spotting_mechanism_casme2.py` (10 video yang sama dengan
isu 01, POC dihitung langsung):

1. Sinyal sub-piksel: offset puncak = integer + koreksi parabolik pada sumbu x
   dan y dari matriks korelasi POC 9×9 (guard: puncak di tepi atau denominator
   ~0 → pakai integer).
2. Sinyal skala-dikoreksi: magnitude dikali (lebar_crop / lebar_target) per ROI
   per frame, mengubah ke satuan piksel citra asli.
3. Laporan: fraksi frame gagal landmark (ref frame-0 dan current), distribusi
   per video; apakah frame gagal jatuh dalam rentang GT ekspresi.

Metrik sama dengan isu 01 (peringkat puncak ekspresi, prominence ranking):
integer vs sub-piksel vs sub-piksel+skala.

## Required Design

- Tidak mengubah `features_extraction/` (POC/Vektor/Quadran produksi); sub-piksel
  dihitung dari output `poc.getPOC()` di dalam skrip probe.
- Sampel video dan metrik identik dengan `diag_magnitude_casme2.py` supaya
  perbandingan apple-to-apple (mean integer = 0,146 di sampel ini).

## Tests

Tidak ada (kontrak). Sanity check: pada gerakan sintetis sub-piksel (< 1 px),
sinyal sub-piksel harus menunjukkan nilai > 0 sedangkan integer tetap 0.

## Done Criteria

- [x] Tabel peringkat: integer 0,146 / sub-piksel 0,150 / sub-piksel+skala 0,150
  (sub-piksel bekerja di sintetis tapi TIDAK mengubah peringkat di video nyata)
- [x] Angka kegagalan landmark: 0,0% dari 24.709 frame — bukan masalah di CAS(ME)²
- [x] Kesimpulan di `report/findings/magnitude-deepdive.md` §6: tidak layak lanjut
  ke produksi; faktor pembatas = SNR gerakan latar, bukan resolusi numerik
