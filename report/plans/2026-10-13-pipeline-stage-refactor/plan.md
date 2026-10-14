# Plan — Refactor pipeline: stage terpisah + struktur folder jelas

> **Status:** SELESAI (2026-10-14). `scripts/` hilang, pipeline di `pipeline/`,
> eksperimen di `research/`, legacy di `legacy/`, model di `models/`.
> Verifikasi: dry-run 7 stage + fold-first 8 stage, `py_compile` bersih,
> semua stage impor resolve. **Belum di-commit** (menunggu perintah).

- **Goal:** pipeline punya satu folder, stage bernomor yang jelas urutannya, dan setiap bagian (split / spotting / apex / fitur / training) bisa ditemukan tanpa hafal nama file.
- **Architecture:** `pipeline/run.sh` (titik masuk) → `pipeline/stages/0..8_*.py` (stage bernomor) → library (`apex/`, `features/`, `tabr/`, `shared/`). Eksperimen ke `research/`, kode lama ke `legacy/`.
- **Tech Stack:** bash (runner) + Python 3.12 (stage), venv `.venv`.

## Must Not Forget

- **JANGAN jalankan apa pun yang memindahkan file selama pipeline masih berjalan.** Cek dulu: `ps -eo pid,args | grep run_pipeline`. Refactor hanya boleh mulai setelah proses itu selesai.
- **Tidak mengubah logika pipeline.** Semua angka harus tetap identik. Yang berubah hanya lokasi, nama, dan penanda stage.
- **Setiap skrip yang dipindah wajib memperbaiki `ROOT`.** Pola sekarang `Path(__file__).resolve().parent.parent`; setelah pindah ke `pipeline/stages/` harus jadi `parents[2]`. Kalau tidak, `from apex import ...`, `from features_extraction ...`, dan `from comparasion.core.config import ...` gagal.
- **Nomor stage tetap 0–8** dan artinya tidak berubah. Jangan renumber.
- **Env var tidak berubah:** `V3_PRESPLIT`, `V3_SPOT_SIGNAL`, `V3_SPOT_MOTION_COMP`, `V3_SPOT_MDMD`, `V3_SPOT_MDMD_K`, `V3_EXTRA_CONFIGS`, `V3_TEST_PEOPLE`, `V3_PRESPLIT_SEED`, `LOSO_DATASET`, `V3_OUT_ROOT`, `V3_FEAT_TAG`.
- **`features_extraction/roi_config.py` tetap satu-satunya sumber kebenaran ROI.** Jangan gandakan definisi ROI/TARGET_SIZE/BLOCK_SIZE.
- **Tidak menjalankan test / e2e / run pipeline penuh.** Verifikasi = `py_compile` + `bash -n` + `--dry-run`. Run penuh dijalankan Khalid.
- **Tidak commit, tidak push, tidak hapus data non-disposable.** `output/` berisi 13 GB hasil run; jangan dihapus.
- **Jangan sentuh git state yang sudah berantakan sebelum refactor** (file tracked yang sudah dihapus seperti `conv1.ipynb`, `core/`, `preprocess-anxiety`, `Super-Refine`). Itu di luar lingkup.
- **Pertahankan nama Indonesia yang sudah dipakai** di banner/log stage dan dokumen (`report/documentation/*.md`).

## Issue Index

### Critical
- [01 — Paket `pipeline/` + titik masuk + peta stage](issues/01-critical-pipeline-package.md)
- [02 — Pindahkan 10 stage + perbaikan bootstrap `ROOT`](issues/02-critical-stage-move-bootstrap.md)

### High
- [03 — Pisahkan eksperimen CAS(ME)² dari pipeline](issues/03-high-experiments-separation.md)
- [04 — Karantina kode legacy](issues/04-high-legacy-quarantine.md)

### Medium
- [05 — Rename modul yang menyesatkan](issues/05-medium-rename-misleading-modules.md)
- [06 — Rapikan folder data hasil (`outputs/` → `models/`)](issues/06-medium-generated-data-dirs.md)

