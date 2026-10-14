RIWAYAT PERUBAHAN & HASIL (CHANGES LOG)
========================================

> **BACA DULU (versi ringkas & rapi):** `report/documentation/ringkasan.md`
> Dokumen itu merangkum semua perubahan + hasil train/val/test dalam bahasa
> sederhana dan tampilan tabel. Dokumen INI adalah versi detail teknisnya.
> Seluruh isi ringkasan diambil dari sini, tidak ada angka baru.

Proyek  : Skripsi - klasifikasi tingkat kecemasan dari video wajah
          (micro-expression spotting POC-ABS -> fitur tabular -> TabR)
Dibuat  : 2026-09-28
Isi     : (tanggal) (apa yang diubah) (hasilnya), dari kondisi asli
          (commit pertama 2025-09-13) sampai kondisi terakhir hari ini.

Cara baca:
- Satu iterasi = satu blok dengan 5 field yang SAMA untuk semua iterasi
  (era 1, 2, 3 tidak beda format):

    ### Iterasi <era>.<nomor> - <judul singkat>
    Tanggal    : kapan dikerjakan
    Status     : selesai | berjalan | dihentikan
    Diubah     : apa yang diubah/ditambah/dihapus
    Dijalankan : uji/run yang dipakai untuk menguji iterasi itu ("-" kalau tidak ada)
    Hasil      : angka/keadaan setelah uji/run itu

- Hasil tiap iterasi ditulis DI DALAM blok iterasi itu, bukan di bagian lain.
  Era hanya pengelompokan kronologis; format blok di semua era identik.
- RINGKASAN 3-FIELD semua uji (tanggal / perubahan dari kondisi asli / hasil)
  ada di report/documentation/progress.md bagian "RIWAYAT SEMUA UJI".
  Dokumen itu untuk membaca cepat; dokumen ini untuk detail teknis.
- "Hasil" = angka/keadaan yang benar-benar tercatat di repo (log,
  summary.md, csv, dokumen). Tidak ada angka karangan.
- PERINGATAN: semua angka sebelum 2026-08-31 memakai split yang BOCOR
  subjek (orang yang sama ada di train dan test). Angka itu tinggi tapi
  tidak sah, jangan dipakai sebagai pembanding.

=====================================================================
0. HASIL TRAINING TERAKHIR (baca ini dulu)
=====================================================================

Run     : LOSO roi25 (1 subjek per fold = subjek yang diuji belum pernah
          dilihat model)
Selesai : 2026-09-28 12:00
Isi     : 56 fold x 3 seed, semua selesai. 20 fitur, 56 subjek, 44.424 baris.
File    : output/training/convat_apex_anxiety_loso_roi25/summary.md

Hasil per subjek (1 keputusan per subjek):

  accuracy          55.36%
  baseline          55.36%   <- accuracy = nebak kelas mayoritas
  sensitivity       70.67%
  specificity       43.01%
  AUC               51.91%   <- acak = 50%

  per seed          57.14% | 53.57% | 55.36%
  per grup          hanya_after 63.64% | before_sama 53.85% |
                    before_berubah 40%

Hasil per frame (sekunder): acc 49.84% / macroF1 49.82% / AUC 50.22%

Artinya: model belum bisa membedakan subjek baru. Accuracy-nya hanya
sebesar menebak kelas mayoritas, dan AUC 52% mendekati acak. Kalau harus
menebak, model cenderung bilang "tinggi" (sensitivity 71% jauh di atas
specificity 43%).

KENAPA begitu (hasil penyelidikan 2026-09-29, lihat Iterasi 3.8-3.13):
  - TIDAK ada sinyal level subjek yang bisa dipelajari dari ROI25. Baseline
    logistik LOSO pada matriks fitur yang sama: AUC 52.52% (mean+std) /
    44.77% (mean saja) / 44.13% (frame->rata subjek), permutation test
    p = 0.280. Baseline mayoritas acc 55.36%.
  - Penyebabnya varian fitur ANTAR subjek lebih besar dari varian frame
    DALAM subjek (mulut_mean_m: 0.353 vs 0.201), jadi fitur lebih kuat
    mengkodekan SIAPA orangnya daripada seberapa cemas dia.
  - Eksperimen agregasi level subjek (Iterasi 3.10) sudah selesai dan
    NEGATIF: AUC 41.29%, di bawah acak.
  - Karena cacatnya ada di representasi POC-ABS ROI25 (di hulu model),
    re-tune TabR / rebalance frame tidak bisa memperbaikinya.
  - Iterasi 3.11-3.13 (balance frame, agregasi clip, tuning) BELUM selesai:
    dihentikan sementara atas instruksi user karena suhu CPU 96C. Resume
    per fold lewat DONE.json, tidak mengulang yang sudah selesai.

=====================================================================
A. RINGKASAN ANGKA KUNCI (kronologis, untuk konteks - bukan hasil
   training terakhir)
=====================================================================

Tanggal        Kondisi                    Metrik test (utama)
-------------  -------------------------  ----------------------------------
s/d 2026-08-25 TabR resmi, split BOCOR    acc 74.28% / macroF1 72.81%
               subjek                     (train 97.36% -> gap 23 poin)
2026-08-31     392 fitur, split subjek-    acc 61.23% / macroF1 53.58% /
               disjoint                   bal_acc 55.16% (gap 2,4 poin)
2026-09-01     196 fitur                  acc 59.98% / macroF1 47.71%
2026-09-01     608 fitur (+alis)          acc 58.6% / macroF1 54.19%
                                          (gap 9,1 poin)
2026-09-01     roi25 (25 sinyal/ROI)      acc 63.37% / macroF1 59.64% /
                                          bal_acc 59.62% (gap 1,1)
                                          <- terbaik pada split subjek-disjoint,
                                             TAPI tidak bertahan di LOSO
2026-09-01     392 ulang, event spotting   acc 62.71% / macroF1 50.67% /
               baru (run 2)               bal_acc 54.4%
2026-09-17     LOSO 392, level FRAME       frame acc 60.41% / macroF1 44.8% /
               (skrip versi lama)         bal_acc 49.24% / AUC 51.51%
                                          -> angka ini TIDAK bisa ditafsirkan
2026-09-28     LOSO roi25, level SUBJEK   acc 55.36% = baseline 55.36%;
(TRAINING      3 seed, 56 fold, selesai   sens 70.67% / spec 43.01%; AUC 51.91%;
 TERAKHIR)     12:00:46                  frame AUC 50.22%
                                          -> masih dekat acak
2026-09-29     Diagnostik sinyal level    logistik LOSO di matriks fitur yang
               subjek (bukan TabR)        sama: AUC 52.52% (mean+std) /
                                          44.77% (mean saja) / 44.13%
                                          (frame->rata subjek); permutation
                                          test p = 0.280
                                          -> TIDAK ada sinyal yang bisa
                                             dipelajari dari ROI25
2026-09-29     Eksperimen 3: agregasi     subject acc 44.05% / AUC 41.29%
               level subjek, 56 fold x    (= DI BAWAH acak), sens 24.00% /
               3 seed, selesai            spec 60.22%
                                          -> negatif; memperkuat kesimpulan
                                             di atas
2026-09-29     Eksperimen 1/2/4           BELUM selesai (dihentikan sementara
               (balance frame, clip,      karena suhu CPU 96C): exp 1 13/56
               tuning)                    fold, exp 2 4/56 fold, exp 4 0 trial

CATATAN PENTING (metrik mana yang sah):
  Label di dataset ini milik subjek/sesi. Karena LOSO = 1 subjek per fold,
  test setiap fold hanya berisi SATU kelas. Akibatnya accuracy / balanced
  accuracy / ROC-AUC per fold TIDAK terdefinisi, dan metrik frame-level yang
  dipool antar fold hanya mengukur komposisi kelas di dalam subjek, bukan
  kemampuan model. Mulai 2026-09-24 collect_loso_results.py memakai metrik
  LEVEL SUBJEK sebagai headline karena alasan ini. Semua angka LOSO
  level-frame (termasuk 60.41% di atas) tidak sah dipakai sebagai bukti
  performa.

=====================================================================
B. LOG ITERASI (format seragam)
=====================================================================

--- ERA 1: PEMBANGUNAN AWAL (2025-09-13 s/d 2026-08-25) ---

### Iterasi 1.1 - Commit pertama
Tanggal    : 2025-09-13
Status     : selesai
Diubah     : Ekstraksi frame + perbaikan dependency
Dijalankan : -
Hasil      : Repo proyek skripsi terbentuk (9bbae70, 328bcf3, ffe491c).
             Belum ada angka evaluasi.

### Iterasi 1.2 - Crop/preprocessing data wajah
Tanggal    : 2025-09-18
Status     : selesai
Diubah     : Crop/preprocessing data wajah
Dijalankan : -
Hasil      : Data crop siap diproses (3252444).

### Iterasi 1.3 - LOSO versi lama
Tanggal    : 2025-10-01
Status     : selesai
Diubah     : Implementasi LOSO versi lama
Dijalankan : -
Hasil      : Lipatan LOSO pertama (9673e89). Metrik LOSO belum dicatat
             di repo.

### Iterasi 1.4 - Deteksi onset-apex
Tanggal    : 2025-10-13
Status     : selesai
Diubah     : Deteksi onset-apex
Dijalankan : -
Hasil      : Modul apex/ lahir (198c190).

### Iterasi 1.5 - POC-ABS + kuadran + vektor gerakan
Tanggal    : 2025-12-20
Status     : selesai
Diubah     : POC-ABS, kuadran, vektor gerakan
Dijalankan : -
Hasil      : Jalur fitur gerakan sub-piksel tersedia (3602bc8, aa65501).

### Iterasi 1.6 - Model TabR kustom (LitTabR v1-v21)
Tanggal    : 2025-12-21
Status     : selesai
Diubah     : Model TabR kustom
Dijalankan : -
Hasil      : Klasifikasi tabular jalan (8258638).

### Iterasi 1.7 - Spotting + analitik q1-q5
Tanggal    : 2026-02-14
Status     : selesai
Diubah     : Spotting + analitik q1-q5
Dijalankan : -
Hasil      : Pipeline spotting berbasis notebook process_all_datasets.ipynb
             (b3392f1, a568867).

### Iterasi 1.8 - Pendekatan baru deteksi apex
Tanggal    : 2026-02-25
Status     : selesai
Diubah     : Pendekatan baru deteksi apex
Dijalankan : -
Hasil      : apex/apex_phase.py (c10878d).

### Iterasi 1.9 - Ganti ke TabR resmi (Yandex)
Tanggal    : 2026-04-06
Status     : selesai
Diubah     : Ganti model kustom ke TabR resmi
Dijalankan : Training TabR resmi, split qholdout (BOCOR subjek)
Hasil      : train 97.36% / val 75.65% / test 74.28%, macroF1 72.81%
             (ac5a122). Split BOCOR subjek -> tidak sah sebagai performa.

### Iterasi 1.10 - Rapikan skrip ekspor dataset anxiety
Tanggal    : 2026-05-03
Status     : selesai
Diubah     : Rapikan skrip ekspor dataset (split event/qholdout/qwalkforward)
Dijalankan : -
Hasil      : 3 skrip ekspor (41a336d, 1a442ea); SEMUA masih bocor subjek.

### Iterasi 1.11 - Merge PR #1 apex/v3
Tanggal    : 2026-05-18
Status     : selesai
Diubah     : Merge PR #1 apex/v3
Dijalankan : -
Hasil      : Titik akhir kode warisan (2053d6e).

### Iterasi 1.12 - TabR kustom v19/v20
Tanggal    : 2026-08-25
Status     : selesai
Diubah     : Balanced clips, m=8, pat=8, freeze=11
Dijalankan : Evaluasi internal + eksternal
Hasil      : internal 69.15% / eksternal 72.63% (angka lama, bocor subjek).

### Iterasi 1.13 - TabR resmi, split qholdout + 608 fitur
Tanggal    : 2026-08-25
Status     : selesai
Diubah     : Tambah fitur alis (608 kolom)
Dijalankan : Training TabR resmi, split qholdout
Hasil      : acc 82.87% / macroF1 81.32%, TAPI train 99.91% -> overfit +
             bocor subjek, tidak sebanding dengan angka lain.

### Iterasi 1.14 - Inferensi di tanggal baru (datatest)
Tanggal    : 2026-08-25
Status     : selesai
Diubah     : Uji generalisasi ke data tanggal baru
Dijalankan : Inferensi datatest, 98 subjek
Hasil      : acc 61%-72%, macroF1 39%-47%; recall kelas "rendah" 3-7%
             (model hampir selalu menebak "cemas").

--- ERA 2: AUDIT & REFACTOR (2026-08-25 s/d 2026-09-03) ---

### Iterasi 2.1 - Audit penuh kode + snapshot dokumentasi
Tanggal    : 2026-08-25
Status     : selesai
Diubah     : Audit kode + tulis before.md, findings/foundings.md,
             findings/spotting-foundings.md, results/results.md + backup
             fisik 668 MB
Dijalankan : -
Hasil      : Semua angka lama terkumpul. 5 temuan utama: (1) subjek bocor
             antar split di SEMUA strategi lama, hanya LOSO yang aman;
             (2) fps asli 60/30, bukan 200; (3) kode optical flow tidak ada
             di repo; (4) ViT belum layak (VRAM 4 GB); (5) 5 file kode mati.
             Angka belum berubah.

### Iterasi 2.2 - Fix spotting #1 (baseline frame-0)
Tanggal    : 2026-08-25
Status     : selesai
Diubah     : Sinyal spotting pakai POC-ABS baseline frame-0
             (USE_ABS_BASELINE = True)
Dijalankan : -
Hasil      : Apex kembali ke puncak ekspresi sebenarnya (sebelumnya puncak
             kecepatan di lereng naik).

### Iterasi 2.3 - Fix spotting #3 (smoothing SavGol)
Tanggal    : 2026-08-25 s/d 2026-08-30
Status     : selesai
Diubah     : Smoothing SavGol window tetap 7 frame (dulu 5% panjang sinyal =
             sampai 31 frame = 517 ms)
Dijalankan : -
Hasil      : Micro-expression pendek (2,4-12 frame @60fps) tidak lagi
             diratakan sampai hilang.

### Iterasi 2.4 - Hapus 5 file kode mati
Tanggal    : 2026-08-26
Status     : selesai
Diubah     : Hapus tabr_v2.py, tabr_faithful.py, utis.py, conv1_base.py,
             qholdout_copy.py
Dijalankan : Cek importer
Hasil      : Repo bersih, tidak ada importer rusak. Akurasi tidak berubah.
             Commit e588d3b.

### Iterasi 2.5 - Split evaluasi diganti subjek-disjoint
Tanggal    : 2026-08-31
Status     : selesai
Diubah     : GroupShuffleSplit seed 72 (33/11/12 subjek) menggantikan split
             level event
Dijalankan : Run 1, 392 fitur, 15 seed
Hasil      : test 61.23% / macroF1 53.58% / bal_acc 55.16% / AUC 58.39%;
             train 63.65% -> gap 23 jadi 2,4 poin. Turun ~13 poin = efek
             bocor subjek yang dihapus, bukan regresi.

### Iterasi 2.6 - Ekspor varian fitur 196
Tanggal    : 2026-09-01
Status     : selesai
Diubah     : Buang kolom t,m yang lossless
Dijalankan : Training 15 seed, split subjek-disjoint
Hasil      : test 59.98% / macroF1 47.71% / bal_acc 52.13% (justru turun).

### Iterasi 2.7 - Ekspor varian fitur 608
Tanggal    : 2026-09-01
Status     : selesai
Diubah     : 392 fitur + alis kiri/kanan
Dijalankan : Training 15 seed, split subjek-disjoint
Hasil      : test 58.6% / macroF1 54.19% / bal_acc 54.5%, gap 9,1 poin ->
             menambah overfitting, tidak membantu.

### Iterasi 2.8 - Ekspor fitur per-ROI (roi25)
Tanggal    : 2026-09-01
Status     : selesai
Diubah     : 5 sinyal x 5 area = 25 fitur/frame (mean_m, max_m, |x|, |y|,
             motion_count) + apex per area
Dijalankan : Training 15 seed, split subjek-disjoint
Hasil      : test 63.37% / macroF1 59.64% / bal_acc 59.62% / AUC 63.81%,
             gap 1,1 poin. Unggul di 4 metrik vs 392 -> varian terbaik pada
             split subjek-disjoint (lihat Iterasi 3.7: tidak bertahan di LOSO).

### Iterasi 2.9 - Mode sinyal spotting baru (per-ROI)
Tanggal    : 2026-09-01
Status     : selesai
Diubah     : Default baru: sinyal per-ROI (bukan mean global), interpolasi
             landmark gagal, threshold mean+std atau MAD
Dijalankan : A/B 15 video
Hasil      : mode lama 75 event (5,0/video); per-ROI + mean+std 201
             (13,4/video); per-ROI + MAD 144 (9,6/video). Apex tetap di
             tengah event (median 50%-51%). Sensitivitas naik 1,9-2,7x ->
             semua dataset wajib ekspor ulang.

### Iterasi 2.10 - Re-spotting + re-ekspor 392 (event baru)
Tanggal    : 2026-09-01 (malam)
Status     : selesai
Diubah     : Re-spotting + re-ekspor 392 dengan event set baru (split sama)
Dijalankan : Run 2 + ensemble 5 seed
Hasil      : Split membesar: 34.530 / 14.668 / 14.962 frame. Run 2: test
             62.71% / macroF1 50.67% / bal_acc 54.4% / AUC 59.06%. Recall
             kelas "rendah" turun 26.1% -> 17.1% (makin bias mayoritas).
             Ensemble 5 seed: test 63.57% tapi macroF1 48.53% -> run 1 lebih
             sehat untuk macroF1.

### Iterasi 2.11 - Dokumen konsolidasi hasil refactor
Tanggal    : 2026-09-02
Status     : selesai
Diubah     : Tulis report/results/result-from-refactor-current-state.txt
Dijalankan : -
Hasil      : Satu file ringkas berisi pipeline lama, temuan, perubahan, arti
             angka dalam bahasa sederhana, rencana.

### Iterasi 2.12 - Logika pipeline pindah dari notebook ke skrip
Tanggal    : 2026-09-03
Status     : selesai
Diubah     : scripts/spotting.py, extract_features_poc_abs.py,
             extract_features_roi.py, switch_spotting_config.py,
             export_to_official_tabr_dataset*.py
Dijalankan : -
Hasil      : Skrip .py jadi sumber kebenaran; notebook 55 MB tidak lagi
             dipakai menjalankan pipeline. report/documentation/pipeline.md
             jadi peta pipeline.

--- ERA 3: EVALUASI LOSO & ITERASI TERAKHIR (2026-09-14 s/d 2026-09-28) ---

### Iterasi 3.1 - run_loso.py + run_loso_ab.sh
Tanggal    : 2026-09-14
Status     : selesai
Diubah     : LOSO murni subjek-disjoint (test = 1 subjek/fold, val = 20%
             subjek sisa), hyperparameter dari run utama (bukan tuning per
             fold), resume otomatis per fold (DONE.json)
Dijalankan : LOSO 392 fitur, 3 seed x 56 fold; opsi --imbalance frames
             (oversample frame kelas minoritas) dan --variance-threshold 1e-4
             (buang blok statis)
Hasil      : LOSO jalan 3 seed x 56 fold dengan resume per fold. Hasil
             dilaporkan di Iterasi 3.2 (level frame).

### Iterasi 3.2 - LOSO 392 selesai dikumpulkan (versi skrip LAMA = level frame)
Tanggal    : 2026-09-17
Status     : selesai
Diubah     : collect_loso_results.py dipakai pertama kali (dataset
             convat_apex_anxiety_loso = 392 fitur)
Dijalankan : scripts/collect_loso_results.py --exp convat_apex_anxiety_loso
Hasil      : Frame-level (pooling semua fold): acc 60.41% / macroF1 44.8% /
             bal_acc 49.24% / AUC 51.51%; recall kelas rendah 10.1% / tinggi
             88.4%. Event-level: acc 61.81% / macroF1 40.24% / bal_acc 49.47%.
             Per-subjek: mean 52.74%, median 53.45%, min 1.3%, max 98.9%
             (56 subjek).
             BACAAN: di subjek baru model masih dekat tebakan (AUC ~50%) dan
             sangat bias mayoritas.
             CATATAN: tabel di atas versi skrip LAMA (level frame). Angka
             level frame tidak sah ditafsirkan di setup LOSO - lihat catatan
             di bagian A.

### Iterasi 3.3 - LOSO roi25 percobaan pertama
Tanggal    : 2026-09-17
Status     : dihentikan
Diubah     : -
Dijalankan : LOSO roi25 (logs/loso_roi25_frames.log)
Hasil      : Berjalan (log 4,1 MB), terhenti di fold_039. Pipeline hari itu
             sempat gagal karena dataset masih dicari di /mnt/FINNY/dataset.

### Iterasi 3.4 - Pipeline dijalankan di mesin baru
Tanggal    : 2026-09-22 s/d 2026-09-23
Status     : selesai
Diubah     : Path dataset dipindah ke /home/finny/datasets/anxiety_raw
Dijalankan : scripts/run_pipeline.sh (stage 1 spotting)
Hasil      : Beberapa run gagal dulu (.venv tidak ada, path dataset salah),
             lalu berhasil: stage 1 spotting 560/560 video (~41 menit) ->
             output/apex/metadata.xlsx + output/apex/event_signals/ total
             diperbarui.

### Iterasi 3.5 - Cache fitur + config LOSO tetap
Tanggal    : 2026-09-24
Status     : selesai
Diubah     : scripts/build_feature_cache.py -> poc_abs_roi_signals_full.pkl;
             experiments/configs/tabr_loso_roi25.toml; perbarui
             run_pipeline.sh, run_loso.py, collect_loso_results.py
Dijalankan : -
Hasil      : Stage 1 & 2 bisa dilewati (hasil sudah ada), stage 3 LOSO roi25
             bisa dimulai tanpa spotting ulang.

### Iterasi 3.6 - LOSO roi25 lanjut (resume per fold)
Tanggal    : 2026-09-24 s/d 2026-09-27
Status     : selesai
Diubah     : -
Dijalankan : LOSO roi25 resume per fold (tiap fold = 1 subjek, seed
             dijalankan berurutan dalam satu fold)
Hasil      : Berjalan 09-24 20:07 -> 23:03 (log 7,1 MB), dilanjutkan 09-27
             20:54 -> 21:56. Dataset LOSO roi25 = 20 fitur efektif (5 dari
             25 kolom dibuang VarianceThreshold 1e-4).

### Iterasi 3.7 - LOSO roi25 SELESAI 56/56 fold x 3 seed (= TRAINING TERAKHIR)
Tanggal    : 2026-09-28 (restart pipeline 09:04, 09:47, 10:34; selesai 12:00:46)
Status     : selesai
Diubah     : -
Dijalankan : scripts/run_pipeline.sh (mode anxiety) -> stage 3
             scripts/run_loso.py, log logs/stage3_loso_20260928_103440.log;
             dataset: 44.424 baris, 56 subjek, 20 fitur, label unit = person
             (20.782 baris fase "before" dibuang); imbalance=clips,
             var-thresh=1e-4, score=roc-auc
Hasil      : 56/56 fold selesai (168 report.json = 56 fold x 3 seed),
             dikumpulkan otomatis ke
             output/training/convat_apex_anxiety_loso_roi25/.
             LEVEL SUBJEK (headline, 1 keputusan/subjek):
               accuracy           55.36% +- 1.79% (= baseline mayoritas 55.36%)
               sensitivity        70.67% +- 6.11%
               specificity        43.01% +- 8.12%
               PPV                50.11% +- 1.45%
               NPV                64.57% +- 0.51%
               ROC-AUC            51.91% +- 0.32%
               confusion (pooled)  TN 40 / FP 53 / FN 22 / TP 53
               pooling antar seed  acc 57.14% / sens 64% / spec 51.61% /
                                   AUC 52.77%
               per grup fase       hanya_after (n=33) acc 63.64%;
                                   before_sama (n=13) acc 53.85%;
                                   before_berubah (n=10) acc 40%
             LEVEL FRAME (sekunder): acc 49.84% +- 0.24% / macroF1 49.82% /
             bal_acc 50.01% / AUC 50.22% / recall rendah 46.43%, tinggi
             53.59%.
             BACAAN: di subjek baru model praktis tidak lebih baik dari
             menebak kelas mayoritas (AUC ~52%); keunggulan roi25 di split
             subjek-disjoint (Iterasi 2.8) TIDAK bertahan di LOSO.

### Iterasi 3.8 - Klarifikasi metrik AUC (kapan dipakai)
Tanggal    : 2026-09-29
Status     : selesai
Diubah     : -
Dijalankan : Cek lib/data.py (default score binclass), bandingkan
             0-tuning.toml lama vs tabr_loso_roi25.toml, baca best_report.json
             dan exp/tabr/convat_apex_anxiety_roi25/0-evaluation/13.toml
Hasil      : AUC SELALU dihitung dan ditulis ke report.json/summary.csv sejak
             awal, TAPI baru jadi metrik PEMILIHAN (early stopping) di
             protokol LOSO.
               - Protokol lama: tidak ada key `score` -> lib/data.py:86-90
                 default binclass = "accuracy". Bukti: best_report.json lama
                 train roc-auc 68.99% tapi train score 65.92% (= accuracy).
               - Protokol LOSO: experiments/configs/tabr_loso_roi25.toml:29
                 `score = "roc-auc"`, butuh patch lokal lib/metrics.py
                 (test 1 subjek -> nan, bukan None).
             Artinya exp 1-4 tidak perlu kerja AUC baru: config LOSO sudah
             memakai roc-auc.
             DIBALIK di Iterasi 3.14: seleksi kembali ke accuracy.

### Iterasi 3.9 - Diagnostik: apakah ada sinyal level subjek?
Tanggal    : 2026-09-29
Status     : selesai
Diubah     : -
Dijalankan : Baseline logistik LOSO pada matriks fitur yang sama (bukan TabR),
             di 3 representasi, plus permutation test 200 shuffle
Hasil      : TIDAK ada sinyal level subjek yang bisa dipelajari dari ROI25:
               subject mean+std (50 kolom)   AUC 52.52% / acc 48.21%
               subject mean saja (20 kolom)  AUC 44.77% / acc 48.21%
               frame logistik -> rata subjek  AUC 44.13% / acc 50.00%
               baseline mayoritas            acc 55.36%
               permutation test              observed 52.52% vs null
                                             46.43% +- 10.57%, p = 0.280
             MEKANISME (varian fitur antar subjek > varian frame dalam subjek):
               mulut_mean_m         antar 0.353 / dalam 0.201
               mata_kiri_mean_m     antar 0.285 / dalam 0.216
               mulut_motion_count   antar 0.164 / dalam 0.105
             BACAAN: fitur lebih kuat mengkodekan SIAPA orangnya daripada
             seberapa cemas dia. Standardisasi train tidak menutup celah ini
             karena pergeserannya bukan affine global. Cacat ada di
             representasi POC-ABS ROI25, di hulu model.
             KOREKSI: angka logistik ~59% yang sempat disebut tidak sah
             (ranking fitur dihitung dari seluruh tabel = bocor). Angka yang
             benar 52.52%.

### Iterasi 3.10 - Eksperimen 3: agregasi level subjek (1 baris = 1 subjek)
Tanggal    : 2026-09-29
Status     : selesai
Diubah     : scripts/run_loso.py: opsi baru --aggregate none|clip|subject
             (ringkas fitur mean+std sebelum training); mode subject tanpa
             balance clips supaya tiap subjek tetap ikut. Tambah
             aggregate_rows() + AGG_KEYS.
Dijalankan : ./run loso --dataset exp3_subject_agg --aggregate subject --seeds 3
             (56 fold x 3 seed, 56 baris = 1 baris/subjek, 40 fitur mean+std)
Hasil      : 56/56 fold selesai, dikumpulkan ke
             output/training/exp3_subject_agg/.
             LEVEL SUBJEK: accuracy 44.05% +- 5.46% (= DI BAWAH baseline
             55.36%), sensitivity 24.00% +- 0.00%, specificity 60.22% +- 9.86%,
             ROC-AUC 41.29% +- 7.38%.
             confusion (pooled antar seed): TN 56 / FP 37 / FN 57 / TP 18.
             BACAAN: negatif, dan gagal DI BAWAH acak. Artinya vektor rata-rata
             subjek justru anti-korelasi dengan label setelah identitas subjek
             dilepas. Konsisten dengan Iterasi 3.9: masalahnya representasi,
             bukan satuan baris training.

### Iterasi 3.11 - Eksperimen 1: balance level FRAME
Tanggal    : 2026-09-29
Status     : berjalan (dihentikan sementara, 13/56 fold)
Diubah     : -
Dijalankan : ./run loso --dataset convat_apex_anxiety_loso_roi25_frames
             --imbalance frames --seeds 3 (log logs/stage3_loso_*_frames.log)
Hasil      : 13/56 fold selesai. Train jadi seimbang frame (mis. 31.283 ->
             33.736 baris). Belum ada hasil akhir; DONE.json per fold, jadi
             resume tidak mengulang fold yang sudah selesai.
             DIHENTIKAN atas instruksi user (suhu CPU 96C).

### Iterasi 3.12 - Eksperimen 2: agregasi level clip
Tanggal    : 2026-09-29
Status     : berjalan (dihentikan sementara, 4/56 fold)
Diubah     : -
Dijalankan : ./run loso --dataset exp2_clip_agg --aggregate clip --seeds 3
             (log logs/exp2_clip_agg.log; 44.424 baris frame -> 3.244 baris
             clip, 40 fitur mean+std)
Hasil      : 4/56 fold selesai. Belum ada hasil akhir.
             DIHENTIKAN atas instruksi user (suhu CPU 96C).

### Iterasi 3.13 - Eksperimen 4: tuning LOSO di fold 0
Tanggal    : 2026-09-29
Status     : berjalan (0 trial selesai)
Diubah     : experiments/configs/tabr_loso_roi25_tuning_fold0.toml (salinan
             tabr_loso_roi25_tuning.toml, path -> data/exp4_stage_fold0,
             n_trials 20); data fold 0 di-stage lewat
             ./run loso --dataset exp4_stage_fold0 --fold 0 --seeds 0
Dijalankan : tune.py pada config di atas (log logs/exp4_tuning_fold0.log)
Hasil      : 0 trial selesai. Tuning di CPU ~8 menit/epoch (tidak layak);
             harus dijalankan di GPU setelah run LOSO lain selesai.
             DIHENTIKAN atas instruksi user (suhu CPU 96C).

### Iterasi 3.14 - Balik ke seleksi accuracy (batalkan tambahan AUC)
Tanggal    : 2026-09-29
Status     : selesai
Diubah     : experiments/configs/tabr_loso_roi25.toml: hapus `score =
             "roc-auc"` (ganti jadi komentar penjelasan);
             experiments/configs/tabr_loso_roi25_tuning.toml: hapus
             `space.data.score` + perbaiki header yang menyebut AUC;
             experiments/configs/tabr_loso_roi25_tuning_fold0.toml: hapus
             `space.data.score`
Dijalankan : Verifikasi statis: lib.load_config() pada ketiga config
             (tanpa training, supaya mesin tetap dingin)
Hasil      : Ketiga config -> score=None -> efektif "accuracy" (default
             binclass TabR), sama seperti protokol asli. AUC tetap DIHITUNG
             dan ditulis ke report.json/summary.csv (itu kode upstream TabR
             sejak awal, bukan tambahan), hanya tidak dipakai memilih epoch.
             ALASAN: perubahan yang disengaja cuma dua - protokol LOSO dan
             fitur ROI25. Menambah AUC sebagai metrik pemilihan ikut mengubah
             perilaku early stopping, jadi tidak bisa dipisahkan saat
             membandingkan dengan angka lama.
             CATATAN PENTING: patch lokal di lib/metrics.py TIDAK dibalik.
             Patch itu bukan mesin pemilihan AUC, tapi kompatibilitas LOSO:
             upstream memanggil roc_auc_score tanpa penjaga, dan test set
             tiap fold LOSO cuma 1 kelas -> ValueError. Patch menambah
             penjaga len(np.unique(y_true)) > 1, zero_division=0, dan
             labels=[0,1]. Tanpa itu semua fold LOSO gagal.
             DIBATALKAN di Iterasi 4.1: AUC dihapus seluruhnya, jadi patch
             dan panggilan roc_auc_score tidak diperlukan lagi.

--- ERA 4: PERBAIKAN REPRESENTASI & PROTOKOL (2026-10-06) ---

Rencana lengkap: report/plans/2026-10-06-loso-representation-fixes/.
Analisis literatur: report/findings/literature-accuracy-drop-2021-2026.md.
Daftar sitasi: report/documentation/research-papers.md.
Catatan: *.md masuk .gitignore, jadi dokumen-dokumen ini tidak terlacak git.

### Iterasi 4.1 - Hapus AUC dari pipeline
Tanggal    : 2026-10-06
Status     : selesai
Diubah     : third_party/.../lib/metrics.py: hapus seluruh blok perhitungan
             'roc-auc' binclass + patch lokal float('nan');
             lib/data.py: hapus 'roc-auc' dari _SCORE_SHOULD_BE_MAXIMIZED;
             scripts/collect_loso_results.py: buang roc_auc dari
             subject_metrics()/frame_metrics(), buang baris AUC di summary.md,
             buang import roc_auc_score;
             scripts/run_loso.py: buang PATCH_MARKER, PATCHED_FILE, dan
             check_tabtr_patch() + pemanggilannya; perbarui pesan split;
             experiments/configs/tabr_loso_roi25*.toml: perbarui komentar.
Dijalankan : grep sisa referensi AUC; collect_loso_results.py dijalankan ulang
             pada hasil LOSO 2026-09-28 dengan --out .amp/in/verify (hasil lama
             TIDAK ditimpa).
Hasil      : Tidak ada roc_auc/roc-auc di kode proyek maupun report TabR.
             summary.md baru: tanpa baris AUC, level frame ditandai
             "diagnostik komposisi, BUKAN performa". Angka lama tidak berubah
             (accuracy 0.5536, sens 0.7067, spec 0.4301).

### Iterasi 4.2 - Normalisasi fitur per subjek (sebab #1: identitas)
Tanggal    : 2026-10-06
Status     : selesai (kode); belum dijalankan di training
Diubah     : scripts/run_loso.py: fungsi subject_standardize() + opsi baru
             --subject-norm {none,subject} (default 'none' = perilaku lama).
             Tiap fitur di-z-score memakai mean/std subjek itu sendiri, tanpa
             label, diterapkan ke train/val/test. Ditolak bila digabung
             --aggregate subject (std subjek = 0).
Dijalankan : Verifikasi statis pada tabel nyata (44.424 baris, 56 subjek,
             25 fitur).
Hasil      : Setelah normalisasi, max |mean per subjek| = 1.23e-15 dan
             max |std per subjek - 1| = 2.66e-15; jumlah baris tetap;
             subjek 1 baris tidak menghasilkan NaN.
             BELUM dijalankan di training TabR (butuh GPU + waktu; menunggu
             perintah user).

### Iterasi 4.3 - Fitur temporal onset->apex->offset (sebab #2: ROI25 statis)
Tanggal    : 2026-10-06
Status     : selesai
Diubah     : scripts/build_temporal_features.py (baru). Tiap event_clip
             (lintasan onset->offset) diringkas jadi 5 deskriptor per ROI per
             sinyal dasar: peak, ttp (waktu ke puncak 0..1), rise, fall, auc.
             4 sinyal dasar (mean_m, mean_abs_x, mean_abs_y, motion_count) x
             5 ROI x 5 deskriptor = 100 kolom baru.
