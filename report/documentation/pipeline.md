# Pipeline Map

> **Peta stage lengkap + semua perintah: `pipeline/README.md`.**
> Dokumen ini ringkasannya saja.

## Layout (sesudah refactor 2026-10-13)

| Path | Isi |
| --- | --- |
| `pipeline/` | **Pipeline utama.** `run.sh` (titik masuk), `stages/` (stage 0–8), `serve/` |
| `pipeline/stages/` | Stage bernomor: split → spotting → fitur → gerbang → training → hasil |
| `apex/` | Deteksi apex (`ApexPhase`, `ApexSmoother`, `ApexPhaseVisualizer`) |
| `features/` | POC, kuadran, vektor, geometri, `roi_config.py` (sumber kebenaran ROI) |
| `tabr/` | Model TabR (`TabR.py`, `data_module.py`, `encoder.py`) |
| `shared/` | `config.py`, `roi.py`, `helper.py` |
| `research/casme2/` | Eksperimen CAS(ME)² (audit/probe/diag) |
| `research/audits/` | Audit umum |
| `legacy/` | Kode lama yang sudah digantikan (lihat `legacy/README.md`) |
| `models/` | Bobot model dlib (`shape_predictor_68_face_landmarks.dat`) |
| `experiments/configs/` | Konfigurasi training TabR (`.toml`) |
| `experiments/features/apex/` | Tabel fitur (xlsx/pkl) — output stage 2–4, input training |
| `output/` | Artefak stage 1 (klip event, metadata) + hasil collect training |
| `third_party/tabular-dl-tabr-official/` | Repo TabR resmi (dipanggil, jangan diedit) |
| `notebooks/` | Eksplorasi, dikelompokkan: `preprocess/ spotting/ export/ tabr/ legacy/` |
| `desktop/` | Pipeline Desk (MyGo) — baca `pipeline/registry.json` |
| `report/` | Dokumentasi (findings, results, documentation, plans) |

## Pipeline utama (`./pipeline/run.sh`)

8 stage (7 tanpa mode fold-first):

| # | Stage | Skrip |
|---|---|---|
| 0 | split per orang | `stages/stage_0_presplit.py` |
| 1 | spotting / apex | `stages/stage_1_spotting.py` |
| 2 | ekstraksi fitur POC-ABS | `stages/stage_2_extract_features.py` |
| 3 | cache pkl | `stages/stage_3_cache.py` |
| 4 | fitur temporal | `stages/stage_4_temporal.py` |
| 5 | gerbang within-subject | `stages/stage_5_gate.py` |
| 6 | training LOSO TabR | `stages/stage_6_train_loso.py` |
| 7 | hasil + baseline | `stages/stage_7_collect.py`, `stages/stage_7_baseline.py` |
| 8 | evaluasi holdout | `stages/stage_8_holdout_combine.py` |

Flag: `--stage N`, `--from N`, `--force`, `--fresh`, `--dry-run`, `--pause`,
`--no-gate`, `--no-train`, `--config`, `--dataset`.

Mode fold-first: `V3_PRESPLIT=1 ./pipeline/run.sh --fresh`.

## Runner lain

- `legacy/runners/run_all_variants.sh` — ulang varian fitur (jalur lama)
- `legacy/export/export_to_official_tabr_dataset*.py` — ekspor tabel fitur → npy TabR (lama)
- `legacy/tools/switch_spotting_config.py` — editor config spotting manual (lama)
- `pipeline/stages/stage_6_train_loso.py --fold N --seeds 1` — smoke test satu fold
- `./run <cmd>` — pintasan (`pipeline`, `loso`, `collect`, `features`, `temporal`, `baseline`, `desk`)

## Model dlib

`models/shape_predictor_68_face_landmarks.dat`
(cara unduh: `report/documentation/before.md`). Override: env `SPOT_PREDICTOR`.

## Catatan sejarah

Sebelum 2026-10-13, pipeline hidup di `scripts/` (61 file bercampur antara stage,
eksperimen, dan kode legacy). Layout lama masih dirujuk di dokumen historis
(`report/findings/*`, `report/documentation/changes-log.md`, `PROGRESS.md`) dan
itu benar untuk zamannya. Perintah lamanya:

| Lama | Sekarang |
|---|---|
| `./scripts/run_pipeline_v3.sh` | `./pipeline/run.sh` |
| `./scripts/run_pipeline.sh` | `legacy/runners/run_pipeline.sh` (v1, tidak dipakai) |
| `scripts/run_loso.py` | `pipeline/stages/stage_6_train_loso.py` |
| `scripts/process_spotting_pipeline.py` | `pipeline/stages/stage_1_spotting.py` |
| `scripts/extract_features_poc_abs.py` | `pipeline/stages/stage_2_extract_features.py` |
| `features_extraction/` | `features/` |
| `src/` | `tabr/` |
| `comparasion/core/{config,roi}.py` | `shared/{config,roi}.py` |
| `outputs/models/` | `models/` |
