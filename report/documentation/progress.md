PROGRES PROYEK SKRIPSI - MICRO-EXPRESSION + TabR
==================================================

Dokumen ini adalah TITIK MASUK untuk sesi baru.
Baca dulu: before.md (state asli), foundings.md (temuan+rencana),
spotting-foundings.md (detail spotting), results.md (baseline angka).

Diperbarui : 2026-10-06


=====================================================================
RIWAYAT SEMUA UJI - (tanggal) (perubahan dari kondisi asli) (hasil)
=====================================================================

Format tiap entri HANYA tiga baris:

  Tanggal             : kapan dijalankan
  Perubahan dari asli : apa yang diubah relatif terhadap kondisi asli
  Hasil               : angka yang benar-benar tercatat di repo

"Kondisi asli" = kode warisan sebelum kampanye perbaikan: TabR resmi,
split level-EVENT yang BOCOR subjek, 392 fitur POC-ABS, tanpa LOSO, tanpa
normalisasi per subjek, tanpa baseline netral, tanpa fitur temporal, tanpa
pembanding logistik/GBDT.

PERINGATAN: semua angka bertanda (BOCOR) tidak sah sebagai performa -
orang yang sama ada di train dan test. Angka LOSO level-frame juga tidak
sah (lihat catatan di changes-log bagian A). Yang sah: LOSO level subjek.

---------------------------------------------------------------------
A. TITIK NOL
---------------------------------------------------------------------

Tanggal             : 2025-09-13
Perubahan dari asli : -
Hasil               : Titik nol. Repo skripsi terbentuk (commit 9bbae70,
                      328bcf3, ffe491c). Belum ada angka evaluasi.

Tanggal             : 2026-04-06
Perubahan dari asli : Ganti model TabR kustom ke TabR resmi (Yandex),
                      fitur 392 POC-ABS, split qholdout level event
Hasil               : train 97.36% / val 75.65% / test 74.28%,
                      macroF1 72.81% (BOCOR subjek). Gap train-test 23
                      poin = overfitting jelas.

Tanggal             : 2026-08-25
Perubahan dari asli : TabR kustom v19/v20 (balanced clips, m=8, pat=8,
                      freeze=11)
Hasil               : internal 69.15% / eksternal 72.63% (BOCOR subjek).

Tanggal             : 2026-08-25
Perubahan dari asli : Tambah fitur alis -> 608 kolom, split qholdout
Hasil               : acc 82.87% / macroF1 81.32%, TAPI train 99.91%
                      (BOCOR subjek + overfit ekstrem). Angka tertinggi
                      yang pernah dicatat, dan yang paling tidak sah.

Tanggal             : 2026-08-25
Perubahan dari asli : Inferensi ke data tanggal baru (datatest, 98 subjek)
Hasil               : acc 61-72%, macroF1 39-47%, recall kelas "rendah"
                      hanya 3-7% -> model hampir selalu menebak "cemas".

---------------------------------------------------------------------
B. MENGHAPUS KEBOCORAN SUBJEK (angka turun, tapi sah)
---------------------------------------------------------------------

Tanggal             : 2026-08-31
Perubahan dari asli : Split evaluasi diganti GroupShuffleSplit subjek-
                      disjoint seed 72 (33/11/12 subjek) menggantikan split
                      level event. 392 fitur, 15 seed.
Hasil               : test 61.23% / macroF1 53.58% / bal_acc 55.16% /
                      AUC 58.39%. Gap train-test 23 -> 2,4 poin.
                      Turun ~13 poin = efek kebocoran yang dihapus, BUKAN
                      regresi model.

Tanggal             : 2026-09-01
Perubahan dari asli : Buang kolom t,m yang lossless -> 196 fitur
Hasil               : test 59.98% / macroF1 47.71% / bal_acc 52.13%.
                      Justru turun; reduksi fitur tidak menolong.

