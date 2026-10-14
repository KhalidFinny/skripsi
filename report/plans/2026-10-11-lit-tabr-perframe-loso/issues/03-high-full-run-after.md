# 03 — Full run after-only 56 fold × 1 seed

**Severity:** high

## Current Problem

Angka bersih untuk metode asli belum ada. Headline saat ini (jalur agregat):
test 47,62% vs baseline 55,36%, MCC −0,1037, AUC 0,3978.

## Target

Jalankan LOSO penuh: `--tag after_s1 --seeds 1` (56 fold, fase `after`,
27.936 baris frame). Hasil:

- accuracy level subjek vs baseline mayoritas 55,36%
- MCC, AUC, balanced accuracy, confusion matrix gabungan
- kurva ringkas: rata-rata epoch terlatih, berapa fold early-stop < epoch 10
  (deteksi "model tidak belajar" seperti diagnosis 4.54)
- perbandingan berdampingan: 47,62% (agregat) vs hasil ini vs 74% bocor
  (dicatat sebagai TIDAK SAH, hanya konteks sejarah)

Laporkan apa adanya. Kalau di bawah baseline: itu jawaban bersih untuk metode
asli pada fase after — lanjut analisis singkat (distribusi prob, fold outlier),
bukan menambah fitur. Kalau di atas: issue 04 jadi prioritas untuk konfirmasi
3 seed.

## Required Design

- Jalan di background dengan log (`logs/lit_tabr_after_s1_*.log`), pola
  `setsid` seperti run pipeline sebelumnya (mesin pernah ganti executor di
  tengah jalan; resume per fold sudah ada).
- Tidak mengubah runner selama run berjalan.

## Tests

Ringkasan akhir dari `summary.md` yang dihasilkan runner + cek DONE 56/56.

## Done Criteria

- [ ] 56/56 fold DONE, summary.md lengkap.
- [ ] Angka dilaporkan ke user dengan perbandingan jujur.
