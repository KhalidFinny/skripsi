# Strategi Bebas Bias & Bebas Overfitting — Tinjauan 2021–2026

Target 70% **ditunda**. Dokumen ini fokus pada dua hal yang lebih dulu harus
beres: **model tidak bias** dan **tidak overfitting**, dengan
**POC-ABS + ROI25 + TabR tetap di dalam** (boleh ditambah, tidak boleh diganti).

Rujukan angka: `convat_apex_anxiety_loso_roi25_reg` (56 fold × 3 seed, 0 FAILED).
Bias yang sudah terukur ada di `report/findings/analisis-bias-loso.md`.

Daftar sitasi lengkap: `report/documentation/research-papers.md`
(bagian "Bias model & overfitting (metode)" dan "Nasional (Indonesia)").

---

## 1. Pisahkan dua masalah, karena obatnya berbeda

| | Overfitting | Bias |
|---|---|---|
| Gejala terukur | train 0.9279 vs test 0.5952 → gap **33,3 poin** | prediksi positif 0.2679 vs sebenarnya 0.4464 → **−0.1786**; tiap grup kalah dari baseline grup sendiri |
| Akar | kapasitas 44.865 param untuk 44 baris train | prior kelas tidak seimbang + identitas subjek bocor ke fitur |
| Obat | kurangi kapasitas/dimensi, ensembling, regularisasi | bobot kelas, ambang dari val, kalibrasi, fitur subject-invariant |

Menggabungkan keduanya adalah kesalahan yang sudah kita buat sekali: konfigurasi
`reg` **mengecilkan gap train–val** tapi **memperbesar gap train–test**
(27,49 → 33,27 poin, Iterasi 4.15). Sebabnya val dipakai memilih `best_epoch`,
jadi val tidak netral.

**Aturan pembacaan baru:** laporkan **MCC + balanced accuracy**, dan **selisih
per grup terhadap baseline grup itu sendiri**. Accuracy pooled tidak dipakai
sebagai headline (paradoks Simpson, lihat dokumen bias).

---

## 2. Lever, urut dampak — semua tetap pakai POC-ABS + TabR

### L1. Fitur subject-invariant (paling menyerang bias)

**Kenapa.** Ini sebab #1 di `literature-accuracy-drop-2021-2026.md`: varian
antar subjek > varian dalam subjek (0.353 vs 0.201), dan identitas adalah
gangguan, bukan sinyal.

**Bukti internasional 2021–2026:**
- Cheong, Kalkan & Gunes (2021), IEEE Signal Processing Magazine — panduan
  bias & fairness khusus **facial affective signal processing**; menyatakan
  ketidakseimbangan data dan atribut demografis adalah sumber bias utama.
- Li & Deng (2022), IEEE TAFFC — **dataset bias** di FER: model belajar
  identitas subjek/dataset, bukan ekspresi.
- Churamani, Kara & Gunes (2022) — *domain-incremental continual learning*
  **menurunkan bias** di FER/AU **tanpa mengorbankan akurasi**.
- Zeeshan et al. (2023), arXiv:2312.05632 — **subject-based domain adaptation**:
  tiap subjek = satu domain; multi-source lebih baik dari single-source.
- DBMF (2025), SN Applied Sciences — *domain adaptation* untuk mitigasi bias
  demografis di affective computing.
- Shen et al., IEEE TAFFC — *subject-invariant contrastive learning*;
  negative transfer terjadi kalau invariansi tidak dipaksa.

**Cara di repo (tanpa mengganti apa pun):**
1. `--subject-norm subject` sudah ada, **tapi tidak bisa dipakai bersama
   `--aggregate subject`** (setelah agregasi std subjek = 0 → semua fitur jadi 0;
   guard di `run_loso.py` menolak). Jadi ini **pindah protokol** ke
   `--aggregate none`/`clip`, bukan A/B murah. Lihat koreksi di L5.
2. Tambah tahap **pembersihan identitas** pada matriks ROI25 sebelum masuk TabR:
   latih model kecil untuk memprediksi `participant` dari fitur, lalu buang
   arah yang prediktif terhadap identitas (mirip MINE/adversarial di paper
   decoupling 2022). POC-ABS tetap penghasil fitur, TabR tetap classifier.
