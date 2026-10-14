# Plan — Perbaikan Representasi & Protokol LOSO

> **Status:** Fase 1 selesai (kode + verifikasi statis) — 2026-10-06.
> Fase 2 (target 70%) direncanakan: issue 10–12.
>
> **KOREKSI:** catatan awal menyebut dataset mentah tidak ada di mesin ini.
> SALAH — dataset ada di `/run/media/finny/New Volume/dataset/`
> (`anxiety_raw` 56 subjek, `datatest` 49 subjek). Jadi issue 04 (baseline
> netral) BISA dijalankan di mesin ini, dan ada 49 subjek tambahan yang belum
> dipakai (56 → 105).
>
> Belum dijalankan (menunggu perintah user): re-run spotting/ekstraksi,
> training LOSO TabR, pipeline lengkap.
>
> Penyimpangan dari rencana awal (dicatat, disengaja):
> - `--subject-norm` jadi `{none,subject}`, bukan `{none,global,subject}`:
>   `global` = perilaku lama = `none`, jadi opsinya redundan.
> - Permutation test di issue 06 memakai **accuracy** level subjek, bukan
>   ROC-AUC: user meminta AUC dihapus dari pipeline, jadi tidak dimasukkan lagi.
> - Constraint user: **POC-ABS dan TabR wajib dipakai.** Jadi head pose /
>   landmark (issue 12) hanya boleh jadi fitur TAMBAHAN ke POC-ABS, bukan
>   pengganti; baseline logistik/GBDT tetap pembanding, bukan model akhir.


## Goal

Memperbaiki 5 sebab penurunan akurasi LOSO di hulu representasi dan di
protokol, sambil tetap memakai POC-ABS, ROI25, LOSO, dan TabR.

## Architecture

Tiga jalur: (a) representasi — normalisasi per subjek + fitur temporal +
baseline netral per subjek; (b) protokol — metrik level subjek tanpa AUC;
(c) pembanding — baseline model sederhana.

## Tech Stack

Python 3.12, pandas/numpy/scikit-learn, TabR resmi (vendored di
`third_party/tabular-dl-tabr-official`), bash runner.

## Must Not Forget

- **Jangan** mengubah/menimpa tabel fitur lama `poc_abs_roi_signals.xlsx`
  dan `poc_abs_roi_signals_full.pkl`; hasil lama harus tetap bisa direproduksi.
- **Jangan** menjalankan training, spotting, atau test/smoke/e2e — user tidak
  minta. Hanya verifikasi statis (parse/import/`--help`).
- **Jangan** commit, push, atau deploy.
- Dokumen markdown baru ikut konvensi proyek di `report/` (bukan `docs/`).
- Semua teks dokumen dan komentar kode memakai bahasa Indonesia, mengikuti
  gaya `report/documentation/changes-log.md`.
- Baseline netral per subjek tidak bisa dijalankan di mesin ini
  (`/mnt/FINNY/dataset` tidak ada) — siapkan kode + perintah, catat di dokumen.
- Metrik pemilihan epoch tetap default TabR (accuracy); tidak menambah mesin
  pemilihan baru.

## Issue Index

**Critical**
- [01 — Hapus AUC dari pipeline](issues/01-critical-remove-auc.md)
- [02 — Normalisasi fitur per subjek](issues/02-critical-subject-normalization.md)

**High**
- [03 — Fitur temporal ROI onset→apex→offset](issues/03-high-temporal-roi-features.md)
- [04 — Baseline netral per subjek di spotting/ekstraksi](issues/04-high-subject-neutral-baseline.md)

**Medium**
- [05 — Protokol level subjek + interval kepercayaan](issues/05-medium-subject-level-protocol.md)
- [06 — Baseline model sederhana sebagai pembanding TabR](issues/06-medium-baseline-models.md)

**Low**
- [07 — Dokumen rujukan paper riset](issues/07-low-research-papers-doc.md)

## Fase 2 — mengejar target 70% (2026-10-06)