Tanggal             : 2026-09-01
Perubahan dari asli : 392 fitur + alis kiri/kanan -> 608 fitur
Hasil               : test 58.60% / macroF1 54.19% / bal_acc 54.50%,
                      gap train-test 9,1 poin. Menambah overfitting tanpa
                      menambah sinyal subjek-baru.

Tanggal             : 2026-09-01
Perubahan dari asli : Fitur per-ROI menggantikan vektor blok 7x7 ->
                      roi25 (5 sinyal x 5 area = 25 fitur/frame)
Hasil               : test 63.37% / macroF1 59.64% / bal_acc 59.62% /
                      AUC 63.81%, gap 1,1 poin. Terbaik di split subjek-
                      disjoint. (Tidak bertahan di LOSO - lihat bawah.)

Tanggal             : 2026-09-01 (malam)
Perubahan dari asli : Re-spotting dengan sinyal per-ROI + re-ekspor 392
                      (event set baru), split sama
Hasil               : Split membesar 34.530/14.668/14.962 frame.
                      Run 2: test 62.71% / macroF1 50.67% / bal_acc 54.40%.
                      Recall kelas "rendah" turun 26.1% -> 17.1% (makin
                      bias mayoritas). Ensemble 5 seed: 63.57% tapi
                      macroF1 48.53% -> run 1 lebih sehat untuk macroF1.

---------------------------------------------------------------------
C. LOSO (1 subjek = test, subjek baru yang belum pernah dilihat)
---------------------------------------------------------------------

Tanggal             : 2026-09-17
Perubahan dari asli : Protokol LOSO murni subjek-disjoint, skrip lama
                      (metrik level FRAME)
Hasil               : frame acc 60.41% / macroF1 44.80% / AUC 51.51%;
                      recall kelas rendah 10.1%. TIDAK SAH ditafsirkan:
                      test tiap fold = 1 subjek = 1 kelas, jadi metrik
                      frame hanya mengukur komposisi kelas dalam subjek.

Tanggal             : 2026-09-28 (TRAINING TERAKHIR)
Perubahan dari asli : LOSO roi25, 56 fold x 3 seed, metrik dipindah ke
                      LEVEL SUBJEK (1 keputusan per subjek)
Hasil               : accuracy 55.36% = baseline mayoritas 55.36%.
                      sensitivity 70.67% / specificity 43.01%,
                      AUC 51.91% (acak 50%). Per seed 57.14/53.57/55.36%.
                      BACAAN: model belum bisa membedakan subjek baru.
                      Keunggulan roi25 di split subjek-disjoint TIDAK
                      bertahan.

Tanggal             : 2026-09-29
Perubahan dari asli : Diagnostik sinyal level subjek memakai logistik
                      (bukan TabR) pada matriks fitur yang sama
Hasil               : TIDAK ada sinyal: AUC 52.52% (mean+std) / 44.77%
                      (mean saja) / 44.13% (frame->rata subjek);
                      permutation test p = 0.280.
                      MEKANISME: varian fitur ANTAR subjek > varian DALAM
                      subjek (mulut_mean_m 0.353 vs 0.201) -> fitur lebih
                      kuat mengkodekan SIAPA orangnya daripada kecemasannya.
                      Cacat ada di representasi, di hulu model.

Tanggal             : 2026-09-29
Perubahan dari asli : Agregasi level subjek (1 baris = 1 subjek, mean+std)
Hasil               : accuracy 44.05% (DI BAWAH baseline 55.36%),
                      sensitivity 24.00% / specificity 60.22%,
                      AUC 41.29% (di bawah acak). Negatif.

---------------------------------------------------------------------
D. PERBAIKAN REPRESENTASI & PROTOKOL (2026-10-06)
---------------------------------------------------------------------

Tanggal             : 2026-10-06
Perubahan dari asli : Baseline netral per subjek (neutral.png = median 10
                      frame awal video) menggantikan acuan frame onset.
                      Re-ekstraksi penuh memperbaiki tabel fitur basi.
