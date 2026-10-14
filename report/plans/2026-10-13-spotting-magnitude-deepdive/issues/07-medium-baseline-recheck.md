# 07 — Ulang uji acuan baseline (frame-0 vs lag-N) dengan resep baru

**Severity:** medium

## Current Problem

Acuan POC (frame-0 ABS vs lag-30/lag-10 vs berurutan) terakhir diuji dengan
metrik P@k dan resep deteksi LAMA (audit 2026-10-09 §4). Kesimpulan "frame-0
bukan regresi, jangan dikembalikan" valid untuk arah besar, tapi lag-N
(lag10/lag30) belum pernah diukur dengan F1 + resep deteksi baru + validasi
subjek. Lag-N berpotensi menekan drift postur yang mencemari acuan frame-0
pada video panjang.

## Target

Jalankan evaluasi F1 (toleransi 0, resep baru) pada cache baseline yang sudah
ada (`output/training/casme2_baseline_signals`, 41 video): abs / lag10 /
lag30 / seq. Laporkan apa adanya; kalau lag-N mendekati atau mengalahkan abs,
baru pertimbangkan perhitungan cache 86 video.

## Required Design

- Hanya membaca cache yang ada; tidak menghitung POC baru.
- 41 video ≠ 86 video — sertakan mean_m/abs pada subset yang sama sebagai
  pembanding apple-to-apple.

## Tests

Tidak ada (kontrak).

## Done Criteria

- [x] Tabel F1 di `report/findings/audit-spotting-casme2.md` §12:
  abs 0,3486 vs lag30 0,1921 / lag10 0,1695 / seq 0,1412
- [x] Keputusan: frame-0 tetap — lag-N tidak layak dibangun cache penuhnya