Analisis: `report/findings/research-strengthen-loso.md`.
**Status target:** 70% LOSO pada N=56 dari fitur micro-expression **belum
didukung literatur** (pita realistis 48–72%; label kuesioner sendiri ber-AUC
0.81 dengan spesifisitas 0.57; N minimum ML kesehatan mental 500–1000).
Urutan di bawah ini mengejar batas atas pita itu, bukan 70% dengan cara
memaksa.

**Critical**
- [10 — Tabel fitur basi: re-ekstraksi dari metadata terbaru](issues/10-critical-stale-feature-table.md)
- [11 — Uji berpasangan dalam-subjek (gerbang keputusan)](issues/11-critical-within-subject-paired-test.md)

**High**
- [12 — Head pose + geometri landmark sepanjang sesi](issues/12-high-headpose-landmark-features.md)

## Fase 3 — eksekusi re-ekstraksi (2026-10-06)

Keputusan user: **pakai dataset yang dipakai sejak awal** (`anxiety_raw`, 56
subjek) supaya perbandingan apple-to-apple; **jangan** gabungkan `datatest`.
Jalankan semua kecuali stage training TabR terakhir (user jalankan sendiri).
Constraint: **POC-ABS + TabR wajib**.

Urutan eksekusi:
1. `scripts/save_neutral_references.py` → `neutral.png` per sample (560 sample).
   Dipilih daripada spotting ulang: klip + metadata sudah konsisten, spotting
   ulang hanya untuk neutral.png itu boros dan berisiko mengubah event set.
2. `extract_features_poc_abs.py --roi-signals --baseline onset` →
   `poc_abs_roi_signals.xlsx` (tabel kanonik, memperbaiki issue 10).
3. `extract_features_poc_abs.py --roi-signals --baseline neutral` →
   `poc_abs_roi_signals_neutral.xlsx` (issue 04).
4. `build_temporal_features.py` untuk kedua tabel (issue 03).
5. `within_subject_test.py` (issue 11) — gerbang keputusan.
6. BERHENTI sebelum training TabR.

### Hasil Fase 3

| langkah | status | hasil |
|---|---|---|
| 1. neutral.png | SELESAI | 560/560 sample (30 detik) |
| 2. fitur onset | SELESAI | 97.303 baris (dari 65.206), 22 menit, 1 error |
| 3. fitur neutral | SELESAI | 97.317 baris, 37 menit, 0 error |
| 4. cache pkl (keduanya) | SELESAI | identik bit-per-bit |
| 5. fitur temporal (keduanya) | SELESAI | 138 kolom, 6.877 / 6.878 event |
| 6. uji berpasangan (gerbang) | SELESAI | tidak ada sinyal — lihat bawah |
| 7. diagnostik level subjek | SELESAI | terbaik 0.6071 (p=0.08) |
| 8. training TabR | **TIDAK dijalankan** | user jalankan sendiri |

**Issue 10 (tabel basi) SELESAI:**

| | stale | baru |
|---|---|---|
| total baris | 65.206 | **97.303** / 97.317 |
| `before` | 20.782 | **52.837** |
| `before/tidak` | **0** | **13.720** / 13.734 |
| subjek `before` | 23 | **56** |
| event `before` | 1.493 | 3.638 (metadata 3.639) |

Arsip tabel lama: `experiments/features/apex/_stale_archive/`.

**Issue 11 (gerbang) SELESAI — hasilnya negatif:**

| tabel | grup berubah (18 subjek) | grup kontrol (38 subjek) | LOSO dalam-subjek |
|---|---|---|---|
| onset | 20/25 fitur "signifikan" | **25/25 signifikan** | acc 0.583, p=0.264 |
| neutral | 0/25 | 0/25 | acc 0.528, p=0.473 |

