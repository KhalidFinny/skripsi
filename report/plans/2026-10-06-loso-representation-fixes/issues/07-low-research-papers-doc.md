# 07 — Dokumen rujukan paper riset

**Severity:** low

## Current Problem

Rujukan literatur untuk penurunan akurasi masih tersebar di percakapan dan
sebagian di `report/findings/literature-accuracy-drop-2021-2026.md`. User
meminta berkas `.md` khusus berisi paper riset yang disitasi.

## Target

`report/documentation/research-papers.md` — daftar paper 2021→sekarang yang
disitasi, dikelompokkan per tema, tiap entri berisi: penulis/tahun, venue,
tautan, dan satu baris "kenapa relevan" yang mengaitkan ke temuan repo.

## Required Design

- Kelompok: (1) evaluasi/kebocoran/protokol LOSO, (2) cross-subject &
  identitas, (3) micro-expression spotting/ROI/baseline, (4) TabR & tabular
  N kecil, (5) deteksi kecemasan/stres dari wajah, (6) rujukan klasik
  pendukung (pra-2021) ditandai jelas sebagai latar.
- Fokus 2021→sekarang; entri pra-2021 hanya bila jadi dasar langsung
  (SAMM/ABT, Davison baseline) dan diberi tanda.
- Setiap entri punya tautan yang bisa dibuka.
- Sertakan tabel pemetaan: sebab → paper pendukung → perbaikan yang dipakai.
- Rujuk balik ke `report/findings/literature-accuracy-drop-2021-2026.md`
  (analisis) supaya tidak duplikasi; dokumen ini yang jadi daftar sitasi.

## Tests

- Cek berkas terbentuk dan tiap entri punya tautan.
- Tidak ada tautan yang jelas salah (spot-check domain).

## Done Criteria

- [ ] `report/documentation/research-papers.md` ada.
- [ ] Paper 2021→sekarang mendominasi, pra-2021 ditandai.
- [ ] Tabel pemetaan sebab → paper → perbaikan ada.
