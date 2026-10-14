# Spotting Magnitude Deep Dive — plan

> **Status:** selesai, 2026-10-13. Kesimpulan: mean_m tetap definisi magnitude
> terbaik (dua pengukuran independen); cutoff default tetap 0,3; `SPOT_CUTOFF`
> dibuka untuk uji A/B 0,5 di sisi anxiety; koreksi FINAL.pdf siap tempel di
> `report/findings/koreksi-final-pdf.md`.

- **Goal:** temukan definisi sinyal magnitude spotting terbaik untuk POC-ABS, tervalidasi jujur di CAS(ME)² (split subjek A/B), lalu kunci sebagai default pipeline; perbaiki penyimpangan FINAL.pdf.
- **Architecture:** video → ROI (dlib 68) → POC-ABS per blok 9×9 → magnitude per blok → **agregasi → sinyal → deteksi apex/fase** → klip event → fitur → TabR LOSO.
- **Tech Stack:** numpy/scipy POC, cache npz CAS(ME)², sklearn.

## Must Not Forget

- Pemilihan konfigurasi spotting HANYA di CAS(ME)² (ground truth) atau di fold train — TIDAK BOLEH menyentuh label/data uji anxiety (leak).
- Split LOSO per subjek terjadi SEBELUM preprocessing (imputer/scaler/balance fit di train saja) — sudah terverifikasi di `run_loso.py` (baris 654-662) dan `run_loso_lit_tabr.py` (baris 141-145); jangan dirusak.
- User yang menjalankan ulang pipeline anxiety penuh (stage 1→end). Kita hanya menyiapkan default + temuan.
- Jangan "perbaiki" Hanning di `poc.py` — sudah terbukti no-op yang tidak merugikan (report/findings/poc-abs-karakterisasi.md §2.3).
- Tidak menjalankan test/e2e pipeline anxiety tanpa diminta user.
- Update PROGRESS.md + HANDOFF.md di akhir.

## Issue Index

### high
- [01-magnitude-characterization](issues/01-high-magnitude-characterization.md) — karakterisasi magnitude: kuantisasi, saturasi ±4px, dilusi mean, kandidat definisi baru.
- [02-aggregation-cutoff-sweep](issues/02-high-aggregation-cutoff-sweep.md) — sweep agregasi × cutoff_ratio di CAS(ME)², validasi split subjek A/B.

### medium
- [03-apply-winner-defaults](issues/03-medium-apply-winner-defaults.md) — kunci pemenang sweep sebagai default pipeline.
- [04-final-pdf-corrections](issues/04-medium-final-pdf-corrections.md) — daftar koreksi FINAL.pdf (block 7→9, 3→5 ROI, parameter deteksi, protokol LOSO, angka jujur).

## Target Architecture

```
frame-0 baseline (ABS) → POC 9×9 per blok → magnitude per blok (kuantized int)
   → AGREGASI TERPILIH (hasil sweep, tervalidasi A/B) → sinyal global
   → savgol 3% adaptif → find_peaks (prominence ranking, height=mean+std)
   → find_phase cutoff_ratio TERPILIH → event onset/apex/offset
```

## Priority Order

1 → 2 → 3 → 4 (4 bisa paralel dengan 3)

## Validation Commands

```bash
# sweep agregasi × cutoff (CAS(ME)², cache-based, cepat)
.venv/bin/python scripts/audit_mag_agg_casme2.py
# karakterisasi magnitude (per-blok, sampel video)
.venv/bin/python scripts/diag_magnitude_casme2.py
```

## Rollout Plan

- [x] 01 selesai: angka kuantisasi/saturasi/dilusi + kandidat definisi → findings
- [x] 02 selesai: pemenang tervalidasi A/B → findings
- [x] 03 selesai: default diubah + didokumentasikan
- [x] 04 selesai: daftar koreksi FINAL.pdf diserahkan
- [ ] User menjalankan ulang pipeline anxiety (opsi A/B: V3_SPOT_CUTOFF=0.5) — di tangan user

## Done Criteria

- [x] Ada jawaban terukur: definisi magnitude spotting mana yang terbaik untuk POC-ABS (F1 + A/B validation)
- [x] Default pipeline mencerminkan pemenang (mean_m + cutoff 0,3 tetap)
- [x] Koreksi FINAL.pdf lengkap per bagian
- [x] PROGRESS.md/HANDOFF.md ter-update
