# CONTEXT — Perbaikan Representasi & Protokol LOSO

## Problem

Pipeline `POC-ABS → ROI25 → TabR` diuji dengan LOSO (1 subjek/fold) dan
hasilnya di level acak:

- LOSO roi25 level subjek: accuracy 55.36% = baseline mayoritas 55.36%,
  ROC-AUC 51.91% (acak 50%). Sumber:
  `output/training/convat_apex_anxiety_loso_roi25/summary.md`.
- Agregasi level subjek (exp3): accuracy 44.05%, AUC 41.29% (di bawah acak).
  Sumber: `output/training/exp3_subject_agg/summary.md`.
- Diagnostik logistik LOSO pada matriks fitur yang sama: AUC 52.52%,
  permutation test p = 0.280 (Iterasi 3.9 di `report/documentation/changes-log.md`).
- Varian fitur ANTAR subjek > varian DALAM subjek
  (`mulut_mean_m` 0.353 vs 0.201).

Artinya model belum bisa membedakan subjek baru. Akar masalah ada di
representasi (hulu), bukan di TabR.

Lima sebab, terurut dampak (lihat `report/findings/literature-accuracy-drop-2021-2026.md`):

1. Fitur mengkodekan **identitas** lebih kuat daripada kondisi (varian antar
   subjek > dalam subjek).
2. Fitur ROI25 **statis** — hanya ringkasan di apex; dinamika onset→apex→offset
   hilang.
3. Baseline POC-ABS = **frame onset klip**, bukan baseline netral per orang
   (`save_event_clip_frames` menyimpan frame onset..offset, jadi "frame 1"
   klip = frame onset yang sudah mulai berkontraksi).
4. Label 1 per subjek tapi **44.424 baris frame**; tiap fold LOSO test-nya
   satu kelas → metrik level frame tidak mengukur kemampuan.
5. **TabR di N kecil** (56 subjek) dengan fitur berisik: retrieval mengambil
   tetangga yang identitasnya sama.

Tambahan eksplisit dari user: **AUC dihapus** — bukan bagian protokol asli,
hanya masuk lewat rencana.

## Fix

Perbaiki di hulu (representasi) dan di protokol, tanpa mengganti POC-ABS,
ROI25, LOSO, atau TabR:

- Hapus AUC dari pipeline dan laporan.
- Normalisasi per subjek (personal z-score) untuk membuang skala identitas.
- Tambah deskriptor temporal onset→apex→offset per ROI.
- Sediakan baseline netral per subjek di tahap spotting/ekstraksi.
- Protokol: metrik level subjek saja sebagai headline, dengan interval
  kepercayaan.
- Sediakan baseline model sederhana (logistik/GBDT) + permutation test
  sebagai pembanding TabR.

## Architecture Now

```
dataset mentah (video)                     [TIDAK ADA di mesin ini]
  │
  ├─ scripts/process_spotting_pipeline.py
  │     + simpan neutral.png per sample   <-- BARU (issue 04)
  │     output: output/apex/dataset/**, metadata.xlsx
  │
  ├─ scripts/extract_features_poc_abs.py
  │     + --baseline onset|neutral        <-- BARU (issue 04)
  │     output: poc_abs_roi_signals.xlsx (25 fitur/frame, TIDAK diubah)
  │
  ├─ scripts/build_feature_cache.py → poc_abs_roi_signals_full.pkl
  │
  ├─ scripts/build_temporal_features.py   <-- BARU (issue 03)
  │     input : pkl per-frame
  │     output: poc_abs_roi_signals_temporal.pkl (25 + temporal per ROI)
  │
  ├─ scripts/run_loso.py
  │     + --subject-norm subject          <-- BARU (issue 02)
  │     - check_tabtr_patch() dihapus     <-- issue 01
  │     output: exp/tabr/<dataset>/fold_*/…
  │
  ├─ scripts/collect_loso_results.py
  │     - roc_auc dihapus                 <-- issue 01
  │     + CI level subjek                 <-- issue 05
  │
  └─ scripts/run_loso_baseline.py         <-- BARU (issue 06)
        logistik + GBDT + permutation test, protokol LOSO identik
```

## Key Files

**Protokol & AUC**
- `scripts/collect_loso_results.py`
- `scripts/run_loso.py`
- `third_party/tabular-dl-tabr-official/lib/metrics.py`
- `third_party/tabular-dl-tabr-official/lib/data.py`

**Representasi**
- `scripts/run_loso.py` (normalisasi per subjek)
- `scripts/build_temporal_features.py` (baru)
- `scripts/extract_features_poc_abs.py` (baseline netral + `--output`)
- `scripts/save_neutral_references.py` (baru; neutral.png dari video mentah)
- `scripts/process_spotting_pipeline.py` (opsi simpan frame netral)
- `scripts/within_subject_test.py` (baru; gerbang keputusan)
- `experiments/configs/tabr_loso_roi25_reg.toml` (baru; config anti-overfitting)

**Konfigurasi & runner**
- `experiments/configs/tabr_loso_roi25.toml`
- `scripts/run_pipeline.sh`
- `run`

**Dokumentasi**
- `report/documentation/research-papers.md` (baru)
- `report/documentation/changes-log.md`

## Important Behavior Changes

- `summary.md` / `summary.csv` LOSO **tidak lagi** memuat kolom AUC.
- `report.json` TabR **tidak lagi** memuat key `roc-auc`.
- `run_loso.py` kehilangan `check_tabtr_patch()` (patch AUC tidak diperlukan lagi).
- Tabel fitur lama (`poc_abs_roi_signals.xlsx`) **tidak diubah** — hasil lama
  tetap bisa direproduksi. Fitur temporal masuk ke file baru.
