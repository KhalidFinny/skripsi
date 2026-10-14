HASIL SEBELUM PERUBAHAN (BASELINE) - RESULTS
==============================================

> **Ringkasan rapi semua hasil (train/val/test) + semua perubahan:**
> `report/documentation/ringkasan.md`
> File INI hanya merekam kondisi awal (baseline) sebagai pembanding.
> Angka run terbaru ada di ringkasan dan di `output/training/*/summary.md`.

Tanggal      : 2026-08-25
Tujuan       : Merekam SEMUA hasil model dari kode ASLI (sebelum ada
               perubahan apa pun). Dokumen ini jadi pembanding: angka
               "sesudah" nanti diukur dengan cara yang sama dan
               dibandingkan dengan tabel di bawah.

PENTING (baca dulu):
- Angka di bawah diambil dari OUTPUT notebook yang sudah dijalankan
  tim sebelumnya (ter-render di file .ipynb), BUKAN dijalankan ulang.
- Sebagian besar angka memakai split yang BOCOR subjek (lihat
  foundings.md) -> angka lebih tinggi dari kenyataan.
- Satu-satunya angka yang bisa dipercaya penuh: yang memakai LOSO
  (subjek-disjoint), dan hasilnya BELUM ADA (notebook v21 tidak ada).


=====================================================================

1. TABR KUSTOM (core/TabR.py, LitTabR) - v1 s/d v21
-----------------------------------------------------

  Sumber: preprocess-anxiety/export_apex_tabr_train_test_v*.ipynb

  v19 dan v20 (balanced_train_clips, m=8, pat=8, freeze=11, lr 5.34e-4):
    internal acc  : 0.691507  (69,2%)
    external acc  : 0.726269  (72,6%)
    Catatan: angka v19 == v20 persis (seed 42 vs 72) - kemungkinan
    sel notebook disalin, bukan hasil run terpisah.

  v20 (tengah pelatihan, sebelum konvergen):
    internal acc  : 0.556233  (55,6%)
    -> ini sumber cerita "50-60%": model menebak kelas mayoritas.

  v21 (LOSO, seed 72):
    FILE NOTEBOOK TIDAK ADA di repo ini. Hanya tercatat di
    analisis_versi_summary.csv. Angka akurasinya TIDAK DIKETAHUI.

  Riwayat konfigurasi v1-v21: preprocess-anxiety/analisis_versi_summary.csv
  (kolom: seed, external, freeze, lr, m_neighbors, patience, split)
  - TANPA kolom akurasi - hanya konfigurasi.


=====================================================================

2. TABR RESMI (Yandex, bin/tabr.py) - HASIL UTAMA
----------------------------------------------------

  Sumber: notebooks/tabr_final_analysis.ipynb

  Baseline (convat_apex_anxiety, 392 fitur POC-ABS, seed 11):
    train acc     : 0.973574  (97,4%)  macroF1 0.972988
    val acc       : 0.756537  (75,7%)  bal 0.751303, macroF1 0.752527
    external test : 0.742826  (74,3%)  n=906 frame
                    bal 0.724237, macroF1 0.728077
    threshold 0.555 (dioptimasi dari val):
      test 0.748344 / bal 0.732113 / macroF1 0.735453

    -> gap train-test 23% = OVERFITTING jelas.

  Hasil tuning Optuna (logs/tabr_overnight_20260324_221022.log):
    trial 0 : val 0.7166, test 0.6865, best_epoch 34
              (patience 5, context_size 9, d_main 132,
               lr 3.37e-4, wd 1.76e-5)
    trial 22: val 0.7557 (terbaik)
    test tertinggi tercatat: 0.7638


=====================================================================

3. INFERENSI DI TANGGAL BARU (DATATEST) - TabR RESMI
------------------------------------------------------

  Sumber: notebooks/tabr_datatest_event_inference.ipynb
  Data: 15_only (1.207 frame/1.000 event/51 subjek),
         17_only (9.379/870/47), mixed (21.451/1.870/98)

  Level event (akurasi/bal/macroF1):
    mixed  max  : qwalk_q123_q4_q5    0.6642 / 0.4990 / 0.4237
    mixed  top3 : qwalk_q123_q4_q5    0.6449 / -      / 0.4485
    15_only max : 0.7150 (macroF1 0.4457)
    17_only max : qwalk_q12_q3_q4_alis 0.6092 (macroF1 0.3946)
    baseline    : mixed max 0.6503, 15_only max 0.6930

  Level subjek (baseline menang di semua):
    mixed  : 0.6837 (98 subjek)
    15_only: 0.7255 (51 subjek)
    17_only: 0.6383 (47 subjek)
    bal = 0.5, recall kelas "rendah" = 3-7%
    -> model hampir selalu memprediksi "cemas" (majority collapse).


