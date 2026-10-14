# 06 — Baseline model sederhana sebagai pembanding TabR

**Severity:** medium

## Current Problem

Hanya TabR yang diuji di protokol LOSO. Literatur kecil-sampel konsisten:
di N kecil dan fitur berdimensi rendah, model tree/linear mengalahkan DL
(Grinsztajn 2022; TabPFN Nature 2025; ACM tabular survey 2025), dan TabR
sendiri menyebut retrieval punya keterbatasan. Tanpa pembanding, tidak
diketahui apakah kegagalan berasal dari representasi atau dari model.

## Target

Script baru `scripts/run_loso_baseline.py` yang menjalankan model sederhana di
protokol LOSO yang identik dengan `run_loso.py` (split subjek sama, fitur
sama, praproses sama), plus permutation test untuk menguji apakah ada sinyal
di atas acak.

## Required Design

- Model: `LogisticRegression` (liblinear/lbfgs, `class_weight='balanced'`) dan
  `GradientBoostingClassifier` (atau `HistGradientBoostingClassifier`) dari
  scikit-learn. Tanpa dependensi baru.
- Protokol: 56 fold (1 subjek/fold), seed split sama (`RANDOM_SEED = 72`),
  val = 20% subjek sisa seperti `run_loso.py`.
- Praproses sama: impute mean, VarianceThreshold opsional, scaler fit train,
  dan opsi `--subject-norm` (issue 02) yang sama.
- Prediksi test per subjek → tabel level subjek → metrik sama dengan
  `collect_loso_results.py` (accuracy, sensitivity, specificity, PPV, NPV,
  baseline mayoritas, Wilson CI) supaya bisa dibandingkan apple-to-apple
  dengan TabR.
- `--aggregate {none,subject}` mengikuti `run_loso.py`; default `subject`
  karena di N = 56 subjek inilah unit label yang benar.
- Permutation test: acak label antar subjek `--permutations N` (default 200),
  laporkan distribusi null dan p-value akurasi/ROC-AUC.
- Keluaran ke `output/training/<dataset>_baseline/` (summary.md/csv +
  per_subject.csv) — **tidak** menyentuh keluaran TabR.
- Tanpa AUC? Satu pengecualian yang disengaja: permutation test memakai
  ROC-AUC **di level subjek** (bukan per fold) karena itu metrik yang tepat
  untuk mengukur sinyal di atas acak. AUC per fold tetap tidak dipakai dan
  tidak dilaporkan.

## Tests

- Parse AST dan `--help`.
- Jalankan pada fitur nyata dengan `--permutations 20 --aggregate subject`
  (ringan: logistik di 56 baris) untuk membuktikan script hidup, lalu
  laporkan angkanya. GradientBoosting dijalankan hanya bila cepat; kalau
  tidak, catat dan biarkan flag-nya tersedia.

## Done Criteria

- [ ] Script ada, menjalankan logistik + GBDT.
- [ ] Protokol LOSO identik dengan run_loso.
- [ ] Permutation test + p-value.
- [ ] Keluaran terpisah dari keluaran TabR.
- [ ] Angka hasil dijalankan pada fitur nyata dan dilaporkan.
