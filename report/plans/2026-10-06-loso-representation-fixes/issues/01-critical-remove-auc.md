# 01 — Hapus AUC dari pipeline

**Severity:** critical

## Current Problem

AUC bukan bagian protokol asli; ia masuk lewat rencana (Iterasi 3.8) dan
sejak itu menempel di kode dan laporan:

- `third_party/tabular-dl-tabr-official/lib/metrics.py:74-84` — menghitung
  `roc-auc` untuk binclass, plus patch lokal `float('nan')` agar LOSO tidak
  crash.
- `third_party/tabular-dl-tabr-official/lib/data.py:26` — `'roc-auc': True`
  di tabel metrik score.
- `scripts/collect_loso_results.py:27,103,116,243,256,280,281` — kolom
  `subject_roc_auc`, `frame_roc_auc`, dan baris AUC di `summary.md`.
- `scripts/run_loso.py:59-61,177-190` — `PATCH_MARKER`, `check_tabtr_patch()`,
  dan pesan split yang beralasan AUC.
- `experiments/configs/tabr_loso_roi25*.toml` — komentar yang menjelaskan AUC.

## Target

Tidak ada lagi `roc-auc`/`roc_auc` di kode proyek maupun di `report.json`.
Metrik pemilihan epoch tetap default TabR (accuracy). Patch lokal di
`lib/metrics.py` ikut hilang karena tidak ada lagi `roc_auc_score` yang
dipanggil untuk test satu kelas.

## Required Design

- Hapus seluruh blok `if task_type == TaskType.BINCLASS and probs is not None:`
  di `metrics.py` (baris 74-84), termasuk patch lokal. `cross-entropy` tetap.
- Hapus `'roc-auc': True` dari `data.py`; cek tidak ada kode lain yang
  mengasumsikan key itu ada.
- Di `collect_loso_results.py`: buang `roc_auc` dari `subject_metrics()` dan
  `frame_metrics()`, buang baris AUC di `summary.md` dan kolomnya di
  `summary.csv`, buang `roc_auc_score` dari import.
- Di `run_loso.py`: buang `PATCH_MARKER`, `PATCHED_FILE`, `check_tabtr_patch()`
  dan pemanggilannya; perbarui pesan split (alasan: val harus memuat 2 kelas
  supaya early stopping bermakna, bukan karena AUC).
- Perbarui komentar config agar tidak menyebut AUC.
- Tabel fitur lama tidak disentuh.

## Tests

- `grep -rn "roc.auc\|roc_auc" scripts/ experiments/configs/` → kosong.
- `grep -rn "roc-auc" third_party/tabular-dl-tabr-official/lib` → kosong.
- Parse AST semua file yang diubah.
- `collect_loso_results.py --exp convat_apex_anxiety_loso_roi25` selesai dan
  `summary.md` tanpa kata AUC.

## Done Criteria

- [ ] `metrics.py` tidak menghitung `roc-auc`.
- [ ] `data.py` tidak mencantumkan `roc-auc`.
- [ ] `collect_loso_results.py` tanpa AUC.
- [ ] `run_loso.py` tanpa `check_tabtr_patch`.
- [ ] Config tidak menyebut AUC.
