# Geometri Wajah + Head Pose sebagai Keluarga Fitur Kedua

Tanggal: 2026-10-06. Melanjutkan
`report/findings/research-strengthen-loso.md` (Lever C dan E) dan
`report/findings/literature-accuracy-drop-2021-2026.md`.

Pertanyaan: POC-ABS sudah terbukti tidak membawa sinyal kecemasan yang bisa
dipakai (gerbang within-subject: 0/25 fitur signifikan pada baseline netral,
LOSO dalam-subjek 0,528, p=0,473). Keluarga fitur apa yang literatur
rekomendasikan, dan bisa dihitung dari data yang **sudah ada di disk**?

---

## 1. Jawaban singkat

**Geometri wajah + head pose, dinormalkan terhadap wajah netral tiap orang.**

Tiga alasan:

1. Ini keluarga fitur dengan angka terbaik di literatur kecemasan-dari-wajah,
   dan bukan POC/optical-flow.
2. Biayanya hampir nol di repo ini: `scripts/process_spotting_pipeline.py`
   **sudah** menjalankan dlib 68 landmark di setiap frame lalu membuangnya.
   Tidak perlu re-spotting, tidak perlu data baru.
3. Ia menyerang akar masalah yang sama dari dua sisi sekaligus: memberi POC-ABS
   sinyal yang selama ini tidak ada, **dan** membuat retrieval TabR mencocokkan
   *kondisi* alih-alih *identitas*.

---

## 2. Bukti per fitur

### AnxietyFaceTrack — IEEE TAFFC 2026, arXiv:2502.16106

N=91, kamera ponsel, setting sosial alami (bukan stres terinduksi),
Random Forest, 5-fold CV:

| keluarga fitur | multiclass | biner |
|---|---|---|
| **3D facial landmarks** | **88%** | **91%** |
| **head pose** | **85%** | **89,66%** |
| action units | 59–66% | 73% |
| eye gaze | 53% | — |

Kontributor utama (analisis SHAP): **rotasi kepala sumbu-x**, **landmark tepi
wajah** (jawline: titik 0,1,3,4,11,12,13,15,16), dan **landmark mata**.
Dengan hanya 6 fitur head pose (lokasi + rotasi) sudah 85% — 6% di bawah
kombinasi terbaik dari 669 fitur.

Catatan jujur: ini 5-fold CV, **bukan LOSO**, dan labelnya social anxiety dari
kuesioner pada setting sosial. Angka 88–91% tidak boleh dipindahkan apa adanya
ke protokol LOSO kita.

### StressGAT — arXiv:2607.20819, 58 peserta, **LOSO 88,62% / F1 0,89**

Mekanisme intinya bukan arsitekturnya, tapi **Differential Action Units**:
setiap fitur dinormalkan terhadap **baseline netral orang itu sendiri**.
Paper itu menyebut persis masalah yang kita alami:

> *"permanent anatomical traits ... transient stress-induced deviations ...
> distributional shift in which the neutral configuration of one individual may
> overlap with the stressed phenotype of another."*

Ini definisi akar masalah #1 di `CONTEXT.md`: fitur kita mengkodekan identitas
lebih kuat daripada kondisi. Differential AU adalah obatnya, dan sudah
tervalidasi pada protokol subjek-independen.

Catatan: label StressGAT = **stres terinduksi**, 58 peserta. Bukan kecemasan
trait dari kuesioner.

### Giannakakis et al. — Biomed. Signal Process. Control 2017; IEEE BHI 2018

Studi eksperimental stres: **mobilitas dan kecepatan kepala meningkat** saat
stres; fitur terpilih adalah **kecepatan** pitch/roll/yaw, bukan sudut
statisnya. Karena itu fitur kecepatan (`geo_d_*`, `geo_head_motion`) dimasukkan
terpisah dari fitur statis.

### Rumahorbo, Elwirehardja, Pardamean — BINUS, Commun. Math. Biol. Neurosci. 2025

Paper Indonesia (DAIC-WOZ, RNN): rekayasa fitur geometris di **area mata dan
bibir** (bukaan kelopak, jarak bibir atas–bawah, panjang dan tinggi bibir)
mengalahkan turunan pertama mentah. Ini dasar `geo_ear_*`, `geo_mar`,
`geo_mouth_open`, `geo_mouth_width`, `geo_lip_corner_drop`.

### EmpathicSchool — arXiv:2209.13542

24 subjek, stres terkait tugas. AU yang berkorelasi dengan stres:
lip tightener (17 subjek), lip stretcher (16), mouth stretch (15),
lip depressor (14), lid droop (13), nostril compressor (10), cheek raiser (9).
Semua ini gerakan di sekitar mulut/mata → lagi-lagi geometri lokal, bukan
magnitudo gerak global.

### Ghimire et al. 2013; arXiv:2506.17191

**Displacement dari ekspresi netral** lebih informatif daripada posisi absolut
landmark. Memvalidasi pilihan diferensial terhadap `neutral.png`.

---

## 3. Yang diimplementasikan

`features_extraction/geometry.py` (satu sumber kebenaran), dipakai lewat
`scripts/extract_features_poc_abs.py --with-geometry`. 21 fitur per frame,
semua dari 68 landmark yang **sudah** dihitung:

**Statis (15) — diskala jarak inter-okular, lalu dikurangi nilai netral subjek**

