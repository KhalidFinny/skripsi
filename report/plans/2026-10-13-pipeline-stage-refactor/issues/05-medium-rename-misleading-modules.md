# 05 — Rename modul yang menyesatkan (medium)

## Current Problem

Tiga nama modul tidak menggambarkan isinya, dan satu file bernama seolah-olah
pipeline padahal bukan. Ini sumber utama kebingungan saat mencari.

**1. `comparasion/` terdengar seperti folder eksperimen, padahal dipakai produksi.**
`extract_features_poc_abs.py` (stage 2, kode hidup) mengimpor:

```python
from comparasion.core.config import ComparisonConfig
from comparasion.core.roi import ROIExtractor
```

Jadi `comparasion/core/` bukan kode perbandingan — ia menyimpan **konfigurasi
bersama + ekstraktor ROI**. Sementara `comparasion/main.py` dan
`comparasion/notebooks/` memang entry point lama (→ pindah ke `legacy/`,
lihat issue 04).

**2. `scripts/spotting.py` bukan pipeline spotting.** Isinya hanya dataclass
`SpottingConfig` (52 baris). Pipeline spotting sebenarnya
`process_spotting_pipeline.py` (1089 baris). Diimpor oleh stage 1:

```python
from spotting import SpottingConfig
```

Impor `from spotting import ...` ini juga rapuh: bergantung pada `scripts/`
yang ada di `sys.path`.

**3. `src/` tidak memberi petunjuk apa pun.** Isinya model TabR:

```
src/TabR.py             model utama
src/data_module.py      LightningDataModule
src/encoder.py
src/value_correction.py
```

**4. `features_extraction/` panjang dan tidak konsisten** dengan folder lain
(`apex/`, `src/`).

## Target

| Sekarang | Sesudah | Alasan |
|---|---|---|
| `comparasion/core/config.py` | `shared/config.py` | ini konfigurasi bersama, bukan perbandingan |
| `comparasion/core/roi.py` | `shared/roi.py` | ekstraktor ROI yang dipakai stage 2 |
| `comparasion/core/{dataset,models,pipeline,tabular}.py` | `legacy/` | sisa kode perbandingan lama |
| `scripts/spotting.py` | `pipeline/spotting_config.py` | namanya konfigurasi, bukan pipeline |
| `src/` | `tabr/` | isinya model TabR |
| `features_extraction/` | `features/` | lebih pendek, konsisten |

Hasil akhir modul pendukung:

```
apex/       deteksi apex
features/   poc, quadran, vektor, geometry, roi_config
tabr/       model TabR
shared/     config + roi
```

## Required Design

- **Rename harus lengkap.** Setiap lokasi impor ikut diperbarui, termasuk yang
  ada di dalam modul lain:
  - `comparasion/core/roi.py` mengimpor `from comparasion.core.config import ...`
  - `comparasion/core/config.py` mengimpor
    `from features_extraction.roi_config import ...`
  - `features_extraction/roi_config.py` menyebut `comparasion/core/config.py`
    di docstring — perbarui komentarnya supaya tidak menunjuk path mati.
- Import site yang terverifikasi dan wajib diperbarui:
  - `features_extraction` → stage 2, `build_temporal_features.py`, semua skrip
    `research/casme2/`, `shared/config.py`
  - `comparasion.core.config` / `.roi` → stage 2, `legacy/extract_features_roi.py`
  - `src` → `pipeline/serve/train_final.py`, `pipeline/serve/predict.py`,
    `legacy/run_loso_lit_tabr.py`
  - `spotting` → stage 1
- `features_extraction/roi_config.py` **tetap satu-satunya sumber kebenaran**
  ROI / `TARGET_SIZE` / `BLOCK_SIZE`. Jangan gandakan definisinya di tempat lain.
- **Tidak ada penambahan `try/except ImportError` atau fallback impor** untuk
  menutupi path lama. Ganti impornya, bukan ditambal.
- Rename ini **boleh ditunda** tanpa menghalangi tujuan utama (issue 01–02).
  Kalau Khalid ingin cepat, lewati issue ini dulu.

## Tests

- `.venv/bin/python -m py_compile` untuk semua file yang impornya berubah.
- `.venv/bin/python -c "from shared.config import ComparisonConfig; from tabr import TabR; from features.roi_config import REGIONS; print('ok')"`
- `grep -rn "features_extraction\|comparasion\.core\|from src\b\|from spotting import" --include=*.py .`
  harus kosong di luar `legacy/`.
- `.venv/bin/python pipeline/stages/1_spotting.py --help` dan
  `pipeline/stages/2_extract_poc_abs.py --help` (membuktikan impor baru resolve).

## Done Criteria

- [ ] `shared/` ada berisi `config.py` + `roi.py`; tidak ada `comparasion/` di jalur hidup
- [ ] `tabr/` ada berisi model TabR; tidak ada `src/` di jalur hidup
- [ ] `features/` ada; tidak ada `features_extraction/` di jalur hidup
- [ ] `pipeline/spotting_config.py` ada; tidak ada `scripts/spotting.py`
- [ ] Semua import site diperbarui (grep bersih di luar `legacy/`)
- [ ] Tidak ada `try/except ImportError` yang ditambahkan
- [ ] Definisi ROI tetap hanya di satu tempat
- [ ] `py_compile` bersih dan `--help` stage jalan