Dijalankan : .venv/bin/python scripts/build_temporal_features.py
Hasil      : experiments/features/apex/poc_abs_roi_signals_temporal.pkl
             (+ .xlsx): 65.206 baris, 138 kolom (38 lama + 100 temporal),
             4.737 event, tidak ada NaN. Tabel lama tidak diubah.

### Iterasi 4.4 - Baseline netral per subjek (sebab #3: acuan = frame onset)
Tanggal    : 2026-10-06
Status     : kode selesai; BELUM dijalankan (dataset mentah tidak ada)
Diubah     : scripts/process_spotting_pipeline.py: env SPOT_SAVE_NEUTRAL
             (default 0) + SPOT_NEUTRAL_FRAMES (default 10); fungsi
             save_neutral_reference() menyimpan median 10 frame pertama video
             sebagai neutral.png per sample.
             scripts/extract_features_poc_abs.py: opsi --baseline
             {onset,neutral} (default 'onset' = perilaku lama) + --output;
             acuan POC memakai neutral.png bila ada, fallback ke frame onset
             dengan peringatan sekali per sample.
             scripts/run_pipeline.sh: stage 1 mengirim SPOT_SAVE_NEUTRAL=1;
             stage 2 memakai --baseline neutral dan menulis ke
             poc_abs_roi_signals_neutral.xlsx (tabel lama tidak ditimpa).
Dijalankan : Verifikasi statis (parse + --help). TIDAK dijalankan end-to-end:
             /mnt/FINNY/dataset tidak ada di mesin ini, jadi re-run spotting +
             ekstraksi harus dilakukan di mesin yang punya dataset mentah.
Hasil      : Kode + perintah siap. Angka belum ada (menunggu re-run).

### Iterasi 4.5 - Protokol level subjek + interval kepercayaan (sebab #4)
Tanggal    : 2026-10-06
Status     : selesai
Diubah     : scripts/collect_loso_results.py: helper wilson_interval() dan
             fmt_ci(); tabel level subjek dapat kolom 95% CI (Wilson, pooled
             antar seed); bagian level frame diberi penjelasan tegas bahwa
             angkanya bukan performa.
Dijalankan : collect_loso_results.py --exp convat_apex_anxiety_loso_roi25
             --out .amp/in/verify
Hasil      : accuracy 0.5536 dengan CI 95% 0.4414-0.6923. CI MEMUAT baseline
             mayoritas 0.5536 -> model tidak terbukti lebih baik dari menebak
             kelas mayoritas. Sens 0.7067 (CI 0.4452-0.7975), spec 0.4301
             (CI 0.3484-0.6803).

### Iterasi 4.6 - Baseline pembanding logistik/GBDT (sebab #5: TabR di N kecil)
Tanggal    : 2026-10-06
Status     : selesai
Diubah     : scripts/run_loso_baseline.py (baru). Protokol LOSO identik
             run_loso.py (56 fold, 1 subjek/fold, split seed 72, praproses
             sama), model LogisticRegression(class_weight='balanced') dan
             GradientBoostingClassifier, metrik level subjek memakai helper
             yang sama dengan collect_loso_results.py, plus permutation test
             level subjek (acak label antar subjek). Keluaran ke
             output/training/<dataset>_baseline/ (tidak menyentuh exp/tabr/).
Dijalankan : 1) fitur roi25 (25 fitur, aggregate subject)
             2) fitur temporal (125 fitur, aggregate subject)
Hasil      : roi25  : logistic acc 0.4643 (p=0.8209), gbdt acc 0.5536
                      (p=0.3632) = tepat baseline mayoritas.
             temporal: logistic acc 0.4821 (p=0.7363), gbdt acc 0.5000
                      (p=0.7065).
             BACAAN: model sederhana pun tidak menemukan sinyal di level
             subjek, bahkan setelah fitur temporal ditambahkan. Ini
             memperkuat kesimpulan Iterasi 3.9/3.10 bahwa masalahnya ada di
             representasi POC-ABS (hulu), bukan di pilihan model.
             CATATAN: run temporal ini masih memakai tabel berbasis baseline
             onset, dan subject-norm otomatis mati karena aggregate=subject.
             Jadi ia menguji fitur temporal saja, bukan kombinasi lengkap
             (netral + temporal + subject-norm), yang butuh re-run 4.4.

### Iterasi 4.7 - Dokumen rujukan paper riset
Tanggal    : 2026-10-06
Status     : selesai
Diubah     : report/documentation/research-papers.md (baru, 37 entri) +
             report/findings/literature-accuracy-drop-2021-2026.md (analisis).
Dijalankan : -
Hasil      : Daftar sitasi 2021->sekarang dikelompokkan per tema, dengan
             tabel pemetaan sebab -> paper -> perbaikan. Entri pra-2021
             ditandai.

### Iterasi 4.8 - Wire ke runner pipeline
Tanggal    : 2026-10-06
Status     : selesai
Diubah     : scripts/run_pipeline.sh: stage 1 mengirim SPOT_SAVE_NEUTRAL;
             stage 2 baseline netral; stage 3 jadi 3a fitur temporal,
             3b LOSO TabR (--subject-norm subject), 3c collect,
             3d baseline pembanding. Dataset & keluaran baru bernama
             convat_apex_anxiety_loso_roi25_fixed supaya hasil lama utuh.
             run: perintah baru 'temporal' dan 'baseline'.
             scripts/build_feature_cache.py: argumen --xlsx/--pkl.
Dijalankan : bash -n scripts/run_pipeline.sh; bash -n run
Hasil      : Sintaks bash OK. Pipeline lengkap belum dijalankan (butuh
             dataset mentah + GPU).

### Iterasi 4.9 - Riset target 70% + temuan tabel fitur BASI
Tanggal    : 2026-10-06
Status     : selesai (riset); 1 temuan blocker belum diperbaiki
Diubah     : report/findings/research-strengthen-loso.md (baru) dan
             report/documentation/research-papers.md (+14 entri: 38-51).
             Plan ditambah Fase 2: issue 10 (tabel fitur basi),
             11 (uji berpasangan dalam-subjek), 12 (head pose + landmark).
Dijalankan : Analisis 168 report.json (train vs val), analisis tabel fitur vs
             metadata, analisis struktur label from metadata.
Hasil      : (a) OVERFITTING terukur: roi25 train 0.8285 vs val 0.5615
             (gap 0.2670); exp3 train 0.9024 vs val 0.7042 (gap 0.1982).
             (b) TARGET 70% belum didukung literatur untuk setup ini: pita
             LOSO kecemasan 47.97-72.73% (MDPI scoping review); label STAI
             sendiri AUC 0.81 / spesifisitas 0.57 (Cochrane); N minimum ML
             kesehatan mental 500-1000 (npj Digital Medicine 2024); Grimm
             GAD-7 dari wajah AUC 0.71. Angka 88-93% di literatur berasal
             dari stres TERINDUKSI dan/atau non-LOSO.
             (c) BLOCKER: tabel fitur basi (1 Sep) vs metadata/dataset
             (22 Sep). before: metadata 3.639 event / 56 subjek vs fitur
             1.493 event / 23 subjek; before/tidak 921 event / 15 subjek ->
             0 baris. Jadi "before selalu anxiety_tinggi" adalah artefak
             kehilangan data, BUKAN protokol. Analisis grup before_sama/
             before_berubah di summary.md TIDAK SAH. Headline LOSO tidak
             terpengaruh (hanya memakai after, yang lengkap).
             (d) Struktur label sebenarnya (metadata segar): 56 subjek semua
             punya before+after; label konsisten 38, BERUBAH 18
             (17 anxiety->tidak, 1 sebaliknya). Ini membuka uji berpasangan
             dalam-subjek tanpa confound identitas (issue 11).
             KOREKSI: uji awal saya pada 10 subjek "flip" memakai tabel basi
             dan TIDAK SAH (before di tabel itu selalu anxiety_tinggi);
             arahnya pun berlawanan dengan ekspektasi. Harus diulang.

### Iterasi 4.10 - Lever yang didukung riset (belum dikerjakan)
Tanggal    : 2026-10-06
Status     : direncanakan
Diubah     : -
Dijalankan : -
Hasil      : Urutan lever, dari dukungan literatur terkuat:
             A. Re-ekstraksi fitur dari metadata terbaru (blocker, gratis,
                dataset mentah ADA di mesin ini: output/apex/dataset 9,5 GB).
             B. Uji berpasangan dalam-subjek 18 subjek (gratis, gerbang
                keputusan: apakah keluarga fitur ini punya sinyal sama sekali).
             C. Head pose + geometri landmark (AnxietyFaceTrack: 3D landmark
                88-91%, head pose 85-89,66%; dlib 68 titik SUDAH dihitung tiap
                frame lalu dibuang -> hampir gratis).
             D. Dinamika temporal/variabilitas, bukan level statis
                (arXiv:2601.04376: AUROC 0.92 fusi facial+physio).
             E. Normalisasi baseline per orang (StressGAT: 88,62% LOSO,
                58 peserta, mekanisme Differential AU).
             F. rPPG heart rate (Sun 2022: 78,75% -> 82,50% dengan fusi);
                risiko rapuh terhadap gerakan.
             G. Tambah N (lever paling pasti, biaya paling besar).

### Iterasi 4.11 - Config anti-overfitting + dataset mentah DITEMUKAN
Tanggal    : 2026-10-06
Status     : selesai (config); temuan dataset
Diubah     : experiments/configs/tabr_loso_roi25_reg.toml (baru).
Dijalankan : lib.load_config() pada config baru; hitung n_parameters model
             lama vs baru.
Hasil      : (a) KOREKSI PENTING: Iterasi 4.9 menyebut dataset mentah
             "tidak ada di mesin ini". SALAH. Dataset ada di
             /run/media/finny/New Volume/dataset/ (drive "New Volume"):
               anxiety_raw/ : before/anxiety 41, before/tidak 15,
                              after/anxiety 25, after/tidak 31
               datatest/    : labeled/15_04_2026 + 17_04_2026,
                              annotations.xlsx, 610 video
             Jadi fix baseline netral (issue 04) BISA dijalankan di mesin ini.
             (b) DATASET KEDUA: datatest punya 49 subjek unik (98 sesi, semua
             subjek punya before+after, 11 subjek berubah label, skor 5-20),
             TIDAK ada irisan nama dengan anxiety_raw. Total potensi:
             56 + 49 = 105 subjek (dari 56 = 1,9x) tanpa mengumpulkan data
             baru. output/apex/datatest di repo sudah HILANG.
             (c) CONFIG BARU menutup overfitting struktural:
               param 487.681 -> 31.297 (turun 93,6%)
               batch 128 -> 8 (0,34 -> 5,5 step/epoch pada 44 baris train)
               context_size 12 -> 8 (konteks retrieval 27% -> 18% data train)
               weight_decay 1e-5 -> 1e-3; dropout0 0,1 -> 0,3;
               context_dropout 0,1 -> 0,3; d_main 192 -> 64.
             CATATAN JUJUR: ini mengecilkan gap train-val, TIDAK menaikkan
             test accuracy ke 70%. Baseline logistik/GBDT di matriks fitur
             yang sama juga di level acak, jadi masalah akurasi ada di
             representasi fitur, bukan hyperparameter.

### Iterasi 4.12 - Re-ekstraksi fitur (perbaikan tabel basi + baseline netral)
Tanggal    : 2026-10-06
Status     : SELESAI
Diubah     : scripts/save_neutral_references.py (baru): neutral.png per sample
             dari video mentah (median 10 frame awal), dipilih daripada
             spotting ulang karena klip + metadata sudah konsisten.
             scripts/extract_features_poc_abs.py: env FEAT_WORKERS untuk
             membatasi worker (kontrol suhu).
             scripts/run_pipeline.sh: stage 1b menjalankan
             save_neutral_references.py (satu mekanisme, idempotent).
             Arsip: experiments/features/apex/_stale_archive/ (metadata 22 Sep
             + tabel fitur basi + pkl basi) — tabel lama TIDAK ditimpa tanpa
             arsip.
Dijalankan : 1) save_neutral_references.py --raw-root "/run/media/finny/New
                Volume/dataset/anxiety_raw" -> 560/560 ok (30 detik)
             2) extract_features_poc_abs.py --baseline onset -> 22 menit,
                4 worker, suhu maks 82C, Errors: 1
             3) build_feature_cache.py -> pkl identik bit-per-bit
             4) extract_features_poc_abs.py --baseline neutral -> 37 menit,
                2 worker (4 worker menyentuh 95C), Errors: 0
             5) build_temporal_features.py untuk kedua tabel
Hasil      : TABEL BASI DIPERBAIKI (issue 10 SELESAI):
               total baris   65.206 -> 97.303 (onset) / 97.317 (neutral)
               before        20.782 -> 52.837
               before/tidak       0 -> 13.720 / 13.734
               subjek before     23 -> 56
               event before   1.493 -> 3.638 (metadata 3.639)
             Fitur temporal: 138 kolom (38 + 100), 6.877 / 6.878 event.
             TEMUAN: baseline netral MEMULIHKAN 1 klip yang gagal di baseline
             onset (frame onset-nya tidak terdeteksi wajah) -> Errors 1 -> 0.
             CATATAN: angka headline LOSO lama (55.36%) dihitung di atas
             44.424 baris `after`; tabel baru punya 44.466. Protokol tidak
             berubah (label unit person, only-after, LOSO), jadi perbandingan
             tetap apple-to-apple.

### Iterasi 4.13 - Gerbang: uji berpasangan dalam-subjek (issue 11)
Tanggal    : 2026-10-06
Status     : SELESAI
Diubah     : scripts/within_subject_test.py (baru).
Dijalankan : within_subject_test.py pada tabel onset dan neutral.
             18 subjek label berubah, 38 kontrol (label sama).
Hasil      : BASELINE ONSET: 20/25 fitur "signifikan" di grup berubah, TAPI
             kontrol juga 25/25 -> itu EFEK SESI, bukan kecemasan. Arahnya pun
             + (after > before), berlawanan dengan arah kecemasan.
             BASELINE NEUTRAL: 0/25 signifikan di KEDUA grup -> baseline
             netral berhasil menghapus artefak sesi, dan tidak menyisakan
             sinyal.
             Klasifikasi dalam-subjek LOSO (36 baris, 18 subjek):
               onset  : acc 0.5833, null 0.4921, p = 0.2637
               neutral: acc 0.5278, null 0.4981, p = 0.4726
             BACAAN: tidak ada sinyal kecemasan level-subjek yang bisa
             dipakai dari fitur POC-ABS. Grup kontrol yang membuktikan: tanpa
             kontrol, 20/25 "signifikan" itu akan salah dibaca sebagai bukti.
             KOREKSI: uji awal saya (Iterasi 4.9) memakai tabel basi dan TIDAK
             SAH; versi ini memakai tabel lengkap.

### Iterasi 4.14 - Diagnostik level subjek pada tabel yang sudah diperbaiki
Tanggal    : 2026-10-06
Status     : SELESAI (BUKAN training TabR - user jalankan sendiri)
Diubah     : -
Dijalankan : run_loso_baseline.py (logistik + GBDT, LOSO 56 fold, permutation
             200) pada 4 kombinasi tabel fitur.
Hasil      : fitur          | model    | acc    | 95% CI        | p
             onset 25       | logistic | 0.5000 | 0.37-0.63     | 0.6517
             onset 25       | gbdt     | 0.5000 | 0.37-0.63     | 0.6517
             onset 125      | logistic | 0.4464 | 0.32-0.58     | 0.8557
             onset 125      | gbdt     | 0.5893 | 0.46-0.71     | 0.1692
             neutral 125    | logistic | 0.5714 | 0.44-0.69     | 0.2189
             neutral 125    | gbdt     | 0.6071 | 0.48-0.72     | 0.0796
             (baseline mayoritas 0.5536)
             BACAAN: hasil TERBAIK sejauh ini = 0.6071 (neutral + temporal,
             GBDT), di atas baseline mayoritas, tapi p = 0.0796 -> BELUM
             signifikan di N=56. Baseline netral konsisten lebih baik dari
             onset pada fitur yang sama (gbdt 0.5893 -> 0.6071; logistic
             0.4464 -> 0.5714): arah perbaikan benar, efeknya kecil.
             70% TIDAK tercapai dan tidak realistis di representasi ini.

### Iterasi 4.15 - Run TabR dengan config anti-overfit (dijalankan USER)
Tanggal    : 2026-10-06 11:24
Status     : SELESAI
Diubah     : -
Dijalankan : User menjalankan scripts/run_loso.py dengan
             experiments/configs/tabr_loso_roi25_reg.toml pada fitur
             poc_abs_roi_signals_neutral_temporal.pkl (237 fitur),
             --aggregate subject, 56 fold x 3 seed.
Hasil      : Kelengkapan: 56 fold, 168 report.json, 0 FAILED.
             Config terverifikasi terpakai: batch_size 8, context_size 8,
             d_main 64, weight_decay 1e-3, param 44.865.
             OVERFITTING (train vs val):
               lama (roi25) : train 0.8285 | val 0.5615 | gap 0.2670
               reg          : train 0.9279 | val 0.7879 | gap 0.1400
             KOREKSI PENTING: "gap turun" itu train-vs-VAL, dan VAL DIPAKAI
             untuk memilih best_epoch -> val tidak netral. Ukuran jujur
             train vs TEST:
               lama : train 0.8285 vs test 0.5536 -> gap 27,49 poin
               reg  : train 0.9279 vs test 0.5952 -> gap 33,27 poin
             Jadi gap jujur MEMBESAR, bukan mengecil. Klaim "overfitting
             turun 48%" di Iterasi 4.11/4.14 TIDAK SAH dan dikoreksi di sini.
             Catatan: train cuma 44 baris dengan 44.865 parameter -> akurasi
             train 92,79% itu hafalan; di rezim ini akurasi train hampir tidak
             informatif sebagai indikator overfitting.
             TEST LEVEL SUBJEK (56 subjek):
               accuracy    0.5952 +- 0.0899  (CI 95% 0.4763-0.7242)
               sensitivity 0.4133 +- 0.0611  (CI 0.2025-0.5548)
               specificity 0.7419 +- 0.1406  (CI 0.6372-0.9081)
               PPV 0.5802 | NPV 0.6073 | baseline mayoritas 0.5536
               per seed: 0.6071 / 0.5000 / 0.6786
               confusion pooled: TN 69 / FP 24 / FN 44 / TP 31
             LEVEL FRAME (diagnostik): acc 0.5952, macroF1 0.5730,
             balanced acc 0.5776, recall 0.7419/0.4133.
             BACAAN:
             - +4,16 poin dari run lama (0.5536 -> 0.5952), TAPI CI memuat
               baseline 0.5536 -> BELUM terbukti lebih baik dari menebak
               mayoritas.
             - Bias BERBALIK, bukan hilang: sensitivitas 0.7067 -> 0.4133,
               spesifisitas 0.4301 -> 0.7419. Model kini condong "rendah";
               59% subjek cemas terlewat.
             - GBDT di fitur & protokol sama: 0.6071 (lebih baik dari TabR).
             - Grup before_berubah acc 0.8889 tapi sensitivitas 0.0000 (semua
               diprediksi rendah); before_sama 0.4737 (di bawah acak).
             - test_score per fold hanya 0 atau 1 (100x=1,0 ; 68x=0,0) ->
               NORMAL, karena test tiap fold = 1 subjek = 1 baris.
             70% tidak tercapai; konsisten dengan gerbang Iterasi 4.13.

### Iterasi 4.16 - Riset konfigurasi TabR untuk N kecil
Tanggal    : 2026-10-06
Status     : SELESAI (riset + config; training TIDAK dijalankan)
Diubah     : experiments/configs/tabr_loso_official_style.toml (baru)
             experiments/configs/tabr_loso_compact.toml (baru; semula bernama tabr_loso_tiny.toml)
             report/findings/research-tabr-config-small-data.md (baru)
             report/documentation/research-papers.md (+7 entri: 52-58)
Dijalankan : Cek config resmi di repo yang sama
             (exp/tabr/california/0-tuning.toml); hitung n_parameters model
             untuk 3 config x 2 set fitur.
Hasil      : (a) REZIM: 237 fitur / 44 baris train = d/n 5,39 -> termasuk
             "high-dimensional low-sample-size". Literatur (PLATO d>>n 2022;
             review reduksi dimensi 2021; GRACES 2023) menyatakan di rezim ini
             metode dominan adalah REDUKSI DIMENSI / seleksi fitur /
             regularisasi / ensemble model lemah - bukan menambah kapasitas DL.
             Satu-satunya set fitur kita di rezim sehat: ROI25 saja (d=25,
             d/n=0,57).
             (b) TEMUAN PENTING: config RESMI TabR memakai d_main 96-384 dan
             d_multiplier 2.0, di-tuning untuk California Housing (~20.640
             baris). Mengikutinya di N=44 menghasilkan 107.041 parameter
             (2.433 param/baris) - 2,4x LEBIH BESAR dari config reg yang
             dipakai (44.865). Jadi menyalin default resmi bukan best practice
             di sini; itu memperburuk overfitting.
             (c) Config baru: official_style (kontrol negatif; default resmi
             + num_policy=quantile + encoder_n_blocks=0) dan tiny (kapasitas
             minimal: d_main 32, d_multiplier 1.0, context_size 4,
             weight_decay 1e-2) -> 13.089 parameter (297 param/baris).
             (d) Lever terkuat yang tersisa = ENSEMBLING: masalah utama kita
             varians (seed 0.5000-0.6786, std 8,99%). Repo SUDAH punya
             bin/ensemble.py (ensemble_size=5) dan bin/go.py (n_seeds=15).
             Biaya 15 seed x 56 fold x ~5,5s = ~70 menit.
             PERINGATAN (paper bias-variance 2025): variance reduction hanya
             membantu kalau SNR mendukung; kalau SNR ~0, ensembling
             menstabilkan ke arah kelas mayoritas, bukan menaikkan akurasi.
             (e) TIDAK disarankan: embeddings PLR/PLE (config resmi TabR
             sendiri tidak memakainya; menambah parameter di 44 baris), dan
             menambah fitur lagi.
             (f) Eksperimen diusulkan E1-E5 (lihat plan Fase 4), termasuk E1
             sebagai KONTROL NEGATIF: kalau default resmi menang, hipotesis
             d>>n salah dan itu informasi penting.

### Iterasi 4.17 - Akuntansi bias pada hasil LOSO
Tanggal    : 2026-10-06
Status     : SELESAI (kode + dokumen; training TIDAK dijalankan)
Diubah     : scripts/collect_loso_results.py (MCC + balanced accuracy + bias
             prediksi + tabel per grup dengan baseline grup sendiri + ambang
             dari val)
             scripts/run_loso.py (simpan val_split.csv per fold)
             report/findings/analisis-bias-loso.md (baru)
             report/documentation/research-papers.md (+11 entri: 59-69)
Dijalankan : Hitung ulang dari artefak run 4.15 (168 report.json, test_split.csv,
             predictions.npz) + `./run collect` ke direktori scratch.
Hasil      : EMPAT BIAS TERUKUR:
             (1) KOMPOSISI / PARADOKS SIMPSON (dampak terbesar).
                 Pooled accuracy 0.6071 > baseline mayoritas global 0.5536,
                 TAPI di SETIAP grup fase model KALAH dari baseline mayoritas
                 grup itu sendiri:
                   before_sama    n=38 (24 positif) acc 0.4737 vs 0.6316 -> -0.1579
                   before_berubah n=18 ( 1 positif) acc 0.8889 vs 0.9444 -> -0.0556
                 Jadi keunggulan pooled adalah artefak komposisi kelas, bukan
                 kemampuan. Komposisi grup sangat berbeda: before_sama 63%
                 positif, before_berubah 5,6% positif.
                 PENTING: `group` diturunkan dari kolom `condition` yang
                 MERUPAKAN label -> grup hanya alat diagnosis, DILARANG dipakai
                 sebagai fitur atau untuk koreksi prior (kebocoran label).
             (2) METRIK. accuracy 0.5952 +- 0.0899 vs balanced accuracy
                 0.5776 +- 0.0847 vs MCC +0.1706 +- 0.1826.
                 MCC per seed: +0.1869 / -0.0196 / +0.3446 -> seed 1 setara
                 tebak acak, ditutupi oleh accuracy 0.5000 yang terlihat "cuma
                 5 poin di bawah baseline".
             (3) PREDIKSI. Laju positif diprediksi 0.2679 vs sebenarnya 0.4464
                 -> bias -0.1786 (konsisten negatif di ketiga seed:
                 -0.1786 / -0.0357 / -0.1429). Konsisten dengan sensitivity
                 0.4133 vs specificity 0.7419.
             (4) AMBANG & KALIBRASI. TabR memakai ambang tetap 0.5
                 (lib/metrics.py: np.round(probs)) - arbitrer. Proba terkompresi
                 tapi monoton: bin [0.0,0.2) rata-rata 0.080 -> laju nyata 0.424;
                 bin [0.8,1.01) rata-rata 0.922 -> laju nyata 0.667. Model
                 under-confident, proba tidak bisa dibaca sebagai peluang.
             (5) VARIANS SEED. Rentang accuracy antar seed 17,9 poin (0.5000
                 s/d 0.6786) walau cuma beda inisialisasi. Sebagian dari satu
                 subjek: di before_berubah (18 subjek, 1 positif) seed 2 menebak
                 positif pada proba 0.540005 (0,04 di atas ambang), seed 0/1
                 tidak. -> selisih antar-konfigurasi < ~10 poin tidak bisa
                 dibedakan dari derau di N=56.
             GAP YANG DITEMUKAN DAN DIPERBAIKI: run_loso.py menyimpan
             test_split.csv tapi TIDAK urutan baris val, sehingga ambang
             pilihan-val tidak bisa direkonstruksi dari artefak run lama
             (percobaan rekonstruksi lewat GroupShuffleSplit hanya cocok 6/56).
             Sekarang run_loso.py menulis + menyalin val_split.csv, dan
             collect_loso_results.py memilih ambang Youden di val tiap fold lalu
             menerapkannya ke test fold itu (leak-free). Untuk run lama bagian
             ini otomatis melaporkan "belum bisa dihitung".
             BACAAN: angka yang layak dikejar bukan "accuracy 70%", tapi
             MCC > 0 dengan CI tidak memuat 0 DAN tidak di bawah baseline grup
             di grup mana pun. Selama gerbang within-subject (Iterasi 4.13)
             masih setara efek sesi, konfigurasi/ambang hanya memindahkan bias.

### Iterasi 4.18 - Riset bebas bias & overfitting (internasional + nasional)
Tanggal    : 2026-10-06
Status     : SELESAI (riset + 1 config baru; training TIDAK dijalankan)
Diubah     : report/findings/strategi-bebas-bias-dan-overfitting.md (baru)
             experiments/configs/tabr_loso_roi25_reg_ce.toml (baru)
             report/documentation/research-papers.md (+31 entri: 70-100)
Dijalankan : Pencarian literatur 2021-2026 (internasional + nasional), lalu
             verifikasi config baru lewat lib.load_config + cek diff vs config reg.
Hasil      : FOKUS DIPINDAH dari "target 70%" ke "model tidak bias & tidak
             overfitting", dengan POC-ABS + ROI25 + TabR tetap dipakai.
             Dua masalah dipisah karena obatnya beda:
               overfitting: train 0.9279 vs test 0.5952 -> gap 33,3 poin
                            obat = kurangi kapasitas/dimensi, ensembling
               bias       : prediksi positif 0.2679 vs nyata 0.4464 (-0.1786)
                            obat = bobot kelas, ambang dari val, kalibrasi,
                                   fitur subject-invariant
             8 LEVER disusun urut dampak (L1-L8), semua tetap pakai POC-ABS+TabR:
               L1 fitur subject-invariant (Cheong 2021; Li&Deng 2022; Churamani
                  2022; Zeeshan 2023; DBMF 2025)
               L2 bobot kelas di loss TabR
               L3 ensembling antar seed (repo SUDAH punya bin/ensemble.py)
               L4 pemilihan epoch pakai cross-entropy, bukan accuracy
               L5 kembalikan dimensi ke d < n (ROI25 saja d/n 0,57)
               L6 kalibrasi Platt di val
               L7 ambang dari val (sudah diimplementasi di Iterasi 4.17)
               L8 AU-based / dinamika temporal
             TEMUAN KODE (dua hal yang selama ini tidak diketahui):
             (a) Loss biner TabR = F.binary_cross_entropy_with_logits TANPA
                 bobot (lib/deep.py:420 dipanggil tanpa kwargs di bin/tabr.py:373).
                 get_loss_fn SUDAH menerima **kwargs -> menambah pos_weight hanya
                 1-2 baris, bukan fitur baru. Ini lever L2.
             (b) Pemilihan epoch cross-entropy TIDAK butuh ubah kode sama sekali:
                 lib/data.py:20 sudah memuat 'cross-entropy': False (minimize) dan
                 lib/metrics.py:73 sudah menghitungnya. Cukup satu baris config.
             CONFIG BARU: tabr_loso_roi25_reg_ce.toml = salinan persis
             tabr_loso_roi25_reg.toml dengan HANYA score = "cross-entropy" diubah.
             Diverifikasi: config parse OK, score dikenali _SCORE_SHOULD_BE_MAXIMIZED
             (minimize), dan diff vs config reg = HANYA {'score'}.
             CATATAN: karena skor di-minimize, val_score yang dilaporkan jadi
             negatif. Itu benar, bukan error. Test score tetap tidak informatif
             (test tiap fold = 1 kelas).
             RUJUKAN NASIONAL (sebelumnya KOSONG di research-papers.md), 16 entri
             2021-2026, semuanya diverifikasi dari halaman penerbit. Yang paling
             relevan:
               - Apriyanthi 2026 (TEKNOSI): kecemasan + SMOTE + fitur temporal,
                 menyatakan pendekatan tanpa penanganan "rentan mengalami bias
                 akibat ketidakseimbangan kelas data" -> pembenaran lokal L2.
               - Chanafy & Sulistiani 2026 (SMATIKA): "metode validasi masih
                 menggunakan split tunggal, sehingga potensi bias evaluasi masih
                 ada" -> pembenaran lokal protokol LOSO + CI.
               - Bachtiar & Wafi 2021 (JTIIK): facial landmark + ELM/SVM/kNN,
                 JAFFE 213 citra, acc 0,76 -> preseden nasional terdekat
                 (fitur ROI + classifier tabular di N kecil).
               - Cahyo 2023 (JATI): micro-expression per komponen wajah (alis,
                 mata, mulut) dengan LBPH -> analog ROI25.
               - Alfin Ghozali & Bahtiar 2026 (TEKNOSI): SLR nasional data tidak
                 seimbang -> SMOTE + tuning + ensemble = L2, L4, L3.
               - Sunaryo 2026 (Rabit): CNN kecemasan FER2013 acc 92,58%, TAPI
                 penulis sendiri menyebut "keterbatasan dalam jumlah dan
                 distribusi data" -> pengakuan lokal masalahnya di data.
             PERINGATAN PEMAKAIAN: paper nasional hampir semua pakai dataset
             publik besar dengan SPLIT TUNGGAL dan melaporkan 76-92%. Angka itu
             TIDAK SEBANDING dengan angka kita (LOSO per subjek, N=56). Yang
             diambil adalah preseden metode + pengakuan keterbatasan.
             URUTAN KERJA DISARANKAN: (1) score=cross-entropy, (2) ambang dari
             val, (3) --subject-norm subject, (4) A/B representasi 25/138/237,
             (5) pos_weight, (6) ensembling 15 seed (~70 menit), (7) Platt,
             (8) pembersihan identitas. Langkah 1-3 hampir gratis dan WAJIB
             sebelum menyimpulkan apa pun.
             YANG TIDAK DISARANKAN: menyalin default resmi TabR (107.041 param),
             menambah fitur statis, SMOTE pada 44 baris subjek, memakai `group`
             sebagai fitur/koreksi prior, mengejar 70% lewat tuning, memakai val
             untuk mengevaluasi.

### Iterasi 4.19 - Audit N + knop POC-ABS/TabR (menjawab "haruskah N diubah?")
Tanggal    : 2026-10-06
Status     : SELESAI (audit + koreksi dokumen; training & re-ekstraksi TIDAK dijalankan)
Diubah     : report/findings/strategi-bebas-bias-dan-overfitting.md
             (+ bagian 2b: N & knop POC-ABS; koreksi L1 & L5; tabel larangan)
Dijalankan : Audit langsung ke dataset mentah, anotasi datatest, artefak run,
             env var spotting, dan argumen run_loso.py.
Hasil      : JAWABAN: N TIDAK BISA diubah lewat konfigurasi. Rinciannya:
             (1) KOREKSI ANGKA datatest. Catatan lama "49 subjek" SALAH.
                 annotations.xlsx = 51 baris / 26 subjek unik, dan hanya 25
                 subjek punya before+after LENGKAP. Dari 98 direktori sesi di
                 labeled/, 48 TIDAK punya anotasi. Jadi tambahan realistis ~25
                 subjek, bukan 49.
                 Label datatest berasal dari kolom `score` numerik 5-17 dengan
                 potongan sempurna di 10.5 (score>=11 -> anxiety_tinggi, cocok
                 51/51). Label anxiety_raw dari NAMA FOLDER tanpa skor. Instrumen
                 tidak bisa dipastikan sama -> label shift. Keputusan lama
                 (tidak menggabung) TERBUKTI benar.
             (2) TEMUAN BARU: setiap sesi punya DUA kamera, *_main.webm (vp8 30fps)
                 dan *_sec.avi (mjpeg 60fps). Pipeline HANYA memakai _sec.avi
                 (dicek: semua 6.878 clip_path berakhiran _sec). Sudah diambil
                 frame dari keduanya untuk konfirmasi: subjek & momen SAMA, beda
                 sudut/framing. Jadi view kedua = augmentasi, BUKAN tambahan N.
             (3) N efektif tetap 56 subjek. Frame/clip (~97.000 baris) juga tidak
                 menambah N karena label milik subjek.
             (4) KOREKSI RENCANA SENDIRI: --subject-norm subject TIDAK BISA
                 dijalankan bersama --aggregate subject. Setelah agregasi tiap
                 subjek = 1 baris, std subjek = 0 -> semua fitur jadi 0. Guard
                 sudah ada di run_loso.py. Jadi lever L1 bukan A/B murah,
                 melainkan pindah protokol. L1 & L5 dikoreksi.
             (5) ANGKA d/n PRESISI (dihitung dari feature_cols.json run reg):
                 --aggregate subject menggandakan tiap fitur jadi mean+std.
                   125 fitur dasar -> 237 (d/n 5,39)  <- run reg
                   125 + --drop-features "_std$" -> 117 (d/n 2,66)
                   125 + drop _std/_ttp_/_rise_/_fall_/_auc_ -> 40 (d/n 0,91)
                   neutral_full (ROI25 murni) 25 -> ~50 (d/n 1,14)
                 Jadi reduksi dimensi BISA dilakukan tanpa re-ekstraksi, murni
                 lewat flag CLI. Ini A/B termurah kedua setelah score.
             (6) KNOP POC-ABS didata (env var di process_spotting_pipeline.py):
                 SPOT_ABS (wajib 1), SPOT_SIGNAL_MODE, SPOT_THRESH (meanstd),
                 SPOT_DISTANCE (1=non-aktif), SPOT_PROM_REL (0.04), SPOT_INTERP,
                 SPOT_SAVE_NEUTRAL, SPOT_NEUTRAL_FRAMES; plus SpottingConfig
                 (block_size 7, padding, min_phase_duration 2, top_k_apex 5,
                 distance_threshold, prominence_threshold, cutoff_ratio, regions).
                 SEMUA butuh re-ekstraksi jam-an.
             URUTAN DIKOREKSI: (1) score=cross-entropy, (2) A/B representasi
             237/117/~50 [tanpa re-ekstraksi], (3) ambang dari val, (4) pos_weight,
             (5) ensembling 15 seed, (6) Platt, (7) subject-norm/pembersihan
             identitas [pindah protokol], (8) knop POC-ABS [re-ekstraksi] -
             sengaja terakhir karena hanya mengubah event mana yang jadi fitur.

