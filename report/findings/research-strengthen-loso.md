# Memperkuat LOSO: Target 70% & Mengurangi Overfitting

Tanggal: 2026-10-06. Melanjutkan
`report/findings/literature-accuracy-drop-2021-2026.md`.

Pertanyaan: bisakah akurasi LOSO naik ke ≥70% (train & test berdekatan,
overfitting turun)? Apa riset yang mendukungnya?

---

## 1. Jawaban singkat: 70% belum didukung untuk setup ini

Bukan karena modelnya kurang pintar, tapi karena tiga batas keras:

**Batas 1 — labelnya sendiri punya plafon.**
Label di dataset ini berasal dari kuesioner. Cochrane review untuk STAI
(instrumen kecemasan yang paling umum) melaporkan terhadap wawancara klinis:
**AUC 0.81, sensitivitas tinggi tapi spesifisitas hanya 0.57**. Artinya
instrumen labelnya sendiri salah klasifikasi banyak orang. Model tidak bisa
melebihi keandalan labelnya; plafon praktisnya ada di sekitar AUC 0.8, dan
dengan label biner + N kecil, akurasi 70% sudah mendekati plafon itu.

Grimm et al. 2022 (label GAD-7, fitur wajah) mendapat **AUC 0.71**. Itu angka
yang realistis untuk "kecemasan dari wajah", bukan 85–95%.

**Batas 2 — N terlalu kecil.**
Zantvoort et al., npj Digital Medicine 2024: untuk ML kesehatan mental,
**ukuran sampel minimum N = 500–1000**. Studi lain (medRxiv 2025) menemukan
kebutuhan median 190 (RF) / 269 (NN) / 480 (XGBoost). Kita punya **56 subjek**,
25 positif. Di bawah ambang itu, varians estimasi akurasi sangat besar — dan
interval kepercayaan kita memang lebar (0.44–0.69).

**Batas 3 — angka 88–93% di literatur bukan tugas yang sama.**
Hampir semua angka tinggi berasal dari **stres terinduksi** (label = tugas mana
yang sedang dikerjakan), bukan kecemasan trait dari kuesioner:

| Studi | Angka | Setup sebenarnya |
|---|---|---|
| StressGAT 2026 | 88.62% LOSO | **stres terinduksi**, 58 peserta, label per-fase tugas |
| TSDNet | 85.42% | split internal, 2.092 klip, bukan LOSO |
| AnxietyFaceTrack | 91% | **5-fold CV**, bukan LOSO, N=91 |
| Gavrilescu 2019 | 77.9% | klip penginduksi emosi |
| MDPI scoping review | **47.97–72.73%** | **LOSO**, deteksi kecemasan |

Bandingkan dengan tugas kita: label kuesioner (trait), LOSO, N=56, fitur
micro-expression. Pita realistisnya **~48–72%**, dan 70% ada di ujung atas.

**Kesimpulan:** 70% bisa dikejar, tapi hanya kalau **keluarga fitur berubah**
dan **label + data dibersihkan dulu**. Menaikkan 55% → 70% dengan tuning TabR
pada 25 fitur statis tidak akan terjadi; itu hanya akan menambah overfitting.

---

## 2. Overfitting yang sekarang — terukur

Dari `report.json` 168 run LOSO yang sudah ada:

| run | train | val | gap |
|---|---|---|---|
| `convat_apex_anxiety_loso_roi25` | 0.8285 | 0.5615 | **0.2670** |
| `exp3_subject_agg` | 0.9024 | 0.7042 | **0.1982** |

Gap 27 poin = overfitting berat. Penyebab strukturalnya ada dua:

1. **TabR tidak cocok untuk N=56.** TabR bekerja dengan me-retrieve tetangga
   dari data train. Dengan `context_size` 12–24 dan hanya ~55 baris train,
   **22–44% data train ikut jadi konteks setiap prediksi**. Retrieval dirancang
   untuk dataset ribuan baris, bukan puluhan.
2. **25 fitur statis + 44.424 baris frame.** Barisnya banyak tapi informasinya
   sedikit; model menghafal baris, bukan belajar sinyal.