### Low
- [07 — Sinkronkan dokumen & semua perintah run](issues/07-low-docs-commands-sync.md)

## Target Architecture

```
pipeline/
  README.md            peta stage: "mulai dari sini"
  run.sh               satu titik masuk (was scripts/run_pipeline_v3.sh)
  spotting_config.py   was scripts/spotting.py (SpottingConfig)
  paths.py             satu tempat yang tahu root repo (bootstrap impor)
  configs/             was experiments/configs/*.toml
  stages/
    0_presplit.py      SPLIT per orang, sebelum spotting
    1_spotting.py      SPOTTING / cari apex
    2_extract_poc_abs.py
    3_cache.py
    4_temporal.py
    5_gate.py
    6_train_loso.py
    7_collect.py
    7_baseline.py
    8_holdout_combine.py
  serve/
    train_final.py
    predict.py

apex/                  deteksi apex (ApexPhase, ApexSmoother, Visualizer)
features/              was features_extraction/
tabr/                  was src/
shared/                was comparasion/core/ (config + roi)

research/
  casme2/              26 skrip eksperimen CAS(ME)²
  audits/              4 audit umum
  README.md            skrip -> dokumen temuan

legacy/                runner & skrip yang sudah digantikan (17 file)
  runners/ official_tabr/ export/ methods/ tools/ notebooks/
  README.md            file -> penggantinya

models/                bobot model (dlib .dat)
output/                hasil run (13+ GB, gitignored) — nama dipertahankan
```

**`scripts/` hilang sepenuhnya.** 61 file di dalamnya habis terbagi:

| Tujuan | Jumlah |
|---|---|
| `pipeline/stages/` | 10 |
| `pipeline/serve/` | 2 |
| `pipeline/run.sh` + `pipeline/spotting_config.py` | 2 |
| `research/casme2/` | 26 |
| `research/audits/` | 4 |
| `legacy/` | 17 |
| **total** | **61** |

Pemetaan pertanyaan → lokasi, sesudah refactor:

| Pertanyaan | Jawaban |
|---|---|
| Di mana titik masuknya? | `pipeline/run.sh` |
| Di mana **split**-nya? | `pipeline/stages/0_presplit.py` |
| Di mana **spotting**-nya? | `pipeline/stages/1_spotting.py` |
| Di mana **apex**-nya? | `apex/` (dipakai stage 1) |
| Di mana ekstraksi **fitur**? | `pipeline/stages/2_extract_poc_abs.py` + `features/` |
| Di mana **ROI** didefinisikan? | `features/roi_config.py` |
| Di mana **training**-nya? | `pipeline/stages/6_train_loso.py` |
| Di mana **evaluasi holdout**? | `pipeline/stages/8_holdout_combine.py` |
| Di mana **pakai model**-nya? | `pipeline/serve/predict.py` |
| Di mana konfigurasi training? | `pipeline/configs/*.toml` |
| Di mana eksperimen CAS(ME)²? | `research/casme2/` |
| Di mana kode lama? | `legacy/` |
| Di mana bobot model? | `models/` |
| Di mana hasil run? | `output/` |

## Priority Order

1. **01 → 02** — paket `pipeline/` + pindahkan stage + perbaikan `ROOT`. Ini inti permintaan Khalid; setelah dua ini selesai, pipeline sudah ketemu dan stage sudah jelas.
2. **03 → 04** — bersihkan `scripts/` dari eksperimen dan legacy, supaya yang tersisa hanya yang relevan.
3. **05 → 06** — rename modul menyesatkan dan rapikan folder data.
4. **07** — sinkronkan dokumen dan perintah.

Kalau Khalid ingin berhenti lebih awal, **setelah 02 pipeline sudah layak dipakai dan didemokan.**

## Validation Commands