3. Individualised baseline per subjek sudah dipakai (`--baseline neutral`),
   sejalan SAMM/ABT — **pertahankan**, ini sudah benar.

**Risiko.** Kalau identitas dan kondisi benar-benar tercampur (fitur cemas =
fitur wajah orang itu), membuang identitas bisa membuang sinyal. Karena itu
langkah 2 harus diuji sebagai A/B dengan gerbang within-subject
(`scripts/within_subject_test.py`) sebagai wasit, bukan langsung dipakai.

---

### L2. Bobot kelas di loss TabR (paling langsung menyerang bias prediksi)

**Kenapa.** Bias −0.1786 itu bukan efek ambang saja; loss-nya memang tidak
pernah diberi tahu bahwa kelas tidak seimbang.

**Temuan kode (penting):** TabR biner memakai
`F.binary_cross_entropy_with_logits` **tanpa bobot**
(`lib/deep.py:420` → `get_loss_fn`), dan `bin/tabr.py:373` memanggilnya tanpa
argumen. Padahal `get_loss_fn` sudah menerima `**kwargs` — jadi menambahkan
`pos_weight` adalah perubahan **1–2 baris**, bukan fitur baru.

**Bukti:**
- Focal loss untuk ketidakseimbangan kelas di FER (IEEE, 2022) — "focal loss
  tackles both class imbalance and the easy/hard example imbalance".
- CUCN, arXiv:2212.07751 — bobot per kelas + modul atensi mengatasi imbalance
  FER tanpa menurunkan akurasi.
- DICC (2025), PMC12109554 — peningkatan akurasi kelas minoritas 1,73–5,48%.
- **Nasional:** Apriyanthi et al. (2026), TEKNOSI — SMOTE + Random Forest untuk
  kecemasan; menyatakan pendekatan tanpa penanganan **"rentan mengalami bias
  akibat ketidakseimbangan kelas data"**.

**Cara:** tambahkan `pos_weight = n_neg/n_pos` (≈1.24 di data ini) sebagai opsi
config, lalu A/B terhadap loss sekarang. Ini menyerang sensitivity 0.4133 yang
rendah tanpa menyentuh ambang.

**Risiko.** Di N=56, menaikkan bobot kelas minoritas bisa menaikkan recall
sekaligus menurunkan specificity; karena itu ukur dengan **MCC**, bukan accuracy.

---

### L3. Ensembling antar seed (paling langsung menyerang varians/overfitting)

**Kenapa.** Rentang accuracy antar seed **17,9 poin** (0.5000–0.6786) hanya dari
inisialisasi berbeda. Ini varians murni, dan varians adalah separuh wajah
overfitting.

**Temuan kode:** repo TabR resmi **sudah punya** `bin/ensemble.py` (merata-ratakan
probabilitas `ensemble_size` seed, baris 80: `stacked_predictions.mean(0)`) dan
`bin/go.py` (`n_seeds=15`, `n_ensembles=3`). Jadi ini **tidak perlu menulis apa
pun** — cukup naikkan jumlah seed.

**Biaya:** 15 seed × 56 fold × ~5,5 s ≈ **70 menit** (dihitung di Iterasi 4.16).