| fitur | arti | dasar |
|---|---|---|
| `geo_ear_kiri`, `geo_ear_kanan`, `geo_ear_mean` | Eye Aspect Ratio (bukaan kelopak) | Rumahorbo 2025; AnxietyFaceTrack (landmark mata) |
| `geo_mar`, `geo_mouth_open`, `geo_mouth_width` | bukaan & lebar mulut | Rumahorbo 2025; EmpathicSchool (AU12/15/25) |
| `geo_lip_corner_drop` | sudut bibir turun relatif garis tengah (AU15) | EmpathicSchool |
| `geo_brow_eye_kiri`, `geo_brow_eye_kanan` | jarak alis–mata bertanda (AU2 naik / AU4 turun) | EmpathicSchool; FACS |
| `geo_brow_gap` | jarak alis dalam (AU1) | FACS |
| `geo_jaw_width` | lebar rahang (landmark tepi wajah) | AnxietyFaceTrack (fitur terkuat) |
| `geo_pitch`, `geo_yaw`, `geo_roll` | head pose 3D (solvePnP) | AnxietyFaceTrack (rotasi sumbu-x terkuat) |
| `geo_eye_line_roll` | kemiringan garis mata | AnxietyFaceTrack (landmark mata) |

**Kecepatan (6) — selisih antar frame, tidak dikurangi baseline**

`geo_d_ear_mean`, `geo_d_mar`, `geo_d_pitch`, `geo_d_yaw`, `geo_d_roll`,
`geo_head_motion` (norma ketiga kecepatan sudut). Dasar: Giannakakis (kecepatan
kepala), arXiv:2601.04376 ("stress is primarily encoded in temporal dynamics —
particularly velocity-based descriptors — rather than static feature levels").

---

## 4. Keputusan teknis yang tidak sepele

**a. Head pose dinyatakan relatif acuan frontal.**
Model 3D memakai +Y ke atas sedangkan citra +Y ke bawah, jadi rotasi wajah
frontal adalah 180° terhadap sumbu X. Kalau sudutnya diambil apa adanya, pitch
duduk di ±179° dan **melompat 360°** begitu wajah melewati titik itu — fitur
kecepatan jadi sampah. Karena itu rotasi dikalikan `R_ref = diag(1,−1,−1)` lebih
dulu; hasilnya pitch ≈ −1,7° (rentang terukur −3,4…+1,4 pada 400 frame) dan
kontinu. Diverifikasi: `head_motion` maksimum 8,2°/frame, tidak ada lonjakan.

**b. Tidak ada NaN, dan cadangan bersatuan sama.**
Kalau `solvePnP` gagal, pose diambil dari proyeksi geometris
(`_head_pose_proxy`) yang **juga dalam derajat**, supaya frame yang jatuh ke
cadangan tidak melompat skala. Nilai 0,0 palsu dihindari karena akan memicu
lonjakan palsu di fitur kecepatan.

**c. Tiga tabel dari satu pass.**
Ekstraksi menulis POC-ABS saja (skema lama, **tidak berubah**), geometri saja,
dan gabungan. Tujuannya: perbandingan antar keluarga fitur bersih tanpa
menjalankan ulang apa pun, dan hasil lama tetap bisa direproduksi.

**d. ROI dan geometri dari landmark yang sama.**
`ROIExtractor.extract_landmarks()` dipakai bersama `extract_rois()`; ROI yang
dihasilkan dijamin identik bit-per-bit (diverifikasi pada frame nyata). Tidak
ada deteksi wajah dua kali.

---

## 5. Batas yang harus diakui

- AnxietyFaceTrack (N=91, 5-fold CV, social anxiety) dan StressGAT (stres
  terinduksi, 58 peserta) **bukan** tugas yang identik dengan kita: label
  kuesioner trait, LOSO, N=56, webcam 30 fps.
- Plafon label tetap berlaku: Cochrane STAI AUC 0,81 dengan spesifisitas 0,57.
- dlib 68 pada webcam resolusi rendah + gerakan kepala = noise. Ini bisa keluar
  sebagai noise, bukan sinyal.
- Karena itu **gerbang within-subject tetap dijalankan lebih dulu**
  (stage 5 pipeline): kalau keluarga geometri juga 0/25 signifikan pada 18
  subjek yang labelnya berubah, hentikan jalur ini.

---

## 6. Rujukan

- **AnxietyFaceTrack** — arXiv:2502.16106 (IEEE TAFFC 2026), N=91.
- **StressGAT** — arXiv:2607.20819, 58 peserta, LOSO 88,62%, Differential AU.
- **Giannakakis et al.** — Biomed. Signal Process. Control 31:89–101, 2017;
  IEEE BHI 2018 (head pose untuk deteksi stres).
- **Rumahorbo, Elwirehardja, Pardamean** — Commun. Math. Biol. Neurosci. 2025,
  BINUS Jakarta (rekayasa fitur geometri mata/bibir, DAIC-WOZ).
- **EmpathicSchool** — arXiv:2209.13542 (dataset stres multimodal, dlib 68 + AU).
- **Ghimire et al.** — 2013 (geometri landmark sekuens); arXiv:2506.17191
  (displacement dari netral > posisi absolut).
- **Driving stress multimodal** — arXiv:2601.04376 (kecepatan > level statis).
- **Cochrane STAI** — CD015458 (plafon label: AUC 0,81, spesifisitas 0,57).
- **Grimm et al. 2022** — GAD-7 dari wajah, AUC 0,71.