Kontrol yang membatalkan bacaan onset: kalau subjek yang labelnya **tidak**
berubah pun menunjukkan perbedaan before→after yang sama kuat, itu **efek
sesi**, bukan kecemasan. Baseline netral menghapus artefak itu — dan tidak
menyisakan sinyal.

**Diagnostik level subjek (BUKAN TabR):**

| fitur | model | acc | 95% CI | p |
|---|---|---|---|---|
| onset 25 | logistic / gbdt | 0.5000 | 0.37–0.63 | 0.65 |
| onset 125 | logistic | 0.4464 | 0.32–0.58 | 0.86 |
| onset 125 | gbdt | 0.5893 | 0.46–0.71 | 0.17 |
| **neutral 125** | **gbdt** | **0.6071** | 0.48–0.72 | **0.08** |
| neutral 125 | logistic | 0.5714 | 0.44–0.69 | 0.22 |

Baseline mayoritas 0.5536. Hasil terbaik 0.6071 — di atas baseline, tapi
**belum signifikan**. 70% tidak tercapai.

## Fase 4 — riset konfigurasi TabR untuk N kecil (2026-10-06)

Analisis: `report/findings/research-tabr-config-small-data.md`.

**Koreksi yang harus dibaca dulu:** klaim "overfitting turun 48%" di Fase 3
**tidak sah**. Gap yang turun itu train-vs-**val**, dan val dipakai memilih
`best_epoch` (tidak netral). Ukuran jujur train-vs-**test**:
lama 27,49 poin → reg **33,27 poin** (membesar). Lihat Iterasi 4.15.

**Temuan kunci:** 237 fitur / 44 baris train = `d/n 5,39` → rezim
*high-dimensional low-sample-size*. Literatur rezim ini menyuruh **mengurangi**
dimensi & kapasitas, bukan menambah. Dan config **resmi** TabR (d_main 96–384)
kalau disalin menghasilkan 107.041 parameter — 2,4x lebih besar dari yang
sekarang dipakai.

**Config baru:**
- `experiments/configs/tabr_loso_official_style.toml` — default resmi +
  `num_policy=quantile` + `encoder_n_blocks=0`. 107.041 param. Dipakai sebagai
  **kontrol negatif**.
- `experiments/configs/tabr_loso_compact.toml` — kapasitas minimal.
  13.089 param (297/baris, 3,4x lebih kecil dari `reg`).

**Eksperimen (user jalankan):**

| # | diuji | config | fitur | hipotesis |
|---|---|---|---|---|
| E1 | apakah default resmi transfer? | `official_style` | 237 | **tidak** — param 2,4x, test turun |
| E2 | kapasitas minimal membantu? | `tiny` | 237 | ≈ reg atau sedikit naik |
| E3 | apakah `d < n` membantu? | `tiny` | **25 (ROI25 saja)** | kandidat terbaik |
| E4 | sweep `context_size` | `tiny` | 25 | 4 vs 8 vs 16 vs 43 |
| E5 | ensembling (varians) | terbaik E1–E4 | terbaik | CI menyempit |

E1 sengaja ada sebagai kontrol negatif: kalau default resmi menang, hipotesis
`d >> n` salah dan itu informasi penting.

**Tidak disarankan:** embeddings PLR/PLE (config resmi TabR sendiri tidak
memakainya; menambah parameter di 44 baris), menambah fitur lagi, dan menyalin
default resmi apa adanya.

**Harapan jujur:** ensembling & pemangkasan kapasitas bisa menyempitkan CI dan
menstabilkan hasil, dan E3 mungkin naik ke ~62–65%. **70% tetap tidak
realistis** di representasi ini — uji gerbang (Iterasi 4.13) menunjukkan tidak
ada sinyal kecemasan yang terukur di fitur POC-ABS.






## Target Architecture

```
fitur lama (25/frame)  ──┬─► build_temporal_features.py ─► fitur temporal
                         │
ekstraksi (+neutral) ────┘
                         │
                         ▼
        run_loso.py --subject-norm subject  ──► exp/tabr/<ds>/fold_*/
                         │
                         ├─► collect_loso_results.py  (level subjek, tanpa AUC, +CI)
                         │
                         └─► run_loso_baseline.py     (logistik/GBDT + permutation)
```

