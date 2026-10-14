# Konfigurasi TabR untuk N Kecil — Riset Lanjutan

Tanggal: 2026-10-06. Melanjutkan `research-strengthen-loso.md`.
Constraint: **POC-ABS dan TabR tetap dipakai.** Boleh menambah, tidak mengganti.

---

## 1. Kondisi sekarang (angka nyata)

Run terakhir (config `tabr_loso_roi25_reg.toml`, 237 fitur):

| metrik | nilai |
|---|---|
| train (frame) | 92,79% |
| val (frame, 11 subjek) | 78,79% |
| **test (level subjek, 56)** | **59,52%** ± 8,99% |
| baseline mayoritas | 55,36% |
| CI 95% test | 47,63% – 72,42% (**memuat baseline**) |
| per seed | 60,71% / **50,00%** / 67,86% |
| param | 44.865 untuk 44 baris train |

Tiga masalah yang harus dijelaskan oleh riset:

1. **Varians antar seed besar** (50,00% → 67,86%). Ini masalah varians, bukan bias.
2. **237 fitur vs 44 baris train** = `d/n = 5,39`.
3. **CI memuat baseline** → belum terbukti lebih baik dari menebak mayoritas.

---

## 2. Temuan kunci: kita ada di rezim `d >> n`

Ini bukan detail, ini yang menentukan metode apa yang masuk akal.

| set fitur | d | d/n (44 baris train) |
|---|---|---|
| ROI25 saja | 25 | **0,57** |
| temporal saja | 100 | 2,27 |
| **ROI25 + temporal (dipakai)** | **237** | **5,39** |

Literatur rezim *high-dimensional low-sample-size* (HDLSS):

> "for tabular datasets with extremely high d-dimensional features but limited
> n samples (i.e. d ≫ n), machine learning models struggle to achieve strong
> performance" — Ruiz et al., *Tabular DL when d ≫ n*, 2022

> "the dominant approaches are statistical methods that reduce the
> dimensionality of the input space, select features, impose regularization
> penalties on parameter magnitudes, or use ensembles of weak tree-based
> models" — ibid.

> "when the sample size is smaller than the data dimensionality ... it easily
> leads to inadequate training or over-fitting phenomenon and drops the
> classification ability of the classifier" — *Feature dimensionality
> reduction: a review*, 2021

Konsekuensi praktis: **arah yang benar untuk N=44 adalah MENGURANGI kapasitas
dan dimensi, bukan menambah.** Kita justru menambah fitur 25 → 237 di iterasi
terakhir.

---

## 3. Temuan penting: config resmi TabR BUKAN untuk N kecil

Saya cek config resmi di repo yang sama
(`exp/tabr/california/0-tuning.toml`). Default resminya:

```
context_size      = 96
batch_size        = 256
d_main            = 96–384
d_multiplier      = 2.0
encoder_n_blocks  = 0
predictor_n_blocks= 1
num_policy        = "quantile"
num_embeddings    = "__null__"
patience          = 16
```

Saya buat config yang mengikuti default resmi itu (hanya mengecilkan
`batch_size` dan `context_size` karena mustahil di 44 baris), lalu menghitung
parameter aktual:

| config | fitur | parameter | param/baris train |
|---|---|---|---|
| `tabr_loso_roi25_reg` (yang kamu pakai) | 237 | 44.865 | 1.020 |
| `tabr_loso_official_style` (mengikuti resmi) | 237 | **107.041** | **2.433** |
| `tabr_loso_compact` (kapasitas minimal) | 237 | **13.089** | **297** |

**Mengikuti default resmi justru MEMPERBESAR model 2,4x.** Default itu
di-tuning untuk California Housing (~20.640 baris), bukan 44 baris.

Bacaan: menyalin default resmi bukan "best practice" di sini — itu memperburuk
overfitting. Yang benar adalah mengecilkan sampai proporsional dengan N.

---

## 4. Lever yang tersedia, urut kekuatan

### Lever 1 — Ensembling (paling menjawab masalah kita)

Masalah utama kita **varians** (seed 50,00% → 67,86%, std 8,99%). Ensembling
adalah alat standar untuk itu:

> "Bagging addresses high variance by training multiple models on
> bootstrap-resampled versions of the data and averaging their predictions.
> Each individual tree may overfit in a slightly different way, but averaging
> tends to cancel out idiosyncratic errors while preserving consistent
> structure." — *A Bias–Variance Perspective on Tabular Data*, 2025