Catatan penting: **val 70.42% di exp3 bukan prestasi.** Val hanya 11 subjek,
dan dipakai untuk memilih `best_epoch`, jadi angkanya optimistis. Angka test
level subjek yang jujur untuk exp3 adalah **44.05%** (di bawah acak). Ini
contoh kenapa val tidak boleh dipakai sebagai klaim.

---

## 3. TEMUAN PENTING: tabel fitur sudah basi (blocker)

Ini harus dibereskan sebelum apa pun yang lain.

| | metadata + dataset | tabel fitur |
|---|---|---|
| tanggal | 2026-09-22 | **2026-09-01** |
| `before` event | 3.639 | 1.493 |
| `before` subjek | 56 | **23** |
| `before/tidak` | 921 event / 15 subjek | **0 baris** |

`experiments/features/apex/poc_abs_roi_signals.xlsx` (1 Sep) tidak pernah
dibuat ulang setelah re-spotting 22 Sep. Akibatnya:

- **2.146 event `before` hilang**, 33 subjek tidak punya data `before`.
- Seluruh blok `before/tidak` hilang → di tabel fitur, `before` jadi 100%
  `anxiety_tinggi`. Itu **artefak kehilangan data, bukan protokol.**
- Analisis grup `before_sama` (13) / `before_berubah` (10) di `summary.md`
  **tidak sah** — dihitung dari 23 subjek, bukan 56.
- Kesimpulan apa pun yang membandingkan `before` vs `after` tidak sah.

Yang **tidak** terpengaruh: headline LOSO. Mode `--label-unit person` hanya
memakai `after`, dan `after` lengkap (metadata 3.239 event vs fitur 3.244
event, 56 subjek). Jadi angka 55.36% tetap berdiri.

### Struktur label sebenarnya (dari metadata segar)

- 56 subjek, **semua** punya `before` dan `after`.
- `before`: 41 anxiety / 15 tidak. `after`: 25 anxiety / 31 tidak.
- Label **konsisten** di dua sesi: 38 subjek. **Berubah: 18 subjek**
  (17 anxiety→tidak, 1 tidak→anxiety).

18 subjek berubah label antar sesi = **satu orang, wajah yang sama, label
berbeda**. Ini kesempatan diagnostik terbaik yang dimiliki dataset ini
(lihat Lever B).

Dataset mentahnya **ada di mesin ini** di `/run/media/finny/New Volume/dataset/`:
`anxiety_raw/` (56 subjek, before+after) dan `datatest/` (49 subjek + 610 video
+ `annotations.xlsx`). Jadi re-ekstraksi dan re-spotting bisa dijalankan tanpa
memindahkan data. (Koreksi: catatan awal saya menyebut `/mnt/FINNY/dataset`
tidak ada dan menyimpulkan dataset tidak tersedia — itu keliru.)

---

## 3b. Dataset kedua: `datatest` — 49 subjek yang belum dipakai

| | anxiety_raw | datatest | gabungan |
|---|---|---|---|
| subjek unik | 56 | **49** | **105** |
| sesi | 112 | 98 | 210 |
| irisan nama | — | **0** | — |
| label berubah antar sesi | 18 | 11 | 29 |

`datatest/annotations.xlsx` punya kolom `subject_id, stage, score, label`
(98 baris, skor 5–20), dan `labeled/{15_04_2026,17_04_2026}/{anxiety_rendah,
anxiety_tinggi}/` berisi 610 video. Semua 49 subjek punya `before` dan `after`.

Ini **1,9x lipat jumlah subjek** tanpa mengumpulkan data baru. Catatan jujur:
datatest diambil April 2026 vs anxiety_raw Desember 2025, dan labelnya berbasis
skor — jadi menggabungkannya menambah domain shift. Itu bisa diuji (dan
justru itu uji generalisasi lintas-koleksi), tapi jangan diasumsikan gratis.

`output/apex/datatest` di repo sudah **hilang** — harus di-spotting ulang dari
`labeled/`.

---

## 4. Lever yang didukung riset, urut dampak

### Lever A — Re-ekstraksi fitur dari metadata sekarang (BLOCKER, gratis)
Jalankan ulang `scripts/extract_features_poc_abs.py --roi-signals` terhadap
`output/apex/dataset` + `metadata.xlsx` (22 Sep). Memulihkan 2.146 event dan
33 subjek, membuka Lever B dan memperbaiki analisis grup. Tidak mengubah
headline LOSO (yang memakai `after`).