Hasil               : Tabel 65.206 -> 97.303 baris; sebelum 20.782 ->
                      52.837; sebelum/tidak 0 -> 13.720 baris; subjek
                      sebelum 23 -> 56. Artefak "sebelum selalu anxiety"
                      hilang.

Tanggal             : 2026-10-06
Perubahan dari asli : Gerbang keputusan: uji berpasangan dalam-subjek
                      (orang yang sama, wajah sama, label beda; 18 subjek
                      berubah vs 38 kontrol)
Hasil               : ONSET: 20/25 fitur "signifikan" TAPI kontrol 25/25
                      -> itu EFEK SESI, bukan kecemasan.
                      NETRAL: 0/25 di KEDUA grup -> baseline netral
                      berhasil menghapus artefak sesi, dan tidak
                      menyisakan sinyal.
                      Klasifikasi dalam-subjek: onset acc 0.5833
                      (p=0.2637); netral 0.5278 (p=0.4726).
                      KESIMPULAN: POC-ABS tidak membawa sinyal kecemasan
                      yang bisa dipakai.

Tanggal             : 2026-10-06
Perubahan dari asli : Baseline pembanding logistik/GBDT (protokol LOSO
                      identik) + permutation test
Hasil               : onset 25   : logistic 0.5000 (p=0.6517) |
                                  gbdt 0.5000 (p=0.6517)
                      onset 125  : logistic 0.4464 (p=0.8557) |
                                  gbdt 0.5893 (p=0.1692)
                      neutral 125: logistic 0.5714 (p=0.2189) |
                                  gbdt 0.6071 (p=0.0796)
                      Baseline mayoritas 0.5536. Terbaik 0.6071 - di atas
                      baseline tapi BELUM signifikan. Model sederhana pun
                      tidak menemukan sinyal -> masalahnya representasi.

Tanggal             : 2026-10-06 11:24
Perubahan dari asli : Config anti-overfitting (parameter 487.681 ->
                      44.865; batch 128 -> 8; context_size 12 -> 8;
                      weight_decay 1e-5 -> 1e-3). Fitur netral+temporal
                      237 kolom, agregasi subjek, 56 fold x 3 seed.
Hasil               : accuracy 0.5952 +- 0.0899 (CI 0.4763-0.7242),
                      sensitivity 0.4133 / specificity 0.7419,
                      MCC +0.1706, balAcc 0.5776. Baseline mayoritas
                      0.5536. +4,16 poin TAPI CI memuat baseline ->
                      belum terbukti lebih baik dari menebak.
                      KOREKSI: klaim "overfitting turun" TIDAK SAH (itu
                      train-vs-VAL, dan val dipakai memilih best_epoch).
                      Gap jujur train-vs-TEST justru MEMBESAR: 27,49 ->
                      33,27 poin. Bias BERBALIK: sens 70.67 -> 41.33,
                      spec 43.01 -> 74.19 (59% subjek cemas terlewat).

Tanggal             : 2026-10-06
Perubahan dari asli : Re-ekstraksi v2 (3 bug ekstraksi diperbaiki: tanda
                      arah dibuang, frame onset hilang, sinyal apex
                      dipalsukan) -> 35 fitur statis / 185 temporal
Hasil               : Tabel 97.317 -> 104.194 baris, frame minimum 2 -> 1.
                      GERBANG: v2 temporal 0.6667 (p=0.0746) - TERBAIK
                      sejauh ini, arah benar, TAPI belum signifikan (5%).
                      v2 statis 0.4167 (p=0.7910); dengan n=36 selisih itu
                      di dalam derau.
                      Kontrol bersih di semua set (0/35, 0/185).

Tanggal             : 2026-10-06
Perubahan dari asli : v3: re-spotting block_size 9 (dari 7), definisi ROI
                      kanonik (mata = kelopak saja, tidak lagi tumpang
                      tindih dengan alis), typo vektor.py diperbaiki
