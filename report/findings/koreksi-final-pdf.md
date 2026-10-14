# Koreksi FINAL.pdf — penyelarasan tulisan dengan kode & hasil jujur

Tanggal: 2026-10-13
Untuk: diterapkan ke sumber dokumen (Word/Google Docs). PDF tidak diedit langsung.
Prinsip: semua angka/parameter di tulisan harus persis sama dengan kode yang
dijalankan, dan angka performa memakai protokol jujur (LOSO), bukan split lama.

---

## Ringkasan koreksi (lama → baru)

| # | Bagian | Lama (FINAL.pdf) | Baru (kode/fakta) |
|---|---|---|---|
| 1 | Abstrak + BAB II/III | block size 7×7 | **block size 9×9** |
| 2 | BAB III (ROI) | 3 ROI: mata-alis kanan/kiri (48×32) + mulut (70×35) | **5 ROI**: mulut 70×35, mata kiri/kanan 48×32, alis kiri/kanan 64×24 |
| 3 | BAB V (deteksi event) | distance 5, prominence 0.5, smoothing tidak disebut adaptif | **distance 1, prominence max(0,04 × rentang sinyal, 0,005), smoothing savgol 3% adaptif, ranking prominence** |
| 4 | BAB V (protokol pengujian) | GroupShuffleSplit 33/11/12 + tune.py 15 seed + ensemble 5 model | **LOSO 56 fold**, split sebelum preprocessing, imputer+scaler fit di train saja |
| 5 | BAB VI (angka performa) | train 0,9904 / val Q4 0,7592 / test Q5 0,7579 / datatest 0,58 | **LOSO test 54,46%** (AUC 0,5204); baseline mayoritas 57,14%; **gate within-subject BA 0,75, p=0,01** |
| 6 | BAB VI Tabel 6.10 | threshold/magnitude 2 video contoh | perbarui dengan angka dari sinyal final (mean_m) bila ada |

---

## 1. Block size 7×7 → 9×9

**Teks pengganti (Abstrak & semua penyebutan "7×7"):**

> Fitur pergerakan mikro diekstraksi menggunakan POC-ABS dengan block size 9×9
> dalam bentuk X, Y, theta, dan magnitude.

**Kalimat justifikasi tambahan untuk BAB III (letakkan setelah penjelasan block size):**

> Pemilihan block size 9×9 didasarkan pada evaluasi saturasi estimasi
> pergeseran. Saturasi terjadi ketika perpindahan melebihi (block_size−1)/2
> piksel. Pengukuran pada 18 klip × 8 frame menunjukkan block size 7
> menghasilkan 4,6% blok mentok di batas pencarian, sedangkan block size 9
> menurunkannya menjadi 1,4% tanpa merusak resolusi spasial ROI. Block size
> yang lebih besar (11–13) menurunkan saturasi lebih jauh tetapi menyisakan
> terlalu sedikit baris blok pada ROI alis, sehingga tidak dipilih.

---

## 2. ROI: 3 → 5 region

**Teks pengganti untuk poin ROI di BAB III:**

> Wajah dipetakan ke dalam lima region of interest (ROI) berdasarkan 68 titik
> landmark dlib: area mulut (landmark 48–67, dinormalisasi ke 70×35 piksel),
> area mata kiri (36–41) dan mata kanan (42–47) (masing-masing 48×32 piksel),
> serta area alis kiri (17–21) dan alis kanan (22–26) (masing-masing 64×24
> piksel). Setiap ROI diperluas dengan padding horizontal 6 piksel dan
> vertikal 8 piksel.
>
> Area alis dipisahkan dari area mata (tidak digabung menjadi satu ROI
> mata-alis) karena penggabungan membuat fitur alis sepenuhnya berada di dalam
> fitur mata sehingga keduanya redundan. Gerakan alis (AU1/AU2/AU4) dan gerakan
> kelopak mata (AU5/AU7) merupakan sinyal yang berbeda secara diagnostik,
> sehingga pemisahan ROI mempertahankan informasi dari keduanya.

