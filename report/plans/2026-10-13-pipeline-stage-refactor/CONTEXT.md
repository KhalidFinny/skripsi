# CONTEXT — Refactor pipeline: stage terpisah + struktur folder jelas

## Problem

Repo ini sulit dinavigasi, terutama saat Khalid perlu **menunjukkan pipeline**
ke pembimbing atau menjalankannya sendiri. Keluhannya: "i cant find when i need a
pipeline to show, so each stage should be well separated and well mark on which
is which, for instance where is the split, the spotting, the apex etc".

Keadaan yang terverifikasi di repo:

- **`scripts/` datar berisi 61 file.** Hanya **10** di antaranya adalah stage
  pipeline. Sisanya ±25 skrip eksperimen CAS(ME)² (`audit_*`, `probe_*`,
  `diag_*`, `rank_*`), ~13 skrip legacy, dan beberapa tool. Tidak ada pemisah
  antara "pipeline" dan "eksperimen".
- **Stage tidak terlihat sebagai stage.** Nomor stage hanya hidup di
  `run_pipeline_v3.sh` (baris `banner`) dan di nama file log. Nama skrip tidak
  memberi tahu urutannya: mana `0` (split), mana `1` (spotting), mana `6`
  (training) — harus dibaca satu per satu.
- **Nama modul menyesatkan:**
  - `comparasion/` terdengar seperti folder eksperimen perbandingan, padahal
    `comparasion/core/` **dipakai produksi** oleh `extract_features_poc_abs.py`
    (impor `ComparisonConfig` dan `ROIExtractor`).
  - `scripts/spotting.py` bukan pipeline spotting (itu
    `process_spotting_pipeline.py`), melainkan **dataclass konfigurasi**
    `SpottingConfig`.
  - `src/` isinya adalah model TabR (`TabR.py`, `data_module.py`,
    `encoder.py`) — nama `src/` tidak memberi petunjuk apa pun.
- **Dua folder output mirip:** `output/` (hasil pipeline kita, 13+ GB) dan
  `outputs/` (isinya hanya satu file: `models/shape_predictor_68_face_landmarks.dat`).
- **Titik masuk tidak menonjol.** Satu-satunya cara tahu harus mulai dari mana
  adalah membuka `report/documentation/pipeline.md` atau mengingat nama
  `scripts/run_pipeline_v3.sh`.
- **File stage melewati batas 500 baris** (aturan dev-tendencies):
  `process_spotting_pipeline.py` 1089, `run_loso.py` 829,
  `extract_features_poc_abs.py` 724, `collect_loso_results.py` 595,
  `run_pipeline_v3.sh` 737.

Akibatnya, jawaban atas pertanyaan sederhana seperti "di mana split-nya?" atau
"di mana deteksi apex-nya?" tidak bisa dijawab dari struktur folder, hanya dari
hafalan.

## Fix

Pindahkan pipeline ke **satu folder `pipeline/`** dengan **stage bernomor** yang
namanya sudah menjelaskan urutan dan isinya, lalu pisahkan eksperimen dan kode
legacy keluar dari jalur pipeline.

Ringkasnya:

1. `pipeline/` baru: `run.sh` (satu titik masuk) + `stages/` berisi
   `0_presplit.py` … `8_holdout.py` + `README.md` berisi peta stage.
2. `research/casme2/` baru: semua skrip audit/probe/diag CAS(ME)².
3. `legacy/` baru: runner dan skrip yang sudah digantikan.
4. Rename modul yang menyesatkan supaya nama = perannya.
5. Satu folder output untuk data yang dihasilkan; model dlib dipindah ke `models/`.

Tidak ada logika pipeline yang diubah. Yang berubah hanya **lokasi, nama, dan
penanda stage**. Semua angka harus tetap sama.

## Architecture Now

Sesudah refactor, satu layar bisa menjawab "di mana apa":