## Priority Order

01 → 02 → 03 → 04 → 05 → 06 → 07

## Validation Commands

```bash
# parse semua file yang diubah
.venv/bin/python - <<'PY'
import ast, pathlib
for f in [
  'scripts/run_loso.py',
  'scripts/collect_loso_results.py',
  'scripts/build_temporal_features.py',
  'scripts/run_loso_baseline.py',
  'scripts/extract_features_poc_abs.py',
  'scripts/process_spotting_pipeline.py',
  'third_party/tabular-dl-tabr-official/lib/metrics.py',
  'third_party/tabular-dl-tabr-official/lib/data.py',
]:
    ast.parse(pathlib.Path(f).read_text())
print('parse ok')
PY

# tidak ada sisa referensi AUC di kode proyek
grep -rn "roc.auc\|roc_auc" scripts/ experiments/configs/ | grep -v '\.pyc'

# import + argumen
.venv/bin/python scripts/collect_loso_results.py --help
.venv/bin/python scripts/build_temporal_features.py --help
.venv/bin/python scripts/run_loso_baseline.py --help

# bentuk ulang summary dari hasil LOSO lama (tanpa training)
.venv/bin/python scripts/collect_loso_results.py --exp convat_apex_anxiety_loso_roi25
```

## Rollout Plan

- [x] 01 Hapus AUC dari metrics, data, configs, collect
- [x] 02 Normalisasi fitur per subjek di run_loso
- [x] 03 Script fitur temporal ROI
- [x] 04 Baseline netral per subjek di spotting + ekstraksi
- [x] 05 Protokol level subjek + CI di collect
- [x] 06 Script baseline model sederhana
- [x] 07 Dokumen rujukan paper riset
- [x] 08 Update `run_pipeline.sh`, `run`, config, changes-log
- [x] 09 Verifikasi statis seluruh perubahan

## Done Criteria

- [x] Tidak ada `roc-auc`/`roc_auc` di kode proyek maupun report TabR.
- [x] `summary.md` LOSO level subjek terbentuk tanpa AUC, dengan CI.
- [x] `run_loso.py` punya `--subject-norm` dan tanpa `check_tabtr_patch`.
- [x] `build_temporal_features.py` menghasilkan tabel fitur temporal.
- [x] Ekstraksi punya opsi baseline netral per subjek.
- [x] `run_loso_baseline.py` menjalankan logistik/GBDT + permutation test.
- [x] `report/documentation/research-papers.md` berisi sitasi 2021→sekarang.
- [x] Tabel fitur lama tidak tersentuh.

## Bukti Verifikasi (2026-10-06)

- Parse AST 9 file yang diubah: ok. `bash -n` untuk `run_pipeline.sh` dan `run`: ok.
- `grep` AUC di `scripts/`, `experiments/`, `apex/`, `features_extraction/`,
  `helper/`, `comparasion/`, `src/`, `run`: kosong. Di `lib/`/`bin/` TabR: kosong.
- `collect_loso_results.py` pada hasil LOSO 2026-09-28 (`--out .amp/in/verify`):
  accuracy 0.5536, CI 95% 0.4414–0.6923 (memuat baseline mayoritas 0.5536).
- `subject_standardize` pada tabel nyata: max |mean per subjek| 1.23e-15,
  max |std per subjek − 1| 2.66e-15.
- `build_temporal_features.py`: 65.206 baris, 138 kolom, 4.737 event, tanpa NaN.
- `run_loso_baseline.py` (roi25, aggregate subject): logistic 0.4643 (p=0.8209),
  gbdt 0.5536 (p=0.3632).
- `run_loso_baseline.py` (temporal, aggregate subject): logistic 0.4821
  (p=0.7363), gbdt 0.5000 (p=0.7065).

