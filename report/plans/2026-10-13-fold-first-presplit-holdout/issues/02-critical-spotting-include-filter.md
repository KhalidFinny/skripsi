# 02 — Spotting include-filter (critical)

## Current Problem

`process_spotting_pipeline.py::discover_video_samples` memproses SEMUA video
di bawah `SPOT_DATASET_ROOT`. Tidak ada cara membatasi ke subset orang.

## Target

Env baru `SPOT_INCLUDE_PERSONS=<path txt>` (default kosong = semua, perilaku
sekarang bit-identik):

- Baca file (satu orang per baris, abaikan baris kosong / `#`), normalize
  tiap entri dengan regex yang sama (`_[0-9]+$` strip).
- Di `discover_video_samples`: parse `participant_raw` dari
  `relative_parent.parts[2]` (struktur `<phase>/<condition>/<participant>_<ts>/q*`),
  normalize, buang sample yang orangnya tidak ada di daftar.
- Log satu baris ringkas di main: `include-filter: X video diproses, Y
  dilewati (Z orang train pool)`.

## Required Design

- Struktur path sudah dipakai di tempat lain (`extract_features_poc_abs.py:227`
  memakai parts[2] sebagai participant_raw) — pakai indeks yang sama.
- Kalau `relative_parent` tidak punya ≥3 parts → JANGAN difilter (dataset
  lain seperti CAS(ME)² punya struktur beda; filter hanya aktif bila
  strukturnya cocok, supaya benchmark spotting tidak berubah).
- File hilang/tidak terbaca → die keras, jangan diam-diam proses semua.

## Tests

- py_compile bersih.
- Jalankan discover dengan filter 44 orang di raw root → 560 - (video 12
  orang) tersisa; tanpa filter → 560 (sama seperti sekarang).

## Done Criteria

- [ ] Env terbaca, default no-op
- [ ] Hitungan video sesuai (44 orang ≈ 440 video, 12 orang ≈ 120)
- [ ] Log ringkas muncul
