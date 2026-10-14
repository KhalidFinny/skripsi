# 02 — Normalisasi fitur per subjek

**Severity:** critical

## Current Problem

Varian fitur ANTAR subjek lebih besar daripada varian DALAM subjek
(`mulut_mean_m` 0.353 vs 0.201), jadi fitur lebih kuat mengkodekan SIAPA
orangnya daripada seberapa cemas dia. Bukti: logistik LOSO AUC 52.52%,
permutation test p = 0.280 (Iterasi 3.9).

`scripts/run_loso.py:337-354` hanya memakai `StandardScaler` yang di-fit pada
gabungan train. Standardisasi global tidak menghapus pergeseran per subjek
karena pergeserannya bukan affine global.

## Target

Opsi `--subject-norm subject`: setiap baris distandardisasi memakai mean/std
subjek itu sendiri (per fitur), dihitung dari baris subjek tersebut saja —
tanpa label, tanpa melihat subjek lain. Subjek uji memakai statistiknya
sendiri (Personal-Zscore, literatur cross-subject).

## Required Design

- Flag baru `--subject-norm {none,global,subject}`, default `none` supaya
  hasil lama tetap bisa direproduksi; runner pipeline yang memakai `subject`.
- Implementasi: fungsi `subject_standardize(df, feature_cols, subject_col)`
  yang mengembalikan df dengan tiap fitur `(x - mean_subjek) / std_subjek`
  (std 0 → 1, anti-bagi-nol).
- Diterapkan **sebelum** impute/scale global, ke `df_tr`, `df_val`, `df_test`
  masing-masing memakai kolom `participant` sendiri.
- Tetap diikuti `StandardScaler` train seperti sekarang (hasil: skala global
  seragam setelah pergeseran subjek dibuang).
- Harus aman untuk mode `--aggregate subject` (1 baris/subjek → std per subjek
  = 0; maka std 0 → 1, fitur jadi 0 untuk semua subjek). Karena itu
  `--subject-norm subject` **tidak boleh** dipakai bersama `--aggregate subject`;
  validasi dan hentikan dengan pesan jelas.
- Catat di `summary.md` bahwa run memakai normalisasi per subjek.

## Tests

- Parse AST.
- `--help` menampilkan `--subject-norm`.
- Kombinasi `--subject-norm subject --aggregate subject` berhenti dengan pesan
  jelas (dicek lewat pembacaan kode; tidak menjalankan training).

## Done Criteria

- [ ] `--subject-norm` ada dengan tiga pilihan.
- [ ] Standardisasi per subjek diterapkan ke train/val/test.
- [ ] Kombinasi terlarang ditolak.
- [ ] Default `none` menjaga reproduksibilitas hasil lama.