(Tabel contoh bentuk hasil data di BAB III menyesuaikan: 5 kelompok fitur.)

---

## 3. BAB V — parameter deteksi event

**Teks pengganti untuk blok konfigurasi deteksi fase:**

```python
distance_threshold: int = 1
prominence_threshold: float = max(0.04 * rentang_sinyal, 0.005)
cutoff_ratio: float = 0.3
height_threshold: float = mean(sinyal_halus) + std(sinyal_halus)
top_k_apex: int = 5
merge_distance: int = 10
min_phase_duration: int = 2
```

**Penjelasan pengganti:**

> Sinyal magnitude diratakan menggunakan filter Savitzky-Golay dengan panjang
> window adaptif sebesar 3% dari panjang sinyal (dibulatkan ganjil, minimal 5
> frame) dan polyorder menyesuaikan ukuran window. Pemilihan kandidat apex
> menggunakan peringkat prominence, yaitu tingkat kemenonjolan lokal puncak,
> bukan nilai absolut sinyal, karena puncak micro-expression sering kali bukan
> puncak tertinggi pada sinyal yang memuat gerakan lain. Ambang tinggi puncak
> ditentukan adaptif sebagai mean + 1 standar deviasi sinyal hasil smoothing,
> dan prominence minimum ditentukan relatif terhadap 4% rentang sinyal halus.
> Batas onset dan offset ditentukan dengan cutoff_ratio 0,3 dari amplitudo
> lokal puncak terhadap lembah sekitarnya. Konfigurasi ini dievaluasi pada
> dataset CAS(ME)² dengan ground truth onset/apex/offset dan menghasilkan F1
> sebesar 0,3192 pada 86 video (308 ekspresi), meningkat sekitar 49% relatif
> dibandingkan konfigurasi awal (F1 0,2141).

(Gambar 5.2/5.3/5.5 tetap relevan; keterangan "mean + 1σ" sudah cocok.)

---

## 4. BAB V — protokol pengujian (ganti total sub-bab tuning/ensemble)

**Teks pengganti:**

> Evaluasi model dilakukan dengan protokol Leave-One-Subject-Out (LOSO)
> cross-validation pada 56 subjek. Pada setiap fold, satu subjek menjadi data
> uji dan 55 subjek sisanya menjadi data latih, dengan sebagian subjek latih
> dipakai sebagai data validasi untuk early stopping. Seluruh tahap
> pra-pemrosesan — penyeimbangan kelas, imputasi nilai kosong (mean), dan
> normalisasi fitur (StandardScaler) — hanya di-fit pada data latih fold
> tersebut, kemudian diterapkan (transform) ke data validasi dan data uji.
> Pembagian data selalu dilakukan sebelum pra-pemrosesan untuk mencegah
> kebocoran informasi dari data uji ke model.
>
> Protokol ini dipilih karena tujuan sistem adalah mengenali kondisi anxiety
> pada orang yang belum pernah dilihat model. Pembagian acak pada level frame
> atau klip membuat frame dari orang yang sama muncul di data latih dan data
> uji sekaligus, sehingga model dapat menghafal identitas orang alih-alih
> mempelajari pola anxiety, dan menghasilkan angka evaluasi yang terlalu
> optimis.

(Hapus bagian tune.py 15 seed, pemilihan seed terbaik dari val, dan ensemble
5 model — itu artefak protokol lama.)

---

## 5. BAB VI — angka performa (ganti Tabel 6.5/6.7/6.9 dan pembahasan 6.2.2)

**Tabel pengganti ringkasan performa:**