```bash
# 0. pastikan tidak ada pipeline berjalan
ps -eo pid,args | grep -E "run_pipeline|process_spotting|run_loso" | grep -v grep

# 1. semua file yang dipindah lolos kompilasi
.venv/bin/python -m py_compile pipeline/stages/*.py pipeline/serve/*.py

# 2. runner tidak salah sintaks
bash -n pipeline/run.sh

# 3. urutan stage benar (default = 7 stage, tanpa presplit)
./pipeline/run.sh --dry-run

# 4. mode fold-first = 8 stage + holdout
V3_PRESPLIT=1 ./pipeline/run.sh --dry-run

# 5. tidak ada referensi path lama yang tertinggal
grep -rn "scripts/run_pipeline_v3\|scripts/process_spotting_pipeline\|scripts/extract_features_poc_abs\|scripts/run_loso.py" \
  --include=*.py --include=*.sh --include=*.md . | grep -v __pycache__ | grep -v "^./legacy/"

# 6. impor library masih sehat dari root
.venv/bin/python -c "from apex import ApexPhase; from features_extraction.poc import POC; print('ok')"
```

## Rollout Plan

- [x] **Tunggu run yang sedang berjalan selesai** — sudah selesai sebelum eksekusi.
- [x] 01 — buat `pipeline/`, `run.sh`, `paths.py`, `README.md` (peta stage)
- [x] 02 — pindahkan 10 stage + perbaiki `ROOT` (`parents[2]`) + `py_compile`
- [x] 02 — `bash -n` + `--dry-run` (default 7 stage, `V3_PRESPLIT=1` 8 stage)
- [x] 03 — pindahkan 27 skrip CAS(ME)² → `research/casme2/`, 4 audit → `research/audits/`
- [x] 04 — pindahkan 17 file legacy → `legacy/` (+ `legacy/README.md`)
- [x] 05 — rename `comparasion/`→`shared/` (+ `legacy/comparasion/`), `src/`→`tabr/`, `features_extraction/`→`features/`, `spotting.py`→`pipeline/spotting_config.py`, `helper/`→`shared/helper.py`
- [x] 06 — `outputs/models/` → `models/` (semua referensi kode diperbarui)
- [x] 07 — sinkronkan `PROGRESS.md`, `HANDOFF.md`, `ringkasan.md`, `pipeline.md`; penunjuk di dokumen historis
- [x] Hapus `scripts/` (kosong setelah semua file punya rumah baru)
- [x] Perbaiki `./run` (pintasan) + `pipeline/registry.json` (dipakai Pipeline Desk)
- [x] Bersihkan: 3 dir kosong, 4 log kosong, `desktop/pipelinedesk/.amp`
- [x] Kelompokkan `notebooks/` → `preprocess/ spotting/ export/ tabr/ legacy/` (30 notebook, tidak ada yang dihapus)

**Tidak dilakukan (sengaja):** `experiments/configs/` **tidak** dipindah ke
`pipeline/configs/`. Alasannya: 660 referensi, dan ±645 di antaranya ada di
`third_party/.../DONE.json` — catatan permanen run training terakhir yang
merekam config apa yang dipakai. Memindahkannya akan membuat provenance hasil
training jadi tidak konsisten, demi keuntungan yang kecil. Configs tetap di
`experiments/configs/` dan didokumentasikan di `pipeline/README.md`.

## Done Criteria

- [x] `./pipeline/run.sh --dry-run` mencetak 7 stage berurutan dengan path yang benar
- [x] `V3_PRESPLIT=1 ./pipeline/run.sh --dry-run` mencetak 8 stage (0–8)
- [x] `py_compile` bersih untuk semua stage yang dipindah
- [x] `scripts/` sudah tidak ada (61 file punya rumah baru)
- [x] `pipeline/README.md` menjawab "di mana split / spotting / apex / training" dalam satu layar
- [x] Tidak ada referensi path lama di kode hidup (`grep` bersih di luar `legacy/` dan dokumen historis)
- [ ] Tidak ada angka pipeline yang berubah (dibuktikan Khalid saat run berikutnya)
- [ ] Di-commit (menunggu perintah Khalid)