- Baseline netral butuh **re-run** spotting + ekstraksi dengan dataset mentah;
  di mesin ini `/mnt/FINNY/dataset` tidak ada, jadi hanya kode + perintahnya
  yang disiapkan.

## Tests

Tidak ada test suite di repo ini. Verifikasi yang dipakai:

- `python -c "import ast; ast.parse(open(f).read())"` untuk tiap file yang diubah.
- `.venv/bin/python scripts/collect_loso_results.py --help` dan sejenisnya
  (import bersih, argumen tampil).
- Jalankan ulang `collect_loso_results.py` pada hasil LOSO lama untuk
  memastikan summary baru tanpa AUC terbentuk.
- Verifikasi statis tabel fitur temporal: jumlah baris, kolom, tanpa NaN.

Test/run penuh (LOSO training, spotting ulang) **tidak dijalankan** di sini
sesuai instruksi user.

## Validation Done

Semua pada 2026-10-06, tanpa training/spotting ulang (sesuai instruksi user).

- Parse AST: 9 file yang diubah, semua ok. `bash -n` untuk `run_pipeline.sh`
  dan `run`: ok.
- Hapus AUC: `grep` di `scripts/`, `experiments/`, `apex/`,
  `features_extraction/`, `helper/`, `comparasion/`, `src/`, `run`, dan di
  `lib/`+`bin/` TabR → kosong.
- `collect_loso_results.py --exp convat_apex_anxiety_loso_roi25
  --out .amp/in/verify` → summary tanpa AUC, dengan kolom 95% CI.
  accuracy 0.5536, CI 0.4414–0.6923 (memuat baseline mayoritas 0.5536);
  sens 0.7067 (0.4452–0.7975); spec 0.4301 (0.3484–0.6803). Hasil lama tidak
  ditimpa.
- `subject_standardize` pada tabel nyata (44.424 baris, 56 subjek, 25 fitur):
  max |mean per subjek| = 1.23e-15, max |std per subjek − 1| = 2.66e-15,
  jumlah baris tetap, subjek 1 baris tidak menghasilkan NaN.
- `build_temporal_features.py`: 65.206 baris, 138 kolom, 4.737 event, tanpa NaN.
- `run_loso_baseline.py`:
  - roi25 (25 fitur): logistic acc 0.4643 (p=0.8209), gbdt 0.5536 (p=0.3632).
  - temporal (125 fitur): logistic acc 0.4821 (p=0.7363), gbdt 0.5000 (p=0.7065).
- `--help` bersih untuk `run_loso.py`, `collect_loso_results.py`,
  `build_temporal_features.py`, `run_loso_baseline.py`,
  `extract_features_poc_abs.py`.

**Belum diverifikasi (butuh perintah user):** training LOSO TabR dengan
`--subject-norm subject` (user jalankan sendiri), dan pipeline lengkap
`./run pipeline --mode anxiety`.

## Fase 3 — hasil eksekusi (2026-10-06)

Semua dijalankan di mesin ini. **Training TabR TIDAK dijalankan**
(`find third_party/.../exp -newermt '2026-10-06 09:00' -name report.json`
= 0).

- `save_neutral_references.py`: 560/560 sample ok (30 detik).
- `--baseline onset`: 97.303 baris, 22 menit, 1 error.
- `--baseline neutral`: 97.317 baris, 37 menit, 0 error.
- `build_feature_cache.py`: identik bit-per-bit untuk kedua tabel.
- `build_temporal_features.py`: 138 kolom, 6.877 / 6.878 event.
- `within_subject_test.py`: lihat tabel di bawah.
- `run_loso_baseline.py`: lihat tabel di bawah.

**Gerbang (issue 11) — negatif:**

| tabel | berubah (18 subjek) | kontrol (38 subjek) | LOSO dalam-subjek |
|---|---|---|---|
| onset | 20/25 "signifikan" | **25/25 signifikan** | 0.583, p=0.264 |
| neutral | 0/25 | 0/25 | 0.528, p=0.473 |

Kontrol membatalkan bacaan onset: subjek yang labelnya tidak berubah pun
menunjukkan perbedaan before→after sama kuat → efek sesi, bukan kecemasan.

**Diagnostik level subjek (sklearn, bukan TabR):**

| fitur | model | acc | 95% CI | p |
|---|---|---|---|---|
| onset 25 | logistic / gbdt | 0.5000 | 0.37–0.63 | 0.65 |
| onset 125 | logistic | 0.4464 | 0.32–0.58 | 0.86 |
| onset 125 | gbdt | 0.5893 | 0.46–0.71 | 0.17 |
| **neutral 125** | **gbdt** | **0.6071** | 0.48–0.72 | **0.08** |
| neutral 125 | logistic | 0.5714 | 0.44–0.69 | 0.22 |

Baseline mayoritas 0.5536. Terbaik 0.6071 (belum signifikan). 70% tidak
tercapai pada representasi ini.


## Known Notes

- `*.md` di `.gitignore`, jadi semua dokumen ini tidak masuk git (konsisten
  dengan `report/documentation/changes-log.md`).
- Perbaikan baseline netral (issue 04) tidak bisa diverifikasi end-to-end di
  mesin ini karena dataset mentah tidak ada.
- `--subject-norm subject` memakai statistik subjek itu sendiri, tanpa label.
  Ini normalisasi tanpa supervisi (bukan kebocoran label), sama seperti
  Personal-Zscore di literatur. Tetap dicatat eksplisit di summary.
- Keputusan lama yang dipertahankan: agregasi subjek (exp3) tetap negatif dan
  tidak dijadikan default.