Hasil               : Metadata 6.878 -> 6.972 event; fitur 100.817 baris x
                      35 statis / 185 temporal; 0 error.
                      GERBANG: v3 statis 0.4444 (p=0.7761); v3 temporal
                      0.6111 (p=0.1990). LEBIH RENDAH dari v2 temporal
                      (0.6667) tapi dengan n=36 selisih itu di dalam derau
                      -> jangan diklaim membaik maupun merugikan.
                      Perbaikan sahih secara rekayasa, tidak diterjemahkan
                      jadi sinyal terukur.

Tanggal             : 2026-10-06
Perubahan dari asli : Training v3 dengan config cross-entropy (370 fitur)
Hasil               : Rata-rata antar seed: accuracy 0.5238 / MCC +0.0154 /
                      balAcc 0.5054. (Angka seed-ensemble-nya 0.6071 -
                      lihat entri koreksi collector di bawah.) Angka ini
                      sempat dilaporkan sebagai "lebih buruk dari mayoritas"
                      -> DICABUT, itu CI seed 0.

Tanggal             : 2026-10-06
Perubahan dari asli : v3_acc: fitur v3 + config AKURASI (isolasi bersih
                      efek fitur vs efek kriteria epoch)
Hasil               : Rata-rata antar seed: accuracy 0.5179 / MCC +0.0054
                      (seed-ensemble 0.5357 / +0.0464).
                      Membuktikan penyebab berhenti-dini adalah JUMLAH
                      FITUR, bukan cross-entropy: fold berhenti di epoch
                      <=1 sebanyak v3acc 97/168 vs v3 CE 101/168, sedangkan
                      reg hanya 34/168.

Tanggal             : 2026-10-06
Perubahan dari asli : Koreksi bug collector ("pooled antar seed"
                      sebenarnya cuma seed 0) -> 3 run dikumpulkan ulang
Hasil               : ANGKA YANG BENAR (seed-ensemble):
                        reg   237 fitur, akurasi        : 62.50%
                               CI 49.41-73.99%, MCC +0.2272, balAcc 60.32%
                        v3    359 fitur, cross-entropy  : 60.71%
                               CI 47.63-72.42%, MCC +0.1910, balAcc 59.10%
                        v3acc 359 fitur, akurasi        : 53.57%
                               CI 40.70-65.98%, MCC +0.0464, balAcc 52.26%
                        d3    60 fitur, akurasi         : 42.86%
                               CI 30.77-55.86%, MCC -0.1561, balAcc 42.19%
                        baseline mayoritas 55.36%
                      KETIGA CI MEMUAT baseline 55.36% -> tidak ada satu
                      pun yang terbukti lebih baik dari menebak kelas
                      mayoritas, TERMASUK reg.
                      CATATAN d3: 60 fitur itu TERBURUK, tapi d3 juga
                      mengubah KELUARGA fitur (statis saja, tanpa temporal),
                      jadi ia BUKAN uji dimensi yang bersih.
                      HANYA ambang-dari-val yang terbukti berguna (bias
                      prediksi -0.1190 -> +0.0238).

Tanggal             : 2026-10-06
Perubahan dari asli : Reduksi dimensi lewat --drop-features (target 180
                      dan 60 fitur)
Hasil               : INVALID. Bug: regex dijalankan SEBELUM agregasi,
                      padahal sufiks `_std` baru ada SESUDAH -> `_std$`
                      mencocokkan 0 kolom (diam-diam), DAN fitur tersensor
                      `*_max_m` ikut kembali. Bukti: d1 dan d2 sama-sama
                      369 fitur dan hasilnya identik bit-per-bit
                      (0.4286, MCC -0.1762). Sudah diperbaiki; uji dimensi
                      yang bersih BELUM pernah jalan.

Tanggal             : 2026-10-06
Perubahan dari asli : Keluarga fitur KEDUA: geometri wajah + head pose
                      (21 kolom geo_*) dari 68 landmark yang sudah
                      dihitung spotting, dinormalkan terhadap wajah netral
                      tiap orang (Differential AU, StressGAT)
