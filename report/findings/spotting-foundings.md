TEMUAN SPOTTING - BAGAIMANA DETEKSI MICRO-EXPRESSION BEKERJA
==============================================================

Tanggal      : 2026-08-25
Tujuan       : Dokumentasi cara kerja SPOTTING (deteksi micro-expression)
               dari kode asli, plus analisis titik lemah yang mungkin
               menjadi kunci perbaikan akurasi ("the one to set").

Sumber       : pembacaan langsung kode:
               - preprocess-anxiety/spotting.py (config)
               - preprocess-anxiety/process_all_datasets.ipynb (logika utama)
               - apex/apex_smoother.py (smoothing)
               - apex/apex_phase.py (deteksi puncak + fase)
               - features_extraction/poc.py, vektor.py, quadran.py


=====================================================================

1. ALUR SPOTTING (URUTAN SEBENARNYA DI KODE)
----------------------------------------------

  1. Input: video satu pertanyaan (q1-q5), 200 fps.
     Semua frame diubah ke grayscale.

  2. Landmark: dlib mendeteksi 68 titik wajah di SETIAP frame.
     Kalau gagal di salah satu frame -> magnitude = 0.0.

  3. Sinyal magnitude = gerakan antar frame BERURUTAN
     (frame N dibandingkan frame N-1), bukan vs frame pertama:

       prev = frame[0]
       for curr in frame[1:]:
           mag = compute_frame_magnitude(prev, curr)
           magnitudes.append(mag)
           prev = curr          # referensi BERGERAK maju

     Artinya sinyal spotting mengukur KECEPATAN gerakan
     (perubahan per frame), bukan perpindahan dari baseline.

  4. Satu angka magnitude per frame (compute_frame_magnitude):
     - 5 ROI di-crop: mata kanan/kiri, alis kanan/kiri, mulut
       (crop = kotak landmark + padding 6/8, lalu resize)
     - POC 7x7 per blok:
       Hanning window -> FFT2 -> cross-power -> normalisasi fase
       -> IFFT -> fftshift
     - Vektor: cari puncak korelasi -> dx, dy per blok
     - Quadran: theta + magnitude per blok (kolom index 4)
     - RATA-RATA magnitude per blok dalam ROI
     - RATA-RATA antar 5 ROI
     -> satu angka global per frame

  5. Deteksi event (detect_events):
     - Smooth sinyal dengan Savitzky-Golay:
       window = 5% panjang sinyal, dibulatkan ganjil,
       dibatasi 5..31 frame (jadi hampir selalu 31 = 155 ms)
       polyorder 2/3/4 sesuai ukuran window
     - Threshold tinggi: height = mean + std sinyal halus
       (puncak di bawah ini DIBUANG)
     - Cari apex: find_peaks(distance=1, prominence=0.005,
       height=mean+std)
     - Merge puncak yang berjarak < 10 frame (ambil yang tertinggi)
     - Ambil top-5 puncak berdasarkan nilai sinyal
     - Fase per apex (two-pass):
       Pass 1: cari valley (titik terendah) kiri/kanan
       Pass 2: dari valley, cari titik cutoff 30% (0.3)
       radius pencarian maksimal 100 frame
       batas antar apex = titik tengah dua apex berurutan
     - Event valid kalau durasi >= 2 frame
     - Simpan klip: event_XXXXX-YYYYY (frame onset..offset),
       frame apex ditandai -apex.png
     - Index sinyal -> index frame = +1 (sinyal punya N-1 elemen)

  Lokasi logika: SEMUA ada di notebook process_all_datasets.ipynb.
  File spotting.py cuma berisi konfigurasi; run_spotting() masih
  NotImplementedError.


=====================================================================

2. PARAMETER YANG BISA DIATUR
-------------------------------

  Semua ada di SpottingConfig (preprocess-anxiety/spotting.py):

    block_size            = 7      ukuran blok POC
    padding_x / padding_y = 6 / 8  padding crop ROI
    min_phase_duration    = 2      durasi event minimum (frame)
    top_k_apex            = 5      maksimal apex per video
    distance_threshold    = 1      jarak minimum antar puncak
    prominence_threshold  = 0.005  keunggulan minimum puncak
    cutoff_ratio          = 0.3    ambang cutoff fase (30%)
    regions               = 5 ROI (landmark 17-67)
    target_size           = mata 48x32, alis 48x20, mulut 70x35

  Parameter tersembunyi (konstanta di file lain, tidak di config):

    - ApexSmoother: window = 5% panjang sinyal, clamp 5..31
    - ApexPhase:    merge_distance = 10
                    valley_uptick  = 0.75
                    MAX_SEARCH_RADIUS = 100
    - Notebook:     height = mean + std sinyal halus

  PERINGATAN (konflik parameter):
    - Default class ApexPhase: distance=5, prominence=0.1,
      cutoff=0.10
    - Yang DIPAKAI notebook: distance=1, prominence=0.005,
      cutoff=0.30 (dari config)
    - Default class tidak pernah terpakai; jangan bingung
      kalau membaca dua nilai berbeda di kode.


=====================================================================