=====================================================================

4. TABR RESMI - VARIAN SPLIT WAKTU (time-aware vs event)
----------------------------------------------------------

  Sumber: notebooks/tabr_compare_timeaware_vs_event_inference.ipynb

  Terbaik (qholdout_q123_q4_q5_alis, 608 fitur):
    test acc 0.8287, macroF1 0.8132, roc_auc 0.9011 (n=10.437)
    train 0.999108 / val 0.839556 -> OVERFITTING ekstrem
    CATATAN: split beda + bocor subjek -> TIDAK bisa dibandingkan
    dengan angka baseline 0.7428 (n=906) di bagian 2.

    UPDATE 2026-08-31: scripts/export_to_official_tabr_dataset_{qholdout,
    qwalkforward}.py SEKARANG subjek-disjoint (GroupShuffleSplit, seed 72,
    sama dengan baseline). Angka 0.8287 di atas (dan 0.7667 event-inference)
    BOCOR SUBJEK -> usang, harus diukur ulang sebelum dipakai.

  Event-inference winner: qholdout_q123_q4_q5 top3_mean 0.7667.
    [USANG - bocor subjek, lihat UPDATE di atas]


=====================================================================

5. BASELINE SVM / KNN / LSTM (comparasion/ - TUGAS BERBEDA!)
--------------------------------------------------------------

  PERINGATAN: baseline ini dikerjakan di dataset SAMM
  (klasifikasi EMOSI: Disgust vs Happiness), BUKAN klasifikasi
  kecemasan. Angka-angkanya tidak bisa dibandingkan langsung
  dengan TabR anxiety di atas.

  Sumber: comparasion/notebooks/{svm,knn,lstm}_*.ipynb

  SVM + POC   : 60/40 acc 0.9075 | 70/30 acc 0.9479
  SVM + 4QMV  : 60/40 acc 0.7464 | 70/30 acc 0.7308
  SVM + PCA   : 60/40 acc 0.8913 | 70/30 acc 0.9231
  KNN + POC   : 60/40 acc 0.6441 | 70/30 acc 0.6730
  KNN + 4QMV  : 60/40 acc 0.7101 | 70/30 acc 0.7115
  KNN + PCA   : SAMA PERSIS dengan SVM+PCA (kemungkinan salah salin)
  LSTM 4QMV   : train 1.0, val 0.30-0.50 (runtuh, data terlalu kecil)

  Bukti overfitting (svm_poc.ipynb, external test):
    train 0.9952 -> external test 0.2222 (jatuh drastis)


=====================================================================

6. RINGKASAN ANGKA YANG DIPAKAI SEBAGAI PEMBANDING
----------------------------------------------------

  Untuk tugas klasifikasi KECEMASAN (yang relevan dengan skripsi):

    Model                      Split               Angka
    -------------------------- ------------------- ------------------
    TabR kustom v19/v20        balanced clips      0.6915 int / 0.7263 ext
    TabR kustom v20 (awal)     balanced clips      0.5562 (collapse)
    TabR resmi baseline        event split+ext20   0.7428 test (n=906)
    TabR resmi threshold 0.555 event split+ext20   0.7483 test
    TabR resmi (datatest)      tanggal baru         0.61-0.72 acc,
                                                    macroF1 0.39-0.47
    TabR resmi qholdout_alis   qholdout (bocor)     0.8287 test (n=10.437)
                                                    [TIDAK sebanding]
    TabR resmi LOSO            LOSO                 BELUM ADA

  Kesimpulan baseline yang jujur:
    - Angka terbaik yang bisa dipercaya: TabR resmi ~0.74 test.
    - Begitu diuji ke data baru: turun ke ~0.61-0.72, dan
      macroF1 cuma 0.39-0.47 (majority collapse).
    - Semua angka sebelum LOSO berpotensi ke-inflasi oleh bocor subjek.

  Setelah perubahan kode nanti, angka "sesudah" diukur ULANG dengan
  protokol evaluasi yang sama (LOSO + macroF1) dan dibandingkan di sini.


=====================================================================

