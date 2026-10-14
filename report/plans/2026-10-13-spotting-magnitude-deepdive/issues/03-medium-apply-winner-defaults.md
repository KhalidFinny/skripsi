# 03 — Kunci pemenang sweep sebagai default pipeline

**Severity:** medium

## Current Problem

`cutoff_ratio` default masih 0,3 (`scripts/spotting.py`) meski 0,5 terbukti lebih
baik di F1 ketat; agregasi sinyal akan berubah sesuai hasil isu 02. Default yang
usang membuat user menjalankan pipeline dengan konfigurasi sub-optimal.

## Target

- `scripts/spotting.py` / `scripts/process_spotting_pipeline.py`: default
  mengikuti pemenang isu 02 (agregasi + cutoff_ratio), tetap bisa di-override
  via env SPOT_* seperti sekarang.
- Komentar di kode menyebut sumber keputusan (findings isu 02), mengikuti pola
  komentar audit yang sudah ada.
- PROGRESS.md + HANDOFF.md di-update: default baru, alasan, dan perintah untuk
  user menjalankan ulang pipeline (regenerasi klip + fitur + LOSO).

## Required Design

- Perubahan default minimal; tidak menambah flag baru kecuali pemenangnya
  memang definisi sinyal baru (top25/weighted).
- Perintah fresh-run untuk user mengikuti pola `scripts/run_pipeline_v3.sh`
  (--fresh), bukan skrip baru.

## Tests

Tidak ada (kontrak). Cek: `.venv/bin/python -c "import scripts.spotting"` atau
lint ringan; user yang menjalankan pipeline.

## Done Criteria

- [x] Default kode = pemenang sweep → mean_m + cutoff 0,3 tetap (sweep tidak
  menghasilkan pemenang baru; default tidak berubah secara angka)
- [x] Opsi `SPOT_CUTOFF` (pipeline) + `V3_SPOT_CUTOFF` (run_pipeline_v3.sh)
  untuk uji A/B cutoff 0,5 di sisi anxiety — terverifikasi: default 0,3,
  `SPOT_CUTOFF=0.5` → 0,5, `bash -n` OK
- [x] PROGRESS.md + HANDOFF.md mencatat perubahan + perintah fresh-run
