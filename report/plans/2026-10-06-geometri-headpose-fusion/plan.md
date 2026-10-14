# Plan — Keluarga Fitur Kedua: Geometri Wajah + Head Pose

> **Status:** SELESAI (kode + verifikasi statis + validasi terbatas pada data nyata)
> — 2026-10-06.
>
> Belum dijalankan (menunggu perintah user): pipeline penuh
> `./scripts/run_pipeline_v3.sh`.
>
> Penyimpangan yang disengaja, dicatat:
> - Config training default pipeline diganti dari `tabr_loso_roi25_reg_ce.toml`
>   ke `tabr_loso_roi25_reg.toml`. Config `_reg_ce` terbukti REGRESI (pemilihan
>   epoch cross-entropy berhenti di epoch <= 1 pada 40-48/56 fold). Memakai
>   config yang sudah rusak akan mengacaukan uji fitur baru ini.
> - `LOSO_DATASET` default diganti ke `convat_apex_anxiety_loso_v3_geo`. Kalau
>   tetap memakai nama lama, 56 fold lama yang sudah `DONE` akan dilewati
>   diam-diam dan training tidak pernah jalan.
> - LOSO **dipertahankan** (keputusan user). Tidak ada split bocor subjek.

## Goal

Memberi POC-ABS sinyal yang tidak ia miliki, dan membuat retrieval TabR
mencocokkan kondisi alih-alih identitas, **tanpa** mengganti POC-ABS, LOSO, atau
TabR — lalu membandingkannya dengan keadaan sebelum perubahan.

## Problem

Gerbang within-subject sudah menyatakan POC-ABS tidak membawa sinyal kecemasan
(baseline netral: 0/25 fitur signifikan, LOSO dalam-subjek 0,528, p=0,473).
Tuning TabR tidak bisa memperbaiki representasi yang tidak berisi sinyal.

## Fix

Keluarga fitur KEDUA dari 68 landmark dlib yang **sudah** dihitung spotting:
geometri wajah + head pose, semua fitur statis diskala jarak inter-okular lalu
dikurangi wajah netral tiap orang (Differential AU, StressGAT).

Dasar riset lengkap: `report/findings/geometri-headpose.md`.

## Architecture

```
output/apex_v2/dataset/**  (klip event + neutral.png)   <- tidak berubah
  │
  └─ scripts/extract_features_poc_abs.py --with-geometry
        │  satu pass, landmark dihitung sekali
        ├─ poc_abs_roi_signals_v3.xlsx         POC-ABS saja (skema lama, TIDAK berubah)
        ├─ poc_abs_roi_signals_v3_geo.xlsx     geometri saja (21 kolom geo_*)
        └─ poc_abs_roi_signals_v3_fused.xlsx   gabungan  <- dipakai training
              │
              ├─ build_feature_cache.py -> *_fused_full.pkl
              ├─ build_temporal_features.py -> *_fused_temporal.pkl
              ├─ within_subject_test.py x3 (poc / geo / gabungan)  <- gerbang
              └─ run_loso.py --quiet --aggregate subject
```

## Must Not Forget

- **Jangan** mengubah skema `poc_abs_roi_signals_v3.xlsx`; hasil lama harus
  tetap bisa direproduksi.
- **Jangan** menjalankan training/spotting/e2e penuh tanpa perintah user. Yang
  dijalankan di sini hanya verifikasi statis + validasi terbatas (`--limit 5`,
  1 fold/1 seed) pada data nyata.
- **Jangan** commit, push, atau deploy.
- Semua teks dokumen dan komentar kode memakai bahasa Indonesia, mengikuti gaya
  `report/documentation/changes-log.md`.
- LOSO dipertahankan; tidak ada split yang bocor subjek.
- `--drop-features` menggantikan default, jadi pola untuk POC-ABS saja harus
  menyertakan `_max_m$`: `--drop-features "_max_m$|^geo_"`.

## Issue Index

**Critical**
- 01 — `ROIExtractor.extract_landmarks()` + `extract_rois_from_landmarks()`,
  `extract_rois` jadi pembungkus tipis. ROI harus identik bit-per-bit.