### Lever B — Uji berpasangan dalam-subjek (gratis, paling menentukan)
Untuk 18 subjek yang labelnya berubah: bandingkan fitur sesi `before` vs
`after`. **Identitas terkontrol sempurna** — orang yang sama, wajah yang sama.
Kalau fitur POC-ABS tidak bisa memisahkan dua sesi itu, maka keluarga fitur ini
memang tidak membawa sinyal kecemasan, dan tidak ada model yang bisa
menyelamatkannya. Ini eksperimen termurah dan paling menentukan yang tersedia,
dan hasilnya menentukan apakah Lever C–G layak dikejar.

Catatan: uji awal saya (10 subjek "flip") **tidak sah** karena memakai tabel
basi; 19/20 fitur tampak signifikan tapi arahnya (after > before) justru
berlawanan dengan ekspektasi, dan `before` di tabel basi selalu
`anxiety_tinggi`. Harus diulang setelah Lever A.

### Lever C — Head pose + geometri landmark sepanjang sesi (paling menjanjikan)
AnxietyFaceTrack, IEEE TAFFC 2026, N=91, smartphone camera:

| fitur | multiclass | binary |
|---|---|---|
| **3D facial landmarks** | **88%** | **91%** |
| **head pose** | **85%** | **89.66%** |
| action units | 59% | 73% |
| eye gaze | 53% | — |

Kontributor utama: **rotasi kepala sumbu-x, landmark tepi wajah, landmark
mata**. Head pose + geometri landmark konsisten jadi fitur terkuat.

**Biaya di repo ini hampir nol:** `scripts/process_spotting_pipeline.py`
sudah menjalankan dlib 68 landmark **di setiap frame** (`detect_landmarks`)
lalu membuangnya, hanya menyimpan skalar POC. Jadi head pose (solvePnP dari 68
titik) dan deskriptor geometri landmark bisa ditambahkan di pass yang sama.

### Lever D — Dinamika temporal, bukan level statis
Paper stress saat mengemudi (arXiv:2601.04376) menyimpulkan:
*"Stress is primarily encoded in temporal dynamics—particularly
velocity-based descriptors—rather than static feature levels"*, dan
cross-modal facial+bio mencapai **AUROC 0.92 ± 0.04**.

Kita sudah punya sinyal kecepatan (POC motion) tapi hanya diambil di apex.
Fitur temporal (Iterasi 4.3) sudah mulai ke arah ini; yang kurang adalah
**variabilitas sepanjang sesi**, bukan hanya per-event.

### Lever E — Normalisasi per subjek adalah mekanisme yang terbukti
StressGAT (arXiv:2607.20819) mencapai **88.62% LOSO pada 58 peserta** dengan
mekanisme intinya: **Differential Action Units** — menormalkan fitur terhadap
baseline netral tiap orang, supaya ciri anatomi permanen tidak tertukar dengan
sinyal stres. Paper itu menyebut persis masalah kita:
*"permanent anatomical traits ... transient stress-induced deviations ...
distributional shift in which the neutral configuration of one individual may
overlap with the stressed phenotype of another."*

Ini memvalidasi arah Iterasi 4.2 (subject-norm) dan 4.4 (baseline netral).
Bedanya: mereka menormalkan **AU** terhadap baseline; kita menormalkan skalar
POC. Kalau Lever C dikerjakan, normalisasi terhadap baseline netral jadi jauh
lebih kuat karena AU/landmark lebih stabil daripada POC.

### Lever F — Modality kedua: rPPG (heart rate) dari video yang sama
- Sun et al. 2022: rPPG saja **78.75%**, fusi rPPG + behavioral **82.50%**.
- Paper driving: fusi facial + physiological AUROC **0.92**.
- UBFC-Phys multimodal: 70.5% (label tugas) → 93% (label self-report).

Risiko: rPPG rapuh terhadap gerakan, pencahayaan, dan kualitas kamera. Video
kita 60/30 fps dengan gerakan kepala; ini bisa jadi sumber noise baru, bukan
sinyal. **Rekomendasi: jangan jadikan prioritas utama.**