> "TabM itself can benefit from the conventional deep ensembling" —
> Gorishniy et al., *TabM*, ICLR 2025

**Sudah didukung repo ini:** `bin/ensemble.py` (ensemble_size=5, n_ensembles=3)
dan `bin/go.py` (n_seeds=15). Kita baru pakai 3 seed per fold.

Biaya: 15 seed × 56 fold × ~5,5 detik ≈ **70 menit**. Ini lever dengan
rasio dampak/biaya terbaik yang tersisa.

**Peringatan jujur dari paper bias–variance yang sama:**

> "variance reduction helps most when base learners have high variance **and**
> the signal-to-noise ratio supports averaging out idiosyncratic errors rather
> than structural bias"

Kalau SNR ≈ 0 (yang ditunjukkan uji gerbang), ensembling akan **menstabilkan
ke arah kelas mayoritas**, bukan menaikkan akurasi. Harapan realistis: CI
menyempit dan hasil lebih dapat dipercaya — bukan lompatan akurasi.

### Lever 2 — Kurangi dimensi fitur sampai `d < n`

Satu-satunya set fitur kita yang ada di rezim sehat adalah **ROI25 saja**
(d=25, d/n=0,57). Ini juga yang paling sesuai constraint "POC-ABS tetap".

Pilihan, dari paling sederhana:
- `--features poc_abs_roi_signals_neutral_full.pkl` (25 fitur, d/n=0,57)
- `--drop-features` diperketat untuk memangkas temporal
- PCA ke ≤ 43 komponen (batas keras: kovarians singular kalau > n−1)

Catatan teknis: PCA di 237 fitur / 44 baris **maksimum 43 komponen**, dan
literatur memperingatkan matriks kovarians singular di rezim ini — jadi PCA
harus di-fit per fold, bukan sekali di seluruh data.

### Lever 3 — Selaraskan dengan default resmi yang masih masuk akal

Dua penyimpangan config kita dari default resmi yang **tidak** didukung
literatur dan murah diperbaiki:

| parameter | config kita | resmi | alasan |
|---|---|---|---|
| `num_policy` | `standard` | **`quantile`** | fitur POC-ABS distribusinya tidak normal; quantile transform menstabilkan |
| `encoder_n_blocks` | `1` | **`0`** | resmi = TabR-S; blok tambahan hanya menambah parameter |

Keduanya sudah diterapkan di `tabr_loso_official_style.toml` (tapi lihat §3:
config itu juga membawa `d_main=96` yang memperbesar model — jadi ia lebih
tepat dipakai sebagai **kontrol**, bukan kandidat utama).

### Lever 4 — Sweep `context_size`

Sekarang 8 dari 44 kandidat (18%). Literatur tidak memberi angka untuk N=44;
paper TabR memakai m=96 di dataset ribuan baris. Yang masuk akal diuji:
**4, 8, 16, 43** (43 = semua kandidat selain diri sendiri).

Perlu dicatat: TabR mengambil manfaat dari **kandidat yang besar**. Di 44
kandidat, mekanisme inti TabR hampir tidak punya ruang — ini keterbatasan
struktural, bukan salah setelan.

### Lever 5 — Tambah subjek (bukan config, tapi paling pasti)

`datatest` punya **49 subjek** yang belum dipakai (total 105). Sudah kamu
putuskan untuk **tidak** dipakai supaya perbandingan apple-to-apple — dicatat,
tidak diusulkan lagi.

---

## 5. Yang TIDAK disarankan

**Embeddings fitur numerik (PLR/PLE).** Gorishniy et al. 2022 menunjukkan
embeddings membantu tabular DL — tapi:
- Config resmi TabR sendiri memakai `num_embeddings = "__null__"` (tidak pakai).
- Embeddings **menambah parameter**; di 44 baris itu menambah overfitting.
- `TabR‡` (dengan embeddings) hanya varian pembanding di paper TabM, bukan default.

Di rezim `d >> n` literatur justru menyuruh sebaliknya. Jangan.

**Menambah fitur lagi.** Kita sudah 25 → 237 dan test hanya naik 4 poin
(tidak signifikan). Arah ini melawan literatur.