### Iterasi 4.20 - Audit + perbaikan kode ekstraksi fitur, re-ekstraksi v2
Tanggal    : 2026-10-06
Status     : SELESAI (ekstraksi v2 + gerbang; training TabR TIDAK dijalankan)
Diubah     : scripts/extract_features_poc_abs.py (3 perbaikan + flag --limit)
             scripts/build_temporal_features.py (regex sinyal dasar diperluas)
             report/findings/perbaikan-ekstraksi-v2.md (baru)
Dijalankan : Audit kode + verifikasi angka dari tabel fitur lama, lalu re-ekstraksi
             dengan FEAT_WORKERS=3 ke berkas v2 (tabel lama tidak ditimpa).
Hasil      : TIGA CACAT NYATA DITEMUKAN DAN DIPERBAIKI.
             (1) TANDA ARAH DIBUANG (paling penting).
                 Quadran menghitung [block_id, X, Y, theta, magnitude, quadrant]
                 dengan X/Y BERTANDA, tapi extract_roi_signal_row hanya menyimpan
                 mean(|X|) dan mean(|Y|). Akibatnya theta dan quadranLabel
                 terbuang TOTAL, dan mulut naik vs turun jadi fitur identik.
                 Perbaikan: tambah `*_mean_x` dan `*_mean_y` (bertanda).
                 Sahih karena acuan POC-ABS = wajah NETRAL, jadi arah konsisten
                 sepanjang event (kalau acuan onset, mean(X) akan saling hapus).
                 VERIFIKASI: kolom fitur 25 -> 35; mean_x punya dua tanda
                 (44,3% negatif / 32,9% positif); korelasi |mean_x| vs mean_abs_x
                 hanya 0,587 -> TIDAK redundan, membawa informasi baru.
             (2) FRAME ONSET HILANG DI SEMUA EVENT.
                 `if idx == 0: ... continue` membuang frame 0 di KEDUA mode
                 baseline. Benar kalau acuan = frame 0 sendiri (POC(frame0,frame0)=0),
                 SALAH kalau acuan neutral.png: frame onset adalah baris data sah.
                 BUKTI: kolom `frame` tabel lama min = 2, baris frame==1 = 0
                 -> 6.878 baris (7,1%) hilang, justru frame tempat ekspresi mulai
                 (yang dibutuhkan deskriptor temporal `_rise`).
                 Perbaikan: buang frame 0 hanya kalau acuannya frame 0 sendiri.
                 VERIFIKASI: tabel v2 kolom `frame` min = 1.
             (3) SINYAL APEX DIPALSUKAN.
                 roi_signals di-seed `[0.0]` -- 0.0 itu bukan frame apa pun, jadi
                 detect_roi_apex melihat lembah palsu di indeks 0 dan SEMUA nomor
                 frame apex bergeser satu (indeks list dipakai memetakan frame via
                 onset_frame + index). Perbaikan: seed list kosong.
                 Dampak terbatas: roi_apex.xlsx tidak dipakai hilir.
             (4) SATURASI POC - DICATAT, SENGAJA BELUM DIPERBAIKI.
                 block_size 7 -> perpindahan maksimum hanya +-3 px, magnitude
                 mentok 3*sqrt(2)=4.243. Terukur: mulut 14,92% baris MENTOK dan
                 59,8% baris > 3,0; alis ~9-10%; mata ~5%. Artinya gerakan
                 TERKUAT justru paling banyak terpotong.
                 Perbaikan butuh ubah block_size di ekstraksi DAN spotting.py
                 (kalau tidak, event timing vs fitur makin tidak sinkron)
                 = re-spotting penuh, bukan re-ekstraksi. Ditunda ke urutan
                 biaya->manfaat. Dicatat sebagai cacat #4 di dokumen.
             TEMUAN TAMBAHAN: build_temporal_features.py memakai WHITELIST regex
             (mean_m|mean_abs_x|mean_abs_y|motion_count), jadi fitur baru mean_x/
             mean_y akan DIAM-DIAM DIBUANG. Regex diperluas; sudah diuji parse
             (kolom lama tetap benar, max_m dan kolom temporal tetap dikecualikan).
             Tabel lama TIDAK ditimpa: keluaran v2
             (poc_abs_roi_signals_neutral_v2{,_full.pkl,_temporal.pkl}).
             Wasit perbaikan ini: MCC di protokol LOSO yang sama, dibanding run reg
             (MCC +0.1706), bukan accuracy.
             HASIL RE-EKSTRAKSI v2 (FEAT_WORKERS=3, 28m19s, 0 error):
               baris      97.317 -> 104.194  (+6.877, +7,1%)
               fitur statis     25 -> 35     (+10 bertanda)
               fitur temporal  125 -> 185    (+60)
               frame minimum      2 -> 1
               fitur hilang: TIDAK ADA
               pkl bit-identik dgn xlsx: ya (48 kolom, 104.194 baris)
             GERBANG WITHIN-SUBJECT pada v2 (wasit utama perubahan ini):
               onset lama    (25 fitur) acc 0.5833  null 0.4921  p 0.2637
               neutral lama  (25 fitur) acc 0.5278  null 0.4981  p 0.4726
               v2 statis     (35 fitur) acc 0.4167  null 0.4969  p 0.7910
               v2 temporal  (185 fitur) acc 0.6667  null 0.4940  p 0.0746
               Kontrol BERSIH di semua set (0/35 dan 0/185 signifikan) --
               jadi tidak ada efek sesi yang terbawa, tidak seperti onset lama
               (20/25 "berubah" vs 25/25 kontrol).
             BACAAN JUJUR:
             - Set TEMPORAL bergerak: 0.5278 (p=0,47) -> 0.6667 (p=0,075).
               Ini hasil gerbang TERBAIK sejauh ini dan arahnya benar.
             - TAPI p=0,075 BELUM signifikan di ambang 5% -> belum bukti.
             - Set statis v2 justru turun (0.4167, p=0,79). Dengan n=36 baris
               selisih 0,42 vs 0,67 ada DI DALAM DERAU; 10 fitur baru di antara
               185 tidak menjelaskan selisih sebesar itu. Jangan disimpulkan
               fitur bertanda merugikan.
             - Jadi: gerbang berpindah dari jelas-null ke MARGINAL, belum
               signifikan. Yang memutuskan tetap A/B LOSO penuh.

### Iterasi 4.21 - v3 (re-spotting) + PERBAIKAN BUG cross-entropy
Tanggal    : 2026-10-06
Status     : SELESAI (kode + re-spotting/re-ekstraksi + gerbang; training BELUM)
Diubah     : features_extraction/roi_config.py (baru: sumber kebenaran ROI/block_size)
             features_extraction/vektor.py (typo len(temp_y) x2 -> temp_x/temp_y)
             comparasion/core/config.py, scripts/spotting.py,
             scripts/extract_features_poc_abs.py, scripts/extract_features_roi.py
             (semua import definisi kanonik, tidak lagi menyalin)
             scripts/extract_features_poc_abs.py (+FEAT_DATASET_ROOT/FEAT_METADATA_PATH)
             scripts/run_loso.py (help --drop-features: block_size 9, bukan 7)
             third_party/.../lib/metrics.py (BUG: cross-entropy tidak selalu ada)
             scripts/run_pipeline_v3.sh (baru: satu perintah 7 stage)
             report/findings/perbaikan-pipeline-v3.md (baru)
Dijalankan : Re-spotting 560 video (block_size 9) + re-ekstraksi + cache + temporal
             + gerbang within-subject, lalu training LOSO (GAGAL, lihat bawah).
Hasil      : BAGIAN A - PERBAIKAN v3 (stages 1-5 SELESAI)
             Akar masalah: definisi ROI/target_size/block_size disalin di LIMA
             tempat dan sudah menyimpang - spotting memakai mata = kelopak saja
             (36-41/42-47), ekstraksi memakai mata = alis+kelopak (17-21+36-41).
             Akibat: alis_kiri HIMPUNAN BAGIAN dari mata_kiri -> dua fitur
             mengukur wilayah sama, dan sinyal spotting != ROI fitur.
             Perbaikan: features_extraction/roi_config.py jadi satu-satunya
             sumber kebenaran; keempat konsumen meng-import dari situ
             (diverifikasi keempatnya identik; irisan alis & mata = KOSONG).
             block_size 7 -> 9: diukur per BLOK pada 18 clip x 8 frame:
                bs=7: mulut 4,62% blok mentok | bs=9: 1,37% | bs=11: 1,21%
                bs=13: 0,85% TAPI alis tinggal 1 baris blok (degenerate) -> tolak
             KOREKSI klaim sendiri: dokumen v2 menyebut "mulut 14,92% baris
             mentok" - itu dari kolom `max_m` yang JUSTRU DIBUANG dari fitur.
             Angka relevan = fraksi BLOK (4,62%). Saturasi nyata tapi tidak
             separah itu. Sudah dikoreksi di perbaikan-ekstraksi-v2.md.
             Typo vektor.py: `if len(temp_y)>1 or len(temp_y)>1` -> `temp_x`.
             Hasil stages 1-5: metadata 6.972 event (dari 6.878, +1,4% karena
             block_size), 560/560 neutral.png, fitur 100.817 baris x 35 statis /
             185 temporal, frame min 1, 0 error.
             GERBANG within-subject v3:
               v3 statis   (35)  acc 0,4444  null 0,4942  p 0,7761
               v3 temporal (185) acc 0,6111  null 0,5004  p 0,1990
             Kontrol bersih (0/35, 0/185; 1/185 di temporal = wajar FDR 5%).
             BACAAN JUJUR: v3 TIDAK memperbaiki gerbang. v3 temporal 0,6111
             (p=0,199) lebih RENDAH dari v2 temporal 0,6667 (p=0,075), tapi
             dengan n=36 selisih itu di dalam derau -> jangan diklaim v3
             merugikan, dan JANGAN diklaim v3 membaik. Tidak ada set fitur yang
             mencapai p<0,05. Perbaikan v3 sahih secara rekayasa, tapi tidak
             diterjemahkan jadi sinyal terukur.
             BAGIAN B - BUG YANG SAYA PERKENALKAN (training 56/56 fold GAGAL)
             tabr_loso_roi25_reg_ce.toml (score=cross-entropy) -> KeyError
             ('cross-entropy') di SEMUA 56 fold; 0 DONE.json, 56 FAILED.txt.
             AKAR MASALAH: lib/data.py:243-245 membaca part_metrics[self.score]
             untuk SETIAP part, tapi patch penghapusan AUC di lib/metrics.py
             menambahkan guard `len(np.unique(y_true)) > 1` pada baris
             cross-entropy. Di LOSO, test = 1 subjek = 1 kelas -> key tidak
             pernah ditulis -> KeyError.
             PERBAIKAN: buang guard, pakai `labels` eksplisit supaya log_loss
             terdefinisi walau y_true satu kelas:
               ce_labels = [0,1] binclass else list(range(probs.shape[1]))
               result['cross-entropy'] = log_loss(y_true, probs, labels=ce_labels)
             Diverifikasi langsung (bukan training): part 1 kelas -> CE=0,2014
             dan score=-0,2014 OK; part 2 kelas -> CE=0,584298 OK.
             KESALAHAN SAYA: sebelumnya saya "memverifikasi" config CE hanya
             dengan lib.load_config + cek _SCORE_SHOULD_BE_MAXIMIZED, TIDAK
             memverifikasi bahwa metriknya ada untuk SETIAP part. Config
             dinyatakan "terverifikasi" padahal belum.
             PERBAIKAN TAMBAHAN: run_pipeline_v3.sh sekarang menghitung DONE.json
             setelah stage 6 dan GAGAL LOUD kalau 0 fold selesai. Sebelumnya
             run_loso.py menelan error per fold dan keluar kode 0, sehingga
             pipeline mencetak "STAGE 6 SELESAI" padahal 56/56 fold gagal.
             CATATAN: karena skor di-minimize, val_score yang dilaporkan NEGATIF.
             Itu benar, bukan error.
             Training BELUM dijalankan ulang. Perintah: ./scripts/run_pipeline_v3.sh --from 6

### Iterasi 4.22 - Bug collector (val threshold) + hasil training v3 = REGRESI
Tanggal    : 2026-10-06
Status     : SELESAI (bug diperbaiki; hasil training v3 terukur dan negatif)
Diubah     : scripts/collect_loso_results.py (BUG val_threshold_metrics)
             experiments/configs/tabr_loso_roi25_reg_ce.toml (ditandai HASIL NEGATIF)
             report/findings/perbaikan-pipeline-v3.md (+ bagian 6.4)
Dijalankan : Training LOSO v3 (56 fold x 3 seed) - SELESAI 0 gagal, 168 report.json.
             Lalu collect (gagal karena bug saya), diperbaiki, lalu collect ulang.
Hasil      : BAGIAN A - BUG COLLECTOR YANG SAYA PERKENALKAN
             val_threshold_metrics() error "zero-dimensional arrays cannot be
             concatenated". Sebab: `probs` (56 array bentuk (1,)) saya
             np.concatenate DULU jadi array 1-D, baru di-zip dengan thresholds.
             Iterasi array 1-D menghasilkan skalar 0-d, dan np.concatenate
             menolak skalar 0-d.
             Perbaikan: ambang diterapkan PER FOLD sebelum digabung
             (fold_preds.append((p >= best).astype(int))), plus np.atleast_1d.
             Diverifikasi: 56 fold dimuat, val ada di 56/56 fold,
             val_threshold_metrics() mengembalikan nilai wajar
             (n_folds=56, threshold_mean=0,3994, accuracy=0,5000, bal_acc=0,5058).
             Lalu collect penuh dijalankan: exit 0, summary.md + csv tertulis.
             BAGIAN B - HASIL TRAINING v3 = REGRESI (yang penting)
             reg (237 fitur, akurasi)  -> acc 0,5952 | MCC +0,1706 | balAcc 0,5776
             v3  (370 fitur, CE)       -> acc 0,5238 | MCC +0,0154 | balAcc 0,5054
             MCC pooled v3 = -0,2195. CI 95% accuracy v3 0,2917-0,5412 SELURUHNYA
             DI BAWAH baseline mayoritas 0,5536 -> LEBIH BURUK dari tebak mayoritas.
             Per grup keduanya negatif: before_sama -0,3158, before_berubah -0,3333.
             Varians antar seed tidak berubah (17,9 poin di kedua run).
             DUA VARIABEL BERUBAH SEKALIGUS (fitur 237->370 DAN kriteria epoch
             accuracy->CE), jadi regresi tidak bisa diatribusikan ke salah satu.
             TAPI penyebab utamanya teridentifikasi: PEMILIHAN EPOCH CE.
             best_epoch per fold:
               reg (akurasi): median 5, mean 12,2
               v3 seed 0: median 3, mean 4,7, 13/56 fold berhenti di epoch <= 1
               v3 seed 1: median 1, mean 1,8, 40/56 fold berhenti di epoch <= 1
               v3 seed 2: median 0, mean 0,8, 48/56 fold berhenti di epoch <= 1
             Jadi di 40-48 dari 56 fold model berhenti SEBELUM sempat belajar.
             Mekanisme: val CE paling rendah di AWAL lalu NAIK begitu model mulai
             menghafal 44 baris train -> "minimize val CE" memilih model nyaris
             belum terlatih. CE proper scoring rule secara teori, tapi sebagai
             KRITERIA EARLY STOPPING terlalu agresif di N=44.
             BIAS PREDIKSI: pada ambang 0,5 bias tetap -0,1190 (CE TIDAK
             memperbaiki bias). Yang memperbaiki adalah AMBANG DARI VAL:
             laju positif 0,4702 vs nyata 0,4464 -> bias +0,0238 (dari -0,1190).
             Jadi ambang-dari-val terbukti berguna; CE tidak.
             KESALAHAN SAYA: saya merekomendasikan config CE sebagai "lever L4"
             dan menyebutnya terverifikasi, padahal (a) metriknya belum saya uji
             untuk semua part (menyebabkan 56/56 fold gagal), dan (b) efek
             praktisnya sebagai early-stopping tidak saya uji sama sekali.
             LANGKAH BERIKUTNYA: fitur v3 + config AKURASI (nama dataset baru
             supaya fold v3 tidak dipakai ulang) untuk memisahkan efek fitur
             dari efek CE.

### Iterasi 4.23 - KOREKSI: bug "pooled" di collector + hasil v3_acc
Tanggal    : 2026-10-06
Status     : SELESAI (bug diperbaiki, 3 run dikumpulkan ulang; training TIDAK dijalankan)
Diubah     : scripts/collect_loso_results.py (BUG: pooled = seed 0)
             report/findings/perbaikan-pipeline-v3.md (bagian 6.4/6.5/6.6 ditulis ulang)
Dijalankan : User menjalankan convat_apex_anxiety_loso_v3_acc (fitur v3 + config
             AKURASI = isolasi bersih vs reg). Lalu collect ulang untuk reg/v3/v3_acc.
Hasil      : BAGIAN A - BUG "POOLED" DI COLLECTOR (pre-existing, saya mewarisinya
             dan MEMAKAI angkanya, jadi saya yang salah melaporkan).
             Kode lama:
               pooled['proba'] = pooled.groupby('subject')['proba'].transform('mean')
               pooled = pooled.drop_duplicates('subject')
               pooled_m = subject_metrics(pooled)
             `pred` TIDAK dihitung ulang, dan subject_metrics() membaca kolom
             `pred` lama; drop_duplicates() menyisakan baris SEED 0. Jadi yang
             dilaporkan "Pooling antar seed" sebenarnya HANYA SEED 0, dan kolom
             "95% CI (pooled antar seed)" juga CI seed 0.
             BUKTI: v3 seed0 acc 0,4107 == angka "Pooling antar seed" summary.md lama.
             PERBAIKAN: pooled['pred'] = (pooled['proba'] >= 0.5).astype(int)
             + label diubah jadi "seed-ensemble" (proba dirata-rata antar seed,
             lalu di-threshold). Ketiga run dikumpulkan ulang.
             BAGIAN B - KLAIM SAYA DI ITERASI 4.22 YANG DICABUT
             (1) "CI v3 0,2917-0,5412 seluruhnya di bawah baseline 0,5536 ->
                 lebih buruk dari mayoritas" -> DICABUT. Itu CI seed 0.
                 CI seed-ensemble yang benar: 0,4763-0,7242, MEMUAT baseline.
             (2) "cross-entropy yang merusak training" -> DICABUT.
                 v3acc (config AKURASI) juga berhenti dini: 97/168 fold di
                 epoch <=1, hampir sama dgn v3 CE (101/168). reg hanya 34/168.
                 Jadi penyebabnya FITUR, bukan kriteria epoch.
             BAGIAN C - ANGKA YANG BENAR (seed-ensemble)
             run    fitur      config         acc     CI95            MCC
             reg    v2 237     akurasi        0,6250  0,4941-0,7399   +0,2272
             v3     v3 370     cross-entropy  0,6071  0,4763-0,7242   +0,1910
             v3acc  v3 370     akurasi        0,5357  0,4070-0,6598   +0,0464
             baseline mayoritas 0,5536
             KETIGA CI MEMUAT BASELINE -> tidak ada run yang terbukti lebih baik
             dari menebak kelas mayoritas, TERMASUK reg.
             Rata-rata antar seed: reg 0,5952/+0,1706 | v3 0,5238/+0,0154 |
             v3acc 0,5179/+0,0054. Per-seed MCC tumpang tindih berat -> selisih
             antar run tidak bisa dibedakan dari derau.
             BAGIAN D - PENYEBAB SEBENARNYA: JUMLAH FITUR
             best_epoch: reg median 5 (mean 12,2) | v3 CE median 1 (mean 2,4)
             | v3acc median 1 (mean 3,9). Fold berhenti di epoch <=1:
             reg 34/168, v3 101/168, v3acc 97/168.
             370 kolom untuk 44 baris train (d/n 8,4) vs 237 (d/n 5,4): dengan
             fitur lebih banyak, akurasi val memuncak di epoch 0-1 lalu turun,
             sehingga early stopping memilih model yang belum belajar. Ini
             masalah rezim high-dimensional low-sample-size yang sudah
             didokumentasikan di research-tabr-config-small-data.md.
             Konsekuensi: menambah fitur (v3) MEMPERBURUK masalah dimensi, dan
             dampaknya lebih besar dari perbaikan ekstraksi apa pun.
             BAGIAN E - YANG TERBUKTI BERGUNA
             HANYA ambang-dari-val: bias prediksi -0,1190 -> +0,0238.
             Yang TIDAK terukur manfaatnya: fitur arah bertanda, frame onset
             kembali, fix apex, block_size 9, ROI tidak tumpang tindih, CE.
             Yang MERUGIKAN: menambah fitur jadi 370.
             Semua perbaikan v3 sahih secara rekayasa dan ketiga bug yang
             ditemukan memang bug nyata, TAPI tidak satu pun menghasilkan sinyal
             yang bisa diukur. Gerbang within-subject tetap tidak signifikan.
             LANGKAH BERIKUTNYA: A/B REDUKSI DIMENSI (bukan menambah apa pun).
             Tabel fitur sudah ada, tanpa re-ekstraksi. Perintah ada di
             perbaikan-pipeline-v3.md bagian 6.6.

### Iterasi 4.24 - BUG --drop-features + hasil reduksi dimensi (d1/d2 INVALID)
Tanggal    : 2026-10-06
Status     : SELESAI (bug diperbaiki; d1/d2 harus diulang)
Diubah     : scripts/run_loso.py (BUG: --drop-features dijalankan di tahap salah;
             + apply_feature_drop() diekstrak jadi fungsi; + gagal keras kalau
             regex tidak cocok kolom mana pun)
Dijalankan : User menjalankan 3 run reduksi dimensi (v3_d1/v3_d2/v3_d3), lalu
             collect. Hasil diperiksa dan ditemukan d1/d2 TIDAK valid.
Hasil      : BAGIAN A - BUG --drop-features (akar: urutan tahap)
             Regex dijalankan SEBELUM agregasi, padahal sufiks `_mean`/`_std`
             baru ada SESUDAH agregasi. Jadi:
               - `--drop-features "_std$"` mencocokkan 0 kolom -> DIAM-DIAM tidak
                 melakukan apa pun (tanpa error, tanpa peringatan).
               - Karena flag ini MENGGANTIKAN default `_max_m$`, fitur tersensor
                 `*_max_m` justru IKUT KEMBALI.
             BUKTI: v3_d1 dan v3_d2 sama-sama 369 fitur (184 mean + 185 std) dan
             hasilnya identik bit-per-bit (acc 0,4286, MCC -0,1762) - mustahil
             kalau reduksi benar-benar terjadi. Log hanya memuat baris default
             `drop fitur /_max_m$/`, tidak pernah ada baris `_std$`.
             Verifikasi aritmetika: v3_temporal 185 fitur; default membuang 5
             max_m -> 180 -> agregasi -> 360 -> variance-threshold -> 359 (= v3_acc).
             Kalau `_std$` menggantikan default: 185 -> agregasi -> 370 -> 369
             (= v3_d1/d2). Cocok persis.
             PERBAIKAN: apply_feature_drop() dipanggil DUA KALI (pra dan pasca
             agregasi) sehingga `_max_m$` dan `_std$` dua-duanya bekerja; plus
             SystemExit kalau regex tidak cocok kolom mana pun (supaya tidak
             gagal diam-diam lagi).
             Diverifikasi: v3 temporal -> _max_m$ 360, _std$|_max_m$ 180 (d/n 4,09),
             _std$|_ttp_|_rise_|_fall_|_auc_|_max_m$ 60 (d/n 1,36);
             v3 statis -> _std$|_max_m$ 30 (d/n 0,68).
             CATATAN PEMAKAIAN: karena --drop-features menggantikan default,
             pola yang dipakai sekarang harus MENYERTAKAN `_max_m$`.
             BAGIAN B - HASIL YANG VALID (seed-ensemble, proba dirata-rata antar seed)
             run    fitur  config         acc     CI95            MCC      balAcc
             reg    237    akurasi        62,50%  49,41-73,99%    +0,2272  60,32%
             v3     359    cross-entropy  60,71%  47,63-72,42%    +0,1910  59,10%
             v3acc  359    akurasi        53,57%  40,70-65,98%    +0,0464  52,26%
             d3     60     akurasi        42,86%  30,77-55,86%    -0,1561  42,19%
             baseline mayoritas            55,36%
             d1/d2 (369 fitur) = INVALID, lihat Bagian A.
             KETIGA CI YANG VALID MEMUAT baseline 55,36% -> tidak ada satu pun
             yang terbukti lebih baik dari menebak kelas mayoritas, termasuk reg.
             TEMUAN PENTING: d3 (60 fitur, ROI25 murni) justru TERBURUK (42,86%).
             Jadi HIPOTESIS "kurangi dimensi akan memperbaiki" TIDAK TERBUKTI -
             arahnya malah sebaliknya. Catatan: d3 juga mengubah KELUARGA fitur
             (statis saja, tanpa temporal), jadi bukan isolasi dimensi murni.
             UJI DIMENSI YANG BERSIH BELUM PERNAH JALAN (d1/d2 invalid).
             best_epoch: reg median 5 (mean 12,2) | v3 1 (2,4) | v3acc 1 (3,9)
             | d1 1 (4,6) | d2 1 (4,6) | d3 median 7 (mean 11,7).
             Menarik: d3 (paling sedikit fitur) justru punya best_epoch paling
             tinggi - konsisten dengan "fitur lebih banyak -> early stopping
             lebih dini".





### Iterasi 4.25 - Keluarga fitur KEDUA: geometri wajah + head pose
Tanggal    : 2026-10-06
Status     : SELESAI (kode + verifikasi statis + validasi terbatas). Pipeline
             penuh BELUM dijalankan (user jalankan sendiri).
Diubah     : features_extraction/geometry.py (BARU; 21 fitur geo_*)
             comparasion/core/roi.py (+extract_landmarks,
             +extract_rois_from_landmarks; extract_rois jadi pembungkus tipis)
             scripts/extract_features_poc_abs.py (+--with-geometry, 3 tabel)
             scripts/run_loso.py (+--quiet)
             scripts/run_pipeline_v3.sh (stage 2/3/4/5/6/7 + config default +
             nama dataset LOSO)
             report/findings/geometri-headpose.md (BARU; dasar riset)
Dijalankan : Verifikasi statis (parse AST, bash -n, --help, --dry-run),
             validasi setara-ROI pada 6 frame nyata, validasi geometri pada 400
             frame nyata, ekstraksi terbatas (--limit 5), dan training 1 fold/1
             seed untuk menguji --quiet.
Hasil      : LATAR - gerbang within-subject sudah menyatakan POC-ABS tidak
             membawa sinyal kecemasan (baseline netral 0/25 fitur signifikan,
             LOSO dalam-subjek 0,528, p=0,473). Tuning TabR tidak bisa
             memperbaiki representasi yang tidak berisi sinyal, jadi yang
             ditambah adalah KELUARGA FITUR, bukan hyperparameter.
             Dasar riset (report/findings/geometri-headpose.md):
               - AnxietyFaceTrack (IEEE TAFFC 2026, N=91): 3D landmark 88-91%,
                 head pose 85-89,7%, AU 59-73%, gaze 53%. Kontributor utama
                 rotasi kepala sumbu-x, landmark tepi wajah, landmark mata.
               - StressGAT (arXiv:2607.20819, 58 peserta, LOSO 88,62%):
                 mekanisme Differential Action Units = fitur dinormalkan
                 terhadap baseline netral tiap orang.
               - Giannakakis 2017/2018: kecepatan kepala naik saat stres.
               - Rumahorbo dkk (BINUS, CMBN 2025): geometri mata/bibir.
             ISI - 21 fitur per frame dari 68 landmark yang SUDAH dihitung
             spotting (tidak perlu re-spotting, tidak perlu data baru):
               15 statis: EAR (bukaan kelopak), MAR/bukaan/lebar mulut, sudut
                 bibir turun, jarak alis-mata kiri/kanan, jarak alis dalam,
                 lebar rahang, pitch/yaw/roll, kemiringan garis mata.
                 Semua diskala jarak inter-okular lalu DIKURANGI wajah netral
                 subjek (neutral.png).
               6 kecepatan: d_ear, d_mar, d_pitch, d_yaw, d_roll, head_motion.
             KENAPA INI MEMBANTU KEDUANYA: POC-ABS mendapat sinyal yang selama
             ini tidak ada; TabR berhenti me-retrieve tetangga berdasarkan
             IDENTITAS karena fitur sudah dinormalkan terhadap netral orang.
             KEPUTUSAN TEKNIS PENTING (bug yang ditemukan dan diperbaiki SEBELUM
             diserahkan):
               1. Head pose dinyatakan relatif acuan frontal R_ref =
                  diag(1,-1,-1). Model 3D +Y ke atas vs citra +Y ke bawah ->
                  rotasi frontal = 180 derajat sumbu X. Tanpa koreksi ini pitch
                  duduk di +/-179 dan MELOMPAT 360 derajat saat melewati titik
                  itu, sehingga fitur kecepatan jadi sampah. Terukur setelah
                  perbaikan: pitch -3,4..+1,4, yaw -3,8..+13,2, roll -2,3..+0,5
                  (derajat) pada 400 frame; head_motion maks 8,2 derajat/frame.
               2. Cadangan tanpa solvePnP (_head_pose_proxy) dibuat bersatuan
                  DERAJAT supaya frame yang jatuh ke cadangan tidak melompat
                  skala; tidak ada NaN dan tidak ada 0,0 palsu (0,0 palsu
                  memicu lonjakan palsu di fitur kecepatan).
               3. _extract_region sekarang memakai np.ndarray landmark, jadi
                  indeksnya WAJIB di-int() sebelum dipakai sebagai slice.
                  Tanpa int() -> TypeError; bug ini tertangkap saat validasi.
               4. Tiga tabel dari SATU pass: POC-ABS saja (skema lama, TIDAK
                  berubah), geometri saja, gabungan. Perbandingan antar
                  keluarga fitur jadi bersih tanpa menjalankan ulang apa pun.
             PERUBAHAN PIPELINE:
               - Stage 2 memakai --with-geometry (satu pass).
               - Stage 3 meng-cache tabel gabungan DAN tabel POC-ABS asli.
               - Stage 4/6/7 memakai tabel gabungan.
               - Stage 5 gerbang dijalankan 3x: POC saja, geometri saja,
                 gabungan. Yang menentukan keluarga baru:
                 output/training/within_subject_v3_geo/summary.md.
               - Config default diganti ke tabr_loso_roi25_reg.toml (akurasi).
                 Config _reg_ce terbukti REGRESI: pemilihan epoch CE berhenti di
                 epoch <= 1 pada 40-48/56 fold.
               - Nama dataset LOSO default diganti ke
                 convat_apex_anxiety_loso_v3_geo. Kalau tetap memakai nama lama,
                 56 fold lama yang sudah DONE akan dilewati diam-diam.
               - --quiet di run_loso.py: progress bar TabR dimatikan dan
                 keluaran tiap fold ditulis ke fold_XXX/train.log. Terukur pada
                 fold 0/1 seed: 460 baris/26.617 byte -> 22 baris/1.631 byte.
             VERIFIKASI:
               - ROI identik bit-per-bit antara extract_rois(img) dan
                 extract_rois_from_landmarks(img, extract_landmarks(img)) pada
                 6 frame nyata, kelima ROI.
               - Ekstraksi terbatas (--limit 5): POC 48 kolom TANPA geo_*;
                 geometri 34 kolom (13 identitas + 21 geo_*); gabungan 69 kolom;
                 0 NaN; 0 kolom konstan.
               - --quiet: DONE.json, report.json, test_split.csv,
                 val_split.csv, train.log semuanya tertulis.
               - Shim tqdm tidak merusak import tqdm.auto (dipakai lib/dnnr).
             CATATAN PEMAKAIAN: karena --drop-features menggantikan default,
             pola untuk POC-ABS saja harus menyertakan _max_m$:
             --drop-features "_max_m$|^geo_".
             BELUM DIJALANKAN: pipeline penuh. Perintah:
             ./scripts/run_pipeline_v3.sh


### Iterasi 4.26 - HASIL: keluarga geometri/head pose TIDAK membantu (+ bug roll saya)
Tanggal    : 2026-10-06
Status     : SELESAI. Pipeline penuh dijalankan user; hasil terukur dan NEGATIF.
             Bug roll ditemukan dan diperbaiki SETELAH run.
Diubah     : features_extraction/geometry.py (BUG: ambiguitas planar solvePnP
             pada roll; + normalize_roll())
Dijalankan : ./scripts/run_pipeline_v3.sh penuh (stage 1-7). 560 video spotting,
             ekstraksi 100.817 baris 0 error, cache, temporal, gerbang 3
             keluarga fitur, LOSO 56 fold x 3 seed, collect + baseline.