Hasil               : GAGAL - keluarga geometri tidak membawa sinyal.
                      GERBANG (orang sama, wajah sama, label beda):
                        POC statis (35) : 0/35 signifikan, acc 0,4444, p 0,7761
                        GEOMETRI (21)   : 0/21 signifikan, acc 0,4444, p 0,7512
                        GABUNGAN (206)  : 0/206, acc 0,6111, p 0,2040
                      KUNCI: acc gabungan 0,6111 IDENTIK dengan POC temporal
                      saja (0,6111) -> geometri menyumbang NOL; angka itu
                      seluruhnya dari fitur POC yang sudah ada.
                      LOSO (385 fitur, 56 fold x 3 seed, 0 gagal):
                        accuracy 0,5595 +- 0,0103 (seed-ensemble 0,4821,
                        CI 0,3567-0,6099 MEMUAT baseline 0,5536);
                        MCC +0,1007; per seed 0,5714/0,5536/0,5536 (datar).
                        Per grup KEDUANYA negatif (Simpson):
                        before_sama 0,4211 vs 0,6316; before_berubah
                        0,6111 vs 0,9444.
                      Pembanding sederhana LEBIH BURUK: logistic 0,4464,
                      gbdt 0,3571 (di bawah acak).
                      Bandingkan run terbaik (reg, POC saja 237 fitur):
                      0,6250 / CI 0,4941-0,7399 / MCC +0,2272.
                      JADI MENAMBAH GEOMETRI MEMPERBURUK: fitur 237 -> 385
                      (d/n 5,4 -> 8,8), fold berhenti di epoch <=1 naik
                      34/168 -> 53/168.
                      BUG SAYA (ditemukan saat memeriksa hasil, sudah
                      diperbaiki): ambiguitas planar solvePnP pada roll ->
                      1.472 baris (1,46%) |roll| > 170 di 5 subjek,
                      geo_head_motion sampai 359,86 derajat/frame. Sebab: 9
                      dari 10 neutral.png subjek abdillah memberi roll ~0,
                      satu memberi +179,66 (orang & sesi sama). Verifikasi
                      lama saya hanya 400 frame dari beberapa klip sehingga
                      tidak menangkapnya. Perbaikan: normalize_roll() melipat
                      roll ke (-90,90]; terverifikasi roll maks |8,64| pada
                      600 frame dan head_motion maks 8,14.
                      ANGKA RUN INI BELUM FINAL karena fitur roll masih rusak
                      saat training. Kesimpulan tidak berubah: 17 dari 21
                      fitur bersih sudah punya kesempatan dan tidak ada yang
                      lolos FDR.
                      NUANSA JUJUR: p mentah terkecil - POC
                      alis_kanan_mean_abs_y 0,0075 (kontrol 0,9201);
                      geometri geo_lip_corner_drop 0,0352 (kontrol 0,4727).
                      Tidak lolos FDR (n=18, 21-35 fitur, ambang ~0,002-0,005)
                      -> "tidak terdeteksi pada N ini", bukan "terbukti nol".
                      !!! DIKOREKSI di entri berikutnya: kesimpulan "geometri
                      menyumbang nol" TIDAK SAH karena 16 dari 42 kolom
                      geometri tidak pernah sampai ke model.

Tanggal             : 2026-10-06
Perubahan dari asli : Perbaikan metodologi batch A (6 bug): urutan
                      variance-vs-scale, permutasi gerbang jadi berpasangan,
                      guard ambang inf, label laporan, --force diteruskan
                      ke stage 6