- 02 — `features_extraction/geometry.py`: 21 fitur, head pose kontinu
  (relatif acuan frontal), cadangan bersatuan derajat, tanpa NaN.
- 03 — `--with-geometry` di ekstraktor: tiga tabel dari satu pass.

**High**
- 04 — Gerbang within-subject dijalankan untuk 3 keluarga fitur, bukan 1.
- 05 — `--quiet` di `run_loso.py`: progress bar TabR dimatikan + keluaran per
  fold ke `fold_XXX/train.log`.

**Medium**
- 06 — `run_pipeline_v3.sh`: stage 2/3/4/5/6/7 memakai tabel gabungan; default
  config dan nama dataset diperbaiki.
- 07 — Dokumentasi: findings, changes-log, HANDOFF/PROGRESS.

## Validation Commands

```bash
# parse + sintaks
.venv/bin/python -c "import ast,pathlib;[ast.parse(pathlib.Path(f).read_text()) for f in ['features_extraction/geometry.py','comparasion/core/roi.py','scripts/extract_features_poc_abs.py','scripts/run_loso.py']]"
bash -n scripts/run_pipeline_v3.sh

# argumen + rencana
.venv/bin/python scripts/extract_features_poc_abs.py --help
.venv/bin/python scripts/run_loso.py --help
./scripts/run_pipeline_v3.sh --dry-run
```

## Rollout Plan

- [x] 01 `extract_landmarks` / `extract_rois_from_landmarks`
- [x] 02 `features_extraction/geometry.py`
- [x] 03 `--with-geometry` + 3 tabel
- [x] 04 Gerbang 3 keluarga fitur
- [x] 05 `run_loso.py --quiet`
- [x] 06 Wiring pipeline
- [x] 07 Dokumentasi
- [x] 08 Verifikasi statis + validasi terbatas

## Done Criteria

- [x] ROI identik bit-per-bit antara jalur lama dan jalur landmark baru.
- [x] `extract_rois` tetap raise `ValueError` kalau tidak ada wajah.
- [x] Tabel POC-ABS saja tidak memuat kolom `geo_*`.
- [x] Tabel geometri = kolom identitas + tepat 21 kolom `geo_*`.
- [x] Tabel gabungan = POC-ABS + geometri.
- [x] Tidak ada NaN dan tidak ada kolom konstan pada tabel geometri.
- [x] Head pose kontinu (tidak ada lonjakan 360°).
- [x] `--quiet` mengecilkan log dan tetap menulis `DONE.json` + `report.json`.
- [x] `--quiet` tidak merusak `import tqdm.auto` (dipakai `lib/dnnr`).

## Bukti Verifikasi (2026-10-06)

- Parse AST 4 file: ok. `bash -n scripts/run_pipeline_v3.sh`: ok.
- `--help` bersih untuk ekstraktor (opsi `--with-geometry` tampil) dan
  `run_loso.py`.
- `./scripts/run_pipeline_v3.sh --dry-run`: rencana stage 2-7 konsisten, tabel
  gabungan dipakai di stage 4-7.
- **ROI setara**: 6 frame nyata, `extract_rois(img)` ==
  `extract_rois_from_landmarks(img, extract_landmarks(img))` identik
  bit-per-bit untuk kelima ROI.
- **Geometri pada 400 frame nyata**: semua finite; pitch −3,4…+1,4;
  yaw −3,8…+13,2; roll −2,3…+0,5 (derajat, semua jauh dari titik wrap);
  `head_motion` maksimum 8,2°/frame.
- **Ekstraksi terbatas** (`--limit 5`, `--with-geometry`, baseline neutral):
  65 baris; POC 48 kolom tanpa `geo_*`; geometri 34 kolom (13 identitas + 21
  `geo_*`); gabungan 69 kolom; 0 NaN; 0 kolom konstan.
- **`--quiet`**: fold 0 / 1 seed, `--aggregate subject` — log turun dari
  460 baris/26.617 byte jadi 22 baris/1.631 byte; `DONE.json`, `report.json`,
  `test_split.csv`, `val_split.csv`, dan `fold_000/train.log` (339 baris)
  semuanya tertulis.