Hasil      : BAGIAN A - KELENGKAPAN RUN (bersih)
             56/56 fold DONE, 0 FAILED, 168 report.json. Config akurasi
             (tabr_loso_roi25_reg.toml) terpakai, batch 8, context 8.
             385 fitur efektif (206 fitur gabungan -> agregasi mean+std ->
             variance threshold), 26 di antaranya kolom geo_*.
             --quiet bekerja: seluruh training = 908 baris log.
             BAGIAN B - GERBANG WITHIN-SUBJECT (wasit)
               POC statis v3 (35) : 0/35 signifikan, acc 0,4444, p 0,7761
               GEOMETRI saja (21) : 0/21 signifikan, acc 0,4444, p 0,7512
               GABUNGAN (206)     : 0/206 signifikan (1/206 di kontrol),
                                    acc 0,6111, p 0,2040
             KUNCI: acc gabungan 0,6111 IDENTIK dengan v3 temporal POC saja
             (0,6111, p 0,1990 dari Iterasi 4.21). Artinya angka itu datang
             SELURUHNYA dari fitur POC temporal yang sudah ada sebelumnya;
             keluarga geometri menyumbang NOL. Geometri sendirian 0,4444 =
             sama dengan POC statis sendirian (0,4444).
             BAGIAN C - HASIL LOSO (fitur gabungan, 385 fitur)
               accuracy  0,5595 +- 0,0103 (rata antar seed)
                         seed-ensemble 0,4821, CI 95% 0,3567-0,6099
               MCC       +0,1007 +- 0,0142 (rata); pooled -0,0696
               balAcc    0,5492 | sens 0,4533 | spec 0,6452 | bias -0,0893
               per seed  0,5714 / 0,5536 / 0,5536  <- datar, tidak ada sebaran
               per grup  before_sama    0,4211 vs baseline grup 0,6316 (-0,2105)
                         before_berubah 0,6111 vs baseline grup 0,9444 (-0,3333)
               baseline mayoritas 0,5536
             CI MEMUAT baseline 0,5536 -> tidak terbukti lebih baik dari menebak.
             Per grup keduanya NEGATIF -> paradoks Simpson, keunggulan pooled
             tidak bisa dipercaya.
             PEMBANDING SEDERHANA di fitur yang sama justru LEBIH BURUK:
               logistic 0,4464 (p 0,8507) | gbdt 0,3571 (p 0,9950)
             gbdt 0,3571 di BAWAH acak = tanda tidak ada sinyal + overfit 44 baris.
             BANDINGKAN DENGAN RUN TERBAIK (reg, POC saja 237 fitur):
               reg    : seed-ensemble 0,6250, CI 0,4941-0,7399, MCC +0,2272
                        per seed 0,6071 / 0,5000 / 0,6786
               v3_geo : seed-ensemble 0,4821, CI 0,3567-0,6099, MCC +0,1007
                        per seed 0,5714 / 0,5536 / 0,5536
             JADI MENAMBAH GEOMETRI MEMBUAT HASIL LEBIH BURUK dari reg.
             MEKANISME (konsisten dengan Iterasi 4.23/4.24): fitur 237 -> 385
             (d/n 5,4 -> 8,8). best_epoch median turun 5 -> 4 dan fold yang
             berhenti di epoch <= 1 naik 34/168 -> 53/168, yaitu early stopping
             makin sering memilih model yang belum belajar.
             BAGIAN D - BUG SAYA: ambiguitas planar solvePnP pada roll
             Ditemukan SAAT MEMERIKSA hasil (bukan saat menulis kode).
             solvePnP dengan model wajah yang hampir planar punya DUA solusi
             kembar untuk wajah hampir frontal: solusi benar dan solusi terbalik
             180 derajat pada roll (pitch/yaw hampir sama).
             BUKTI: 9 dari 10 neutral.png subjek abdillah_agil_arbiansyah
             memberi roll ~0, SATU sample memberi +179,66 - orang yang sama,
             sesi yang sama. Karena fitur statis dikurangi baseline, ambiguitas
             ini berubah jadi lonjakan ~180-360 derajat.
             DAMPAK TERUKUR: 1.472 baris (1,46%) dengan |roll| > 170,
             terkonsentrasi di 5 subjek (sampai 20% frame mereka);
             geo_head_motion mencapai 359,86 derajat/frame (gerakan kepala yang
             mustahil). Merusak geo_roll, geo_d_roll, geo_head_motion.
             KENAPA LOLOS VERIFIKASI SAYA: verifikasi sebelumnya hanya memakai
             400 frame dari beberapa klip dan semuanya memberi rentang bersih
             (-2,3..+0,5). Subjek yang kena tidak ada di sampel itu. Verifikasi
             yang benar harus lintas SEMUA subjek, bukan beberapa klip.
             PERBAIKAN: normalize_roll() melipat roll ke (-90, 90] - kendala
             yang sah karena wajah manusia dalam wawancara tidak pernah
             terbalik. Diverifikasi: sebaran roll neutral.png abdillah
             -2,60..+0,49 (dari -2,60..+179,66); 600 frame lintas subjek roll
             maks |8,64| dan 0 baris di luar (-90,90]; head_motion maks 8,14
             (dari 359,86).
             PENTING: bug ini TIDAK mengubah kesimpulan. Fitur yang bersih
             (EAR, MAR, alis, rahang - 17 dari 21) sudah punya kesempatan
             muncul dan tidak ada yang lolos koreksi FDR. Tapi angka run di
             Bagian C dihitung dengan fitur roll yang masih rusak, jadi run
             itu TIDAK boleh dipakai sebagai angka final.
             BAGIAN E - NUANSA YANG JUJUR (bukan "tidak ada sinyal" mutlak)
             p-value mentah terkecil di grup "berubah" (sebelum koreksi FDR):
               POC     : alis_kanan_mean_abs_y  0,0075 (kontrol 0,9201)
               GEOMETRI: geo_lip_corner_drop    0,0352 (kontrol 0,4727)
             Keduanya TIDAK signifikan di kontrol (jadi bukan efek sesi), TAPI
             tidak ada yang lolos FDR: dengan n=18 subjek dan 21-35 fitur,
             ambang FDR praktis ~0,002-0,005. Bacaan yang benar: TIDAK TERDETEKSI
             pada ukuran sampel ini, bukan "terbukti nol".
             LANGKAH BERIKUTNYA (pilihan user):
             1. Re-run dengan roll yang sudah diperbaiki (ekstraksi ~30 menit +
               training ~30 menit) supaya angka Bagian C bersih.
             2. Berhenti menambah keluarga fitur; ini uji keluarga fitur KEDUA
               yang gagal, dan dua-duanya gagal di gerbang yang sama.
             YANG TERBUKTI BERGUNA sejauh ini tetap HANYA ambang-dari-val.


### Iterasi 4.27 - EMPAT PERBAIKAN METODOLOGI (batch A) - 1 di antaranya membatalkan kesimpulan saya
Tanggal    : 2026-10-06
Status     : SELESAI (kode + verifikasi pada data nyata). Re-run BELUM.
Diubah     : scripts/run_loso.py (BUG: urutan praproses variance vs scale)
             scripts/run_loso_baseline.py (BUG yang sama)
             scripts/within_subject_test.py (BUG: permutasi global -> berpasangan)
             scripts/collect_loso_results.py (BUG: ambang inf + heading salah)
             scripts/run_pipeline_v3.sh (BUG: --force tidak diteruskan ke stage 6)
Dijalankan : Audit kode + verifikasi tiap perbaikan pada artefak run nyata
             (tanpa training). Semua diukur, bukan diklaim.
Hasil      : BAGIAN A - BUG #1 (PALING PENTING): variance threshold = filter SKALA
             VarianceThreshold(1e-4) dijalankan pada nilai MENTAH, SEBELUM
             StandardScaler. Ambang varianza absolut pada fitur bersatuan
             berbeda bukan filter "blok statis" - itu filter SKALA. Fitur
             geometri (ternormalisasi inter-okular, orde ~1e-4) jatuh di bawah
             ambang yang disetel untuk POC-ABS.
             TERUKUR pada tabel gabungan nyata (fold-level, 402 kolom):
               LAMA (variance->scale): geo lolos 26/42, POC 359/360, total 385
               BARU (scale->variance): geo lolos 42/42, POC 360/360, total 402
             Jadi 16 dari 42 kolom geometri (mean+std) TIDAK PERNAH sampai ke
             model. Yang terbuang termasuk:
               geo_lip_corner_drop (p gerbang 0,0352 = fitur geometri TERKUAT)
               geo_mouth_open, geo_mouth_width, geo_mar, geo_brow_eye_kiri/kanan,
               geo_brow_gap, geo_d_ear_mean, geo_d_mar
             geo_mouth_open adalah fitur yang justru direkomendasikan paper
             Indonesia (Rumahorbo dkk, BINIS, CMBN 2025).
             KONSEKUENSI: kesimpulan saya di Iterasi 4.26 ("geometri menyumbang
             nol") TIDAK SAH - 43% keluarga itu, termasuk anggotanya yang paling
             menjanjikan, tidak pernah diuji. Yang benar: fitur geometri yang
             lolos filter skala tidak menyumbang apa-apa. Harus diulang.
             Perbaikan: scale DULU, baru variance. Fitur yang bertahan nilainya
             IDENTIK (StandardScaler per kolom; diverifikasi np.allclose), jadi
             yang berubah hanya SELEKSI, bukan nilai. Tetap fit train saja ->
             tidak ada kebocoran.
             Catatan: run lama POC (reg, 237 fitur) hampir tidak terpengaruh
             karena POC hanya kehilangan 1 kolom dari 360, jadi hasil terbaik
             sebelumnya masih bisa dibandingkan.
             BAGIAN B - BUG #2: ambiguitas planar solvePnP pada roll
             (ditemukan di Iterasi 4.26, diperbaiki di sana). Tabel fitur yang
             tersimpan masih memuat roll rusak, jadi butuh re-ekstraksi.
             BAGIAN C - BUG #3: permutasi gerbang global, seharusnya berpasangan
             Desainnya berpasangan (tiap subjek = 2 sesi, label berbeda), jadi
             null yang benar = "label tiap subjek dibalik atau tidak", bukan
             "acak label global". Versi global memutus pasangan sesi.
             Dampak terukur (200 permutasi):
               POC      : p 0,7761 (global) -> 0,8010 (berpasangan)
               geometri : p 0,7512 (global) -> 0,8109 (berpasangan); dijalankan
                          ulang lewat script: null 0,4914, p 0,7363
               gabungan : p 0,2040 (global) -> 0,1542 (berpasangan)
             Kesimpulan tidak berubah, tapi metode lama tidak bisa dipertahankan
             di sidang.
             BAGIAN D - BUG #4: ambang Youden bisa terpilih = inf
             roc_curve() mengembalikan thr[0] = inf, dan argmax(tpr-fpr) bisa
             memilihnya. Kalau terpilih: semua test fold itu diprediksi 0 DAN
             rata-rata ambang jadi inf -> laporan menulis "inf +- nan".
             TERJADI NYATA: 1 fold dari 56 di seed 0 run v3_geo.
             Perbaikan: batasi pilihan ke ambang berhingga.
             Sebelum: ambang terpilih (rata-rata) = inf +- nan
             Sesudah: 0,5250 +- 0,0322
             Ini penting karena ambang-dari-val adalah SATU-SATUNYA lever yang
             sejauh ini terbukti berguna (Iterasi 4.22/4.23) - angkanya tidak
             boleh rusak.
             BAGIAN E - BUG #5: label laporan salah
             (a) collect: heading "## Level {row_unit}" menamai tabel diagnostik
                 FRAME sebagai "Level subject" saat --row-unit subject. Diperbaiki
                 jadi "## Level frame (diagnostik komposisi, BUKAN performa)",
                 plus catatan "Satuan baris training: `subject`".
             (b) within_subject_test: judul di-hardcode "(POC-ABS)" padahal
                 dijalankan juga untuk geometri/gabungan. Sekarang memakai nama
                 berkas tabel.
             BAGIAN F - CATATAN: run terbaik (roi25_reg, 62,50%) TIDAK punya
             val_split.csv karena dijalankan sebelum Iterasi 4.17 menambahkannya.
             Jadi analisis ambang-dari-val untuk run itu tidak bisa dihitung
             (script melaporkan "belum bisa dihitung", bukan crash). Data gap,
             bukan bug kode.
             BAGIAN G - BUG #6: --force pipeline TIDAK diteruskan ke stage 6
             run_pipeline_v3.sh memakai --force hanya untuk melewati cek "sudah
             ada" di stage 2/3/4. Stage 6 memanggil run_loso.py TANPA --force,
             dan run_loso.py melewati fold yang sudah punya DONE.json.
             Akibatnya `./scripts/run_pipeline_v3.sh --force` mengekstraksi
             ulang fitur TAPI melewati SEMUA 56 fold, lalu melaporkan SELESAI
             dengan hasil LAMA - diam-diam. Ini persis jebakan yang sama dengan
             nama dataset di Iterasi 4.25.
             Perbaikan: FORCE_ARG=() / [ "$FORCE" = 1 ] && FORCE_ARG=(--force),
             diteruskan ke run_loso.py.
             Diverifikasi: dry-run tanpa --force tidak memuat --force; dengan
             --force memuat "--force --quiet".
             VERIFIKASI (semua pada artefak nyata, tanpa training):
             - parse AST 4 berkas + bash -n pipeline: ok.
             - #1: tiru urutan baru pada tabel gabungan -> 385 vs 402, geo 26/42
               vs 42/42; nilai kolom yang bertahan identik (np.allclose True).
             - #3: 500 permutasi x 3 subjek -> label hanya dibalik di dalam
               subjek, 0 rusak; null bergeser sesuai harapan.
             - #4: seed 0 v3_geo lama mean=inf -> baru 0,5292; seluruh 3 seed
               berhingga (0,5292 / 0,4910 / 0,5549).
             - #5: collect + gerbang dijalankan ke direktori scratch; heading
               "Level frame" dan judul memakai nama berkas tabel.
             - #6: dry-run dengan/tanpa --force.
             LANGKAH BERIKUTNYA: re-ekstraksi (roll) + re-run LOSO dengan
             keenam perbaikan. Perintah: ./scripts/run_pipeline_v3.sh --force


### Iterasi 4.28 - AUC kembali (level subjek) + spotting TIDAK perlu diutak-atik + config final
Tanggal    : 2026-10-06
Status     : SELESAI (kode + 3 eksperimen). Tidak ada training TabR baru.
Diubah     : scripts/collect_loso_results.py (AUC level subjek, dihitung sendiri)
Dijalankan : 1) AUC untuk 4 run yang sudah ada (tanpa training).
             2) A/B seleksi event/apex pada tabel yang SUDAH ada (tanpa re-spotting).
             3) Uji signifikansi AUC (bootstrap 2000 + permutasi 2000).
Hasil      : BAGIAN A - AUC DITAMBAHKAN, DIHITUNG SENDIRI (bukan patch lib TabR)
             Alasan AUC dihapus dulu (Iterasi 4.1): (a) permintaan user, (b) butuh
             patch lib/metrics.py karena test per fold LOSO cuma 1 kelas.
             Sekarang AUC dihitung dari proba LEVEL SUBJEK yang sudah dikumpulkan
             collector: tiap subjek menyumbang TEPAT SATU proba dari model yang
             tidak pernah melihatnya -> bebas-bocor, terdefinisi, dan TIDAK
             memerlukan patch upstream. Jadi keputusan Iterasi 4.1 soal patch
             tetap berlaku; yang kembali hanya METRIK-nya.
             AUC TIDAK bergantung ambang 0.5, jadi ia mengukur perankingan.
             BAGIAN B - AUC MEMBEDAKAN CONFIG, accuracy TIDAK
             AUC seed-ensemble (bootstrap 95%, permutasi 2000):
               run        fitur  AUC     CI95            p       verdict
               roi25_reg  237    0,6142  0,4513-0,7577   0,0765  di atas acak
               tiny       237    0,6142  0,4518-0,7612   0,0765  di atas acak
               v3_acc     370    0,4774  0,3122-0,6404   0,6252  level acak
               v3_geo     402    0,4387  0,2890-0,5939   0,7926  BAWAH acak
             TEMUAN PENTING:
             (1) reg dan tiny punya AUC IDENTIK (0,6142). Kapasitas ekstra reg
                 (52.545 vs 13.089 param) TIDAK membeli apa pun.
             (2) v3 (370/402 fitur) JATUH ke level/bawah acak. Jadi menambah
                 fitur BUKAN cuma tidak menolong - ia MENGHANCURKAN sinyal lemah
                 yang tadinya ada. Ini penjelasan mekanistik untuk regresi v3
                 yang selama ini cuma terlihat sebagai angka accuracy.
             (3) AUC 0,6142 / p=0,0765 adalah hasil TERBAIK proyek ini, dan
                 konsisten dengan baseline GBDT netral+temporal (acc 0,6071,
                 p=0,0796) - dua metode berbeda menunjuk representasi yang sama.
             (4) AUC 0,614 BELUM signifikan (CI memuat 0,5). Jujur: sinyal lemah,
                 belum terbukti.
             BAGIAN C - SPOTTING/APEX TIDAK PERLU DIUBAH (A/B tanpa re-spotting)
             Diuji dengan MEMFILTER event yang sudah ada (bukan spotting ulang),
             pada tabel POC temporal 185 fitur, gerbang 200 permutasi:
               seleksi                    baris    acc     p
               SEMUA event               100.817  0,6111  0,1393  <- terbaik
               event micro (durasi <=12f)  34.143  0,4167  0,8209
               event panjang (durasi >12f) 66.674  0,5556  0,2985
               frame APEX saja              6.971  0,5278  0,4080
               2 frame sekitar apex        20.912  0,6111  0,1592
               onset..apex (rise)          54.637  0,5278  0,4627
               apex..offset (fall)         53.151  0,5833  0,2139
             KESIMPULAN: TIDAK ADA subset event yang memunculkan sinyal. Yang
             terbaik tetap SELURUH event. Membatasi ke micro-expression murni
             (<=12 frame) justru TERBURUK (0,4167). Apex-only di level acak.
             Jadi hipotesis "spotting/apex salah tempat sehingga sinyal hilang"
             TIDAK didukung: kalau event yang terdeteksi memang noise, membatasi
             ke subset yang "lebih bersih" seharusnya MEMBANTU - yang terjadi
             sebaliknya. Tuning SPOT_* (butuh re-spotting jam-an) TIDAK
             dijustifikasi oleh data ini.
             CATATAN METODOLOGI: uji apex pertama saya SALAH - saya bandingkan
             `frame` (indeks relatif-klip, 1 = onset) dengan `apex_frame`
             (absolut di video), sehingga cuma 121 baris yang cocok secara
             kebetulan. Setelah dipetakan benar (apex_rel = apex_frame -
             onset_frame + 1) hasilnya 6.971 baris dan tetap null. Kesalahan ini
             tertangkap karena jumlah barisnya tidak masuk akal.
             BAGIAN D - DISTRIBUSI DURASI EVENT (konteks)
             metadata 6.972 event: median 12 frame, mean 14,5, min 3, maks 102.
             Pada 60 fps, micro-expression = 1/25..1/5 s = 2,4..12 frame.
             Jadi ~55% event masuk rentang micro-expression, ~45% lebih panjang.
             Event memang condong panjang, tapi Bagian C menunjukkan itu BUKAN
             penyebab hilangnya sinyal.
             BAGIAN E - CONFIG FINAL YANG DIREKOMENDASIKAN
             `tabr_loso_compact.toml` (semula `tabr_loso_tiny.toml`) pada tabel POC netral+temporal (237 fitur),
             agregasi subjek:
               AUC      0,6142  <- SAMA dengan config reg
               accuracy 0,5714  (baseline mayoritas 0,5536)
               gap tr-val -0,0055 (train < val -> nol hafalan)
               gap tr-test 0,1909 (terendah dari semua run)
               sebaran antar seed 5,4 poin (terendah kedua)
             Config ini yang dipakai sebagai headline: AUC setara reg, tapi satu-
             satunya yang overfitting-nya praktis nol, jadi tidak ada hafalan
             yang perlu dimaafkan di sidang.
             `reg` tetap dilaporkan sebagai pembanding akurasi (acc 0,5952,
             AUC sama 0,6142, tapi gap tr-test 0,3327).
             CATATAN JUJUR: peringkat config ini TIDAK boleh diklaim dari
             accuracy (selisih 2,4 poin < derau antar seed sampai 18 poin).
             Yang membuat tiny menang adalah AUC + gap + varians, bukan accuracy.


### Iterasi 4.29 - AUDIT spotting/apex + PEMULIHAN metadata yang saya rusak + rename config
Tanggal    : 2026-10-07
Status     : SELESAI (audit + pemulihan + rename). Tidak ada training baru.
Diubah     : scripts/process_spotting_pipeline.py (rebuild_metadata_rows menerima
             source_video: str, bukan objek sample; + rebuild_metadata_from_clips;
             + env SPOT_REBUILD_METADATA_ONLY)
             experiments/configs/tabr_loso_tiny.toml -> tabr_loso_compact.toml
Dijalankan : Audit kode spotting/apex + uji empiris apex, lalu pemulihan metadata.
Hasil      : BAGIAN A - SAYA MERUSAK metadata.xlsx DAN MEMULIHKANNYA
             Saat mengimpor process_spotting_pipeline.py untuk menguji ulang
             sinyal, blok eksekusi tingkat-modul di berkas itu IKUT JALAN. Karena
             SPOT_DATASET_ROOT saat itu salah, ia menemukan 0 video lalu MENULIS
             metadata.xlsx KOSONG -> 6.972 baris hilang.
             PEMULIHAN: klip event (6.972) dan neutral.png (560) utuh, jadi
             metadata dibangun ulang dari nama direktori klip + nama berkas
             *-apex.png. Driv raw sedang TIDAK ter-mount, jadi jalur resume biasa
             tidak bisa dipakai; karena itu ditambahkan
             SPOT_REBUILD_METADATA_ONLY=1 yang bekerja TANPA video mentah.
             Hasil: 6.972 baris, 560 sample - persis sama.
             VERIFIKASI PEMULIHAN:
               - 6.972/6.972 clip cocok dengan tabel fitur yang utuh.
               - 6.966/6.972 rows-fitur == saved_frames; 6 sisanya LEBIH KECIL
                 karena frame yang wajahnya tidak terdeteksi memang dilewatkan
                 (perilaku lama, bukan error metadata). n_feat > saved_frames: 0.
               - min(frame)==1 pada 6.971/6.972; max(frame)==saved_frames pada
                 6.971/6.972.
               - RE-EKSTRAKSI 40 klip dari metadata hasil rebuild -> 746 baris,
                 dibandingkan dengan tabel v3 asli: 48 kolom, NOL perbedaan,
                 IDENTIK BIT-PER-BIT.
             PELAJARAN: berkas pipeline ini punya efek samping saat di-import.
             Jangan pernah `import` berkas ini untuk menguji fungsi di dalamnya.
             BAGIAN B - AUDIT SPOTTING/APEX: TIDAK ADA BUG YANG MENJATUHKAN AKURASI
             (1) Kekhawatiran user "apex bukan puncak, cuma gerakan" SUDAH
                 diperbaiki di Iterasi 2.2 dan TERVERIFIKASI masih berlaku:
                 run_pipeline_v3.sh mengirim SPOT_ABS=1, dan build_roi_signals
                 memakai ref = frame-0 TETAP (bukan frame N-1). Jadi sinyalnya
                 DISPLACEMENT kumulatif -> puncaknya memang apex. Kalau memakai
                 frame berurutan (mode lama), puncaknya adalah TRANSISI, bukan
                 apex - itu bug yang dimaksud, dan sudah tidak aktif.
             (2) block_size TIDAK mismatch: spotting dan ekstraksi dua-duanya
                 mengimpor BLOCK_SIZE=9 dari features_extraction/roi_config.py
                 (dulu pernah menyimpang; sudah diperbaiki di Iterasi 4.21).
             (3) Apex memang puncak interior, BUKAN artefak drift: posisi apex
                 relatif di dalam klip median 0,556 (tengah), dan hanya 1,7%
                 event punya apex di frame terakhir. Bandingkan argmax mentah
                 yang 15,6% jatuh di frame terakhir - logika fase justru
                 MEMBUANG artefak ujung klip itu.
             (4) Tidak ada kebocoran label di spotting/ekstraksi: label tidak
                 pernah dibaca; `condition` hanya dipakai untuk diagnosis grup
                 dan sudah ditandai sebagai kebocoran label kalau dipakai fitur.
             (5) Threshold height = mean+std dihitung per-sample dari seluruh
                 sinyal video itu sendiri (bukan per-label, bukan lintas sample)
                 -> bukan kebocoran, hanya deteksi offline.
             TEMUAN YANG TETAP NYATA (tapi BUKAN penyebab akurasi jatuh):
             (a) DEDUP LINTAS ROI MEMIHAK MULUT. detect_events_per_roi
                 mengurutkan kandidat berdasarkan `apex_value` MENTAH, dan
                 magnitudo mulut jauh lebih besar dari alis -> event yang
                 bertahan hampir selalu event mulut. Micro-expression alis
                 (AU1/AU2/AU4) jadi jarang terwakili. Perbaikan yang benar:
                 normalisasi apex_value per ROI (z-score dalam ROI) sebelum
                 dedup. BELUM dikerjakan - dampaknya belum diukur.
             (b) Region asal event TIDAK disimpan di metadata, jadi asal-usul
                 tiap event tidak bisa diaudit dari artefak. Observability gap.
             (c) merge_distance=10 di ApexPhase aktif (tidak di-override) dan
                 bisa menggabungkan dua micro-expression berbeda.
             BAGIAN C - CONFIG DI-RENAME
             `tabr_loso_tiny.toml` -> `tabr_loso_compact.toml` (permintaan user).
             Header config diisi HASIL terukurnya (AUC 0,6142 = sama dgn reg,
             gap train-val -0,0055). Referensi di dokumen ikut diperbarui.
             Direktori hasil lama `convat_loso_tiny_roi25` TIDAK diubah (itu
             artefak hasil); run berikutnya memakai nama baru.


### Iterasi 4.30 - FIX dedup lintas-ROI (mulut bias) + reset data + driv ter-mount
Tanggal    : 2026-10-07
Status     : SELESAI (kode + verifikasi end-to-end pada 3 video nyata). Reset sudah
             dijalankan; pipeline siap dijalankan user dari awal.
Diubah     : scripts/process_spotting_pipeline.py
               - detect_events_per_roi: skor dedup jadi `apex_z` (z-score di dalam
                 sinyal ROI itu sendiri), bukan `apex_value` mentah
               - region disimpan di event -> metadata -> nama direktori klip
               - rebuild_metadata_rows: regex `event_(\d+)-(\d+)(?:_(.+))?`
             scripts/run_pipeline_v3.sh
               - --fresh: hapus klip HANYA kalau driv mentah ada (penjaga)
               - driv mentah tidak lagi wajib kalau klip sudah ada (auto rebuild)
               - --fresh juga membersihkan exp/tabr + data + within_subject
Dijalankan : Mount driv (nvme0n1p7 "New Volume"), verifikasi 560 video, uji
             end-to-end 3 video (spotting -> metadata -> ekstraksi 3 tabel),
             lalu reset data turunan.
Hasil      : BAGIAN A - DRIV TER-MOUNT, DATA MENTAH UTUH
             Driv fisiknya ADA (nvme0n1p7, label "New Volume", 43,9G) tapi tidak
             ter-mount; di-mount dengan udisksctl. Terverifikasi: 560 .avi + 560
             .webm, 11G, struktur before/after lengkap. Jadi reset penuh AMAN -
             klip bisa dibuat ulang.
             BAGIAN B - BUG DEDUP LINTAS-ROI (yang dilaporkan di Iterasi 4.29)
             detect_events_per_roi mengurutkan kandidat berdasarkan `apex_value`
             MENTAH. Magnitudo mulut jauh lebih besar dari alis/mata, jadi event
             mulut selalu menang saat overlap dan micro-expression alis
             (AU1/AU2/AU4) tenggelam.
             PERBAIKAN: skor dedup = z-score apex di dalam sinyal ROI itu sendiri
             (`apex_z`), sehingga antar ROI sebanding. `apex_value` mentah tetap
             disimpan untuk pelaporan.
             BUKTI DAMPAK (3 video nyata, 44 event):
               SEBELUM (konsekuensi logika lama): mulut mendominasi dedup
               SESUDAH: alis_kiri 10, alis_kanan 10, mata_kanan 10,
                        mulut 7, mata_kiri 7
               -> alis+mata 37/44 (84%), mulut 7/44 (16%).
             REGION SEKARANG TERSIMPAN: event -> metadata (kolom `region`) ->
             akhiran nama direktori klip (`event_00090-00096_alis_kanan`).
             Dipilih masuk nama direktori supaya bisa DIPULIHKAN saat rebuild
             metadata; regex rebuild dibuat toleran (region opsional) sehingga
             klip lama tanpa sufiks tetap terbaca (region = None).
             BUKTI ROUND-TRIP: metadata asli vs hasil rebuild -> 44/44 baris,
             region identik di semua baris.
             BUKTI END-TO-END: spotting 3 video -> 44 event -> ekstraksi
             --with-geometry -> 3 tabel (POC 48 kolom / geometri 21 / gabungan
             69), 786 baris, Errors: 0.
             CATATAN: uji pertama saya gagal 44/44 karena output ditaruh di /tmp,
             di luar ROOT proyek; extractor memakai relative_to(ROOT) sehingga
             path luar proyek ditolak. Bukan regresi - uji diulang di dalam
             proyek dan 0 error.
             BAGIAN C - PENJAGA --fresh (penting)
             Sebelumnya `--fresh` menghapus $OUT_ROOT TANPA SYARAT. Kalau driv
             mentah tidak ter-mount, itu = kehilangan 6.972 klip tanpa
             penggantinya. Sekarang: klip dihapus HANYA kalau $RAW_ROOT ada.
             Selain itu driv mentah tidak lagi wajib: kalau klip sudah ada,
             stage 1 otomatis membangun ulang metadata dari klip
             (SPOT_REBUILD_METADATA_ONLY=1) tanpa spotting ulang.
             BAGIAN D - RESET DATA (dijalankan)
             Dihapus (semua turunan, bisa dibuat ulang):
               output/apex_v2 (klip + metadata, 9,5G)
               experiments/features/apex/poc_abs_roi_signals_v3* (semua varian)
               output/training/convat_apex_anxiety_loso_v3_geo{,_baseline}
               output/training/within_subject_v3_{poc,geo,geo_temporal}
               third_party/.../exp/tabr/convat_apex_anxiety_loso_v3_geo
               third_party/.../data/convat_apex_anxiety_loso_v3_geo
             Disk: 56G -> 66G bebas.
             DIKEEP sebagai jejak audit: hasil historis (roi25, roi25_reg,
             v3, v3_acc, v3_d1/d2/d3, compact) beserta output/training-nya.
             BAGIAN E - PERINTAH
             ./scripts/run_pipeline_v3.sh
             (tidak perlu --fresh lagi; reset sudah dilakukan. Stage 1 akan
             spotting ulang 560 video ~50 menit dan MENERAPKAN fix dedup.)
             Semua 7 stage jalan: spotting -> ekstraksi -> cache -> temporal ->
             gerbang -> LOSO -> collect+baseline.


### Iterasi 4.31 - FIX default dataset pipeline (v3_geo -> roi25_reg) + penjaga mismatch + sidik jari fitur
Tanggal    : 2026-10-07
Status     : SELESAI (kode + verifikasi). BELUM ada training ulang.
Diubah     : scripts/run_pipeline_v3.sh
               - LOSO_DATASET default: convat_apex_anxiety_loso_v3_geo (402 fitur)
                 -> convat_apex_anxiety_loso_roi25_reg (237 fitur)
             scripts/run_loso.py
               - --dataset default: convat_apex_anxiety_loso_roi25
                 -> convat_apex_anxiety_loso_roi25_reg (samakan dgn DEFAULT_CONFIG)
               - peringatan kalau `[data] path` di config != --dataset
               - feature_fingerprint(): DONE.json kini mencatat `inputs.features_sha1`
                 + `inputs.config`; fold di-skip HANYA kalau sidik jari cocok
Masalah    : (1) Run 2026-10-07 13:26:59 (stage 6 memakai fold yang dilatih 13:08-13:14)
                 menghasilkan MCC -0,0175 / AUC 0,4723 / accuracy 0,4940 - DI BAWAH
                 acak dan di bawah baseline mayoritas 0,5536. Baseline pembanding ikut
                 null (logistic 0,4286 p=0,9055; gbdt 0,4643 p=0,7861).
             (2) 56 fold `roi25_reg` di exp/tabr bertanggal 2026-10-06 11:14-11:23
                 dilatih pada tabel fitur LAMA (237 kolom), sedangkan tabel fitur
                 sekarang (fused_temporal.pkl, 2026-10-07 13:06) punya 219 kolom.
                 Tanpa fix (2), run berikutnya akan SKIP 56 fold itu dan melaporkan
                 angka lama sebagai hasil tabel fitur baru.
Akar       : (1) Pipeline memakai dataset _v3_geo (402 fitur), sedangkan config compact
                 di-tuning pada 237 fitur (roi25_reg). run_loso.py:511 menimpa
                 `[data] path` dengan `:data/{--dataset}`, jadi path yang ditulis di
                 config DIABAIKAN tanpa peringatan.
             (2) DONE.json hanya mencatat fold/subjek/rows/seeds, TIDAK mencatat tabel
                 fitur mana yang dipakai. Resume karena itu tidak bisa membedakan
                 "sudah benar" dari "sudah usang".
Bukti      : AUC 0,6142 (config compact & reg) terukur pada 237 fitur
             (changes-log Iterasi 4.2x). Pada 402 fitur: AUC 0,4723.
             Perbandingan output/training/:
               _roi25_reg  237 fitur  acc 0,5952  MCC +0,1706   <- terbaik
               _v3         359 fitur  acc 0,5238  MCC +0,0154
               _v3_geo     402 fitur  acc 0,4940  MCC -0,0175   <- run terakhir
Verifikasi : ./scripts/run_pipeline_v3.sh --dry-run ->
               DATASET : convat_apex_anxiety_loso_roi25_reg
               CONFIG  : experiments/configs/tabr_loso_compact.toml
             Ketiga default disamakan (run_pipeline_v3.sh, run_loso.py, compact.toml
             `[data] path`) -> identik.
             Penjaga mismatch: config=roi25_reg + --dataset=v3_geo -> peringatan tampil;
             config=roi25_reg + --dataset=roi25_reg -> senyap.
             Sidik jari: stabil utk input sama; berubah kalau tabel ditulis ulang
             (mtime) atau kolomnya beda; DONE.json lama tanpa `inputs` -> latih ulang.
Catatan    : KOREKSI (2026-10-07 15:3x) - klaim awal di entri ini SALAH.
             Saya menulis bahwa mengganti LOSO_DATASET memulihkan kombinasi 237
             fitur. Itu tidak benar. `--dataset` HANYA menamai folder keluaran;
             DATA LATIH ditentukan oleh `--features`, dan stage 6 selalu memakai
             `poc_abs_roi_signals_v3_fused_temporal.pkl` (POC + geometri).
             Bukti: run 14:10:38-15:30:33 menghasilkan summary.csv + per_subject.csv
             yang BYTE-IDENTIK dengan run _v3_geo sebelumnya (diff bersih).
             Pemetaan fitur yang benar (dari log stage 6 + pengukuran langsung):
               402 fitur <- _v3_fused_temporal.pkl   (201 numerik x2)  <- DIPAKAI
               240 fitur <- _neutral_temporal.pkl    (120 numerik x2)  -> 237
                            setelah variance-threshold (3 dibuang)
             Jadi selisih 237 vs 402 = FUSI GEOMETRI, bukan nama dataset.
             Untuk kembali ke 237, ubah `--features` ke _neutral_temporal.pkl.
             Catatan: 5 region di metadata (alis_kiri/kanan, mata_kiri/kanan, mulut)
             memang BY DESIGN - roi_config.py sengaja memisahkan alis dari mata
             supaya tidak tumpang tindih.
             Sisa catatan di bawah tetap berlaku.




### Iterasi 4.32 - RISET + UJI: apakah sinyal bisa diperkuat? (jawaban: tidak ada sinyal stabil)
Tanggal    : 2026-10-07
Status     : SELESAI (riset + 4 run eksperimen). Tidak ada perubahan protokol.
Diubah     : scripts/run_pipeline_v3.sh
               - TRAIN_FEATURES dipisah dari FEAT_FUSED_TEMPORAL (yang terakhir
                 adalah KELUARAN stage 4, bukan masukan training)
               - stage 6/7 memakai TRAIN_FEATURES (default: POC-saja temporal)
             experiments/features/apex/poc_abs_roi_signals_v3_poc_temporal.pkl (baru)
             experiments/features/apex/poc_abs_roi_signals_v3_poc20_temporal.pkl (baru)