Hasil               : BUG #1 (membatalkan kesimpulan entri di atas):
                      VarianceThreshold(1e-4) jalan pada nilai MENTAH sebelum
                      scaler -> itu filter SKALA, bukan filter "fitur statis".
                      Terukur: LAMA geo lolos 26/42 (total 385 kolom);
                      BARU geo lolos 42/42 (total 402). 16 kolom geometri
                      tidak pernah masuk model, termasuk geo_lip_corner_drop
                      (p gerbang 0,0352, fitur geometri TERKUAT) dan
                      geo_mouth_open (fitur yang direkomendasikan paper BINUS).
                      Jadi "geometri = nol" belum teruji; harus diulang.
                      BUG #2: roll solvePnP ambigu (lihat entri di atas);
                      tabel tersimpan masih rusak -> butuh re-ekstraksi.
                      BUG #3: permutasi gerbang global -> berpasangan.
                      p: POC 0,7761 -> 0,8010; geometri 0,7512 -> 0,7363;
                      gabungan 0,2040 -> 0,1542. Kesimpulan tidak berubah.
                      BUG #4: ambang Youden bisa = inf (terjadi 1/56 fold).
                      Laporan menulis "inf +- nan"; sekarang 0,5250 +- 0,0322.
                      Ini merusak satu-satunya lever yang terbukti berguna.
                      BUG #5: heading "Level subject" untuk tabel frame, dan
                      judul gerbang di-hardcode "(POC-ABS)".
                      BUG #6: --force pipeline TIDAK diteruskan ke stage 6, jadi
                      `run_pipeline_v3.sh --force` mengekstraksi ulang fitur
                      TAPI melewati semua 56 fold dan melaporkan SELESAI dengan
                      hasil LAMA. Sudah diteruskan; diverifikasi lewat dry-run.
                      VERIFIKASI pada artefak nyata tanpa training; re-run
                      belum dijalankan. Perintah: ./scripts/run_pipeline_v3.sh --force

---------------------------------------------------------------------
E. RINGKASAN SATU BARIS PER ERA
---------------------------------------------------------------------

Era                        Metrik test terbaik yang tercatat
-------------------------  ------------------------------------------
Asli (BOCOR subjek)        acc 82.87% (tidak sah)
Setelah subjek-disjoint    acc 63.37% (roi25)
LOSO (sah, level subjek)   acc 62.50% (reg) - CI memuat baseline 55.36%
Kesimpulan sementara       Belum ada konfigurasi/fitur POC-ABS yang
                           terbukti lebih baik dari menebak mayoritas
                           pada subjek baru.



=====================================================================

1. APA PROYEK INI
------------------

  Klasifikasi tingkat kecemasan (tinggi/rendah) dari video wajah
  dengan mendeteksi micro-expression lalu memasukkannya ke model
  TabR.

  Pipeline:
    Video (.avi 60fps RealSense / .webm 30fps webcam)
      -> dlib 68 landmark -> crop 5 ROI (mata, alis, mulut)
      -> POC-ABS per frame (vs frame-0 baseline) -> vektor dx,dy
      -> kuadran Q1-Q4 -> sinyal magnitude -> cari apex (SavGol 7,
         find_peaks, top-5) -> klip event (onset..offset)
      -> fitur tabular (392 / 608 kolom)
      -> TabR resmi (Yandex) -> klasifikasi

  PENTING: fps aktual = 60 (.avi) / 30 (.webm), BUKAN 200 seperti
  dokumentasi. Micro-expression = 1/25-1/5 dtk = 2.4-12 frame di 60fps.


=====================================================================

2. DOKUMEN YANG ADA (baca urutan ini)
--------------------------------------

  - before.md              : snapshot state asli + cara menjalankan
                             + lampiran instalasi & backup
  - foundings.md           : temuan umum + rencana 5 fase + daftar
                             kode mati (5 file sudah dihapus)
  - spotting-foundings.md  : detail cara kerja spotting + 6 titik
                             lemah + prioritas perbaikan (1 & 3
                             SUDAH diimplementasikan)
  - results.md             : angka baseline SEBELUM perubahan
                             (TabR resmi 0.7428 test, dll)
  - summary/progress.md    : dokumen ini


=====================================================================