| Evaluasi | Protokol | Hasil |
|---|---|---|
| Klasifikasi state (sesi before/after, 112 unit) | LOSO 56 fold | accuracy test 54,46%; train 89,9%; val 62,5%; AUC 0,5204; sensitivity 0,79; specificity 0,15 |
| Baseline mayoritas | — | 57,14% |
| Klasifikasi trait (level orang) | LOSO | 41–49% (semua varian di bawah baseline) |
| **Gerbang within-subject** (fitur rise, logistic, berpasangan per subjek) | paired test | **balanced accuracy 0,75, p = 0,01** |

**Teks pengganti pembahasan:**

> Hasil evaluasi LOSO menunjukkan klasifikasi anxiety lintas subjek dari fitur
> POC-ABS per-frame belum melampaui baseline mayoritas (54,46% vs 57,14%),
> dengan AUC 0,5204 yang menandakan kemampuan pemeringkatan lintas subjek
> masih mendekati acak. Analisis karakterisasi fitur menunjukkan penyebabnya:
> sekitar 79% varians fitur dijelaskan oleh perbedaan identitas antar-orang,
> bukan kondisi anxiety, sehingga model kesulitan menggeneralisasi ke orang
> baru.
>
> Hasil yang signifikan diperoleh pada evaluasi within-subject: perubahan
> fitur POC-ABS antara sesi sebelum dan sesudah pemicu (fitur rise, yaitu
> kemiringan onset menuju apex) membedakan kondisi anxiety dan bukan dengan
> balanced accuracy 0,75 (p = 0,01, uji berpasangan pada subjek yang sama).
> Artinya sinyal pergerakan mikro yang diekstraksi POC-ABS memang memuat
> informasi anxiety ketika perbandingan dilakukan terhadap baseline orang yang
> sama, meskipun generalisasi lintas subjek masih menjadi batasan.
>
> Angka evaluasi pada draft sebelumnya (akurasi uji 0,7579 pada split
> Q4/Q5 dan 0,58 pada datatest) diperoleh dengan pembagian data level frame,
> yang terbukti bocor: frame dari subjek yang sama muncul di data latih dan
> uji. Angka tersebut tidak dilaporkan sebagai hasil karena tidak
> merepresentasikan kemampuan generalisasi model.

---

## 6. Tabel 6.10 (ringkasan spotting)

Perbarui setelah pipeline final dijalankan ulang; gunakan angka dari sinyal
final (agregasi mean_m). Format tabel tetap. Nilai spotting CAS(ME)² yang sah
untuk dikutip sekarang: **F1 = 0,3192** (86 video, 308 GT, toleransi 0 frame).

---

## 7. BAB V — acuan sinyal magnitude (frame berurutan → frame-0)

Listing `build_magnitude_signal` di FINAL.pdf membandingkan frame berurutan
(prev vs curr) dan memberi `mag = 0.0` saat landmark gagal. Kode yang
dijalankan sekarang berbeda pada dua hal itu.

**Teks pengganti:**

> Sinyal magnitude dibangun dengan membandingkan setiap frame terhadap frame
> pertama video (baseline tetap, POC-ABS), bukan terhadap frame sebelumnya.
> Pemilihan baseline tetap dievaluasi pada 41 video CAS(ME)² dan mengungguli
> acuan frame berurutan maupun acuan lag-10/lag-30 (F1 0,3486 vs 0,14–0,19),
> karena pada video 30 fps perpindahan antar-frame berurutan lebih kecil dari
> satu piksel sehingga terkuantisasi menjadi nol. Bila landmark wajah gagal
> terdeteksi pada suatu frame, nilai sinyal pada frame tersebut diisi melalui
> interpolasi linier dari frame sekitarnya, bukan diberi nilai nol, agar tidak
> menimbulkan puncak palsu pada sinyal.

## 8. BAB V — parameter smoother & detektor (sinkronisasi listing)