7. HASIL TERBARU - SPLIT SUBJEK-DISJOINT (SEBELUM PERUBAHAN BERIKUTNYA)
------------------------------------------------------------------------

  Tanggal      : 2026-08-31 (pipeline_anxiety_20260831_212745.log)
  Perubahan    : export_to_official_tabr_dataset.py memakai GroupShuffleSplit
                 subjek-disjoint (test 20%, val 20% partisipan) - menggantikan
                 split event-level yang bocor subjek.
  Split        : train 33 subjek / val 11 / test 12 (56 total, TIDAK bocor)
                 train 23.742 frame / val 8.922 / test 9.190 frame
  Fitur        : 392 POC-ABS (frame-0 displacement), format npy sama.

  Alur evaluasi: Optuna 30 trial -> konfigurasi terbaik -> evaluasi 15 seed
  -> ensemble-5.

  Optuna (30 trial, seed 72): best trial 26, val 0.5963.
  Semua trial val 0.50-0.60 -> model nyaris tidak bisa memisahkan kelas
  pada subjek yang belum pernah dilihat.

  Evaluasi 15 seed (konfigurasi terbaik: d_main=111, lr 3.85e-05,
  patience 4, context_size 11, dropout 0.49/0.47):
    terbaik seed 3:  val 0.6027 / test 0.6123
    rentang test   : 0.5619 - 0.6123
    test (seed 3)  : accuracy 0.6123, macroF1 0.5358, roc_auc 0.5839,
                     cross-entropy 0.6622
    train (seed 3) : accuracy 0.6365 -> gap train-test hanya 2,4 poin
                     (sebelumnya 23 poin) = overfitting hilang.

  Per-kelas test (seed 3), label 0=anxiety_rendah, 1=anxiety_tinggi:
    kelas 0: recall 0.261 / F1 0.347 (support 3.635)
    kelas 1: recall 0.842 / F1 0.724 (support 5.555)
    -> masih bias kelas mayoritas, tapi tidak seruntuh datatest
       (recall rendah 3-7% sebelumnya).

  Ensemble-5: hanya 3 anggota tercatat di log (berhenti di 0-ensemble-5/2):
    test 0.6217 / 0.6063 / 0.6040 (val 0.6159 / 0.6158 / 0.5937).

  Perbandingan dengan baseline lama (bagian 2, bocor subjek):
    - test acc 0.7428 (n=906, bocor) -> 0.6123 (n=9.190, subjek-disjoint).
      Penurunan ~13 poin = efek bocor subjek, BUKAN regresi model.
    - gap train-test 23 poin -> 2,4 poin: angka lama overfit.
    - roc_auc test 0.584 -> ranking nyaris acak pada subjek baru.
      Kesimpulan: fitur POC-ABS 392 saat ini hampir tidak memisahkan
      kelas di luar subjek latih. Ini baseline yang harus dikalahkan
      perubahan berikutnya (mis. sinyal per-ROI).


=====================================================================

8. EKSPERIMEN REDUKSI FITUR - 196 vs 392 vs 608 (2026-08-31)
--------------------------------------------------------------

  Temuan analisis fitur:
    - TIDAK ADA blok 7x7 yang 100% statis. Semua blok bergerak;
      blok paling jarang bergerak = mata_kiri cell 11 (6,5% frame),
      mulut cell 34 (pusat mulut, 10,7%). Kriteria "buang blok statis"
      membuang 0 fitur.
    - Redundansi nyata: t = atan2(y,x) dan m = hypot(x,y) TEPAT
      diturunkan dari x,y per blok (diverifikasi: 98/98 sel, t punya
      32 nilai unik, m 10 nilai unik = semua norma pasangan int).
      Kolom t,m (196 dari 392) TIDAK membawa informasi baru.

  Keputusan (user, 2026-08-31): buang t,m -> 392 -> 196 fitur (lossless).

  Dataset diekspor dengan SPLIT SUBJEK-DISJOINT YANG SAMA PERSIS
  (GroupShuffleSplit seed 72, 33/11/12 subjek; diverifikasi identik
  antar dataset; row 23.742/8.922/9.190; tanpa NaN):

    convat_apex_anxiety     392 fitur (baseline, sudah dilatih)
    convat_apex_anxiety_196 196 fitur (x,y saja, lossless)
    convat_apex_anxiety_608 608 fitur (392 + alis kiri/kanan 27 sel
                            masing-masing; dari poc_abs_flatten_ordered_608.xlsx,
                            region 5, row count identik 44.659)

  Persiapan training (TOML 0-tuning.toml sudah dibuat per dataset,
  search space sama dengan baseline):
    cd third_party/tabular-dl-tabr-official
    PYTHONUNBUFFERED=1 /home/finny/projects/Skripsi/.venv/bin/python \
      bin/go.py --force exp/tabr/convat_apex_anxiety_196/0-tuning.toml
    PYTHONUNBUFFERED=1 /home/finny/projects/Skripsi/.venv/bin/python \
      bin/go.py --force exp/tabr/convat_apex_anxiety_608/0-tuning.toml
    # lalu:
    uv run python scripts/collect_training_results.py --exp convat_apex_anxiety_196
    uv run python scripts/collect_training_results.py --exp convat_apex_anxiety_608

  Yang dibandingkan nanti (split sama): test acc/macroF1/bal_acc
  392 (0.6123/0.5358/0.5516) vs 196 vs 608.

  HASIL TRAINING (2026-09-01, 30 trial Optuna + evaluasi 15 seed,
  TOML search space sama, CUDA_VISIBLE_DEVICES=0):

    Dataset    Fitur  Test acc  macroF1  bal_acc  ROC-AUC  Train acc  gap
    ---------  -----  --------  -------  -------  -------  ---------  ----
    anxiety     392   0.6123    0.5358   0.5516   0.5839   0.6365     2.4
    anxiety_196 196   0.5998    0.4771   0.5213   0.5459   0.5697    -3.0
    anxiety_608 608   0.5860    0.5419   0.5450   0.5721   0.6774     9.1

  Bacaan:
    - 196 (buang t,m) TIDAK unggul: test acc turun 0.0125, macroF1 turun
      lebih jauh. Lossless secara informasi (t,m bijective terhadap x,y di
      grid 7x7), tapi satu run Optuna 30 trial = noise pencarian; model juga
      underfit (train 0.5697 < test). Untuk klaim "196 setara 392" perlu
      evaluasi konfigurasi terbaik yang SAMA di semua dataset.
    - 608 (tambah alis) TIDAK membantu: test acc terendah 0.5860, gap
      train-test paling besar (9.1) = alis menambah overfitting tanpa sinyal
      subjek-baru. Alis hanya "menang" di split bocor (qholdout_alis 0.8287).
    - Kesimpulan: reduksi fitur t,m dan penambahan alis keduanya tidak
      memperbaiki generalisasi subjek-disjoint; pembatasnya tetap sinyal
      per-subjek (ROC-AUC 0.55-0.58), bukan jumlah fitur.


