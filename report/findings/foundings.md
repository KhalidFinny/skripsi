TEMUAN & RENCANA - PROYEK SKRIPSI MICRO-EXPRESSION
====================================================

Ringkasan Singkat
-----------------

Proyek ini mendeteksi micro-expression (gerakan wajah yang sangat halus
dan sangat singkat) untuk mengklasifikasikan tingkat kecemasan seseorang
(tinggi atau rendah).

Alur utamanya:

  Video wajah (.avi, 200 fps)
    |
    v
  Deteksi 68 titik wajah (dlib)
    |
    v
  Potong 5 area wajah (mata, alis, mulut)
    |
    v
  Hitung gerakan dengan POC-ABS (pergerakan sub-piksel)
    |
    v
  Cari momen puncak gerakan (apex)
    |
    v
  Ubah semua gerakan jadi angka (fitur tabular)
    |
    v
  Masukkan ke model TabR -> hasil: cemas / tidak cemas


=====================================================================

1. Bagaimana "Spotting" Bekerja
-------------------------------

Spotting = mencari kapan micro-expression terjadi di dalam video.

Caranya:

1. Deteksi wajah
   dlib menemukan 68 titik di wajah setiap frame (gambar).

2. Potong area
   Dari 68 titik itu, kita ambil 5 area (ROI):
   - mulut (70x35 piksel)
   - mata kiri + alis (48x32 piksel)
   - mata kanan + alis (48x32 piksel)
   - alis kiri (64x24 piksel)
   - alis kanan (64x24 piksel)

3. Hitung gerakan
   Pakai POC-ABS (Phase-Only Correlation): bandingkan setiap frame
   dengan frame pertama sebagai acuan (baseline). POC-ABS bisa
   mendeteksi gerakan lebih kecil dari 1 piksel. Ini penting karena
   micro-expression memang bergerak sangat halus.

4. Hitung energi gerakan
   Untuk setiap frame, jumlahkan besar gerakan semua blok 7x7:
   - Energi = akar(dx^2 + dy^2)
   - Artinya: "seberapa besar gerakan, tanpa peduli ke arah mana".

5. Cari puncak (apex)
   Sinyal energi dihaluskan dulu (filter Savitzky-Golay), lalu dicari
   puncaknya (top_k = 5, paling banyak 5 puncak per video).

6. Tentukan awal dan akhir
   Onset (mulai) dan offset (selesai) dicari di sekitar puncak.
   Satu kejadian (event) = satu potongan video dari onset sampai offset.

Catatan penting:
Logika spotting sebenarnya TIDAK ada di file .py. Fungsi run_spotting()
di preprocess-anxiety/spotting.py masih kosong (cuma NotImplementedError).
Semua logika ada di dalam notebook besar (process_all_datasets.ipynb).
Ini menyulitkan siapa pun yang ingin menjalankan ulang atau mengubah prosesnya.


=====================================================================

2. Bagaimana Data Didapat dan Diubah
-------------------------------------

1. Data mentah
   Video .avi 200 fps, direkam dengan kamera Intel RealSense.
   Dataset ada di folder ../dataset (di luar folder proyek ini,
   TIDAK ada di komputer ini).

2. Frame
   Video dipecah jadi gambar per frame (.jpg).

3. ROI
   Setiap frame dipotong 5 area wajah.

4. Fitur
   Setiap area dihitung gerakannya dengan POC-ABS, jadi vektor (dx, dy),
   lalu diklasifikasikan arahnya (kuadran Q1-Q4).

5. Event
   Puncak gerakan ditemukan, lalu diambil potongan video di sekitarnya.

6. Tabel fitur
   Semua frame dalam event dijadikan baris. Satu baris punya 392 angka
   fitur (98 blok x 4) + kolom meta (subjek, pertanyaan, label).
   Total sekitar 2.764 event clip.

7. Siapkan data model
   Nilai kosong diisi (imputer), angka dinormalisasi (StandardScaler),
   lalu dibagi jadi train / val / test.

Ada 5 cara membagi data (split):

  a. event_clip_split
     Acak per event.
     Aman dari bocor? TIDAK. Subjek yang sama bisa ada di train dan test.

  b. balanced_train_clips
     Sama seperti di atas, plus jumlah kelas diseimbangkan.
     Aman dari bocor? TIDAK. Masih bocor.

  c. qholdout
     Train q1-q3, val q4, test q5 (berdasarkan nomor pertanyaan).
     Aman dari bocor? TIDAK. Subjek yang sama ada di semua split.

  d. qwalkforward
     Fold 1: train q1-q2, test q3. Fold 2: train q1-q3, test q4.
     Aman dari bocor? TIDAK. Sama.

  e. loso (LOSO = Leave-One-Subject-Out)
     Train semua subjek kecuali 1, test subjek yang 1 itu.
     Aman dari bocor? YA. Satu-satunya yang aman.

Ini masalah terbesar:
Kebanyakan split membiarkan subjek yang sama muncul di train dan test.
Jadi model "menghafal" orang, bukan belajar pola kecemasan.
Angka akurasinya jadi menipu.


=====================================================================

