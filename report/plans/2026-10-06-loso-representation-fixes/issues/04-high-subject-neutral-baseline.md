# 04 — Baseline netral per subjek di spotting/ekstraksi

**Severity:** high

## Current Problem

Baseline POC-ABS adalah **frame pertama klip event**, dan klip event disimpan
dari `onset_frame` sampai `offset_frame`
(`scripts/process_spotting_pipeline.py`, `save_event_clip_frames`). Jadi
"frame 1" klip = frame onset yang ototnya sudah mulai berkontraksi, bukan
wajah netral. Akibatnya amplitudo onset→apex sistematis terpotong dan
bervariasi per event dan per orang.

Ekstraksi juga memakai frame yang sama:
`scripts/extract_features_poc_abs.py:394-403` (`if idx == 0: baseline_rois`).

Literatur: SAMM memakai *individualised baseline* + *Adaptive Baseline
Threshold*; Davison et al. 2016 memakai baseline netral per peserta.

## Target

Spotting menyimpan satu frame referensi netral per sample; ekstraksi memakai
frame itu sebagai acuan POC, bukan frame onset klip.

## Required Design

- `process_spotting_pipeline.py`:
  - env baru `SPOT_SAVE_NEUTRAL` (default `0` = perilaku lama).
  - bila `1`, simpan `neutral.png` di direktori sample (median frame dari
    `SPOT_NEUTRAL_FRAMES` frame pertama video, default 10; median per piksel
    menekan noise sensor).
  - sampah gambar di-`del` + `gc.collect()` seperti pola file ini.
- `extract_features_poc_abs.py`:
  - argumen `--baseline {onset,neutral}`, default `onset` (perilaku lama).
  - bila `neutral`: acuan = `neutral.png` di direktori sample; bila tidak ada,
    **jatuh ke onset** dan catat peringatan (jangan gagal diam-diam).
  - direktori sample diturunkan dari `clip.event_dir.parent`.
- Perubahan ini memerlukan re-run spotting + ekstraksi dengan dataset mentah;
  `/mnt/FINNY/dataset` tidak ada di mesin ini, jadi hanya kode dan perintah
  yang disiapkan, dicatat di `report/documentation/changes-log.md`.
- Tabel fitur lama tidak ditimpa: output tetap
  `poc_abs_roi_signals.xlsx` hanya bila dijalankan ulang; dokumentasi
  menyarankan nama baru untuk run netral.

## Tests

- Parse AST kedua script.
- `extract_features_poc_abs.py --help` menampilkan `--baseline`.
- Pembacaan kode memastikan fallback ke onset + peringatan.

## Done Criteria

- [ ] Spotting bisa menyimpan `neutral.png` per sample.
- [ ] Ekstraksi punya `--baseline neutral`.
- [ ] Fallback ke onset dengan peringatan bila netral tidak ada.
- [ ] Perintah re-run tercatat di dokumentasi.