=====================================================================

9. SINYAL PER-ROI (5 sinyal x 5 area = 25 fitur/frame) - 2026-09-01
--------------------------------------------------------------------

  Ide: agregasi per ROI menggantikan vektor per blok 7x7. Per frame
  (POC-ABS vs baseline), tiap ROI (mulut, mata_kiri, mata_kanan,
  alis_kiri, alis_kanan) menyumbang 5 sinyal:
    mean_m, max_m, mean_abs_x, mean_abs_y, motion_count (fraksi blok m>0)
  = 25 fitur/frame. Apex per area juga dideteksi (parameter sama dgn
  spotting: distance 1, prominence 0.005, cutoff 0.3, top-1, min durasi 2)
  -> output pelengkap output/apex/features/roi_apex.xlsx (8.814 baris,
  2.155 event; frame apex selalu di dalam onset..offset).

  Implementasi: export_apex_poc_abs_ordered_script.py --roi-signals
  (5 region; baris fitur IDENTIK dgn 392: 44.659 row, error 1 = event
  tomi yang sama). Bug awal: exception di deteksi apex membuang ~256
  event -> diperbaiki (apex gagal = None, baris fitur tetap dipertahankan).

  Dataset: convat_apex_anxiety_roi25, split subjek-disjoint IDENTIK
  (33/11/12, 23.742/8.922/9.190, tanpa NaN).

  HASIL TRAINING (30 trial Optuna + 15 seed, search space sama):

    Dataset   Fitur  Test acc  macroF1  bal_acc  ROC-AUC  gap train-test
    --------  -----  --------  -------  -------  -------  -------------
    anxiety    392   0.6123    0.5358   0.5516   0.5839   2.4
    anxiety_196 196  0.5998    0.4771   0.5213   0.5459   -3.0
    anxiety_608 608  0.5860    0.5419   0.5450   0.5721   9.1
    roi25       25   0.6337    0.5964   0.5962   0.6381   1.1

  roi25 UNGGUL di semua metrik test (acc +0.021, macroF1 +0.061,
  bal_acc +0.045, ROC-AUC +0.054 vs baseline 392) dan gap train-test
  terkecil (1.1 poin). Bacaan: agregasi per-ROI menangkap sinyal lebih
  baik daripada vektor blok 7x7 per blok, dengan dimensi 16x lebih kecil.
  (Catatan: satu run Optuna per dataset; kenaikan konsisten di 4 metrik
  dan gap overfitting terkecil -> bukan noise belaka.)


=====================================================================