### Lever G — Menambah N (dampak terbesar, biaya terbesar)
Literatur ukuran sampel menempatkan N=500–1000 sebagai minimum untuk ML
kesehatan mental. Kita **tidak bisa** mencapai itu tanpa pengumpulan baru,
tapi **tidak perlu mengumpulkan apa pun untuk naik dari 56 → 105 subjek**:
`datatest` (49 subjek) sudah ada di drive dan belum pernah dipakai. Lihat §3b.
Ini lever dengan rasio dampak/biaya terbaik setelah Lever A dan B.

### Catatan model — TabR pada N=56
Untuk ukuran N ini, literatur tabular kecil-sampel (Grinsztajn 2022, TabPFN
Nature 2025) menunjukkan model sederhana/beregularisasi lebih baik. Baseline
saya (Iterasi 4.6) sudah menunjukkan logistic/GBDT tidak lebih baik dari acak
— tapi itu di atas fitur yang kita tahu tidak membawa sinyal. Setelah Lever A
dan B, model yang tepat adalah **logistik/GBDT dengan regularisasi kuat**,
atau TabR dengan `context_size` sangat kecil. **TabR dengan context 12–24 pada
55 baris train adalah mismatch struktural.**

---

## 5. Saran urutan kerja

1. **Lever A** — re-ekstraksi fitur (blocker, di mesin ini, ~jam).
2. **Lever B** — uji berpasangan 18 subjek. **Gerbang keputusan.**
   - Kalau sinyal ADA → kejar Lever C+D+E, target 65–72% realistis.
   - Kalau sinyal TIDAK ADA → berhenti menggarap fitur POC-ABS; pindah ke
     Lever C dari awal (head pose/landmark/AU) atau Lever G (tambah N).
3. **Lever C+D+E** — head pose + geometri landmark + variabilitas sesi,
   dinormalkan terhadap baseline netral. Ini jalur dengan dukungan literatur
   terkuat untuk 70%.
4. **Lever G** — kalau target 70% wajib dan waktu memungkinkan.
5. Lever F hanya kalau C–E sudah selesai dan masih kurang.

Jangan mengulang: menambah fitur statis, rebalance frame, agregasi clip/subjek,
atau tuning TabR di atas representasi yang belum terbukti punya sinyal.

---

## 6. Rujukan baru (2021→sekarang)

Detail + tautan ada di `report/documentation/research-papers.md`.

- **StressGAT** — Graph Attention, Differential Action Units, 88.62% LOSO,
  58 peserta. arXiv:2607.20819. *Mekanisme normalisasi baseline per orang.*
- **AnxietyFaceTrack** — IEEE TAFFC 2026, N=91. 3D landmark 88–91%, head pose
  85–89.66%, AU 59–73%, gaze 53%. *Fitur mana yang benar-benar bekerja.*
- **Baseline normalization inflation** — Frontiers Digital Health 2026.
  Normalisasi yang tumpang tindih dengan test menggelembungkan akurasi
  **3–13 poin** walau partisi subjek tetap ketat. *Peringatan metodologis.*
- **Beyond Questionnaires** — arXiv:2501.05461. SAD dari gaze/head/body pose;
  gaze sendiri 68%, tapi digabung justru turun.
- **Driving stress multimodal** — arXiv:2601.04376. Dinamika temporal > level
  statis; fusi facial+physio AUROC 0.92.
- **UBFC-Phys multimodal** — ACM MM 2025. 70.5% (label tugas) → 93%
  (label self-report). *Label yang lebih valid menaikkan angka lebih dari fitur.*
- **Zantvoort et al.** — npj Digital Medicine 2024. N minimum 500–1000.
- **Cochrane STAI** — CD015458. AUC 0.81, spesifisitas 0.57 → plafon label.
- **Grimm et al. 2022** — GAD-7 dari video, AUC 0.71.
- **MDPI scoping review** — 47.97–72.73% untuk deteksi kecemasan LOSO.
- **Few-shot hidden emotion** — arXiv:2606.31249. Fitur foundation model
  berdimension tinggi → train >80%, test ~50%. *Jebakan overfitting.*
- **Sample size requirements** — medRxiv 2025. Median 190–480.
