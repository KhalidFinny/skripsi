# Kenapa Akurasi Jatuh — Tinjauan Literatur 2021–2026

Fokus: menjelaskan penurunan akurasi LOSO pada pipeline
**POC-ABS (spotting + fitur) → ROI25 → TabR**, dan apa yang bisa dipakai
untuk memperkuat ketiganya tanpa mengganti POC-ABS.

Angka repo yang dirujuk (lihat `report/documentation/changes-log.md`):
LOSO roi25 level subjek acc 55.36% (= baseline mayoritas) / AUC 51.91%;
exp3 agregasi subjek acc 44.05% / AUC 41.29% (di bawah acak);
diagnostik logistik LOSO AUC 52.52%, permutation test p = 0.280;
varian antar subjek > varian dalam subjek (mulut_mean_m 0.353 vs 0.201).

---

## 1. Kesimpulan singkat (5 sebab, urut dampak)

| # | Sebab | Bukti repo | Bukti literatur |
|---|---|---|---|
| 1 | **Representasi lebih mengkodekan identitas daripada kondisi** — varian antar subjek > varian dalam subjek | changes-log Iterasi 3.9 (0.353 vs 0.201); logistik LOSO AUC 52.52%, p=0.280 | [Decoupling motion vs identity features, 2022](#id-decoupling); [cross-subject EEG review 2024](#cross-subject-review) |
| 2 | **Fitur ROI25 statis (mean/max/|x|/|y|/count di apex) membuang dinamika temporal** gerakan mikro | 20 fitur efektif, semua ringkasan statis | [TPAMI ME survey 2022](#tpami-survey); [MDMO/LMP ROI 2021–2023](#roi-mdmo); [ROI+ArcFace 2024](#roi-arcface) |
| 3 | **Baseline POC-ABS = frame-0 klip, bukan baseline netral per orang** → struktur wajah orang tetap terbawa | `USE_ABS_BASELINE=True` (Iterasi 2.2) | [SAMM/Adaptive Baseline Threshold 2018](#samm-abt); [Davison baseline 2016](#davison-baseline) |
| 4 | **Label 1 per subjek/sesi, tapi 44.424 baris frame** → metrik level frame tidak mengukur kemampuan; LOSO 1 subjek = test 1 kelas | changes-log catatan metrik; AUC per fold nan | [Varanka 2024](#varanka-leakage); [Sneaky emotions 2023](#sneaky); [EEG eval protocols 2026](#eeg-eval) |
| 5 | **TabR di N kecil + fitur berisik** — retrieval mengambil tetangga yang identitasnya sama → menghafal, bukan menggeneralisasi | 56 subjek, 20–40 fitur; val naik-turun, best_epoch sering 0 | [TabR ICLR 2024](#tabr); [Grinsztajn 2022](#grinsztajn); [TabPFN Nature 2025](#tabpfn); [ACM tabular survey 2025](#acm-survey) |

Turunan: model runtuh ke prior kelas mayoritas (sens 70.67% vs spec 43.01%,
acc = baseline 55.36%). Ini pola klasik di literatur kecil-sampel.

---

## 2. Daftar paper 2021 → sekarang

### 2.1 Evaluasi, kebocoran, dan protokol LOSO
- **Varanka et al., "Data Leakage and Evaluation Issues in Micro-Expression
  Analysis", IEEE TAFFC 15(1), 2024** (arXiv:2211.11425). Menunjukkan
  memperbaiki kebocoran data bisa **menjatuhkan performa sampai setara
  classifier acak**. Persis pola yang terlihat di repo. Wajib dikutip.
- **Moreno-Alcayde et al., "Sneaky emotions: impact of data partitions in
  affective computing", 2023** (PMC10769959). Level pemisahan
  (subjek vs video) mengubah hasil secara drastis.
- **Austin et al., "Distributional bias compromises leave-one-out
  cross-validation", 2025** (PMC12662204). LOO punya bias distribusional;
  estimasi varians tinggi.
- **"Evaluation Protocols and Cross-Subject Generalization in EEG Emotion
  Recognition", arXiv:2607.27655.** Subject-dependent ~0.999 vs subjek
  held-out 0.53 — celah besar yang sama bentuknya dengan repo.
- **scikit-learn — GroupKFold / LeaveOneGroupOut / StratifiedGroupKFold.**
  Rujukan protokol resmi: subjek = grup, test satu kelas → metrik tertentu
  tidak terdefinisi.

### 2.2 Cross-subject, identitas, dan domain shift
- **"Decoupling facial motion features and identity features for
  micro-expression recognition", 2022** (PMC9680898). Fitur identitas
  adalah gangguan; dipisah dengan Mutual Information Neural Estimator.
- **"Toward cross-subject and cross-session generalization in EEG-based
  emotion recognition: systematic review, taxonomy, and methods",
  Neurocomputing 2024** (S0925231224011251). Perbedaan fisiologis antar
  subjek membuat kategori sama punya distribusi berbeda → domain shift.
- **Shen et al., "Contrastive Learning of Subject-Invariant EEG
  Representations for Cross-Subject Emotion Recognition", IEEE TAFFC 2023.**
  Negative transfer akibat variabilitas antar subjek.
- **"Personal-Zscore: Eliminating Individual Difference for EEG-Based
  Cross-Subject Emotion Recognition".** Normalisasi per subjek.
- **Kim et al., "Domain-generalized Deep Learning for Improved
  Subject-independent Emotion Recognition Based on EEG", 2025**
  (PMC12235040). Membandingkan Deep CORAL, GroupDRO, VREx, DANN.
- **Wang et al., "DMMR: Cross-Subject Domain Generalization for EEG-based
  Emotion Recognition", AAAI 2024.**
- **"Cross-Domain Facial Expression Recognition via Disentangling Identity
  Representation", 2023.** Menanggalkan identitas untuk FER.
- **"Foundation of Affective Computing & Interaction", arXiv:2506.15497.**
  Perbedaan individu (plastisitas, morfologi, intensitas ekspresi) membuat
  generalisasi antar individu sulit; performa subject-independent masih
  rendah.

### 2.3 Micro-expression: spotting, ROI, dan baseline
- **Li et al., "Video-based Facial Micro-Expression Analysis: A Survey",
  IEEE TPAMI 2022** (arXiv:2201.12728). Protokol *subject-independent*
  (5-fold tanpa tumpang subjek), pentingnya alignment/normalisasi wajah.
- **Yap et al., "SAMM: A Spontaneous Micro-Facial Movement Dataset",
  IEEE TAFFC 9(1), 2018.** *Individualised baseline* + *Adaptive Baseline
  Threshold* (ABT); catatan eksplisit bahwa ciri wajah individual membuat
  generalisasi "almost impossible".
- **Davison et al., "Objective Micro-Facial Movement Detection Using
  FACS-Based Regions and Baseline Evaluation", arXiv:1612.05038.**
  Baseline netral per peserta + χ².
- **"Micro-Expression Recognition Algorithm Using Regions of Interest and
  the Weighted ArcFace Loss", MDPI Electronics 14(1):2, 2024.** ROI +
  optical flow; relevan untuk memperkaya ROI25.
- **"Multi-scale multi-modal micro-expression recognition",
  arXiv:2301.02969.** Protokol LOSO, dlib 68 titik, affine dari frame
  pertama.
- **MDMO / LMP — fitur statistik ROI (36 ROI) dan Local Motion Pattern.**
  Dasar historis untuk fitur per-ROI; dipakai sebagai pembanding ROI25.
- **Li et al., "From Macro to Micro (MA2MI)", arXiv:2405.16451, 2024.**
  Kekurangan data anotasi ME diatasi dengan pra-latih macro-expression.
- **"ME-TST+: Micro-expression Analysis via Temporal State...",
  arXiv:2508.08082, 2025.**
- **Duque et al., fase Riesz Pyramid untuk membedakan ME vs gerakan mata
  (2018).** Relevan langsung ke POC (berbasis fase).
- **"Micro-Expression Spotting Based on Optical Flow Feature with Boundary
  Calibration", ACM MM 2024.**
- **Zhao et al., "A two-stage 3D CNN based learning method for spontaneous
  micro-expression recognition", Neurocomputing 448, 2021.**

### 2.4 TabR dan pembelajaran tabular kecil-sampel
- **Gorishniy et al., "TabR: Unlocking the Power of Retrieval-Augmented
  Tabular Deep Learning", ICLR 2024** (arXiv:2307.14338). Kekuatan TabR =
  retrieval; **keterbatasan**: overhead, dan di dataset kecil retrieval
  cenderung mengambil tetangga yang mirip identitas.
- **Grinsztajn et al., "Why do tree-based models still outperform deep
  learning on typical tabular data?", NeurIPS 2022.** DL kalah di data
  kecil, fitur tak teratur, dan interaksi ireguler.
- **Hollmann et al., "Accurate predictions on small data with a tabular
  foundation model" (TabPFN), Nature 637, 2025.** Untuk <10.000 sampel,
  arsitektur DL biasa (termasuk MLP/TabR) kalah; perlu model prior.
- **"A Survey on Tabular Data: From Tree-based Methods to Tabular Deep
  Learning", ACM Computing Surveys, 2025.** "Tree-based methods remain
  strong baselines in low-dimensional and small-data contexts."
- **Gorishniy et al., "Revisiting Deep Learning Models for Tabular Data",
  NeurIPS 2021.**

### 2.5 Deteksi kecemasan/stres dari wajah (konteks domain)
- **"AnxietyFaceTrack: A Smartphone-Based Non-Intrusive Approach for
  Detecting Social Anxiety Using Facial Features", arXiv:2502.16106, 2025.**
  N kecil, bias model, ground truth kuesioner.
- **"Beyond Questionnaires: Video Analysis for Social Anxiety Detection",
  arXiv:2501.05461, 2025.** SAD, akurasi ~74% dengan fitur tubuh+wajah.
- **Lu et al., "Depression and anxiety detection method based on SFE-Former",
  Engineering Applications of AI, 2025.**
- **"Stress recognition: identifying relevant facial action units through
  explainable AI and machine learning", Comput. Methods Programs Biomed.,
  2024.** AU + ML; stres akut.
- **"A multimodal stress detection dataset with facial...", Scientific
  Data, 2025.** AU per subjek bervariasi → korelasi AU-stres berbeda antar
  orang.

---

## 3. Arah memperkuat (tanpa ganti POC-ABS)

Prinsip: **akar masalah ada di representasi (hulu), bukan di TabR.**
Tiga sumbu perbaikan:

**A. Hapus identitas dari fitur (prioritas 1).**
- POC-ABS: ganti baseline frame-0 klip menjadi **baseline netral per
  subjek** (individualised baseline ala SAMM/ABT). Ini paling murah dan
  paling langsung menyerang sebab #1 dan #3.
- Normalisasi per subjek: *personal z-score* fitur terhadap statistik
  subjek sendiri, bukan statistik global train.
- Opsional: lapisan *identity decoupling* (MINE) / adversarial
  subject-invariance bila fitur tetap membawa identitas.

**B. Perkaya ROI25 agar punya dinamika temporal (prioritas 2).**
- Tetap 5 ROI × sinyal POC-ABS, tapi simpan **onset–apex–offset** (delta
  dan slope), bukan hanya statistik apex.
- Tambah deskriptor temporal per ROI (mis. ringkasan lintasan gerak dalam
  event) mengikuti keluarga MDMO/LMP.
- Jaga jumlah fitur kecil (saat ini 20 efektif) — di N=56 subjek, menambah
  fitur statis hanya menambah derau.

**C. Benahi protokol LOSO + pilihan model (prioritas 3).**
- Unit keputusan = **subjek**; hanya laporkan metrik level subjek
  (acc, sens, spec, PPV, NPV, AUC antar subjek) + interval kepercayaan.
- Metrik level frame antar-fold **tidak dilaporkan sebagai performa**.
- Baseline wajib: logistik/GBDT pada matriks fitur yang sama +
  permutation test (sudah ada di Iterasi 3.9 — pertahankan sebagai kontrol).
- Pertimbangkan GBDT/TabPFN sebagai pembanding TabR di N=56; bila TabR
  tetap dipakai, jalankan pada baris level subjek dengan retrieval yang
  tidak bocor identitas.

**Kontrol kualitas:** setiap perubahan harus diuji dengan A/B pada protokol
LOSO yang sama, dan angka lama (bocor subjek) tidak dipakai sebagai
pembanding.

---

## 4. Yang sudah gugur (jangan diulang)

- Menambah fitur statis (196/608/alis) → overfit, tidak membantu.
- Rebalance frame / agregasi clip → tidak menyentuh akar (representasi).
- Agregasi subjek tanpa perbaikan fitur → di bawah acak (exp3).
- Re-tune TabR pada representasi cacat → tidak bisa memperbaiki hulu.