3. TITIK LEMAH (KANDIDAT "THE ONE TO SET")
---------------------------------------------

  3.1 Referensi berurutan vs absolut (PALING KRUSIAL)
      - Spotting pakai frame N vs N-1  -> puncak KECEPATAN,
        terjadi di lereng naik ekspresi, BUKAN di puncak ekspresi.
      - Fitur model pakai POC-ABS vs frame-0 klip -> puncak
        PERPINDAHAN (apex ekspresi sebenarnya).
      - Teori: puncak turunan != puncak fungsi.
        Contoh: ekspresi naik 10 frame -> puncak kecepatan di
        frame ~5-6, apex sebenarnya di frame ~10.
      - Akibat: apex terdeteksi LEBIH AWAL, klip bergeser,
        fitur tidak berpusat pada ekspresi sebenarnya.
      - Perbaikan: pakai POC-ABS (frame-0 atau baseline bergulir)
        untuk sinyal spotting juga, supaya konsisten dengan fitur.
      - STATUS: SUDAH DIIMPLEMENTASIKAN 25/08/2026.
        Flag USE_ABS_BASELINE di process_all_datasets.ipynb
        (sel config):
          True  = POC-ABS (frame-0 baseline)  <-- default sekarang
          False = frame berurutan (kode asli)
        Untuk A/B test, tinggal ganti nilai flag dan jalankan
        ulang notebook. Index sinyal->frame (+1) tidak berubah
        karena kedua mode menghasilkan N-1 magnitude.

  3.2 Rata-rata seluruh wajah mengaburkan gerakan lokal
      - mean per blok + mean antar 5 ROI = satu angka global.
      - Micro-expression di SATU area (misal alis) diencerkan
        5x dan oleh blok statis -> sinyal kotor, SNR rendah.
      - Perbaikan: sinyal PER-ROI (5 sinyal terpisah, apex per
        area), atau pakai max alih-alih mean.

  3.3 Window smoothing 31 frame = 155 ms bisa menghapus ME pendek
      - Micro-expression = 1/25 - 1/5 detik = 8-40 frame di 200fps.
      - SavGol window hampir selalu 31 frame (clamp dari 5% panjang)
        -> ME 8-15 frame diratakan sampai nyaris hilang.
      - Perbaikan: window tetap 7-15 frame (sesuai durasi ME),
        bukan 5% dari panjang video.
      - STATUS: SUDAH DIIMPLEMENTASIKAN 25/08/2026.
        apex/apex_smoother.py sekarang memakai window TETAP 7 frame
        (untuk sinyal >= 7; sinyal pendek dipangkas ke bawah).
        Tambahan temuan 25/08: fps ACTUAL = 60 (bukan 200 seperti
        dokumentasi) -> ME = 2.4-12 frame di 60fps, jadi window 7
        (~117 ms) wajib, dan window lama 31 (= 517 ms) akan
        menghapus micro-expression sepenuhnya.

  3.4 Threshold height = mean+std (global)
      - Video dengan banyak gerakan global (bicara, gerak kepala)
        -> threshold naik -> micro-expression nyata terlewat.
      - Video tenang -> noise lolos jadi puncak palsu.
      - Perbaikan: ambang per-ROI, atau berbasis prominence saja,
        atau MAD (median absolute deviation, lebih tahan outlier).

  3.5 Landmark gagal -> magnitude 0.0
      - Frame yang gagal deteksi jadi nol -> lembah palsu +
        distorsi smoothing di sekitarnya.
      - Perbaikan: interpolasi nilai, atau deteksi ulang wajah.

  3.6 distance=1 + prominence=0.005 hampir non-aktif
      - Filtering praktis hanya bergantung pada height=mean+std
        dan merge_distance=10.
      - Artinya sensitivitas spotting ditentukan oleh SATU
        threshold itu. Parameter lain hampir tidak berpengaruh.


=====================================================================

4. PRIORITAS PERBAIKAN ("THE ONE TO SET")
--------------------------------------------

  Urutan prioritas dari yang paling mungkin berdampak:

  1. Sinyal spotting -> POC-ABS (frame-0 / baseline)
     Apex = puncak ekspresi sebenarnya, konsisten dengan fitur.
     (hipotesis terkuat: spotting dan fitur memakai definisi
     "puncak" yang berbeda, bisa salah menggeser seluruh klip)

  2. Sinyal per-ROI (5 sinyal, apex per area)
     SNR naik, gerakan lokal tidak terencerkan.

  3. Window smoothing 7-15 frame (bukan 31)
     Micro-expression pendek tidak terhapus.

  4. Threshold adaptif per-ROI
     Micro-expression tidak terlewat di video yang ramai gerak.


=====================================================================

5. CARA MENGUJI PER-VARIAN (SAAT DATA TERSEDIA)
--------------------------------------------------

  Rencana uji (A/B, semua pakai evaluasi subjek-disjoint dari
  foundings.md Fase 1):

    Varian A (baseline) : kode asli, sinyal berurutan + mean global
    Varian B           : A + sinyal POC-ABS (frame-0)
    Varian C           : A + sinyal per-ROI
    Varian D           : A + window smoothing 7-15
    Varian E           : kombinasi B+C+D

  Metrik pembanding: jumlah event terdeteksi per video,
  posisi apex vs ground-truth (kalau ada), lalu akurasi model
  end-to-end dengan split yang sama.

  CATATAN: semua uji butuh data video mentah (../dataset) atau
  minimal xlsx/npy dari tim. Tanpa data, hanya bisa disiapkan
  kodenya.