RISET (2019-2026) - teknik yg ditemukan:
  1. Differential AU vs neutral baseline (StressGAT, arXiv 2607.20819):
     normalisasi per orang thd baseline netral + temporal + LOSO -> 88,62%
     pada 58 subjek. REPO SUDAH melakukan ketiganya (--baseline neutral,
     stage 4 temporal, stage 6 LOSO). Jadi resepnya bukan yg kurang.
  2. Identity-invariant FER (IF-GAN arXiv 1903.08051; Kim IEEE 2024;
     Shao 2023) - buang informasi identitas dari representasi ekspresi.
  3. PERINGATAN METODOLOGIS (Frontiers Digital Health 2026): "test-inclusive
     baseline normalization" menggelembungkan akurasi 3-13 poin. Relevan:
     neutral.png diambil dari sampel yg sama. Sudah diperiksa: neutral =
     frame awal video, event = frame berikutnya (terpisah secara temporal),
     jadi ini personalisasi yg sah, bukan kebocoran.

EKSPERIMEN (semua LOSO 56 fold x 3 seed, config compact, bebas-bocor):
  tabel                              fitur   acc      MCC      AUC     verdict
  _v3_fused_temporal (POC+geometri)   402   0,4940  -0,0175   0,4723  bawah acak
  _v3_poc_temporal (POC semua sinyal) 360   0,5357  +0,0554   0,4852  bawah acak
  _v3_poc20_temporal (20 sinyal/ROI)  240   0,4524  -0,1159   0,4589  bawah acak
  _neutral_temporal (klip LAMA)       240   0,5476  +0,0856   0,5385  level acak
  baseline mayoritas                         0,5536

TEMUAN UTAMA - 0,6142 TIDAK TEREPRODUKSI:
  Tabel yg sama (neutral_temporal, 240 fitur) dijalankan ulang -> AUC 0,5385,
  BUKAN 0,6142. Selisih ini di dalam derau antar-seed.
  Derau antar-seed (dari summary.csv, data & config identik):
    237 backup : acc per seed [0,607 | 0,500 | 0,679]  spread 0,179
                 MCC per seed [0,187 |-0,020 | 0,345]  spread 0,364
    240 klip baru: acc [0,500 | 0,446 | 0,411]  spread 0,089
    Satu seed bilang "sinyal bagus", seed lain bilang "murni acak".
  Jarak "terbaik" ke acak = 0,11. Derau antar-seed = 0,09-0,18.
  -> DERAU LEBIH BESAR DARI SINYAL.

  Catatan: changes-log sendiri sudah menulis (Iterasi 4.2x):
  "(4) AUC 0,614 BELUM signifikan (CI memuat 0,5). Jujur: sinyal lemah,
  belum terbukti." Jadi angka itu memang tidak pernah diklaim terbukti.

KESIMPULAN:
  Tidak ada sinyal stabil untuk diperkuat. Semua konfigurasi (402/360/240,
  klip baru & lama) berada di dalam derau acak. Memperbaiki granularitas
  baris, normalisasi, atau seleksi fitur tidak akan menciptakan sinyal yg
  tidak ada di representasi POC-ABS pada dataset ini.
  Jalur yg masih terbuka: ganti representasi (bukan model/hyperparameter).


### Iterasi 4.33 - PIPELINE JADI MURNI POC-ABS (AU/geometri dihapus dari alur)
Tanggal    : 2026-10-07
Status     : SELESAI (kode + dry-run). BELUM dijalankan ulang end-to-end.
Diubah     : scripts/run_pipeline_v3.sh
               - stage 2: buang flag --with-geometry (dan cek berkas _geo/_fused)
               - stage 3: cache hanya tabel POC-ABS (bukan gabungan)
               - stage 4: masukan = _v3_full.pkl (POC) -> _v3_poc_temporal.pkl
               - stage 5: gerbang jadi POC-only (2 tabel, bukan 3 keluarga)
               - variabel FEAT_GEO_XLSX / FEAT_FUSED_XLSX / FEAT_FUSED_PKL /
                 FEAT_FUSED_TEMPORAL dihapus; diganti FEAT_TEMPORAL
               - --fresh: daftar dir within_subject disesuaikan
             (tidak diubah) scripts/extract_features_poc_abs.py
               - kode --with-geometry TETAP ADA, hanya tidak dipanggil pipeline
Alasan     : hasil terukur pada protokol LOSO bebas-bocor (Iterasi 4.2x, 4.32):
               POC-ABS saja    AUC 0,6142   <- terbaik yg pernah dicatat
               POC + geometri  AUC 0,4387   -> BAWAH acak
             Fitur geometri mengodekan identitas subjek (72% varians fitur =
             antar-orang), bukan kondisi kecemasan. Menambahkannya menghancurkan
             sinyal lemah yg ada. Keputusan: fokus POC-ABS saja, sesuai judul.
Verifikasi : ./scripts/run_pipeline_v3.sh --dry-run ->
               stage 2: extract_features_poc_abs.py --roi-signals --baseline neutral
                        (tanpa --with-geometry)
               stage 4: _v3_full.pkl -> _v3_poc_temporal.pkl
               stage 5: within_subject_test.py x2 (poc + geo_temporal/POC-temporal)
               stage 6/7: --features _v3_poc_temporal.pkl
             grep: 0 referensi variabel geo/fused; 2 sisa kata "with-geometry"
             hanya di komentar.

TEMUAN YANG SENGAJA TIDAK DIPERBAIKI (dicatat supaya tidak hilang):
  `detect_roi_apex` menghitung `clip.onset_frame + indeks_sinyal`. Itu hanya
  benar kalau indeks sinyal == nomor frame clip-relatif.
    - mode `--baseline neutral` (dipakai pipeline): frame 1 menghasilkan baris DAN
      slot sinyal -> pemetaan 1:1 -> rumus itu BENAR. Tidak ada bug di sini.
    - mode `--baseline onset`: frame 1 sengaja dibuang dari keduanya -> seluruh
      nomor frame bergeser 1. Di situ rumusnya meleset.
  Sudah sempat ditulis perbaikan (daftar frame paralel), lalu DIREVERT karena:
  (a) no-op pada konfigurasi sekarang, (b) tabel apex tidak dikonsumsi training.
  Menambah kode mati hanya menambah permukaan bug. Catatan ini penggantinya.

KOREKSI CATATAN SEBELUMNYA (penting, sempat salah tulis):
  Saya sempat menulis bahwa alur berbasis-berkas ini "menghalangi live video" dan
  butuh ring buffer. Itu KELIRU - saya mencampur training dan inference.
  Yang benar: dataset ini memang REKAMAN, dan tujuannya melatih model dari rekaman
  itu untuk nanti dipakai di feed langsung. Itu alur yang normal dan benar.
  Pipeline ini adalah pipeline TRAINING; ia tidak perlu memproses feed langsung.
  Kebutuhan real-time (ring buffer, acuan netral bergerak) adalah urusan tahap
  INFERENCE terpisah, di luar lingkup repo ini. Tidak ada yang perlu diubah di sini.


### Iterasi 4.34 - KARAKTERISASI POC-ABS + 2 tabel eksperimen (apa yg diukur, bukan berapa banyak)
Tanggal    : 2026-10-08
Status     : SELESAI (riset + analisis + tabel). Training BELUM dijalankan.
Dokumen    : report/findings/poc-abs-karakterisasi.md (lengkap)
Ditambah   : experiments/features/apex/poc_signed_full.pkl    (E1, 20 fitur)
             experiments/features/apex/poc_dynamics_full.pkl  (E2, 180 fitur)

TEMUAN STRUKTURAL:
  1. Grid blok membuang 21-31% piksel ROI (mulut 31%, alis 26%, mata 21%).
     Resolusi spasial hanya 14-21 blok per ROI.
  2. Sudut/kuadran (tetha, label Q1-Q4) DIHITUNG lalu DIBUANG - tidak pernah
     jadi fitur. Informasi arah paling terkode hilang.
  3. Hanning window di poc.py adalah NO-OP: np.dot(hann, hann) menghasilkan
     SKALAR 3.0 (inner product), bukan matriks 2D. Phase correlation membagi
     dengan magnitudo, jadi pengali skalar hilang total. TERBUKTI: hasil
     identik bit-per-bit dengan tanpa window.
     TIDAK DIPERBAIKI karena diuji justru merugikan: pada 400 patch sintetis,
     window skalar = 100% tepat, window 2D = 69,8% tepat. Blok 9x9 terlalu
     kecil untuk window 2D (tepi di-nol-kan -> informasi hilang).
  4. neutral.png = median 10 frame pertama; bisa tidak netral kalau subjek
     belum tenang saat rekaman mulai.
  5. mean_x/mean_y dihitung atas SEMUA blok termasuk yang diam (nilai 0),
     jadi mencampur "berapa banyak blok bergerak" dengan "ke arah mana".

UJI SINYAL (semua gagal):
  Sinyal dasar (35): p<0,05 = 1/35 (harapan acak 1,75). FDR 0/35. AUC>0,60 = 0/35.
  Dinamika (185)   : p<0,05 = 20/185 (harapan 9,2) TAPI FDR 0/185, Bonferroni 0/185.
                     Permutasi acak-tanda (3000x): obs 21 vs null 8,8+-11,0 -> p=0,109.
                     AUC1 max 0,6464 vs null max 0,6431+-0,0249 -> p=0,40 (seleksi).
  Distribusi (std/iqr/skew) juga tetap didominasi identitas (0,62-0,79).
  Dominasi identitas median = 0,79 (fitur 79% "siapa orangnya").

EKSPERIMEN YANG DISIAPKAN (belum dijalankan):
  E1 arah bertanda saja  : poc_signed_full.pkl    -> 20 fitur
     (buang semua magnitudo; magnitudo = identitas 0,87, arah = 0,60)
  E2 dinamika saja       : poc_dynamics_full.pkl  -> 180 fitur
     (hanya rise/fall/ttp; kecemasan fenomena temporal)
  Jalankan:
    TRAIN_FEATURES=$PWD/experiments/features/apex/poc_signed_full.pkl   ./scripts/run_pipeline_v3.sh --from 6
    TRAIN_FEATURES=$PWD/experiments/features/apex/poc_dynamics_full.pkl ./scripts/run_pipeline_v3.sh --from 6
  Ekspektasi jujur: kemungkinan besar tetap acak. Keduanya belum pernah dicoba
  dan menyasar komponen berbeda secara prinsip, bukan variasi jumlah fitur.

CATATAN: pipeline ini TRAINING dari rekaman, dan itu benar. Kebutuhan real-time
(ring buffer, referensi netral bergerak) adalah urusan tahap INFERENCE terpisah.


### Iterasi 4.35 - E3: arah atas BLOK BERGERAK + sudut yg tadinya dibuang
Tanggal    : 2026-10-08
Status     : SELESAI (kode + verifikasi numerik). Ekstraksi BELUM dijalankan.
Diubah     : scripts/extract_features_poc_abs.py
               extract_roi_signal_row(): +5 sinyal per ROI (25 total):
                 mean_x_mov / mean_y_mov = arah dirata-ratakan HANYA atas blok
                   yang bergerak (mags>0). mean_x/mean_y lama mencampur
                   "berapa banyak blok bergerak" dgn "ke arah mana".
                 angle_cos / angle_sin  = rata-rata SIRKULAR sudut (bukan
                   aritmetik: 0 dan 359 derajat bukan 179,5). Dihitung ulang
                   dari atan2(Y,X), tidak bergantung pembulatan Quadran.
                 angle_R = panjang resultan, 0=arah acak .. 1=semua searah.
                   Mengukur KOHERENSI arah, info yg hilang di mean_x.
             scripts/build_temporal_features.py
               BASE_SIGNAL_RE: whitelist diperluas utk 5 sinyal baru.
               BUG YG DICEGAH: regex itu whitelist, jadi tanpa perubahan ini
               stage 4 akan DIAM-DIAM mengabaikan semua kolom E3 (tidak ada
               deskriptor temporal utk mereka, tanpa error apa pun).
Alasan     : Quadran sudah menghitung tetha (0-360) lalu membuangnya; hanya
             magnitude + X + Y yang dipakai. Sudut = arah paling terkode.
Verifikasi : (1) syntax OK utk kedua file.
             (2) Uji numerik logika baru (3 kasus sintetis):
                 - 2 blok bergerak (2,0) + 3 diam: mean_x(all)=0,80 (terencerkan)
                   vs mean_x_mov=2,00 (benar); angle_R=1,00 (benar)
                 - 4 blok bergerak 2 kanan + 2 kiri: mean_x_mov=0,00 dan
                   angle_R=0,00 -> R menandai arah TIDAK koheren
                 - sudut 0 derajat: cos=1,00 sin=0,00 R=1,00, rata-rata
                   sirkular = 0,0 derajat (benar)
             (3) regex diuji 11 nama kolom: 10 cocok benar, `max_m` sengaja
                 tidak cocok (memang dibuang pipeline).
             (4) Tabel lama TIDAK tertimpa: output E3 memakai --output nama baru.

PERINTAH (ekstraksi ~30 menit, lalu training):
  cd /home/finny/projects/Skripsi
  FEAT_WORKERS=3 FEAT_DATASET_ROOT=$PWD/output/apex_v2/dataset \
  FEAT_METADATA_PATH=$PWD/output/apex_v2/metadata.xlsx \
  .venv/bin/python scripts/extract_features_poc_abs.py --roi-signals --baseline neutral \
    --output experiments/features/apex/poc_abs_roi_signals_e3.xlsx
  .venv/bin/python scripts/build_feature_cache.py \
    --xlsx experiments/features/apex/poc_abs_roi_signals_e3.xlsx \
    --pkl  experiments/features/apex/poc_abs_roi_signals_e3_full.pkl
  .venv/bin/python scripts/build_temporal_features.py \
    --input  experiments/features/apex/poc_abs_roi_signals_e3_full.pkl \
    --output experiments/features/apex/poc_abs_roi_signals_e3_temporal.pkl --no-xlsx
  TRAIN_FEATURES=$PWD/experiments/features/apex/poc_abs_roi_signals_e3_temporal.pkl \
    ./scripts/run_pipeline_v3.sh --from 6

CATATAN: E3 menggantikan E1 (E3 mencakup arah bertanda + arah blok-bergerak +
sudut). E2 (dinamika saja) tetap berdiri sendiri.


### Iterasi 4.36 - Deteksi perubahan DALAM DIRI ORANG YANG SAMA + 2 bug (metrik & agregasi)
Tanggal    : 2026-10-08
Status     : SELESAI (kode + analisis terverifikasi). Training penuh BELUM dijalankan.
Diubah     : scripts/within_subject_test.py
               within_subject_diff_loso(): metrik utama diganti balanced accuracy +
               MCC. Sebelumnya melaporkan accuracy mentah padahal kelasnya 17:1,
               jadi angka "acc 1,0000" itu cuma "selalu tebak kelas mayoritas".
             scripts/run_loso.py
               AGG_KEYS['subject']: ['participant'] -> ['participant','phase'].
               aggregate_rows(): kolom yang sudah jadi kunci tidak di-agg lagi
                 (kalau tidak, reset_index gagal "cannot insert phase").
               --aggregate & --label-unit help: diperbaiki (klaim lama "semua
                 'before' berlabel anxiety" SALAH: 41/56 = 73%, bukan semua;
                 dan "'session' ... 10 subjek" SALAH: 18 subjek).

TEMUAN 1 - FORMULASI SELISIH (after-before) DEGENERATE, BUKAN SINYAL.
  Dari 18 subjek yang labelnya berubah, 17 turun (tinggi->rendah) dan HANYA 1
  naik. Jadi baseline mayoritas = 94,44% dan "akurasi tinggi" tidak berarti apa
  pun. Setelah metrik diperbaiki, MCC = +0,0000 di 5/5 keluarga fitur
  (v3 35 fitur, e3 30, temporal 185, dynamics 90, e3only 25). Nol informasi.

TEMUAN 2 - KONFOUND LABEL vs FASE (dari metadata, 56 subjek x 2 sesi).
  before : 41/56 anxiety_tinggi (73,2%)   after: 25/56 (44,6%)
  tabel silang before x after: 24/17/1/14
  Prediktor "fase saja" (before -> tinggi) = 64,29% vs baseline mayoritas 58,93%.
  Artinya label sangat tercampur urutan sesi (sebelum vs sesudah ujian).

TEMUAN 3 - FITUR MENGODEKAN IDENTITAS, BUKAN KECEMASAN.
  Same-subject nearest-neighbour retrieval (112 vektor sesi, acak 0,90%):
    v3 (35 fitur) 18,75%   |   e3only (30 fitur) 8,04%
  Per keluarga (e3, 112 sesi):
    mean_abs_x/y 26,79% (paling identitas) | magnitude 15,18%
    signed mean_x/y 5,36% | E3 angle 4,46% | E3 mov 3,57% (paling bebas identitas)
  Keluarga asli POC-ABS (mean|X|, mean|Y|) justru yang PALING terikat identitas,
  padahal geometri dibuang dari pipeline dengan alasan yang sama.

TEMUAN 4 - UJI DALAM-SUBJEK (18 subjek berubah, 36 baris, LOSO, acak 0,50).
    E3 mov 0,5833 | E3 angle 0,5833 | signed 0,5556 | abs dir 0,5000
    magnitude 0,4444 (di bawah acak) | ALL 0,5833
  Terbaik p 0,1692 (e3only, 25 sinyal). Tidak signifikan; tidak ada fitur lolos
  FDR 5% (0/30 di semua keluarga), kontrol juga 0.

VERIFIKASI:
  (1) py_compile OK (within_subject_test.py, run_loso.py).
  (2) aggregate_rows jalur default pipeline (--label-unit person) TIDAK berubah:
      56 baris, semua phase='after', 31 rendah / 25 tinggi.
  (3) Jalur --label-unit session: 112 baris (56 before + 56 after), 66 tinggi /
      46 rendah, 0 baris yang labelnya bertentangan dgn frame-nya sendiri
      (sebelum perbaikan: 56 baris dgn 18 campuran dua kondisi berlawanan).
  (4) Jalur clip tidak berubah: 7.026 baris, 370 kolom.

PERINTAH (jalankan ulang gerbang dalam-subjek, ~4 menit):
  cd /home/finny/projects/Skripsi
  for f in poc_abs_roi_signals_v3_full poc_abs_roi_signals_e3_full \
           poc_abs_roi_signals_v3_poc_temporal poc_dynamics_full poc_e3only_full; do
    .venv/bin/python scripts/within_subject_test.py \
      --features experiments/features/apex/$f.pkl \
      --out output/training/ws_${f} --permutations 200 | grep -E "LOSO|PERUBAHAN"
  done

CATATAN: pipeline default (--label-unit person) MEMBUANG 53.161 dari 97.808
baris (54%), yaitu SELURUH sesi 'before'. Itu pilihan sadar (menghindari
confound fase), bukan bug - tapi konsekuensinya N=56 sesi saja.


### Iterasi 4.37 - KOREKSI metrik gerbang (balanced accuracy degenerasi) + penjaga resume
Tanggal    : 2026-10-08
Status     : SELESAI (kode + verifikasi). Angka 4.36 yang dilaporkan sebagai
             "bal-acc 0,9412/1,0000" untuk uji selisih SUDAH SALAH dan diganti.
Diubah     : scripts/within_subject_test.py
               + loso_scores(): balanced accuracy/accuracy/MCC dgn label [0,1]
                 EKSPLISIT lewat confusion_matrix.
               + majority_label(): fallback kelas mayoritas.
               within_subject_loso() & within_subject_diff_loso(): fold dgn set
                 train SATU KELAS tidak lagi dibuang (dulu `continue`), tapi
                 diprediksi kelas mayoritas train. Output 2 sekarang "balanced
                 accuracy", bukan accuracy mentah.
             scripts/run_loso.py
               feature_fingerprint() -> run_fingerprint(): sidik jari resume kini
                 mencakup OPSI RUN, bukan cuma tabel fitur (dataset, label_unit,
                 aggregate, subject_norm, drop_features, imbalance,
                 variance_threshold, seeds, path config, dan HASH ISI config).
               DONE.json: `features_sha1` -> `run_sha1` + `run_key`.

TEMUAN 5 - BALANCED ACCURACY SAYA SENDIRI DEGENERASI (bug di perbaikan 4.36).
  Di 4.36 saya ganti accuracy -> balanced accuracy supaya tidak tertipu kelas
  mayoritas 17:1. Tapi loop LOSO masih `continue` saat train cuma 1 kelas.
  Akibatnya saat subjek minoritas (1 orang) jadi test, fold-nya DIBUANG, dan
  yang dievaluasi cuma 17 baris kelas mayoritas. `balanced_accuracy_score`
  tanpa label eksplisit lalu menghitung recall atas kelas yang ADA saja ->
  melaporkan 1,0000 (terlihat sempurna) padahal model TIDAK PERNAH menebak
  kelas minoritas. MCC 0,0000 di sebelahnya adalah petunjuk inkonsistensinya.
  Perbaikan: fold tidak dibuang, diprediksi kelas mayoritas train; metrik
  dihitung dgn confusion_matrix(labels=[0,1]).

HASIL GERBANG SETELAH DIPERBAIKI (5 keluarga, 200 permutasi):
  Formulasi SELISIH after-before (18 subjek, naik 1 : turun 17):
    v3 35        bal-acc 0,5000 | MCC +0,0000 | p 0,7264
    e3 30        bal-acc 0,5000 | MCC +0,0000 | p 0,7264
    temporal 335 bal-acc 0,5000 | MCC +0,0000 | p 0,8657
    dynamics 95  bal-acc 0,5000 | MCC +0,0000 | p 0,8209
    e3only 30    bal-acc 0,4412 | MCC -0,0857 | p 0,9005
    -> PERSIS acak. Nol informasi. (Angka 4.36 "0,9412/1,0000" = artefak.)
  Formulasi PERINGKAT dalam-subjek (36 baris, acak 0,50):
    e3only 0,6111 (p 0,1692) | v3 0,5833 (p 0,1642) | e3 0,5833 (p 0,1642)
    temporal 0,5000 (p 0,5970) | dynamics 0,4722 (p 0,5871)
  Uji berpasangan FDR 5%: 0/30 s/d 0/335 signifikan di SEMUA keluarga;
  grup kontrol juga 0. Tidak ada sinyal.

TEMUAN 6 - PENJAGA RESUME FOLD TIDAK MENCAKUP OPSI RUN (sebab "hasil tidak berubah").
  Run 13:36 hari ini melaporkan "STAGE 6 SELESAI. fold selesai: 56" dalam 7
  DETIK: seluruh 56 fold di-SKIP karena DONE.json ada. Sidik jari lama hanya
  menutup tabel fitur, jadi ganti --label-unit/--aggregate/--subject-norm/seeds
  TIDAK memaksa latih ulang -> hasil lama dilaporkan seolah hasil baru.
  Ini akar dari gejala "sudah diubah ini-itu tapi hasilnya sama".
  Verifikasi: run_key berbeda terdeteksi (label_unit & aggregate), deterministik
  untuk run_key sama, dan DONE.json lama (tanpa run_sha1) -> latih ulang.

VERIFIKASI:
  (1) py_compile OK (within_subject_test.py, run_loso.py).
  (2) Uji langsung: y_true 17x kelas 0 -> metrik lama bal-acc 1,0000;
      metrik baru bal-acc 0,5000 + MCC 0,0000 (benar).
  (3) Jalur default pipeline (--label-unit person) TIDAK berubah oleh fix
      AGG_KEYS: 56 baris, label/fase/target/nilai numerik IDENTIK antara
      kunci lama ['participant'] dan baru ['participant','phase'].
  (4) Jalur --label-unit session: 112 baris, 0 label bertentangan dgn frame.

KONSEKUENSI YANG HARUS DIKETAHUI: karena sidik jari berubah, run berikutnya
akan melatih ulang 56 fold (~1-2 jam), bukan skip. Hasil di
output/training/convat_apex_anxiety_loso_roi25_reg/summary.md yang ada sekarang
TETAP SAHIH untuk konfigurasi default (jalur person), karena fix agregasi
terbukti no-op di jalur itu.


### Iterasi 4.38 - AKAR "sinyal dulu ada": artefak SESI dari baseline onset + device CPU + log epoch
Tanggal    : 2026-10-08
Status     : SELESAI (kode + bukti terukur). Training penuh BELUM dijalankan.
Diubah     : scripts/run_loso.py
               + --device {auto,cpu,cuda}, DEFAULT cpu. Menyetel
                 CUDA_VISIBLE_DEVICES SEBELUM torch diimpor (lib.util.get_device
                 membaca torch.cuda.is_available()). '' = CPU.
               + --epochs-log: satu baris per fold per seed (ep terbaik, skor
                 train/val), karena --quiet menyembunyikan progres epoch.
               DONE.json seeds: + train_score.
             scripts/run_pipeline_v3.sh
               stage 6: + --device ${TRAIN_DEVICE:-cpu} + --epochs-log.
               HAPUS `export CUDA_VISIBLE_DEVICES=0` (dulu memaksa GPU).

TEMUAN 7 - SINYAL LAMA = ARTEFAK SESI (baseline onset), BUKAN KECEMASAN.
  Dua tabel lama diuji dgn gerbang dalam-subjek yang sama. Grup "kontrol" =
  subjek yang labelnya TIDAK berubah; di grup itu TIDAK BOLEH ada perbedaan
  sistematis. Kalau ada, efeknya efek sesi/waktu.
    output/apex + baseline ONSET   (poc_abs_roi_signals_full.pkl):
        berubah  20/25 fitur signifikan (FDR 5%)
        KONTROL  25/25 fitur signifikan  <-- SEMUA fitur
        |mean_diff| median: berubah 0,101 | kontrol 0,063
    output/apex + baseline NEUTRAL (poc_abs_roi_signals_neutral_full.pkl):
        berubah   0/25 ; KONTROL 0/25
  Bacaan: dgn acuan onset (frame pertama klip), fitur berbeda sistematis antara
  sesi before dan after untuk SEMUA orang, termasuk yang labelnya sama. Jadi
  "sinyal lemah" yang dulu terlihat itu mengukur SESI, bukan kecemasan. Acuan
  netral menghapus artefak itu, dan setelah bersih yang tersisa memang nol.
  Ini jawaban atas "kok dulu ada sinyal, sekarang tidak".

TEMUAN 8 - MODEL TIDAK BELAJAR (best_epoch 0-1 pada 70% seed).
  Dari 168 fold-seed: best_epoch 0 = 75, 1 = 43, 2 = 21, sisanya <20 total.
  Contoh fold 0: train acc 0,977 (hafal) vs val 0,545 (acak) -> early stopping
  berhenti di epoch 0-3. Artinya val tidak pernah membaik dari inisialisasi.
  Konsisten dgn AUC level-subjek 0,3974 (di bawah acak).
  Catatan: test_score tiap fold 0,0 atau 1,0 karena test = 1 subjek 1 label;
  itu bukan bug, hanya metrik per-fold tidak terdefinisi di protokol LOSO ini.

TEMUAN 9 - CRASH GPU. Mesin reboot ~16:31 (boot ke-8 hari itu); training 16:17-16:25
  selesai lalu mesin jatuh. lib/util.py:485 get_device() memakai CUDA bila
  tersedia, dan run_loso.py + pipeline mengekspor CUDA_VISIBLE_DEVICES=0, jadi
  tiap fold membuat konteks CUDA baru (56x3=168 konteks) di GTX 1650 Ti 4 GB.
  Beban itu tidak membeli apa pun: 44 baris train x <=660 fitur. Default
  diubah ke CPU.

VERIFIKASI:
  (1) py_compile + `bash -n` OK; --help menampilkan --device/--epochs-log.
  (2) 1 fold nyata dgn --device cpu --epochs-log:
        "Device  : cpu (CUDA disembunyikan dari torch)"
        "[0] OK aaisyah_... | s0 ep3 tr0.98 va0.55"
      -> CPU jalan, dan epoch terbaik + skor train/val kini terlihat di log.
  (3) --dry-run stage 6 memuat `--device cpu --epochs-log`.
  (4) Tabel lama diuji dgn gerbang yg sudah dikoreksi (temuan 7).

CATATAN: log orkestrasi `logs/pipeline_v3_*.log` lama terhapus saat verifikasi
(salah perintah `rm`). Log stage (stage1..stage7_*.log), summary.md, dan
DONE.json TIDAK terhapus; tiap run berikutnya membuat log pipeline-nya sendiri.

PERINTAH:
  cd /home/finny/projects/Skripsi
  ./scripts/run_pipeline_v3.sh                 # device CPU (default)
  TRAIN_DEVICE=cuda ./scripts/run_pipeline_v3.sh   # kalau memang mau GPU


### Iterasi 4.39 - Validasi tahap spotting dgn CAS(ME)^2 (Fokus A) + pipeline jadi importable
Tanggal    : 2026-10-09
Status     : SELESAI (kode + smoke test nyata). Run penuh BELUM dijalankan.
Diubah     : scripts/process_spotting_pipeline.py
               Blok eksekusi level-MODUL (rebuild metadata, spotting penuh,
               export_event_signals) dipindah ke main() + guard
               `if __name__ == '__main__'`. Dulu `import` file ini langsung
               menulis metadata.xlsx/klip (pernah menghapus metadata).
               Tidak ada logika spotting yang berubah.
             scripts/eval_spotting_casme2.py (BARU)
               Benchmark spotting POC-ABS vs ground truth CAS(ME)^2.
               Sinyal & detektor DIIMPOR dari process_spotting_pipeline, bukan
               disalin, jadi yang diukur pipeline ini apa adanya.

KONTEKS: user memilih Fokus A (pertahankan kecemasan sbg target, pakai CAS(ME)^2
hanya utk memvalidasi SPOTTING) + sedikit Fokus B (pisahkan macro vs micro).
Alasannya: label kecemasan terbukti tercampur fase dan fitur lebih kuat
mengodekan identitas (temuan 4.36-4.38), sedangkan tahap spotting belum pernah
diuji terhadap ground truth apa pun.

DATA: CAS(ME)^2 `rawvideo.rar` (6,95 GB, 97 avi) diekspor ke
/home/finny/datasets/casme2/rawvideo/.
  - `7z` build ini TIDAK punya codec RAR dan `unrar` tidak terpasang (butuh
    sudo) -> dipakai `libarchive-c` lewat venv (tanpa sudo).
  - Drive mentah 97% penuh (1,6 GB bebas), jadi diekspor ke /home (55 GB bebas).
  - Konvensi: dataset mentah di ~/datasets/<nama>/ (seperti anxiety_raw).
Ground truth: `code_final.xlsx` 356 ekspresi -> 308 beranotasi lengkap
(57 micro, 251 macro), 86 video, 22 subjek. Pemetaan nama ekspresi -> nama file
lewat sheet "naming rule 1/2"; diverifikasi 0 offset GT di luar jumlah frame video.

HASIL SMOKE TEST (2 video, 5 ekspresi - BUKAN angka final):
  recall 1,0000 | precision 0,1515 | F1 0,2632 | TP/FP/FN 5/28/0
  error apex median 6 frame | micro 1/1 terdeteksi (apex meleset 7 frame)
  -> detektor SENSITIF tapi TIDAK SPESIFIK: semua ekspresi GT ketemu, tapi
     memicu 28 event palsu. Ini angka ber-ground-truth pertama utk spotting ini.

VERIFIKASI:
  (1) py_compile OK (kedua berkas); `bash -n` pipeline tidak tersentuh.
  (2) Import safety: `import process_spotting_pipeline` kini hanya mencetak
      banner config, TIDAK menulis berkas.
  (3) Pipeline tetap jalan: dijalankan dgn SPOT_DATASET_ROOT palsu ->
      `main()` terpanggil dan berhenti di validasi path (FileNotFoundError).
  (4) GT: 308 ekspresi, 86 video, 0 offset di luar video.
  (5) Smoke test end-to-end 2 video -> summary.md/matched.csv/false_positives.csv.
  (6) Deteksi dijalankan SEKALI per video lalu dicocokkan per toleransi
      (versi pertama keliru memproses ulang video untuk tiap toleransi).

PERINTAH:
  cd /home/finny/projects/Skripsi
  .venv/bin/python scripts/eval_spotting_casme2.py            # 86 video, ~1 jam
  .venv/bin/python scripts/eval_spotting_casme2.py --limit 3  # uji cepat


### Iterasi 4.40 - FIX OOM: spotting memuat seluruh video ke RAM (crash saat run penuh)
Tanggal    : 2026-10-09
Status     : SELESAI (kode + bukti memori + kesetaraan bit). Run penuh BELUM.
Diubah     : scripts/process_spotting_pipeline.py
               + iter_video_frames(): generator baca frame satu per satu.
               + count_video_frames().
               build_roi_signals(): menerima list ATAU generator (+ frame_count),
                 dan TIDAK lagi menyalin semua frame ke grayscale di awal.
             scripts/eval_spotting_casme2.py
               detect_in_video(): memakai iter_video_frames, bukan load_video_frames.
               + --workers (default 3).

GEJALA: run penuh dihentikan mesin. Bukan crash Python dan BUKAN reboot -
proses dibunuh OOM killer:
  Oct 09 09:29:16 kernel: Out of memory: Killed process 46207 (python)
    total-vm:6253468kB, anon-rss:3765516kB
  Oct 09 09:32:07 kernel: Out of memory: Killed process 50593 (python)
  (uptime tetap jalan; Discord & Chrome ikut memicu oom-killer)
  swap terpakai 5,0 GB, load average 27.

AKAR MASALAH: `load_video_frames` memuat SEMUA frame jadi list numpy, lalu
`build_roi_signals` menyalinnya LAGI ke grayscale (`grays = [...]`). Video
CAS(ME)^2 sampai 4370 frame 640x480:
  4370 x 640 x 480 x 3 byte = 4,03 GB (list warna)
  + ~1,3 GB (salinan grayscale) = ~5,3 GB per worker
Dengan 4 worker = ~21 GB, padahal RAM 15 GiB. Video anxiety pendek (median 436
frame) jadi tidak pernah memicu ini; CAS(ME)^2 5-10x lebih panjang.

PERBAIKAN: untuk sinyal hanya perlu frame acuan + frame saat ini, jadi frame
di-STRIM. Puncak memori terukur pada video 4370 frame: 0,27 GB (dari ~5,3 GB),
yaitu ~20x lebih kecil -> 4 worker = ~1,1 GB.

VERIFIKASI:
  (1) py_compile OK kedua berkas.
  (2) KESETARAAN BIT: sinyal streaming vs list pada 1 video (1075 frame, 5 ROI)
      identik, maxdiff 0,0 di semua ROI.
  (3) END-TO-END TIDAK BERUBAH: smoke test 2 video sesudah fix menghasilkan
      matched.csv yang IDENTIK dengan sebelum fix (5 deteksi sama, error apex
      6/7/7/4/6 sama). Perbaikan ini murni memori, bukan perilaku.
  (4) Puncak memori 0,27 GB pada video 4370 frame (diukur dgn ru_maxrss).

CATATAN: pipeline utama TIDAK diubah alurnya - ia memang butuh frame utuh untuk
menyimpan klip event. Tapi karena build_roi_signals tidak lagi membuat salinan
grayscale, puncak memori pipeline juga turun (~1/3 dari sebelumnya).

PERINTAH:
  cd /home/finny/projects/Skripsi
  .venv/bin/python scripts/eval_spotting_casme2.py              # 86 video, ~15-25 mnt
  .venv/bin/python scripts/eval_spotting_casme2.py --workers 2  # kalau RAM sesak


