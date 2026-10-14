CATATAN AWAL (BEFORE) - SNAPSHOT STATE PROYEK
================================================

Tanggal      : 2026-08-25
Pembuat      : agent (sesi analisis kodebase)
Tujuan       : Merekam keadaan ASLI proyek sebelum ada perubahan apa pun.
               Dokumen ini dipakai sebagai pembanding: kalau nanti ada
               file/direktori berubah, hilang, atau ditambah, kita bisa
               lihat bedanya dari catatan ini.

Backup fisik : /home/finny/projects/Skripsi-backup-2026-08-25/
               (satu-satunya backup: kondisi saat ini termasuk .git,
               model dlib, dan clone TabR; 668 MB, 81.829 file,
               tanpa .venv; dibuat 25/08/2026, checksum diverifikasi)

Sumber       : hasil investigasi langsung ke folder proyek
               (ls, du, git, find, glob) pada tanggal di atas.


=====================================================================

1. IDENTITAS PROYEK
--------------------

  - Lokasi         : /home/finny/projects/Skripsi
  - Repo git       : YA (HEAD 2053d6e "Merge pull request #1 from
                     SyahrulBhudiF/apex/v3")
  - Status git     : bersih; satu folder tidak ter-track (.eleanore/)
  - Python         : >= 3.12, < 3.13 (aturan di pyproject.toml)
  - Manajer paket  : uv (uv.lock ada; .venv BELUM ada)
  - GPU            : GTX 1650 Ti Mobile (VRAM 4 GB)


=====================================================================

2. YANG ADA (KODE DAN DOKUMEN)
-------------------------------

  Folder                 Ukuran   Isi
  ---------------------- -------- ------------------------------------
  core/                  40K      TabR.py, tabr_v2.py, tabr_faithful.py,
                                  encoder.py, value_correction.py,
                                  data_module.py, utis.py
  features_extraction/   16K      poc.py, vektor.py, quadran.py
  apex/                  28K      apex_phase.py, apex_smoother.py,
                                  apex_phase_visualizer.py
  preprocess-anxiety/    78M      spotting.py + notebook besar
                                  (process_all_datasets.ipynb 55MB)
  scripts/               48K      export_to_official_tabr_dataset*.py
                                  (4 script) + run_official_tabr*.sh (6 script)
  comparasion/           1.7M     main.py + core/ (config, roi, pipeline,
                                  dataset, models, tabular) + notebooks/
  notebooks/             5.4M     tabr_final_analysis.ipynb,
                                  tabr_datatest_event_inference.ipynb,
                                  tabr_compare_*, tabr_*_tuning.ipynb
  third_party/           8K       tabular_dl_tabr_adapter.py SAJA
  Super-Refine/          4.9M     percobaan GFPGAN + Real-ESRGAN
                                  (tidak dipakai pipeline utama)
  logs/                  6.7M     tabr_overnight_20260324_*.log
  helper/                4K       helper.py
  conv1_base.py          14K      template CNN (RUSAK: "class %(nn.Module)")
  foundings.md                    dokumen temuan + rencana (dibuat 25/08)
  pyproject.toml + uv.lock        dependensi: torch, torchvision, lightning,
                                  optuna, faiss-gpu-cu12, dlib, delu, dll.


=====================================================================

3. YANG TIDAK ADA (SEMUA DATA MENTAH DAN OUTPUT)
--------------------------------------------------

  Direktori / File                          Status
  ----------------------------------------- ---------------------------
  dataset/                                  TIDAK ADA (di-gitignore)
  ../dataset (di luar folder proyek)        TIDAK ADA (video mentah .avi
                                            200 fps aslinya di sini)
  output/                                   TIDAK ADA (semua hasil:
                                            frames, magnitudes, apex,
                                            dataset, features)
  output_casme2/                            TIDAK ADA (hasil comparasion)
  models/                                   TIDAK ADA
  preprocess-anxiety/models/
    shape_predictor_68_face_landmarks.dat   TIDAK ADA (model dlib)
  comparasion/output_casme2/                TIDAK ADA
  data_raw/, SAMM/, Casme3/                 TIDAK ADA (dataset eksternal)
  lightning_logs/, checkpoints/             TIDAK ADA
  testing/, testing_output/, testing_preprocess/  TIDAK ADA
  new_images/, features_grouped/,
    tabr_experiment/, gfpgan/, onset_apex/  TIDAK ADA
  third_party/tabular-dl-tabr-official/     FOLDER KOSONG (isinya:
                                            bin/, lib/, exp/, data/ —
                                            semua tidak ada)
  .venv                                     TIDAK ADA


=====================================================================

4. CATATAN PENTING TENTANG KEADAAN ASLI
-----------------------------------------

  1. Folder third_party/tabular-dl-tabr-official/ KOSONG.
     Padahal skrip v25 (run_official_tabr_v25.sh) memanggil
     bin/go.py + config .toml di dalamnya. Artinya: repo resmi Yandex
     TabR belum di-clone, dan config TOML (0-tuning.toml,
     0-evaluation/*.toml) juga hilang.

  2. Model dlib (shape_predictor_68_face_landmarks.dat) tidak ada.
     Tanpa file ini, ROI extraction tidak bisa jalan.

  3. Semua video mentah tidak ada di komputer ini (../dataset).
     Notebook menyimpan path lama milik orang lain:
       /home/ryuko/Documents/Codes/Python/Skripsi/Convat-1st/...
     Semua path seperti ini HARUS diganti dulu sebelum menjalankan.

  4. Log v25 (logs/tabr_overnight_20260324_220851.log) berasal dari
     mesin lain dan isinya run yang GAGAL (AssertionError).

  5. Jupyter tidak terpasang di PATH (/usr/bin/python, uv tersedia).
     Notebook dijalankan lewat `uv run jupyter` setelah uv sync.

  6. Satu-satunya artefak data yang ter-track git:
     preprocess-anxiety/analisis_versi_summary.csv (riwayat konfigurasi
     percobaan v1-v21, tanpa kolom akurasi).

  7. Di gitignore, semua *.md tidak ter-track — termasuk dokumen ini
     dan foundings.md. Kalau mau di-commit, hapus baris "*.md".


=====================================================================

5. CARA MENJALANKAN (HOW TO RUN)
----------------------------------

Urutan yang benar dari video mentah sampai hasil model.
Setiap langkah menandai bagian mana yang HILANG dan perlu disiapkan dulu.

---------------------------------------------------------------------
INSTALASI (PERTAMA KALI)
---------------------------------------------------------------------

A. Paket sistem (Fedora / Nobara):
   sudo dnf install -y git cmake gcc-c++ ffmpeg

   (cmake + gcc-c++ dipakai untuk build dlib.
    ffmpeg dipakai oleh moviepy / opencv.)

B. Install uv (kalau belum ada):
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv --version

C. Pasang dependensi Python (otomatis buat .venv + Python 3.12):
   cd /home/finny/projects/Skripsi
   uv sync

   Catatan:
   - faiss-gpu-cu12 butuh driver NVIDIA + CUDA 12.
     Kalau gagal, ganti "faiss-gpu-cu12" -> "faiss-cpu" di pyproject.toml.
   - dlib butuh cmake. Kalau build gagal, coba:
       DLIB_NO_GUI_SUPPORT=1 uv sync

D. Verifikasi instalasi:
   uv run python -c "import torch, faiss, dlib, cv2; print('OK')"
   uv run python -c "import torch; print('cuda:', torch.cuda.is_available())"

E. Unduh model dlib (WAJIB, sekarang tidak ada):
   mkdir -p preprocess-anxiety/models
   wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
   bunzip2 shape_predictor_68_face_landmarks.dat.bz2
   mv shape_predictor_68_face_landmarks.dat preprocess-anxiety/models/

F. Clone repo TabR resmi (WAJIB, sekarang folder kosong):
   git clone https://github.com/yandex-research/tabular-dl-tabr \
     third_party/tabular-dl-tabr-official

   PENTING: bin/go.py dan config exp/tabr/convat_apex_anxiety/*.toml
   TIDAK ada di repo resmi (itu buatan tim sebelumnya) — harus dibuat
   ulang dari notebook/scripts sebelum training bisa jalan.

G. Data mentah video (tidak bisa di-install, minta ke tim):
   Struktur yang diharapkan:
     ../dataset/{before|after}/{anxiety|tidak}/{subjek}/q{1..5}/*.avi

---------------------------------------------------------------------
LANGKAH 0 - Siapkan lingkungan Python
---------------------------------------------------------------------

  cd /home/finny/projects/Skripsi
  uv sync

  Catatan:
  - uv akan membuat .venv sesuai pyproject.toml (Python 3.12).
  - faiss-gpu-cu12 butuh CUDA 12. GPU 4 GB cukup untuk TabR kecil,
    tapi kalau driver tidak mendukung, ganti jadi faiss-cpu.
  - dlib butuh build tool (cmake). Kalau gagal: sudo dnf install cmake.
  - Jupyter: jalankan lewat uv:
      uv run jupyter notebook

---------------------------------------------------------------------
LANGKAH 1 - Siapkan model dlib (HILANG, wajib diunduh)
---------------------------------------------------------------------

  mkdir -p preprocess-anxiety/models
  wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
  bunzip2 shape_predictor_68_face_landmarks.dat.bz2
  mv shape_predictor_68_face_landmarks.dat preprocess-anxiety/models/

  Alamat ini sudah dikode: comparasion/core/config.py baris 23.

---------------------------------------------------------------------
LANGKAH 2 - Siapkan data mentah (HILANG, minta ke tim)
---------------------------------------------------------------------

  Struktur yang diharapkan kode:
    ../dataset/{label}/{participant}/q{1..5}/*.avi

  Contoh: ../dataset/before/anxiety/subjekA/q1/video.avi
  (label: before/after, anxiety/tidak — lihat foundings.md bagian 2)

  Video asli 200 fps kamera Intel RealSense (.avi).
  Kalau belum punya, seluruh pipeline tidak bisa dijalankan.

---------------------------------------------------------------------
LANGKAH 3 - Spotting (mencari apex/event)
---------------------------------------------------------------------

  Buka dan jalankan notebook:
    preprocess-anxiety/process_all_datasets.ipynb

  Yang dilakukan notebook ini:
  - baca video per pertanyaan
  - deteksi wajah + landmark (dlib)
  - potong ROI + hitung POC-ABS per frame
  - cari apex (Savitzky-Golay + find_peaks)
  - simpan event clip ke output/apex/dataset/... + metadata.xlsx

  PENTING sebelum jalan:
  - ganti semua path "/home/ryuko/..." dan "../dataset" ke lokasi asli
  - logika spotting sebenarnya tidak ada di file .py (run_spotting()
    di preprocess-anxiety/spotting.py masih NotImplementedError),
    jadi satu-satunya sumber logika adalah notebook ini.

  Bisa juga dijalankan dari terminal (headless, sama seperti Run All):
    uv run jupyter nbconvert --to notebook --execute --inplace \
      preprocess-anxiety/process_all_datasets.ipynb

---------------------------------------------------------------------
LANGKAH 4 - Ekspor fitur ke tabel
---------------------------------------------------------------------

  Buka dan jalankan notebook:
    preprocess-anxiety/export_apex_poc_abs_ordered.ipynb

  Hasil: output/apex/features/poc_abs_flatten_ordered.xlsx
  - 407 kolom = 392 fitur + kolom meta
  - sekitar 2.764 event clip

  Headless dari terminal:
    uv run jupyter nbconvert --to notebook --execute --inplace \
      preprocess-anxiety/export_apex_poc_abs_ordered.ipynb

---------------------------------------------------------------------
LANGKAH 5 - Ekspor ke format resmi TabR (npy)
---------------------------------------------------------------------

  uv run python scripts/export_to_official_tabr_dataset.py

  Hasil: X_num_{train,val,test}.npy + Y_*.npy + info.json
  di dalam third_party/tabular-dl-tabr-official/data/convat_apex_anxiety/

  Variasi lain:
    uv run python scripts/export_to_official_tabr_dataset_qholdout.py
    uv run python scripts/export_to_official_tabr_dataset_qwalkforward.py

---------------------------------------------------------------------
LANGKAH 6 - Training TabR resmi (Yandex)
---------------------------------------------------------------------

  Siapkan repo resmi (HILANG):
    git clone https://github.com/yandex-research/tabular-dl-tabr \
      third_party/tabular-dl-tabr-official

  Config TOML (0-tuning.toml) juga hilang — harus dibuat ulang.
  Skrip asli memanggil:
    cd third_party/tabular-dl-tabr-official
    uv run python bin/go.py exp/tabr/convat_apex_anxiety/0-tuning.toml

  Versi final (ensemble 2x5):
    uv run python bin/ensemble.py 0-evaluation \
      --n-ensembles 2 --ensemble-size 5

  Referensi konfigurasi yang dipakai dulu (dari logs):
    seed 72, batch 128, patience 4-6, context_size 7-12,
    lr ~3.37e-4, wd ~1.76e-5, 30 trial Optuna.

---------------------------------------------------------------------
LANGKAH 7 - Baseline (SVM/KNN/LSTM) & comparasion
---------------------------------------------------------------------

  Pipeline comparasion (CASME2/SAMM style) bisa dipanggil:
    uv run python -c "from comparasion.main import run_all; \
      run_all('<lokasi_dataset>')"

  Hasil: output_casme2/... (poc_abs_flatten.xlsx + quadran_sum.xlsx)

  Catatan: baseline SVM/KNN/LSTM dikerjakan di notebook
  comparasion/notebooks/ (svm_*, knn_*, lstm_*).


=====================================================================

6. APA YANG PERLU DISIAPKAN SEBELUM BISA RUN (RINGKAS)
--------------------------------------------------------

  1. Data video mentah ............ minta ke tim (../dataset)
  2. Model dlib ................... unduh shape_predictor (Langkah 1)
  3. Repo TabR resmi .............. git clone (Langkah 6)
  4. Config TOML TabR ............. buat ulang (hilang dari mesin ryuko)
  5. Path hardcoded ................ ganti "/home/ryuko/..." ke lokal
  6. Environment ................... uv sync (Langkah 0)

  Sampai keenam hal ini beres, pipeline tidak bisa dijalankan
  ujung ke ujung. Ini juga alasan kenapa foundings.md menyarankan
  Fase 0 (kembalikan yang hilang) dikerjakan pertama.


=====================================================================

LAMPIRAN A - PERUBAHAN SETELAH SNAPSHOT (25/08/2026, malam)
-------------------------------------------------------------

Bagian ini mencatat instalasi yang dilakukan SETELAH snapshot dibuat,
supaya "keadaan asli" di atas tetap bisa dibedakan dari perubahan.

  1. Python 3.12.13 di-install via uv
     (uv python install 3.12; disimpan di ~/.local/share/uv/python/)

  2. uv sync BERHASIL - .venv dibuat (7,5 GB), berisi antara lain:
     - torch 2.9.1+cu128 (CUDA AKTIF di GTX 1650 Ti, 4 GB)
     - torchvision 0.24.1, lightning, optuna
     - faiss 1.14.1, dlib 20.0.0, opencv 4.11.0
     - pandas, numpy, scikit-learn, delu, dll.

  3. Model dlib diunduh:
     preprocess-anxiety/models/shape_predictor_68_face_landmarks.dat
     (96 MB, dari dlib.net, diverifikasi bisa dimuat)

  4. Repo TabR resmi di-clone:
     third_party/tabular-dl-tabr-official/
     (git clone --depth 1 github.com/yandex-research/tabular-dl-tabr;
      berisi bin/go.py, bin/tabr.py, lib/, exp/ benchmark)
     - config exp/tabr/convat_apex_anxiety/*.toml TETAP TIDAK ADA
       (buatan tim sebelumnya, perlu dibuat ulang)

  Yang MASIH hilang (bukan urusan instalasi):
  1. Data video mentah ../dataset (minta ke tim)
  2. Config TOML TabR (harus dibuat ulang, lihat foundings.md Fase 0)
  3. Path hardcoded /home/ryuko/... di notebook (ganti ke lokal)

---------------------------------------------------------------------
LAMPIRAN B - BACKUP (SATU-SATUNYA, 25/08/2026)
-------------------------------------------------------------

  Backup kondisi saat ini (semua kode + .git + clone TabR + model
  dlib), TANPA .venv (7,5 GB, bisa dibuat ulang dengan uv sync):

  Lokasi : /home/finny/projects/Skripsi-backup-2026-08-25/
  Isi    : 668 MB, 81.829 file (termasuk .git, foundings.md, before.md,
           third_party/tabular-dl-tabr-official/, model dlib)
  Cek    : checksum diverifikasi identik dengan aslinya

  Catatan: kondisi asli SEBELUM instalasi tetap bisa dilihat lewat
  git history repo ini (HEAD 2053d6e) — tidak perlu backup terpisah.
