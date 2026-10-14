# legacy/ — kode yang sudah digantikan

Isi folder ini **bukan** jalur pipeline yang dipakai sekarang. Semuanya
disimpan sebagai jejak sejarah dan bahan rujukan, bukan untuk dijalankan
sehari-hari.

**Penting:** skrip di sini masih menulis path **layout lama** (mis.
`scripts/extract_features_poc_abs.py`). Path itu sudah tidak ada sejak refactor
2026-10-13. Kalau perlu menjalankan sesuatu dari sini, perbaiki path-nya dulu
atau pakai padanan barunya di kolom "Digantikan oleh".

## Peta: file → penggantinya

### runners/
| File | Digantikan oleh |
|---|---|
| `run_pipeline.sh` | `pipeline/run.sh` (pipeline v3) |
| `run_all_variants.sh` | `pipeline/run.sh` + `V3_EXTRA_CONFIGS` |
| `run_loso_ab.sh` | `pipeline/run.sh` + `V3_EXTRA_CONFIGS` |

### official_tabr/
Runner tuning TabR resmi (Yandex) era v25. Digantikan oleh
`pipeline/stages/stage_6_train_loso.py` + `experiments/configs/*.toml`.

| File |
|---|
| `run_official_tabr_v25.sh` |
| `run_official_tabr_v25_final.sh` |
| `run_official_tabr_v25_finetune_8h.sh` |
| `run_official_tabr_v25_tuning.sh` |
| `run_official_tabr_overnight_8h.sh` |
| `run_official_tabr_scaling_freeze_8h.sh` |

### export/
Ekspor dataset ke format TabR resmi (versi lama).

| File | Digantikan oleh |
|---|---|
| `export_to_official_tabr_dataset.py` | `pipeline/stages/stage_6_train_loso.py` (ekspor internal) |
| `export_to_official_tabr_dataset_qholdout.py` | mode `V3_PRESPLIT=1` (stage 0 + stage 8) |
| `export_to_official_tabr_dataset_qwalkforward.py` | mode `V3_PRESPLIT=1` |

### methods/
Jalur metode lama yang sudah kalah bersaing.

| File | Kenapa legacy | Digantikan oleh |
|---|---|---|
| `run_loso_lit_tabr.py` | LitTabR kustom; hasil level subjek 41,07% (kalah dari TabR resmi) | `pipeline/stages/stage_6_train_loso.py` |
| `extract_features_roi.py` | mode 3-region lama, sebelum `features/roi_config.py` jadi sumber kebenaran | `pipeline/stages/stage_2_extract_features.py` |

### tools/
| File | Digantikan oleh |
|---|---|
| `collect_training_results.py` | `pipeline/stages/stage_7_collect.py` |
| `switch_spotting_config.py` | env `V3_SPOT_*` di `pipeline/run.sh` |
| `save_neutral_references.py` | `neutral.png` disimpan langsung oleh `pipeline/stages/stage_1_spotting.py` |

## Catatan

- Tidak ada file di sini yang dihapus. Kalau yakin tidak diperlukan lagi,
  hapus lewat keputusan terpisah, bukan diam-diam.
- Folder ini tidak boleh diimpor oleh kode hidup (`pipeline/`, `research/`).