### Iterasi 4.41 - Proposal: BAB I lengkap (1.1-1.5) + sitasi dibatasi 2017-2026
Tanggal    : 2026-10-09
Status     : SELESAI. BAB II-III masih placeholder (sesuai arahan user).
Diubah     : proposal/main.typ
               - 1.1 Latar Belakang ditulis ulang.
               - 1.2 Rumusan Masalah, 1.3 Batasan, 1.4 Tujuan, 1.5 Manfaat
                 dirapikan (naskah asli sudah ada isinya, hanya dirapikan
                 bahasanya dan dijadikan satu gaya penulisan).
             proposal/refs.bib
               - 3 entri pra-2017 DIHAPUS: ekman1992argument,
                 robinson2013impact, yan2014casme2.
               - 2 entri baru 2017-2026: hur2020anxiety, li2022mesurvey.
               - Header: aturan "terbit 2017-2026" dicatat.
             proposal/proposal.pdf (hasil compile)

ARAHAN USER: hanya BAB I, jangan tulis BAB II-III. Rentang sitasi maksimum
2017-2026. Tanpa em dash. Bahasa lebih sederhana tapi tetap akademik.

MASALAH YANG HARUS DISELESAIKAN: tiga sitasi inti di naskah lama terbit
sebelum 2017 (Ekman 1992 untuk emosi dasar, Robinson 2013 untuk beda fear vs
anxiety, Yan 2014 untuk CASME II). Ketiganya dipakai di kalimat yang penting,
jadi tidak bisa sekadar dihapus tanpa pengganti.

PENGGANTI (keduanya akses terbuka, terverifikasi):
  - hur2020anxiety (J. Neuroscience 40(41):7949-7964, 2020, PMC7548695)
    -> fear vs anxiety: ancaman pasti dan dapat diprediksi vs ancaman tidak
       pasti yang berlangsung lama dan memunculkan kewaspadaan berkelanjutan.
  - li2022mesurvey (IEEE TAFFC 13(4):2028-2046, 2022, CC BY 4.0)
    -> dataset micro-expression berbasis emosi dasar punya kelas cadangan;
       emosi kompleks tidak punya label sendiri sehingga sulit dipelajari.
  - Untuk daftar emosi dasar, dipakai @oh2018survey (2018) yang sudah ada.
  - CASME II sebagai dataset tetap disebut, sitasinya dialihkan ke li2022mesurvey
    supaya tidak ada entri pra-2017.

VERIFIKASI:
  (1) `typst compile main.typ proposal.pdf` sukses tanpa error (12 halaman).
  (2) PDF: 0 em dash. Semua sitasi ter-resolve (0 penanda "??").
  (3) Tahun di DAFTAR PUSTAKA: 2018, 2019, 2020, 2022, 2023, 2024, 2025, 2026.
      Tidak ada tahun < 2017.
  (4) Struktur BAB I: 1.1 Latar Belakang, 1.2 Rumusan Masalah, 1.3 Batasan
      Masalah, 1.4 Tujuan, 1.5 Manfaat. BAB II-III tetap "belum ditulis".
  (5) Screenshot halaman 1 dan 3 diperiksa (judul + awal BAB I).

CATATAN: BAB II dan BAB III sengaja TIDAK ditulis. Isi Tabel 3.1 (rentang skor
kuesioner) belum bisa diisi karena instrumen/skor belum tersedia di repo.


### Iterasi 4.42 - HASIL benchmark spotting CAS(ME)^2 + fix artefak false_positives
Tanggal    : 2026-10-09
Status     : SELESAI. Hasil run penuh sudah dibaca dan dilaporkan.
Diubah     : scripts/eval_spotting_casme2.py
               evaluate(): `all_fp` dan `all_fn` kini membawa `video_path`.
               main(): false_positives.csv kini memuat kolom `video`
                 (sebelumnya tidak, sehingga FP tidak bisa ditelusuri ke video
                 mana pun dan tidak bisa dianalisis).

HASIL RUN PENUH (86 video, 308 ekspresi ber-GT, 1647 deteksi, 0 video gagal):

  Toleransi 0 frame:
    precision 0,0971 | recall 0,5195 | F1 0,1637 | TP/FP/FN 160/1487/148
    error apex median 7 frame (mean 10,8; p90 28)
    macro (n=251): recall 0,5498 | micro (n=57): recall 0,3860
  Toleransi 5 frame:
    precision 0,1044 | recall 0,5584 | F1 0,1760 | TP/FP/FN 172/1475/136
    macro recall 0,5777 | micro recall 0,4737

TEMUAN 10 - DETEKTOR ADALAH PEAK-FINDER BERANGGARAN TETAP, BUKAN DETEKTOR.
  Rata-rata 19,2 deteksi per video (maks 25), sedangkan GT hanya median 2 per
  video. Angka 25 = 5 ROI x `top_k_apex=5` di scripts/spotting.py. Jadi detektor
  SELALU mengeluarkan hampir sebanyak kapasitasnya, apa pun isi videonya.
  Konsekuensinya: precision ~0,10 itu konsekuensi aritmetika dari 2 GT vs ~25
  deteksi, bukan bukti bahwa puncak yang dipilih salah tempat.
  Bukti pendukung: error apex hanya 7 frame (median) -> puncak yang dipilih
  MEMANG dekat ke ekspresi asli; yang salah adalah jumlahnya, bukan posisinya.
  FP tersebar rata di 5 ROI (286-315 tiap ROI), jadi tidak ada ROI yang
  mendominasi kesalahan.

TEMUAN 11 - RECALL MICRO 0,386 (22/57), MACRO 0,550 (138/251).
  Ini angka ber-ground-truth pertama untuk klaim "POC-ABS bisa
  micro-expression". Detektor menemukan sekitar 4 dari 10 micro-expression pada
  toleransi 0 frame, dan 5 dari 10 pada toleransi 5 frame. Klaim lama bahwa
  POC-ABS mencapai 94-96% pada CASME II @rosiani2020pocabs TIDAK sebanding:
  itu akurasi KLASIFIKASI emosi setelah ekspresi dipotong, sedangkan angka ini
  adalah recall DETEKSI pada video panjang yang belum dipotong.

CATATAN: benchmark ini mengukur detektor apa adanya. Parameter (`top_k_apex`,
`SPOT_PROM_REL`, threshold) di-tuning pada video anxiety 60 fps berdurasi
pendek, sedangkan CAS(ME)^2 30 fps dan 5-10x lebih panjang. Kalau parameter
diubah, jalankan dua kali (sebelum/sesudah) dan laporkan keduanya.

VERIFIKASI:
  (1) py_compile OK.
  (2) Smoke test 2 video setelah fix: deteksi 14 dan 19 (IDENTIK dengan sebelum
      fix) -> perbaikan murni artefak, bukan perilaku.
  (3) false_positives.csv kini memuat kolom `video`.


### Iterasi 4.43 - FIX: parameter detektor bisa diuji + cache sinyal + grid sweep
Tanggal    : 2026-10-09
Status     : SELESAI (kode + verifikasi kesetaraan). Sweep penuh BELUM dijalankan
             (user akan menjalankan sendiri).
Diubah     : scripts/process_spotting_pipeline.py
               + DetectParams (dataclass) + resolve_detect_params().
               _make_detector(), _height_threshold(), detect_events(),
               detect_events_per_roi() menerima `params` opsional.
               params=None => perilaku LAMA PERSIS (diverifikasi).
             scripts/eval_spotting_casme2.py
               Sinyal dihitung SEKALI lalu di-cache ke disk (npz), deteksi
               dijalankan ulang per kombinasi parameter.
               + --top-k, --prom-rel, --thresh (masing-masing menerima beberapa
                 nilai = grid), + --signal-cache / --no-cache.
               Ringkasan kini memuat tabel grid + detail kombinasi terbaik.

ALASAN: hasil 4.42 menunjukkan detektor mengeluarkan ~19 deteksi/video sedangkan
GT hanya ~2, dengan plafon 25 = 5 ROI x top_k_apex 5. Akar masalahnya parameter
pemilihan event, tapi parameter itu tidak bisa diuji tanpa mengubah perilaku
pipeline utama (dipakai bersama).

PENDEKATAN (sengaja): default pipeline TIDAK diubah. Mengubahnya akan
membatalkan seluruh klip + tabel fitur + hasil training yang sudah ada, padahal
nilai terbaiknya belum diketahui. Yang ditambahkan adalah kemampuan MENGUJI
parameter, bukan parameter baru.

BIAYA: sinyal POC-ABS (dlib + POC per frame) adalah bagian mahal, ~40 menit untuk
86 video. Sinyal TIDAK bergantung pada parameter deteksi, jadi dihitung sekali,
di-cache, lalu grid parameter hanya mengulang tahap deteksi. Terukur: run
2-video dengan cache = 2,4 detik (dari ~3 menit).

TEMUAN 12 - `prom_rel` TIDAK BINDING pada data ini.
  Menaikkan prominence (0,04 -> 0,20) memang mengurangi jumlah puncak mentah
  (mis. mulut 32 -> 27), TAPI karena top_k memotong ke 5 teratas, 5 puncak
  terkuat tetap sama. Jadi hasil akhir identik. Yang benar-benar mengikat
  adalah `top_k` dan mode ambang tinggi (meanstd vs mad).

VERIFIKASI:
  (1) py_compile OK (kedua berkas).
  (2) KESETARAAN jalur lama: detect_events_per_roi(sinyal) ==
      detect_events_per_roi(sinyal, resolve_detect_params(None)) -> 14 event
      identik. Nilai default yang di-resolve sama persis dengan global sekarang
      (top_k=5, prom_rel=0.04, thresh=meanstd, distance=1, min_phase_duration=2).
  (3) KESETARAAN end-to-end: benchmark dgn parameter default mereproduksi smoke
      test LAMA persis -> P=0,1515 R=1,0000 F1=0,2632, deteksi 14 dan 19.
  (4) Grid + cache jalan: 6 kombinasi pada 2 video selesai 2,4 detik.
  (5) `detect_events` (mode global) masih jalan: 5 event.
  (6) Pipeline tetap jalan sebagai skrip: main() terpanggil, berhenti di
      validasi path.
  (7) BUG yang ditemukan+diperbaiki saat verifikasi: `np.savez_compressed` ke
      NAMA file yang tidak berakhiran `.npz` menambahkan `.npz` sendiri sehingga
      file tmp tidak ada saat rename (FileNotFoundError). Ditulis lewat file
      object sekarang.

INDIKASI AWAL (2 video, BUKAN angka final): top_k=1 -> F1 0,4615 vs top_k=5
-> 0,2632. Perlu sweep penuh untuk memastikan.

PERINTAH (sweep penuh; sinyal 86 video ~40 menit sekali, lalu tiap grid ~detik):
  cd /home/finny/projects/Skripsi
  .venv/bin/python scripts/eval_spotting_casme2.py \
    --top-k 1 2 3 4 5 --prom-rel 0.04 --thresh meanstd mad


### Iterasi 4.44 - FIX: benchmark tidak lagi bergantung driv eksternal + summary thresh
Tanggal    : 2026-10-09
Status     : SELESAI. Sweep penuh sedang berjalan.
Diubah     : scripts/eval_spotting_casme2.py
               DEFAULT_GT diarahkan ke salinan lokal
               /home/finny/datasets/casme2/annotations/casme2_code_final.xlsx
               (sebelumnya file di driv "/run/media/finny/New Volume/...").
               Ringkasan: baris "default pipeline (pembanding)" kini memuat
               `thresh` juga (sebelumnya tidak, padahal thresh ikut di-grid).

MASALAH: user menjalankan sweep dan gagal dengan
  "ground truth tidak ditemukan: /run/media/finny/New Volume/.../code_final.xlsx"
Driv eksternal (nvme0n1p7) sudah LEPAS SENDIRI tiga kali hari ini. Video CAS(ME)^2
sudah disalin ke /home sejak awal (4.39), jadi hanya file anotasi yang masih
bergantung driv.

AKAR MASALAH + PERBAIKAN: file GT hanya 35 KB dan TIDAK pernah berubah, jadi
disalin ke /home/finny/datasets/casme2/annotations/ (checksum md5 diverifikasi
identik: 5b372a4c46740706562b37d598192f08). Setelah ini seluruh benchmark
(video + anotasi) berjalan tanpa driv sama sekali.

VERIFIKASI:
  (1) py_compile OK.
  (2) Driv di-UNMOUNT sengaja, lalu benchmark dijalankan `--limit 1`:
      berhasil, GT terbaca dari /home, summary.md terbentuk.
  (3) Salinan GT: md5 identik dengan aslinya, pandas bisa membaca (356 baris).

CATATAN: ini juga sebabnya `udisksctl mount -b /dev/nvme0n1p7` muncul di
beberapa perintah sebelumnya. Mulai sekarang benchmark spotting TIDAK butuh
perintah itu; hanya pipeline utama (spotting video mentah) yang butuh driv.


### Iterasi 4.45 - HASIL sweep + DIAGNOSIS: sinyal bagus, PEMILIHAN PUNCAK yang gagal
Tanggal    : 2026-10-09
Status     : SELESAI (sweep 86 video + 5 diagnostik). Tidak ada perubahan default.
Diubah     : (tidak ada kode produksi; hanya analisis)

HASIL SWEEP (86 video, 308 ekspresi GT, 10 kombinasi, cache sinyal dipakai):
  top_k=1 meanstd : P 0,1838 R 0,2208 F1 0,2006  <- TERBAIK   (det/video 4,3)
  top_k=1 mad     : P 0,1862 R 0,2110 F1 0,1979              (4,1)
  top_k=2 meanstd : P 0,1386 R 0,3182 F1 0,1931              (8,2)
  top_k=3 meanstd : P 0,1158 R 0,3929 F1 0,1789              (12,2)
  top_k=4 meanstd : P 0,1001 R 0,4416 F1 0,1632              (15,8)
  top_k=5 meanstd : P 0,0971 R 0,5195 F1 0,1637              (19,2)  <- default
  F1 TURUN MONOTON terhadap top_k. Semua kombinasi buruk (F1 <= 0,20).
  Catatan: smoke test 2 video sebelumnya menyarankan F1 0,4615 utk top_k=1;
  angka itu TIDAK bertahan di 86 video (0,2006). Sampel kecil menyesatkan.

DIAGNOSIS 1 - BUKAN sekadar plafon top_k. Bahkan dgn pencocokan paling longgar
  (GT dianggap kena kalau ADA satu deteksi beririsan, banyak-ke-satu), recall
  plafon hanya 0,2370 (73/308) pada top_k=1. Jadi 76% ekspresi tidak punya
  deteksi beririsan sama sekali. Jarak apex GT ke deteksi terdekat: median 131
  frame, p75 324, p90 677. Deteksi ada di tempat yang salah, bukan cuma terlalu
  banyak.

DIAGNOSIS 2 - DRIFT ADA TAPI BUKAN PENYEBABNYA.
  Sinyal POC-ABS (vs frame-0) naik di 93% video (median +0,199; mean +0,252);
  durasi video median 2305 frame (77 s). Tapi setelah di-detrend
  (rolling-median 101), coverage justru TURUN 0,2403 -> 0,2078 dan jarak
  median naik 131 -> 154. Jadi menghapus tren tidak memulihkan puncak.
  Window smoothing sudah tetap 7 frame (bukan skala panjang sinyal), jadi itu
  juga bukan penyebabnya.

DIAGNOSIS 3 - SINYALNYA BAGUS. Ini temuan terpenting.
  Nilai sinyal pada frame apex GT, dibandingkan seluruh video (persentil):
    median persentil = 0,988   (acak = 0,50)
    proporsi > 0,90  = 0,929 ;  > 0,95 = 0,812
  z-score sinyal pada apex GT: median 1,683; 75,6% punya z > 1,0.
  Artinya POC-ABS MEMANG memuncak di lokasi ekspresi. Sinyalnya informatif.

DIAGNOSIS 4 - RANTAI FILTER: yang membunuh adalah `top_k`.
  konfigurasi                        coverage   det/video
  tanpa filter (semua local max)      1,0000     2773,5
  height = mean+std                   0,9870      735,6
  height + prominence 0,04            0,9870      623,3
  height + prom + top_k=5 (SEKARANG)  0,4870       25,0
  height + prom + top_k=1             0,2208        5,0
  Dgn height+prominence saja, 98,7% ekspresi punya puncak yang beririsan.
  `top_k` memotongnya jadi 48,7% (top_k=5) atau 22,1% (top_k=1).
  CATATAN PENTING: coverage 0,987 pada 623 puncak/video itu sebagian besar
  TRIVIAL (623 puncak atas ~2300 frame = satu puncak tiap 3,7 frame, jadi
  hampir semua lokasi tertutup). Yang bermakna adalah penurunan akibat top_k.

DIAGNOSIS 5 - TIDAK ADA SKOR PUNCAK YANG MEMISAHKAN EKSPRESI.
  Untuk tiap GT, puncak beririsan terbaik diberi peringkat relatif (0 = skor
  tertinggi) di antara semua puncak ROI itu:
    nilai mentah        : median 0,173 | dalam 4% teratas 21,9% | 10%: 36,9%
    prominence lokal 15 : median 0,171 | 4% teratas 20,9%      | 10%: 36,8%
    z lokal 101         : median 0,168 | 4% teratas 14,5%      | 10%: 31,6%
  Puncak ekspresi hanya "sedikit lebih tinggi" dari ~125 puncak lain per ROI
  (median di peringkat ~17%), dan tidak ada skor (mentah, prominence, z lokal)
  yang memperbaikinya. Itu sebabnya anggaran kecil (top_k) selalu kehilangan
  sebagian besar ekspresi.

KESIMPULAN JAWABAN PERTANYAAN "apakah spotting terbukti jalan di CAS(ME)^2?":
  TIDAK. F1 terbaik 0,20. TAPI kegagalannya BUKAN di sinyal: POC-ABS memuncak
  di 93% lokasi ekspresi (persentil 0,988). Kegagalannya di PEMILIHAN PUNCAK:
  ~125 puncak per ROI, dan puncak ekspresi tidak terpisah jelas dari puncak
  gerakan lain (median peringkat 17%), sehingga anggaran top_k apa pun
  mengorbankan salah satu (precision atau recall) dan F1 mentok ~0,20.

ARAH PERBAIKAN (belum dikerjakan): masalah ini adalah masalah PEMERINGKATAN,
  bukan masalah ambang. Yang perlu adalah penilai puncak yang benar-benar
  memisahkan ekspresi dari gerakan lain (mis. klasifikasi puncak dgn fitur
  lokal: bentuk rise/fall, durasi, simetri antar-ROI, koherensi antar-ROI),
  bukan menggeser top_k atau threshold. Menggeser top_k sudah terbukti tidak
  cukup (seluruh kurva F1 di bawah 0,20).

EVIDENCE: logs/diag_spotting.log, logs/diag2.log, logs/detrend.log,
  logs/sig_test.log, logs/filter_test.log, logs/rank_test.log,
  output/training/spotting_casme2/summary.md


### Iterasi 4.46 - PLATO F1 ~0,20: diuji 7 arah, semuanya mentok. Bukan tuning lagi.
Tanggal    : 2026-10-09
Status     : SELESAI (diagnostik menyeluruh). Tidak ada perubahan default.
Diubah     : + scripts/rank_peak_casme2.py      (bandingkan skor peringkat puncak)
             + scripts/probe_signal_casme2.py    (mean/max/count x abs/seq)
             + scripts/probe_smoothing_casme2.py (perataan & ambang)
             + scripts/probe_learned_rank_casme2.py (pembelajar memisahkan puncak)

TUJUAN: user minta "perbaiki sampai bagus". Jadi diuji SEMUA tuas yang masuk akal.

YANG DIUJI DAN HASILNYA (semua memakai cache sinyal; F1 pembanding pipeline
top_k=5 = 0,1637 dan top_k=1 = 0,2006):

1. PERINGKAT PUNCAK HANDCRAFTED (86 video, anggaran 3,6 deteksi/video = setara
   kepadatan GT). F1 terbaik hanya 0,1748:
     width 0,1748 | z 0,1656 | val_x_sup 0,1534 | prom_rel 0,1411
     val (dipakai sekarang) 0,1319 | sup 0,1135 | prom 0,1074
   -> tidak ada skor sederhana yang mengalahkan baseline secara berarti.

2. AGREGASI SINYAL (mean vs max vs count) x ACUAN (frame-0 vs frame sebelumnya),
   4 video. Median peringkat puncak ekspresi 0,065-0,274; variasinya antar-video
   lebih besar dari beda antar-konfigurasi. Tidak ada pemenang jelas.

3. PERATAAN TEMPORAL + AMBANG (86 video, grid 4 window x 3 ambang):
     win  7 hk1.0: 736 puncak/video, coverage 0,987, rank 0,044
     win  7 hk2.0: 165 puncak/video, coverage 0,870, rank 0,169
     win  7 hk3.0:  33 puncak/video, coverage 0,490, rank 0,219
   TEMUAN PENTING: menaikkan ambang MEMPERBURUK peringkat ekspresi
   (0,044 -> 0,219). Artinya puncak ekspresi BUKAN puncak terkuat; menaikkan
   ambang membuang ekspresi lebih dulu daripada derau. Tidak ada window yang
   memperbaiki.

4. PERBESAR ROI 3x (hipotesis kuantisasi sub-pixel): coverage tetap ~1,0 tapi
   persentil apex TURUN 0,999 -> 0,977 dan puncak BERTAMBAH 435 -> 472.
   Kuantisasi whole-pixel BUKAN penyebab utama.

5. BLINK (1.185 anotasi blink CAS(ME)^2): puncak di dalam blink 3.280 (rate TP
   0,143) vs di luar 50.320 (0,060). Blink menyumbang hanya 5,6% FP. Bukan
   penyebab utama. (26,9% GT ekspresi memang beririsan blink.)

6. DRIFT & ARTEFAK AWAL: sinyal naik di 93% video (median +0,199) tapi detrend
   justru memperburuk (coverage 0,2403 -> 0,2078). Puncak 5% terkuat di 5%
   pertama video = 5,0% vs GT 1,0% -> artefak ada tapi kecil.

7. PEMBELAJAR MEMISAHKAN PUNCAK (31 fitur multi-ROI + konteks temporal,
   GroupKFold per video, 53.600 kandidat, 6,5% positif):
     logistic AUC 0,6776 | gbdt AUC 0,6706
     Kurva F1 terbaik dari skor pembelajaran: 0,2047 (pada 80 kandidat/video)
   -> HANYA 0,004 di atas baseline top_k=1 (0,2006). Bahkan model yang belajar
      dari label CAS(ME)^2 tidak bisa mengangkat F1 secara berarti.

KESIMPULAN: F1 ~0,20 adalah PLAFON untuk sinyal POC-ABS (magnitudo) + pemilihan
puncak, baik handcrafted MAUPUN pembelajaran dengan fitur ROI. Ini bukan lagi
masalah tuning parameter. Sebabnya terukur: video berisi ~700 puncak gerak,
ekspresi hanya ~3,6 per video, dan puncak ekspresi TIDAK lebih kuat dari
gerakan lain (menaikkan ambang justru membuangnya lebih dulu).

YANG SUDAH DIELIMINASI (jangan diulang): top_k, threshold, prominence,
perataan, agregasi mean/max/count, acuan frame-0 vs berurutan, perbesaran ROI,
drift, artefak awal, blink.

ARAH YANG TERSISA (belum dikerjakan):
  (a) Fitur per-kandidat yang LEBIH KAYA: pakai seluruh vektor fitur POC-ABS
      yang sudah dihitung pipeline (mean_x, mean_y, sudut, koherensi per ROI),
      bukan hanya magnitudo 5 ROI. Belum diuji; ini satu-satunya tuas fitur
      yang belum dicoba.
  (b) Ubah peran spotting: jadikan GENERATOR KANDIDAT recall-tinggi
      (coverage 0,987 pada 736 kandidat/video) dan biarkan TabR (model yang
      sudah ada di metode) yang mendiskriminasi. Ini konsisten dengan arsitektur
      two-stage spotting->recognition di literatur.
  (c) Terima temuan sebagai KARAKTERISASI metode (POC-ABS bagus untuk mendeteksi
      GERAKAN, bukan untuk memeringkat ekspresi emosional) dan laporkan apa
      adanya. Ini jujur dan tetap kontribusi.

EVIDENCE: output/training/{rank_casme2,probe_smooth_casme2,learned_rank_casme2}/,
  logs/{rank_peak,probe_signal,probe_smooth,probe_learned}.log


### Iterasi 4.47 - TUAS TERAKHIR BERHASIL: fitur arah+koherensi naikkan F1 0,20 -> 0,27
Tanggal    : 2026-10-09
Status     : SELESAI. Kemajuan nyata tapi BELUM "bagus". Default pipeline tidak diubah.
Diubah     : + scripts/probe_rich_features_casme2.py

HIPOTESIS YANG DIUJI: skor handcrafted dan pembelajar atas MAGNITUDO 5 ROI
sama-sama mentok F1 ~0,20 (4.46). Tetapi pipeline sudah menghitung BANYAK sinyal
per ROI, bukan cuma magnitudo: arah bertanda (mean_x, mean_y) dan koherensi
sudut (angle_R). Arah/koherensi mungkin membedakan ekspresi emosional dari
gerakan lain (bicara/menelan/blink), yang magnitudonya lebih besar.

HASIL (15 video, 8.580 kandidat, 747 positif = 8,7%):
  Fitur kaya (61 fitur: 6 sinyal x 5 ROI x {nilai, z-lokal} + sup):
    gbdt AUC = 0,7183   (pembanding magnitudo-5-ROI: 0,6706)  -> +0,048
    F1 terbaik = 0,2702 pada 80 kandidat/video (pembanding: 0,2047) -> +0,065
  Kurva F1 vs anggaran:
    3,6/video: P 0,5185 R 0,0375 F1 0,0699
    20/video : P 0,3800 R 0,1526 F1 0,2178
    40/video : P 0,2900 R 0,2329 F1 0,2584
    80/video : P 0,2192 R 0,3521 F1 0,2702  <- terbaik
    160/video: P 0,1758 R 0,5649 F1 0,2682

BACAAN:
  - Ada informasi pembeda di fitur ARAH dan KOHERENSI yang tidak ada di
    magnitudo. Ini arah yang benar.
  - TAPI F1 0,27 masih jauh dari "bagus" (literatur ME spotting 0,4-0,7, dan
    itu memakai jaringan spasiotemporal dalam, bukan fitur handcrafted).
  - F1 terbaik butuh 80 kandidat/video, sedangkan GT hanya 3,6/video. Jadi
    masih ~22 kandidat palsu per ekspresi nyata.
  - Pada anggaran yang setara kepadatan GT (3,6/video), F1 hanya 0,0699.

STATUS JAWABAN "apakah spotting sudah bagus di CAS(ME)^2?": BELUM.
  Namun sekarang bukan lagi "mentok di 0,20": kombinasi fitur arah+koherensi
  sudah membuktikan ada ruang, dan arah pengembangannya jelas (perkaya fitur
  per-kandidat + pengklasifikasi, bukan geser ambang).

LANGKAH BERIKUT YANG DIUSULKAN (belum dikerjakan):
  1. Jalankan uji fitur kaya pada SELURUH 86 video (bukan 15) untuk angka final.
  2. Analisis kepentingan fitur: mana dari mean_x/mean_y/angle_R/max_m/
     motion_count yang paling menyumbang, supaya fokus.
  3. Ganti klasifikasi PER-PUNCAK dengan klasifikasi JENDELA (sliding window):
     puncak hanya memberi satu titik waktu, sedangkan ekspresi punya profil
     temporal (naik-cepat, apex, turun-cepat). Ini pendekatan standar di
     literatur ME spotting dan belum dicoba di repo ini.

EVIDENCE: output/training/rich_rank_casme2/candidates.csv, logs/probe_rich.log


### Iterasi 4.48 - KESIMPULAN JUJUR: klasifikasi jendela TIDAK menyelamatkan spotting
Tanggal    : 2026-10-09
Status     : SELESAI. Verdict negatif, tapi bersih dan terukur. Default pipeline tidak diubah.
Diubah     : + scripts/rich_signals_casme2.py     (hitung + cache sinyal kaya 86 video)
             + scripts/window_spot_casme2.py       (klasifikasi jendela + protokol jujur)
             + scripts/rank_rich_casme2.py         (kandidat puncak, fitur kaya, semua video)

TUGAS DARI USER: "do 1 and 3" = (1) jalankan uji fitur kaya di SEMUA 86 video,
(3) ganti klasifikasi per-puncak dengan klasifikasi JENDELA.

HASIL (86 video, 308 ekspresi, GroupKFold per video, TIDAK pernah lihat video uji):

  Pembanding (semua di 86 video):
    pipeline top_k=5 (default)              F1 0,1637
    pipeline top_k=1                        F1 0,2006
    puncak + fitur kaya                     AUC 0,6686 | F1 0,2156

  Klasifikasi JENDELA (fitur kaya, ambang dipilih di data latih = jujur):
    window=64  AUC 0,6492 | F1 longgar 0,3715
    window=96  AUC 0,6442 | F1 longgar 0,4281
    window=128 AUC 0,6296 | F1 longgar 0,4068

  Sekilas F1 naik 0,20 -> 0,43 (dua kali lipat). TERNYATA ARTEFAK.

PEMERIKSAAN KEJUJURAN YANG MEMBONGKARNYA (window=96):
    durasi event deteksi : median 209 frame
    durasi GT            : median  29 frame     -> event 7x terlalu panjang
    syarat tumpang tindih diperketat ke IoU >= 0,5:
        P 0,0058 | R 0,0065 | F1 0,0061     <- praktis nol
    lokalisasi (jarak pusat event ke apex GT): median 172 frame
        <=10 frame: 5,5% | <=20: 12,0% | <=40: 22,7% | <=80: 36,0%

  Bacaan: F1 0,43 itu datang dari event yang dibuat SANGAT panjang sehingga
  hampir selalu "beririsan" dengan GT, ditambah aturan pencocokan yang hanya
  butuh beririsan. Begitu tumpang tindih diukur wajar (IoU >= 0,5), hasilnya
  nol. Pusat event pun meleset 172 frame (5,7 detik) dari apex sebenarnya.

VERDICT: tahap spotting TIDAK bekerja pada CAS(ME)^2. Bukan masalah sinyal
(sinyal memuncak di ekspresi, persentil 0,988), bukan masalah ambang, dan bukan
masalah ukuran jendela. Metodenya tidak melokalisasi ekspresi dengan cukup tepat.

DUA JEBAKAN METODOLOGI YANG DITEMUKAN DAN DITUTUP (ini pelajaran penting):
  1. SUBSET KECIL MENYESATKAN. window=16 memberi AUC 0,71 pada 20 video tapi
     0,60 pada 86. Semua angka di 4.47 (F1 0,27 pada 15 video) ikut terlalu
     optimistis; angka jujurnya 0,2156.
  2. AMBANG TIDAK BOLEH DIPILIH DARI DATA UJI. Menyapu ambang di prediksi uji
     lalu melaporkan F1 terbaik adalah seleksi bocor. Skrip sekarang memilih
     ambang di sub-split data LATIH tiap fold (--threshold-mode inner, default).
     Efeknya terukur: posthoc 0,4453 vs inner 0,4281 pada window=96.
  3. PENCocokan "BERIRISAN" TERLALU LONGGAR bila durasi event tidak dikontrol.
     Ditambahkan pemeriksaan IoU >= 0,5 + statistik durasi + lokalisasi.

CATATAN: pada anggaran setara kepadatan GT (3,6 deteksi/video) metode puncak
memberi F1 0,0523; pada 80/video 0,2156. Jadi trade-off precision/recall tetap
tidak menguntungkan di titik mana pun.

EVIDENCE: output/training/{spotting_casme2,rank_rich_full,window_honest_w64,
  window_honest_w96}/summary.md, logs/{final7,final8,rich_signals}.log


### Iterasi 4.49 - AUDIT + DEEP DIVE: ternyata ada DUA REGRESI di inti spotting
Tanggal    : 2026-10-09/10
Status     : SELESAI. F1 spotting CAS(ME)^2 0,1637 -> 0,3192 (tervalidasi split subjek).
Diubah     : ~ apex/apex_smoother.py      (window tetap 7 -> 3% adaptif)
             ~ apex/apex_phase.py         (find_top_k_apex: parameter `ranking`)
             ~ scripts/process_spotting_pipeline.py (SPOT_SIGNAL_MODE default
                                          global_mean, SPOT_RANKING prominence)
             ~ scripts/eval_spotting_casme2.py    (ikut SPOT_SIGNAL_MODE)
             ~ scripts/run_pipeline_v3.sh         (override V3_FEAT_TAG/V3_GATE_TAG)
             + scripts/audit_*.py                 (9 skrip audit)

TUGAS DARI USER: "stop being pessimistic, if the before can do it so can we,
deep dive this shit" + "full audit on the codebase on stuff we change since the
original".

TEMUAN KUNCI: logika spotting ASLI tidak ada di file .py mana pun.
`preprocess-anxiety/spotting.py` (versi asli) hanya stub NotImplementedError;
logika sesungguhnya ada di notebook `process_all_datasets.ipynb`. Jadi
`scripts/process_spotting_pipeline.py` adalah REIMPLEMENTASI, dan diff terhadap
backup 2026-08-25 menemukan 4 divergensi perilaku.

Notebook punya TIGA generasi:
  Gen 1 `micro_expression_spotting.ipynb`  : savgol TETAP 28, find_peaks
      (prominence=0) TANPA height, urut PROMINENCE, top 3
  Gen 2 `..._v2.ipynb` / `..._v2 Casme.ipynb`: ApexSmoother 5% clamp 31, urut NILAI
  Gen 3 `process_all_datasets.ipynb`       : = gen 2 + agregasi global

Pipeline memakai gen 2/3 TAPI membuang dua hal dari gen 1 -> dua regresi:

REGRESI 1 - agregasi per-ROI (bukan global). Plafon deteksi jadi 5 ROI x top_k:
  19,2 deteksi/video untuk GT 3,6. F1 0,1637.
  -> global: 5,0 deteksi/video, F1 0,2141.

REGRESI 2 - peringkat puncak menurut NILAI (bukan prominence) + window tetap 7
  (bukan 5%/28). Puncak ekspresi sering BUKAN puncak tertinggi (drift lebih
  tinggi), jadi height=mean+std + peringkat nilai membuangnya.
  -> window 3% + prominence: F1 0,2141 -> 0,3179.

  Efek terpisah (86 video, toleransi 0, top_k=5):
    tetap 7 / nilai        F1 0,2141
    28 tetap / nilai       F1 0,2602      <- efek WINDOW
    28 tetap / prominence  F1 0,3144      <- efek PERINGKAT
    3% adaptif / prominence F1 0,3179     <- gabungan

  VALIDASI SPLIT SUBJEK (pilih di satu paruh subjek, ukur di paruh lain):
    A->B: 3%/prominence/k5, train 0,3202 -> TEST 0,3152
    B->A: 3%/prominence/k5, train 0,3152 -> TEST 0,3202
    pembanding pipeline lama: 0,2061-0,2206
  Kedua fold memilih konfigurasi SAMA, test ~ train -> bukan overfitting.

BUKTI ACUAN FRAME-0 BUKAN REGRESI (jangan dikembalikan ke berurutan):
  Uji sintetis: POC mencari pergeseran BILANGAN BULAT; pada 30 fps gerakan
  antar-frame micro-expression sub-piksel -> tak terlihat.
    2 px / 8 frame : abs 0,364 vs seq 0,099
    5 px / 20 frame: abs 1,259 vs seq 0,071
  Nyata (41 video): P@5 abs 0,1007 vs seq 0,0470.

