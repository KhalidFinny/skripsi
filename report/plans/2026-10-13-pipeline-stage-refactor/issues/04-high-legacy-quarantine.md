# 04 — Karantina kode legacy (high)

## Current Problem

`scripts/` masih menyimpan runner dan skrip yang **sudah digantikan**, tanpa
penanda apa pun bahwa itu lama. Contoh paling membingungkan: ada **dua runner
pipeline**, `run_pipeline.sh` (v1, 303 baris) dan `run_pipeline_v3.sh` (737
baris). Dari nama saja tidak jelas mana yang dipakai sekarang.

Terverifikasi 17 file legacy:

**Runner lama (3):**
- `run_pipeline.sh` — versi 1; hanya dirujuk oleh dokumen lama
  (`report/documentation/pipeline.md`, `progress.md`). Sudah digantikan
  `run_pipeline_v3.sh`.
- `run_all_variants.sh` (66 baris), `run_loso_ab.sh` (38 baris) — runner A/B
  lama.

**Runner tuning TabR resmi (6):**
- `run_official_tabr_v25.sh`, `_v25_final.sh`, `_v25_finetune_8h.sh`,
  `_v25_tuning.sh`, `_overnight_8h.sh`, `_scaling_freeze_8h.sh`
  (0–1 rujukan; hanya saling memanggil satu sama lain).

**Ekspor dataset lama (3):**
- `export_to_official_tabr_dataset.py`, `_qholdout.py`, `_qwalkforward.py`

**Jalur metode lama (2):**
- `run_loso_lit_tabr.py` (408 baris) — jalur LitTabR "metode asli"; hasilnya
  41,07% level subjek, sudah kalah dari TabR resmi.
- `extract_features_roi.py` (450 baris) — mode 3-region lama, sebelum
  `features_extraction/roi_config.py` jadi sumber kebenaran.

**Tool lama (2):**
- `collect_training_results.py` (127 baris) — kolektor lama untuk
  `third_party/.../exp/tabr`; digantikan `collect_loso_results.py`.
- `switch_spotting_config.py` (82 baris) — pengalih konfigurasi spotting lama.

**Tool pendukung runner v1 (1):**
- `save_neutral_references.py` (166 baris) — hanya dipanggil oleh
  `run_pipeline.sh` (v1). Pipeline v3 menyimpan `neutral.png` sendiri di dalam
  `process_spotting_pipeline.py`, jadi skrip ini ikut legacy.

**Kode non-pipeline yang juga usang:**
- `notebooks/` — notebook lama (`export_apex_tabr_train_test_v*.ipynb`, dll).
- `comparasion/main.py` dan `comparasion/notebooks/` — entry point lama;
  `comparasion/core/` tetap hidup (lihat issue 05).

## Target

```
legacy/
  README.md              kenapa tiap file ada di sini + penggantinya
  runners/               run_pipeline.sh, run_all_variants.sh, run_loso_ab.sh
  official_tabr/         6 runner run_official_tabr_*.sh
  export/                3 export_to_official_tabr_dataset*.py
  methods/               run_loso_lit_tabr.py, extract_features_roi.py
  tools/                 collect_training_results.py, switch_spotting_config.py,
                         save_neutral_references.py
  notebooks/             notebooks/ lama
```

`legacy/README.md` memuat tabel: file | digantikan oleh | tanggal/iterasi.

## Required Design

- **Tidak ada yang dihapus.** Legacy dipindah, bukan dibuang — masih berguna
  sebagai jejak sejarah dan bisa dipakai ulang kalau perlu.
- `legacy/` tidak boleh diimpor oleh kode hidup. Cek setelah pindah.
- `run_pipeline.sh` (v1) dipindah, **bukan dipertahankan sebagai shim**.
  Setelah issue 01, titik masuk tunggal adalah `pipeline/run.sh`, dan dokumen
  lama yang menyebut `run_pipeline.sh` diperbarui di issue 07.
- `notebooks/` hanya dipindah kalau tidak ada dokumen hidup yang masih
  merujuknya sebagai cara menjalankan sesuatu. Kalau ada, catat di README
  `legacy/` sebagai "masih dirujuk oleh <dokumen>".
- Jangan menyentuh `third_party/` (itu kode pihak ketiga, bukan legacy kita).

## Tests

- `ls scripts/` tidak lagi memuat nama legacy mana pun.
- `grep -rn "run_official_tabr\|run_all_variants\|run_loso_ab\|collect_training_results\|switch_spotting_config" --include=*.sh --include=*.py .`
  bersih di luar `legacy/`.
- `bash -n legacy/runners/*.sh` (sintaks tetap sehat setelah pindah).
- `.venv/bin/python -m py_compile legacy/**/*.py` untuk file yang masih Python.

## Done Criteria

- [ ] 17 file legacy ada di `legacy/` dengan subfolder yang rapi
- [ ] `legacy/README.md` ada dengan tabel pengganti
- [ ] `scripts/` tidak lagi memuat runner lama maupun skrip legacy
- [ ] Tidak ada kode hidup yang mengimpor `legacy/`
- [ ] Tidak ada file yang terhapus
