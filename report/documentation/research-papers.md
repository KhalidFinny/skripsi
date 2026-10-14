# Daftar Paper Riset — Penurunan Akurasi LOSO (2021 → sekarang)

Daftar sitasi untuk `report/findings/literature-accuracy-drop-2021-2026.md`
(analisis lengkapnya ada di situ; berkas ini yang jadi daftar rujukan).

Konteks proyek: `POC-ABS → ROI25 → TabR` diuji LOSO (1 subjek/fold).
Hasil: accuracy 55.36% = baseline mayoritas, AUC 51.91% (acak 50%).

Fokus 2021 → sekarang. Entri pra-2021 hanya bila jadi dasar langsung dan
ditandai **[pra-2021]**.

---

## Pemetaan sebab → paper → perbaikan

| Sebab | Paper pendukung | Perbaikan di repo |
|---|---|---|
| 1. Fitur mengkodekan identitas | [6](#6-decoupling-motion-vs-identity), [7](#7-cross-subject-review), [8](#8-subject-invariant-contrastive), [9](#9-personal-zscore), [13](#13-foundation-affective), [38](#38-stressgat) | `--subject-norm subject` (normalisasi per subjek) |
| 2. ROI25 statis, dinamika hilang | [14](#14-tpami-me-survey), [17](#17-roi-arcface), [18](#18-multi-scale-multimodal), [22](#22-me-survey-frontiers), [41](#41-driving-stress) | `scripts/build_temporal_features.py` (onset→apex→offset) |
| 3. Baseline = frame onset, bukan netral | [15](#15-samm), [16](#16-davison-baseline), [25](#25-riesz-phase), [38](#38-stressgat) | `SPOT_SAVE_NEUTRAL` + `--baseline neutral` |
| 4. Label per subjek, metrik per frame | [1](#1-varanka-leakage), [2](#2-sneaky-emotions), [3](#3-loo-bias), [4](#4-eeg-eval-protocols), [5](#5-sklearn-groupcv) | Level subjek + Wilson CI di `collect_loso_results.py` |
| 5. TabR di N kecil | [26](#26-tabr), [27](#27-grinsztajn), [28](#28-tabpfn), [29](#29-acm-tabular-survey), [30](#30-revisiting-tabular) | `scripts/run_loso_baseline.py` (logistik + GBDT + permutation) |
| Bias metrik & pelaporan | [59](#59-mcc-vs-auc), [60](#60-mcc-untuk-classifier-optimal-di-data-tak-seimbang), [61](#61-mcc-terdegradasi) | MCC + balanced accuracy di `collect_loso_results.py` |
| Bias ambang keputusan | [62](#62-threshold-moving-untuk-klasifikasi-tak-seimbang), [63](#63-statistik-j-youden) | ambang Youden dari val per fold (`val_split.csv`) |
| Bias kalibrasi | [64](#64-platt-scaling-setelah-undersampling), [65](#65-kalibrasi-probabilitas-scikit-learn) | rencana: Platt (bukan isotonic) di val |
| Bias komposisi / Simpson | [66](#66-simpsons-paradox-dan-fairness-ml), [67](#67-deteksi-simpsons-paradox) | tabel per grup + baseline grup di `collect_loso_results.py` |
| Bias prior / label shift | [68](#68-estimasi-label-shift), [69](#69-distribution-shift-d2l) | didokumentasikan; koreksi tidak dijalankan (N terlalu kecil) |
| De-bias: fitur subject-invariant | [70](#70-bias-fairness-facial-asp), [71](#71-fer-dataset-bias), [72](#72-domain-incremental-bias), [73](#73-fairness-small-dataset), [74](#74-mgp-bias-mitigation), [75](#75-subject-based-da-fer), [76](#76-dbmf-domain-adaptation) | rencana: pembersihan identitas + `--subject-norm subject` (lihat `strategi-bebas-bias-dan-overfitting.md` L1) |
| De-bias: kelas tidak seimbang | [77](#77-dicc), [78](#78-cucn), [79](#79-focal-loss-gcn-fer), [87](#87-teknosi-hybrid-kecemasan-smote) | rencana: `pos_weight` di loss TabR (L2) |
| Overfitting & N kecil | [80](#80-overfitting-mitigation-survey), [81](#81-few-shot-fer), [82](#82-cross-subject-eeg-2026) | ensembling 15 seed + reduksi dimensi (L3, L5) |
| Tabular DL (pembanding) | [83](#83-tabnet), [97](#97-coscitech-tabnet), [98](#98-teknosi-tabnet-seleksi-fitur) | TabNet sebagai model tabular DL pembanding |
| AU & micro-expression | [84](#84-me-detection-review-2025), [94](#94-jati-lbph-komponen-wajah) | `build_temporal_features.py` (onset→apex→offset) |
| Konteks & preseden nasional | [85](#85-rabit-kecemasan-cnn), [86](#86-jaic-depresi-mobilenet), [88](#88-mib-stres-mahasiswa), [89](#89-smatika-kesehatan-mental), [90](#90-malcom-kecemasan-twitter), [91](#91-eksplora-svm-twitter), [92](#92-jaic-depresi-backward-elimination), [93](#93-jtiik-facial-landmark), [95](#95-explore-dcnn), [96](#96-jsrcs-cnn-fer2013), [99](#99-teknosi-slr-imbalanced), [100](#100-intec-emosi-deep-learning) | pembanding & pengakuan keterbatasan dari literatur Indonesia |
| Target 70% & overfitting | [38](#38-stressgat)–[46](#46-sample-size-medrxiv), [48](#48-cochrane-stai) | Lihat `report/findings/research-strengthen-loso.md` |


---

## 1. Evaluasi, kebocoran data, dan protokol LOSO

### 1. Varanka leakage
Varanka, T., et al. **"Data Leakage and Evaluation Issues in Micro-Expression
Analysis."** IEEE Transactions on Affective Computing, 15(1), 2024.
arXiv:2211.11425.
<https://arxiv.org/abs/2211.11425>
*Relevansi:* menunjukkan memperbaiki kebocoran data bisa menjatuhkan performa
sampai setara classifier acak — pola yang persis terlihat di proyek ini.
Rujukan wajib.

### 2. Sneaky emotions
Moreno-Alcayde, Y., et al. **"Sneaky emotions: impact of data partitions in
affective computing."** 2023. PMC10769959.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC10769959/>
*Relevansi:* level pemisahan data (subjek vs video) mengubah hasil drastis.

### 3. LOO bias
Austin, G. I., et al. **"Distributional bias compromises leave-one-out
cross-validation."** 2025. PMC12662204.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC12662204/>
*Relevansi:* LOO punya bias distribusional dan varians tinggi sebagai
estimator — alasan melaporkan interval kepercayaan, bukan angka tunggal.

### 4. EEG eval protocols
**"Evaluation Protocols and Cross-Subject Generalization in EEG Emotion
Recognition."** arXiv:2607.27655.
<https://arxiv.org/pdf/2607.27655>
*Relevansi:* subject-dependent ≈ 0.999 vs subjek held-out ≈ 0.53. Bentuk celah
yang sama dengan proyek ini.

### 5. sklearn GroupCV
scikit-learn. **"Cross-validation: evaluating estimator performance"** —
`GroupKFold`, `LeaveOneGroupOut`, `StratifiedGroupKFold`.
<https://scikit-learn.org/stable/modules/cross_validation.html>
*Relevansi:* rujukan protokol resmi; subjek = grup, dan fold dengan satu kelas
membuat metrik klasifikasi tertentu tidak terdefinisi.

---

## 2. Cross-subject, identitas, dan domain shift

### 6. Decoupling motion vs identity
**"Decoupling facial motion features and identity features for
micro-expression recognition."** 2022. PMC9680898.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC9680898/>
*Relevansi:* fitur identitas adalah **gangguan** untuk MER; dipisahkan dengan
Mutual Information Neural Estimator. Dasar langsung sebab #1.

### 7. Cross-subject review
**"Toward cross-subject and cross-session generalization in EEG-based emotion
recognition: Systematic review, taxonomy, and methods."** Neurocomputing, 2024.
S0925231224011251.
<https://www.sciencedirect.com/science/article/pii/S0925231224011251>
*Relevansi:* perbedaan fisiologis antar subjek membuat kategori yang sama
punya distribusi berbeda → domain shift; taksonomi metode penanganannya.

### 8. Subject-invariant contrastive
Shen, X., Liu, X., Hu, X., Zhang, D., Song, S. **"Contrastive Learning of
Subject-Invariant EEG Representations for Cross-Subject Emotion
Recognition."** IEEE Transactions on Affective Computing, 14(3), 2023.
<https://dl.acm.org/doi/abs/10.1109/TAFFC.2022.3164516>
*Relevansi:* negative transfer akibat variabilitas antar subjek.

### 9. Personal-Zscore
**"Personal-Zscore: Eliminating Individual Difference for EEG-Based
Cross-Subject Emotion Recognition."**
*Relevansi:* normalisasi per subjek untuk membuang perbedaan individu — dasar
langsung `--subject-norm subject`.

### 10. Domain-generalized subject-independent
Kim, J. H., et al. **"Domain-generalized Deep Learning for Improved
Subject-independent Emotion Recognition Based on Electroencephalography."**
2025. PMC12235040.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC12235040/>
*Relevansi:* membandingkan Deep CORAL, GroupDRO, VREx, DANN.

### 11. DMMR
Wang, Y., et al. **"DMMR: Cross-Subject Domain Generalization for EEG-based
Emotion Recognition."** AAAI 2024.
<https://ojs.aaai.org/index.php/AAAI/article/view/27819>
*Relevansi:* domain generalization lintas subjek dengan self-supervised
multi-decoder.

### 12. Disentangling identity FER
**"Cross-Domain Facial Expression Recognition via Disentangling Identity
Representation."** 2023.
*Relevansi:* menanggalkan identitas untuk FER lintas domain.

### 13. Foundation affective
**"Foundation of Affective Computing & Interaction."** arXiv:2506.15497.
<https://arxiv.org/html/2506.15497v1>
*Relevansi:* perbedaan individu (plastisitas, morfologi, intensitas ekspresi)
membuat generalisasi antar individu sulit; performa subject-independent masih
rendah.

---

## 3. Micro-expression: spotting, ROI, dan baseline

### 14. TPAMI ME survey
Li, Y., Wei, J., Liu, Y., Kauttonen, J., Zhao, G. **"Deep Learning for
Micro-Expression Recognition: A Survey."** IEEE Transactions on Affective
Computing, 13(4), 2028–2046, 2022. DOI 10.1109/TAFFC.2022.3205170.
<https://arxiv.org/pdf/2201.12728>
*Relevansi:* protokol *subject-independent* (5-fold tanpa tumpang subjek),
pentingnya alignment/normalisasi wajah, taksonomi fitur.

### 15. SAMM
Davison, A. K., Lansley, C., Ng, C. C., Tan, K., Yap, M. H. **"SAMM: A
Spontaneous Micro-Facial Movement Dataset."** IEEE Transactions on Affective
Computing, 9(1), 2018. **[pra-2021]**
<https://ieeexplore.ieee.org/document/7492264>
*Relevansi:* *individualised baseline* + *Adaptive Baseline Threshold* (ABT);
menyatakan ciri wajah individual membuat generalisasi "almost impossible".
Dasar langsung perbaikan baseline (sebab #3).

### 16. Davison baseline
Davison, A. K., et al. **"Objective Micro-Facial Movement Detection Using
FACS-Based Regions and Baseline Evaluation."** arXiv:1612.05038. **[pra-2021]**
<https://arxiv.org/abs/1612.05038>
*Relevansi:* baseline netral per peserta + χ² jarak; AUC 0.7512 (SAMM) /
0.7261 (CASME II).

### 17. ROI ArcFace
**"Micro-Expression Recognition Algorithm Using Regions of Interest and the
Weighted ArcFace Loss."** MDPI Electronics, 14(1):2, 2024.
<https://www.mdpi.com/2079-9292/14/1/2>
*Relevansi:* ROI + optical flow; cara memperkaya ROI25 tanpa mengubah
paradigma.

### 18. Multi-scale multimodal
**"Multi-scale multi-modal micro-expression recognition."** arXiv:2301.02969.
<https://arxiv.org/pdf/2301.02969>
*Relevansi:* protokol LOSO, dlib 68 titik, affine dari frame pertama.

### 19. MA2MI
Li, H., Niu, H., Zhao, F. **"From Macro to Micro: Boosting micro-expression
recognition via pre-training on macro-expression videos."** arXiv:2405.16451,
2024.
<https://arxiv.org/pdf/2405.16451>
*Relevansi:* mengatasi kelangkaan anotasi ME; MIACNet memisahkan fitur posisi
wajah dan fitur aksi.

### 20. ME-TST+
**"ME-TST+: Micro-expression Analysis via Temporal State..."** arXiv:2508.08082,
2025.
<https://www.alphaxiv.org/abs/2508.08082v1>
*Relevansi:* pemodelan state temporal untuk ME.

### 21. ME spotting boundary calibration
**"Micro-Expression Spotting Based on Optical Flow Feature with Boundary
Calibration."** ACM Multimedia 2024.
<https://dl.acm.org/doi/10.1145/3664647.3689142>
*Relevansi:* ROI + optical flow untuk spotting; batas onset/offset.

### 22. ME survey Frontiers
**"A Survey of Automatic Facial Micro-Expression Analysis: Databases, Methods,
and Challenges."** Frontiers in Psychology, 2018. **[pra-2021]**
<https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2018.01128/full>
*Relevansi:* ringkasan pendekatan *individualised baseline* dan kesulitan
generalisasi.

### 23. Two-stage 3D CNN
Zhao, S., et al. **"A two-stage 3D CNN based learning method for spontaneous
micro-expression recognition."** Neurocomputing, 448, 2021.
*Relevansi:* referensi MER berbasis DL pada data ME spontan.

### 24. MDMO / LMP
**MDMO** (normalized statistical feature berbasis 36 ROI) dan **Local Motion
Pattern (LMP)** (25 ROI).
*Relevansi:* keluarga fitur statistik per-ROI — pembanding historis langsung
untuk ROI25.

### 25. Riesz phase
Duque, C. A., et al. (Riesz Pyramid untuk membedakan ME vs gerakan mata),
2018. **[pra-2021]**
*Relevansi:* analisis variasi fase antar frame — relevan langsung ke POC
(berbasis fase).

---

## 4. TabR dan pembelajaran tabular kecil-sampel

### 26. TabR
Gorishniy, Y., Rubachev, I., Kartashev, N., Shlenskii, D., Kotelnikov, A.,
Babenko, A. **"TabR: Unlocking the Power of Retrieval-Augmented Tabular Deep
Learning."** ICLR 2024. arXiv:2307.14338.
<https://arxiv.org/abs/2307.14338>
*Relevansi:* model yang dipakai. Kekuatannya = retrieval; keterbatasan yang
dinyatakan penulis: overhead, dan pada data kecil retrieval cenderung
mengambil tetangga yang mirip identitas.

### 27. Grinsztajn
Grinsztajn, L., Oyallon, E., Varoquaux, G. **"Why do tree-based models still
outperform deep learning on typical tabular data?"** NeurIPS 2022.
*Relevansi:* DL kalah di data kecil, fitur tak teratur, interaksi ireguler —
persis rezim N = 56 subjek.

### 28. TabPFN
Hollmann, N., et al. **"Accurate predictions on small data with a tabular
foundation model."** Nature, 637, 2025.
<https://www.nature.com/articles/s41586-024-08328-6>
*Relevansi:* untuk < 10.000 sampel, arsitektur DL biasa (termasuk MLP/TabR)
kalah dari model dengan prior.

### 29. ACM tabular survey
**"A Survey on Tabular Data: From Tree-based Methods to Tabular Deep
Learning."** ACM Computing Surveys, 2025.
<https://dl.acm.org/doi/abs/10.1145/3807777>
*Relevansi:* "tree-based methods remain strong baselines in low-dimensional
and small-data contexts."

### 30. Revisiting tabular
Gorishniy, Y., Rubachev, I., Khrulkov, V., Babenko, A. **"Revisiting Deep
Learning Models for Tabular Data."** NeurIPS 2021.
*Relevansi:* dasar arsitektur TabR/FT-Transformer.

---

## 5. Deteksi kecemasan/stres dari wajah

### 31. AnxietyFaceTrack
**"AnxietyFaceTrack: A Smartphone-Based Non-Intrusive Approach for Detecting
Social Anxiety Using Facial Features."** arXiv:2502.16106, 2025.
<https://arxiv.org/html/2502.16106v1>
*Relevansi:* N kecil, bias model, ground truth kuesioner; keterbatasan yang
sama dengan proyek ini.

### 32. Beyond Questionnaires
**"Beyond Questionnaires: Video Analysis for Social Anxiety Detection."**
arXiv:2501.05461, 2025.
<https://arxiv.org/pdf/2501.05461>
*Relevansi:* SAD dari fitur tubuh+wajah; akurasi ~74% pada split internal.

### 33. SFE-Former
Lu, L., et al. **"Depression and anxiety detection method based on
SFE-Former."** Engineering Applications of Artificial Intelligence, 2025.
<https://www.sciencedirect.com/science/article/abs/pii/S0952197625003549>
*Relevansi:* model ekspresi wajah sekuensial untuk depresi/kecemasan.

### 34. Stress AU + XAI
**"Stress recognition: identifying relevant facial action units through
explainable artificial intelligence and machine learning."** Computer Methods
and Programs in Biomedicine, 2024.
<https://www.sciencedirect.com/science/article/abs/pii/S0169260724005005>
*Relevansi:* kombinasi AU yang menandakan stres berbeda per jenis stressor.

### 35. Multimodal stress dataset
**"A multimodal stress detection dataset with facial..."** Scientific Data,
2025.
<https://www.nature.com/articles/s41597-025-05812-0>
*Relevansi:* korelasi AU–stres berbeda antar individu.

### 36. TSDNet
Zhang, H., Feng, L., Li, N., Jin, Z., Cao, L. **"Video-Based Stress Detection
through Deep Learning."** Sensors, 20(19):5552, 2020. **[pra-2021]**
<https://pmc.ncbi.nlm.nih.gov/articles/PMC7582689/>
*Relevansi:* akurasi 85.42% pada dataset 2.092 klip, tapi split internal —
pembanding untuk menunjukkan bahaya mengutip angka tanpa protokol subjek.

### 37. Giannakakis
Giannakakis, G., et al. **"Stress and anxiety detection using facial cues from
videos."** Biomedical Signal Processing and Control, 2017. **[pra-2021]**
*Relevansi:* dasar fitur wajah untuk stres/kecemasan.

---

## Catatan pembacaan

- Angka tinggi di literatur (80–95%) umumnya berasal dari **split internal**
  atau protokol yang tidak subjek-disjoint. Setelah protokol subjek-disjoint
  diterapkan, angka MER turun ke kisaran 50–60% (lihat #1 dan #14).
- Karena itu, angka proyek ini (accuracy = baseline mayoritas, AUC ≈ acak)
  **konsisten** dengan literatur begitu kebocoran subjek dihilangkan — bukan
  anomali.
- Rujukan [6], [9], [15], [16] adalah dasar langsung untuk perbaikan yang
  dipakai; [27]–[29] adalah dasar untuk menambahkan baseline sederhana.

---

## 6. Memperkuat LOSO: target 70% dan overfitting (2021 → sekarang)

Analisis lengkap: `report/findings/research-strengthen-loso.md`.

### 38. StressGAT
**"Explainable graph attention network for stress recognition (StressGAT) via
differential action units."** arXiv:2607.20819, 2026.
<https://arxiv.org/pdf/2607.20819>
*Relevansi:* **88.62% LOSO, 58 peserta**, dengan mekanisme inti **Differential
Action Units** — fitur dinormalkan terhadap baseline netral tiap orang untuk
memisahkan ciri anatomi permanen dari sinyal stres. Menyebut persis masalah
kita: *"distributional shift in which the neutral configuration of one
individual may overlap with the stressed phenotype of another."*
Dasar terkuat untuk Lever C/D/E. **Catatan: labelnya stres terinduksi, bukan
trait kuesioner.**

### 39. AnxietyFaceTrack (IEEE TAFFC 2026)
Sahu, N. K., Gupta, S., Lone, H. R. **"AnxietyFaceTrack: A Smartphone-Based
Non-Intrusive Approach for Detecting State Anxiety Using Facial Features."**
IEEE Transactions on Affective Computing, 17(2), 2026.
<https://www.computer.org/csdl/journal/ta/2026/02/11399911/2eePrMzWa9a>
(preprint: <https://arxiv.org/html/2502.16106v1>)
*Relevansi:* N=91, kamera smartphone. **3D facial landmarks 88% multiclass /
91% binary; head pose 85% / 89.66%; action units 59% / 73%; eye gaze 53%.**
Kontributor utama: rotasi kepala sumbu-x, landmark tepi wajah, landmark mata.
**Peringatan: validasinya 5-fold CV, bukan LOSO.**

### 40. Baseline normalization inflation
**"Baseline normalization choices inflate classification performance in
wearable health monitoring: quantification and mitigation strategies."**
Frontiers in Digital Health, 2026.
<https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2026.1827279/pdf>
*Relevansi:* normalisasi yang tumpang tindih dengan test menggelembungkan
balanced accuracy **3–13 poin**, dan ini terjadi **walaupun partisi subjek
tetap ketat**. Peringatan metodologis untuk desain baseline netral kita:
statistik normalisasi harus dihitung hanya dari data subjek itu sendiri dan
tidak boleh tumpang tindih dengan window evaluasi.

### 41. Driving stress multimodal
**"Combining Facial Videos and Biosignals for Stress Estimation During
Driving."** arXiv:2601.04376, 2026.
<https://arxiv.org/html/2601.04376v2>
*Relevansi:* menyimpulkan *"stress is primarily encoded in temporal
dynamics—particularly velocity-based descriptors—rather than static feature
levels"*; fusi facial + physiological via cross-attention mencapai
**AUROC 0.92 ± 0.04**. Dasar untuk Lever D (variabilitas temporal, bukan level
statis).

### 42. UBFC-Phys multimodal
**"A multimodal framework for exploring behavioural cues for stress
detection."** ACM Multimedia 2025.
<https://dl.acm.org/doi/10.1145/3716553.3750797>
*Relevansi:* fusi penuh 93% vs 70.5% dengan **label tugas** — *"label self-report
menaikkan >20 poin"*. Bukti bahwa kualitas label sering lebih menentukan
daripada fitur.

### 43. Beyond Questionnaires
**"Beyond Questionnaires: Video Analysis for Social Anxiety Detection."**
arXiv:2501.05461, 2025.
<https://arxiv.org/pdf/2501.05461>
*Relevansi:* gaze sendirian 68% (1D-CNN), tapi digabung fitur lain justru
turun. Head pose + body pose + AU juga berkontribusi.

### 44. Few-shot hidden emotion
**"Rethinking the Role of Feature Engineering and Learning Strategies in
Few-Shot Hidden Emotion Recognition."** arXiv:2606.31249, 2026.
<https://arxiv.org/html/2606.31249v1>
*Relevansi:* fitur foundation model berdimension tinggi → **train >80%,
test ~50%**. Jebakan overfitting pada data sedikit; mendukung argumen
mengurangi dimensi fitur dan memakai offset/base + MIL pooling.

### 45. Self-supervised ME (SelfME / Das)
Fan, X., Chen, X., Jiang, M., Shahid, A. R., Yan, H. **"SelfME: Self-supervised
Motion Learning for Micro-expression Recognition."** CVPR 2023.
Das, A., et al. **"Interpretable Self-Supervised Facial Micro-Expression
Learning."** 2021. PMC8252663.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC8252663/>
*Relevansi:* pra-latih self-supervised bisa melatih dengan data sangat sedikit
— jalur kalau mau tetap di ranah micro-expression.

### 46. Sample size requirements (medRxiv)
**"Sample Size Requirements for Machine Learning Classification in Clinical
Tabular Data."** medRxiv, 2025.
<https://www.medrxiv.org/content/10.1101/2025.08.19.25333999v1.full-text>
*Relevansi:* kebutuhan median 190 (RF) / 269 (NN) / 480 (XGBoost) sampel.

### 47. Zantvoort — N minimum
Zantvoort, K., et al. **"Finding the best fit: minimum dataset sizes for
machine learning in mental health."** npj Digital Medicine, 2024.
<https://www.nature.com/articles/s41746-024-01360-w>
*Relevansi:* mengusulkan **N = 500–1000** sebagai minimum untuk ML kesehatan
mental. Kita punya 56.

### 48. Cochrane STAI
**"State-Trait Anxiety Inventory (STAI) for detecting anxiety disorders in
adults."** Cochrane Database of Systematic Reviews, 2025. CD015458.
<https://www.cochrane.org/evidence/CD015458_how-well-does-the-state-trait-anxiety-inventory-stai-identify-anxiety-disorders>
*Relevansi:* terhadap wawancara klinis, **AUC 0.81, sensitivitas tinggi,
spesifisitas 0.57**. Plafon keandalan label kuesioner — model tidak bisa
melebihi keandalan labelnya.

### 49. Grimm — GAD-7 dari video
Grimm, et al. **"Video-based anxiety classification using GAD-7."** 2022.
*Relevansi:* **AUC 0.71** untuk kecemasan dari fitur wajah dengan label GAD-7.
Angka realistis untuk tugas ini, bukan 85–95%.

### 50. MDPI scoping review
**"Scoping Review of ML Approaches in Anxiety Detection from In-Lab to
In-the-Wild."** Applied Sciences, 15(18):10099, 2025.
<https://www.mdpi.com/2076-3417/15/18/10099>
*Relevansi:* studi dengan **LOSO melaporkan akurasi 47.97–72.73%**, jauh lebih
rendah dari k-fold. Batas atas realistis untuk target kita.

### 51. Sun — rPPG + behavioral
Sun, et al. **"Estimating Stress in Online Meetings by Remote Physiological
Signal and Behavioral Features."** 2022.
<https://www.academia.edu/104394252/>
*Relevansi:* rPPG saja **78.75%**, fusi rPPG + behavioral **82.50%**. Dasar
Lever F (modalitas kedua), dengan catatan rPPG rapuh terhadap gerakan.

---

## 7. Konfigurasi TabR untuk N kecil (2021 → sekarang)

Analisis: `report/findings/research-tabr-config-small-data.md`.

### 52. TabM — parameter-efficient ensembling
Gorishniy, Y., Rubachev, I., Kartashev, N., et al. **"TabM: Advancing Tabular
Deep Learning with Parameter-Efficient Ensembling."** ICLR 2025.
arXiv:2410.24210. <https://arxiv.org/html/2410.24210>
*Relevansi:* menunjukkan **deep ensemble** menaikkan performa tabular DL, dan
`TabM†` (dengan embeddings) lebih baik dari tanpa. Juga menandai **`TabR‡`**
(TabR + periodic embeddings) sebagai varian pembanding — bukan default.
Dasar untuk Lever 1 (ensembling).

### 53. On Embeddings for Numerical Features
Gorishniy, Y., Rubachev, I., Babenko, A. **"On Embeddings for Numerical
Features in Tabular Deep Learning."** NeurIPS 2022. arXiv:2203.05556.
<https://arxiv.org/abs/2203.05556>
*Relevansi:* embeddings fitur kontinu (PLR/PLE) meningkatkan tabular DL dan
mempersempit jarak dengan GBDT — **tapi menambah parameter**. Di 44 baris
train itu menambah overfitting. Config resmi TabR sendiri memakai
`num_embeddings = "__null__"`. Karena itu **tidak** direkomendasikan di sini.

### 54. Tabular DL when d ≫ n (PLATO)
Ruiz, C., Ren, H., Huang, K., Leskovec, J. **"Tabular Deep Learning when
d ≫ n by Using an Auxiliary Knowledge Graph."** NeurIPS 2022 AI for Science
Workshop. <https://openreview.net/pdf?id=xbe-b4EpphA>
*Relevansi:* rezim kita tepat (`d/n = 5,39`). Menyatakan model ML "struggle to
achieve strong performance" di `d ≫ n`, dan bahwa **metode dominan adalah
reduksi dimensi, seleksi fitur, penalti regularisasi, dan ensemble model
lemah** — bukan menambah kapasitas DL. Dasar utama Lever 2.

### 55. Feature dimensionality reduction — review
**"Feature dimensionality reduction: a review."** Complex & Intelligent
Systems, 2021. <https://link.springer.com/article/10.1007/s40747-021-00637-x>
*Relevansi:* karakteristik *small sample* (dimensi fitur > jumlah sampel):
"easily leads to inadequate training or over-fitting phenomenon and drops the
classification ability of the classifier"; matriks kovarians menjadi singular
sehingga reduksi dimensi klasik pun sulit. Batas praktis: PCA maksimum `n−1`
komponen (di kita: 43).

### 56. GRACES — seleksi fitur HDLSS
**"Graph convolutional network-based feature selection for high-dimensional
and low-sample size data."** Bioinformatics, 39(4), 2023.
<https://academic.oup.com/bioinformatics/article/39/4/btad135/7135826>
*Relevansi:* "most of them fail under the high-dimensional and low-sample size
(HDLSS) setting due to the challenge of overfitting" — dan teknik pengurang
overfitting yang dipakai (dropout berganda, noise Gaussian, koreksi F).

### 57. Bias–variance perspective on tabular data
**"A Bias–Variance Perspective on Tabular Data."** arXiv:2512.05469, 2025.
<https://arxiv.org/html/2512.05469v1>
*Relevansi:* **kapan** variance reduction berhasil: "helps most when base
learners have high variance **and** the signal-to-noise ratio supports
averaging out idiosyncratic errors rather than structural bias". Ini peringatan
langsung untuk Lever 1 kita: kalau SNR ≈ 0, ensembling menstabilkan ke arah
kelas mayoritas, bukan menaikkan akurasi.

### 58. CorrBoost — seleksi fitur untuk DNN tabular
**"A feature selection technique and utility of tabular deep neural
networks."** Neural Computing and Applications, 2025.
<https://dl.acm.org/doi/10.1007/s00521-025-11648-x>
*Relevansi:* menggabungkan analisis korelasi dan XGBoost untuk mengatasi
dimensi fitur pada DNN tabular.


---

## Bias, ambang, dan kalibrasi

Bagian ini melayani `report/findings/analisis-bias-loso.md`. Masalahnya:
di data 45/55 dengan N=56, **accuracy saja menyesatkan** — model bisa terlihat
menang di pooled padahal kalah di setiap subgrup.

### 59. MCC vs AUC
Chicco, D., Jurman, G. **"The Matthews correlation coefficient (MCC) should
replace the ROC AUC as the standard metric for assessing binary
classification."** BioData Mining, 16(4), 2023. DOI 10.1186/s13040-023-00322-4.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC9938573/>
*Relevansi:* F1 dan accuracy "can generate inflated overoptimistic results,
especially on positively-imbalanced datasets". MCC adalah satu-satunya rate yang
memaksimalkan keempat rate dasar sekaligus. Dipakai untuk membenarkan MCC sebagai
angka utama di `collect_loso_results.py`.

### 60. MCC untuk classifier optimal di data tak seimbang
Boughorbel, S., Jarray, F., El-Anbari, M. **"Optimal classifier for imbalanced
data using Matthews Correlation Coefficient metric."** PLOS ONE,
12(6):e0177678, 2017. **[pra-2021]**
<https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0177678>
*Relevansi:* "the use of inadequate performance metrics, such as accuracy, lead
to poor generalization results because the classifiers tend to predict the
largest size class" — persis pola specificity 0.74 / sensitivity 0.41 di repo.

### 61. MCC terdegradasi
**"On the performance of Matthews correlation coefficient (MCC) for imbalanced
dataset."** Pattern Recognition Letters, 2020. S016786552030115X. **[pra-2021]**
<https://www.sciencedirect.com/science/article/abs/pii/S016786552030115X>
*Relevansi:* **bantahan wajib** — "MCC deteriorates seriously when the dataset in
classification are imbalanced", MCC "is not a balanced measurement". Karena itu
laporan menampilkan accuracy + balanced accuracy + MCC bersama, bukan menukar
accuracy dengan MCC saja.

### 62. Threshold moving untuk klasifikasi tak seimbang
Brownlee, J. **"A Gentle Introduction to Threshold-Moving for Imbalanced
Classification."** Machine Learning Mastery.
<https://www.machinelearningmastery.com/threshold-moving-for-imbalanced-classification/>
*Relevansi:* ambang 0.5 default "is the default threshold for interpreting
probabilities to class labels" dan bukan pilihan optimal di data tak seimbang;
ambang harus dipilih di **validation**, bukan test. Dasar `val_split.csv`.

### 63. Statistik J Youden
Youden, W. J. **"Index for rating diagnostic tests."** Cancer, 3(1):32–35, 1950.
**[pra-2021]**
<https://en.wikipedia.org/wiki/Youden%27s_J_statistic>
*Relevansi:* `J = Sensitivity + Specificity − 1 = TPR − FPR`; ambang dengan J
terbesar. Dipakai di `val_threshold_metrics()`.

### 64. Platt scaling setelah undersampling
**"Using Platt's scaling for calibration after undersampling."**
arXiv:2410.18144, 2024.
<https://arxiv.org/pdf/2410.18144>
*Relevansi:* pada data tak seimbang, Platt dengan transformasi logit + GAM paling
tahan saat model mendorong proba ke ekstrem, dan isotonic kalah di sampel kecil.
Relevan karena proba repo terkompresi (bin 0.08 → laju nyata 0.42).

### 65. Kalibrasi probabilitas (scikit-learn)
scikit-learn. **"Probability calibration"**, §1.16.
<https://scikit-learn.org/stable/modules/calibration.html>
*Relevansi:* isotonic "is more prone to overfitting, especially on small
datasets"; isotonic baru setara/lebih baik "when there is enough data
(greater than ~ 1000 samples)". Di 56 subjek → pakai sigmoid/Platt.

### 66. Simpson's paradox dan fairness ML
**"Detecting Simpson's Paradox: A Step Towards Fairness in Machine
Learning."** 2022. ResearchGate 363061053.
<https://www.researchgate.net/publication/363061053_Detecting_Simpson's_Paradox_A_Step_Towards_Fairness_in_Machine_Learning>
*Relevansi:* "if confounding effects are not properly addressed in automatic
data mining, the outcomes of data analysis can be completely opposite". Persis
kasus repo: pooled menang, tiap subgrup kalah.

### 67. Deteksi Simpson's paradox
**"Detecting Simpson's Paradox."** AAAI.
<https://cdn.aaai.org/ocs/17641/17641-77733-1-PB.pdf>
*Relevansi:* algoritma identifikasi variabel confounding; dasar untuk menyadari
bahwa `group` adalah confounding yang tidak boleh dipakai sebagai fitur.

### 68. Estimasi label shift
**"A Unified View of Label Shift Estimation."** NeurIPS 2020. **[pra-2021]**
<https://proceedings.neurips.cc/paper/2020/file/219e052492f4008818b8adb6366c7ed6-Paper.pdf>
*Relevansi:* prior label bergeser antar domain; estimasi bobot `p(y)/q(y)` bisa
dilakukan tanpa menyentuh dimensi input. Di repo: prior `before_sama` (63%
positif) vs `before_berubah` (5,6% positif).

### 69. Distribution shift (d2l)
Zhang, A., Lipton, Z. C., Li, M., Smola, A. J. **"Environment and Distribution
Shift"**, Dive into Deep Learning, §4.7.
<https://d2l.ai/chapter_linear-classification/environment-and-distribution-shift.html>
*Relevansi:* "Failure to account for this bias can become problematic at test
time." Juga dasar keputusan **tidak** menjalankan koreksi label shift di sini:
di N=56 per fold estimasi prior target terlalu berisik.


---

## Bias model & overfitting (metode)

Bagian ini melayani `report/findings/strategi-bebas-bias-dan-overfitting.md`:
apa yang bisa **ditambahkan** ke pipeline supaya model tidak bias dan tidak
overfitting, dengan POC-ABS + ROI25 + TabR tetap dipakai.

### 70. Bias & fairness facial ASP
Cheong, J., Kalkan, S., Gunes, H. **"The Hitchhiker's Guide to Bias and Fairness
in Facial Affective Signal Processing: Overview and Techniques."** IEEE Signal
Processing Magazine, 38(6), 39–49, 2021. DOI 10.1109/MSP.2021.3106619.
<https://doi.org/10.1109/MSP.2021.3106619>
*Relevansi:* panduan khusus untuk **facial affective signal processing**;
menyatakan ketidakseimbangan data dan atribut demografis adalah sumber bias
utama. Rujukan payung untuk seluruh L1.

### 71. Dataset bias di FER
Li, S., Deng, W. **"A Deeper Look at Facial Expression Dataset Bias."** IEEE
Transactions on Affective Computing, 13(2), 881–893, 2022.
DOI 10.1109/TAFFC.2020.2973158.
<https://doi.org/10.1109/TAFFC.2020.2973158>
*Relevansi:* model FER belajar **identitas subjek/dataset**, bukan ekspresi.
Dasar teoretis kenapa fitur ROI25 bisa mengkode identitas.

### 72. Domain-incremental untuk mitigasi bias
Churamani, N., Kara, O., Gunes, H. **"Domain-incremental Continual Learning for
Mitigating Bias in Facial Expression and Action Unit Recognition."** 2022.
<https://dl.acm.org/doi/abs/10.1145/3607865.3616175>
*Relevansi:* menunjukkan pendekatan berbasis domain **menurunkan bias** di FER/AU
**tanpa mengorbankan akurasi** — tepatnya trade-off yang kita ingin hindari.

### 73. Fairness di dataset kecil
Cheong, J., Spitale, M., Gunes, H. **"'It's not Fair!' — Fairness for a Small
Dataset of Multi-modal Dyadic Mental Well-being Coaching."** ACII 2023, 1–8.
<https://dl.acm.org/doi/10.1145/3607865.3616448>
*Relevansi:* fairness khusus di **dataset kecil** pada konteks kesehatan mental —
situasi kita (56 subjek). Catatan penting: penulis mempertanyakan apakah
counterfactual cukup untuk mengatasi ketidakseimbangan data.

### 74. MGP — loss untuk mitigasi bias
Jiang, J., Manoranjan, V., Salam, H., Celiktutan, O. **"Generalised Bias
Mitigation for Personality Computing."** MRAC '23, 39–50.
DOI 10.1145/3607865.3616175.
<https://dl.acm.org/doi/abs/10.1145/3607865.3616175>
*Relevansi:* memperkenalkan *Multi-Group Parity* (MGP), loss yang menargetkan
paritas performa antar grup. Relevan untuk masalah paradoks Simpson kita,
tapi **belum aman dipakai** di sini karena grup kita turunan label.

### 75. Subject-based domain adaptation untuk FER
Zeeshan, M. O., Aslam, M. H., Belharbi, S., Koerich, A. L., Pedersoli, M.,
Bacon, S., Granger, E. **"Subject-Based Domain Adaptation for Facial Expression
Recognition."** arXiv:2312.05632, 2023.
<https://arxiv.org/pdf/2312.05632v1>
*Relevansi:* memperlakukan **tiap subjek sebagai satu domain**; "facial
expressions are person-dependent and not versatile". Dasar langsung untuk
memperlakukan identitas subjek sebagai domain shift, bukan derau acak.

### 76. DBMF — domain adaptation untuk bias
**"Domain adaptation for bias mitigation in affective computing."** SN Applied
Sciences, 2025. DOI 10.1007/s42452-025-06659-1.
<https://link.springer.com/content/pdf/10.1007/s42452-025-06659-1.pdf>
*Relevansi:* kerangka *Demographic Bias Mitigation Framework* (DBMF) memakai
domain adaptation untuk menekan bias di FER dan sentiment analysis.

### 77. DICC — kelas tidak seimbang di FER
**"Optimizing Class Imbalance in Facial Expression Recognition Using Dynamic
Intra-Class Clustering."** 2025. PMC12109554.
<https://pmc.ncbi.nlm.nih.gov/articles/PMC12109554/>
*Relevansi:* peningkatan akurasi kelas minoritas 1,73% / 1,97% / 5,48% pada
FER2013 / MMAFEDB / Emotion-Domestic. Juga catatan penting: oversampling
sederhana "may be highly similar to the original data … can easily lead to
overfitting" — peringatan langsung untuk rencana SMOTE.

### 78. CUCN — ketidakseimbangan + ketidakpastian
**"Combating Uncertainty and Class Imbalance in Facial Expression
Recognition."** arXiv:2212.07751, 2022.
<https://arxiv.org/abs/2212.07751>
*Relevansi:* bobot per kelas + mekanisme penalti supaya model lebih fokus ke
kelas kecil, tanpa menurunkan akurasi keseluruhan.

### 79. Focal loss untuk FER
**"Class Imbalance in Facial Expression Recognition by GCN with Focal Loss."**
IEEE, 2022. Document 9727624.
<https://ieeexplore.ieee.org/document/9727624>
*Relevansi:* "focal loss tackles both class imbalance and the easy/hard example
imbalance" — alternatif dari bobot kelas statis.

### 80. Survei mitigasi overfitting
**"A Survey of Overfitting Mitigation Methods in Deep Learning: From
Regularization to Data Augmentation."** 2025.
<https://www.researchgate.net/publication/400398213_A_Survey_of_Overfitting_Mitigation_Methods_in_Deep_Learning_From_Regularization_to_Data_Augmentation>
*Relevansi:* katalog metode regularisasi → augmentasi; dipakai sebagai peta
untuk memilih lever overfitting (L3–L5).

### 81. Few-shot learning untuk FER
**"Few-shot learning for facial expression recognition: a comprehensive
survey."** Journal of Real-Time Image Processing, 2023.
DOI 10.1007/s11554-023-01310-x.
<https://link.springer.com/article/10.1007/s11554-023-01310-x>
*Relevansi:* "owing to the small amount of samples used for training,
overfitting and generalization problems are big issues of FSL" — pernyataan
eksplisit bahwa di N kecil overfitting adalah masalah struktural.

### 82. Generalisasi cross-subject (EEG) 2026
**"Cross-subject generalization for EEG emotion recognition."** Frontiers in
Computational Neuroscience, 2026. DOI 10.3389/fncom.2026.1865513.
<https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2026.1865513/full>
*Relevansi:* taksonomi metode lintas-subjek terbaru (domain adaptation,
contrastive/self-supervised, generative). Berguna sebagai daftar opsi L1.

### 83. TabNet
Arik, S. Ö., Pfister, T. **"TabNet: Attentive Interpretable Tabular
Learning."** AAAI 35(8), 2021. DOI 10.1609/aaai.v35i8.16826.
<https://ojs.aaai.org/index.php/AAAI/article/view/16826>
*Relevansi:* arsitektur tabular DL berbasis attention — kerabat dekat TabR;
dipakai sebagai pembanding, bukan pengganti.

### 84. Review deteksi micro-expression 2025
**"Advances in Facial Micro-Expression Detection and Recognition: A
Comprehensive Review."** MDPI Information, 16(10), 876, 2025.
<https://www.mdpi.com/2078-2489/16/10/876>
*Relevansi:* menyatakan **AU-based modeling berperan sentral** di pipeline
terintegrasi (kalibrasi onset/apex/offset lalu klasifikasi), dan keyframe
modeling "good robustness" di skenario data sedikit.


---

## Nasional (Indonesia) 2021–2026

Bagian ini menjawab permintaan rujukan **nasional**. Semua entri sudah
diverifikasi judul, jurnal, dan tahunnya dari halaman penerbit.

> **Cara memakai bagian ini dengan benar.** Hampir semua paper nasional memakai
> dataset publik besar (FER2013, JAFFE, Twitter/X) dengan **split tunggal**, dan
> melaporkan akurasi 76–92%. Angka itu **tidak sebanding** dengan angka kita
> (LOSO per subjek, N=56). Yang diambil dari mereka adalah **preseden metode**
> dan **pengakuan keterbatasan**, bukan angka akurasinya.

### 85. Rabit — kecemasan dari ekspresi wajah
Sunaryo, A. F. P., Sofhia, M., Perangin Angin, E. N., Barus, E. A.
**"Klasifikasi Ekspresi Wajah untuk Identifikasi Indikasi Kecemasan Menggunakan
Convolutional Neural Network (CNN)."** Rabit: Jurnal Teknologi dan Sistem
Informasi Univrab, 11(2), 4239–4246, Juli 2026.
DOI 10.36341/rabit.v11i2.8065.
<https://jurnal.univrab.ac.id/index.php/rabit/article/view/8065>
*Relevansi:* CNN + FER2013 → status PANIC / NORMAL / UNCERTAIN; acc 92,58%,
precision 93,48%, recall 92,58%, F1 92,27%. **Kutipan kuncinya:** performa
"dipengaruhi oleh faktor seperti pencahayaan, kualitas kamera, posisi wajah,
dan **keterbatasan dalam jumlah dan distribusi data**" — pengakuan lokal bahwa
masalahnya di data, bukan di arsitektur.

### 86. JAIC — depresi dari ekspresi wajah
Bakkar, M. E., Sari, C. A., Rachmawanto, E. H. **"Classification of Depression
Indication Based on Facial Expression Using MobileNetV2 and Support Vector."**
Journal of Applied Informatics and Computing (JAIC), 10(4), 3611–3622, Agustus
2026. DOI 10.30871/jaic.v10i4.13495.
<https://jurnal.polibatam.ac.id/index.php/JAIC/article/view/13495>
*Relevansi:* preseden nasional klasifikasi kondisi mental dari wajah;
MobileNetV2 (fitur) + SVM (classifier) — pola "ekstraktor fitur + classifier
tabular" seperti POC-ABS + TabR kita.

### 87. TEKNOSI — kecemasan + SMOTE + fitur temporal
Apriyanthi, N. P. E., Satya Dharma, I. G. T., Dhewanty, C. M. **"Klasifikasi
Hybrid Kecemasan Pengguna X Menggunakan Random Forest, SMOTE, dan Fitur
Temporal."** Jurnal Nasional Teknologi dan Sistem Informasi (TEKNOSI), 12(2),
242–250, Agustus 2026. DOI 10.25077/TEKNOSI.v12i2.2026.242-250.
<https://teknosi.fti.unand.ac.id/index.php/teknosi/article/view/4336>
*Relevansi:* **paling relevan dari sisi nasional.** Menyatakan pendekatan
klasifikasi berbasis konten tunggal "rentan mengalami **bias akibat
ketidakseimbangan kelas data**" — pembenaran lokal untuk L2. Menggabungkan
fitur teks + **variabel temporal** (is_night) lewat early fusion → acc 76,83%.
Pola "fitur statis + fitur temporal" = pola ROI25 + temporal kita.

### 88. MIB — deteksi stres mahasiswa
Wibowo, M., Djafar, M. R. F. **"Perbandingan Metode Klasifikasi Untuk Deteksi
Stress Pada Mahasiswa di Perguruan Tinggi."** Jurnal Media Informatika
Budidarma (MIB), 7(1), 153–159, Januari 2023. DOI 10.30865/mib.v7i1.5182.
<https://www.researchgate.net/publication/382632256>
*Relevansi:* membandingkan Naïve Bayes, Decision Tree, SVM, Neural Network,
Random Tree, Random Forest, kNN untuk stres mahasiswa; menunjukkan pemilihan
algoritma sangat memengaruhi akurasi.

### 89. SMATIKA — kesehatan mental + bias evaluasi
Chanafy, M., Sulistiani, H. **"Comparative Analysis of Machine Learning
Algorithm Performance for Student Mental Health Classification."** SMATIKA:
STIKI Informatika Jurnal, 16(1), 2026. DOI 10.32664/smatika.v16i01.2080.
<https://jurnal.ubhinus.ac.id/index.php/SMATIKA/article/download/2080/1097>
*Relevansi:* **kutipan metodologis yang kuat dari literatur nasional.** Penulis
sendiri menyatakan keterbatasan: "metode validasi masih menggunakan split
tunggal, sehingga **potensi bias evaluasi masih ada**", dan menyarankan
"penerapan teknik validasi k-fold cross validation". Ini pembenaran lokal untuk
protokol LOSO + interval kepercayaan yang kita pakai, sekaligus bukti bahwa
split tunggal adalah kelemahan umum di literatur nasional.

### 90. MALCOM — depresi & kecemasan dari teks
Rahayu, K., Fitria, V., Septhya, D., Rahmaddeni, R., Efrizoni, L.
**"Klasifikasi Teks untuk Mendeteksi Depresi dan Kecemasan pada Pengguna
Twitter Berbasis Machine Learning."** MALCOM: Indonesian Journal of Machine
Learning and Computer Science, 3(2), 108–114, September 2023.
DOI 10.57152/malcom.v3i2.780.
*Relevansi:* deteksi kecemasan pada data Indonesia; domain berbeda (teks) —
berguna sebagai pembanding klaim "deteksi kecemasan bisa akurat".

### 91. Eksplora — SVM untuk depresi & kecemasan
Darmawan, F., Joe, M., Kurniawan, Y. I., Afuan, L. **"Analisis Sentimen
Kemungkinan Depresi dan Kecemasan pada Twitter Menggunakan Support Vector
Machine."** Jurnal Eksplora Informatika, 13(1), 24–36, September 2023.
DOI 10.30864/eksplora.v13i1.854.
<https://doi.org/10.30864/eksplora.v13i1.854>
*Relevansi:* pembanding lokal berbasis SVM untuk kecemasan/depresi.

### 92. JAIC — depresi mahasiswa + seleksi fitur
Sabar, R. A., Pajri, A. E., Budiani, J. R. **"Classification of Student
Depression Using Support Vector Machine Modelling and Backward Elimination."**
Journal of Applied Informatics and Computing (JAIC), 10(1), Februari 2026.
<https://jurnal.polibatam.ac.id/index.php/JAIC/article/view/12203>
*Relevansi:* **backward elimination** untuk memilih fitur pada data kesehatan
mental — preseden nasional untuk L5 (reduksi dimensi).

### 93. JTIIK — facial landmark + classifier sederhana
Bachtiar, F. A., Wafi, M. **"Komparasi Metode Klasifikasi untuk Deteksi
Ekspresi Wajah Dengan Fitur Facial Landmark."** Jurnal Teknologi Informasi dan
Ilmu Komputer (JTIIK), 8(5), 949–956, Oktober 2021.
DOI 10.25126/jtiik.2021834434.
<https://jtiik.ub.ac.id/index.php/jtiik/article/view/4434>
*Relevansi:* **preseden nasional paling dekat dengan pipeline kita** — fitur
berbasis **landmark/ROI** (bukan citra mentah) + classifier tabular (ELM, SVM,
kNN), JAFFE 213 citra. ELM terbaik: acc 0,76, F1 0,76, waktu komputasi
6,97×10⁻³ s. Menunjukkan di N kecil, fitur ROI + classifier ringan adalah
pendekatan yang wajar dan diterima.

### 94. JATI — micro-expression per komponen wajah
Cahyo, D. N., Zahro, H. Z., Vendyansyah, N. **"Pengenalan Ekspresi Mikro Wajah
dengan Ekstraksi Fitur pada Komponen Wajah menggunakan metode Local Binary
Pattern Histogram."** JATI (Jurnal Mahasiswa Teknik Informatika), 7(1),
Februari 2023.
<https://www.ejournal.itn.ac.id/jati/article/download/6167/3872>
*Relevansi:* ekstraksi fitur **per komponen wajah (alis, mata, mulut)** dengan
LBPH — analog langsung ROI25 kita (5 ROI: mulut, mata kiri/kanan, alis
kiri/kanan). Preseden lokal untuk memakai ROI sebagai unit fitur.

### 95. EXPLORE — DCNN ekspresi wajah
Adiatma, B. C. L., Utami, E., Hartanto, A. D. **"Pengenalan Ekspresi Wajah
Menggunakan Deep Convolutional Neural Network."** EXPLORE, 11(2), 75, 2021.
DOI 10.35200/explore.v11i2.478.
*Relevansi:* baseline lokal DCNN untuk ekspresi wajah.

### 96. JSRCS — CNN FER2013 + sensitivitas/spesifisitas
Ekawati, I., Putra, F. N. R., Sumadyo, M., Whidhiasih, R. N. **"Deteksi Emosi
Menggunakan Convolutional Neural Network Berdasarkan Ekspresi Wajah."** JSRCS
(Jurnal Students' Research Computer Science), 5(1), 73–82, Mei 2024.
DOI 10.31599/h0kayy31.
<https://ejurnal.ubharajaya.ac.id/index.php/JSRCS/article/download/2926/1865>
*Relevansi:* FER2013, CNN, acc 76%; **melaporkan akurasi, sensitivitas, dan
spesifisitas** — pola pelaporan yang kita pakai di `collect_loso_results.py`.

### 97. CoSciTech — TabNet pada data tabular
Ismanto, E., et al. **"Analisis Perbandingan Model Fully Connected Neural
Network dan TabNet untuk Klasifikasi Perawatan Pasien pada Data Tabular."**
Jurnal CoSciTech (Computer Science and Information Technology), 5(3), 526–532,
2024.
<https://ejurnal.umri.ac.id/index.php/coscitech/article/view/8256>
*Relevansi:* preseden nasional model tabular DL berbasis attention (TabNet)
vs FCNN. Berguna untuk mempertahankan pilihan model tabular DL (TabR) di
tinjauan pustaka, sekaligus menunjukkan TabNet sebagai pembanding yang wajar.

### 98. TEKNOSI — seleksi fitur untuk TabNet
Ningsih, A. R. S., Sani, R. R., Dewi, I. N. **"Perbandingan Metode Seleksi
Fitur Chi-Square dan Information Gain untuk Peningkatan Interpretabilitas dan
Optimasi Kinerja Model TabNet."** Jurnal Nasional Teknologi dan Sistem
Informasi (TEKNOSI), 11(3), Desember 2025.
<https://teknosi.fti.unand.ac.id/index.php/teknosi/article/view/3880>
*Relevansi:* seleksi fitur + TabNet dengan tujuan "peningkatan interpretabilitas
dan optimasi kinerja" — preseden nasional untuk L5 (reduksi dimensi sebelum
model attention-based).

### 99. TEKNOSI — SLR data tidak seimbang
Alfin Ghozali, M., Bahtiar, A. **"Systematic Literature Review: Optimasi Model
Klasifikasi pada Imbalanced Data Menggunakan SMOTE, Hyperparameter Tuning, dan
Ensemble Learning."** Jurnal Nasional Teknologi dan Sistem Informasi (TEKNOSI),
12(2), Agustus 2026.
<https://teknosi.fti.unand.ac.id/index.php/teknosi/article/view/4419>
*Relevansi:* SLR nasional yang merangkum tiga obat data tidak seimbang —
**SMOTE, hyperparameter tuning, ensemble learning** — persis tiga lever L2, L4,
dan L3 kita. Rujukan yang kuat untuk bab metodologi.

### 100. INTEC — deteksi emosi deep learning
Edy, M. R. **"Deteksi Emosi dari Ekspresi Wajah dengan Deep Learning."** INTEC
(Information Technology Education Journal), 3(2), Mei 2024.
<https://journal.unm.ac.id/index.php/INTEC/article/view/2866>
*Relevansi:* CNN untuk emosi wajah real-time, integrasi ke sistem web; konteks
penerapan lokal.


---

## Paper yang Dipakai di Proposal (2017–2026)

Bagian ini mencatat **seluruh paper yang benar-benar disitasi di proposal**
(`proposal/main.typ` + `proposal/refs.bib`), mencakup BAB I dan BAB II. Daftar
ini bukan daftar tambahan untuk LOSO. Aturan sumbernya: terbit **2017 sampai
2026**, jurnal internasional harus akses terbuka, dan jurnal nasional minimal
**SINTA 2**.

Jumlahnya **28 entri**, dan jumlah itu sama persis dengan isi `refs.bib`, jadi
tidak ada entri yang menggantung. Semua tautannya sudah diperiksa dan bisa
dibuka untuk verifikasi (lihat "Hasil pemeriksaan tautan" di bawah).

> **Kenapa bagian ini ada.** BAB II disusun dengan menulis ulang (parafrase)
> BAB II proposal rujukan, lalu mengganti setiap sitasi yang tidak memenuhi
> aturan sumber. Substitusi itu dicatat di tabel di bawah supaya tidak ada
> klaim yang kehilangan rujukannya.

### Substitusi sumber: 7 dari 28 sitasi proposal acuan ditolak

Tabel ini membandingkan **BAB II proposal acuan (Syahrul)**, yang memuat 28
sitasi, dengan pilihan sumber di proposal ini.

| Sitasi asli | Alasan ditolak | Pengganti |
|---|---|---|
| Sathyanarayanan 2024 (confusion matrix) | **African Journal of Biomedical Research** — AJOL menyatakan jurnal ini "no longer meets AJOL's criteria", tidak terindeks bereputasi | @chicco2023mcc (BioData Mining, OA) |
| Sejati & Mardhiyyah 2021 (Dlib) | **JurTI (Jurnal Teknologi Informasi) Universitas Asahan — SINTA 5**, di bawah batas SINTA 2 | @bachtiar2021jtiik (JTIIK, **SINTA 2**) |
| Nur Cahyo dkk. 2023 (LBPH per komponen wajah) | **JATI (Jurnal Mahasiswa Teknik Informatika) — SINTA 4**, di bawah batas SINTA 2 | @bachtiar2021jtiik (JTIIK, **SINTA 2**) |
| Nurshabrina dkk. 2024 (definisi kecemasan) | **Action Research Literate — SINTA 5**, di bawah batas SINTA 2 | @hur2020anxiety (J. Neuroscience, OA) |
| Oktamarin dkk. 2022 (kecemasan abnormal) | **Jurnal Multidisipliner Bharasumba** — tidak terindeks SINTA | @javaid2023epidemiology (Middle East Current Psychiatry, OA) |
| Dewi dkk. 2025 (prevalensi kecemasan Indonesia) | sumber prevalensi lebih lemah daripada yang tersedia | @wahdi2025mental (Child Adolesc Psychiatry Ment Health, OA) |
| Schwarz dkk. 2022 (FAISS) | makalah workshop CEUR-WS, bukan jurnal terindeks | @johnson2021faiss (IEEE Trans. Big Data) |

Satu sitasi lain **tidak** ditolak kualitasnya, tetapi disatukan ke sumber yang
sudah dipakai di BAB I untuk klaim yang sama:

| Sitasi asli | Keputusan |
|---|---|
| Watson dkk. 2022 (fear vs anxiety) | digabung ke @hur2020anxiety (J. Neuroscience, OA), yang sudah dipakai di BAB I untuk pembeda fear dan anxiety |

Satu sitasi asli **dipertahankan** dengan catatan:

| Sitasi asli | Catatan |
|---|---|
| Arik & Pfister 2021 (TabNet) | prosiding AAAI, **tidak akses terbuka**. Dipakai hanya untuk mendefinisikan struktur data tabular (baris = objek, kolom = fitur), bukan untuk klaim performa. Kalau pembimbing meminta seluruh sitasi akses terbuka, entri ini yang perlu diganti lebih dulu. |

Satu sitasi asli lain, **Huang dkk. 2020 (embedding retrieval)**, pada awalnya
dipertahankan, tetapi kemudian dihapus saat 2.2 dirampingkan pada Iterasi 4.59
karena rincian FAISS sudah dialihkan ke @johnson2021faiss.

### Tabel lengkap: 28 paper yang dipakai di proposal

Ini adalah **daftar lengkap paper yang benar-benar disitasi di proposal**
(`proposal/main.typ` + `proposal/refs.bib`), bukan daftar tambahan untuk LOSO.
Semuanya terbit **2017-2026**; jurnal internasional akses terbuka, jurnal
nasional minimal **SINTA 2**. Kolom "Dipakai di" menyebut letak sitasinya di
proposal. Setiap baris punya **dua tautan**: DOI resmi dan **akses bebas**
(tanpa langganan, tanpa beli, tanpa jadi anggota).

#### A. Ekspresi wajah dan ekspresi mikro

| No | Penulis (tahun) | Judul | Wadah | Dipakai di | Tautan |
|---|---|---|---|---|---|
| 1 | Rosiani, Ulla Delfana dkk. 2020 | A Novel Approach on Motion Estimation for Micro-Expression Recognition Using Phase Only Correlation with All Block Search (POC-ABS) | International Journal of Intelligent Engineering and Systems | 1.1; Tabel 2.1; 2.2.4 | [DOI](https://doi.org/10.22266/ijies2020.1231.48) · [PDF gratis](http://www.inass.org/2020/2020123148.pdf) |
| 2 | Choirina, Priska dkk. 2022 | Pengenalan Ekspresi Mikro Wajah Berdasarkan Point Feature Tracking Menggunakan Fase Apex Pada Database Ekspresi Mikro | Edu Komputika Journal | Tabel 2.1; 2.2.1; 2.2.3 | [DOI](https://doi.org/10.15294/edukomputika.v9i1.56600) · [PDF gratis](https://journal.unnes.ac.id/sju/index.php/edukom/article/download/56600/22530) |
| 3 | Oh, Yee-Hui dkk. 2018 | A Survey of Automatic Facial Micro-Expression Analysis: Databases, Methods, and Challenges | Frontiers in Psychology | 1.1 | [DOI](https://doi.org/10.3389/fpsyg.2018.01128) · [PDF gratis](https://www.frontiersin.org/articles/10.3389/fpsyg.2018.01128/pdf) |
| 4 | Ben, Xianye dkk. 2022 | Video-Based Facial Micro-Expression Analysis: A Survey of Datasets, Features and Algorithms | IEEE TPAMI | 2.2.1 | [DOI](https://doi.org/10.1109/TPAMI.2021.3067464) · [PDF gratis (arXiv)](https://arxiv.org/pdf/2201.12728) |
| 5 | Lu, Shaojing dkk. 2022 | A More Objective Quantification of Micro-Expression Intensity through Facial Electromyography | Proc. 2nd Workshop on Facial Micro-Expression (ACM) | 2.2.1 | [DOI](https://doi.org/10.1145/3552465.3555038) · [versi jurnal gratis (arXiv)](https://arxiv.org/pdf/2409.00017) |
| 6 | Dong, Zizhao dkk. 2022 | Spontaneous Facial Expressions and Micro-Expressions Coding: From Brain to Face | Frontiers in Psychology | 2.2.1 | [DOI](https://doi.org/10.3389/fpsyg.2021.784834) · [PDF gratis](https://www.frontiersin.org/articles/10.3389/fpsyg.2021.784834/pdf) |
| 7 | Li, Yante dkk. 2022 | Deep Learning for Micro-Expression Recognition: A Survey | IEEE Trans. Affective Computing | 1.1; 2.2.3 | [DOI](https://doi.org/10.1109/TAFFC.2022.3205170) · [PDF gratis (IEEE OA)](https://ieeexplore.ieee.org/ielx7/5165369/9964459/09915437.pdf) |
| 8 | Kim, Minyoung dkk. 2022 | Effects of Diagnostic Regions on Facial Emotion Recognition: The Moving Window Technique | Frontiers in Psychology | 2.2.1 | [DOI](https://doi.org/10.3389/fpsyg.2022.966623) · [PDF gratis](https://www.frontiersin.org/articles/10.3389/fpsyg.2022.966623/pdf) |
| 9 | Zhao, Guoying dkk. 2023 | Facial Micro-Expressions: An Overview | Proceedings of the IEEE | 2.2.2 | [DOI](https://doi.org/10.1109/JPROC.2023.3275192) · [PDF gratis (IEEE OA)](https://ieeexplore.ieee.org/ielx7/5/4357935/10144523.pdf) |
| 10 | Dawel, Amy dkk. 2025 | Faking It Isn't Making It: Research Needs Spontaneous and Naturalistic Facial Expressions | Affective Science | 2.2.1 | [DOI](https://doi.org/10.1007/s42761-025-00320-1) · [PDF gratis](https://link.springer.com/content/pdf/10.1007/s42761-025-00320-1.pdf) |

#### B. Data tabular dan pembelajaran mesin

| No | Penulis (tahun) | Judul | Wadah | Dipakai di | Tautan |
|---|---|---|---|---|---|
| 11 | Arik, Sercan Ö. dkk. 2021 | TabNet: Attentive Interpretable Tabular Learning | Proc. AAAI Conference on Artificial Intelligence | 2.2.5 | [DOI](https://doi.org/10.1609/aaai.v35i8.16826) · [PDF gratis (arXiv)](https://arxiv.org/pdf/1908.07442) |
| 12 | Johnson, Jeff dkk. 2021 | Billion-Scale Similarity Search with GPUs | IEEE Trans. Big Data | 2.2.5 | [DOI](https://doi.org/10.1109/TBDATA.2019.2921572) · [PDF gratis (arXiv)](https://arxiv.org/pdf/1702.08734) |
| 13 | Gorishniy, Yury dkk. 2024 | TabR: Tabular Deep Learning Meets Nearest Neighbors | Proc. 12th ICLR | 1.1; Tabel 2.1; 2.2.5 | [arXiv](https://arxiv.org/abs/2307.14338) · [PDF gratis](https://arxiv.org/pdf/2307.14338) |
| 14 | Pasaribu, Johannes dkk. 2024 | Tabular Data Classification and Regression: XGBoost or Deep Learning with Retrieval-Augmented Generation | IEEE Access | Tabel 2.1; 2.2.5 | [DOI](https://doi.org/10.1109/ACCESS.2024.3518205) · [PDF gratis (IEEE Access OA)](https://ieeexplore.ieee.org/document/10802905) |
| 15 | Yang, Shizhong dkk. 2024 | Confusion Matrix | The Southwest Respiratory and Critical Care Chronicles | Tabel 2.1 | [DOI](https://doi.org/10.12746/swrccc.v12i53.1391) · [PDF gratis](https://pulmonarychronicles.com/index.php/pulmonarychronicles/article/download/1391/2969) |
| 16 | Chicco, Davide dkk. 2023 | The Matthews Correlation Coefficient (MCC) Should Replace the ROC AUC as the Standard Metric for Assessing Binary Classification | BioData Mining | 2.2.6 | [DOI](https://doi.org/10.1186/s13040-023-00322-4) · [PDF gratis](https://biodatamining.biomedcentral.com/counter/pdf/10.1186/s13040-023-00322-4) |

#### C. Kecemasan, stres, dan kesehatan mental

| No | Penulis (tahun) | Judul | Wadah | Dipakai di | Tautan |
|---|---|---|---|---|---|
| 17 | Hur, Juyoen dkk. 2020 | Anxiety and the Neurobiology of Temporally Uncertain Threat Anticipation | Journal of Neuroscience | 1.1; 2.2.2 | [DOI](https://doi.org/10.1523/JNEUROSCI.0704-20.2020) · [PDF gratis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7548695/) |
| 18 | Javaid, Syed Fahad dkk. 2023 | Epidemiology of Anxiety Disorders: Global Burden and Sociodemographic Associations | Middle East Current Psychiatry | 1.1; 2.2.2 | [DOI](https://doi.org/10.1186/s43045-023-00315-3) · [PDF gratis](https://mecp.springeropen.com/counter/pdf/10.1186/s43045-023-00315-3) |
| 19 | Wahdi, Amirah Ellyza dkk. 2025 | Mental Health Service Use among Adolescents in Three Low- and Middle-Income Countries | Child and Adolescent Psychiatry and Mental Health | 1.1; 2.2.2 | [DOI](https://doi.org/10.1186/s13034-025-00924-2) · [PDF gratis](https://link.springer.com/content/pdf/10.1186/s13034-025-00924-2.pdf) |
| 20 | Lei, Jiedi dkk. 2024 | Exploring the Association between Social Camouflaging and Self- versus Caregiver-Report Discrepancies in Anxiety and Depressive Symptoms | Autism (SAGE) | 2.2.2 | [DOI](https://doi.org/10.1177/13623613241238251) · [PDF gratis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11459877/pdf/10.1177_13623613241238251.pdf) |
| 21 | Sharma, Deepak dkk. 2024 | Demystifying Mental Health by Decoding Facial Action Unit Sequences | Big Data and Cognitive Computing (MDPI) | 2.2.2 | [DOI](https://doi.org/10.3390/bdcc8070078) · [artikel gratis](https://www.mdpi.com/2624-7402/8/7/78) |
| 22 | Möcklinghoff, Sarah dkk. 2024 | Examining the Role of Post-Event Processing in Test Anxiety: Pilot Testing in Three Student Samples | Int. Journal of Educational Research Open (Elsevier OA) | 2.2.2 | [DOI](https://doi.org/10.1016/j.ijedro.2024.100363) · [artikel gratis](https://www.sciencedirect.com/science/article/pii/S2666374024000451) |
| 23 | Sahu, Nilesh Kumar dkk. 2025 | AnxietyFaceTrack: A Smartphone-Based Non-Intrusive Approach for Detecting Social Anxiety Using Facial Features | arXiv (pracetak) | 1.1 | [arXiv](https://arxiv.org/abs/2502.16106) · [PDF gratis](https://arxiv.org/pdf/2502.16106) |
| 24 | Gavrilescu, Mihai dkk. 2019 | Predicting Depression, Anxiety, and Stress Levels from Videos Using the Facial Action Coding System | Sensors (MDPI) | 1.1 | [DOI](https://doi.org/10.3390/s19173693) · [artikel gratis](https://www.mdpi.com/1424-8220/19/17/3693) |
| 25 | Zhang, Haoyu dkk. 2020 | Video-Based Stress Detection through Deep Learning | Sensors (MDPI) | 1.1 | [DOI](https://doi.org/10.3390/s20195552) · [artikel gratis](https://www.mdpi.com/1424-8220/20/19/5552) |

#### D. Nasional (minimal SINTA 2)

| No | Penulis (tahun) | Judul | Wadah | Dipakai di | Tautan |
|---|---|---|---|---|---|
| 26 | Bachtiar, Fitra A. dkk. 2021 | Komparasi Metode Klasifikasi untuk Deteksi Ekspresi Wajah Dengan Fitur Facial Landmark | JTIIK | 2.2.3 | [DOI](https://doi.org/10.25126/jtiik.2021834434) · [artikel gratis](https://jtiik.ub.ac.id/index.php/jtiik/article/view/4434) |
| 27 | Prakoso, Raihan Adi dkk. 2026 | Sistem Deteksi Stres Menggunakan Metode Support Vector Machine dengan Fitur RMSSD dan PNN50 | JTIIK | 1.1 | [DOI](https://doi.org/10.25126/jtiik.2026133) · [terbitan gratis](https://jtiik.ub.ac.id/index.php/jtiik/issue/view/99) |
| 28 | Larasati, Sza Sza Amulya dkk. 2024 | Penerapan Decision Tree dan Random Forest dalam Deteksi Tingkat Stres Manusia Berdasarkan Kondisi Tidur | JTIIK | 1.1 | [DOI](https://doi.org/10.25126/jtiik.2024117993) · [artikel gratis](https://jtiik.ub.ac.id/index.php/jtiik/article/view/7993) |

### Cara mengakses tanpa bayar (ringkas)

Semua tautan di atas mengarah ke sumber resmi yang gratis dibaca. Tidak ada yang
butuh langganan atau pembelian. Ringkasnya:

| Kondisi paper | Cara aksesnya |
|---|---|
| Jurnal akses terbuka penuh (MDPI, Frontiers, Springer/BMC OA, JTIIK, Edu Komputika, IJIES, IEEE Access) | langsung buka tautan "gratis"-nya |
| Diterbitkan IEEE tetapi punya versi OA | pakai tautan **PDF gratis (IEEE OA)** yang sudah terdaftar di tabel |
| Diterbitkan IEEE/ACM tetapi versi OA-nya di arXiv | pakai tautan **PDF gratis (arXiv)** |
| Diterbitkan SAGE/Journal of Neuroscience tetapi ada di PubMed Central | pakai tautan **PDF gratis (PMC)** |
| Nomor **5 (Lu dkk. 2022)** | versi prosiding ACM-nya terkunci. Yang gratis adalah **versi jurnal lanjutannya** di arXiv (2409.00017) yang membahas topik sama dengan penulis yang sama, tetapi **bukan artikel identik**. Kalau yang harus dikutip versi ACM-nya, aksesnya lewat perpustakaan kampus. |

Dua catatan penting saat membuka:

1. Beberapa penerbit (MDPI, JTIIK, IEEE, SAGE) menolak permintaan otomatis
   dengan kode 403. Tautannya tetap sah dan terbuka normal di peramban biasa.
2. Kalau tautan arXiv di atas mengarah ke versi *submitted* (preprint), isinya
   bisa sedikit berbeda dari versi terbit. Untuk angka yang dikutip di proposal,
   angka dari versi terbit tetap dipakai.

### Hasil pemeriksaan tautan (2026-10-13)

**Tautan DOI (kolom pertama).** Ke-28 tautan diperiksa ulang. Tidak ada tautan
mati.

- **26 entri** dicek lewat `api.crossref.org`: DOI terdaftar, dan judul + wadah
  terbit hasil Crossref cocok dengan yang tertulis di `refs.bib`.
- **Prakoso dkk. 2026** (`10.25126/jtiik.2026133`): DOI terdaftar dan mengarah ke
  JTIIK volume 13 nomor 3, tetapi **metadata judul/penulis di Crossref masih
  kosong** (deposit JTIIK belum lengkap). Judul dan penulis di tabel diambil dari
  laman artikel JTIIK, bukan dari Crossref.
- **Sahu dkk. 2025** memakai DOI arXiv, yang memang tidak ada di Crossref. Tautan
  mengarah ke `arxiv.org/abs/2502.16106` dan terbuka normal.

**Tautan akses bebas (kolom kedua).** Setiap tautan "gratis" diuji dengan
`curl -L` pada 2026-10-13. Hasilnya:

- **Terverifikasi mengembalikan PDF langsung:** 16 tautan (arXiv, Frontiers,
  Springer/BMC, IEEE OA, PMC, IJIES, Edu Komputika). Semuanya terunduh sebagai
  `application/pdf` tanpa login.
- **Terverifikasi mengembalikan halaman artikel:** 8 tautan (IEEE Access,
  BioMed Central, MECP, Springer, PMC, ScienceDirect, MDPI, JTIIK).
- **Terblokir bot, bukan mati:** MDPI, JTIIK, dan ACM membalas 403 untuk
  permintaan otomatis. Sudah dicoba dengan header peramban lengkap; tetap 403,
  tetapi halaman artikelnya normal saat dibuka manual di peramban.
- **Tidak ada satu pun tautan** yang mengarah ke situs berbagi ilegal. Semua
  tautan gratis berasal dari penerbit, arXiv, PubMed Central, atau situs jurnal
  resmi.

Catatan pembukaan tautan: beberapa penerbit (IEEE, MDPI, SAGE, ACM, JTIIK)
menolak permintaan otomatis dengan kode 403/202 walaupun DOI-nya sah. Kalau itu
terjadi, buka tautannya lewat peramban biasa.

### Bentuk 2.1 dan isi Tabel 2.1

2.1 berbentuk **tabel rujukan** seperti proposal acuan (satu paragraf pengantar,
Tabel 2.1, lalu satu paragraf penghubung ke 2.2). Tema 2.1 **dibatasi pada
bagian pembelajaran mesin** yang benar-benar dipakai penelitian ini, sehingga
penelitian psikologi dan kesehatan mental tidak dimasukkan ke tabel.

Tabel 2.1 memuat **5 penelitian**, urut tahun:

| # | Penelitian | Masuk karena |
|---|---|---|
| 1 | Rosiani dkk. 2020 | metode ekstraksi fitur (POC-ABS) |
| 2 | Choirina dkk. 2022 | preseden nasional POC-ABS/ROI terbatas |
| 3 | Gorishniy dkk. 2024 | model klasifikasi (TabR) |
| 4 | Pasaribu dkk. 2024 | bukti TabR unggul pada klasifikasi |
| 5 | Yang & Berdine 2024 | dasar confusion matrix dan metrik |

Jumlah baris sengaja dijaga **sama dengan proposal acuan (5 baris)** dan tidak
dilebihkan, supaya tabel tidak terkesan menjiplak atau menumpuk rujukan.
Rujukan lain yang benar-benar dipakai tetap disitasi pada 2.2 dan BAB I.

### Bentuk 2.2 Dasar Teori

2.2 difokuskan pada **ekspresi mikro dan _anxiety_** serta metode yang benar-benar
dipakai penelitian ini, bukan latar belakang umum ilmu komputer. Sebelas
subbagian sebelumnya (2.2.1-2.2.11) diringkas menjadi **enam**:

| Sebelum | Sesudah |
|---|---|
| 2.2.1 Ekspresi Wajah + 2.2.2 Ekspresi Mikro | **2.2.1 Ekspresi Mikro Wajah** |
| 2.2.3 Gangguan Kecemasan (Anxiety Disorder) | **2.2.2 Kecemasan dan Ekspresi Mikro** |
| 2.2.4 Pengolahan Citra + 2.2.5 Deteksi Wajah + 2.2.6 Dlib | **2.2.3 Facial Landmark dan Dlib** |
| 2.2.7 POC-ABS | **2.2.4 Phase Only Correlation with All Block Search (POC-ABS)** |
| 2.2.8 Data Tabular + 2.2.9 FAISS + 2.2.10 TabR | **2.2.5 Data Tabular dan Tabular Retrieval Network (TabR)** |
| 2.2.11 Confusion Matrix | **2.2.6 Metrik Evaluasi** |

Subbagian terakhir **tidak lagi membahas _confusion matrix_**. Isinya hanya
definisi kelas positif/negatif dan rumus _accuracy_, _precision_, _recall_,
serta _F1-score_, karena metrik itulah yang benar-benar dipakai. Gambar
_confusion matrix_ (sebelumnya Gambar 2.9) dihapus, sehingga jumlah gambar BAB II
menjadi **8** (Gambar 2.1-2.8).

`yang2024confusion` **tetap** di `refs.bib` karena masih disitasi sebagai baris
Tabel 2.1 (dasar confusion matrix dan metrik), jadi total entri tetap **28** dan
semuanya tersitasi.

Yang **dihapus** karena bersifat umum dan tidak dipakai langsung: penjelasan
umum pengolahan citra (peningkatan kualitas, restorasi, segmentasi), pembagian
citra statis vs bergerak, penjelasan rinci deteksi wajah pada citra bergerak,
serta rincian teknis internal FAISS (IVF, PQ, OPQ, nlist, nprobe). Definisi
dasar deteksi wajah tetap ada, tetapi digabung ke subbagian Dlib.

Pada 2.2.4 POC-ABS, empat blok "Keterangan:"nci tiap variabel
dihapus dan diganti satu paragraf penjelasan; penurunan rumus tetap lengkap,
tetapi langkah-langkah per blok diringkas menjadi daftar lima butir.

Entri `refs.bib` yang tidak lagi disitasi setelah perampingan dihapus, sehingga
seluruh entri yang tersisa pasti terpakai: total **28 entri**, semuanya tersitasi
dan tampil di Daftar Pustaka. Yang dihapus: `archana2024deep`,
`sinulingga2023keyframe`, `huang2020embedding`, dan `liu2022tvli`.

Perubahan pada iterasi ini:

| Perubahan | Alasan |
|---|---|
| Angka **AUC 0,98 / akurasi 0,93 pada dataset _electricity_** dibuang | angka itu berasal dari _random split_ yang **bocor**: pada dataset _electricity_ retrieval dapat mencapai ~100% karena kebocoran (didokumentasikan pada TabReD, arXiv:2406.19380). Klaim diganti dengan temuan kualitatif Pasaribu dkk. |
| Klaim TabNet **"akurasi hingga 96,99%"** dibuang | tidak ada di abstrak/isi makalah; diganti dengan perannya sebagai acuan definisi data tabular |
| Klaim Liu dkk. **"UAR ≈ 0,70, UF1 ≈ 0,73, 37,9 ms/sampel"** diganti dengan 1,53 juta parameter | angka lama tidak dapat diverifikasi dari makalah; angka parameter ada di abstrak |
| Seluruh **8 gambar digambar ulang** dari nol | Gambar 2.1, 2.3, 2.4, 2.5 memakai data CASME II yang diproses sendiri (dlib + POC); Gambar 2.2, 2.6-2.8 digambar dengan matplotlib |