- Shim `tqdm` diverifikasi: `from tqdm import tqdm` mengembalikan no-op,
  `import tqdm.auto` dan `import tqdm.std` tetap jalan, context manager +
  `update`/`set_postfix`/`set_description`/`write` tidak error.

**Belum diverifikasi:** pipeline penuh (spotting 560 video + ekstraksi penuh +
gerbang + training 56 fold x 3 seed). Itu yang dijalankan user berikutnya.

## Fase 2 — perbaikan metodologi (batch A, 2026-10-06)

Pipeline penuh Fase 1 sudah dijalankan (hasil: `changes-log.md` Iterasi 4.26).
Audit setelah itu menemukan **6 bug**; semuanya sudah diperbaiki di kode dan
diverifikasi pada artefak nyata. Re-run BELUM dijalankan.

**Critical**

- [x] **#1 Urutan variance-vs-scale** (`run_loso.py`, `run_loso_baseline.py`).
  `VarianceThreshold(1e-4)` jalan pada nilai MENTAH sebelum scaler → itu filter
  SKALA. Terukur: geometri hanya 26/42 kolom lolos (385 total); setelah dibalik
  (scale dulu) jadi 42/42 (402). 16 kolom geometri tidak pernah sampai ke model,
  termasuk `geo_lip_corner_drop` (p gerbang 0,0352) dan `geo_mouth_open`.
  **Membatalkan kesimpulan Iterasi 4.26** ("geometri menyumbang nol").
  Fitur yang bertahan nilainya identik (`np.allclose` True) — yang berubah hanya
  seleksi. Tetap fit train saja, tidak ada kebocoran.
- [x] **#6 `--force` tidak diteruskan ke stage 6** (`run_pipeline_v3.sh`).
  `run_pipeline_v3.sh --force` mengekstraksi ulang fitur TAPI melewati semua 56
  fold (DONE.json) dan melaporkan SELESAI dengan hasil LAMA. Sekarang
  diteruskan lewat `FORCE_ARG`.

**High**

- [x] **#2 Roll solvePnP ambigu** → `normalize_roll()` melipat roll ke (-90, 90].
  Tabel fitur tersimpan masih rusak → butuh re-ekstraksi.
- [x] **#3 Permutasi gerbang global → berpasangan** (`within_subject_test.py`).
  p: POC 0,7761→0,8010; geometri 0,7512→0,7363; gabungan 0,2040→0,1542.
  Kesimpulan tidak berubah, metode sekarang bisa dipertahankan.

**Medium**

- [x] **#4 Ambang Youden bisa = `inf`** (`collect_loso_results.py`). Terjadi 1/56
  fold → laporan menulis `inf ± nan`. Sekarang 0,5250 ± 0,0322. Ini merusak
  satu-satunya lever yang terbukti berguna.

**Low**

- [x] **#5 Label laporan salah**: heading `## Level {row_unit}` menamai tabel
  frame sebagai "Level subject"; judul gerbang di-hardcode "(POC-ABS)".

### Verifikasi Fase 2

Semua pada artefak nyata, tanpa training.

- Parse AST 4 berkas + `bash -n` pipeline: ok.
- #1: tiru urutan baru pada tabel gabungan → 385 vs 402; geo 26/42 vs 42/42;
  nilai kolom yang bertahan identik (`np.allclose` True).
- #3: 500 permutasi × 3 subjek → label hanya dibalik di dalam subjek, 0 rusak.
- #4: seed 0 v3_geo lama mean=inf → baru 0,5292; ketiga seed berhingga.
- #5: collect + gerbang dijalankan ke direktori scratch; label benar.
- #6: dry-run dengan/tanpa `--force`.

### Fase 2 — rollout

- [ ] Re-ekstraksi (fix roll) + re-run LOSO: `./scripts/run_pipeline_v3.sh --force`
      (~1 jam). `--force` wajib, kalau tidak stage 2-4 dan 56 fold dilewati.

### Done Criteria Fase 2

- [x] Keenam bug diperbaiki dan diverifikasi.
- [ ] Hasil bersih dari run ulang (belum dijalankan).
- [ ] Klaim "keluarga geometri gagal" diuji ulang dengan seluruh 42 kolom.