Listing `ApexSmoother` memakai window 5% dan `polyorder = min(3, window−2)`;
kode memakai **3% adaptif** dan polyorder 2/3/4 menurut ukuran window
(audit 86 video: 3% adaptif F1 0,315–0,320 vs 5%/tetap 0,213–0,260).
Listing `ApexPhase` memakai distance 5 dan prominence 0,5; kode memakai
**distance 1, prominence max(0,04 × rentang sinyal, 0,005)**, ditambah tiga
parameter yang belum didokumentasikan: **merge_distance 10** (penggabungan
puncak berdekatan), **valley_uptick_threshold 0,75** (batas kenaikan saat
mencari lembah fase), dan **MAX_SEARCH_RADIUS 100** (radius maksimal
pencarian onset/offset dari apex). Sinkronkan listing dengan nilai-nilai ini.

## 9. BAB V — listing POC (float64 → int) dan daftar blok

- Listing `POC.__init__` menyebut konversi ke float64 "agar proses perhitungan
  numerik lebih stabil"; kode yang dijalankan mengonversi blok ke **int**
  (mengikuti implementasi paper). Dokumentasikan yang dijalankan.
- "mulut 70×35 → 10×5 = 50 blok (7×7), mata-alis 48×32 → 24 blok, total 98
  blok × 4 = 392 fitur": hitung ulang dengan block 9 dan 5 ROI aktual
  (mulut 7×3 = 21, mata 5×3 = 15, alis 7×2 = 14; total 2×15 + 2×14 + 21 =
  79 blok × 4 = **316 fitur**), dan sesuaikan Tabel 4.8 menjadi lima kelompok
  fitur. Tabel 4.5.1 juga menyebut "area yang diambil yaitu alis dan mulut"
  dan "block size 7x7" — samakan dengan koreksi #1/#2.

## 10. Definisi M di Tabel 4.8 dan sinyal spotting (hasil audit Hpoc)

Di paper POC-ABS (Rosiani dkk., 2020), fitur **M per blok adalah nilai puncak
korelasi (Hpoc)**, bukan panjang vektor |V| — contoh mereka XB28=2, YB28=2
dengan MB28=0,46 (= nilai puncak 0,4687 yang ditampilkan). Implementasi kita
memakai |V| untuk vektor fitur. Hasil audit (`scripts/audit_hpoc_casme2.py`,
86 video CAS(ME)²): untuk SPOTTING, kombinasi z(|V|)+z(Hpoc) tervalidasi
sedikit lebih baik dari |V| saja (F1 0,3343 vs 0,3192, terpilih di kedua fold
validasi subjek); resep persis paper (acuan berurutan, eksklusi blok diam,
block 5) justru lebih buruk pada data 30 fps kita.

**Teks tambahan untuk BAB V (bila SPOT_SIGNAL=combo diadopsi setelah uji A/B
sisi anxiety):**

> Sinyal spotting menggabungkan dua besaran per frame: rata-rata panjang
> vektor gerak blok (|V|) dan rata-rata penurunan nilai puncak korelasi
> (1 − Hpoc), masing-masing dinormalisasi z-score per video lalu dijumlahkan.
> Besaran kedua sesuai dengan definisi fitur M pada paper POC-ABS asli dan
> bersifat kontinu sehingga tetap membawa informasi pada perpindahan di bawah
> satu piksel; kombinasi keduanya dievaluasi pada CAS(ME)² dan menghasilkan
> F1 0,3343 (vs 0,3192 untuk |V| saja).

(Tabel 4.8 TETAP: M = |V| untuk vektor fitur per blok — tidak berubah.)

---

## Catatan tambahan untuk konsistensi

- Konfigurasi TabR di BAB III (n_external 2, batch 128, maks 50 epoch,
  context freezing) cocok dengan implementasi model kustom; pastikan angka
  n_external di tulisan mengikuti model yang dipakai di hasil akhir
  (model kustom memakai m = 4 tetangga retrieval, context freezing epoch 6,
  learning rate 3e-4, hidden 128).
- Istilah: samakan "fase before/after ujian" dengan definisi label sesi
  (18 dari 56 subjek berubah label antar-sesi — label milik sesi, bukan orang).
