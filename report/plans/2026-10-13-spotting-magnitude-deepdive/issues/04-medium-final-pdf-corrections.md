# 04 — Koreksi FINAL.pdf

**Severity:** medium

## Current Problem

FINAL.pdf (draf skripsi BAB I-VII) menyimpang dari kode pada beberapa angka dan
protokol. Kalau dibiarkan, penguji bisa menemukan inkonsistensi antara tulisan
dan implementasi. Penyimpangan yang teridentifikasi:

| Bagian FINAL.pdf | Tertulis | Kode/fakta |
|---|---|---|
| Abstrak + BAB II/III | block size 7×7 | `BLOCK_SIZE = 9` (roi_config.py; alasan saturasi terdokumentasi) |
| BAB III | 3 ROI (mata-alis gabungan, 48×32) | 5 ROI, alis terpisah (64×24) — alis ⊂ mata terbukti redundan |
| BAB V (deteksi event) | distance 5, prominence 0.5 | distance 1, prominence relatif 0,04 × rentang sinyal; smoothing 3% adaptif; ranking prominence; threshold mean+1σ (ini cocok) |
| BAB V (protokol pengujian) | GroupShuffleSplit 33/11/12 + tune.py 15 seed + ensemble 5 model | LOSO 56 fold, split SEBELUM preprocessing, imputer/scaler fit di train saja |
| BAB VI (angka) | train 0,9904 / val Q4 0,7592 / test Q5 0,7579 / datatest 0,58 | angka itu dari split frame-level (leaky); hasil jujur LOSO: test 54,46% (AUC 0,5204), gate within-subject BA 0,75 p=0,01 |
| BAB VI Tabel 6.10 | contoh threshold/magnitude 2 video | perlu diperbarui mengikuti sinyal pemenang isu 02 |

## Target

`report/findings/koreksi-final-pdf.md`: daftar koreksi per bagian/halaman,
format "lama → baru" + teks pengganti siap tempel (bahasa Indonesia), supaya
user tinggal menerapkannya di sumber dokumen (Word/Google Docs). Termasuk
narasi pengganti untuk BAB V protokol pengujian (LOSO) dan BAB VI pembahasan
(angka jujur + gate within-subject sebagai hasil signifikan).

## Required Design

- Tidak mengedit PDF; sumber dokumen tidak ada di repo.
- Angka baru mengikuti hasil isu 02 bila default berubah; kalau tidak, pakai
  angka LOSO yang sudah ada (54,46%).
- Nada penulisan: jujur (user memilih jujur 50-60% daripada angka leaky).

## Tests

Tidak ada.

## Done Criteria

- [x] Semua baris tabel di atas punya teks pengganti
- [x] File dapat diserahkan ke user tanpa konteks tambahan
  → `report/findings/koreksi-final-pdf.md`
