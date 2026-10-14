# 05 — Protokol level subjek + interval kepercayaan

**Severity:** medium

## Current Problem

Label milik subjek, tapi satu subjek menyumbang 500–1400 baris frame. Tiap
fold LOSO menahan 1 subjek, jadi test set tiap fold hanya satu kelas dan
metrik level frame antar-fold hanya mengukur komposisi kelas di dalam subjek,
bukan kemampuan model. `summary.md` masih menampilkan tabel level frame
sebagai bagian hasil, yang mengundang salah tafsir.

Tidak ada interval kepercayaan: angka 55.36% dilaporkan tanpa ketidakpastian,
padahal N = 56 subjek dan akurasi = baseline mayoritas.

## Target

`summary.md`/`summary.csv` menjadikan level subjek sebagai satu-satunya
metrik performa, dilengkapi interval kepercayaan 95% untuk accuracy,
sensitivity, dan specificity. Level frame hanya dicatat sebagai diagnostik
komposisi, dengan label tegas bukan-performa.

## Required Design

- Tambah helper Wilson interval (proporsi binomial, aman untuk N kecil dan
  proporsi ekstrem) di `collect_loso_results.py`.
- `summary.md` bagian level subjek: tambah kolom `95% CI` untuk accuracy,
  sensitivity, specificity (dihitung pada prediksi pooled antar seed, bukan
  rata-rata CI antar seed).
- Bagian level frame diganti judul menjadi penanda diagnostik dan
  ditambahkan satu baris penjelasan bahwa angka itu tidak mengukur kemampuan
  model di protokol LOSO.
- Tetap laporkan baseline mayoritas berdampingan dengan accuracy.
- Tanpa dependensi baru (rumus Wilson manual, `math.sqrt`).

## Tests

- Parse AST dan jalankan `collect_loso_results.py --exp convat_apex_anxiety_loso_roi25`.
- Cek `summary.md`: ada kolom CI; tidak ada klaim performa di bagian level frame.
- Cek nilai CI masuk akal (batas bawah < titik estimasi < batas atas).

## Done Criteria

- [ ] Wilson CI dihitung dan ditampilkan.
- [ ] Level subjek = satu-satunya metrik performa.
- [ ] Level frame ditandai diagnostik.
- [ ] Baseline mayoritas selalu berdampingan dengan accuracy.