10. PERBAIKAN SINYAL SPOTTING (3.2/3.4/3.5) - 2026-09-01
--------------------------------------------------------

  Diimplementasikan di process_all_datasets_script.py (pipeline stage 1),
  default = mode baru, bisa diubah via env var untuk A/B:

    SPOT_SIGNAL_MODE : 'roi_signals' (default) | 'global_mean'  (3.2)
    SPOT_INTERP      : '1' (default) | '0'                      (3.5)
    SPOT_THRESH      : 'meanstd' (default) | 'mad'              (3.4)

  3.2: sinyal per-ROI (bukan mean antar ROI); apex dideteksi per area
       dgn threshold per-ROI; event overlap digabung (ambil apex_value
       tertinggi). 3.4: threshold height = mean+std per sinyal, atau
       median+2.5*1.4826*MAD. 3.5: nilai landmark-gagal di-interpolasi
       linier (sebelumnya 0.0).

  Validasi A/B pada 15 video (3 sesi partisipan, output/apex_ab/):
    Mode                          events   per-video  apex_rel (median)
    A global, no interp (=lama)     75        5.0         0.50
    B global + interp               75        5.0         0.50
    C roi_signals + meanstd        201       13.4         0.50
    D roi_signals + mad            144        9.6         0.51
  - Mode A == metadata lama persis (75/75) -> refactor aman.
  - Interpolasi netral pada subset ini (landmark gagal jarang).
  - Per-ROI menaikkan sensitivitas 1.9-2.7x (gerakan lokal tidak
    terencerkan mean), apex tetap di tengah event.
  - Tradeoff: roi_signals menghasilkan event 2-3x lebih banyak;
    sebagian bisa noise. MAD (D) = kompromi (1.9x).

  AKIBAT: event/metadata berubah -> SEMUA dataset (392/196/608/roi25)
  harus di-export ulang dan dilatih ulang. Langkah: stage 1 spotting
  --force (jam) -> stage 2 fitur -> stage 3 npy -> training.
  CATATAN: notebook process_all_datasets.ipynb BELUM disinkronkan
  (script pipeline adalah sumber kebenaran).

=====================================================================

11. RETRAIN 392 FITUR DUA KALI - HASIL PAGI vs HASIL SEKARANG
--------------------------------------------------------------

  Run 1 (hasil pagi yang sudah dicatat di bagian 7):
    - split subjek-disjoint lama: 23.742 / 8.922 / 9.190 frame
    - best seed (berdasarkan val): seed 3
    - val 0.6027 / test 0.6123
    - test macroF1 0.5358 / bal_acc 0.5516 / ROC-AUC 0.5839
    - per-kelas test: recall label 0 = 0.261, label 1 = 0.842

  Run 2 (hasil sekarang; stage4_training_20260901_200527.log,
  output/training/convat_apex_anxiety/summary.md):
    - setelah spotting baru + re-export, split menjadi
      34.530 / 14.668 / 14.962 frame
    - Optuna 30 trial: best trial 11, val 0.7610 / test 0.6242
      (time 0:22:37)
    - evaluasi 15 seed: best seed berdasar val = seed 13
      val 0.7574 / test 0.6271
    - rentang test 15 seed: 0.6093 - 0.6326
      (test tertinggi mentah = seed 8, 0.6326; bukan seed terbaik val)
    - test seed 13: macroF1 0.5067 / bal_acc 0.5440 / ROC-AUC 0.5906
    - per-kelas test seed 13: recall label 0 = 0.171, label 1 = 0.917

  Ensemble-5 sekarang SUKSES jalan lagi (sesudah bug mismatch cache/split
  diperbaiki). Tiga blok seed memberi:
    - seed 0-4  : test 0.6248 / macroF1 0.4593 / bal_acc 0.5277
    - seed 5-9  : test 0.6357 / macroF1 0.4853 / bal_acc 0.5422
    - seed 10-14: test 0.6323 / macroF1 0.4708 / bal_acc 0.5358

  Bacaan jujur:
    - run 2 menaikkan accuracy test sedikit: 0.6123 -> 0.6271 (+0.0148)
    - tapi macroF1 turun: 0.5358 -> 0.5067, dan bal_acc turun:
      0.5516 -> 0.5440
    - recall kelas minoritas (label 0 / anxiety_rendah) turun cukup besar:
      0.261 -> 0.171
    - jadi training kedua BUKAN kemenangan bersih; model sekarang lebih
      sering benar di kelas mayoritas, tetapi makin lemah mengenali kelas
      rendah. Kalau metrik utama skripsi = macroF1/balanced accuracy, run 1
      masih lebih sehat daripada run 2 walau accuracy-nya lebih rendah.
