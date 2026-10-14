# 11 — Uji berpasangan dalam-subjek (gerbang keputusan)

**Severity:** critical (gerbang: menentukan apakah Lever fitur layak dikejar)

## Current Problem

Setelah kebocoran subjek dihapus, semua angka jatuh ke acak (LOSO roi25 acc
55.36% = baseline, AUC 51.91%; exp3 44.05%). Pertanyaannya: apakah **keluarga
fitur POC-ABS memang tidak membawa sinyal kecemasan**, atau modelnya yang
salah? Selama ini tidak ada eksperimen yang memisahkan keduanya, karena setiap
perbandingan masih tercampur identitas subjek.

Dataset ini punya alat yang tepat untuk itu dan belum dipakai: **18 subjek
mengubah label antar sesi** (`before` vs `after`), dari metadata segar:

```
before x after:  anxiety→anxiety 24 | anxiety→tidak 17
                 tidak→anxiety    1 | tidak→tidak   14
konsisten 38 | berubah 18
```

Untuk 18 subjek itu: **orang yang sama, wajah yang sama, label berbeda.**
Tidak ada confound identitas sama sekali.

## Target

Uji hipotesis nol: fitur POC-ABS tidak membedakan sesi `before` vs `after`
pada subjek yang labelnya berubah.

## Required Design

- Bergantung pada issue 10 (tabel fitur harus lengkap dulu).
- Untuk tiap subjek dengan label berubah, bandingkan fitur agregat sesi
  `before` vs `after` (mean per fitur per sesi).
- Uji berpasangan per fitur (Wilcoxon signed-rank lebih aman dari t-test
  karena N=18 dan distribusi tak diketahui) + koreksi multiple comparison
  (Benjamini-Hochberg).
- **Kontrol:** 38 subjek yang labelnya konsisten. Di grup ini tidak boleh ada
  perbedaan sistematis; kalau ada, berarti efeknya efek sesi/waktu, bukan
  kecemasan. Kontrol ini yang membuat uji ini kredibel.
- **Arah harus dilaporkan**, bukan hanya signifikansi. Uji awal pada tabel
  basi memberi arah berlawanan dari ekspektasi; itu salah satu alasan uji ini
  harus diulang di data bersih.
- Keluaran: `output/training/within_subject_paired/summary.md` + `.csv`.
- Script baru: `scripts/within_subject_test.py`.

## Tests

- Jalankan script; laporkan jumlah fitur signifikan di grup "berubah" vs grup
  kontrol, plus arahnya.

## Done Criteria

- [ ] Uji berpasangan dijalankan pada tabel fitur yang sudah lengkap.
- [ ] Grup kontrol dilaporkan berdampingan.
- [ ] Arah efek dilaporkan.
- [ ] Kesimpulan eksplisit: sinyal ada / tidak ada.

## Konsekuensi

- **Sinyal ADA** → kejar issue 12 (head pose + landmark) dan perluasan fitur;
  target 65–72% realistis.
- **Sinyal TIDAK ADA** → berhenti menggarap POC-ABS sebagai fitur level
  subjek; pindah ke issue 12 dari awal, atau tambah N.