3. Akurasi: Angka Sebenarnya
-----------------------------

  - TabR v20 (awal, tanpa balancing): 55,6%
    Sama saja menebak kelas mayoritas. Ini sumber cerita "50-60%".

  - TabR v19/v20 (dengan balanced clips): 69% internal / 72,6% eksternal
    Lebih baik.

  - TabR resmi (Yandex), seed 11: 74,3% test (macroF1 72,8%)
    Hasil terbaik yang jujur.

  - qholdout + fitur alis (608 fitur): 82,9%
    Angka tinggi, tapi split berbeda dan bocor. Tidak bisa dibandingkan.

  - Test di tanggal baru (datatest): akurasi 61-72%, macroF1 39-47%
    Begitu diuji ke data baru, performa turun.

Tentang cerita "optical flow dapat 80%":

  Kode optical flow TIDAK ADA sama sekali di proyek ini.
  Tidak ada implementasi Farneback, Lucas-Kanade, atau metode optical
  flow lain. Jadi kita tidak bisa membandingkan angka 80% itu dengan
  metode POC ini, karena metode pembandingnya tidak ada di repo.

  Kemungkinan besar metode optical flow menang karena salah satu dari ini
  (perlu dibuktikan):
  - evaluasinya memakai split yang benar (subjek berbeda antara train
    dan test), atau
  - optical flow melihat gerakan seluruh wajah, bukan hanya 5 area kecil.


=====================================================================

4. Kenapa Model Overfitting
----------------------------

Overfitting = model bagus di data latihan, tapi buruk di data baru.

Buktinya:
  1. Train 97,4% vs test 74,3% - selisih 23% (TabR resmi).
  2. Train 99,9% vs val 84% (model qholdout+alis) - parah.
  3. SVM: train 99,5% -> test eksternal 22,2% - jatuh drastis.
  4. Model menebak kelas mayoritas: di data subjek baru, hampir semua
     diprediksi "cemas", recall kelas "tidak cemas" hanya 3-7%.

Penyebab utamanya:

  1. Subjek bocor antar split (penyebab nomor 1 - lihat tabel split).
  2. Dataset kecil: 112 subjek, sekitar 2.764 event.
     Model rumit mudah menghafal.
  3. Fitur terlalu banyak dan banyak yang tidak berguna:
     392-608 angka, padahal banyak blok 7x7 yang tidak bergerak
     (area statis di dalam ROI).
  4. Evaluasi pakai akurasi biasa. Dengan kelas tidak seimbang, akurasi
     menyesatkan. Harus pakai macroF1 / balanced accuracy.


=====================================================================

5. Hal yang Tidak Perlu / Bisa Dibuang
---------------------------------------

  - core/tabr_v2.py          : MATI. Tidak pernah dipakai
                              (tidak di-import di mana pun).
                              SUDAH DIHAPUS 25/08/2026.
  - core/tabr_faithful.py    : MATI. Tidak pernah dipakai.
                              SUDAH DIHAPUS 25/08/2026.
  - core/utis.py             : MATI. Nama typo dari "utils", tidak dipakai.
                              SUDAH DIHAPUS 25/08/2026.
  - core/TabR.py (LitTabR
    v1-v21)                  : LAMA. Sudah digantikan TabR resmi Yandex.
  - conv1_base.py            : RUSAK. Ada baris "class %(nn.Module)" -
                              template belum diisi, tidak bisa jalan.
                              SUDAH DIHAPUS 25/08/2026.
  - Super-Refine/ (GFPGAN +
    Real-ESRGAN)             : PERCOBAAN SAMPING. Tidak dipakai di
                              pipeline utama. Bahaya: memperbaiki kualitas
                              gambar justru bisa menghilangkan sinyal
                              micro-expression yang bergerak <1 piksel.
  - export_to_official_tabr_
    dataset_qholdout_copy.py : DUPLIKAT. Hampir sama persis dengan versi
                              aslinya, beda 2 baris.
                              SUDAH DIHAPUS 25/08/2026.
  - third_party/tabular-dl-
    tabr-official/           : KOSONG. Folder kosong! Skrip v25 tidak
                              bisa jalan. Perlu di-clone ulang.
  - Notebook 55MB
    (process_all_datasets
    .ipynb)                  : SULIT DIPELIHARA. Logika spotting harus
                              dipindah ke file .py.

Ringkasnya: banyak kode mati dan percobaan yang tidak terpakai.
Membersihkannya tidak akan langsung menaikkan akurasi, tapi membuat
proyek lebih mudah dipahami, dijalankan ulang, dan dijelaskan saat sidang.


=====================================================================

6. Apakah ViT (Vision Transformer) Memungkinkan?
-------------------------------------------------

Kesimpulan: belum sekarang. Alasannya:

  1. GPU kecil: GTX 1650 Ti Mobile, hanya 4 GB VRAM.
     ViT butuh memori besar.

  2. Data terlalu sedikit: ViT butuh data sangat banyak agar tidak
     overfitting. Kita cuma punya sekitar 2.764 event clip.
     ViT akan overfit lebih parah daripada TabR.

  3. Masalah teknis mendasar: micro-expression bergerak kurang dari
     1 piksel. POC-ABS menangkap gerakan ini lewat domain frekuensi.
     Kalau gambar dipotong kecil-kecil jadi patch (cara kerja ViT),
     sinyal gerakannya justru hilang.

