# 12 — Head pose + geometri landmark sepanjang sesi

**Severity:** high

## Current Problem

Seluruh fitur sekarang berasal dari **satu momen per event** (apex) dan hanya
dari gerakan POC di 5 ROI. Literatur menunjukkan cue kecemasan terkuat dari
wajah bukan itu:

AnxietyFaceTrack (IEEE TAFFC 2026, N=91, kamera smartphone):

| fitur | multiclass | binary |
|---|---|---|
| 3D facial landmarks | **88%** | **91%** |
| head pose | **85%** | **89.66%** |
| action units | 59% | 73% |
| eye gaze | 53% | — |

Kontributor utama: rotasi kepala sumbu-x, landmark tepi wajah, landmark mata.
Ditambah arXiv:2601.04376: *"stress is primarily encoded in temporal
dynamics—particularly velocity-based descriptors—rather than static feature
levels"*.

**Kita sudah membuang data ini.** `scripts/process_spotting_pipeline.py`
menjalankan `detect_landmarks()` (dlib 68 titik) di **setiap frame**
(`build_roi_signals`) lalu hanya menyimpan skalar POC. 68 koordinat per frame
per video hilang.

## Target

Fitur head pose dan geometri landmark sepanjang sesi, ditambahkan di pass yang
sama dengan spotting, tanpa dependency baru.

## Required Design

- **Head pose:** `cv2.solvePnP` dari 68 titik dlib + model 3D wajah generik →
  yaw/pitch/roll per frame. OpenCV sudah dipakai di repo.
- **Geometri landmark:** jarak/jarak-ter-normalisasi antar titik kunci (tepi
  wajah, mata, mulut, alis), dinormalkan terhadap skala wajah (mis. jarak
  antar pupil) supaya **tidak** mengkodekan ukuran kepala — ini penting karena
  fitur yang tidak dinormalkan justru memperkuat identitas (sebab #1).
- **Agregasi sesi:** per subjek per sesi, simpan **variabilitas** (std,
  rentang) dan bukan hanya mean — literatur menekankan dinamika.
- **Normalisasi baseline:** fitur dinormalkan terhadap `neutral.png` subjek
  (issue 04), mengikuti mekanisme Differential AU StressGAT.
- Simpan ke tabel fitur terpisah (`poc_abs_roi_signals_pose.xlsx`) supaya
  tidak menimpa yang ada; gabungkan lewat `--features` di `run_loso.py`.
- Jaga jumlah fitur tetap kecil (puluhan, bukan ratusan) — di N=56, menambah
  dimensi menambah overfitting (arXiv:2606.31249).
- **Perhatian metodologis** (Frontiers Digital Health 2026): statistik
  normalisasi tidak boleh tumpang tindih dengan window evaluasi.

## Tests

- Verifikasi statis + satu video contoh: plot yaw/pitch/roll, cek nilainya
  masuk akal (bukan konstan, bukan liar).
- Cek korelasi fitur baru dengan `participant` (kalau tinggi → masih
  mengkodekan identitas, harus dinormalkan lagi).

## Done Criteria

- [ ] Head pose (yaw/pitch/roll) per frame dihasilkan.
- [ ] Deskriptor geometri landmark ter-normalisasi skala wajah.
- [ ] Agregasi sesi memuat variabilitas, bukan hanya mean.
- [ ] Dinormalkan terhadap baseline netral.
- [ ] Tabel fitur lama tidak tersentuh.