HASIL AKHIR (86 video, toleransi 0, default pipeline):
  sebelum (per-ROI/7/nilai)          P 0,0971 R 0,5195 F1 0,1637  det/v 19,2
  + agregasi global                  P 0,1837 R 0,2565 F1 0,2141  det/v  5,0
  + 3% adaptif + prominence          P 0,2753 R 0,3799 F1 0,3192  det/v  4,9
  top_k=4 (terbaik)                  P 0,3079 R 0,3409 F1 0,3236  det/v  4,0
  F1 micro ikut naik (0,1250 -> 0,2342 pada top_k=4).

KEJUJURAN: window panjang membuat durasi event memanjang (median 60 vs GT 28),
tapi F1 dengan IoU >= 0,5 ikut naik 0,071 -> 0,139, jadi bukan sekadar event
yang dipanjangkan.

SANITY CHECK REGIME 60 fps (16 klip kecemasan nyata), sebelum regenerasi:
  drift   : hi/lo 4,087 (abs) vs 3,891 (lag30) -> TIDAK didominasi drift
  window  : tetap 7 = 73 puncak, 3% = 71 puncak, event sama-sama 5/klip
  durasi  : tetap 7 median 10 frame, 3% median 14 (mikro 60fps = 2,4-12)
  -> parameter baru aman dipakai di pipeline kecemasan.

KOREKSI: klaim "dominasi identitas" (poc-abs-karakterisasi.md, median 0,79)
TIDAK bebas dari masalah spotting - `poc_abs_roi_signals_v3_full.pkl` punya
kolom event_clip (6.473 klip, 0 null), jadi fitur itu dihitung DI DALAM klip
event hasil spotting lama. Angka 0,79 juga tidak bisa direproduksi (eta-kuadrat:
peserta 0,030; sesi 0,047). Perlu diukur ulang pada data baru.

EVIDENCE: report/findings/audit-spotting-casme2.md,
  output/training/{audit_agg_f1_casme2,audit_peak_rank_casme2,
  audit_window_sweep_casme2,audit_anxiety_regime}/summary.md


### Iterasi 4.50 - REGENERASI pipeline kecemasan dengan spotting yang diperbaiki
Tanggal    : 2026-10-10
Status     : DIJALANKAN. Parameter deteksi berubah -> semua klip + fitur lama
             TIDAK BERLAKU LAGI dan harus dibuat ulang.
Diubah     : (tidak ada kode baru; memakai hasil Iterasi 4.49)

ALASAN: hasil LOSO "POC-ABS tidak membawa sinyal kecemasan" dihitung dari fitur
yang diekstrak dari klip event hasil spotting yang rusak (12,7 event/sample).
Tidak bisa disimpulkan apa pun sebelum fiturnya datang dari event yang benar.

ISOLASI: keluaran lama TIDAK disentuh. Semua ke direktori/tag baru:
  V3_RAW_ROOT=/home/finny/datasets/anxiety_avi  (salinan lokal 560 .avi, 9,5 GB;
      drive eksternal 97% penuh dan lepas-mount sendiri)
  V3_OUT_ROOT=output/apex_fixed
  V3_FEAT_TAG=poc_abs_roi_signals_v3fixed
  V3_GATE_TAG=within_subject_v3fixed
  LOSO_DATASET=convat_apex_anxiety_loso_v3fixed

VERIFIKASI FORMAT (560 video): event per sample turun 12,7 -> ~4,7, nama klip
  `event_XXXXX-XXXXX_global` (dulu `_alis_kanan` dll), neutral.png tersimpan,
  tiap event punya frame apex.

HASIL (semua stage 1-7 selesai 10:10):

  Spotting : metadata 7.094 -> 2.647 baris (12,7 -> 4,8 event/sample),
             region semua `global`, durasi median 11 -> 17 frame.
  Fitur    : 97.808 -> 62.955 baris frame, 60 sinyal (sama), 0 error.

  GATE WITHIN-SUBJECT (uji paling bersih: orang sama, label beda):
                     lama            -> baru
    per-frame   : BA 0,5833 p 0,1642 -> BA 0,6111 p 0,1244
    temporal    : BA 0,5000 p 0,5970 -> BA 0,6389 p 0,1045
    fitur signifikan FDR 5%: 0/60 dan 0/335 (dua-duanya)
    -> NAIK dan arahnya benar, tapi BELUM p < 0,05 (n = 18 subjek).

  DOMINASI IDENTITAS (eta-kuadrat): 0,030 -> 0,041 (tetap jauh di bawah 0,79
    yang diklaim dokumen lama; angka lama tidak bisa direproduksi).

  LOSO TabR (56 fold x 3 seed):
    metrik            lama      -> baru      baseline mayoritas
    accuracy        0,4881    -> 0,4821        0,5536
    balanced acc    0,4692    -> 0,4716        -
    MCC            -0,0521    -> -0,0622       -
    AUC             0,3974    -> 0,4606        0,5
    sensitivity     0,2933    -> 0,3733        -
    specificity     0,6452    -> 0,5699        -
    Baseline pada fitur baru: logistic acc 0,5714 (p 0,2189),
      GBDT 0,5536 (p 0,3781) - dua-duanya tidak signifikan.

  KESIMPULAN: memperbaiki spotting itu NYATA dan perlu (F1 0,164 -> 0,319,
  gate BA 0,50 -> 0,64, AUC 0,397 -> 0,461), TAPI belum mengubah kesimpulan
  klasifikasi: accuracy tetap di bawah baseline mayoritas dan AUC masih < 0,5.
  Jadi kegagalan klasifikasi kecemasan BUKAN (kebanyakan) akibat spotting rusak.

EVIDENCE: output/training/convat_apex_anxiety_loso_v3fixed/summary.md,
  output/training/within_subject_v3fixed_{poc,geo_temporal}/summary.md,
  output/training/convat_apex_anxiety_loso_v3fixed_baseline/summary.md,
  logs/regenerate_fixed2.log, output/apex_fixed/metadata.xlsx


### Iterasi 4.51 - REPRESENTASI FITUR: sinyal ada di dinamika onset (`rise`)
Tanggal    : 2026-10-10
Status     : SELESAI. STATE kecemasan terdeteksi signifikan (BA 0,833, p 0,0020).
             TRAIT lintas-subjek tetap di bawah acak.
Diubah     : ~ scripts/build_temporal_features.py (+ --descriptors, --only-descriptors)
             + scripts/audit_feature_representation.py
             + scripts/audit_feature_family_casme2.py
             + scripts/audit_rise_control.py
             + report/findings/audit-feature-representation.md

TUGAS DARI USER: "feature representation now bcs rn we dont have any way to add
dataset at the moment".

STRUKTUR LABEL (temuan yang mengubah pembacaan): label itu PER-SESI, bukan
per-orang. 18 dari 56 subjek labelnya berubah antar sesi (17 naik->turun).
Pipeline memakai --label-unit person = hanya sesi `after` = pertanyaan TRAIT,
dan membuang 35.019 baris `before`.

Jadi ada DUA pertanyaan:
  STATE : wajah orang yang sama berubah antara sesi cemas vs tenang (n=18)
  TRAIT : tebak tingkat kecemasan orang yang belum dilihat (n=56)

1. CEILING TRAIT: tidak ada fitur yang lolos derau seleksi.
   max |AUC-0,5| = 0,2432; null 200 acak = 0,2379 ± 0,0251; p = 0,385.
   AUC terbaik (0,73) persis sebesar yang didapat dari 670 fitur acak.

2. ABLASI KELUARGA pada gerbang within-subject (55-335 fitur per keluarga):
     desc:rise (55)      BA 0,8333   kontrol 0,4605   <- TERBAIK
     arah (120)          BA 0,6667   kontrol 0,4605
     koherensi (90)      BA 0,6389   kontrol 0,5263
     SEMUA (335)         BA 0,6389   kontrol 0,4737
     magnitude (125)     BA 0,6111   kontrol 0,5000
   `rise` = (peak - first) / idx_peak = kemiringan onset->apex. Yang informatif
   adalah KECEPATAN onset micro-expression, bukan besaran gerakan.
   Menambah fitur lain MENGENCERKAN: rise+arah 0,750; rise+base 0,694.

3. UJI KONTROL (bukan artefak sesi): untuk 38 subjek yang labelnya TIDAK
   berubah, `rise` tidak bisa membedakan before/after (BA 0,4605). Jadi `rise`
   spesifik pada subjek yang kecemasannya berubah.

4. VALIDASI BERSARANG (keluarga dipilih hanya dari 17 subjek latih):
   BA 0,7778 di luar sampel; `desc:rise` terpilih di 16/18 fold.

5. DITERAPKAN: tabel `experiments/features/apex/poc_abs_rise_v3fixed.pkl`
   (55 fitur). Gerbang within-subject:
     SEMUA (335): BA 0,6389  p 0,1045
     rise  (55) : BA 0,8333  p 0,0020   <- SIGNIFIKAN, pertama kali di proyek ini

6. TAPI TRAIT TETAP TIDAK BEKERJA (LOSO 56 fold x 3 seed):
     SEMUA (335): acc 0,4821  MCC -0,0622  AUC 0,4606
     rise  (55) : acc 0,4762  MCC -0,1037  AUC 0,3978   (baseline 0,5536)
   Semua keluarga di sekitar acak pada tugas trait (AUC 0,32-0,53).

KESIMPULAN: representasi yang benar untuk STATUS kecemasan adalah dinamika onset
(`rise`), bukan besaran gerakan. Efeknya STATE, bukan TRAIT. Framing tesis yang
didukung data: "POC-ABS mendeteksi perubahan status kecemasan (before vs after
ujian) pada orang yang sama", bukan "mengklasifikasi tingkat kecemasan orang".

EVIDENCE: report/findings/audit-feature-representation.md,
  output/training/within_subject_rise_v3fixed/summary.md,
  output/training/convat_apex_anxiety_loso_rise/summary.md,
  output/training/audit_feature_family/summary.csv


### Iterasi 4.52 - FIX pipeline: stage 4 & 6 memakai representasi `rise`
Tanggal    : 2026-10-11
Status     : SELESAI. Pipeline penuh (stage 5-7) dijalankan ulang, hasil dikonfirmasi.
Diubah     : ~ scripts/run_pipeline_v3.sh

MASALAH yang diperbaiki: stage 4 SELALU membangun tabel dengan 5 deskriptor
(335 fitur), jadi pipeline tetap melatih representasi lemah walaupun tabel `rise`
sudah dibuat manual di Iterasi 4.51. Representasi terbaik tidak pernah jadi default.

PERUBAHAN di run_pipeline_v3.sh:
  1. V3_DESCRIPTORS (default `rise`) + V3_ONLY_DESCRIPTORS (default 1) ->
     stage 4 memanggil build_temporal_features.py --descriptors rise
     --only-descriptors. Nama berkas ikut: ..._poc_temporal_rise.pkl supaya
     isinya jelas dan berkas lama (semua deskriptor) tidak tertimpa.
  2. Stage 6 sekarang meneruskan --drop-features. Default run_loso.py `_max_m$`
     MEMATALAKAN kalau tidak ada kolom yang cocok; pada mode --only-descriptors
     kolom `*_max_m` memang sudah dibuang -> pipeline mati. Sekarang dikosongkan
     saat --only-descriptors aktif, dan tetap `_max_m$` pada mode lama.
  3. `V3_DESCRIPTORS="peak ttp rise fall auc" V3_ONLY_DESCRIPTORS=0` memulihkan
     perilaku lama (diverifikasi lewat --dry-run).

VERIFIKASI (run penuh stage 5-7, log logs/pipeline_v3_20261011_194127.log):
  Gerbang within-subject, tabel rise (55 fitur): BA 0,8333, p 0,0050
  Gerbang within-subject, tabel per-frame (60 fitur): BA 0,6111, p 0,1244
  LOSO TabR (56 fold x 3 seed, rise):
    accuracy 0,4762 | bal-acc 0,4533 | MCC -0,1037 | AUC 0,3978
    baseline mayoritas 0,5536
  Baseline pembanding pada fitur rise:
    logistic acc 0,5357 (p 0,4179) | gbdt 0,4464 (p 0,8557)
  Hasil lama TIDAK tertimpa (tag gerbang & dataset dipisah):
    gerbang v3fixed tetap BA 0,6389; LOSO v3fixed tetap AUC 0,4606.

BACAAN: `rise` mengonfirmasi efek STATE yang signifikan lewat pipeline resmi.
TRAIT tetap di bawah baseline mayoritas pada representasi apa pun yang diuji.

EVIDENCE: logs/pipeline_v3_20261011_194127.log,
  output/training/within_subject_v3fixed_rise_{poc,geo_temporal}/summary.md,
  output/training/convat_apex_anxiety_loso_v3fixed_rise{,_baseline}/summary.md


### Iterasi 4.53 - Tampilkan train/val/test (persen) + FIX bug jumlah seed
Tanggal    : 2026-10-11
Status     : SELESAI.
Diubah     : ~ scripts/collect_loso_results.py

PERMINTAAN USER: tampilkan hasil train/val/test juga, dalam persen.

DITAMBAHKAN: bagian "## Train / Val / Test (akurasi, persen)" di tiap summary.md,
sumbernya `summary.json` per fold-seed (ditulis bin/tabr.py, berisi `scores` =
akurasi train/val/test pada epoch terbaik) + `best_epoch`. Angka test-nya
diverifikasi sama dengan baris `accuracy` level subjek (47,62% = 0,4762).

HASIL (run `rise`, 168 fold-seed):
  train 72,06% (±16,13) | val 49,89% (±9,77) | test 47,62% (±49,94)
  gap train-val +22,17 poin
  epoch terbaik median 1; 48,8% fold-seed berhenti di epoch 0
  -> ditambahkan PERINGATAN otomatis kalau >=40% fold-seed berhenti di epoch 0,
     karena itu berarti model praktis tidak terlatih dan angka di bawahnya
     mengukur model yang tidak belajar, bukan batas kemampuan fitur.

Bandingkan antar run (train/val/test):
  roi25_reg    82,82% / 61,50% / 48,80%
  v3fixed      87,80% / 58,33% / 48,21%
  v3fixed_rise 72,06% / 49,89% / 47,62%
Pola sama: train jauh di atas val (hafalan), val ~50%, test ~48% (< baseline
mayoritas 55,36%). Run `rise` paling tidak menghafal (gap terkecil).

BUG YANG DITEMUKAN & DIPERBAIKI saat mengerjakan ini:
`collect_loso_results.py` menghitung jumlah seed HANYA dari fold pertama
(`fold_dirs[0]`). Pada `convat_apex_anxiety_loso_roi25_reg`, `fold_000` cuma
punya 1 seed dir sedangkan 55 fold lain punya 3 -> n_seeds terbaca 1, dan seed
1..2 di 55 fold DIBUANG DIAM-DIAM. Akibatnya laporan run itu sempat turun ke
accuracy 0,4107 (hanya seed 0). Sekarang jumlah seed diambil dari GABUNGAN
semua fold; setelah diperbaiki hasilnya kembali 0,4884 ± 0,0866, cocok dengan
angka yang tercatat sebelumnya (0,4881 ± 0,0805; beda tipis karena 2 fold-seed
tidak ada di disk: 166 vs 168).

DAMPAK: hanya `roi25_reg` yang terpengaruh (fold_000-nya parsial). Run lain
sudah punya 3 seed di fold_000, jadi angkanya tidak berubah (diverifikasi
sebelum/sesudah: v3fixed 0,4821 dan rise 0,4762 tetap sama).

EVIDENCE: output/training/convat_apex_anxiety_loso_{roi25_reg,v3fixed,
  v3fixed_rise,rise}/summary.md


### Iterasi 4.54 - `--epochs-trace`: kurva epoch terlihat + DIAGNOSIS overfit
Tanggal    : 2026-10-11
Status     : SELESAI.
Diubah     : ~ scripts/run_loso.py (+ --epochs-trace, epoch_trace_from_checkpoint)
             ~ scripts/run_pipeline_v3.sh (stage 6 meneruskan --epochs-trace)
             ~ report/findings/audit-feature-representation.md (§9)

PERMINTAAN USER: "when training let me see the epoch again i dont know all this".

DITAMBAHKAN: `--epochs-trace [N]` (default N=40) mencetak per fold per seed:
  val_acc%/epoch, train_loss/epoch, val_loss/epoch, best epoch, dan peringatan
  OVERFIT otomatis. Sumbernya `checkpoint.pt` -> `training_log` (berisi metrics
  val/test per epoch, termasuk cross-entropy yang TIDAK ada di summary.json /
  report.json) + train loss dari tfevents `loss_train/`. Ini cara yang sama
  dipakai `notebooks/tabr_feature_pruning_tuning.ipynb` (collect_epoch_metrics).
Stage 6 pipeline kini meneruskannya; `V3_EPOCHS_TRACE=0` mematikannya.

TEMUAN BESAR dari kurva ini (fold 1, seed 0, tabel rise):
  epoch    :  0     4     7     12    18    24
  train_ce : 0.70  0.58  0.48  0.33  0.19  0.11   <- turun terus
  val_ce   : 0.68  0.69  0.71  0.75  0.90  1.10   <- NAIK terus
  val_acc  :  45%   64%   73%   45%   45%   45%
=> OVERFIT sejak epoch 0. Model menghafal 44 subjek latih; val loss tidak pernah
   membaik. Val acc 73% di epoch 7 hanya derau di atas model yang makin buruk.

Ini menjelaskan dua keanehan yang sudah tercatat:
  1. 48,8% fold-seed "berhenti di epoch 0" (Iterasi 4.53) -> bukan bug early
     stopping; memang tidak ada epoch yang membaik.
  2. Akurasi val berupa tangga 9,1% (hanya ~11 subjek val) -> pemilihan epoch
     lewat akurasi val nyaris acak; seharusnya lewat val LOSS.

IMPLIKASI: angka LOSO ~48% (di bawah baseline mayoritas 55,36%) adalah hasil
jujur model yang tidak bisa generalisasi, BUKAN bukti fitur tidak bersinyal.
Gerbang within-subject tetap BA 0,833 (p 0,005) pada fitur yang sama -> sinyal
STATE nyata, transfer antar-subjek yang gagal. Langkah berikutnya: perbaiki
rezim training (regularisasi / konfigurasi / pemilihan epoch lewat val loss).

CATATAN NOTEBOOK: repo sudah punya analisis epoch di
`notebooks/tabr_final_analysis.ipynb` (plot Train Loss / Val Accuracy / Test
Accuracy per epoch + garis best_epoch) dan `tabr_feature_pruning_tuning.ipynb`
(`collect_epoch_metrics`). Keduanya membaca tfevents/checkpoint; implementasi
`--epochs-trace` sengaja memakai sumber yang sama supaya konsisten.

CLUE DARI NOTEBOOK (kandidat penyebab overfit): `notebooks/check_freeze_tabr.ipynb`
memakai `LR = 3e-4`, `EARLY_STOPPING_PATIENCE = 10`, `M_NEIGHBORS = 4` dan
menambah teknik freeze-context. Config pipeline kita memakai `lr = 1e-3`
(3,3x LEBIH TINGGI), `patience = 16`, `context_size = 4`. Learning rate 3x lebih
tinggi adalah kandidat kuat penyebab val loss naik sejak epoch 0.
Bukti pendukung dari notebook itu: laporan klasifikasinya juga degenerat
(recall kelas 0 = 0,011 vs kelas 1 = 0,989; macro-F1 0,398) -- pola "tebak kelas
mayoritas" yang sama dengan hasil kita.
Belum diuji; kandidat eksperimen berikutnya (turunkan lr ke 3e-4).

EVIDENCE: logs (keluaran --epochs-trace), checkpoint.pt tiap fold-seed,
  report/findings/audit-feature-representation.md §9,
  notebooks/check_freeze_tabr.ipynb


### Iterasi 4.55 - RUN ULANG BERSIH dari nol: angka otoritatif + koreksi
Tanggal    : 2026-10-11
Status     : SELESAI. Pipeline penuh stage 1-7 dari nol, 560/560 sample.
Diubah     : (tidak ada kode; run penuh + koreksi angka di dokumen)

