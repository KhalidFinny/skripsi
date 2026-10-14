# 02 — Pindahkan 10 stage + perbaikan bootstrap `ROOT` (critical)

## Current Problem

Stage pipeline tersebar di `scripts/` dengan nama yang tidak menunjukkan urutan:

| Stage sekarang | Skrip sekarang | Baris |
|---|---|---|
| 0 PRE-SPLIT | `scripts/split_persons_presplit.py` | 189 |
| 1 SPOTTING | `scripts/process_spotting_pipeline.py` | 1089 |
| 2 EKSTRAKSI FITUR | `scripts/extract_features_poc_abs.py` | 724 |
| 3 CACHE PKL | `scripts/build_feature_cache.py` | 65 |
| 4 FITUR TEMPORAL | `scripts/build_temporal_features.py` | 193 |
| 5 GERBANG | `scripts/within_subject_test.py` | 458 |
| 6 TRAINING LOSO | `scripts/run_loso.py` | 829 |
| 7 HASIL + BASELINE | `scripts/collect_loso_results.py` (595) + `scripts/run_loso_baseline.py` (249) | |
| 8 HOLDOUT | `scripts/combine_feature_tables.py` (66) + `run_loso.py` | |

**Jebakan teknis yang wajib ditangani.** Setiap skrip stage mencari root repo
dari lokasi dirinya sendiri:

```python
ROOT = Path(__file__).resolve().parent.parent   # scripts/ -> repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

Setelah pindah ke `pipeline/stages/`, `parent.parent` menunjuk ke `pipeline/`,
bukan root repo. Akibatnya semua impor ini gagal:

- `from apex import ApexPhase, ApexSmoother, ApexPhaseVisualizer`
- `from features_extraction.poc import POC` (dan `quadran`, `vektor`, `geometry`)
- `from comparasion.core.config import ComparisonConfig`
- `from spotting import SpottingConfig`
- `from src...` (di `train_final_model.py`, `predict.py`)

Terverifikasi: `process_spotting_pipeline.py:34`, `extract_features_poc_abs.py:32`,
`build_temporal_features.py:41`, `run_loso.py:48`, `within_subject_test.py:42`
semuanya memakai pola `parent.parent`.

## Target

Pindahkan ke `pipeline/stages/` dengan nama bernomor:

```
scripts/split_persons_presplit.py        -> pipeline/stages/0_presplit.py
scripts/process_spotting_pipeline.py     -> pipeline/stages/1_spotting.py
scripts/extract_features_poc_abs.py      -> pipeline/stages/2_extract_poc_abs.py
scripts/build_feature_cache.py           -> pipeline/stages/3_cache.py
scripts/build_temporal_features.py       -> pipeline/stages/4_temporal.py
scripts/within_subject_test.py           -> pipeline/stages/5_gate.py
scripts/run_loso.py                      -> pipeline/stages/6_train_loso.py
scripts/collect_loso_results.py          -> pipeline/stages/7_collect.py
scripts/run_loso_baseline.py             -> pipeline/stages/7_baseline.py
scripts/combine_feature_tables.py        -> pipeline/stages/8_holdout_combine.py
```

Perbaikan bootstrap: satu helper bersama, bukan salinan `parents[2]` di 10 file.

```python
# pipeline/paths.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # pipeline/ -> repo root

def ensure_on_path() -> None:
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
```

Tiap stage memakai:

```python
from pipeline.paths import ROOT, ensure_on_path
ensure_on_path()
```

Ini contoh sah dari aturan dev-tendencies "satu komponen dipakai bersama": ada
10 pemakai nyata, bukan spekulasi.

`run.sh` juga harus memperbarui semua path stage yang dipanggil, dan tetap
`cd` ke root repo sebelum menjalankan stage.

## Required Design

- **Nama stage di log dan banner tetap bahasa Indonesia** seperti sekarang
  ("SPOTTING (cari apex/event)", dst). Hanya nama file yang berubah.
- Nomor stage tidak berubah (0–8).
- `pipeline/paths.py` adalah satu-satunya tempat yang tahu root repo.
- Setiap stage tetap bisa dijalankan langsung (mis.
  `.venv/bin/python pipeline/stages/1_spotting.py --help`) tanpa bergantung pada
  cwd.
- Path output default (mis. `output/apex_v2`, `experiments/features/...`) tidak
  berubah supaya hasil run lama tetap ketemu.
- Jangan ubah argumen CLI tiap stage.

## Tests

- `.venv/bin/python -m py_compile pipeline/stages/*.py pipeline/paths.py`
- `bash -n pipeline/run.sh`
- `./pipeline/run.sh --dry-run` dan `V3_PRESPLIT=1 ./pipeline/run.sh --dry-run`
- `.venv/bin/python pipeline/stages/1_spotting.py --help` (membuktikan impor
  `apex`/`features_extraction`/`spotting` masih resolve setelah pindah)
- `grep -rn "parent.parent" pipeline/stages/` harus kosong (sudah pakai helper)

## Done Criteria

- [ ] 10 skrip ada di `pipeline/stages/` dengan nama bernomor
- [ ] `pipeline/paths.py` ada dan dipakai semua stage
- [ ] `py_compile` bersih untuk semua stage
- [ ] `--help` tiap stage jalan (impor resolve)
- [ ] `--dry-run` (default + `V3_PRESPLIT=1`) mencetak path `pipeline/stages/...`
- [ ] Tidak ada `parent.parent` tersisa di `pipeline/stages/`
- [ ] Argumen CLI dan env var tiap stage tidak berubah