**Menyalin default resmi apa adanya.** Lihat §3 — itu memperbesar model 2,4x.

---

## 6. Eksperimen yang disarankan (berurut)

Semua pakai `--aggregate subject` (label milik subjek) dan `--subject-norm none`.

| # | yang diuji | config | fitur | hipotesis |
|---|---|---|---|---|
| E1 | apakah default resmi transfer? | `official_style` | 237 | **tidak** — param 2,4x, test turun |
| E2 | apakah kapasitas minimal membantu? | `tiny` | 237 | test ≈ reg atau sedikit naik |
| E3 | apakah `d < n` membantu? | `tiny` | **25 (ROI25 saja)** | kandidat terbaik |
| E4 | sweep context | `tiny` | 25 | 4 vs 8 vs 16 vs 43 |
| E5 | ensembling | terbaik dari E1–E4 | terbaik | CI menyempit, akurasi stabil |

E1 sengaja dimasukkan sebagai **kontrol negatif**: kalau default resmi
menang, hipotesis `d >> n` saya salah dan itu informasi penting.

Cara jalan (contoh E3):

```bash
./run loso --dataset convat_loso_tiny_roi25 \
  --features experiments/features/apex/poc_abs_roi_signals_neutral_full.pkl \
  --aggregate subject --subject-norm none \
  --config experiments/configs/tabr_loso_compact.toml

./run collect --exp convat_loso_tiny_roi25 \
  --features experiments/features/apex/poc_abs_roi_signals_neutral_full.pkl \
  --out output/training
```

E5 (ensemble, setelah memilih config terbaik) — 15 seed lalu ensemble:

```bash
./run loso --dataset convat_loso_ens --features <tabel terbaik> \
  --aggregate subject --subject-norm none --seeds 15 --config <config terbaik>

cd third_party/tabular-dl-tabr-official
PROJECT_DIR=$PWD .venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from pathlib import Path
import bin.ensemble
for f in sorted(Path('exp/tabr/convat_loso_ens').glob('fold_*')):
    bin.ensemble.main(f / '0-evaluation', n_ensembles=1, ensemble_size=5)
"
```

---

## 7. Harapan yang jujur

| goal | status |
|---|---|
| Overfitting turun | **sudah tercapai** (gap train–val 26,70 → 14,00 poin) |
| CI menyempit, hasil lebih dapat dipercaya | mungkin (E5) |
| Akurasi naik ke ~62–65% | mungkin, kalau E3 (d<n) benar |
| **70%** | **tidak realistis di representasi ini** |

Alasan 70% tidak realistis, dari data kita sendiri:
- Uji gerbang dalam-subjek: **0/25 fitur signifikan** di baseline netral, dan
  grup kontrol juga 0/25 → tidak ada sinyal kecemasan yang terukur.
- Baseline GBDT di fitur yang sama: 60,71% (p=0,08).
- Literatur kecemasan LOSO: 47,97–72,73%.
- Label STAI sendiri: AUC 0,81, spesifisitas 0,57 → plafon label.

Config hanya bisa menyelamatkan **varians dan kejujuran pengukuran**. Ia tidak
bisa menciptakan sinyal yang tidak ada di fitur.

---

## 8. Rujukan baru

Detail + tautan di `report/documentation/research-papers.md`.

- Gorishniy et al., **TabR**, ICLR 2024 — TabR-S (encoder 0 blok, predictor 1
  blok), default `context_size=96`, `num_embeddings=null`.
- Gorishniy et al., **TabM**, ICLR 2025 — deep ensemble membantu; `TabR‡`
  (embeddings) hanya varian.
- Gorishniy et al., **On Embeddings for Numerical Features**, NeurIPS 2022 —
  embeddings membantu, tapi menambah parameter.
- Ruiz et al., **Tabular DL when d ≫ n**, 2022 — di `d >> n`, metode dominan
  adalah reduksi dimensi/seleksi fitur/regularisasi/ensemble.
- **Feature dimensionality reduction: a review**, 2021 — karakteristik small
  sample: overfitting, matriks kovarians singular.
- **GRACES**, Bioinformatics 2023 — seleksi fitur HDLSS.
- **A Bias–Variance Perspective on Tabular Data**, 2025 — kapan variance
  reduction berhasil dan kapan gagal.
- Grinsztajn et al., NeurIPS 2022 — tree > DL di data kecil.