KONTEKS: output lama dihapus supaya bisa reset total (Iterasi 4.55a: hapus 31 GB
stage output: output/apex{,_v2,_fixed}, experiments/features/apex/*,
exp/tabr + data/ untuk direktori kita saja -- benchmark upstream TabR
dipertahankan. Yang TIDAK disentuh: raw video, model dlib, backup, scripts,
configs, report.)

HASIL RUN BERSIH (log logs/pipeline_v3_20261011_204555.log):
  stage 1: 2.667 event (1.344 before / 1.323 after), 560 sample
  stage 2-4: 63.413 baris, tabel `rise` 55 fitur
  stage 5-7: gerbang + LOSO + baseline

TEMUAN PENTING - RUN SEBELUMNYA TIDAK LENGKAP:
  run lama (`apex_fixed`) pernah dimatikan di tengah lalu di-resume. Logika
  resume melewati sample yang direktori output-nya sudah ada, sehingga sample
  yang tertulis separuh (di paruh `before`) ikut terlewat.

    | | run lama | run bersih |
    | event          | 2.647 | 2.667 |
    | baris before   | 35.019 | 35.477 (+458) |
    | baris after    | 27.936 | 27.936 (SAMA) |

  Semua selisih ada di `before`; `after` identik. Karena LOSO hanya memakai
  `after`, angka LOSO TIDAK berubah (dan memang identik sampai 4 desimal).
  Gerbang within-subject memakai KEDUA sesi, jadi angkanya berubah:

    gerbang `rise` (55 fitur):  BA 0,8333 p 0,0050  ->  BA 0,7500 p 0,0100
    gerbang per-frame (60)   :  BA 0,6389 p 0,1244  ->  BA 0,6389 p 0,0647

  ANGKA YANG BENAR: 0,7500 (p 0,0100). 0,8333 (Iterasi 4.51-4.52) diukur pada
  data `before` yang tidak lengkap dan TIDAK BOLEH dipakai lagi.

HASIL OTORITATIF:
  gerbang `rise`        : BA 0,7500, p 0,0100 (signifikan)
  gerbang per-frame     : BA 0,6389, p 0,0647
  gerbang vektor selisih: BA 0,5000, p 0,6119/0,7612 (tidak ada sinyal arah)
  LOSO (56 fold x 3 seed): train 72,06% / val 49,89% / test 47,62%
                           bal-acc 0,4533, MCC -0,1037, AUC 0,3978
                           baseline mayoritas 55,36%
  baseline: logistic 53,57% (p 0,4179) | GBDT 44,64% (p 0,8557)

OVERFIT UNIVERSAL: dari --epochs-trace, 168 dari 168 fold-seed memicu peringatan
OVERFIT (train loss turun, val loss naik). Bukan sebagian fold.

EVIDENCE: logs/pipeline_v3_20261011_204555.log, logs/stage6_loso_20261011_204555.log,
  output/training/{within_subject_run2_poc,within_subject_run2_geo_temporal,
  convat_apex_anxiety_loso_run2,convat_apex_anxiety_loso_run2_baseline}/summary.md,
  report/findings/audit-feature-representation.md §10

### Iterasi 4.56 - Proposal: BAB II Landasan Teori lengkap + audit sumber 2017-2026
Tanggal    : 2026-10-12
Status     : SELESAI. BAB II (2.1-2.2.11) tertulis; proposal.pdf 35 halaman.
Diubah     : proposal/main.typ (BAB II + penomoran gambar/tabel + Daftar Isi),
             proposal/refs.bib (+20 entri, total 32),
             proposal/figures/ (9 gambar, BARU),
             report/documentation/research-papers.md (+bagian "Sitasi BAB II")
Dijalankan : typst compile main.typ proposal.pdf
             + verifikasi 34 DOI lewat api.crossref.org
             + render PDF ke PNG dan diperiksa visual (halaman 7-35)
Hasil      : kompilasi 0 error, 0 sitasi tak ter-resolve, 0 em dash,
             0 entri pustaka di luar rentang 2017-2026.

KONTEKS: BAB II disusun dengan menulis ulang (parafrase) BAB II proposal
rujukan (Proposal Skripsi_Syahrul-Bhudi-Ferdiansyah), mempertahankan struktur
aslinya 2.1 Studi Literatur + 2.2.1-2.2.11, lalu setiap sitasi yang tidak
memenuhi aturan sumber proposal diganti.

AUDIT SUMBER - 7 dari 28 sitasi BAB II asli DITOLAK (melanggar aturan
"internasional akses terbuka / nasional minimal SINTA 2"):

    Sitasi asli                          Masalah              Pengganti
    Sathyanarayanan 2024                 jurnal tidak lagi    Chicco & Jurman 2023
      (confusion matrix)                 memenuhi kriteria    (BioData Mining, OA)
                                         AJOL
    Sejati & Mardhiyyah 2021             JurTI = SINTA 5      Bachtiar & Wafi 2021
      (Dlib)                                                  (JTIIK, SINTA 2)
    Nur Cahyo dkk. 2023                  JATI = SINTA 4       Bachtiar & Wafi 2021
      (LBPH per komponen wajah)                               (JTIIK, SINTA 2)
    Nurshabrina dkk. 2024                Action Research      Hur dkk. 2020
      (definisi kecemasan)               Literate = SINTA 5   (J. Neuroscience)
    Oktamarin dkk. 2022                  Bharasumba tidak     Javaid dkk. 2023
      (kecemasan abnormal)               terindeks SINTA      (Middle East Curr Psych)
    Dewi dkk. 2025                       sumber prevalensi    Wahdi dkk. 2025
      (prevalensi kecemasan)             lebih lemah          (Child Adolesc Psych)
    Schwarz dkk. 2022                    workshop CEUR-WS,    Johnson dkk. 2021
      (FAISS)                            bukan jurnal         (IEEE Trans Big Data)

  Satu sitasi lain (Watson dkk. 2022) tidak ditolak kualitasnya, tetapi
  disatukan ke `hur2020anxiety` yang sudah dipakai di BAB I untuk klaim yang
  sama.

  Catatan: Arik & Pfister 2021 (TabNet) DIPERTAHANKAN walau prosiding AAAI tidak
  akses terbuka, karena hanya dipakai untuk mendefinisikan struktur data tabular
  (baris = objek, kolom = fitur), bukan untuk klaim performa. Ini satu-satunya
  entri yang perlu diganti kalau pembimbing meminta seluruh sitasi OA.

VERIFIKASI DOI: 34 DOI diselesaikan lewat api.crossref.org; semuanya cocok
judul + penulis pertama + wadah terbit. Rentang tahun hasil verifikasi
2020-2025, jadi aturan 2017-2026 aman. Satu-satunya yang gagal di Crossref
adalah arXiv TabR (10.48550/arXiv.2307.14338) karena arXiv bukan anggota
Crossref; entri itu sudah ada di refs.bib sejak Iterasi 4.41 dan URL-nya benar.

GAMBAR: 9 gambar BAB II diekstrak dari PDF asli memakai pdfimages dan
diperiksa satu per satu (bukan dikarang): ekspresi wajah, micro-expression,
facial landmark Dlib, dua frame n1/n2, proses POC, arsitektur TabR, encoder/
predictor, retrieval module, dan confusion matrix.

TIGA CACAT TATA LETAK ditemukan lewat render PDF dan diperbaiki:
  1. Keterangan gambar tampil "Gambar Gambar 2.1" karena `numbering` sudah
     mengembalikan prefix sementara `figure.supplement` menambahkannya lagi.
     -> `numbering` sekarang hanya mengembalikan "2.1".
  2. Tabel 2.1 (ringkasan 5 penelitian) lebih tinggi dari satu halaman dan
     isinya saling menimpa. -> `figure.where(kind: table)` diset
     `block(breakable: true)` sehingga tabel terpotong rapi dan header
     berulang di halaman berikutnya.
  3. Sel "Metode" pada Tabel 2.1 meluber ke kolom sebelahnya sampai header
     "Tahun" terpotong. -> lebar kolom disetel ulang ke (1,45 / 0,5 / 1 / 2,05)
     dan isi sel disingkat ("TV-L1, ShuffleNetV2").

EVIDENCE: proposal/proposal.pdf (35 halaman), proposal/main.typ,
  proposal/refs.bib, proposal/figures/*.png (9 berkas),
  report/documentation/research-papers.md (bagian "Sitasi BAB II")

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan (`tampilkan-daftar-gambar-tabel = false`) sampai BAB III ada.


=====================================================================
### Iterasi 4.67 - EKSEKUSI refactor: scripts/ (61 file) dibongkar ke struktur baru
Tanggal    : 2026-10-13
Status     : SELESAI (BELUM DI-COMMIT). Plan 4.66 dieksekusi penuh.
Diubah     : scripts/ DIHAPUS (61 file habis terbagi):
             pipeline/stages/stage_0..8 (10 stage), pipeline/serve/ (2),
             pipeline/ (run.sh, spotting_config.py, paths.py BARU, README.md BARU),
             research/casme2/ (27), research/audits/ (4), legacy/ (17 + README.md)
             Rename: comparasion/->shared/, src/->tabr/,
             features_extraction/->features/, helper/helper.py->shared/helper.py,
             outputs/models/->models/, run_pipeline_v3.sh->pipeline/run.sh
             notebooks/ dikelompokkan: preprocess|spotting|export|tabr|legacy
             ./run diperbaiki; pipeline/registry.json diperbarui
             PROGRESS.md, HANDOFF.md, report/documentation/{pipeline.md,ringkasan.md}
Dijalankan : ./pipeline/run.sh --dry-run
             V3_PRESPLIT=1 ./pipeline/run.sh --dry-run
             bash -n pipeline/run.sh && bash -n run
             .venv/bin/python -m py_compile (pipeline/ features/ tabr/ shared/ apex/ research/)
             uji impor nyata: stage_1_spotting, stage_5_gate, stage_6_train_loso,
               stage_7_collect, stage_7_baseline, stage_8_holdout_combine,
               shared.config, shared.roi, tabr.TabR, features.poc
             grep path lama di kode hidup
Hasil      : dry-run 7 stage (default) dan 8 stage (V3_PRESPLIT=1), semua path baru
             benar; bash -n bersih; py_compile bersih; 10 modul impor OK;
             grep bersih di luar legacy/ dan dokumen historis.
             Artefak training utuh: 47 folder / 31 summary.md di output/training/,
             output/final_model/ (model.ckpt, meta.json, preprocessor.joblib,
             context.npz) utuh, 30 notebook utuh (tidak ada yang dihapus).
             TIDAK ADA angka pipeline yang diubah (refactor murni; pembuktian
             angka menunggu run berikutnya).

CATATAN PENTING — nama stage TIDAK boleh diawali angka: plan menulis
`0_presplit.py`, tetapi `import 1_spotting` = SyntaxError (diuji). Empat modul
stage diimpor file lain, jadi dipakai `stage_N_nama.py`. Ini penyimpangan sadar
dari plan.

CATATAN PENTING — bootstrap ROOT: semua skrip stage memakai
`Path(__file__).parent.parent`. Setelah pindah ke `pipeline/stages/` (dua tingkat
di bawah root) itu rusak dan SEMUA impor gagal. Ditutup dengan satu helper
`pipeline/paths.py` (dipakai 10 stage) + bootstrap `parents[2]` (stage/serve) dan
`parents[1]` (stage_7_baseline). Impor sibling ditulis ulang
(`from spotting import` -> `from pipeline.spotting_config import`, dst).

YANG SENGAJA TIDAK DILAKUKAN:
  - `experiments/configs/` TIDAK dipindah. 660 referensi menyebutnya, ±645 di
    antaranya di `third_party/.../DONE.json` (catatan permanen run training
    terakhir). Memindahkan = merusak provenance hasil. Configs tetap di tempat.
  - Tidak ada notebook dihapus (arahan user).
  - Tidak ada artefak training dihapus (arahan user).
  - Tidak ada duplikat byte-identik di luar folder hasil; tiap .toml config
    memang direferensikan, jadi tidak ada yang dihapus.
  - File yang dihapus hanya: 3 folder kosong, 4 log 0 byte,
    `desktop/pipelinedesk/.amp`.

KOREKSI/ARAHAN USER: "go ahead with the folder and file rarrranging i need it to
be able to see, need it to be organized and tidy thank you", lalu "delete
duplicates and unused also just group them on soe folders", "but dont delete
notebooks", "the ones that are needed on recent result of training dont delete".

EVIDENCE: pipeline/README.md (peta stage), pipeline/run.sh, pipeline/paths.py,
  report/plans/2026-10-13-pipeline-stage-refactor/plan.md (status SELESAI),
  PROGRESS.md, report/documentation/pipeline.md, output/training/*/summary.md

BELUM: di-commit (menunggu perintah Khalid). BAB III masih placeholder.


=====================================================================
### Iterasi 4.66 - Plan: refactor pipeline (stage terpisah + struktur folder)
Tanggal    : 2026-10-13
Status     : SELESAI (saat itu PLAN SAJA). 7 issue ditulis. DIEKSEKUSI -> Iterasi 4.67.
Diubah     : report/plans/2026-10-13-pipeline-stage-refactor/ (BARU:
             CONTEXT.md, plan.md, issues/01..07), PROGRESS.md
Dijalankan : discovery saja — ls/grep/wc/git/ps untuk memetakan struktur nyata
             + cek struktur 7 tabel markdown + verifikasi aritmetika 61 file
Hasil      : plan lengkap; 9 file; semua link issue resolve; 7 tabel valid;
             26+4+17+10+4 = 61 file scripts/ habis terbagi tanpa sisa.

KOREKSI USER: "plan for a refactor of pipeline files and folder restructure right
now it looks confusing and i cant find when i need a pipeline to show, so each
stage should be well separated and well mark on which is which, for instance where
is the split, the spotting, the apex etc".

MASALAH YANG DITEMUKAN (terverifikasi, bukan dugaan):
  - scripts/ datar berisi 61 file; hanya 10 yang stage pipeline. Sisanya 26
    eksperimen CAS(ME)2, 4 audit, 17 legacy, 4 pendukung.
  - Nama stage tidak terlihat: nomor stage hanya hidup di dalam
    run_pipeline_v3.sh (fungsi banner) dan nama file log.
  - 3 nama modul menyesatkan, semuanya HIDUP (bukan dead code):
      comparasion/      -> dipakai produksi stage 2 (ComparisonConfig, ROIExtractor)
      scripts/spotting.py -> cuma dataclass SpottingConfig (52 baris)
      src/              -> isinya model TabR
  - output/ vs outputs/: outputs/ cuma berisi 1 file model dlib (95 MB).
  - 23 dokumen menyebut path lama (changes-log 29x, PROGRESS 16x, HANDOFF 11x).
  - File stage melewati 500 baris: process_spotting 1089, run_loso 829,
    extract_features_poc_abs 724, collect_loso_results 595, runner 737.

JEBAKAN TEKNIS (wajib ditangani, kalau tidak semua impor gagal):
  Tiap skrip stage memakai ROOT = Path(__file__).resolve().parent.parent.
  Setelah pindah ke pipeline/stages/ (dua tingkat di bawah root) ini rusak.
  Solusi: satu helper bersama pipeline/paths.py dipakai 10 stage.

BLOCKER: ada pipeline SEDANG BERJALAN saat plan ditulis (PID 314580,
  run_pipeline_v3.sh --fresh, stage 1 spotting, ~32 menit). Memindahkan file
  sekarang memutus proses itu. Eksekusi menunggu run selesai.

ISI PLAN (7 issue, urut prioritas):
  01 critical  paket pipeline/ + titik masuk run.sh + README peta stage
  02 critical  pindahkan 10 stage + bootstrap ROOT (pipeline/paths.py)
  03 high      pisahkan 26 eksperimen CAS(ME)2 -> research/casme2/ (+4 audit)
  04 high      karantina 17 file legacy -> legacy/ (+ notebooks/)
  05 medium    rename: comparasion/->shared/, src/->tabr/,
               features_extraction/->features/, spotting.py->pipeline/spotting_config.py
  06 medium    outputs/models/->models/; experiments/configs/->pipeline/configs/
  07 low       sinkronkan dokumen hidup + beri penunjuk di dokumen historis

TARGET: scripts/ HILANG SEPENUHNYA (61 file punya rumah baru).

EVIDENCE: report/plans/2026-10-13-pipeline-stage-refactor/{CONTEXT.md,plan.md,
  issues/01..07}

BELUM: eksekusi plan (menunggu run selesai + persetujuan user).
  BAB III (Metodologi) masih placeholder.


### Iterasi 4.65 - Ringkasan riset: timeline bertimestamp + tabel hasil dirapikan
Tanggal    : 2026-10-13
Status     : SELESAI. Bagian 3 ringkasan.md jadi timeline; tabel hasil urut.
Diubah     : report/documentation/ringkasan.md (bagian 3 + kolom waktu tabel 4)
Dijalankan : git log --format='%ad' (era 2025-09 s/d 2026-08)
             + baca nama log logs/*_YYYYMMDD_HHMMSS.log (era 2026-09 s/d 2026-10)
             + stat -c '%y' output/training/*/summary.md (waktu run selesai)
             + cek struktur 19 tabel + render HTML untuk diperiksa visual
Hasil      : timeline 7 era x 5 kolom, 19 tabel valid (118 baris, 0 rusak),
             urutan tabel hasil sudah kronologis.

KOREKSI USER: "i more needing a timeline so that i know the table of results is
good but i need a timeline time stamp on when what did it have, what is the result
what is the problem, then the next is the same but with the what we change also
from before and the new results from that change timestamp but keep the result
table tho its good".

BAGIAN 3 diganti jadi TIMELINE, 5 kolom:
    Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah -> hasil baru

Tiap baris = satu kejadian: kapan, apa yang dikerjakan, hasilnya, masalah yang
ketahuan, lalu perbaikan + hasil barunya. Dibagi 7 era:
  Era 1 Membangun dari nol                    2025-09 s/d 2026-08
  Era 2 Audit + perbaikan split               2026-08-25 s/d 2026-09-01
  Era 3 Evaluasi jujur LOSO                   2026-09-17 s/d 2026-09-29
  Era 4 Perbaikan metodologi                  2026-10-06 s/d 2026-10-08
  Era 5 Validasi spotting CAS(ME)2            2026-10-09 s/d 2026-10-10
  Era 6 Run bersih + temuan utama             2026-10-11
  Era 7 Model final + STATE + proposal        2026-10-12 s/d 2026-10-13
Ditutup "Ringkasan timeline dalam 1 layar" (12 tonggak penting).

TIMESTAMP SEMUA NYATA (bukan karangan), sumbernya:
  - git log --format='%ad'  -> tanggal commit 2025-09-13 s/d 2026-08-26
  - nama file log (YYYYMMDD_HHMMSS) -> kejadian 2026-09 s/d 2026-10
  - stat -c '%y' pada summary.md -> waktu run selesai
  - jam di pipeline_v3_20261012_140147.log -> run terakhir 14:01:47-15:06:24

TABEL HASIL (bagian 4) DIPERTAHANKAN, hanya dirapikan:
  - kolom "Tanggal" -> "Waktu", diisi jam (11:41, 12:00, 10:10, 21:51,
    09:55, 13:36, 13:37, 15:06)
  - urutan baris 11-13 dibetulkan (sebelumnya LitTabR 09:55 ditaruh setelah
    run 13:36, jadi tidak kronologis)

EVIDENCE: report/documentation/ringkasan.md (364 baris, 19 tabel)

BELUM: BAB III (Metodologi) masih placeholder.


### Iterasi 4.64 - Ringkasan riset: satu dokumen rapi (bahasa sederhana)
Tanggal    : 2026-10-13
Status     : SELESAI. `report/documentation/ringkasan.md` dibuat.
Diubah     : report/documentation/ringkasan.md (BARU),
             penunjuk ditambahkan di changes-log.md, PROGRESS.md,
             report/results/results.md
Dijalankan : cek struktur 16 tabel di ringkasan.md (jumlah kolom konsisten)
             + verifikasi angka terhadap output/training/*/summary.md,
               changes-log, dan output/final_model/meta.json
Hasil      : 16 tabel valid (0 baris rusak), 2 code fence seimbang,
             semua angka cocok dengan sumbernya, tidak ada angka baru.

KOREKSI USER: "changes log, progress, results update all for changes from the
start what we add why we add what we fiks on each changes on each runs, the
result we need with train test val until the most recent one in an md and it
needs to be readable with words that everyoen can understand not too much
technical jargon and a more tidy design".

DOKUMEN BARU `report/documentation/ringkasan.md`, isi 8 bagian:
  1. Penelitian ini tentang apa (diagram alur + fakta dataset 56 subjek/2 sesi)
  2. Cara membaca hasil (train/val/test + arti baseline)
  3. Perjalanan perubahan dalam 6 fase, tiap fase tabel
     "Yang dikerjakan | Kenapa | Hasil":
       Fase 1 Membangun pipeline        (2025-09-13 s/d 2026-08-25)
       Fase 2 Audit + perbaikan dasar   (2026-08-25 s/d 2026-09-01)
       Fase 3 Evaluasi jujur LOSO       (2026-09-17 s/d 2026-09-29)
       Fase 4 Perbaikan metodologi      (2026-09-29 s/d 2026-10-08)
       Fase 5 Spotting CAS(ME)2 + fitur (2026-10-09 s/d 2026-10-11)
       Fase 6 Model final + proposal    (2026-10-12 s/d 2026-10-13)
  4. Tabel SEMUA run train/val/test - 14 baris, paling lama -> paling baru
  5. Hasil spotting CAS(ME)2 (F1 0,20 -> 0,43)
  6. Hasil uji dalam-subjek (BA 0,75 p 0,010 = temuan terkuat)
  7. Kesimpulan jujur (berhasil / belum berhasil / langkah berikutnya)
  8. Peta lokasi file + kamus 13 istilah

RUN PALING BARU yang ditampilkan: STATE/session 2026-10-12
  train 89,90% / val 62,50% / test 54,46%, baseline 57,14%, AUC 0,5204.

TIGA DOKUMEN LAMA DIBERI PENUNJUK ke ringkasan (tidak dihapus, tetap jadi
sumber detail): changes-log.md, PROGRESS.md, report/results/results.md.

EVIDENCE: report/documentation/ringkasan.md

BELUM: BAB III (Metodologi) masih placeholder.


### Iterasi 4.63 - Akses bebas (gratis) untuk 28 paper proposal
Tanggal    : 2026-10-13
Status     : SELESAI. Tiap paper punya tautan DOI + tautan akses bebas.
Diubah     : report/documentation/research-papers.md
             (tabel 28 paper + bagian "Cara mengakses tanpa bayar")
Dijalankan : api.unpaywall.org untuk mencari salinan OA tiap DOI
             + curl -L ke semua tautan gratis (uji tautan mati + cek tipe PDF)
             + unduh & periksa 2 PDF IEEE untuk memastikan artikel yang benar
Hasil      : 28 baris tabel, 30 tautan gratis, 16 di antaranya PDF langsung;
             tidak ada tautan mati; proposal tetap 24 halaman, 0 error.

KOREKSI USER: "can i get the paper that we used to be getting from somewhere where
we dont need to become a member or we dont need to purchase atleast just free sign
in? because some ieee papers are locked away and i need a more easier way to
access them to verify".

Setiap baris tabel kini punya DUA tautan: DOI resmi + akses bebas (gratis).

Cara mencari: Unpaywall API (api.unpaywall.org) per DOI, lalu tiap tautan diuji
curl -L. Semua tautan gratis berasal dari sumber resmi (penerbit OA, arXiv,
PubMed Central, situs jurnal) — tidak ada situs berbagi ilegal.

PAPER IEEE YANG DIKIRA TERKUNCI, ternyata ada PDF OA resminya:
  - Zhao 2023 (Proc. IEEE / JPROC)  -> ieeexplore.ieee.org/ielx7/5/4357935/10144523.pdf
    (diunduh, diperiksa: benar artikel itu, 21 halaman)
  - Li 2022 (IEEE TAFFC)            -> ieeexplore.ieee.org/ielx7/5165369/9964459/09915437.pdf
    (diunduh, diperiksa: benar artikel itu, 19 halaman)
  - Pasaribu 2024 (IEEE Access)     -> OA penuh dari IEEE

JALUR GRATIS LAIN:
  arXiv  : Ben 2022 (TPAMI), Arik 2021 (AAAI), Johnson 2021 (IEEE TBDATA),
           Gorishniy 2024 (TabR), Sahu 2025
  PMC    : Hur 2020 (J. Neuroscience), Lei 2024 (Autism/SAGE)
  Penerbit OA penuh: MDPI, Frontiers, Springer/BMC, JTIIK, Edu Komputika,
           IJIES (inass.org), IEEE Access

SATU KASUS TIDAK PUNYA SALINAN OA:
  Lu dkk. 2022 (nomor 5, prosiding ACM FME) — versi ACM terkunci dan tidak ada
  salinan OA. Yang gratis adalah versi jurnal lanjutannya di arXiv 2409.00017
  (penulis sama, topik sama, BUKAN artikel identik). Ditulis eksplisit di md.

HASIL UJI TAUTAN GRATIS:
  - 16 tautan -> PDF langsung (application/pdf) tanpa login
  - 8 tautan  -> halaman artikel yang bisa dibaca
  - MDPI, JTIIK, ACM -> 403 untuk permintaan otomatis (halaman normal di peramban)

EVIDENCE: report/documentation/research-papers.md (baris 901-1060),
  proposal/refs.bib (28 entri), proposal/proposal.pdf (24 halaman)

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan sampai BAB III ada.


### Iterasi 4.62 - Paper proposal didata ulang di research-papers.md + tautan
Tanggal    : 2026-10-12
Status     : SELESAI. 28 paper proposal terdaftar dengan tautan yang terverifikasi.
Diubah     : report/documentation/research-papers.md
             (bagian "Sitasi BAB II Proposal" -> "Paper yang Dipakai di Proposal")
Dijalankan : .venv/bin/python (baca refs.bib -> tabel) 
             + curl -L ke 28 tautan (cek tautan mati)
             + api.crossref.org untuk 27 DOI (cek judul + wadah terbit)
             + typst compile main.typ proposal.pdf
Hasil      : 28 baris tabel = 28 tautan = 28 entri refs.bib; tidak ada tautan mati;
             proposal tetap 24 halaman, 0 error.

KOREKSI USER: "all the paper we found put it on the md of research paper the ones
on the proposal, and then give it the link that i can open and verify".

Bagian "Sitasi BAB II Proposal" diganti menjadi "Paper yang Dipakai di Proposal
(2017-2026)". Isinya daftar lengkap 28 paper yang benar-benar disitasi di
proposal (BAB I + BAB II), dikelompokkan:

    A. Ekspresi wajah dan ekspresi mikro          (10 paper)
    B. Data tabular dan pembelajaran mesin         (6 paper)
    C. Kecemasan, stres, dan kesehatan mental      (9 paper)
    D. Nasional (minimal SINTA 2)                  (3 paper)

Kolom: No, Penulis (tahun), Judul, Wadah, Dipakai di, Tautan. Tautan langsung ke
DOI/arXiv sehingga bisa diklik untuk diperiksa.

Daftar lama bernomor 101-131 dihapus karena tidak sinkron lagi (liu2022tvli,
archana2024deep, sinulingga2023keyframe, huang2020embedding sudah tidak dipakai;
Tabel 2.1 berubah 10 -> 5 baris). Tabel baru dibuat dengan membaca refs.bib
langsung, jadi jumlahnya pasti 28.

Dua catatan basi diperbaiki: baris "Huang dkk. 2020 dipertahankan" (sudah dihapus)
dan baris klaim Liu dkk. (Liu sudah tidak dipakai).

VERIFIKASI TAUTAN (2026-10-13):
  - 28 tautan dicek curl -L: TIDAK ADA yang mati. Kode 403/202 dari IEEE, MDPI,
    SAGE, ACM, JTIIK adalah blokir bot penerbit, bukan DOI rusak.
  - 27 DOI dicek api.crossref.org: judul + wadah terbit cocok. Dua pengecualian:
    Prakoso 2026 (10.25126/jtiik.2026133) DOI terdaftar dan mengarah ke JTIIK
    13(3), tetapi metadata judul/penulis Crossref masih kosong; Sahu 2025
    memakai DOI arXiv yang tidak ada di Crossref (laman arXiv terbuka normal).

EVIDENCE: report/documentation/research-papers.md (baris 901-1020),
  proposal/refs.bib (28 entri), proposal/proposal.pdf (24 halaman)

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan sampai BAB III ada.


### Iterasi 4.61 - Proposal: Confusion Matrix dihapus dari dasar teori
Tanggal    : 2026-10-12
Status     : SELESAI. 2.2.6 menjadi Metrik Evaluasi; proposal.pdf 24 halaman.
Diubah     : proposal/main.typ (2.2.6, Daftar Isi, Daftar Gambar),
             .amp/in/proposal/make_figures.py (fungsi confusion matrix dihapus)
Dijalankan : typst compile main.typ proposal.pdf
             + cek entri refs.bib yang tidak tersitasi
             + render PDF ke PNG dan diperiksa visual (halaman 16)
Hasil      : kompilasi 0 error, 0 sitasi tak ter-resolve, 0 em dash, 24 halaman,
             28/28 entri pustaka tampil, penomoran 2.2.1-2.2.6 dan Gambar 2.1-2.8
             berurutan, Daftar Isi cocok dengan halaman cetak aslinya.

KOREKSI USER: "dont need confusion matriks on the dasar teori".

2.2.6 Confusion Matrix -> 2.2.6 Metrik Evaluasi. Definisi confusion matrix dan
Gambar 2.9 dihapus. Yang tersisa: penetapan kelas positif/negatif dan rumus
accuracy, precision, recall, F1-score.

Metrik evaluasi TETAP ada karena Rumusan Masalah 1.2 dan Tujuan 1.3 menyebut
keempat metrik tersebut, jadi rumusnya harus tetap ada di dasar teori.
Penomoran 2.2.1-2.2.6 tidak berubah, 2.2.5 tetap di posisinya.

IKUT DIHAPUS:
  - proposal/figures/fig2-9-confusion-matrix.png (Gambar BAB II jadi 8:
    Gambar 2.1-2.8)
  - fungsi `fig_confusion_matrix` di generator gambar

TIDAK DIHAPUS: entri refs.bib `yang2024confusion` tetap ada (28 entri) karena
masih disitasi sebagai baris Tabel 2.1.

EVIDENCE: proposal/proposal.pdf (24 halaman), proposal/main.typ,
  proposal/refs.bib (28 entri), proposal/figures/ (8 berkas),
  .amp/in/artifacts/proposal/metrik-18.png (render pemeriksaan 2.2.6)

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan sampai BAB III ada.


### Iterasi 4.60 - Proposal: perampingan agar tidak terkesan menjiplak
Tanggal    : 2026-10-12
Status     : SELESAI. BAB I dan BAB II dirampingkan; proposal.pdf 24 halaman.
Diubah     : proposal/main.typ (1.1 dipotong ~setengah, 1.2 dan 1.3 jadi 2 butir,
             Tabel 2.1 jadi 5 baris, 2.2.4/2.2.5/2.2.6 diringkas, Daftar Isi),
             proposal/refs.bib (28 entri)
Dijalankan : typst compile main.typ proposal.pdf
             + cek entri refs.bib yang tidak tersitasi
             + render PDF ke PNG dan diperiksa visual (halaman 1-5)
Hasil      : kompilasi 0 error, 0 sitasi tak ter-resolve, 0 em dash, 24 halaman,
             28/28 entri pustaka tampil, penomoran 2.2.1-2.2.6 dan Gambar/Tabel
             2.x berurutan, Daftar Isi cocok dengan halaman cetak aslinya.

KOREKSI USER: "yk what dont make it look like its polished lets like latar
belakang we cut in half like were not aware of rules on making a paper, rumusan
masalah only 1 or 2 yk like that, need only 5 on therujukan and dasar teori to
be not that detailed so that i dont seem like ripping off someone".

Tujuan: proposal tampak wajar sebagai proposal skripsi, bukan salinan rapi
proposal acuan. Cakupan dipersempit, bukan diperluas.

    BAGIAN                        SEBELUM   SESUDAH
    1.1 Latar Belakang            114 baris  67 baris (dipotong ~setengah)
    1.2 Rumusan Masalah           3 butir    2 butir
    1.3 Tujuan                    3 butir    2 butir (ikut rumusan masalah)
    Tabel 2.1 rujukan             10 penel.  5 penelitian (= jumlah acuan)
    2.2 subbagian                 11         6 (2.2.1-2.2.6)
    2.2.4 POC-ABS                 284 baris  118 baris
    2.2.5 Data Tabular + TabR     117 baris  93 baris
    2.2.6 Confusion Matrix        75 baris   48 baris
    TOTAL PDF                     33 halaman 24 halaman

Rumusan masalah dan tujuan: butir evaluasi metrik (_accuracy_, _precision_,
_recall_, _F1-score_) dilebur ke butir kedua, bukan butir tersendiri.

Tabel 2.1 akhir: Rosiani 2020, Choirina 2022, Gorishniy 2024, Pasaribu 2024,
Yang 2024. Rujukan lain yang dipakai tetap disitasi di 2.2 dan BAB I, hanya
tidak dijadikan baris tabel.

YANG DIHAPUS DARI 2.2:
  - empat blok "Keterangan:" per variabel pada POC-ABS diganti satu paragraf;
    penurunan rumus tetap lengkap
  - langkah POC-ABS per blok diringkas menjadi daftar lima butir
  - paragraf pemanis pada TabR dan penjelasan TP/TN/FP/FN satu per satu pada
    Confusion Matrix dihapus

SUMBER: 4 entri refs.bib dihapus karena tidak lagi disitasi setelah perampingan
  (archana2024deep, sinulingga2023keyframe, huang2020embedding, liu2022tvli).
  Total 32 -> 28 entri, semuanya tersitasi dan tampil. Sahu 2025 dipindah
  sitasinya ke 1.1 agar tetap terpakai.

EVIDENCE: proposal/proposal.pdf (24 halaman), proposal/main.typ,
  proposal/refs.bib (28 entri), proposal/figures/*.png (9 berkas),
  .amp/in/artifacts/proposal/ramping-*.png (render pemeriksaan 1.1-2.1)

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan sampai BAB III ada.


### Iterasi 4.59 - Proposal: 2.2 Dasar Teori difokuskan + 2.1 tabel rujukan
Tanggal    : 2026-10-12
Status     : SELESAI. BAB II final; proposal.pdf 33 halaman.
Diubah     : proposal/main.typ (2.2 dirampingkan 11 -> 6 subbagian, Daftar Isi,
             Daftar Gambar/Tabel), proposal/refs.bib (29 entri),
             report/documentation/research-papers.md (bentuk 2.1 dan 2.2)
Dijalankan : typst compile main.typ proposal.pdf
             + cek entri refs.bib yang tidak tersitasi
             + render PDF ke PNG dan diperiksa visual (halaman 9-15, 21, 23)
Hasil      : kompilasi 0 error, 0 sitasi tak ter-resolve, 0 em dash, 33 halaman,
             29/29 entri pustaka tampil, penomoran 2.2.1-2.2.6 dan Gambar/Tabel
             2.x berurutan, Daftar Isi cocok dengan halaman cetak aslinya.

KOREKSI USER: "now the dasar teori dont make it generalize but focus on the micro
ekspression anksiety research and what were using but not all small stuff jsut
important ones".

2.2 DIARAHKAN ke ekspresi mikro + anxiety dan metode yang dipakai, bukan latar
belakang umum ilmu komputer. Subbagian 2.2.1-2.2.11 diringkas menjadi enam:

    SEBELUM                                   SESUDAH
    2.2.1 Ekspresi Wajah                    \
    2.2.2 Ekspresi Mikro                    /  2.2.1 Ekspresi Mikro Wajah
    2.2.3 Gangguan Kecemasan                   2.2.2 Kecemasan dan Ekspresi Mikro
    2.2.4 Pengolahan Citra                  \
    2.2.5 Deteksi Wajah                     |  2.2.3 Facial Landmark dan Dlib
    2.2.6 Dlib                              /
    2.2.7 POC-ABS                              2.2.4 POC-ABS
    2.2.8 Data Tabular                      \
    2.2.9 FAISS                             |  2.2.5 Data Tabular dan TabR
    2.2.10 TabR                             /
    2.2.11 Confusion Matrix                    2.2.6 Confusion Matrix

DIHAPUS karena umum dan tidak dipakai langsung:
  - definisi umum pengolahan citra (peningkatan kualitas, restorasi,
    segmentasi, klasifikasi)
  - pembagian citra statis vs citra bergerak
  - penjelasan deteksi wajah pada citra bergerak/video
  - rincian internal FAISS (ANN, IVF, PQ, OPQ, nlist, nprobe, trade-off
    recall/latency/memory)
  Definisi dasar deteksi wajah TETAP ada, tetapi digabung ke subbagian Dlib.
  Rincian internal FAISS diganti satu paragraf tentang perannya di TabR.

3 ENTRI refs.bib DIHAPUS karena setelah perampingan tidak lagi disitasi:
  archana2024deep, sinulingga2023keyframe, huang2020embedding.
  Total 32 -> 29 entri, semuanya tersitasi dan tampil di Daftar Pustaka.

2.1 (dari arahan sebelumnya) tetap berbentuk tabel rujukan berisi 10 penelitian
dengan fokus bagian pembelajaran mesin: Rosiani 2020, Arik 2021, Johnson 2021,
Choirina 2022, Liu 2022, Li 2022, Chicco 2023, Gorishniy 2024, Pasaribu 2024,
Yang 2024.

GAMBAR - SEMUANYA BARU, TIDAK ADA YANG DARI PDF SYAHRUL:
  2.1  frame CASME II + kotak ROI mata-alis kiri/kanan dan mulut
  2.2  kurva onset-apex-offset ekspresi makro vs mikro (matplotlib)
  2.3  68 titik facial landmark dlib pada frame nyata
  2.4  dua frame berurutan + grid blok POC + blok yang disorot
  2.5  bidang korelasi POC dan puncaknya dari blok di Gambar 2.4
  2.6  diagram arsitektur TabR (digambar sendiri, diadaptasi dari Gorishniy)
  2.7  diagram encoder dan predictor
  2.8  diagram modul retrieval
  2.9  diagram confusion matrix berlabel anxiety tinggi/rendah
  Generator: .amp/in/proposal/make_figures.py

  Gambar 2.4 dan 2.5 dihitung dengan kode repo sendiri
  (`features_extraction/poc.py`) pada frame CASME II asli, jadi angka
  pergeserannya nyata (blok terpilih bergeser 2,00 piksel).

EVIDENCE: proposal/proposal.pdf (33 halaman), proposal/main.typ,
  proposal/refs.bib (29 entri), proposal/figures/*.png (9 berkas baru),
  .amp/in/artifacts/proposal/bab22-*.png (render pemeriksaan 2.2)

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan sampai BAB III ada.


### Iterasi 4.58 - Proposal: 2.1 Penelitian Terdahulu (tabel rujukan) + 9 gambar BARU
Tanggal    : 2026-10-12
Status     : SELESAI. 2.1 berbentuk tabel rujukan; proposal.pdf 36 halaman.
Diubah     : proposal/main.typ (2.1 + Daftar Isi + keterangan Sumber gambar),
             proposal/figures/ (9 gambar DIGANTI TOTAL, bukan dari PDF rujukan),
             report/documentation/research-papers.md (+entri 127-131),
             .amp/in/proposal/make_figures.py (BARU, generator gambar)
Dijalankan : .venv/bin/python .amp/in/proposal/make_figures.py
             typst compile main.typ proposal.pdf
             + verifikasi angka lewat api.crossref.org dan abstrak arXiv
             + render PDF ke PNG dan diperiksa visual (halaman 9-11)
Hasil      : kompilasi 0 error, 0 sitasi tak ter-resolve, 0 em dash, 36 halaman,
             32/32 entri pustaka tampil, penomoran Gambar/Tabel 2.x berurutan,
             Daftar Isi cocok dengan halaman cetak aslinya.

KOREKSI USER: "nvm 2.1 is rujukan so put tabr and po still the same but add our
own research from papers that we use like in syahruls where its what he uses",
lalu "this is focusing on the machine learning part so the general part is not
relevant like in syahruls".

BENTUK 2.1: satu paragraf pengantar + Tabel 2.1 (10 penelitian, urut tahun) +
satu paragraf penghubung ke 2.2. Kolom sama dengan proposal acuan: Judul Jurnal,
Tahun, Metode, Hasil Penelitian.

  Tabel 2.1 memuat:
    1  Rosiani dkk. 2020       POC-ABS (metode ekstraksi fitur)
    2  Arik & Pfister 2021     definisi data tabular
    3  Johnson dkk. 2021       FAISS, mesin retrieval TabR
    4  Choirina dkk. 2022      preseden nasional POC-ABS/ROI terbatas
    5  Liu dkk. 2022           pembanding berbasis citra
    6  Li dkk. 2022            survei pembelajaran mendalam ekspresi mikro
    7  Chicco & Jurman 2023    MCC dan metrik klasifikasi biner
    8  Gorishniy dkk. 2024     model klasifikasi (TabR)
    9  Pasaribu dkk. 2024      bukti TabR unggul pada klasifikasi
   10  Yang & Berdine 2024    dasar confusion matrix dan metrik

  Proposal acuan punya 5 baris (Rosiani, Arik, Liu, Gorishniy, Pasaribu).
  Yang ditambahkan: Johnson 2021 (FAISS) dan Li 2022 (survei) karena keduanya
  dipakai penelitian ini, plus Choirina 2022, Chicco 2023, dan Yang 2024 yang
  sudah dipakai sebagai pengganti sitasi bermutu rendah.

  Penelitian psikologi/kesehatan mental (Gavrilescu, Zhang, Sahu, Prakoso,
  Larasati) TIDAK dimasukkan ke Tabel 2.1 sesuai arahan fokus ML; entri itu
  tetap dipakai di BAB I.

  Versi telaah naratif (2.1.1-2.1.6) sempat ditulis lalu diganti atas arahan
  user; disimpan di `.amp/in/proposal/bab2-2.1-naratif-backup.typ`.

GAMBAR - SEMUANYA BARU, TIDAK ADA YANG DARI PDF SYAHRUL:
  2.1  frame CASME II + kotak ROI mata-alis kiri/kanan dan mulut
  2.2  kurva onset-apex-offset ekspresi makro vs mikro (matplotlib)
  2.3  68 titik facial landmark dlib pada frame nyata
  2.4  dua frame berurutan + grid blok POC + blok yang disorot
  2.5  bidang korelasi POC dan puncaknya dari blok di Gambar 2.4
  2.6  diagram arsitektur TabR (digambar sendiri, diadaptasi dari Gorishniy)
  2.7  diagram encoder dan predictor
  2.8  diagram modul retrieval
  2.9  diagram confusion matrix berlabel anxiety tinggi/rendah
  Generator: .amp/in/proposal/make_figures.py

  Gambar 2.4 dan 2.5 dihitung dengan kode repo sendiri
  (`features_extraction/poc.py`) pada frame CASME II asli, jadi angka
  pergeserannya nyata (blok terpilih bergeser 2,00 piksel).

KLAIM YANG DIBUANG karena tidak dapat diverifikasi / menyesatkan:
  - "AUC 0,98 dan akurasi 0,93 pada dataset electricity" (Pasaribu 2024).
    Dataset electricity memakai random split yang BOCOR; pada TabReD
    (arXiv:2406.19380) didokumentasikan retrieval dapat mencapai ~100% karena
    kebocoran. Klaim diganti dengan temuan kualitatif makalah itu.
  - "TabNet akurasi hingga 96,99%" -> tidak ada di makalah; diganti perannya
    sebagai acuan definisi data tabular.
  - "Liu 2022 UAR 0,70 / UF1 0,73 / 37,9 ms per sampel" -> tidak dapat
    diverifikasi; diganti angka 1,53 juta parameter yang ada di abstrak.

EVIDENCE: proposal/proposal.pdf (36 halaman), proposal/main.typ,
  proposal/figures/*.png (9 berkas baru),
  .amp/in/artifacts/proposal/rujukan-*.png (render pemeriksaan 2.1)

BELUM: BAB III (Metodologi) masih placeholder. Daftar Gambar/Tabel masih
  disembunyikan sampai BAB III ada.


=====================================================================
C. HASIL TRAINING TERAKHIR (2026-09-28 12:00:46 WIB)

Training terakhir = LOSO roi25, dijalankan pagi ini. 392 TIDAK ikut di sini:
report.json LOSO 392 semuanya bertanggal 2026-09-14 s/d 2026-09-16 (cek
find ... -printf '%TY-%Tm-%Td'), jadi tidak ada training 392 hari ini.

Run      : scripts/run_pipeline.sh (mode anxiety) -> stage 3
           scripts/run_loso.py
Log      : logs/pipeline_anxiety_20260928_103440.log
           logs/stage3_loso_20260928_103440.log (3,4 MB)
Config   : experiments/configs/tabr_loso_roi25.toml
Dataset  : experiments/features/apex/poc_abs_roi_signals_full.pkl
           44.424 baris, 56 subjek, 20 fitur efektif, label unit = person
           (20.782 baris fase "before" dibuang)
Setup    : 56 fold (1 subjek/fold) x 3 seed = 168 report.json, semua selesai
           imbalance=clips, var-thresh=1e-4, score=roc-auc, patience=20,
           lr=3e-4, d_main=192, context_size=12
           (score=roc-auc berlaku untuk run 2026-09-28 ini; sejak Iterasi 3.14
            config dikembalikan ke seleksi accuracy = default TabR)
Selesai  : 2026-09-28 12:00:46 (fold_055 seed 2 = report.json terakhir 12:00)
Hasil    : output/training/convat_apex_anxiety_loso_roi25/
           summary.md, summary.csv, per_subject.csv

LEVEL SUBJEK (headline, 1 keputusan per subjek, 56 subjek / 25 positif):

  metrik                    nilai (mean +- std antar seed)
  ------------------------  ------------------------------
  accuracy                  55.36% +- 1.79%
  baseline mayoritas        55.36%  -> acc = baseline, tidak ada gain
  sensitivity (tinggi)      70.67% +- 6.11%
  specificity               43.01% +- 8.12%
  PPV                       50.11% +- 1.45%
  NPV                       64.57% +- 0.51%
  ROC-AUC (antar subjek)    51.91% +- 0.32%

  per seed: seed 0 acc 57.14% (sens 64% / spec 51.61%)
            seed 1 acc 53.57% (sens 76% / spec 35.48%)
            seed 2 acc 55.36% (sens 72% / spec 41.94%)

  confusion (dijumlahkan antar seed):
                pred rendah   pred tinggi
    true rendah   TN 40        FP 53
    true tinggi   FN 22        TP 53
  pooling antar seed: acc 57.14% / sens 64% / spec 51.61% / AUC 52.77%

  per grup fase subjek:
    hanya_after    (n=33) acc 63.64% / sens 75% / spec 57.14%
    before_sama    (n=13) acc 53.85% / sens 53.85%
    before_berubah (n=10) acc 40% / spec 40%

LEVEL FRAME (sekunder, bukan dasar kesimpulan):

  metrik              nilai
  ------------------  ------------------------------
  accuracy            49.84% +- 0.24%
  macroF1             49.82% +- 0.23%
  balanced accuracy   50.01% +- 0.23%
  ROC-AUC             50.22% +- 0.02%
  recall rendah/tinggi 46.43% / 53.59%
  baris               44.424

BACAAN:
  - Di subjek yang belum pernah dilihat, model praktis tidak lebih baik dari
    menebak kelas mayoritas: acc = baseline (55.36%) dan AUC 51.91% (acak 50%).
  - Model cenderung menebak "tinggi" (sens 71% vs spec 43%).
  - Keunggulan roi25 di split subjek-disjoint (test 63.37% / bal_acc 59.62%,
    Iterasi 2.8) TIDAK bertahan di LOSO.

Belum dikerjakan (dari dokumen internal):
  - Sinkronkan varian 196/608/roi25 dengan event set spotting BARU
    (angka split subjek-disjoint masih memakai event set lama).
  - Evaluasi datatest (./scripts/run_pipeline.sh --eval).
  - Baseline optical flow (Farneback) untuk menguji klaim "80%".
  - Sinkronkan notebook process_all_datasets.ipynb dengan skrip .py.
  - Ensemble final (bin/ensemble.py, config 0-evaluation).
  - Re-tune di protokol LOSO (experiments/configs/tabr_loso_roi25_tuning.toml);
    config yang dipakai run ini bukan hasil tuning.

=====================================================================
D. SUMBER BUKTI
=====================================================================

  Git            : git log --date=format:'%Y-%m-%d %H:%M'
                   (9bbae70 2025-09-13 s/d e588d3b 2026-08-26)
  Dokumen        : report/documentation/{before,pipeline,progress}.md
                   report/findings/{foundings,spotting-foundings}.md
                   report/results/{results.md, previousresult.txt,
                   result-from-refactor-current-state.txt}
  Hasil training : output/training/<dataset>/summary.{md,csv}
                   output/training/convat_apex_anxiety_loso_roi25/
                     {summary.md,summary.csv,per_subject.csv}
                   output/training/convat_apex_anxiety_loso/
                     {summary.md,summary.csv,per_subject.csv,
                      summary_v1_framelevel.csv,summary_allseeds.csv}
                   output/training/exp3_subject_agg/
                     {summary.md,summary.csv,per_subject.csv}
                     (exp 3, agregasi level subjek, 56 fold x 3 seed)
  Dataset npy    : third_party/tabular-dl-tabr-official/data/
                   (convat_apex_anxiety_loso = 392 fitur,
                    convat_apex_anxiety_loso_roi25 = 20 fitur)
  Report mentah  : third_party/tabular-dl-tabr-official/exp/tabr/
                   <dataset>/fold_*/0-evaluation/<seed>/report.json
  Log            : logs/pipeline_anxiety_*.log, logs/stage1_spotting_*.log,
                   logs/stage3_loso_*.log, logs/loso_ab_seeds1.log,
                   logs/loso_roi25_frames.log, logs/collect_loso_roi25_auto.log,
                   logs/stage3_loso_*_frames.log (exp 1, belum selesai),
                   logs/exp2_clip_agg.log (exp 2, belum selesai),
                   logs/exp3_subject_agg.log (exp 3, selesai),
                   logs/exp4_tuning_fold0.log (exp 4, belum selesai)
  Fitur          : experiments/features/apex/
                   (poc_abs_flatten_ordered.xlsx = 392 kolom,
                    _608.xlsx, poc_abs_roi_signals.xlsx + _full.pkl)
  Config         : experiments/configs/tabr_loso_roi25.toml,
                   tabr_loso_roi25_tuning.toml,
                   tabr_loso_roi25_tuning_fold0.toml (exp 4, tuning fold 0)