```
pipeline/                        ← SATU tempat untuk pipeline
  README.md                      ← peta stage (mulai dari sini)
  run.sh                         ← satu titik masuk
  paths.py                       ← satu tempat yang tahu root repo
  spotting_config.py             ← konfigurasi spotting (was scripts/spotting.py)
  configs/                       ← konfigurasi training (.toml)
  stages/
    0_presplit.py                ← SPLIT per orang (sebelum spotting)
    1_spotting.py                ← SPOTTING / cari apex
    2_extract_poc_abs.py         ← EKSTRAKSI FITUR POC-ABS
    3_cache.py                   ← cache pkl
    4_temporal.py                ← fitur temporal (rise, dll)
    5_gate.py                    ← gerbang within-subject
    6_train_loso.py              ← TRAINING LOSO TabR
    7_collect.py + 7_baseline.py ← kumpulkan hasil + baseline
    8_holdout_combine.py         ← evaluasi holdout 12 orang
  serve/
    train_final.py               ← latih model final
    predict.py                   ← pakai model final

apex/                            ← deteksi apex (ApexPhase, ApexSmoother)
features/                        ← was features_extraction/ (poc, roi, vektor)
tabr/                            ← was src/ (model TabR)
shared/                          ← was comparasion/core/ (config + roi)

research/
  casme2/                        ← 26 eksperimen CAS(ME)²
  audits/                        ← 4 audit umum
legacy/                          ← 17 file yang sudah digantikan
models/                          ← bobot model (dlib, dll)
output/                          ← hasil run (13+ GB, gitignored)
```

`scripts/` **hilang sepenuhnya**: 61 file habis terbagi ke `pipeline/stages/` (10),
`pipeline/serve/` (2), `pipeline/` (2), `research/` (30), dan `legacy/` (17).

## Key Files

**Stage pipeline (dipindah ke `pipeline/stages/`):**

- `scripts/split_persons_presplit.py` → `0_presplit.py` (stage 0, split)
- `scripts/process_spotting_pipeline.py` → `1_spotting.py` (stage 1, spotting/apex)
- `scripts/extract_features_poc_abs.py` → `2_extract_poc_abs.py` (stage 2)
- `scripts/build_feature_cache.py` → `3_cache.py` (stage 3)
- `scripts/build_temporal_features.py` → `4_temporal.py` (stage 4)
- `scripts/within_subject_test.py` → `5_gate.py` (stage 5)
- `scripts/run_loso.py` → `6_train_loso.py` (stage 6)
- `scripts/collect_loso_results.py` → `7_collect.py` (stage 7)
- `scripts/run_loso_baseline.py` → tetap, dipanggil stage 7
- `scripts/combine_feature_tables.py` → dipanggil stage 8

**Runner:** `scripts/run_pipeline_v3.sh` → `pipeline/run.sh`

**Modul pendukung (dipakai stage, tetap jadi library):**

- `apex/` — `ApexPhase`, `ApexSmoother`, `ApexPhaseVisualizer`
- `features_extraction/` — `poc.py`, `quadran.py`, `vektor.py`, `geometry.py`,
  `roi_config.py` (sumber kebenaran ROI)
- `comparasion/core/` — `config.py`, `roi.py` (dipakai stage 2)
- `src/` — `TabR.py`, `data_module.py`, `encoder.py`
- `scripts/spotting.py` — `SpottingConfig` (konfigurasi, bukan pipeline)

**Konfigurasi:** `experiments/configs/*.toml`

## Important Behavior Changes

- **Perintah run berubah**: `./scripts/run_pipeline_v3.sh` →
  `./pipeline/run.sh`. Semua env var (`V3_PRESPLIT`, `V3_SPOT_SIGNAL`, dst)
  tetap sama.
- **Nomor stage tetap sama** (0–8), hanya lokasi filenya yang pindah.
- **Tidak ada perubahan angka.** Logika tiap stage tidak disentuh.
- **Setiap skrip stage butuh perbaikan `sys.path`.** Sekarang tiap skrip memakai
  `ROOT = Path(__file__).resolve().parent.parent`. Setelah pindah ke
  `pipeline/stages/` (dua tingkat di bawah root), itu menjadi
  `parents[2]`. Ini wajib diperbaiki, kalau tidak semua impor
  (`from apex import ...`, `from features_extraction ...`,
  `from comparasion.core.config import ...`) langsung gagal.
