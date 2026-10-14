# 06 — Sweep internals detektor (merge, top_k, durasi, uptick, radius)

**Severity:** high

## Current Problem

Resep deteksi baru (3% adaptif + prominence) memakai angka warisan yang belum
pernah di-sweep di protokol baru: `merge_distance=10`, `top_k=5`,
`min_phase_duration=2`, `valley_uptick_threshold=0,75`, `MAX_SEARCH_RADIUS=100`.
Audit sebelumnya hanya menyapu window smoothing, ranking, height, dan cutoff.

## Target

Skrip `scripts/audit_detector_internals_casme2.py` — one-at-a-time sensitivity
di sekitar titik sekarang (bukan grid penuh), cache-based (mean_m, 86 video):

| parameter | titik sekarang | variasi |
|---|---|---|
| merge_distance | 10 | 5, 10, 20 |
| top_k | 5 | 3, 4, 5, 6, 8 |
| min_phase_duration | 2 | 1, 2, 4 |
| valley_uptick | 0,75 | 0,5, 0,75, 0,9 |
| search_radius | 100 | 30, 60, 100, 200 |

Setiap variasi diukur F1 (toleransi 0) + F1 ketat + durasi median di semua 86
video; kombinasi terbaik divalidasi split subjek A/B (kedua arah) seperti
isu 02.

## Required Design

- Sinyal: cache kaya mean_m (sudah ada). Agregasi global + resep baru.
- Hanya satu parameter digeser per run; kalau ada >1 yang menang, uji
  kombinasinya lalu validasi A/B.
- Tidak mengubah default produksi di isu ini.

## Tests

Tidak ada (kontrak).

## Done Criteria

- [x] Tabel sensitivitas 5 parameter di `report/findings/audit-spotting-casme2.md` §11
- [x] Validasi A/B: KOMBI (topk4+mindur4+uptick0,9+radius200) F1 0,3451 menang di
  KEDUA fold — tapi F1 ketat turun (0,0986) dan durasi memanjang (84). Default
  pipeline untuk fitur tetap BASE; KOMBI = opsi pelaporan spotting