3. STATUS PENGERJAAN
---------------------

  SELESAI:
  - Backup codebase    : /home/finny/projects/Skripsi-backup-2026-08-25/
                         (668 MB, 81.829 file, tanpa .venv)
  - Instalasi lengkap  : uv sync (torch 2.9.1+cu128, CUDA aktif,
                         faiss 1.14.1, dlib 20.0.0, opencv 4.11.0,
                         nbconvert 7.17.1), Python 3.12.13 via uv
  - Model dlib         : preprocess-anxiety/models/
                         shape_predictor_68_face_landmarks.dat (96MB)
  - Repo TabR resmi    : third_party/tabular-dl-tabr-official/
                         di-clone (punya bin/go.py)
  - Kernel jupyter     : 'skripsi' terdaftar (ipykernel, venv python)
  - Kode mati dihapus  : core/tabr_v2.py, tabr_faithful.py, utis.py,
                         conv1_base.py, qholdout_copy.py
  - Fix spotting #1    : POC-ABS (frame-0 baseline) - flag
                         USE_ABS_BASELINE (default True)
  - Fix spotting #3    : window smoothing TETAP 7 frame
                         (apex/apex_smoother.py)
  - Progress bar       : semua stage (spotting + ekspor fitur = tqdm;
                         npy = marker [1/7]-[7/7]; training = baris
                         val/test live)
  - Config TOML TabR   : exp/tabr/convat_apex_anxiety/0-tuning.toml
                         (dibuat ulang dari parameter log Optuna)

  DATA (semua ADA di folder dataset/):
  - anxiety_raw/  : 11 GB, 112 subjek (before/anxiety 41, before/tidak
                    15, after/anxiety 25, after/tidak 31), 560 .avi
                    (60fps RealSense) + 560 .webm (30fps webcam)
  - datatest/     : 2.7 GB, 98 subjek (51 di 15_04_2026, 47 di
                    17_04_2026), labeled/{tanggal}/{anxiety_rendah,
                    anxiety_tinggi}/subjek/q1-q5/*.webm (490 video)
  - CAS-ME2 (13GB), casme, color, putri : untuk baseline/percobaan

  STATUS PIPELINE:
  - datatest: spotting SELESAI 490/490 (metadata.xlsx ada), fitur
              ekspor SELESAI (output/apex/datatest/features).
              Belum: evaluasi model di datatest (opsional, --eval)
  - anxiety : spotting ulang SUDAH dijalankan; fitur 392 + npy utama
              SUDAH di-export ulang. Split terbaru untuk 392:
              train 34.530 / val 14.668 / test 14.962 frame.
  - training TabR: SUDAH dijalankan 2x untuk 392 fitur.
                   Run 1 = test 0.6123 / macroF1 0.5358 / bal_acc 0.5516
                   Run 2 = test 0.6271 / macroF1 0.5067 / bal_acc 0.5440
                   Hasil terbaik lama antar varian: roi25 = 0.6337 /
                   0.5964 / 0.5962


=====================================================================

4. CARA MENJALANKAN (perintah utama)
-------------------------------------

  Semua via scripts/run_pipeline.sh (stage berurutan, progress bar):

    ./scripts/run_pipeline.sh                        # datatest
    ./scripts/run_pipeline.sh --mode anxiety         # dataset utama
    ./scripts/run_pipeline.sh --stage 1              # hanya spotting
    ./scripts/run_pipeline.sh --from 2               # mulai stage 2
    ./scripts/run_pipeline.sh --force                # ulang walau ada
    ./scripts/run_pipeline.sh --dry-run              # rencana saja
    ./scripts/run_pipeline.sh --abs 0                # A/B: frame berurutan
    ./scripts/run_pipeline.sh --eval                 # datatest: eval model

  Stage:
    0 = pra-syarat (cek env, data, dll)
    1 = spotting     -> output/apex/datatest/dataset/... (klip event)
    2 = ekspor fitur -> output/apex/datatest/features/ (608 kolom)
                        atau output/apex/features/poc_abs_flatten_ordered.xlsx
                        (392 kolom, mode anxiety)
    3 = anxiety: ekspor npy (third_party/.../data/convat_apex_anxiety/)
        datatest: evaluasi model (--eval)
    4 = anxiety: training TabR (bin/go.py 0-tuning.toml, 30 trial)

  Script pendukung:
    scripts/switch_spotting_config.py --mode datatest --abs 1
      (ubah config notebook spotting; script memakai env var SPOT_*)
    preprocess-anxiety/process_all_datasets_script.py
      (spotting; env: SPOT_DATASET_ROOT, SPOT_OUTPUT_ROOT,
       SPOT_VIDEO_EXT, SPOT_ABS)
    preprocess-anxiety/export_apex_poc_abs_ordered_script.py
      (fitur anxiety, 392 kolom)
    preprocess-anxiety/export_apex_poc_abs_ordered_v2_script.py
      (fitur datatest, 608 kolom)

  A/B test spotting: ganti --abs (1 = POC-ABS, 0 = frame berurutan),
  jalankan ulang --stage 1 --force, bandingkan hasilnya.


=====================================================================

5. TEMUAN PENTING / GOTCHA (harus diingat)
-------------------------------------------

  1. fps aktual 60/30, BUKAN 200 -> window smoothing 7 frame WAJIB
     (31 frame = 517ms akan menghapus micro-expression).
  2. Subjek BOCOR antar split di semua strategi lama (event_clip_split,
     balanced, qholdout, qwalkforward). Hanya LOSO yang aman.
     -> Fase 1 SUDAH dikerjakan; semua angka split lama sekarang usang.
  3. Kode optical flow TIDAK ADA di repo - klaim "80%" tidak bisa
     dibandingkan sampai baseline dibuat.
  4. ViT belum layak: GPU 4GB, data kecil, patch menghapus sinyal
     <1 piksel. Evaluasi dulu (Fase 1) baru pikirkan ViT.
  5. Path lama /home/ryuko/... masih ada di notebook lama - jangan
     pakai notebook itu; pakai script (.py) yang sudah digenerate.
  6. Loop "Event signals" di notebook = opsional (visualisasi),
     LAMBAT (sekuensial, ~1-2 jam), bukan input training.
  7. Config TOML 0-tuning.toml adalah REKREASI (asli hilang).
     Hasil training bisa beda dari results.md - itu wajar.
  8. *.md tidak ter-track git (gitignore) - dokumen ini & sebelum-nya
     tidak akan ter-commit kecuali gitignore diubah.
  9. nbconvert menyangga output - SELALU pakai script .py untuk
     progress live (sudah diatur di run_pipeline.sh).


=====================================================================

6. RENCANA BERIKUTNYA (prioritas)
----------------------------------

  A. Sinkronkan varian 196/608/roi25 dengan event set spotting BARU,
     supaya perbandingan dengan retrain 392 sekarang benar-benar
     apple-to-apple.
  B. Evaluasi datatest: ./scripts/run_pipeline.sh --eval
  C. Jalankan variant qholdout/qwalkforward yang SUDAH subjek-disjoint,
     lalu bandingkan dengan baseline utama.
  D. Buat baseline optical flow (Farneback) untuk perbandingan adil.
  E. Sinkronkan notebook process_all_datasets.ipynb / spotting.py
     dengan script yang sekarang jadi sumber kebenaran.
  F. Config 0-evaluation untuk ensemble final (bin/ensemble.py)
     sudah dibetulkan; tinggal dipakai konsisten pada run berikutnya.


=====================================================================

7. REFERENSI ANGKA (dari results.md)
-------------------------------------

  TabR resmi baseline lama (seed 11, 392 fitur, bocor): 0.7428 test
  (threshold 0.555 -> 0.7483).
  392 run 1 jujur: test 0.6123 / macroF1 0.5358 / bal_acc 0.5516.
  392 run 2 sekarang: test 0.6271 / macroF1 0.5067 / bal_acc 0.5440.
  roi25 (run lama, split 23.742/8.922/9.190): 0.6337 / 0.5964 / 0.5962.
  Datatest (tanggal baru): acc 0.61-0.72, macroF1 0.39-0.47.
  SVM (SAMM, tugas beda): 0.91-0.95 in-sample, jatuh ke 0.22 external.