Kalau tetap mau dicoba (sebagai percobaan samping, bukan model utama):
  - syaratnya: perbaiki dulu evaluasi (split subjek-disjoint),
  - pakai crop ROI kecil sebagai input,
  - siapkan augmentasi data yang banyak,
  - dan pahami bahwa ini bukan pengganti jalur POC -> TabR.


=====================================================================

7. Rencana Kerja
-----------------

Fase 0 - Kembalikan yang Hilang (syarat utama)
  - Clone ulang repo resmi Yandex TabR ke
    third_party/tabular-dl-tabr-official/.
  - Temukan video mentah ../dataset (tidak ada di komputer ini).
  - Pastikan hasil ekspor (file .xlsx / .npy) masih ada.

Fase 1 - Perbaiki Cara Evaluasi (pengaruh terbesar)
  - Ubah semua split menjadi subjek-disjoint: subjek yang sama tidak
    boleh ada di train dan test. Pakai LOSO atau GroupShuffleSplit.
  - Lapor metrik yang seimbang: macroF1 dan balanced accuracy,
    bukan akurasi mentah.
  - Angka akan turun, tapi sekarang angka itu jujur dan bisa
    dipertanggungjawabkan.

Fase 2 - Bersihkan Kode Mati
  - Hapus: tabr_v2.py, tabr_faithful.py, utis.py, conv1_base.py,
    qholdout_copy.py.
  - Arsipkan Super-Refine/ sebagai percobaan terpisah.
  - Pindahkan logika spotting dari notebook ke file .py yang rapi.

Fase 3 - Analisis Fitur
  - Cari blok 7x7 yang tidak pernah bergerak (statis) lalu buang,
    supaya fitur berkurang dan overfitting mengecil.
  - Bandingkan 392 vs 608 fitur dengan split yang sama
    (pakai hasil Fase 1).

Fase 4 - Percobaan Model (dengan evaluasi yang sama)
  - TabR resmi + LOSO + metrik seimbang + ensemble 2x5.
  - Tambahkan baseline optical flow (Farneback) dengan framing fitur
    yang sama, supaya klaim "optical flow 80%" bisa dibandingkan
    secara adil di dalam proyek ini.

Fase 5 - ViT (opsional, hanya kalau Fase 1-4 beres)
  - Percobaan kecil dengan ViT pada crop ROI, dengan ekspektasi
    realistis: bukan pengganti jalur utama.


=====================================================================

Prioritas
---------

Yang paling penting dikerjakan pertama: Fase 1 (perbaiki evaluasi).

Selama split masih bocor subjek, angka berapa pun tidak bisa dipercaya,
termasuk angka 80% dari metode optical flow.

Setelah evaluasi jujur, baru kita tahu apakah POC -> TabR sebenarnya
sudah lebih baik dari yang terlihat, atau memang perlu diganti/diperbaiki.

=====================================================================

8. UPDATE 2026-09-01 - 392 FITUR SUDAH DILATIH 2 KALI
------------------------------------------------------

Run 1 (hasil yang lebih dulu dicatat di results.md bagian 7):
  - split subjek-disjoint 23.742 / 8.922 / 9.190 frame
  - best seed 3 -> test acc 0.6123, macroF1 0.5358, bal_acc 0.5516,
    ROC-AUC 0.5839
  - recall kelas rendah = 0.261, kelas tinggi = 0.842

Run 2 (hasil terbaru; output/training/convat_apex_anxiety/summary.md):
  - setelah spotting baru + re-export, split membesar jadi
    34.530 / 14.668 / 14.962 frame
  - best seed berdasar val = 13 -> test acc 0.6271, macroF1 0.5067,
    bal_acc 0.5440, ROC-AUC 0.5906
  - recall kelas rendah turun ke 0.171, recall kelas tinggi naik ke 0.917
  - ensemble terbaik (seed 5-9) memberi test acc 0.6357, tetapi macroF1
    hanya 0.4853 dan bal_acc 0.5422

Maknanya:
  1. Setelah split jujur, performa TabR 392 fitur yang realistis sekarang
     ada di kisaran acc 0.61-0.64, macroF1 0.48-0.54, bal_acc 0.54-0.55.
     Jadi angka lama 0.74-0.83 memang terlalu optimistis.
  2. Training kedua menaikkan accuracy mentah, tetapi TIDAK memperbaiki
     kualitas seimbang antarkelas. Model malah lebih condong ke kelas
     mayoritas (anxiety_tinggi).
  3. Jadi metrik utama untuk keputusan berikutnya harus macroF1 /
     balanced accuracy, BUKAN accuracy saja.

Implikasi rencana:
  - baseline 392 yang "jujur" sekarang sudah cukup jelas.
  - langkah berikutnya bukan melatih 392 berulang-ulang, tetapi membandingkan
    fitur lain (196 / 608 / roi25) pada protokol yang sama sesudah
    spotting baru di-re-export.
