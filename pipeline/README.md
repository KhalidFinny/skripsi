# pipeline/ — peta pipeline

**Mulai dari sini.**

```bash
./pipeline/run.sh              # semua stage, dari awal
./pipeline/run.sh --dry-run    # lihat rencana saja, tanpa menjalankan
```

Pipeline mengalir satu arah: **video mentah → spotting/apex → fitur → gerbang →
training → hasil**. Gagal di satu stage = berhenti di situ.

---

## Stage

| # | Stage | Skrip | Input | Output |
|---|---|---|---|---|
| 0 | **SPLIT** per orang | `stages/stage_0_presplit.py` | nama folder peserta | `output/presplit/{split.csv,train_persons.txt,test_persons.txt}` |
| 1 | **SPOTTING / APEX** | `stages/stage_1_spotting.py` | video `.avi` mentah | `output/apex_v2/dataset/` + `metadata.xlsx` |
| 2 | **EKSTRAKSI FITUR** POC-ABS | `stages/stage_2_extract_features.py` | klip hasil stage 1 | `experiments/features/apex/*.xlsx` |
| 3 | **CACHE** pkl | `stages/stage_3_cache.py` | xlsx stage 2 | `*.pkl` (baca <1s) |
| 4 | **FITUR TEMPORAL** | `stages/stage_4_temporal.py` | pkl stage 3 | `*_poc_temporal_rise.pkl` |
| 5 | **GERBANG** within-subject | `stages/stage_5_gate.py` | fitur stage 3 & 4 | `output/training/within_subject_*/` |
| 6 | **TRAINING** LOSO TabR | `stages/stage_6_train_loso.py` | fitur temporal | `third_party/.../exp/tabr/<dataset>/fold_*/` |
| 7 | **HASIL** + baseline | `stages/stage_7_collect.py`, `stages/stage_7_baseline.py` | fold hasil stage 6 | `output/training/<dataset>/summary.md` |
| 8 | **HOLDOUT** 12 orang | `stages/stage_8_holdout_combine.py` | tabel train + holdout | `<dataset>_holdout/summary.md` |

Stage 0 dan 8 **hanya jalan di mode fold-first** (`V3_PRESPLIT=1`).

---

## Mau lihat apa? Ke mana

| Pertanyaan | Jawaban |
|---|---|
| Titik masuk pipeline | `pipeline/run.sh` |
| **Split** train/test per orang | `stages/stage_0_presplit.py` |
| **Spotting** / cari event | `stages/stage_1_spotting.py` |
| **Apex** (deteksi puncak ekspresi) | `apex/` — dipakai stage 1 |
| **Ekstraksi fitur** POC-ABS | `stages/stage_2_extract_features.py` |
| Definisi **ROI** (mata-alis, mulut) | `features/roi_config.py` — satu-satunya sumber kebenaran |
| POC, kuadran, vektor, geometri | `features/` |
| **Model TabR** | `tabr/` |
| Konfigurasi training | `experiments/configs/*.toml` |
| **Training** LOSO | `stages/stage_6_train_loso.py` |
| **Evaluasi holdout** | `stages/stage_8_holdout_combine.py` |
| **Pakai model** (prediksi) | `serve/predict.py` |
| Latih model final | `serve/train_final.py` |
| Konfigurasi spotting | `spotting_config.py` |
| Bootstrap impor | `paths.py` |
| Eksperimen CAS(ME)² | `research/casme2/` |
| Audit umum | `research/audits/` |
| Kode lama (tidak dipakai) | `legacy/` |
| Bobot model (dlib) | `models/` |
| Hasil run | `output/` |

---

## Perintah

| Perintah | Artinya |
|---|---|
| `./pipeline/run.sh` | semua stage dari awal |
| `./pipeline/run.sh --fresh` | hapus output dulu, lalu jalan dari nol |
| `./pipeline/run.sh --from 2` | lanjut dari stage 2 |
| `./pipeline/run.sh --stage 6` | hanya stage 6 |
| `./pipeline/run.sh --force` | jalankan ulang walau output sudah ada |
| `./pipeline/run.sh --pause` | konfirmasi sebelum tiap stage |
| `./pipeline/run.sh --dry-run` | cetak rencana saja |
| `./pipeline/run.sh --no-gate` | lewati stage 5 |
| `./pipeline/run.sh --no-train` | berhenti setelah stage 5 |
| `./pipeline/run.sh --config <toml>` | pakai konfigurasi training lain |

Pintasan: `./run pipeline [args...]`, `./run loso`, `./run collect`,
`./run features`, `./run temporal`, `./run baseline`, `./run desk`.

### Mode fold-first (8 stage)

```bash
V3_PRESPLIT=1 ./pipeline/run.sh --fresh
```

Split per orang terjadi **sebelum** spotting. 44 orang jadi train pool, 12 orang
holdout **tidak dibaca** sampai stage 8.

### Env yang sering dipakai

| Env | Fungsi | Default |
|---|---|---|
| `V3_PRESPLIT` | aktifkan mode fold-first | `0` |
| `V3_EXTRA_CONFIGS` | config tambahan, satu run banyak config | – |
| `V3_SPOT_SIGNAL` | sinyal spotting: `mean_m`, `combo`, `mdmd`, `hpoc` | `mean_m` |
| `V3_SPOT_MOTION_COMP` | buang gerakan kepala/latar yang serentak | `0` |
| `V3_SPOT_MDMD` / `V3_SPOT_MDMD_K` | lever MDMD + jendelanya | `0` / `5` |
| `V3_TEST_PEOPLE` | jumlah orang holdout | `12` |
| `V3_PRESPLIT_SEED` | seed split | `42` |
| `V3_OUT_ROOT` | lokasi output klip | `output/apex_v2` |
| `V3_FEAT_TAG` | tag nama tabel fitur | `poc_abs_roi_signals_v3` |
| `LOSO_DATASET` | nama dataset/hasil | `convat_apex_anxiety_loso_roi25_reg` |
| `SPOT_PREDICTOR` | path model dlib | `models/shape_predictor_68_face_landmarks.dat` |

Contoh run lengkap:

```bash
V3_PRESPLIT=1 V3_SPOT_MOTION_COMP=1 V3_SPOT_SIGNAL=mdmd \
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
  ./pipeline/run.sh --fresh
```

---

## Jalankan satu stage langsung

Setiap stage bisa dijalankan sendiri:

```bash
.venv/bin/python pipeline/stages/stage_3_cache.py --help
.venv/bin/python pipeline/stages/stage_6_train_loso.py --dataset <nama> --features <pkl>
```

Catatan: stage 1 dan 2 **tidak punya `--help`** — keduanya langsung menjalankan
`main()` dan membaca konfigurasi dari env (`SPOT_DATASET_ROOT`,
`FEAT_DATASET_ROOT`). Jalankan lewat `run.sh` atau set env-nya dulu.

---

## Struktur

```
pipeline/
  README.md            ← dokumen ini
  run.sh               titik masuk
  paths.py             satu tempat yang tahu root repo
  spotting_config.py   SpottingConfig
  registry.json        definisi pipeline untuk Pipeline Desk (desktop)
  stages/              stage 0-8 (bernomor = urutan)
  serve/               train_final.py, predict.py
apex/                  deteksi apex
features/              POC, kuadran, vektor, geometri, roi_config
tabr/                  model TabR
shared/                config + roi + helper
research/              eksperimen CAS(ME)² + audit
legacy/                kode lama (lihat legacy/README.md)
models/                bobot model
output/                hasil run (gitignored)
```