**Peringatan yang harus dikutip** (bias–variance tabular 2025, entri #57):
variance reduction hanya menolong kalau SNR mendukung; kalau SNR ≈ 0, ensembling
menstabilkan ke arah **kelas mayoritas**, bukan menaikkan akurasi. Jadi
ensembling akan **mengecilkan varians**, dan itu memang tujuannya di sini
(bukan menaikkan akurasi).

---

### L4. Pemilihan epoch pakai cross-entropy, bukan accuracy

**Kenapa.** `best_epoch` sekarang dipilih dengan accuracy — metrik yang justru
bias ke kelas mayoritas. Cross-entropy adalah *proper scoring rule*.

**Temuan kode:** TabR **sudah mendukung** ini. `lib/data.py:20`
(`_SCORE_SHOULD_BE_MAXIMIZED` memuat `'cross-entropy': False`) dan
`lib/metrics.py:73` menghitungnya. Jadi ini **satu baris config**
(`[data] score = "cross-entropy"`), tanpa ubah kode.

**Risiko rendah, biaya rendah → ini A/B pertama yang paling murah.**

---

### L5. Kembalikan dimensi ke `d < n`

**Kenapa.** 237 fitur / 44 baris train → **d/n 5,39** = rezim
*high-dimensional low-sample-size*. Literatur (PLATO d≫n 2022; review reduksi
dimensi 2021; GRACES 2023) sepakat di rezim ini obatnya **reduksi dimensi**,
bukan menambah kapasitas.

**Angka d/n yang presisi** (dihitung dari artefak run, bukan perkiraan).
Penting: `--aggregate subject` menggandakan tiap fitur jadi **mean + std**, jadi
dimensi = 2× fitur dasar.

| representasi | fitur dasar | fitur setelah agregasi | d/n (44 baris) |
|---|---|---|---|
| `poc_abs_roi_signals_neutral_temporal.pkl` (dipakai run `reg`) | 125 | **237** | **5,39** |
| sama, tapi `--drop-features "_std$"` | 125 | 117 | 2,66 |
| sama, `--drop-features "_std$\|_ttp_\|_rise_\|_fall_\|_auc_"` | 125 | 40 | 0,91 |
| `poc_abs_roi_signals_neutral_full.pkl` (ROI25 murni) | 25 | ~50 | 1,14 |

**Nasional:** Ningsih et al. (2025), TEKNOSI — membandingkan **Chi-Square vs
Information Gain** untuk TabNet, tujuannya justru "peningkatan interpretabilitas
dan optimasi kinerja". Ismanto et al. (2024), CoSciTech — membandingkan
Fully-Connected NN vs **TabNet pada data tabular** (preseden TabNet di jurnal
nasional, dan TabNet juga attention-based seperti TabR).

**Cara:** A/B representasi pada protokol identik, **tanpa re-ekstraksi**
(semua tabel fitur sudah ada):

```bash
# a) 237 fitur (baseline run reg)
./run loso --dataset X --features experiments/features/apex/poc_abs_roi_signals_neutral_temporal.pkl \
  --aggregate subject --config experiments/configs/tabr_loso_roi25_reg_ce.toml

# b) buang separuh std -> 117 fitur, d/n 2,66
./run loso --dataset X --features experiments/features/apex/poc_abs_roi_signals_neutral_temporal.pkl \
  --aggregate subject --drop-features "_std$" --config experiments/configs/tabr_loso_roi25_reg_ce.toml

# c) ROI25 murni -> ~50 fitur, d/n 1,14
./run loso --dataset X --features experiments/features/apex/poc_abs_roi_signals_neutral_full.pkl \
  --aggregate subject --config experiments/configs/tabr_loso_roi25_reg_ce.toml
```

Yang dipakai adalah yang **MCC tertinggi**, bukan accuracy tertinggi.

> **KOREKSI atas rencana awal.** Lever L1 langkah 1 (`--subject-norm subject`)
> **TIDAK BISA** dijalankan bersama `--aggregate subject`: setelah agregasi tiap
> subjek cuma punya 1 baris, jadi std subjek = 0 → semua fitur jadi 0. Guard ini
> sudah ada di `run_loso.py` dan menolak kombinasi tersebut. Jadi subject-norm
> hanya mungkin dengan `--aggregate none` atau `--aggregate clip` — artinya ia
> **bukan** A/B yang murah, melainkan pindah protokol. Ditunda sampai setelah
> A/B representasi di atas selesai.

---

### L6. Kalibrasi probabilitas (Platt di val)

**Kenapa.** Proba terkompresi: bin rata-rata 0.080 → laju nyata 0.424; bin 0.922
→ 0.667. Model *under-confident*, proba tidak bisa dibaca sebagai peluang.

**Cara:** Platt/sigmoid di val (bukan isotonic — isotonic butuh >~1000 sampel,
sklearn §1.16.3.2). Lihat `analisis-bias-loso.md` §5.2.

---

### L7. Ambang keputusan dari val

Sudah diimplementasikan (`val_split.csv` + `val_threshold_metrics()`), tinggal
diaktifkan dengan re-run LOSO. Ambang 0.5 adalah pilihan arbitrer.

---

### L8. Tambah AU-based / dinamika temporal (opsional, kalau L1–L6 sudah bersih)

Review MDPI *Information* 16(10):876 (2025) menyatakan **AU-based modeling
memainkan peran sentral** di pipeline spotting→recognition, karena memberi
representasi yang objektif dan berbasis fisiologi untuk memisahkan
micro-expression asli dari noise/overlap macro-expression. Ini sejalan dengan
`build_temporal_features.py` yang sudah ada (onset→apex→offset).

**Nasional:** Cahyo et al. (2023), JATI — ekstraksi fitur mikro-ekspresi
**per komponen wajah (alis, mata, mulut)** dengan LBPH; ini persis ROI25 kita
(5 ROI), jadi ada preseden lokal.

---

## 2b. N — apakah bisa diubah, dan knop POC-ABS

### 2b.1 Jawaban singkat: **N tidak bisa diubah lewat konfigurasi**

| Sumber "N" | Jumlah | Menambah unit independen? |
|---|---|---|
| `anxiety_raw` | **56 subjek** (41+15 before, 25+31 after) | ini N sekarang |
| `datatest` | **hanya 25 subjek** punya before+after lengkap | ya, tapi label tidak sebanding (lihat bawah) |
| View kedua (`*_main.webm`) | 560 file, **belum dipakai** | **TIDAK** — orang & momen yang sama |
| Frame / clip | ~97.000 baris | **TIDAK** — label milik subjek |

**Koreksi angka `datatest`.** Catatan lama menyebut "49 subjek". Setelah dicek
langsung ke `annotations.xlsx`: berkas itu berisi **51 baris / 26 subjek unik**,
dan hanya **25 subjek** punya before+after lengkap. Dari 98 direktori sesi di
`labeled/`, **48 direktori tidak punya anotasi sama sekali**. Jadi tambahan
realistis bukan 49, tapi **~25 subjek**.

Selain itu label `datatest` berasal dari kolom **`score` numerik (5–17)** dengan
potongan sempurna di 10.5 (`score>=11` → `anxiety_tinggi`, cocok 51/51).
Label `anxiety_raw` berasal dari **nama folder** (`anxiety`/`tidak`) tanpa skor.
Kita **tidak bisa memastikan keduanya memakai instrumen yang sama** → menggabung
= risiko *label shift* + melanggar syarat "perbandingan adil" yang sudah
ditetapkan. **Keputusan lama (tidak menggabung) tetap benar**, dan sekarang ada
bukti kerasnya.

### 2b.2 View kedua: ada, tapi bukan tambahan N

Setiap sesi punya **dua kamera**: `*_main.webm` (vp8, 30 fps) dan
`*_sec.avi` (mjpeg, 60 fps). Pipeline **hanya memakai `_sec.avi`** — dicek dari
`clip_path` semua 6.878 event. Saya sudah ambil frame dari keduanya: subjek dan
momen **sama**, hanya sudut/framing berbeda.

Konsekuensinya:
- **Bukan** tambahan sampel independen → tidak menaikkan N statistik.
- Berguna sebagai **augmentasi** (latih di view A, uji di view B) — tapi itu uji
  ketahanan, bukan jalan menuju 70%, dan butuh re-ekstraksi penuh (~jam).
- Jangan pernah dilaporkan sebagai "N bertambah".

### 2b.3 Knop POC-ABS (env var di `scripts/process_spotting_pipeline.py`)

| Env var | Default | Arti | Biaya |
|---|---|---|---|
| `SPOT_ABS` | `1` | baseline POC-ABS | **WAJIB tetap 1** |
| `SPOT_SIGNAL_MODE` | `roi_signals` | mode sinyal per ROI | — |
| `SPOT_THRESH` | `meanstd` | ambang deteksi event (mean+std) | re-ekstraksi |
| `SPOT_DISTANCE` | `1` (non-aktif) | jarak minimum antar puncak (frame) | re-ekstraksi |
| `SPOT_PROM_REL` | `0.04` | prominence minimum relatif | re-ekstraksi |
| `SPOT_INTERP` | `1` | interpolasi sinyal | re-ekstraksi |
| `SPOT_SAVE_NEUTRAL` | `0` | simpan frame netral (untuk baseline netral) | re-ekstraksi |
| `SPOT_NEUTRAL_FRAMES` | `10` | jumlah frame netral | re-ekstraksi |

Dan di `SpottingConfig` (`scripts/spotting.py`): `block_size` 7,
`padding_x` 6, `padding_y` 8, `min_phase_duration` 2, `top_k_apex` 5,
`distance_threshold` 1, `prominence_threshold` 0.005, `cutoff_ratio` 0.3,
`regions` (5 ROI), `target_size`.

**Peringatan:** SEMUA knop POC-ABS butuh **re-ekstraksi penuh** (spotting + fitur,
jam-an), dan mengubahnya mengubah *event mana* yang jadi fitur — **bukan**
menambah sinyal kondisi. Karena gerbang within-subject (Iterasi 4.13) sudah
menunjukkan sinyal setara efek sesi, tuning POC-ABS **bukan** langkah pertama
yang rasional. Kerjakan A/B TabR yang gratis dulu (L4, L5), baru POC-ABS.

### 2b.4 Urutan biaya → manfaat

| Prioritas | Aksi | Re-ekstraksi? | Biaya |
|---|---|---|---|
| 1 | `score="cross-entropy"` (L4) | tidak | 1 re-run LOSO |
| 2 | A/B representasi 237 / 117 / ~50 (L5) | tidak | 3 re-run LOSO |
| 3 | Ambang dari val (L7) | tidak | ikut re-run |
| 4 | `pos_weight` di loss (L2) | tidak | 1–2 baris kode |
| 5 | Ensembling 15 seed (L3) | tidak | ~70 menit |
| 6 | Kalibrasi Platt (L6) | tidak | kode baru |
| 7 | Knop POC-ABS (`SPOT_THRESH`, `SPOT_DISTANCE`, …) | **ya** | jam-an |
| 8 | View kedua sebagai augmentasi | **ya** | jam-an |

---

## 3. Paper nasional (Indonesia) 2021–2026

Bagian ini yang sebelumnya **kosong** di `research-papers.md`. Semua sudah
diverifikasi judul/jurnal/tahunnya dari halaman penerbit.

### 3.1 Deteksi kecemasan / stres / depresi dari wajah & teks

| Paper | Terbitan | Yang relevan buat kita |
|---|---|---|
| Sunaryo et al., "Klasifikasi Ekspresi Wajah untuk Identifikasi Indikasi Kecemasan Menggunakan CNN", DOI 10.36341/rabit.v11i2.8065 | Rabit 11(2), 2026 | CNN + FER2013 → PANIC/NORMAL/UNCERTAIN, acc 92,58%. **Tapi** penulis sendiri menyatakan performa "dipengaruhi … **keterbatasan jumlah dan distribusi data**" → pengakuan lokal bahwa masalahnya di data, bukan arsitektur |
| Bakkar, Sari & Rachmawanto, "Classification of Depression Indication Based on Facial Expression Using MobileNetV2 and SVM", DOI 10.30871/jaic.v10i4.13495 | JAIC 10(4), 2026 | Wajah → indikasi depresi; preseden lokal untuk klasifikasi kondisi mental dari wajah |
| Apriyanthi, Satya Dharma & Dhewanty, "Klasifikasi Hybrid Kecemasan Pengguna X Menggunakan Random Forest, SMOTE, dan Fitur Temporal", DOI 10.25077/TEKNOSI.v12i2.2026.242-250 | TEKNOSI 12(2), 2026 | **Paling relevan**: hybrid fitur + temporal, SMOTE, acc 76,83%; eksplisit menyebut bias akibat ketidakseimbangan kelas |
| Wibowo & Djafar, "Perbandingan Metode Klasifikasi untuk Deteksi Stress Pada Mahasiswa di Perguruan Tinggi", DOI 10.30865/mib.v7i1.5182 | MIB 7(1), 2023 | Perbandingan NB/DT/SVM/NN/RF/kNN untuk stres mahasiswa; dasar pembanding model sederhana |
| Chanafy & Sulistiani, "Comparative Analysis of ML Algorithm Performance for Student Mental Health Classification", DOI 10.32664/smatika.v16i01.2080 | SMATIKA 16(1), 2026 | **Kutipan penting**: "metode validasi masih menggunakan split tunggal, sehingga **potensi bias evaluasi masih ada**" — pembenaran lokal untuk protokol LOSO + CI |
| Rahayu et al., "Klasifikasi Teks untuk Mendeteksi Depresi dan Kecemasan pada Pengguna Twitter Berbasis Machine Learning", DOI 10.57152/malcom.v3i2.780 | MALCOM 3(2), 2023 | Kecemasan dari data Indonesia; domain berbeda (teks), berguna sebagai pembanding klaim |
| Darmawan et al., "Analisis Sentimen Kemungkinan Depresi dan Kecemasan pada Twitter Menggunakan SVM", DOI 10.30864/eksplora.v13i1.854 | Eksplora Informatika 13(1), 2023 | Sama, pembanding lokal |
| Sabar, Pajri & Budiani, "Classification of Student Depression Using SVM Modelling and Backward Elimination" | JAIC 10(1), 2026 | **Seleksi fitur** (backward elimination) untuk data kesehatan mental — sejalan L5 |

### 3.2 Wajah, micro-expression, dan fitur ROI

| Paper | Terbitan | Yang relevan |
|---|---|---|
| Bachtiar & Wafi, "Komparasi Metode Klasifikasi untuk Deteksi Ekspresi Wajah Dengan Fitur Facial Landmark", DOI 10.25126/jtiik.2021834434 | JTIIK 8(5), 2021 | **Facial landmark** sebagai fitur + ELM/SVM/kNN; JAFFE 213 citra; ELM terbaik acc 0,76. Preseden lokal: landmark/ROI mengalahkan citra mentah di N kecil |
| Cahyo, Zahro & Vendyansyah, "Pengenalan Ekspresi Mikro Wajah dengan Ekstraksi Fitur pada Komponen Wajah menggunakan metode LBPH" | JATI 7(1), 2023 | Ekstraksi per komponen wajah (alis, mata, mulut) — analog langsung ROI25 |
| Adiatma, Utami & Hartanto, "Pengenalan Ekspresi Wajah Menggunakan Deep Convolutional Neural Network", DOI 10.35200/explore.v11i2.478 | EXPLORE 11(2), 2021 | Baseline lokal DCNN |
| Ekawati et al., "Deteksi Emosi Menggunakan CNN Berdasarkan Ekspresi Wajah", DOI 10.31599/h0kayy31 | JSRCS 5(1), 2024 | FER2013 CNN acc 76%, **melaporkan sensitivitas dan spesifisitas** — pola pelaporan yang kita pakai |
| Edy, "Deteksi Emosi dari Ekspresi Wajah dengan Deep Learning" | INTEC 3(2), 2024 | Deteksi emosi real-time; konteks lokal |

### 3.3 Tabular & data tidak seimbang

| Paper | Terbitan | Yang relevan |
|---|---|---|
| Ismanto et al., "Analisis Perbandingan Model Fully Connected Neural Network dan TabNet untuk Klasifikasi Perawatan Pasien pada Data Tabular" | CoSciTech 5(3), 2024 | TabNet (attention-based tabular) di jurnal nasional; preseden untuk mempertahankan model tabular DL |
| Ningsih, Sani & Dewi, "Perbandingan Metode Seleksi Fitur Chi-Square dan Information Gain untuk Peningkatan Interpretabilitas dan Optimasi Kinerja Model TabNet" | TEKNOSI 11(3), 2025 | Seleksi fitur + TabNet → sejalan L5 |
| Alfin Ghozali & Bahtiar, "Systematic Literature Review: Optimasi Model Klasifikasi pada Imbalanced Data Menggunakan SMOTE, Hyperparameter Tuning, dan Ensemble Learning" | TEKNOSI 12(2), 2026 | SLR lokal: tiga obat imbalanced data = **SMOTE, tuning, ensemble** — persis L2, L4, L3 |

**Catatan penting soal paper nasional.** Hampir semuanya memakai dataset publik
besar (FER2013, JAFFE, Twitter/X) dengan **split tunggal**, dan akurasinya
76–92%. Angka itu **tidak bisa dibandingkan** dengan angka kita, karena protokol
berbeda (bukan LOSO per subjek, bukan N=56). Yang kita ambil dari mereka adalah
**preseden metode dan pengakuan keterbatasan**, bukan angka akurasinya.

---

## 4. Yang TIDAK disarankan

| Jangan | Alasan |
|---|---|
| Menyalin default resmi TabR (`d_main` 96–384) | 107.041 parameter di 44 baris (Iterasi 4.16) → memperburuk overfitting |
| Menambah fitur statis lagi | Sudah gugur: 196/608/alis → overfit, tidak membantu |
| SMOTE pada baris subjek | Di N=56 per fold, SMOTE membuat sampel sintetis dari 44 titik; risiko overfit lebih besar dari manfaat. Paper nasional memakai SMOTE pada data teks besar, bukan 44 baris. **Uji hanya kalau L2 gagal** |
| Memakai `group` sebagai fitur / koreksi prior | `group` turunan `condition` = label → bocor |
| Mengejar accuracy 70% lewat tuning | Varians seed 17,9 poin; selisih < ~10 poin tidak bisa dibedakan dari derau |
| Memakai val untuk mengevaluasi | Val dipakai memilih `best_epoch` — sudah pernah menjebak kita (Iterasi 4.15) |
| Menggabung `datatest` demi menaikkan N | Hanya ~25 subjek berlabel lengkap (bukan 49), dan instrumen labelnya (`score` 5–17) tidak bisa dipastikan sama → *label shift* + merusak perbandingan adil |
| Menghitung view kedua (`*_main.webm`) sebagai tambahan N | Orang & momen yang sama; itu augmentasi, bukan sampel independen |
| Menjalankan `--subject-norm subject` bersama `--aggregate subject` | Setelah agregasi std subjek = 0 → semua fitur jadi 0. Ditolak oleh guard `run_loso.py` |
| Menuning knop POC-ABS sebagai langkah pertama | Semua butuh re-ekstraksi jam-an, dan hanya mengubah *event mana* yang jadi fitur, bukan menambah sinyal kondisi |

---

## 5. Urutan yang disarankan

Murah → mahal, dan tiap langkah punya wasit:

| # | Langkah | Biaya | Wasit |
|---|---|---|---|
| 1 | `score = "cross-entropy"` (L4) | 1 baris config, re-run LOSO | MCC pooled + MCC per seed |
| 2 | A/B representasi 237 / 117 / ~50 fitur (L5) | 3× re-run, tanpa re-ekstraksi | MCC |
| 3 | Ambang dari val (L7) | kode siap, ikut re-run | accuracy vs 0.5 **dan** laju positif prediksi vs nyata |
| 4 | `pos_weight` di loss (L2) | 1–2 baris kode, re-run | MCC + sensitivity/specificity |
| 5 | Ensembling 15 seed (L3) | ~70 menit | **std antar seed** (turun?) |
| 6 | Kalibrasi Platt (L6) | kode baru | kurva kalibrasi + Brier |
| 7 | Pembersihan identitas / subject-norm (L1) | pindah protokol (tidak bisa dengan `--aggregate subject`) | gerbang within-subject |
| 8 | Knop POC-ABS (2b.3) | **re-ekstraksi jam-an** | hanya kalau 1–7 sudah bersih |

Langkah 1–3 hampir gratis dan **wajib** sebelum menyimpulkan apa pun, karena
tanpa itu kita masih membandingkan angka yang bias. Langkah 8 sengaja ditaruh
terakhir: ia satu-satunya yang butuh jam-an, dan mengubah *event mana* yang jadi
fitur — bukan menambah sinyal kondisi.

---

## 6. Harapan yang jujur

Yang **bisa** dicapai langkah 1–7: **model tidak bias dan tidak overfitting** —
MCC > 0 dengan CI tidak memuat 0, tidak kalah dari baseline grup di grup mana
pun, varians antar seed mengecil, dan proba yang bisa dibaca.

Yang **belum** bisa dijanjikan: accuracy 70%. Gerbang within-subject masih
menunjukkan sinyal setara efek sesi (onset 0.583 p=0.264; netral 0.528 p=0.473;
kelompok kontrol juga 25/25 "signifikan"). Selama itu belum berubah, semua
langkah di atas **merapikan cara mengukur dan menyetel model**, bukan menambah
sinyal yang tidak ada di representasi.

Kalau setelah langkah 1–8 MCC masih ≈ 0, kesimpulannya bukan "kurang tuning",
tapi **representasi POC-ABS/ROI25 tidak membawa sinyal kondisi** — dan itu
temuan yang sah serta bisa dipertahankan di sidang, asalkan dilaporkan dengan
MCC, CI, dan uji per grup seperti di dokumen bias.