- Skrip eksperimen CAS(ME)² dan legacy **tidak lagi** ikut terlihat di
  `scripts/`.

## Tests

Kontrak Khalid: **tidak menjalankan test/e2e kecuali diminta.** Verifikasi yang
dipakai di sini hanya:

- `py_compile` untuk semua file yang dipindah.
- `bash -n pipeline/run.sh` untuk sintaks shell.
- `./pipeline/run.sh --dry-run` (dan varian `V3_PRESPLIT=1`) untuk membuktikan
  urutan stage dan path tetap benar.
- `grep` untuk memastikan tidak ada referensi ke path lama yang tertinggal.

Run pipeline penuh (berjam-jam) **dijalankan Khalid**, bukan oleh agen.

## Validation Done

Baru sampai tahap **discovery**. Yang sudah diverifikasi:

- `scripts/` berisi **61 file**, terbagi: **10** stage pipeline, **26** eksperimen
  CAS(ME)², **4** audit umum, **17** legacy, **4** pendukung pipeline
  (`run_pipeline_v3.sh`, `spotting.py`, `train_final_model.py`, `predict.py`).
  10+26+4+17+4 = 61, jadi tidak ada file yang tak terhitung.
- `comparasion/core/` **hidup** — diimpor `extract_features_poc_abs.py`
  (bukan dead code, meski namanya menyesatkan).
- `scripts/spotting.py` **hidup** — diimpor `process_spotting_pipeline.py`
  sebagai `SpottingConfig`.
- `src/` **hidup** — diimpor `train_final_model.py`, `predict.py`,
  `run_loso_lit_tabr.py`.
- `save_neutral_references.py` **legacy** — hanya dipanggil `run_pipeline.sh`
  (v1); pipeline v3 menyimpan `neutral.png` sendiri di stage 1.
- Tiap skrip stage memakai `Path(__file__).resolve().parent.parent` sebagai
  `ROOT` → akan rusak kalau dipindah tanpa penyesuaian.
- Jalur model dlib ada di **dua** tempat: `comparasion/core/config.py:22`
  (relatif) dan `process_spotting_pipeline.py:51` (dengan override
  `SPOT_PREDICTOR`).
- `output/` 13+ GB; `outputs/` hanya berisi
  `models/shape_predictor_68_face_landmarks.dat`.
- **23 dokumen** menyebut `run_pipeline_v3.sh` (terbanyak:
  `changes-log.md` 29×, `PROGRESS.md` 16×, `HANDOFF.md` 11×).
- **Ada pipeline yang sedang berjalan** saat plan ini ditulis (PID 314580,
  `run_pipeline_v3.sh --fresh`, stage 1 spotting, ±32 menit).

Belum dijalankan: pemindahan file apa pun, `py_compile`, atau `--dry-run`.
Eksekusi menunggu plan disetujui dan run yang sedang jalan selesai.

## Known Notes

- **Run yang sedang berjalan memblokir eksekusi.** Memindahkan file sekarang
  akan memutus proses yang memanggil `scripts/process_spotting_pipeline.py`.
  Refactor harus dijalankan setelah run itu selesai.
- **Rename modul adalah bagian paling berisiko** karena menyentuh impor di
  banyak file. Karena itu dipisah menjadi issue sendiri (severity medium) supaya
  bisa ditunda tanpa menghalangi tujuan utama (stage terpisah & ketemu).
- **Isu `output/` vs `outputs/` kecil.** `outputs/` cuma berisi satu file model
  dlib; pindah ke `models/` sudah cukup. Mengganti nama `output/` → `runs/`
  opsional karena folder itu gitignored dan berisi 13 GB data.
- **Git state sudah berantakan sebelum refactor ini** (416 untracked, 32
  deleted, 44 modified; ada file tracked yang sudah dihapus dari working tree
  seperti `conv1.ipynb`, `core/`, `preprocess-anxiety`, `Super-Refine`). Ini
  bukan bagian dari refactor ini dan tidak akan disentuh — hanya dicatat supaya
  tidak tertukar dengan perubahan refactor.
- **Tidak ada commit/push** tanpa perintah Khalid.
