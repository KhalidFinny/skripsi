# 02 — Sweep agregasi × cutoff_ratio di CAS(ME)²

**Severity:** high

## Current Problem

- Alternatif agregasi (max_m, motion_count, mean_x, mean_y, angle_R) terakhir
  diuji dengan resep deteksi LAMA (window tetap 7 + ranking nilai). Dengan resep
  BARU (3% adaptif + prominence ranking, F1 0,3192) belum pernah diuji.
- `cutoff_ratio` 0,5 menaikkan F1 ketat (IoU≥0,5) 0,149→0,179 dan memperpendek
  durasi event 59→41 frame (mendekati GT median 28) — terbukti, tapi belum
  diterapkan.
- Definisi baru dari isu 01 (top-k%, tertimbang) belum pernah diukur sama sekali.

## Target

Skrip `scripts/audit_mag_agg_casme2.py`:

- Grid: agregasi {mean_m, max_m, motion_count, top25_m, weighted_m} ×
  cutoff_ratio {0,3, 0,5}, deteksi DIPAKUIN ke resep baru
  (3% adaptif, prominence ranking, height=mean+std, top_k=5, global_mean).
- Sinyal dari cache kaya `output/training/casme2_rich_signals/*.npz` bila
  memungkinkan; top25_m/weighted_m dihitung dari hasil isu 01 (cache per-blok
  untuk 86 video penuh hanya jika isu 01 menunjukkan kandidat itu menjanjikan).
- Protokol: 22 subjek dibagi paruh A/B (deterministik). Konfigurasi terbaik
  dipilih di A, dilaporkan di B, dan sebaliknya — sama seperti audit 2026-10-09
  §8.4, menutup jebakan "pilih parameter di data uji".

Metrik: F1 (beririsan, toleransi 0) + F1 ketat (IoU≥0,5) + durasi median.

## Required Design

- Tidak mengubah default pipeline di isu ini — hanya mengukur.
- Jika pemenang A→B dan B→A berbeda, pilih yang menang di kedua arah atau
  laporkan tidak ada pemenang (jangan memaksakan).

## Tests

Tidak ada (kontrak).

## Done Criteria

- [x] Tabel grid lengkap di `report/findings/audit-spotting-casme2.md` (§10) +
  `output/training/audit_mag_agg_casme2/README.md`
- [x] Satu pemenang tervalidasi dua arah, ATAU kesimpulan mean_m tetap terbaik
  → **mean_m tetap terbaik** (fold A/B memilih kandidat berbeda; mean_m unggul
  di tabel penuh). cutoff 0,3 menang F1 longgar di kedua fold → default tetap;
  cutoff 0,5 menang F1 ketat → dibuka sebagai opsi `SPOT_CUTOFF` untuk uji sisi
  anxiety (isu 03)
